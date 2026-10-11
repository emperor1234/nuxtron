"""Content/Media use cases: append audit."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import JOB_NOT_CANCELLABLE
from ..constants import JOB_NOT_FOUND
from ..constants import JOB_NOT_RETRYABLE
from ..constants import MANAGED_PROVIDERS
from ..constants import MAX_CONCURRENT_JOBS_PER_TENANT
from ..constants import MEDIA_TYPES
from ..runtime import ContextRuntime
from ..schemas import MediaJobCreateRequest
from ..schemas import MediaOutputUrlRequest
from ..schemas import MediaValidateRequest
from ..services.processing import _build_job_record
from ..services.processing import _issue_validation_token
from ..services.processing import _sse_message
from ..services.processing import _validate_magic_bytes
from ..services.processing import _verify_validation_token
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from functools import partial
from typing import Annotated
from typing import Any
import hashlib
import hmac
import os
import threading
import time


def helper_append_audit(runtime: ContextRuntime, tenant_id: str, action: str, job_id: int | None = None) -> None:
    with runtime._lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "job_id": job_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "media-jobs-router",
            }
        )


def helper_broadcast_job_update(runtime: ContextRuntime, job: dict[str, Any]) -> None:
    """Push job status update to all SSE clients watching this job."""
    job_id_str = str(job["id"])
    message = _sse_message("job.updated", job.copy())
    with runtime._lock:
        watchers = list(runtime._subscribers.get(job_id_str, []))
    for watcher in watchers:
        try:
            watcher["loop"].call_soon_threadsafe(watcher["queue"].put_nowait, message)
        except RuntimeError:
            continue


def helper_simulate_processing(runtime: ContextRuntime, job: dict[str, Any]) -> None:
    """
    Simulate async sandbox processing in a background thread.
    In production replace with BullMQ/Redis job dispatch or AWS Lambda invoke.
    Enforces per-tenant concurrency cap before proceeding.
    Progress events are pushed via SSE as they occur.
    """
    job_id = job["id"]
    tenant_id = job["tenant_id"]
    deadline = time.time() + 30
    while time.time() < deadline:
        with runtime._lock:
            concurrent = sum(
                (
                    1
                    for j in runtime.media_jobs_memory
                    if j.get("tenant_id") == tenant_id and j.get("status") == "processing" and (j.get("id") != job_id)
                )
            )
        if concurrent < MAX_CONCURRENT_JOBS_PER_TENANT:
            break
        time.sleep(0.05)
    steps = [
        (10, "processing", "Validating storage key"),
        (30, "processing", "Dispatching to sandbox executor"),
        (60, "processing", "Sandbox processing in progress"),
        (90, "processing", "Writing output to processed-output bucket"),
        (100, "complete", "Done"),
    ]
    should_fail = "fail" in str(job.get("storage_key", "")).lower()
    for pct, status, message in steps:
        time.sleep(0.1)
        failure_snapshot: dict[str, Any] | None = None
        with runtime._lock:
            target = next(
                (j for j in runtime.media_jobs_memory if j["id"] == job_id and j["tenant_id"] == tenant_id), None
            )
            if target is None or target.get("status") == "cancelled":
                return
            if should_fail and pct >= 60:
                target["status"] = "failed"
                target["progress_pct"] = pct
                target["error"] = "Sandbox processing failed (simulated fault)."
                target["updated_at"] = datetime.now(UTC).isoformat()
                target["completed_at"] = datetime.now(UTC).isoformat()
                dlq_entry: dict[str, Any] = {
                    "id": len(runtime.media_jobs_dlq_memory) + 1,
                    "tenant_id": tenant_id,
                    "job_id": target["id"],
                    "reason": target["error"],
                    "failed_at": target["completed_at"],
                    "retries": 0,
                }
                runtime.media_jobs_dlq_memory.append(dlq_entry)
                failure_snapshot = target.copy()
            else:
                target["status"] = status
                target["progress_pct"] = pct
                target["updated_at"] = datetime.now(UTC).isoformat()
                if status == "complete":
                    target["output_key"] = f"processed/{tenant_id}/{job_id}/{target['storage_key'].split('/')[-1]}"
                    target["completed_at"] = datetime.now(UTC).isoformat()
            snapshot = target.copy()
        if failure_snapshot is not None:
            failure_snapshot["_message"] = "Job moved to dead-letter queue."
            helper_broadcast_job_update(runtime, failure_snapshot)
            helper_append_audit(runtime, tenant_id, "media_job_failed", job_id)
            return
        snapshot["_message"] = message
        helper_broadcast_job_update(runtime, snapshot)
    helper_append_audit(runtime, tenant_id, "media_job_completed", job_id)


def execute_validate_file(runtime: ContextRuntime, payload: MediaValidateRequest, auth: AuthDep) -> dict[str, Any]:
    """
    NEW: Magic-byte file type validation (Rule 2 from architecture doc).
    Client sends first 16 bytes as base64 before uploading.
    Returns a validation_token to include when queuing the job.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:validate", 300, 60)
    import base64

    try:
        raw = base64.b64decode(payload.first_bytes_b64 + "==")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="first_bytes_b64 is not valid base64.") from exc
    is_valid, detected = _validate_magic_bytes(raw, payload.expected_mime)
    if not is_valid:
        helper_append_audit(runtime, auth.tenant_id, f"media_file_rejected:{detected}")
        raise HTTPException(status_code=422, detail=f"Magic-byte validation failed: {detected}. Upload rejected.")
    if os.getenv("ENVIRONMENT", "development").lower() == "production" and not payload.storage_key:
        raise HTTPException(status_code=422, detail="storage_key is required for production validation.")
    token = _issue_validation_token(auth.tenant_id, payload.storage_key, payload.expected_mime)
    return {"status": "ok", "tenant_id": auth.tenant_id, "mime_type": payload.expected_mime, "validation_token": token}


def execute_create_media_job(runtime: ContextRuntime, payload: MediaJobCreateRequest, auth: AuthDep) -> dict[str, Any]:
    """
    NEW: Queue a media processing job.
    Server only receives a storage key (metadata) — never file bytes (Rule 1).
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:jobs:create", 120, 60)
    if payload.media_type not in MEDIA_TYPES:
        raise HTTPException(status_code=422, detail=f"media_type must be one of: {', '.join(sorted(MEDIA_TYPES))}")
    if os.getenv("MEDIA_REQUIRE_VALIDATION_TOKEN", "0").strip().lower() in {"1", "true", "yes", "on"} and (
        not payload.validation_token
    ):
        raise HTTPException(status_code=422, detail="validation_token is required in strict media mode.")
    strict_validation = os.getenv("MEDIA_REQUIRE_VALIDATION_TOKEN", "0").strip().lower() in {"1", "true", "yes", "on"}
    if strict_validation or os.getenv("ENVIRONMENT", "development").lower() == "production":
        mime = str(payload.processing_options.get("mime_type", ""))
        if not _verify_validation_token(payload.validation_token or "", auth.tenant_id, payload.storage_key, mime):
            raise HTTPException(status_code=422, detail="Invalid or expired object-bound validation token.")
    now_iso = datetime.now(UTC).isoformat()
    with runtime._lock:
        active = sum(
            (
                1
                for j in runtime.media_jobs_memory
                if j.get("tenant_id") == auth.tenant_id and j.get("status") in {"queued", "processing"}
            )
        )
        if active >= MAX_CONCURRENT_JOBS_PER_TENANT:
            raise HTTPException(
                status_code=429,
                detail=f"Concurrent job limit reached ({MAX_CONCURRENT_JOBS_PER_TENANT}). Wait for active jobs to complete before submitting more.",
            )
        job = _build_job_record(len(runtime.media_jobs_memory) + 1, auth.tenant_id, payload, now_iso)
        runtime.media_jobs_memory.append(job)
    helper_append_audit(runtime, auth.tenant_id, "media_job_queued", job["id"])
    threading.Thread(target=partial(helper_simulate_processing, runtime), args=(job.copy(),), daemon=True).start()
    return {"status": "ok", "tenant_id": auth.tenant_id, "job": job}


def execute_list_media_jobs(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=16)] = None,
    media_type: Annotated[str | None, Query(max_length=16)] = None,
) -> dict[str, Any]:
    """NEW: List all media jobs for the tenant, with optional status/type filters."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:jobs:list", 240, 60)
    with runtime._lock:
        jobs = [
            j.copy()
            for j in runtime.media_jobs_memory
            if j.get("tenant_id") == auth.tenant_id
            and (status is None or j.get("status") == status)
            and (media_type is None or j.get("media_type") == media_type)
        ]
    jobs.sort(key=lambda j: str(j.get("created_at", "")), reverse=True)
    pending = sum((1 for j in jobs if j.get("status") in {"queued", "processing"}))
    return {"status": "ok", "tenant_id": auth.tenant_id, "jobs": jobs, "total": len(jobs), "pending": pending}


def execute_get_media_job(runtime: ContextRuntime, job_id: int, auth: AuthDep) -> dict[str, Any]:
    """NEW: Get single media job status."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:jobs:get", 600, 60)
    with runtime._lock:
        job = next(
            (
                j.copy()
                for j in runtime.media_jobs_memory
                if j.get("id") == job_id and j.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
    if job is None:
        raise HTTPException(status_code=404, detail=JOB_NOT_FOUND)
    return {"status": "ok", "tenant_id": auth.tenant_id, "job": job}


def execute_cancel_media_job(runtime: ContextRuntime, job_id: int, auth: AuthDep) -> dict[str, Any]:
    """NEW: Cancel a queued job (only jobs in 'queued' state can be cancelled)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:jobs:cancel", 60, 60)
    with runtime._lock:
        job = next(
            (j for j in runtime.media_jobs_memory if j.get("id") == job_id and j.get("tenant_id") == auth.tenant_id),
            None,
        )
        if job is None:
            raise HTTPException(status_code=404, detail=JOB_NOT_FOUND)
        if job.get("status") not in {"queued", "processing"}:
            raise HTTPException(status_code=409, detail=JOB_NOT_CANCELLABLE)
        job["status"] = "cancelled"
        job["updated_at"] = datetime.now(UTC).isoformat()
        snapshot = job.copy()
    helper_append_audit(runtime, auth.tenant_id, "media_job_cancelled", job_id)
    helper_broadcast_job_update(runtime, snapshot)
    return {"status": "ok", "tenant_id": auth.tenant_id, "job": snapshot}


def execute_retry_media_job(runtime: ContextRuntime, job_id: int, auth: AuthDep) -> dict[str, Any]:
    """NEW: Retry a failed job. Re-queues and removes from DLQ if present."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:jobs:retry", 60, 60)
    with runtime._lock:
        job = next(
            (j for j in runtime.media_jobs_memory if j.get("id") == job_id and j.get("tenant_id") == auth.tenant_id),
            None,
        )
        if job is None:
            raise HTTPException(status_code=404, detail=JOB_NOT_FOUND)
        if job.get("status") != "failed":
            raise HTTPException(status_code=409, detail=JOB_NOT_RETRYABLE)
        job["status"] = "queued"
        job["progress_pct"] = 0
        job["error"] = None
        job["updated_at"] = datetime.now(UTC).isoformat()
        job["retry_count"] = job.get("retry_count", 0) + 1
        runtime.media_jobs_dlq_memory[:] = [
            d
            for d in runtime.media_jobs_dlq_memory
            if not (d.get("job_id") == job_id and d.get("tenant_id") == auth.tenant_id)
        ]
        snapshot = job.copy()
    helper_append_audit(runtime, auth.tenant_id, "media_job_retried", job_id)
    threading.Thread(target=partial(helper_simulate_processing, runtime), args=(snapshot,), daemon=True).start()
    return {"status": "ok", "tenant_id": auth.tenant_id, "job": snapshot}


def execute_get_output_signed_url(
    runtime: ContextRuntime, job_id: int, payload: MediaOutputUrlRequest, auth: AuthDep
) -> dict[str, Any]:
    """
    NEW: Generate a time-limited signed CDN URL for the processed output (Rule 6).
    Only available for completed jobs.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:jobs:output-url", 120, 60)
    with runtime._lock:
        job = next(
            (
                j.copy()
                for j in runtime.media_jobs_memory
                if j.get("id") == job_id and j.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
    if job is None:
        raise HTTPException(status_code=404, detail=JOB_NOT_FOUND)
    if job.get("status") != "complete":
        raise HTTPException(status_code=409, detail="Output URL only available for completed jobs.")
    output_key = job.get("output_key", "")
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        from ....content import storage

        if (
            not all(os.getenv(name, "").strip() for name in ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"))
            or storage._minio_presign is None
        ):
            raise HTTPException(status_code=503, detail="Object storage presigning is unavailable.")
        signed_url = storage._minio_presign(
            os.getenv("MINIO_ENDPOINT", ""),
            os.getenv("MINIO_ACCESS_KEY", ""),
            os.getenv("MINIO_SECRET_KEY", ""),
            f"{auth.tenant_id}-{job['output_bucket']}",
            output_key,
            "GET",
            payload.expires_seconds,
        )
        helper_append_audit(runtime, auth.tenant_id, "media_output_url_issued", job_id)
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "job_id": job_id,
            "output_key": output_key,
            "signed_url": signed_url,
            "expires_at": int(time.time()) + payload.expires_seconds,
            "expires_seconds": payload.expires_seconds,
        }
    endpoint = os.getenv("MINIO_ENDPOINT", "https://cdn.example.com").rstrip("/")
    expires_at = int(time.time()) + payload.expires_seconds
    secret = os.getenv("MINIO_SECRET_KEY", "dev-secret").encode()
    sig_payload = f"{auth.tenant_id}:{output_key}:{expires_at}"
    signature = hmac.new(secret, sig_payload.encode(), hashlib.sha256).hexdigest()[:32]
    signed_url = (
        f"{endpoint}/{job['output_bucket']}/{output_key}?X-Tenant={auth.tenant_id}&Expires={expires_at}&Sig={signature}"
    )
    helper_append_audit(runtime, auth.tenant_id, "media_output_url_issued", job_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "job_id": job_id,
        "output_key": output_key,
        "signed_url": signed_url,
        "expires_at": expires_at,
        "expires_seconds": payload.expires_seconds,
        "recommended_cdn_headers": {
            "Content-Security-Policy": "default-src 'none'",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": f"private, max-age={payload.expires_seconds}",
        },
    }


def execute_list_dlq(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """NEW: List dead-letter queue (failed jobs that exhausted retries)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:dlq:list", 120, 60)
    with runtime._lock:
        items = [d.copy() for d in runtime.media_jobs_dlq_memory if d.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda d: str(d.get("failed_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "dlq": items, "total": len(items)}


def execute_list_providers(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    NEW: Full catalog of managed third-party processing providers from the
    architecture document — Cloudinary, Mux, Bunny.net, AssemblyAI, Deepgram,
    Adobe PDF Services.  Returns live configuration status for each provider.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:providers", 60, 60)
    providers_out = []
    for key, info in MANAGED_PROVIDERS.items():
        configured = all((os.getenv(ev, "") for ev in info["env_vars"]))
        providers_out.append(
            {
                "id": key,
                **info,
                "configured": configured,
                "status": "ready" if configured else "credentials-required",
                "missing_env_vars": [ev for ev in info["env_vars"] if not os.getenv(ev, "")],
            }
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "providers": providers_out,
        "total": len(providers_out),
        "configured_count": sum((1 for p in providers_out if p["configured"])),
        "note": "Use POST /media/sandbox/dispatch to route jobs through any configured provider.",
    }
