"""Seo/Platform HTTP adapters beginning with linkbuilding analyze."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.ahrefs_parity import execute_content_brief
from ..operations.ahrefs_parity import execute_linkbuilding_analyze
from ..operations.ai_article_writer import execute_aeo_optimize
from ..operations.ai_article_writer import execute_ai_article_writer
from ..operations.ai_article_writer import execute_aio_score
from ..operations.ai_article_writer import execute_geo_optimize
from ..operations.ai_article_writer import execute_llmo_analyze
from ..operations.ai_article_writer import execute_sageo_analyze
from ..runtime import ContextRuntime
from ..schemas import AEOReq
from ..schemas import AIOReq
from ..schemas import AIWriterReq
from ..schemas import ContentBriefReq
from ..schemas import GEOReq
from ..schemas import LLMOReq
from ..schemas import LinkBuildingReq
from ..schemas import SageoReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/linkbuilding/analyze")
    async def linkbuilding_analyze(req: LinkBuildingReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_linkbuilding_analyze(runtime, req, auth)

    @router.post("/content/brief")
    async def content_brief(req: ContentBriefReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_content_brief(runtime, req, auth)

    @router.post("/content/write")
    async def ai_article_writer(req: AIWriterReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_ai_article_writer(runtime, req, auth)

    @router.post("/geo/optimize")
    async def geo_optimize(req: GEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_geo_optimize(runtime, req, auth)

    @router.post("/aeo/optimize")
    async def aeo_optimize(req: AEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_aeo_optimize(runtime, req, auth)

    @router.post("/aio/score")
    async def aio_score(req: AIOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_aio_score(runtime, req, auth)

    @router.post("/llmo/analyze")
    async def llmo_analyze(req: LLMOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_llmo_analyze(runtime, req, auth)

    @router.post("/sageo/analyze")
    async def sageo_analyze(req: SageoReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_sageo_analyze(runtime, req, auth)
