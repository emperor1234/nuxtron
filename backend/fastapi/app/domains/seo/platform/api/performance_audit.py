"""Seo/Platform HTTP adapters beginning with performance audit."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.ecommerce_seo import execute_performance_monitor_create
from ..operations.ecommerce_seo import execute_performance_monitor_run
from ..operations.ecommerce_seo import execute_performance_monitors
from ..operations.ecommerce_seo import execute_performance_rum_ingest
from ..operations.ecommerce_seo import execute_performance_tests_create
from ..operations.ecommerce_seo import execute_performance_tests_status
from ..operations.local_seo_optimize import execute_performance_audit
from ..operations.local_seo_optimize import execute_performance_rum_summary
from ..runtime import ContextRuntime
from ..schemas import PerformanceAuditReq
from ..schemas import PerformanceMonitorCreateReq
from ..schemas import PerformanceRumIngestReq
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/performance/audit")
    async def performance_audit(req: PerformanceAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_audit(runtime, req, auth)

    @router.post("/performance/rum/ingest")
    async def performance_rum_ingest(req: PerformanceRumIngestReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_rum_ingest(runtime, req, auth)

    @router.get("/performance/rum/summary")
    async def performance_rum_summary(url: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_rum_summary(runtime, url, auth)

    @router.post("/performance/tests")
    async def performance_tests_create(
        req: PerformanceAuditReq, background_tasks: BackgroundTasks, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_performance_tests_create(runtime, req, background_tasks, auth)

    @router.get("/performance/tests/{test_id}")
    async def performance_tests_status(test_id: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_tests_status(runtime, test_id, auth)

    @router.post("/performance/monitor/create")
    async def performance_monitor_create(
        req: PerformanceMonitorCreateReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_performance_monitor_create(runtime, req, auth)

    @router.get("/performance/monitors")
    async def performance_monitors(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_monitors(runtime, auth)

    @router.post("/performance/monitors/{monitor_id}/run")
    async def performance_monitor_run(monitor_id: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_monitor_run(runtime, monitor_id, auth)
