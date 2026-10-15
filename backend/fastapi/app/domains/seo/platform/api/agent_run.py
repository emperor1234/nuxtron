"""Seo/Platform HTTP adapters beginning with agent run."""

from typing import Annotated

from fastapi import APIRouter, Depends

from .....deps import AuthContext, require_auth
from ..operations.performance_report_shared import (
    execute_accessibility_audit,
    execute_agent_run,
    execute_landing_page_generate,
    execute_media_seo_audit,
    execute_security_seo_audit,
    execute_social_seo_audit,
)
from ..operations.ux_conversion_audit import execute_rag_search_query, execute_ux_conversion_audit
from ..runtime import ContextRuntime
from ..schemas import (
    AccessibilityAuditReq,
    AgentRunReq,
    LandingPageGenerateReq,
    MediaSeoAuditReq,
    RagSearchReq,
    SecuritySeoAuditReq,
    SocialSeoAuditReq,
    UxConversionReq,
)


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/agent/run")
    async def agent_run(req: AgentRunReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_agent_run(runtime, req, auth)

    @router.post("/accessibility/audit")
    async def accessibility_audit(req: AccessibilityAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_accessibility_audit(runtime, req, auth)

    @router.post("/media/audit")
    async def media_seo_audit(req: MediaSeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_media_seo_audit(runtime, req, auth)

    @router.post("/social/audit")
    async def social_seo_audit(req: SocialSeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_social_seo_audit(runtime, req, auth)

    @router.post("/landing/generate")
    async def landing_page_generate(req: LandingPageGenerateReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_landing_page_generate(runtime, req, auth)

    @router.post("/security/audit")
    async def security_seo_audit(req: SecuritySeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_security_seo_audit(runtime, req, auth)

    @router.post("/ux/audit")
    async def ux_conversion_audit(req: UxConversionReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_ux_conversion_audit(runtime, req, auth)

    @router.post(
        "/rag-search/query",
        responses={501: {"description": "Connected site indexing and source-cited retrieval are not implemented"}},
    )
    async def rag_search_query(req: RagSearchReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_rag_search_query(runtime, req, auth)
