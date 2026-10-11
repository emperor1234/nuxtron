"""Seo/Platform HTTP adapters beginning with vso optimize."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.ai_article_writer import execute_daeo_analyze
from ..operations.ai_article_writer import execute_eeat_score
from ..operations.ai_article_writer import execute_entity_analyze
from ..operations.ai_article_writer import execute_gxo_optimize
from ..operations.ai_article_writer import execute_msvo_analyze
from ..operations.ai_article_writer import execute_peao_analyze
from ..operations.ai_article_writer import execute_sxo_analyze
from ..operations.ai_article_writer import execute_vso_optimize
from ..runtime import ContextRuntime
from ..schemas import DaeoReq
from ..schemas import EEATReq
from ..schemas import EntityReq
from ..schemas import GXOReq
from ..schemas import MsvoReq
from ..schemas import PeaoReq
from ..schemas import SXOReq
from ..schemas import VSOReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/vso/optimize")
    async def vso_optimize(req: VSOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_vso_optimize(runtime, req, auth)

    @router.post("/sxo/analyze")
    async def sxo_analyze(req: SXOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_sxo_analyze(runtime, req, auth)

    @router.post("/gxo/optimize")
    async def gxo_optimize(req: GXOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_gxo_optimize(runtime, req, auth)

    @router.post("/eeat/score")
    async def eeat_score(req: EEATReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_eeat_score(runtime, req, auth)

    @router.post("/entity/analyze")
    async def entity_analyze(req: EntityReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_entity_analyze(runtime, req, auth)

    @router.post("/peao/analyze")
    async def peao_analyze(req: PeaoReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_peao_analyze(runtime, req, auth)

    @router.post("/msvo/analyze")
    async def msvo_analyze(req: MsvoReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_msvo_analyze(runtime, req, auth)

    @router.post("/daeo/analyze")
    async def daeo_analyze(req: DaeoReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_daeo_analyze(runtime, req, auth)
