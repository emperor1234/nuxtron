"""Content/Media use cases for validation, durable job gates, and provider inventory."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any
import base64
import os

from ..constants import AuthDep
from ..constants import MANAGED_PROVIDERS
from ..runtime import ContextRuntime
from ..runtime import require_durable_media_jobs
from ..schemas import MediaJobCreateRequest
from ..schemas import MediaOutputUrlRequest
from ..schemas import MediaValidateRequest
from ..services.processing import _issue_validation_token
from ..services.processing import _validate_magic_bytes


def helper_append_audit(runtime: ContextRuntime, tenant_id: str, action: str, job_id: int | None = None) -> None:
    """Append a process-local development record for non-job validation actions."""
    with runtime._lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "job_id": job_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "media-validation",
            }
        )


def execute_validate_file(runtime: ContextRuntime, payload: MediaValidateRequest, auth: AuthDep) -> dict[str, Any]:
    """Validate supplied file magic bytes and issue an object-bound validation token."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:validate", 300, 60)
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
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "mime_type": payload.expected_mime,
        "validation_token": token,
    }


def execute_create_media_job(runtime: ContextRuntime, payload: MediaJobCreateRequest, auth: AuthDep) -> dict[str, Any]:
    require_durable_media_jobs()


def execute_list_media_jobs(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=16)] = None,
    media_type: Annotated[str | None, Query(max_length=16)] = None,
) -> dict[str, Any]:
    require_durable_media_jobs()


def execute_get_media_job(runtime: ContextRuntime, job_id: int, auth: AuthDep) -> dict[str, Any]:
    require_durable_media_jobs()


def execute_cancel_media_job(runtime: ContextRuntime, job_id: int, auth: AuthDep) -> dict[str, Any]:
    require_durable_media_jobs()


def execute_retry_media_job(runtime: ContextRuntime, job_id: int, auth: AuthDep) -> dict[str, Any]:
    require_durable_media_jobs()


def execute_get_output_signed_url(
    runtime: ContextRuntime, job_id: int, payload: MediaOutputUrlRequest, auth: AuthDep
) -> dict[str, Any]:
    require_durable_media_jobs()


def execute_list_dlq(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    require_durable_media_jobs()


def execute_list_providers(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Report configured credentials separately from the currently unavailable processing capability."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:providers", 60, 60)
    providers_out = []
    for key, info in MANAGED_PROVIDERS.items():
        missing_env_vars = [ev for ev in info["env_vars"] if not os.getenv(ev, "").strip()]
        configured = not missing_env_vars
        providers_out.append(
            {
                "id": key,
                **info,
                "configured": configured,
                "available": False,
                "status": "credentials-configured-but-unavailable"
                if configured
                else "credentials-required-and-unavailable",
                "missing_env_vars": missing_env_vars,
                "availability_reason": "Durable tenant-scoped jobs, worker dispatch, and provider completion tracking are not configured.",
            }
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "providers": providers_out,
        "total": len(providers_out),
        "configured_count": sum(1 for provider in providers_out if provider["configured"]),
        "available_count": 0,
        "note": "Configured credentials do not enable media processing; job APIs return 501 until durable storage and workers are implemented.",
    }
