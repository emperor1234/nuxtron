"""Seo/Platform HTTP adapters beginning with agency platform analyze."""

from typing import Annotated

from fastapi import APIRouter, Depends

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_reviews_service import REVIEW_REPUTATION_501_RESPONSE
from ..operations.review_reputation_analyze import (
    execute_brand_voice_rewrite,
    execute_review_reputation_analyze,
)
from ..operations.ux_conversion_audit import (
    execute_agency_platform_analyze,
    execute_integrations_automation_analyze,
    execute_log_file_analyze,
    execute_topical_map_build,
)
from ..runtime import ContextRuntime
from ..schemas import (
    AgencyPlatformReq,
    BrandVoiceReq,
    IntegrationsAutomationReq,
    LogFileAnalysisReq,
    ReviewReputationReq,
    TopicalMapReq,
)


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post(
        "/agency-platform/analyze",
        responses={501: {"description": "Verified workspace inventory and governance evidence are not connected."}},
    )
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

    @router.post("/reviews/analyze", status_code=501, response_model=None, responses={501: REVIEW_REPUTATION_501_RESPONSE})
    async def review_reputation_analyze(req: ReviewReputationReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_review_reputation_analyze(runtime, req, auth)

    @router.post("/brand-voice/rewrite")
    async def brand_voice_rewrite(req: BrandVoiceReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_brand_voice_rewrite(runtime, req, auth)
