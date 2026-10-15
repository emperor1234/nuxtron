"""Seo/Platform use cases: performance report shared."""

import uuid
from datetime import UTC, datetime
from functools import partial
from typing import Annotated

from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_agent_service import analyze_agent_plan
from .....domains.seo.services.seo_internal_linking_service import suggest_internal_linking
from .....domains.seo.services.seo_landing_service import generate_landing_page
from .....domains.seo.services.seo_performance_service import raise_performance_unavailable
from ..constants import _AGENT_SYS, _INTERNAL_LINKING_SYS, _LANDING_SYS
from ..runtime import ContextRuntime
from ..schemas import (
    AccessibilityAuditReq,
    AgentRunReq,
    InternalLinkingReq,
    LandingPageGenerateReq,
    MediaSeoAuditReq,
    PerformanceCompareReq,
    SecuritySeoAuditReq,
    SocialSeoAuditReq,
)
from ..services import extract_waterfall as provider_ollama_json
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_find_cached_analysis, helper_log

_ACCESSIBILITY_AUDIT_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "A verified rendered-page accessibility scanner is not configured. Compliance scores and findings are disabled until page evidence can be inspected.",
}

_MEDIA_SEO_AUDIT_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "A verified media crawler is not configured. Image counts, compression estimates, and page media findings are disabled until the submitted site can be inspected for real assets.",
}

_SECURITY_SEO_AUDIT_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "A verified security scanner is not configured. Security scores, header checks, cloaking or spam findings, and redirect claims are disabled until the target response and page content can be inspected. Use the local header review for pasted evidence.",
}

_SOCIAL_SEO_AUDIT_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "A page metadata fetcher and platform rendering validators are not configured. Social SEO scores, metadata findings, and distribution opportunities are disabled until the submitted page can be inspected. Use the local Social Share Preview for user-entered metadata.",
}


async def execute_performance_report_shared(
    runtime: ContextRuntime, share_token: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_reports_compare(
    runtime: ContextRuntime, req: PerformanceCompareReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_history(
    runtime: ContextRuntime, url: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_crux_history(
    runtime: ContextRuntime, url: str, auth: Annotated[AuthContext, Depends(require_auth)], months: int = 6
):
    raise_performance_unavailable()


async def execute_agent_run(
    runtime: ContextRuntime, req: AgentRunReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Create an autonomous SEO strategy plan for a goal."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:agent", limit=5, window_seconds=60)
    plan_id = str(uuid.uuid4())
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "agent", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "agent_run",
            {
                "goal": req.goal,
                "plan_id": cached.get("result", {}).get("plan_id"),
                "cached": True,
                "analysis_id": cached["id"],
            },
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_agent_plan(
        goal=req.goal,
        domain=req.domain,
        plan_id=plan_id,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_AGENT_SYS,
        clean_text_fn=_clean,
    )
    result["plan_id"] = plan_id
    result["domain"] = req.domain
    result["created_at"] = datetime.now(UTC).isoformat()
    result["status"] = "planned"
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "agent", payload, result
    )
    helper_log(runtime, auth.tenant_id, "agent_run", {"goal": req.goal, "plan_id": plan_id, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_accessibility_audit(
    runtime: ContextRuntime, req: AccessibilityAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not claim WCAG results without a rendered DOM and scanner evidence."""
    raise HTTPException(status_code=501, detail=_ACCESSIBILITY_AUDIT_UNAVAILABLE)


async def execute_media_seo_audit(
    runtime: ContextRuntime, req: MediaSeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not return invented media metrics without inspected page assets."""
    raise HTTPException(status_code=501, detail=_MEDIA_SEO_AUDIT_UNAVAILABLE)


async def execute_social_seo_audit(
    runtime: ContextRuntime, req: SocialSeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not claim inspected metadata or distribution outcomes without source evidence."""
    raise HTTPException(status_code=501, detail=_SOCIAL_SEO_AUDIT_UNAVAILABLE)


async def execute_landing_page_generate(
    runtime: ContextRuntime, req: LandingPageGenerateReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Generate a conversion-ready landing page structure with schema markup and A/B hooks."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:landing", limit=5, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "landing", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "landing_page_generate",
            {"product": req.product_name, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await generate_landing_page(
        product_name=req.product_name,
        target_keyword=req.target_keyword,
        audience=req.audience,
        schema_types=req.schema_types,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_LANDING_SYS,
        clean_text_fn=_clean,
    )
    result["product_name"] = req.product_name
    result["target_keyword"] = req.target_keyword
    result["generated_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "landing", payload, result
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "landing_page_generate",
        {"product": req.product_name, "keyword": req.target_keyword, "cached": False},
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_security_seo_audit(
    runtime: ContextRuntime, req: SecuritySeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not return a score without a real scanner and inspected response evidence."""
    raise HTTPException(status_code=501, detail=_SECURITY_SEO_AUDIT_UNAVAILABLE)


async def execute_internal_linking_suggest(
    runtime: ContextRuntime, req: InternalLinkingReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Generate semantic internal-link suggestions with anchor guidance and placement hints."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:internal_linking", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "internal_linking", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "internal_linking_suggest",
            {"page_url": req.page_url, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await suggest_internal_linking(
        page_url=req.page_url,
        page_content=req.page_content,
        target_urls=req.target_urls,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_INTERNAL_LINKING_SYS,
        clean_text_fn=_clean,
    )
    result["page_url"] = req.page_url
    result["generated_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "internal_linking", payload, result
    )
    helper_log(runtime, auth.tenant_id, "internal_linking_suggest", {"page_url": req.page_url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}
