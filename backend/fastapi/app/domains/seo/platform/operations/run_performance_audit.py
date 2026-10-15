"""Fail-closed operations for unsupported performance reports and auto-fixes."""

from typing import Annotated

from fastapi import Depends

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_performance_service import raise_performance_unavailable
from ..runtime import ContextRuntime
from ..schemas import PerformanceAutoFixReq, PerformanceReportShareReq


async def execute_performance_report_share(
    _runtime: ContextRuntime,
    _analysis_id: str,
    _req: PerformanceReportShareReq,
    _auth: Annotated[AuthContext, Depends(require_auth)],
) -> None:
    raise_performance_unavailable()


async def execute_performance_auto_fix(
    _runtime: ContextRuntime,
    _req: PerformanceAutoFixReq,
    _auth: Annotated[AuthContext, Depends(require_auth)],
) -> None:
    raise_performance_unavailable()
