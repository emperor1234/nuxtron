"""Seo/Platform use cases: ux conversion audit."""

from ..services import extract_waterfall as provider_ollama_json
from functools import partial
from .....deps import AuthContext
from .....deps import require_auth
from .....domains.seo.services.seo_agency_platform_service import analyze_agency_platform
from .....domains.seo.services.seo_analytics_reporting_service import generate_analytics_report
from .....domains.seo.services.seo_competitor_service import analyze_competitor_intel
from .....domains.seo.services.seo_content_auditor_service import analyze_content_auditor
from .....domains.seo.services.seo_crawl_budget_service import analyze_crawl_budget
from .....domains.seo.services.seo_integrations_automation_service import analyze_integrations_automation
from .....domains.seo.services.seo_knowledge_graph_service import analyze_knowledge_graph
from .....domains.seo.services.seo_log_file_service import analyze_log_file
from .....domains.seo.services.seo_news_discover_service import analyze_news_discover
from .....domains.seo.services.seo_rag_search_service import query_rag_search
from .....domains.seo.services.seo_realtime_monitoring_service import analyze_realtime_monitoring
from .....domains.seo.services.seo_topical_map_service import build_topical_map
from .....domains.seo.services.seo_ux_service import audit_ux_conversion
from ..constants import _AGENCY_PLATFORM_SYS
from ..constants import _ANALYTICS_REPORTING_SYS
from ..constants import _COMPETITOR_INTEL_SYS
from ..constants import _CONTENT_AUDITOR_SYS
from ..constants import _CRAWL_BUDGET_SYS
from ..constants import _INTEGRATIONS_AUTOMATION_SYS
from ..constants import _KNOWLEDGE_GRAPH_SYS
from ..constants import _LOG_FILE_SYS
from ..constants import _NEWS_DISCOVER_SYS
from ..constants import _RAG_SEARCH_SYS
from ..constants import _REALTIME_MONITORING_SYS
from ..constants import _TOPICAL_MAP_SYS
from ..constants import _UX_CONVERSION_SYS
from ..runtime import ContextRuntime
from ..schemas import AgencyPlatformReq
from ..schemas import CompetitorIntelReq
from ..schemas import ContentAuditorReq
from ..schemas import CrawlBudgetReq
from ..schemas import IntegrationsAutomationReq
from ..schemas import KnowledgeGraphReq
from ..schemas import LogFileAnalysisReq
from ..schemas import NewsDiscoverReq
from ..schemas import PlannerExecuteReq
from ..schemas import RagSearchReq
from ..schemas import RealtimeMonitoringReq
from ..schemas import TopicalMapReq
from ..schemas import UxConversionReq
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_find_cached_analysis
from .sync_job_store import helper_log
from datetime import UTC
from datetime import datetime
from fastapi import Depends
from starlette.concurrency import run_in_threadpool
from typing import Annotated


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
    runtime: ContextRuntime, req: RagSearchReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Semantic site search: retrieve, rank, and synthesize answers from site content."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:rag", limit=20, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "rag_search", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "rag_search_query",
            {"query": req.query, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await query_rag_search(
        query=req.query,
        site_domain=req.site_domain,
        content_corpus=req.content_corpus,
        top_k=req.top_k,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_RAG_SEARCH_SYS,
        clean_text_fn=_clean,
    )
    result["site_domain"] = req.site_domain
    result["searched_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "rag_search", payload, result
    )
    helper_log(
        runtime, auth.tenant_id, "rag_search_query", {"query": req.query, "domain": req.site_domain, "cached": False}
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_competitor_analyze(
    runtime: ContextRuntime, req: CompetitorIntelReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Analyze competitors for keyword gaps, content gaps, and AI visibility intelligence."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:competitor", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "competitor", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "competitor_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    comps = req.competitors[:5] if req.competitors else ["competitor1.com", "competitor2.com"]
    result = await analyze_competitor_intel(
        domain=req.domain,
        competitors=req.competitors,
        target_keyword=req.target_keyword,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_COMPETITOR_INTEL_SYS,
        clean_text_fn=_clean,
    )
    result["domain"] = req.domain
    result["competitors_analyzed"] = comps
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "competitor", payload, result
    )
    helper_log(runtime, auth.tenant_id, "competitor_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_realtime_monitor(
    runtime: ContextRuntime, req: RealtimeMonitoringReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Monitor real-time search volatility, rank swings, and AI-surface visibility changes."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:realtime", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "realtime_monitoring", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "realtime_monitor",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_realtime_monitoring(
        domain=req.domain,
        tracked_queries=req.tracked_queries,
        lookback_hours=req.lookback_hours,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_REALTIME_MONITORING_SYS,
        clean_text_fn=_clean,
    )
    result["domain"] = req.domain
    result["tracked_queries"] = req.tracked_queries[:8] if req.tracked_queries else ["brand query", "money query"]
    result["monitored_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "realtime_monitoring", payload, result
    )
    helper_log(runtime, auth.tenant_id, "realtime_monitor", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_content_auditor_analyze(
    runtime: ContextRuntime, req: ContentAuditorReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Audit AI-assisted content for factuality, hallucination risk, and E-E-A-T quality."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:content_auditor", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "content_auditor", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "content_auditor_analyze",
            {"source_url": req.source_url, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_content_auditor(
        content=req.content,
        source_url=req.source_url,
        topic=req.topic,
        target_model=req.target_model,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_CONTENT_AUDITOR_SYS,
        clean_text_fn=_clean,
    )
    result["source_url"] = req.source_url
    result["target_model"] = req.target_model
    result["audited_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "content_auditor", payload, result
    )
    helper_log(runtime, auth.tenant_id, "content_auditor_analyze", {"source_url": req.source_url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_knowledge_graph_analyze(
    runtime: ContextRuntime, req: KnowledgeGraphReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Analyze entity graph health, relationship coverage, and entity expansion gaps."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:knowledge_graph", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "knowledge_graph", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "knowledge_graph_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    seeds = req.seed_entities[:10] if req.seed_entities else ["brand", "core product", "industry concept"]
    result = await analyze_knowledge_graph(
        domain=req.domain,
        seed_entities=req.seed_entities,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_KNOWLEDGE_GRAPH_SYS,
        clean_text_fn=_clean,
    )
    result["domain"] = req.domain
    result["seed_entities"] = seeds
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "knowledge_graph", payload, result
    )
    helper_log(runtime, auth.tenant_id, "knowledge_graph_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_crawl_budget_analyze(
    runtime: ContextRuntime, req: CrawlBudgetReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Analyze crawl efficiency and prioritize crawl budget for high-value URLs."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:crawl_budget", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "crawl_budget", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "crawl_budget_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_crawl_budget(
        domain=req.domain,
        sample_urls=req.sample_urls,
        log_snippet=req.log_snippet,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_CRAWL_BUDGET_SYS,
        clean_text_fn=_clean,
    )
    result["domain"] = req.domain
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "crawl_budget", payload, result
    )
    helper_log(runtime, auth.tenant_id, "crawl_budget_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


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
    """Generate analytics and reporting summary across SEO modules for the selected domain and goal."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:analytics_reporting", limit=10, window_seconds=60)
    domain = req.domain or "example.com"
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "analytics", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "analytics_reporting",
            {"domain": domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await generate_analytics_report(
        goal=req.goal,
        domain=domain,
        primary_keyword=req.primary_keyword,
        market=req.market,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_ANALYTICS_REPORTING_SYS,
        clean_text_fn=_clean,
    )
    result["domain"] = domain
    result["generated_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "analytics", payload, result
    )
    helper_log(runtime, auth.tenant_id, "analytics_reporting", {"domain": domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_agency_platform_analyze(
    runtime: ContextRuntime, req: AgencyPlatformReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Assess agency multi-tenant operations, governance, and workspace health."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:agency_platform", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "agency_platform", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "agency_platform_analyze",
            {"agency_name": req.agency_name, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_agency_platform(
        agency_name=req.agency_name,
        workspaces=req.workspaces,
        governance_focus=req.governance_focus,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_AGENCY_PLATFORM_SYS,
        clean_text_fn=_clean,
    )
    result["agency_name"] = req.agency_name
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "agency_platform", payload, result
    )
    helper_log(runtime, auth.tenant_id, "agency_platform_analyze", {"agency_name": req.agency_name, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_integrations_automation_analyze(
    runtime: ContextRuntime, req: IntegrationsAutomationReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Analyze connector coverage, automation backlog, and integration workflow health."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:integrations_automation", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "integrations_automation", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "integrations_automation_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_integrations_automation(
        domain=req.domain,
        integrations=req.integrations,
        automation_goals=req.automation_goals,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_INTEGRATIONS_AUTOMATION_SYS,
        clean_text_fn=_clean,
    )
    result["domain"] = req.domain
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "integrations_automation", payload, result
    )
    helper_log(runtime, auth.tenant_id, "integrations_automation_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


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
