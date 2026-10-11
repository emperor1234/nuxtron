"""Seo/Platform HTTP adapters beginning with performance alert events."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.ecommerce_seo import execute_performance_alert_events
from ..operations.ecommerce_seo import execute_performance_report
from ..operations.performance_report_shared import execute_performance_crux_history
from ..operations.performance_report_shared import execute_performance_history
from ..operations.performance_report_shared import execute_performance_report_shared
from ..operations.performance_report_shared import execute_performance_reports_compare
from ..operations.run_performance_audit import execute_performance_auto_fix
from ..operations.run_performance_audit import execute_performance_report_share
from ..runtime import ContextRuntime
from ..schemas import PerformanceAutoFixReq
from ..schemas import PerformanceCompareReq
from ..schemas import PerformanceReportShareReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/performance/alerts/events")
    async def performance_alert_events(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_alert_events(runtime, auth)

    @router.get("/performance/report/{analysis_id}")
    async def performance_report(analysis_id: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_report(runtime, analysis_id, auth)

    @router.post("/performance/report/{analysis_id}/share")
    async def performance_report_share(
        analysis_id: str, req: PerformanceReportShareReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_performance_report_share(runtime, analysis_id, req, auth)

    @router.get("/performance/report/shared/{share_token}")
    async def performance_report_shared(share_token: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_report_shared(runtime, share_token, auth)

    @router.post("/performance/reports/compare")
    async def performance_reports_compare(
        req: PerformanceCompareReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_performance_reports_compare(runtime, req, auth)

    @router.post("/performance/auto-fix")
    async def performance_auto_fix(req: PerformanceAutoFixReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_auto_fix(runtime, req, auth)

    @router.get("/performance/history")
    async def performance_history(url: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_history(runtime, url, auth)

    @router.get("/performance/crux/history")
    async def performance_crux_history(url: str, auth: Annotated[AuthContext, Depends(require_auth)], months: int = 6):
        return await execute_performance_crux_history(runtime, url, auth, months)
