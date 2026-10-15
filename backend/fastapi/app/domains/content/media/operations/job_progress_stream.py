"""Content/Media use cases for disabled job capabilities and sandbox configuration."""

from __future__ import annotations

from .....deps import require_auth
from ..constants import AuthDep
from ..constants import MANAGED_PROVIDERS
from ..constants import MAX_CONCURRENT_JOBS_PER_TENANT
from ..constants import MEDIA_TYPES
from ..constants import _MAGIC_SIGNATURES
from ..runtime import ContextRuntime
from ..runtime import require_durable_media_jobs
from ..schemas import MediaSandboxDispatchRequest
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from typing import Annotated
from typing import Any
import os


async def execute_job_progress_stream(
    runtime: ContextRuntime,
    request: Request,
    job_id: int,
    api_key: Annotated[str | None, Query(alias="api_key")] = None,
    tenant_id_param: Annotated[str | None, Query(alias="tenant_id")] = None,
) -> StreamingResponse:
    """Require identity, then fail closed until a durable job/event store is installed."""
    await require_auth(request=request, x_api_key=api_key, x_tenant_id=tenant_id_param)
    require_durable_media_jobs()


def execute_media_jobs_stats(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    require_durable_media_jobs()


def execute_sandbox_config(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Report the actual disabled state; this endpoint performs no execution or fallback."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:media:sandbox:config", 60, 60)
    strict_mode = os.getenv("MEDIA_REQUIRE_VALIDATION_TOKEN", "0").strip().lower() in {"1", "true", "yes", "on"}
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "sandbox": {
            "execution_mode": "unavailable",
            "available_executors": {
                "aws_lambda": False,
                "google_cloud_run": False,
                "minio_storage": False,
                "kubernetes": False,
                "memory_fallback": False,
            },
            "isolation_layers": {
                "layer_1_hardware": {
                    "name": "Hardware Isolation",
                    "technology": "Firecracker microVMs",
                    "active": False,
                    "description": "No isolated media execution environment is configured.",
                },
                "layer_2_kernel": {
                    "name": "Kernel Interception",
                    "technology": "gVisor / Cloud Run",
                    "active": False,
                    "description": "No sandbox runtime is configured.",
                },
                "layer_3_container": {
                    "name": "Container Hardening",
                    "technology": "Docker + Kubernetes",
                    "active": False,
                    "description": "No media worker deployment is configured.",
                },
            },
            "security_rules": {
                "rule_1_zero_trust_ingress": {
                    "name": "Zero-Trust File Ingress",
                    "enforced": False,
                    "description": "A complete media upload-to-job pipeline is not configured.",
                    "endpoint": "POST /storage/presign",
                },
                "rule_2_magic_byte_validation": {
                    "name": "Magic Byte Validation",
                    "enforced": True,
                    "strict_mode": strict_mode,
                    "description": "The validation endpoint checks supplied bytes; no media job can start until durable processing is installed.",
                    "endpoint": "POST /media/validate-file",
                    "purge_endpoint": "DELETE /media/raw-input",
                    "supported_mime_types": list(_MAGIC_SIGNATURES.keys()),
                },
                "rule_3_network_isolation": {
                    "name": "Network-Isolated Processing",
                    "enforced": False,
                    "description": "No isolated worker is configured.",
                },
                "rule_4_ephemeral_execution": {
                    "name": "Ephemeral Execution Environments",
                    "enforced": False,
                    "description": "No per-job ephemeral execution environment is configured.",
                },
                "rule_5_row_level_security": {
                    "name": "Row Level Security",
                    "enforced": False,
                    "description": "Media job records have no durable tenant-scoped repository.",
                },
                "rule_6_signed_urls": {
                    "name": "Time-Limited Signed URLs",
                    "enforced": False,
                    "description": "Output URLs are disabled until durable artifacts and job records exist.",
                    "endpoint": "POST /media/jobs/{id}/output-url",
                },
            },
            "job_processing": {
                "available": False,
                "reason": "Durable tenant-scoped persistence, queue dispatch, isolated workers, and provider completion tracking are not configured.",
            },
            "provider_catalog": {
                "providers": sorted(MANAGED_PROVIDERS),
                "available": False,
                "reason": "Provider credentials alone do not enable processing.",
            },
            "raw_input_ttl_hours": int(os.getenv("MEDIA_RAW_INPUT_TTL_HOURS", "24")),
            "max_concurrent_jobs_per_tenant": MAX_CONCURRENT_JOBS_PER_TENANT,
            "strict_validation_token": strict_mode,
        },
    }


async def execute_sandbox_dispatch(
    runtime: ContextRuntime, payload: MediaSandboxDispatchRequest, auth: AuthDep
) -> dict[str, Any]:
    """Validate the declared provider contract, then fail before any external side effect."""
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
    require_durable_media_jobs()
