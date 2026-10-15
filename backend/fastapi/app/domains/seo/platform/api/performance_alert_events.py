"""Seo/Platform HTTP adapters beginning with performance alert events."""

from typing import Annotated

from fastapi import APIRouter, Depends

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_performance_service import PERFORMANCE_UNAVAILABLE_501_RESPONSE
from ..operations.ecommerce_seo import execute_performance_alert_events, execute_performance_report
from ..operations.performance_report_shared import (
    execute_performance_crux_history,
    execute_performance_history,
    execute_performance_report_shared,
    execute_performance_reports_compare,
)
from ..operations.run_performance_audit import execute_performance_auto_fix, execute_performance_report_share
from ..runtime import ContextRuntime
from ..schemas import PerformanceAutoFixReq, PerformanceCompareReq, PerformanceReportShareReq


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/performance/alerts/events", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_alert_events(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_alert_events(runtime, auth)

    @router.get("/performance/report/{analysis_id}", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_report(analysis_id: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_report(runtime, analysis_id, auth)

    @router.post("/performance/report/{analysis_id}/share", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_report_share(
        analysis_id: str, req: PerformanceReportShareReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_performance_report_share(runtime, analysis_id, req, auth)

    @router.get("/performance/report/shared/{share_token}", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_report_shared(share_token: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_report_shared(runtime, share_token, auth)

    @router.post("/performance/reports/compare", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_reports_compare(
        req: PerformanceCompareReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_performance_reports_compare(runtime, req, auth)

    @router.post("/performance/auto-fix", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_auto_fix(req: PerformanceAutoFixReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_auto_fix(runtime, req, auth)

    @router.get("/performance/history", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_history(url: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_history(runtime, url, auth)

    @router.get("/performance/crux/history", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_crux_history(url: str, auth: Annotated[AuthContext, Depends(require_auth)], months: int = 6):
        return await execute_performance_crux_history(runtime, url, auth, months)
