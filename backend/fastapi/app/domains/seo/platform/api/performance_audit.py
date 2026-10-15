"""Seo/Platform HTTP adapters beginning with performance audit."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_performance_service import PERFORMANCE_UNAVAILABLE_501_RESPONSE
from ..operations.ecommerce_seo import (
    execute_performance_monitor_create,
    execute_performance_monitor_run,
    execute_performance_monitors,
    execute_performance_rum_ingest,
    execute_performance_tests_create,
    execute_performance_tests_status,
)
from ..operations.local_seo_optimize import execute_performance_audit, execute_performance_rum_summary
from ..runtime import ContextRuntime
from ..schemas import PerformanceAuditReq, PerformanceMonitorCreateReq, PerformanceRumIngestReq


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/performance/audit", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_audit(req: PerformanceAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_audit(runtime, req, auth)

    @router.post("/performance/rum/ingest", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_rum_ingest(req: PerformanceRumIngestReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_rum_ingest(runtime, req, auth)

    @router.get("/performance/rum/summary", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_rum_summary(url: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_rum_summary(runtime, url, auth)

    @router.post("/performance/tests", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_tests_create(
        req: PerformanceAuditReq, background_tasks: BackgroundTasks, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_performance_tests_create(runtime, req, background_tasks, auth)

    @router.get("/performance/tests/{test_id}", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_tests_status(test_id: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_tests_status(runtime, test_id, auth)

    @router.post("/performance/monitor/create", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_monitor_create(
        req: PerformanceMonitorCreateReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_performance_monitor_create(runtime, req, auth)

    @router.get("/performance/monitors", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_monitors(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_monitors(runtime, auth)

    @router.post("/performance/monitors/{monitor_id}/run", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_monitor_run(monitor_id: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_monitor_run(runtime, monitor_id, auth)
