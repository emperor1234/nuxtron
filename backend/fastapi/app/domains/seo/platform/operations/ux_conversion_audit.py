"""Seo/Platform use cases: ux conversion audit."""

from datetime import UTC, datetime
from functools import partial
from typing import Annotated

from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_log_file_service import analyze_log_file
from .....domains.seo.services.seo_news_discover_service import analyze_news_discover
from .....domains.seo.services.seo_rag_search_service import raise_rag_search_unavailable
from .....domains.seo.services.seo_topical_map_service import build_topical_map
from .....domains.seo.services.seo_ux_service import audit_ux_conversion
from ..constants import _LOG_FILE_SYS, _NEWS_DISCOVER_SYS, _TOPICAL_MAP_SYS, _UX_CONVERSION_SYS
from ..runtime import ContextRuntime
from ..schemas import (
    AgencyPlatformReq,
    CompetitorIntelReq,
    ContentAuditorReq,
    CrawlBudgetReq,
    IntegrationsAutomationReq,
    KnowledgeGraphReq,
    LogFileAnalysisReq,
    NewsDiscoverReq,
    PlannerExecuteReq,
    RagSearchReq,
    RealtimeMonitoringReq,
    TopicalMapReq,
    UxConversionReq,
)
from ..services import extract_waterfall as provider_ollama_json
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_find_cached_analysis, helper_log

_CONTENT_AUDITOR_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "A verifiable source-retrieval and citation-checking pipeline is not configured. Generated fact-check verdicts and quality scores are disabled until findings can be tied to evidence.",
}

_CRAWL_BUDGET_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "The connected crawl-budget metric engine is not available. Use the local sample review in the dashboard; no sitewide score or crawl-waste estimate is produced by this API.",
}

_REALTIME_MONITOR_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "Search-provider observations and a durable monitoring scheduler are not configured. Query positions, volatility, AI-surface presence, and alert claims are disabled; use the dashboard's manual observation log instead.",
}

_INTEGRATIONS_AUTOMATION_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": "An authorized workspace connector inventory and health-check service is not configured. Coverage scores, connector health, event-flow risk, and generated automation backlog claims are disabled.",
}

_AGENCY_PLATFORM_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "An authorized workspace inventory, membership and role data, policy records, audit events, owners, and SLA "
        "observations are not connected. Caller-entered workspace names and generated health or governance scores are disabled."
    ),
}

_COMPETITOR_INTEL_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Verified SERP positions, keyword-volume data, traffic and backlink metrics, and sampled AI-answer observations "
        "are not connected. Generated competitor rankings, authority, visibility, and content-gap scores are disabled."
    ),
}


async def execute_ux_conversion_audit(
    runtime: ContextRuntime, req: UxConversionReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Audit UX, conversion friction points, trust signals, and A/B test ideas from organic traffic."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:ux", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "ux", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "ux_conversion_audit",
            {"url": req.url, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await audit_ux_conversion(
        url=req.url,
        page_type=req.page_type,
        traffic_source=req.traffic_source,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_UX_CONVERSION_SYS,
        clean_text_fn=_clean,
    )
    result["url"] = req.url
    result["page_type"] = req.page_type
    result["audited_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(partial(helper_save_analysis, runtime), auth.tenant_id, "ux", payload, result)
    helper_log(
        runtime, auth.tenant_id, "ux_conversion_audit", {"url": req.url, "page_type": req.page_type, "cached": False}
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_rag_search_query(
    _runtime: ContextRuntime, _req: RagSearchReq, _auth: AuthContext
):
    """Reject remote search until a tenant-scoped index and cited retrieval exist."""
    raise_rag_search_unavailable()


async def execute_competitor_analyze(
    runtime: ContextRuntime, req: CompetitorIntelReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Reject competitor estimates until the report is backed by verified search evidence."""
    raise HTTPException(status_code=501, detail=_COMPETITOR_INTEL_UNAVAILABLE)


async def execute_realtime_monitor(
    runtime: ContextRuntime, req: RealtimeMonitoringReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not label estimates as real search observations or ongoing monitoring."""
    raise HTTPException(status_code=501, detail=_REALTIME_MONITOR_UNAVAILABLE)


async def execute_content_auditor_analyze(
    runtime: ContextRuntime, req: ContentAuditorReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not expose factuality verdicts without source-backed evidence."""
    raise HTTPException(status_code=501, detail=_CONTENT_AUDITOR_UNAVAILABLE)


async def execute_knowledge_graph_analyze(
    runtime: ContextRuntime, req: KnowledgeGraphReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not claim a live entity graph without crawling or source-backed data."""
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "A source-backed entity graph is not connected. The dashboard provides a local outline planner and does not infer live graph health or relationships.",
        },
    )


async def execute_crawl_budget_analyze(
    runtime: ContextRuntime, req: CrawlBudgetReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Prevent formula-based crawl metrics from being exposed as measured results."""
    raise HTTPException(status_code=501, detail=_CRAWL_BUDGET_UNAVAILABLE)


async def execute_news_discover_analyze(
    runtime: ContextRuntime, req: NewsDiscoverReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Analyze freshness, headline quality, and Google Discover readiness for news content."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:news_discover", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "news_discover", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "news_discover_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_news_discover(
        domain=req.domain,
        recent_headlines=req.recent_headlines,
        focus_topics=req.focus_topics,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_NEWS_DISCOVER_SYS,
        clean_text_fn=_clean,
        llm_timeout_seconds=12,
    )
    result["domain"] = req.domain
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "news_discover", payload, result
    )
    helper_log(runtime, auth.tenant_id, "news_discover_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_analytics_reporting(
    runtime: ContextRuntime, req: PlannerExecuteReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not report inferred traffic changes without observations from an analytics provider."""
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "No analytics-provider connection is configured for this report. Generated traffic scores, trends, risks, and attribution are disabled; use the dashboard's manual period comparison for values you supply.",
        },
    )


async def execute_agency_platform_analyze(
    runtime: ContextRuntime, req: AgencyPlatformReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Reject unverified workspace-health claims until trusted evidence sources are connected."""
    raise HTTPException(status_code=501, detail=_AGENCY_PLATFORM_UNAVAILABLE)


async def execute_integrations_automation_analyze(
    runtime: ContextRuntime, req: IntegrationsAutomationReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Fail closed until connector health comes from authorized workspace integrations."""
    raise HTTPException(status_code=501, detail=_INTEGRATIONS_AUTOMATION_UNAVAILABLE)


async def execute_topical_map_build(
    runtime: ContextRuntime, req: TopicalMapReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Build a topical authority map with pillar pages, clusters, and silo architecture."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:topical", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "topical_map", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "topical_map_build",
            {"seed_topic": req.seed_topic, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await build_topical_map(
        seed_topic=req.seed_topic,
        domain=req.domain,
        depth=req.depth,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_TOPICAL_MAP_SYS,
        clean_text_fn=_clean,
    )
    result["seed_topic"] = req.seed_topic
    result["domain"] = req.domain
    result["generated_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "topical_map", payload, result
    )
    helper_log(runtime, auth.tenant_id, "topical_map_build", {"seed_topic": req.seed_topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_log_file_analyze(
    runtime: ContextRuntime, req: LogFileAnalysisReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Analyze crawl logs for bot behavior, anomalies, and crawl budget waste."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:logfile", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "log_file", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "log_file_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_log_file(
        log_snippet=req.log_snippet,
        domain=req.domain,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_LOG_FILE_SYS,
        clean_text_fn=_clean,
    )
    result["domain"] = req.domain
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "log_file", payload, result
    )
    helper_log(runtime, auth.tenant_id, "log_file_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}
