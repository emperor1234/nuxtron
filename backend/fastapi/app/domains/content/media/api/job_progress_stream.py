"""Content/Media HTTP adapters beginning with job progress stream."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import JOB_NOT_FOUND
from ..operations.append_audit import execute_list_providers
from ..operations.job_progress_stream import execute_job_progress_stream
from ..operations.job_progress_stream import execute_media_jobs_stats
from ..operations.job_progress_stream import execute_sandbox_config
from ..operations.job_progress_stream import execute_sandbox_dispatch
from ..operations.purge_raw_input import execute_job_audit_trail
from ..operations.purge_raw_input import execute_purge_raw_input
from ..runtime import ContextRuntime
from ..schemas import MediaSandboxDispatchRequest
from fastapi import APIRouter
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/media/jobs/{job_id:int}/stream", responses={404: {"description": JOB_NOT_FOUND}})
    async def job_progress_stream(
        request: Request,
        job_id: int,
        api_key: Annotated[str | None, Query(alias="api_key")] = None,
        tenant_id_param: Annotated[str | None, Query(alias="tenant_id")] = None,
    ) -> StreamingResponse:
        return await execute_job_progress_stream(runtime, request, job_id, api_key, tenant_id_param)

    @router.get("/media/jobs/stats")
    def media_jobs_stats(auth: AuthDep) -> dict[str, Any]:
        return execute_media_jobs_stats(runtime, auth)

    @router.get("/media/sandbox/config")
    def sandbox_config(auth: AuthDep) -> dict[str, Any]:
        return execute_sandbox_config(runtime, auth)

    @router.get("/media/providers")
    def list_providers(auth: AuthDep) -> dict[str, Any]:
        return execute_list_providers(runtime, auth)

    @router.post(
        "/media/sandbox/dispatch",
        responses={
            400: {"description": "Unknown provider or media type mismatch."},
            422: {"description": "Invalid media_type."},
            429: {"description": "Per-tenant concurrency limit reached."},
        },
    )
    async def sandbox_dispatch(payload: MediaSandboxDispatchRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_sandbox_dispatch(runtime, payload, auth)

    @router.delete(
        "/media/raw-input", responses={403: {"description": "Storage key does not belong to the authenticated tenant."}}
    )
    def purge_raw_input(
        storage_key: Annotated[str, Query(min_length=1, max_length=1024)], auth: AuthDep
    ) -> dict[str, Any]:
        return execute_purge_raw_input(runtime, storage_key, auth)

    @router.get("/media/jobs/{job_id:int}/audit", responses={404: {"description": JOB_NOT_FOUND}})
    def job_audit_trail(job_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_job_audit_trail(runtime, job_id, auth)
