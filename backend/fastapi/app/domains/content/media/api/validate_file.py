"""Content/Media HTTP adapters beginning with validate file."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import JOB_NOT_CANCELLABLE
from ..constants import JOB_NOT_FOUND
from ..constants import JOB_NOT_RETRYABLE
from ..operations.append_audit import execute_cancel_media_job
from ..operations.append_audit import execute_create_media_job
from ..operations.append_audit import execute_get_media_job
from ..operations.append_audit import execute_get_output_signed_url
from ..operations.append_audit import execute_list_dlq
from ..operations.append_audit import execute_list_media_jobs
from ..operations.append_audit import execute_retry_media_job
from ..operations.append_audit import execute_validate_file
from ..runtime import ContextRuntime
from ..schemas import MediaJobCreateRequest
from ..schemas import MediaOutputUrlRequest
from ..schemas import MediaValidateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post(
        "/media/validate-file", responses={422: {"description": "Invalid base64 or magic-byte validation failure."}}
    )
    def validate_file(payload: MediaValidateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_validate_file(runtime, payload, auth)

    @router.post(
        "/media/jobs",
        responses={
            422: {"description": "Invalid media_type or missing validation_token in strict mode."},
            429: {"description": "Per-tenant concurrency limit reached."},
        },
    )
    def create_media_job(payload: MediaJobCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_media_job(runtime, payload, auth)

    @router.get("/media/jobs")
    def list_media_jobs(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=16)] = None,
        media_type: Annotated[str | None, Query(max_length=16)] = None,
    ) -> dict[str, Any]:
        return execute_list_media_jobs(runtime, auth, status, media_type)

    @router.get("/media/jobs/{job_id:int}", responses={404: {"description": JOB_NOT_FOUND}})
    def get_media_job(job_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_get_media_job(runtime, job_id, auth)

    @router.delete(
        "/media/jobs/{job_id:int}",
        responses={404: {"description": JOB_NOT_FOUND}, 409: {"description": JOB_NOT_CANCELLABLE}},
    )
    def cancel_media_job(job_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_cancel_media_job(runtime, job_id, auth)

    @router.post(
        "/media/jobs/{job_id:int}/retry",
        responses={404: {"description": JOB_NOT_FOUND}, 409: {"description": JOB_NOT_RETRYABLE}},
    )
    def retry_media_job(job_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_retry_media_job(runtime, job_id, auth)

    @router.post(
        "/media/jobs/{job_id:int}/output-url",
        responses={
            404: {"description": JOB_NOT_FOUND},
            409: {"description": "Output URL only available for completed jobs."},
        },
    )
    def get_output_signed_url(job_id: int, payload: MediaOutputUrlRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_get_output_signed_url(runtime, job_id, payload, auth)

    @router.get("/media/jobs/dlq")
    def list_dlq(auth: AuthDep) -> dict[str, Any]:
        return execute_list_dlq(runtime, auth)
