"""Seo/Platform HTTP adapters beginning with backlink intelligence analyze."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.review_reputation_analyze import execute_backlink_intelligence_analyze
from ..operations.review_reputation_analyze import execute_content_creation_blogging_plan
from ..operations.review_reputation_analyze import execute_get_analysis
from ..operations.review_reputation_analyze import execute_list_analyses
from ..operations.review_reputation_analyze import execute_rank_tracking_analyze
from ..runtime import ContextRuntime
from ..schemas import BacklinkIntelligenceReq
from ..schemas import ContentCreationBloggingReq
from ..schemas import RankTrackingReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/backlink-intelligence/analyze")
    async def backlink_intelligence_analyze(
        req: BacklinkIntelligenceReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_backlink_intelligence_analyze(runtime, req, auth)

    @router.post("/rank-tracking/analyze")
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
