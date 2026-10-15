"""Content/Media use cases: purge raw input."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import JOB_NOT_FOUND
from ..runtime import ContextRuntime
from ..runtime import require_durable_media_jobs
from .append_audit import helper_append_audit
from ...storage import delete_minio_object
from fastapi import HTTPException
from fastapi import Request
from fastapi import Query
from typing import Annotated
from typing import Any
import hashlib
import os


def execute_purge_raw_input(
    runtime: ContextRuntime,
    storage_key: Annotated[str, Query(min_length=1, max_length=1024)],
    auth: AuthDep,
    request: Request | None = None,
) -> dict[str, Any]:
    """Delete a tenant-owned raw-input object through configured MinIO storage.

    Invalid magic-byte uploads should be deleted immediately. The call fails
    explicitly unless credentials and the real storage signer are configured.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:purge", 120, 60)
    tenant_prefix = f"raw-input/{auth.tenant_id}/"
    if not storage_key.startswith(tenant_prefix):
        raise HTTPException(
            status_code=403, detail=f"storage_key must begin with {tenant_prefix!r} (tenant isolation)."
        )
    if "\\" in storage_key or any(segment in {"", ".", ".."} for segment in storage_key.split("/")):
        raise HTTPException(status_code=400, detail="storage_key contains an invalid path segment.")
    bucket = os.getenv("MINIO_RAW_INPUT_BUCKET", "raw-input")
    production = os.getenv("ENVIRONMENT", "development").strip().lower() in {"prod", "production"}
    if production:
        from ....identity.security_audit import durable_audit_enabled, record_security_event

        if not durable_audit_enabled():
            raise HTTPException(status_code=503, detail="Durable security audit is unavailable.")
        peer = request.client.host if request is not None and request.client is not None else ""
        record_security_event(
            tenant_id=auth.tenant_id,
            event_type="media_raw_input_delete_requested",
            principal_id=auth.subject,
            auth_mode=auth.auth_mode,
            method="DELETE",
            path=request.url.path if request is not None else "/media/raw-input",
            request_id=str(getattr(request.state, "request_id", "")) if request is not None else "",
            client_ip=peer,
            user_agent=request.headers.get("user-agent", "") if request is not None else "",
            metadata={"bucket": bucket, "storage_key_sha256": hashlib.sha256(storage_key.encode()).hexdigest()},
        )
    delete_minio_object(bucket, storage_key)
    if not production:
        helper_append_audit(runtime, auth.tenant_id, f"media_raw_purged:{storage_key[:80]}")
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "storage_key": storage_key,
        "deleted_from_storage": True,
        "note": "Purged from raw-input bucket.",
    }


def execute_job_audit_trail(runtime: ContextRuntime, job_id: int, auth: AuthDep) -> dict[str, Any]:
    """
    NEW: Full audit trail for a specific job — all state transitions,
    timestamps, DLQ history, and provider dispatch events.
    """
    require_durable_media_jobs()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:audit", 120, 60)
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
    with runtime._lock:
        related_audit = [
            e.copy()
            for e in runtime.audit_log_memory
            if e.get("tenant_id") == auth.tenant_id and e.get("job_id") == job_id
        ]
        dlq_entries = [
            d.copy()
            for d in runtime.media_jobs_dlq_memory
            if d.get("tenant_id") == auth.tenant_id and d.get("job_id") == job_id
        ]
    related_audit.sort(key=lambda e: str(e.get("created_at", "")))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "job_id": job_id,
        "job": job,
        "audit_events": related_audit,
        "dlq_entries": dlq_entries,
        "event_count": len(related_audit),
    }
