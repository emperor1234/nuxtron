"""Intelligence/Platform HTTP adapters beginning with recovery status."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.get_job import execute_get_job
from ..operations.get_job import execute_platform_intelligence
from ..operations.get_job import execute_policy_status
from ..operations.get_job import execute_sla_report
from ..operations.log import execute_clear_recovery_item
from ..operations.log import execute_list_jobs
from ..operations.log import execute_recovery_status
from ..operations.log import execute_trigger_retry
from ..runtime import ContextRuntime
from ..schemas import RetryRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/recovery/status", summary="Module 36 — view error recovery queue")
    def recovery_status(auth: AuthDep, limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
        return execute_recovery_status(runtime, auth, limit)

    @router.post("/recovery/retry", summary="Module 36 — trigger manual retry for a failed item")
    def trigger_retry(req: RetryRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_trigger_retry(runtime, req, auth)

    @router.delete("/recovery/queue/{job_id}", summary="Module 36 — remove a job from the recovery queue")
    def clear_recovery_item(job_id: str, auth: AuthDep) -> dict[str, Any]:
        return execute_clear_recovery_item(runtime, job_id, auth)

    @router.get("/jobs", summary="Module 37 — list all async SEO jobs for this tenant")
    def list_jobs(
        auth: AuthDep,
        status: str | None = Query(default=None, description="Filter: queued | running | completed | failed"),
        module: str | None = Query(default=None, description="Filter by module name"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        return execute_list_jobs(runtime, auth, status, module, limit)

    @router.get("/jobs/{job_id}", summary="Module 37 — get a specific async job by ID")
    def get_job(job_id: str, auth: AuthDep) -> dict[str, Any]:
        return execute_get_job(runtime, job_id, auth)

    @router.get("/policy/status", summary="Module 39 — secrets and policy enforcement status")
    def policy_status(auth: AuthDep) -> dict[str, Any]:
        return execute_policy_status(runtime, auth)

    @router.get("/sla", summary="Module 49 — SLA compliance and uptime report")
    def sla_report(auth: AuthDep) -> dict[str, Any]:
        return execute_sla_report(runtime, auth)

    @router.get("/intelligence", summary="Module 50 — cross-module platform intelligence & recommendations")
    def platform_intelligence(auth: AuthDep) -> dict[str, Any]:
        return execute_platform_intelligence(runtime, auth)
