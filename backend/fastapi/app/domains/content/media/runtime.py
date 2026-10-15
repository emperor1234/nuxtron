"""Content/Media runtime dependencies and explicit capability gates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import NoReturn

from fastapi import HTTPException
from pydantic import BaseModel


class MediaJobsUnavailableDetail(BaseModel):
    code: Literal["NOT_IMPLEMENTED"]
    message: str


class MediaJobsUnavailableResponse(BaseModel):
    detail: MediaJobsUnavailableDetail


MEDIA_JOBS_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": "Media job processing is disabled until durable tenant-scoped storage, worker dispatch, and provider completion tracking are configured.",
}
MEDIA_JOBS_UNAVAILABLE_RESPONSE = {
    501: {
        "model": MediaJobsUnavailableResponse,
        "description": "Durable tenant-scoped media jobs and worker processing are not configured.",
    }
}


def require_durable_media_jobs() -> NoReturn:
    """Fail closed in every environment until a durable media-job adapter is installed."""
    raise HTTPException(status_code=501, detail=MEDIA_JOBS_UNAVAILABLE_DETAIL)


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _lock: Any
    _subscribers: dict[str, list[dict[str, Any]]]
    audit_log_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    media_jobs_dlq_memory: list[dict[str, Any]]
    media_jobs_memory: list[dict[str, Any]]
