"""Seo/Platform HTTP adapters beginning with agency platform analyze."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.review_reputation_analyze import execute_brand_voice_rewrite
from ..operations.review_reputation_analyze import execute_planner_execute
from ..operations.review_reputation_analyze import execute_planner_execute_all_modules
from ..operations.review_reputation_analyze import execute_review_reputation_analyze
from ..operations.ux_conversion_audit import execute_agency_platform_analyze
from ..operations.ux_conversion_audit import execute_integrations_automation_analyze
from ..operations.ux_conversion_audit import execute_log_file_analyze
from ..operations.ux_conversion_audit import execute_topical_map_build
from ..runtime import ContextRuntime
from ..schemas import AgencyPlatformReq
from ..schemas import BrandVoiceReq
from ..schemas import IntegrationsAutomationReq
from ..schemas import LogFileAnalysisReq
from ..schemas import PlannerExecuteAllReq
from ..schemas import PlannerExecuteReq
from ..schemas import ReviewReputationReq
from ..schemas import TopicalMapReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/agency-platform/analyze")
    async def agency_platform_analyze(req: AgencyPlatformReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_agency_platform_analyze(runtime, req, auth)

    @router.post("/integrations-automation/analyze")
    async def integrations_automation_analyze(
        req: IntegrationsAutomationReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_integrations_automation_analyze(runtime, req, auth)

    @router.post("/topical-map/build")
    async def topical_map_build(req: TopicalMapReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_topical_map_build(runtime, req, auth)

    @router.post("/log-file/analyze")
    async def log_file_analyze(req: LogFileAnalysisReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_log_file_analyze(runtime, req, auth)

    @router.post("/reviews/analyze")
    async def review_reputation_analyze(req: ReviewReputationReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_review_reputation_analyze(runtime, req, auth)

    @router.post("/brand-voice/rewrite")
    async def brand_voice_rewrite(req: BrandVoiceReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_brand_voice_rewrite(runtime, req, auth)

    @router.post("/planner/execute")
    async def planner_execute(req: PlannerExecuteReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_planner_execute(runtime, req, auth)

    @router.post("/planner/execute-all-modules")
    async def planner_execute_all_modules(
        req: PlannerExecuteAllReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_planner_execute_all_modules(runtime, req, auth)
