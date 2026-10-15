"""Seo/Platform use cases: ahrefs parity."""

import asyncio
from datetime import UTC, datetime
from functools import partial
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from .....deps import AuthContext, require_auth
from .....domains.seo.seo_module_registry import audit_ahrefs_core_tool_parity
from .....domains.seo.services.seo_ai_service import analyze_seo_ai_core
from .....domains.seo.services.seo_content_brief_service import generate_content_brief
from .....domains.seo.services.seo_keyword_research_service import raise_keyword_research_unavailable
from .....domains.seo.services.seo_linkbuilding_service import analyze_linkbuilding
from .....domains.seo.services.seo_on_page_service import analyze_on_page
from .....domains.seo.services.seo_performance_service import raise_performance_unavailable
from .....domains.seo.services.seo_schema_service import generate_schema_markup
from ..constants import _BRIEF_SYS, _LINKBUILDING_SYS, _ONPAGE_SYS, _SCHEMA_SYS, _SEO_AI_CORE_SYS
from ..runtime import ContextRuntime
from ..schemas import (
    ContentBriefReq,
    KeywordResearchReq,
    LinkBuildingReq,
    OnPageReq,
    PerformanceAuditReq,
    SchemaGenReq,
    SeoAiCoreReq,
    TechnicalAuditReq,
)
from ..services import extract_waterfall as provider_ollama_json
from ..services.get_shared_job_store import _clean
from .save_analysis import (
    helper_get_module,
    helper_job_get,
    helper_job_update,
    helper_run_on_page_job,
    helper_run_schema_job,
    helper_save_analysis,
)
from .sync_job_store import helper_find_cached_analysis, helper_job_create, helper_log

_TECHNICAL_AUDIT_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "A verified crawler is not configured. The current audit does not measure the submitted site, so synthetic results are disabled.",
}


async def execute_ahrefs_parity(auth: Annotated[AuthContext, Depends(require_auth)]):
    """
    Ahrefs core-tool parity audit with vendor transparency.
    This reports mapped tool coverage and distinguishes declared parity from
    implementation availability in this platform.
    """
    audit = audit_ahrefs_core_tool_parity()
    return {"status": "ok", "tenant_id": auth.tenant_id, "audit": audit}


async def execute_get_module_detail(
    runtime: ContextRuntime, module_key: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Return detail for a single SEO module."""
    module = helper_get_module(runtime, module_key)
    if module is None:
        raise HTTPException(status_code=404, detail=f"Unknown SEO module: {module_key}")
    return {"status": "ok", "tenant_id": auth.tenant_id, "module": module}


async def execute_seo_ai_core_analyze(
    runtime: ContextRuntime, req: SeoAiCoreReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Run a core SEO-AI planning pass across keyword, content, and technical priorities."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:seo-ai", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "seo_ai_core", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "seo_ai_core_analyze",
            {"domain": req.domain, "primary_keyword": req.primary_keyword, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_seo_ai_core(
        domain=req.domain,
        primary_keyword=req.primary_keyword,
        business_goal=req.business_goal,
        content_excerpt=req.content_excerpt,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SEO_AI_CORE_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "seo_ai_core", payload, result
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "seo_ai_core_analyze",
        {"domain": req.domain, "primary_keyword": req.primary_keyword, "cached": False},
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_keyword_research(
    runtime: ContextRuntime, req: KeywordResearchReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Reject server-generated keyword metrics until a verified provider is connected."""
    raise_keyword_research_unavailable()


async def execute_keyword_research_async(
    runtime: ContextRuntime, req: KeywordResearchReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not queue synthetic keyword-research jobs."""
    raise_keyword_research_unavailable()


async def execute_on_page_analyze(
    runtime: ContextRuntime, req: OnPageReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """AI-powered on-page SEO analysis and optimization recommendations."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:onpage", limit=20, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "on_page", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "on_page_analyze", {"url": req.url, "analysis_id": cached["id"], "cached": True}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_on_page(
        url=req.url,
        content=req.content,
        focus_keyword=req.focus_keyword,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_ONPAGE_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "on_page", payload, result
    )
    helper_log(
        runtime, auth.tenant_id, "on_page_analyze", {"url": req.url, "analysis_id": analysis_id, "cached": False}
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_on_page_analyze_async(
    runtime: ContextRuntime, req: OnPageReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Queue an on-page SEO analysis job and return immediately with a pollable job id."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:onpage", limit=20, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "on_page", payload)
    if cached is not None:
        job = helper_job_create(runtime, auth.tenant_id, "on_page", payload)
        response = {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
        helper_job_update(
            runtime,
            str(job["job_id"]),
            status="completed",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            result=response,
            error=None,
        )
        helper_log(
            runtime,
            auth.tenant_id,
            "on_page_async",
            {"url": req.url, "analysis_id": cached["id"], "cached": True, "job_id": job["job_id"]},
        )
        return {
            "job_id": job["job_id"],
            "status": "completed",
            "module": "on_page",
            "cached": True,
            "poll_path": f"/seo-platform/jobs/{job['job_id']}",
            "result": response,
        }
    job = helper_job_create(runtime, auth.tenant_id, "on_page", payload)
    job_id = str(job["job_id"])
    asyncio.create_task(helper_run_on_page_job(runtime, job_id, auth.tenant_id, req, payload))
    helper_log(runtime, auth.tenant_id, "on_page_async", {"url": req.url, "job_id": job_id, "cached": False})
    return {
        "job_id": job_id,
        "status": "queued",
        "module": "on_page",
        "cached": False,
        "poll_path": f"/seo-platform/jobs/{job_id}",
    }


async def execute_technical_audit(
    runtime: ContextRuntime, req: TechnicalAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not claim measured technical audit results without an actual crawler."""
    raise HTTPException(status_code=501, detail=_TECHNICAL_AUDIT_UNAVAILABLE)


async def execute_technical_audit_async(
    runtime: ContextRuntime, req: TechnicalAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not queue synthetic technical audit results as if they were measured."""
    raise HTTPException(status_code=501, detail=_TECHNICAL_AUDIT_UNAVAILABLE)


async def execute_get_async_job_status(
    runtime: ContextRuntime, job_id: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Get status/result for a previously queued SEO async job."""
    job = helper_job_get(runtime, job_id, auth.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def execute_generate_schema(
    runtime: ContextRuntime, req: SchemaGenReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Generate valid Schema.org JSON-LD for 18+ schema types."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:schema", limit=30, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "schema", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "schema_generate",
            {"type": req.schema_type, "analysis_id": cached["id"], "cached": True},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await generate_schema_markup(
        schema_type=req.schema_type,
        content=req.content,
        url=req.url,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SCHEMA_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "schema", payload, result
    )
    helper_log(runtime, auth.tenant_id, "schema_generate", {"type": req.schema_type, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_generate_schema_async(
    runtime: ContextRuntime, req: SchemaGenReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Queue a schema generation job and return immediately with a pollable job id."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:schema", limit=30, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "schema", payload)
    if cached is not None:
        job = helper_job_create(runtime, auth.tenant_id, "schema", payload)
        response = {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
        helper_job_update(
            runtime,
            str(job["job_id"]),
            status="completed",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            result=response,
            error=None,
        )
        helper_log(
            runtime,
            auth.tenant_id,
            "schema_async",
            {"type": req.schema_type, "analysis_id": cached["id"], "cached": True, "job_id": job["job_id"]},
        )
        return {
            "job_id": job["job_id"],
            "status": "completed",
            "module": "schema",
            "cached": True,
            "poll_path": f"/seo-platform/jobs/{job['job_id']}",
            "result": response,
        }
    job = helper_job_create(runtime, auth.tenant_id, "schema", payload)
    job_id = str(job["job_id"])
    asyncio.create_task(helper_run_schema_job(runtime, job_id, auth.tenant_id, req, payload))
    helper_log(runtime, auth.tenant_id, "schema_async", {"type": req.schema_type, "job_id": job_id, "cached": False})
    return {
        "job_id": job_id,
        "status": "queued",
        "module": "schema",
        "cached": False,
        "poll_path": f"/seo-platform/jobs/{job_id}",
    }


async def execute_schema_types():
    """List all supported schema types."""
    return {
        "schema_types": [
            "Article",
            "FAQPage",
            "HowTo",
            "Product",
            "LocalBusiness",
            "Organization",
            "Person",
            "VideoObject",
            "Event",
            "Recipe",
            "Review",
            "BreadcrumbList",
            "WebSite",
            "WebPage",
            "SoftwareApplication",
            "Course",
            "JobPosting",
            "NewsArticle",
        ]
    }


async def execute_linkbuilding_analyze(
    runtime: ContextRuntime, req: LinkBuildingReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """AI-powered link building gap analysis and outreach strategy."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:linkbuilding", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "linkbuilding", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "linkbuilding_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    niche = req.niche or (req.target_keywords[0] if req.target_keywords else "")
    result = await analyze_linkbuilding(
        domain=req.domain,
        competitors=req.competitors,
        niche=niche,
        target_keywords=req.target_keywords,
        opportunity_types=req.opportunity_types,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_LINKBUILDING_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "linkbuilding", payload, result
    )
    helper_log(runtime, auth.tenant_id, "linkbuilding_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_content_brief(
    runtime: ContextRuntime, req: ContentBriefReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Generate a detailed SEO content brief for writers."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:content_brief", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "content_brief", payload
    )
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "content_brief", {"topic": req.topic, "analysis_id": cached["id"], "cached": True}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await generate_content_brief(
        topic=req.topic,
        keywords=req.keywords,
        word_count=req.word_count,
        audience=req.audience,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_BRIEF_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "content_brief", payload, result
    )
    helper_log(runtime, auth.tenant_id, "content_brief", {"topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


def helper_performance_test_profile(req: PerformanceAuditReq) -> dict[str, Any]:
    return {
        "url": req.url,
        "target_device": req.target_device,
        "target_region": req.target_region,
        "connection": req.connection,
        "browser": req.browser,
        "include_video": bool(req.include_video),
        "adblock_enabled": bool(req.adblock_enabled),
        "capture_har": bool(req.capture_har),
    }


async def execute_performance_browser_profiles(
    runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()
