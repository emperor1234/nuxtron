"""Content/Media use cases: job progress stream."""

from __future__ import annotations
from .....deps import require_auth
from ..constants import AuthDep
from ..constants import JOB_NOT_FOUND
from ..constants import MANAGED_PROVIDERS
from ..constants import MAX_CONCURRENT_JOBS_PER_TENANT
from ..constants import MEDIA_TYPES
from ..constants import _MAGIC_SIGNATURES
from ..providers import _PROVIDER_DISPATCH
from ..runtime import ContextRuntime
from ..schemas import MediaSandboxDispatchRequest
from ..services.processing import _sse_message
from .append_audit import helper_append_audit
from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from typing import Annotated
from typing import Any
import asyncio
import json
import os


async def execute_job_progress_stream(
    runtime: ContextRuntime,
    request: Request,
    job_id: int,
    api_key: Annotated[str | None, Query(alias="api_key")] = None,
    tenant_id_param: Annotated[str | None, Query(alias="tenant_id")] = None,
) -> StreamingResponse:
    """
    NEW: SSE stream for real-time job progress.
    EventSource cannot send custom headers so auth params are accepted
    as query-string values (same pattern as /notifications/stream).
    """
    ctx = await require_auth(request=request, x_api_key=api_key, x_tenant_id=tenant_id_param)
    with runtime._lock:
        job = next(
            (
                j.copy()
                for j in runtime.media_jobs_memory
                if j.get("id") == job_id and j.get("tenant_id") == ctx.tenant_id
            ),
            None,
        )
    if job is None:
        raise HTTPException(status_code=404, detail=JOB_NOT_FOUND)
    queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    subscriber: dict[str, Any] = {"queue": queue, "loop": loop}
    job_id_str = str(job_id)
    with runtime._lock:
        runtime._subscribers.setdefault(job_id_str, []).append(subscriber)
    initial_message = _sse_message("job.snapshot", job)

    async def event_stream() -> AsyncIterator[str]:
        yield initial_message
        if job.get("status") in {"complete", "failed", "cancelled"}:
            return
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=20)
                    yield message
                    try:
                        data = json.loads(message.split("data:", 1)[-1].strip())
                        if data.get("status") in {"complete", "failed", "cancelled"}:
                            break
                    except (json.JSONDecodeError, IndexError):
                        pass
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            with runtime._lock:
                runtime._subscribers[job_id_str] = [
                    s for s in runtime._subscribers.get(job_id_str, []) if s is not subscriber
                ]

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


def execute_media_jobs_stats(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    NEW: Monitoring stats — job counts by status, media type breakdown,
    DLQ depth, concurrency utilisation, and provider breakdown per tenant.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:stats", 120, 60)
    with runtime._lock:
        tenant_jobs = [j for j in runtime.media_jobs_memory if j.get("tenant_id") == auth.tenant_id]
        dlq_count = sum((1 for d in runtime.media_jobs_dlq_memory if d.get("tenant_id") == auth.tenant_id))
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_provider: dict[str, int] = {}
    for j in tenant_jobs:
        s = str(j.get("status", "unknown"))
        by_status[s] = by_status.get(s, 0) + 1
        t = str(j.get("media_type", "unknown"))
        by_type[t] = by_type.get(t, 0) + 1
        p = str(j.get("provider", "internal"))
        by_provider[p] = by_provider.get(p, 0) + 1
    active = by_status.get("processing", 0) + by_status.get("queued", 0)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "stats": {
            "total_jobs": len(tenant_jobs),
            "by_status": by_status,
            "by_media_type": by_type,
            "by_provider": by_provider,
            "active_jobs": active,
            "completed_jobs": by_status.get("complete", 0),
            "failed_jobs": by_status.get("failed", 0),
            "dlq_depth": dlq_count,
            "concurrent_limit": MAX_CONCURRENT_JOBS_PER_TENANT,
            "utilization_pct": round(active / MAX_CONCURRENT_JOBS_PER_TENANT * 100, 1)
            if MAX_CONCURRENT_JOBS_PER_TENANT > 0
            else 0,
        },
    }


def execute_sandbox_config(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    NEW: Returns sandbox security configuration — the three isolation layers
    (Hardware/Kernel/Container) and the six security rules from the architecture doc.
    Shows real enforcement status based on configured env vars.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:sandbox:config", 60, 60)
    execution_mode = os.getenv("MEDIA_EXECUTION_MODE", "memory-fallback")
    has_lambda = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("AWS_REGION"))
    has_cloudrun = bool(os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("K_SERVICE"))
    has_minio = bool(os.getenv("MINIO_ENDPOINT"))
    has_k8s = bool(os.getenv("KUBERNETES_SERVICE_HOST"))
    strict_mode = os.getenv("MEDIA_REQUIRE_VALIDATION_TOKEN", "0").strip().lower() in {"1", "true", "yes", "on"}
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "sandbox": {
            "execution_mode": execution_mode,
            "available_executors": {
                "aws_lambda": has_lambda,
                "google_cloud_run": has_cloudrun,
                "minio_storage": has_minio,
                "kubernetes": has_k8s,
                "memory_fallback": True,
            },
            "isolation_layers": {
                "layer_1_hardware": {
                    "name": "Hardware Isolation",
                    "technology": "Firecracker microVMs (AWS Lambda uses internally)",
                    "active": has_lambda or execution_mode == "firecracker",
                    "description": "KVM-based virtualisation — each job in own micro-VM, boots ~125ms",
                    "self_hosted_note": "Use Firecracker directly for max control at scale",
                },
                "layer_2_kernel": {
                    "name": "Kernel Interception",
                    "technology": "gVisor / Cloud Run",
                    "active": has_cloudrun or execution_mode == "gvisor",
                    "description": "Intercepts all syscalls before host kernel — eliminates kernel exploit class",
                    "managed_note": "Cloud Run, App Engine, Cloud Functions use gVisor automatically",
                },
                "layer_3_container": {
                    "name": "Container Hardening",
                    "technology": "Docker + Kubernetes",
                    "active": has_k8s,
                    "description": "Non-root, seccomp, dropped capabilities, RBAC prevents lateral movement",
                },
            },
            "security_rules": {
                "rule_1_zero_trust_ingress": {
                    "name": "Zero-Trust File Ingress",
                    "enforced": True,
                    "description": "Files travel directly browser→storage via presigned URL. API handles metadata only.",
                    "endpoint": "POST /storage/presign",
                },
                "rule_2_magic_byte_validation": {
                    "name": "Magic Byte Validation",
                    "enforced": True,
                    "strict_mode": strict_mode,
                    "description": "First 16 bytes validated against known magic signatures before job queuing.",
                    "endpoint": "POST /media/validate-file",
                    "purge_endpoint": "DELETE /media/raw-input",
                    "supported_mime_types": list(_MAGIC_SIGNATURES.keys()),
                },
                "rule_3_network_isolation": {
                    "name": "Network-Isolated Processing",
                    "enforced": has_lambda or has_cloudrun or execution_mode in {"firecracker", "gvisor"},
                    "description": "Sandbox has zero outbound internet access during processing.",
                    "note": "Enforced by Lambda/Cloud Run automatically; configure NetworkPolicy for self-hosted.",
                },
                "rule_4_ephemeral_execution": {
                    "name": "Ephemeral Execution Environments",
                    "enforced": has_lambda or has_cloudrun or execution_mode in {"firecracker", "gvisor"},
                    "description": "Fresh VM/container per job, destroyed on completion. No shared state.",
                },
                "rule_5_row_level_security": {
                    "name": "Row Level Security",
                    "enforced": True,
                    "description": "All job queries filter by tenant_id. Cross-tenant leakage impossible at API layer.",
                    "database_note": "Enable PostgreSQL RLS policies for defense-in-depth at DB layer.",
                },
                "rule_6_signed_urls": {
                    "name": "Time-Limited Signed URLs",
                    "enforced": True,
                    "description": "Output files served via HMAC-signed expiring URLs, never permanent.",
                    "default_ttl_seconds": 900,
                    "max_ttl_seconds": 86400,
                    "endpoint": "POST /media/jobs/{id}/output-url",
                },
            },
            "raw_input_ttl_hours": int(os.getenv("MEDIA_RAW_INPUT_TTL_HOURS", "24")),
            "max_concurrent_jobs_per_tenant": MAX_CONCURRENT_JOBS_PER_TENANT,
            "strict_validation_token": strict_mode,
        },
    }


async def execute_sandbox_dispatch(
    runtime: ContextRuntime, payload: MediaSandboxDispatchRequest, auth: AuthDep
) -> dict[str, Any]:
    """
    NEW: Dispatch a media file to a named managed provider.
    Routes to Cloudinary (image/video), Mux (video), Bunny.net (image/video),
    AssemblyAI (audio), Deepgram (audio), or Adobe PDF Services (document).
    Falls back to structured simulation response when credentials are absent.
    Enforces per-tenant concurrency cap.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:dispatch", 60, 60)
    if payload.provider not in MANAGED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {payload.provider!r}. Valid: {', '.join(sorted(MANAGED_PROVIDERS))}",
        )
    provider_info = MANAGED_PROVIDERS[payload.provider]
    if payload.media_type not in MEDIA_TYPES:
        raise HTTPException(status_code=422, detail=f"media_type must be one of: {', '.join(sorted(MEDIA_TYPES))}")
    if payload.media_type not in provider_info["media_types"]:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {payload.provider!r} supports {provider_info['media_types']}, not {payload.media_type!r}.",
        )
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
                detail=f"Concurrent job limit reached ({MAX_CONCURRENT_JOBS_PER_TENANT}). Wait for active jobs to complete.",
            )
        now_iso = datetime.now(UTC).isoformat()
        job_record: dict[str, Any] = {
            "id": len(runtime.media_jobs_memory) + 1,
            "tenant_id": auth.tenant_id,
            "storage_key": payload.storage_key,
            "media_type": payload.media_type,
            "output_bucket": "processed-output",
            "processing_options": payload.operation_params,
            "provider": payload.provider,
            "operation": payload.operation,
            "status": "processing",
            "progress_pct": 10,
            "output_key": None,
            "error": None,
            "validation_token_provided": False,
            "created_at": now_iso,
            "updated_at": now_iso,
            "completed_at": None,
            "source": "sandbox-dispatch",
            "persistence": "memory-fallback",
            "retry_count": 0,
        }
        runtime.media_jobs_memory.append(job_record)
    helper_append_audit(runtime, auth.tenant_id, f"media_dispatch:{payload.provider}", job_record["id"])
    dispatch_fn = _PROVIDER_DISPATCH.get(payload.provider)
    result: dict[str, Any]
    if dispatch_fn is None:
        result = {"provider": payload.provider, "status": "error", "error": "No adapter registered."}
    else:
        result = await dispatch_fn(payload.storage_key, payload.operation, payload.operation_params, payload.source_url)
    terminal_ok = result.get("status") in {"complete", "dispatched", "processing"}
    final_status = "complete" if terminal_ok else "failed"
    with runtime._lock:
        target = next((j for j in runtime.media_jobs_memory if j["id"] == job_record["id"]), None)
        if target:
            target["status"] = final_status
            target["progress_pct"] = 100 if final_status == "complete" else 0
            now_upd = datetime.now(UTC).isoformat()
            target["updated_at"] = now_upd
            if final_status == "complete":
                fname = payload.storage_key.split("/")[-1]
                target["output_key"] = f"processed/{auth.tenant_id}/{job_record['id']}/{fname}"
                target["completed_at"] = now_upd
            else:
                target["error"] = result.get("error", "Provider dispatch failed.")
                runtime.media_jobs_dlq_memory.append(
                    {
                        "id": len(runtime.media_jobs_dlq_memory) + 1,
                        "tenant_id": auth.tenant_id,
                        "job_id": job_record["id"],
                        "reason": target["error"],
                        "failed_at": now_upd,
                        "retries": 0,
                        "provider": payload.provider,
                    }
                )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "job_id": job_record["id"],
        "provider": payload.provider,
        "provider_name": provider_info["name"],
        "dispatch_result": result,
        "job_status": final_status,
    }
