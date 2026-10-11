"""Content/Media HTTP composition and legacy import exports."""

from __future__ import annotations
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    validate_file,
    job_progress_stream,
)
from .services.processing import _sse_message as _sse_message
from .services.processing import _detect_magic_mime as _detect_magic_mime
from .services.processing import _validate_magic_bytes as _validate_magic_bytes
from .services.processing import _issue_validation_token as _issue_validation_token
from .services.processing import _build_job_record as _build_job_record
from .services.processing import _dispatch_cloudinary as _dispatch_cloudinary
from .services.processing import _dispatch_mux as _dispatch_mux
from .services.processing import _dispatch_bunny as _dispatch_bunny
from .services.processing import _dispatch_assemblyai as _dispatch_assemblyai
from .services.dispatch_deepgram import _dispatch_deepgram as _dispatch_deepgram
from .services.adobe_pdf import _dispatch_adobe_pdf as _dispatch_adobe_pdf
from .schemas import MediaValidateRequest as MediaValidateRequest
from .schemas import MediaOutputUrlRequest as MediaOutputUrlRequest
from .schemas import MediaSandboxDispatchRequest as MediaSandboxDispatchRequest
from .schemas import MediaJobCreateRequest as MediaJobCreateRequest
from .constants import JSON_CONTENT_TYPE as JSON_CONTENT_TYPE
from .constants import MAX_CONCURRENT_JOBS_PER_TENANT as MAX_CONCURRENT_JOBS_PER_TENANT
from .constants import MANAGED_PROVIDERS as MANAGED_PROVIDERS
from .providers import _PROVIDER_DISPATCH as _PROVIDER_DISPATCH
from .constants import AuthDep as AuthDep
from .constants import ASSEMBLYAI_TRANSCRIPT_API_ENDPOINT as ASSEMBLYAI_TRANSCRIPT_API_ENDPOINT
from .constants import _MAGIC_SIGNATURES as _MAGIC_SIGNATURES
from .constants import JOB_NOT_FOUND as JOB_NOT_FOUND
from .constants import MEDIA_TYPES as MEDIA_TYPES
from .constants import JOB_NOT_CANCELLABLE as JOB_NOT_CANCELLABLE
from .constants import JOB_NOT_RETRYABLE as JOB_NOT_RETRYABLE
from .constants import MUX_ASSET_API_ENDPOINT as MUX_ASSET_API_ENDPOINT
import asyncio
import hashlib
import hmac
import json
import os
import time
from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime
from typing import Annotated
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic import Field
from ....deps import AuthContext
from ....deps import require_auth


def create_media_jobs_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    media_jobs_memory: list[dict[str, Any]],
    media_jobs_dlq_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """
    NEW: Media Job Queue router implementing the Sandboxed Media SaaS
    Architecture pipeline.  All processing is intentionally simulated
    (memory-fallback) so the API layer is complete and correct; swap in
    real BullMQ/SQS dispatchers in the worker layer without changing routes.
    """
    router = APIRouter()
    _lock = threading.Lock()
    _subscribers: dict[str, list[dict[str, Any]]] = {}
    runtime = ContextRuntime(
        _lock=_lock,
        _subscribers=_subscribers,
        audit_log_memory=audit_log_memory,
        enforce_rate_limit=enforce_rate_limit,
        media_jobs_dlq_memory=media_jobs_dlq_memory,
        media_jobs_memory=media_jobs_memory,
    )
    validate_file.register(router, runtime)
    job_progress_stream.register(router, runtime)
    return router
