"""Seo/Platform HTTP adapters beginning with backlink intelligence analyze."""

from typing import Annotated

from fastapi import APIRouter, Depends

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_rank_tracking_service import RANK_TRACKING_501_RESPONSE
from ..operations.review_reputation_analyze import (
    execute_backlink_intelligence_analyze,
    execute_content_creation_blogging_plan,
    execute_get_analysis,
    execute_list_analyses,
    execute_rank_tracking_analyze,
)
from ..runtime import ContextRuntime
from ..schemas import BacklinkIntelligenceReq, ContentCreationBloggingReq, RankTrackingReq


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/backlink-intelligence/analyze")
    async def backlink_intelligence_analyze(
        req: BacklinkIntelligenceReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_backlink_intelligence_analyze(runtime, req, auth)

    @router.post(
        "/rank-tracking/analyze",
        status_code=501,
        response_model=None,
        responses={501: RANK_TRACKING_501_RESPONSE},
    )
    async def rank_tracking_analyze(req: RankTrackingReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_rank_tracking_analyze(runtime, req, auth)

    @router.post("/content-creation-blogging/plan")
    async def content_creation_blogging_plan(
        req: ContentCreationBloggingReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_content_creation_blogging_plan(runtime, req, auth)

    @router.get("/analyses")
    async def list_analyses(
        auth: Annotated[AuthContext, Depends(require_auth)], module: str | None = None, limit: int = 50
    ):
        return await execute_list_analyses(runtime, auth, module, limit)

    @router.get("/analyses/{analysis_id}")
    async def get_analysis(analysis_id: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_get_analysis(runtime, analysis_id, auth)
