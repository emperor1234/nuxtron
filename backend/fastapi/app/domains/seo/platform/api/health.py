"""Seo/Platform HTTP adapters beginning with health."""

from typing import Annotated

from fastapi import APIRouter, Depends

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_keyword_research_service import KEYWORD_RESEARCH_UNAVAILABLE_DETAIL
from ..operations.ahrefs_parity import (
    execute_ahrefs_parity,
    execute_get_module_detail,
    execute_keyword_research,
    execute_keyword_research_async,
    execute_seo_ai_core_analyze,
)
from ..operations.save_analysis import execute_audit_modules, execute_health, execute_list_modules
from ..runtime import ContextRuntime
from ..schemas import KeywordResearchReq, SeoAiCoreReq

_KEYWORD_RESEARCH_501_RESPONSE = {
    "description": "Verified keyword research providers are not connected.",
    "content": {"application/json": {"example": {"detail": KEYWORD_RESEARCH_UNAVAILABLE_DETAIL}}},
}


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/health")
    async def health():
        return await execute_health(runtime)

    @router.get("/modules")
    async def list_modules(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_list_modules(runtime, auth)

    @router.get("/modules/audit")
    async def audit_modules(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_audit_modules(runtime, auth)

    @router.get("/ahrefs/parity")
    async def ahrefs_parity(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_ahrefs_parity(auth)

    @router.get("/modules/{module_key}")
    async def get_module_detail(module_key: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_get_module_detail(runtime, module_key, auth)

    @router.post("/seo-ai/analyze")
    async def seo_ai_core_analyze(req: SeoAiCoreReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_seo_ai_core_analyze(runtime, req, auth)

    @router.post("/keywords/research", status_code=501, response_model=None, responses={501: _KEYWORD_RESEARCH_501_RESPONSE})
    async def keyword_research(req: KeywordResearchReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_keyword_research(runtime, req, auth)

    @router.post("/keywords/research/async", status_code=501, response_model=None, responses={501: _KEYWORD_RESEARCH_501_RESPONSE})
    async def keyword_research_async(req: KeywordResearchReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_keyword_research_async(runtime, req, auth)
