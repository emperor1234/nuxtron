
"""Seo/Platform HTTP composition and legacy import exports."""

import asyncio  # noqa: F401
import subprocess  # noqa: F401
import threading
from collections.abc import Callable
from typing import Any

import httpx  # noqa: F401
import psycopg  # noqa: F401
from fastapi import APIRouter

from .api import (
    agency_platform_analyze,
    agent_run,
    backlink_intelligence_analyze,
    competitor_analyze,
    cxao_analyze,
    health,
    linkbuilding_analyze,
    local_seo_optimize,
    on_page_analyze,
    performance_alert_events,
    performance_audit,
    planner,
    vso_optimize,
)
from .constants import _ACCESSIBILITY_SYS as _ACCESSIBILITY_SYS
from .constants import _AEO_SYS as _AEO_SYS
from .constants import _AGENCY_PLATFORM_SYS as _AGENCY_PLATFORM_SYS
from .constants import _AGENT_SYS as _AGENT_SYS
from .constants import _AIO_SYS as _AIO_SYS
from .constants import _ANALYTICS_REPORTING_SYS as _ANALYTICS_REPORTING_SYS
from .constants import _BACKLINK_INTELLIGENCE_SYS as _BACKLINK_INTELLIGENCE_SYS
from .constants import _BLOCKED as _BLOCKED
from .constants import _BRAND_VOICE_SYS as _BRAND_VOICE_SYS
from .constants import _BRIEF_SYS as _BRIEF_SYS
from .constants import _COMPETITOR_INTEL_SYS as _COMPETITOR_INTEL_SYS
from .constants import _CONTENT_AUDITOR_SYS as _CONTENT_AUDITOR_SYS
from .constants import _CONTENT_CREATION_BLOGGING_SYS as _CONTENT_CREATION_BLOGGING_SYS
from .constants import _CRAWL_BUDGET_SYS as _CRAWL_BUDGET_SYS
from .constants import _CXAO_SYS as _CXAO_SYS
from .constants import _DAEO_SYS as _DAEO_SYS
from .constants import _ECOMMERCE_SYS as _ECOMMERCE_SYS
from .constants import _EEAT_SYS as _EEAT_SYS
from .constants import _ENTITY_SYS as _ENTITY_SYS
from .constants import _GEO_SYS as _GEO_SYS
from .constants import _GROWTH_PLAYBOOKS_SYS as _GROWTH_PLAYBOOKS_SYS
from .constants import _GXO_SYS as _GXO_SYS
from .constants import _INTEGRATIONS_AUTOMATION_SYS as _INTEGRATIONS_AUTOMATION_SYS
from .constants import _INTERNAL_LINKING_SYS as _INTERNAL_LINKING_SYS
from .constants import _KNOWLEDGE_GRAPH_SYS as _KNOWLEDGE_GRAPH_SYS
from .constants import _LANDING_SYS as _LANDING_SYS
from .constants import _LINKBUILDING_SYS as _LINKBUILDING_SYS
from .constants import _LLMO_SYS as _LLMO_SYS
from .constants import _LOCAL_SYS as _LOCAL_SYS
from .constants import _LOG_FILE_SYS as _LOG_FILE_SYS
from .constants import _MEDIA_SEO_SYS as _MEDIA_SEO_SYS
from .constants import _MSVO_SYS as _MSVO_SYS
from .constants import _MULTI_CHANNEL_ACTIVATION_SYS as _MULTI_CHANNEL_ACTIVATION_SYS
from .constants import _NEWS_DISCOVER_SYS as _NEWS_DISCOVER_SYS
from .constants import _OLLAMA_CACHE as _OLLAMA_CACHE
from .constants import _OLLAMA_CACHE_LOCK as _OLLAMA_CACHE_LOCK
from .constants import _OLLAMA_INFLIGHT as _OLLAMA_INFLIGHT
from .constants import _ONPAGE_SYS as _ONPAGE_SYS
from .constants import _PEAO_SYS as _PEAO_SYS
from .constants import _PERFORMANCE_SYS as _PERFORMANCE_SYS
from .constants import _RANK_TRACKING_SYS as _RANK_TRACKING_SYS
from .constants import _REALTIME_MONITORING_SYS as _REALTIME_MONITORING_SYS
from .constants import _REVENUE_ATTRIBUTION_SYS as _REVENUE_ATTRIBUTION_SYS
from .constants import _REVIEW_REPUTATION_SYS as _REVIEW_REPUTATION_SYS
from .constants import _SAGEO_SYS as _SAGEO_SYS
from .constants import _SCHEMA_SYS as _SCHEMA_SYS
from .constants import _SECURITY_SEO_SYS as _SECURITY_SEO_SYS
from .constants import _SEO_AB_TESTING_SYS as _SEO_AB_TESTING_SYS
from .constants import _SEO_AI_CORE_SYS as _SEO_AI_CORE_SYS
from .constants import _SITE_MIGRATION_SYS as _SITE_MIGRATION_SYS
from .constants import _SOCIAL_SEO_SYS as _SOCIAL_SEO_SYS
from .constants import _STRICT_NO_MOCK_FALSY as _STRICT_NO_MOCK_FALSY
from .constants import _SXO_SYS as _SXO_SYS
from .constants import _TECHNICAL_SYS as _TECHNICAL_SYS
from .constants import _TOPICAL_MAP_SYS as _TOPICAL_MAP_SYS
from .constants import _TRUST_RISK_GOVERNANCE_SYS as _TRUST_RISK_GOVERNANCE_SYS
from .constants import _UX_CONVERSION_SYS as _UX_CONVERSION_SYS
from .constants import _VIDEO_SYS as _VIDEO_SYS
from .constants import _VSO_SYS as _VSO_SYS
from .constants import _WRITER_SYS as _WRITER_SYS
from .constants import OLLAMA_BASE_URL as OLLAMA_BASE_URL
from .constants import OLLAMA_TIMEOUT as OLLAMA_TIMEOUT
from .constants import SEO_ANALYSIS_CACHE_TTL_SEC as SEO_ANALYSIS_CACHE_TTL_SEC
from .constants import SEO_DEFAULT_MODEL as SEO_DEFAULT_MODEL
from .constants import SEO_MODULE_COUNT as SEO_MODULE_COUNT
from .constants import SEO_OLLAMA_CACHE_MAX_ENTRIES as SEO_OLLAMA_CACHE_MAX_ENTRIES
from .constants import SEO_OLLAMA_CACHE_TTL_SEC as SEO_OLLAMA_CACHE_TTL_SEC
from .constants import SEO_PERF_CHROME_PATH as SEO_PERF_CHROME_PATH
from .constants import SEO_PERF_CRUX_API_KEY as SEO_PERF_CRUX_API_KEY
from .constants import SEO_PERF_FREE_TIMEOUT_SEC as SEO_PERF_FREE_TIMEOUT_SEC
from .constants import SEO_PERF_LIGHTHOUSE_PATH as SEO_PERF_LIGHTHOUSE_PATH
from .constants import SEO_PERF_PSI_API_KEY as SEO_PERF_PSI_API_KEY
from .constants import SEO_PERF_WEBPAGETEST_API_KEY as SEO_PERF_WEBPAGETEST_API_KEY
from .constants import SEO_UPSTASH_TIMEOUT_SEC as SEO_UPSTASH_TIMEOUT_SEC
from .constants import _shared_job_store
from .constants import logger as logger
from .runtime import ContextRuntime
from .schemas import AccessibilityAuditReq as AccessibilityAuditReq
from .schemas import AEOReq as AEOReq
from .schemas import AgencyPlatformReq as AgencyPlatformReq
from .schemas import AgentRunReq as AgentRunReq
from .schemas import AIOReq as AIOReq
from .schemas import AIWriterReq as AIWriterReq
from .schemas import BacklinkIntelligenceReq as BacklinkIntelligenceReq
from .schemas import BrandVoiceReq as BrandVoiceReq
from .schemas import CompetitorIntelReq as CompetitorIntelReq
from .schemas import ContentAuditorReq as ContentAuditorReq
from .schemas import ContentBriefReq as ContentBriefReq
from .schemas import ContentCreationBloggingReq as ContentCreationBloggingReq
from .schemas import CrawlBudgetReq as CrawlBudgetReq
from .schemas import CxaoReq as CxaoReq
from .schemas import DaeoReq as DaeoReq
from .schemas import EcommerceSEOReq as EcommerceSEOReq
from .schemas import EEATReq as EEATReq
from .schemas import EntityReq as EntityReq
from .schemas import GEOReq as GEOReq
from .schemas import GrowthPlaybooksReq as GrowthPlaybooksReq
from .schemas import GXOReq as GXOReq
from .schemas import IntegrationsAutomationReq as IntegrationsAutomationReq
from .schemas import InternalLinkingReq as InternalLinkingReq
from .schemas import InternationalMultilingualReq as InternationalMultilingualReq
from .schemas import KeywordResearchReq as KeywordResearchReq
from .schemas import KnowledgeGraphReq as KnowledgeGraphReq
from .schemas import LandingPageGenerateReq as LandingPageGenerateReq
from .schemas import LinkBuildingReq as LinkBuildingReq
from .schemas import LLMOReq as LLMOReq
from .schemas import LocalSEOReq as LocalSEOReq
from .schemas import LogFileAnalysisReq as LogFileAnalysisReq
from .schemas import MediaSeoAuditReq as MediaSeoAuditReq
from .schemas import MsvoReq as MsvoReq
from .schemas import MultiChannelActivationReq as MultiChannelActivationReq
from .schemas import NewsDiscoverReq as NewsDiscoverReq
from .schemas import OnPageReq as OnPageReq
from .schemas import PeaoReq as PeaoReq
from .schemas import PerformanceAuditReq as PerformanceAuditReq
from .schemas import PerformanceAutoFixReq as PerformanceAutoFixReq
from .schemas import PerformanceCompareReq as PerformanceCompareReq
from .schemas import PerformanceMonitorCreateReq as PerformanceMonitorCreateReq
from .schemas import PerformanceReportShareReq as PerformanceReportShareReq
from .schemas import PerformanceRumIngestReq as PerformanceRumIngestReq
from .schemas import PlannerExecuteAllReq as PlannerExecuteAllReq
from .schemas import PlannerExecuteReq as PlannerExecuteReq
from .schemas import ProgrammaticSEOReq as ProgrammaticSEOReq
from .schemas import RagSearchReq as RagSearchReq
from .schemas import RankTrackingReq as RankTrackingReq
from .schemas import RealtimeMonitoringReq as RealtimeMonitoringReq
from .schemas import RevenueAttributionReq as RevenueAttributionReq
from .schemas import ReviewReputationReq as ReviewReputationReq
from .schemas import SageoReq as SageoReq
from .schemas import SchemaGenReq as SchemaGenReq
from .schemas import SecuritySeoAuditReq as SecuritySeoAuditReq
from .schemas import SeoAbTestingReq as SeoAbTestingReq
from .schemas import SeoAiCoreReq as SeoAiCoreReq
from .schemas import SiteMigrationReq as SiteMigrationReq
from .schemas import SocialSeoAuditReq as SocialSeoAuditReq
from .schemas import SXOReq as SXOReq
from .schemas import TechnicalAuditReq as TechnicalAuditReq
from .schemas import TopicalMapReq as TopicalMapReq
from .schemas import TrustRiskGovernanceReq as TrustRiskGovernanceReq
from .schemas import UxConversionReq as UxConversionReq
from .schemas import VideoSEOReq as VideoSEOReq
from .schemas import VSOReq as VSOReq
from .services.extract_waterfall import _extract_crux_field as _extract_crux_field
from .services.extract_waterfall import _extract_filmstrip as _extract_filmstrip
from .services.extract_waterfall import _extract_waterfall as _extract_waterfall
from .services.extract_waterfall import _ollama_json as _ollama_json
from .services.extract_waterfall import _run_free_performance_stack as _run_free_performance_stack
from .services.get_shared_job_store import _clean as _clean
from .services.get_shared_job_store import _extract_core_vitals as _extract_core_vitals
from .services.get_shared_job_store import _extract_scores as _extract_scores
from .services.get_shared_job_store import _lighthouse_command_candidates as _lighthouse_command_candidates
from .services.get_shared_job_store import _normalize_perf_metric_name as _normalize_perf_metric_name
from .services.get_shared_job_store import _perf_float as _perf_float
from .services.get_shared_job_store import _perf_int as _perf_int
from .services.get_shared_job_store import _perf_percentile as _perf_percentile
from .services.get_shared_job_store import _performance_score_from_field as _performance_score_from_field
from .services.get_shared_job_store import _run_crux as _run_crux
from .services.get_shared_job_store import _run_http_probe as _run_http_probe
from .services.get_shared_job_store import _run_lighthouse as _run_lighthouse
from .services.get_shared_job_store import _run_lighthouse_sync as _run_lighthouse_sync
from .services.get_shared_job_store import _run_network_probe as _run_network_probe
from .services.get_shared_job_store import _run_network_probe_sync as _run_network_probe_sync
from .services.get_shared_job_store import _run_pagespeed as _run_pagespeed
from .services.get_shared_job_store import _run_webpagetest as _run_webpagetest
from .services.get_shared_job_store import _seo_analysis_cache_key as _seo_analysis_cache_key
from .services.get_shared_job_store import _seo_analysis_dist_cache_enabled as _seo_analysis_dist_cache_enabled
from .services.get_shared_job_store import _strict_no_mock_mode as _strict_no_mock_mode
from .services.get_shared_job_store import _upstash_command as _upstash_command
from .services.get_shared_job_store import _upstash_rest_base_url as _upstash_rest_base_url
from .services.get_shared_job_store import _upstash_rest_token as _upstash_rest_token
from .services.get_shared_job_store import get_shared_job_store as get_shared_job_store
from .services.rollup_performance_rum import _rollup_performance_rum as _rollup_performance_rum


def create_seo_platform_router(
    *,
    enforce_rate_limit,
    audit_log_memory: list[dict[str, Any]],
    seo_analyses_memory: list[dict[str, Any]],
    db_ready_fn: Callable[[], bool] | None = None,
    db_dsn_fn: Callable[[], str] | None = None,
) -> APIRouter:
    """Factory for the SEO Platform router (all 20+ AI SEO modules)."""
    router = APIRouter(prefix="/seo-platform", tags=["seo-platform"])
    _db_ready_fn = db_ready_fn if db_ready_fn is not None else lambda: False
    _db_dsn_fn = db_dsn_fn if db_dsn_fn is not None else lambda: ""
    _db_initialized = False
    _job_lock = threading.Lock()
    _job_store: dict[str, dict[str, Any]] = {}
    _shared_job_store.clear()
    _shared_job_store.update(_job_store)
    import sys as _sys

    _mod = _sys.modules[__name__]
    _mod._shared_job_store = _job_store
    _MODULE_EFFORT_MAP: dict[str, str] = {
        "keyword_research": "medium",
        "on_page_seo": "low",
        "technical_seo": "medium",
        "schema_markup": "low",
        "link_building": "high",
        "content_brief": "low",
        "ai_writer": "low",
        "geo_seo": "medium",
        "aeo": "medium",
        "aio": "low",
        "llmo": "high",
        "vso": "medium",
        "sxo": "medium",
        "gxo": "medium",
        "eeat": "medium",
        "entity_seo": "medium",
        "local_seo": "medium",
        "video_seo": "medium",
        "sageo": "high",
        "peao": "high",
        "msvo": "high",
        "daeo": "high",
        "programmatic_seo": "high",
        "ecommerce_seo": "medium",
        "competitor_intelligence": "medium",
        "realtime_monitoring": "high",
        "content_auditor": "low",
        "knowledge_graph": "high",
        "internal_linking": "low",
        "crawl_budget": "medium",
        "news_seo": "low",
        "analytics": "medium",
        "agency_platform": "high",
        "integrations": "medium",
        "topical_map": "medium",
        "log_file_analysis": "medium",
        "reviews_reputation": "low",
        "brand_voice": "low",
        "ux_conversion": "medium",
        "rag_search": "low",
        "backlink_intelligence": "high",
        "rank_tracking": "medium",
        "content_creation_blogging": "medium",
    }
    _MODULE_NEXT_STEPS: dict[str, list[dict[str, str]]] = {
        "keyword_research": [
            {
                "action": "Map intent clusters to URL structure and content calendar",
                "priority": "high",
                "effort": "medium",
                "impact": "high",
            },
            {
                "action": "Identify quick-win keywords with low difficulty and high CTR potential",
                "priority": "high",
                "effort": "low",
                "impact": "high",
            },
            {
                "action": "Build keyword-to-persona matrix for content targeting",
                "priority": "medium",
                "effort": "medium",
                "impact": "medium",
            },
        ],
        "on_page_seo": [
            {
                "action": "Fix title tag and meta description within 24 hours",
                "priority": "high",
                "effort": "low",
                "impact": "high",
            },
            {
                "action": "Optimize heading hierarchy and keyword placement",
                "priority": "high",
                "effort": "low",
                "impact": "medium",
            },
            {
                "action": "Add structured data markup for target schema types",
                "priority": "medium",
                "effort": "medium",
                "impact": "high",
            },
        ],
        "technical_seo": [
            {
                "action": "Resolve all critical crawlability and indexability issues first",
                "priority": "critical",
                "effort": "medium",
                "impact": "high",
            },
            {
                "action": "Fix Core Web Vitals to meet Google's threshold",
                "priority": "high",
                "effort": "medium",
                "impact": "high",
            },
            {
                "action": "Submit updated XML sitemap and request re-crawl via GSC",
                "priority": "high",
                "effort": "low",
                "impact": "medium",
            },
        ],
        "geo_seo": [
            {
                "action": "Add definitive answer blocks at top of every key content page",
                "priority": "high",
                "effort": "low",
                "impact": "high",
            },
            {
                "action": "Enrich content with citable statistics and expert quotes",
                "priority": "high",
                "effort": "medium",
                "impact": "high",
            },
            {
                "action": "Implement FAQPage and HowTo schema for every target topic",
                "priority": "high",
                "effort": "low",
                "impact": "high",
            },
        ],
        "aeo": [
            {
                "action": "Create dedicated FAQ page optimized for PAA extraction",
                "priority": "high",
                "effort": "low",
                "impact": "high",
            },
            {
                "action": "Reformat top content as direct answers under 40 words",
                "priority": "high",
                "effort": "low",
                "impact": "high",
            },
            {
                "action": "Add SpeakableSpecification markup for voice search targets",
                "priority": "medium",
                "effort": "medium",
                "impact": "medium",
            },
        ],
        "llmo": [
            {
                "action": "Publish Wikipedia-citable company overview and product pages",
                "priority": "critical",
                "effort": "high",
                "impact": "high",
            },
            {
                "action": "Build authoritative citation footprint across tier-1 publications",
                "priority": "high",
                "effort": "high",
                "impact": "high",
            },
            {
                "action": "Establish structured fact repository for LLM training signals",
                "priority": "high",
                "effort": "medium",
                "impact": "high",
            },
        ],
        "eeat": [
            {
                "action": "Add author bios with credentials and first-hand experience signals",
                "priority": "high",
                "effort": "low",
                "impact": "high",
            },
            {
                "action": "Acquire editorial mentions in authoritative industry publications",
                "priority": "high",
                "effort": "high",
                "impact": "high",
            },
            {
                "action": "Display trust signals: certifications, awards, press mentions",
                "priority": "medium",
                "effort": "low",
                "impact": "medium",
            },
        ],
        "competitor_intelligence": [
            {
                "action": "Target all high-traffic competitor content gaps with new articles",
                "priority": "high",
                "effort": "high",
                "impact": "high",
            },
            {
                "action": "Build skyscraper content for top competitor link assets",
                "priority": "high",
                "effort": "high",
                "impact": "high",
            },
            {
                "action": "Monitor competitor SERP movements weekly and respond within 48h",
                "priority": "medium",
                "effort": "low",
                "impact": "medium",
            },
        ],
        "backlink_intelligence": [
            {
                "action": "Launch targeted outreach to reclaim unlinked brand mentions",
                "priority": "high",
                "effort": "medium",
                "impact": "high",
            },
            {
                "action": "Execute skyscraper campaign for top competitor link sources",
                "priority": "high",
                "effort": "high",
                "impact": "high",
            },
            {
                "action": "Set monthly link velocity targets and track via spreadsheet",
                "priority": "medium",
                "effort": "low",
                "impact": "medium",
            },
        ],
    }
    _DEFAULT_NEXT_STEPS = [
        {
            "action": "Review all identified issues and prioritize by revenue impact",
            "priority": "high",
            "effort": "low",
            "impact": "high",
        },
        {
            "action": "Implement quick-win recommendations within 48 hours",
            "priority": "high",
            "effort": "low",
            "impact": "medium",
        },
        {
            "action": "Schedule follow-up audit in 30 days to measure improvement",
            "priority": "medium",
            "effort": "low",
            "impact": "medium",
        },
    ]
    _PERF_TEST_LOCATIONS: list[dict[str, Any]] = [
        {"code": "lhr1", "label": "London (UK)", "country": "GB", "provider": "Cloudflare + AWS"},
        {"code": "iad1", "label": "Washington DC (US)", "country": "US", "provider": "AWS"},
        {"code": "sfo1", "label": "San Francisco (US)", "country": "US", "provider": "GCP"},
        {"code": "sin1", "label": "Singapore", "country": "SG", "provider": "AWS"},
        {"code": "bom1", "label": "Mumbai (IN)", "country": "IN", "provider": "Cloudflare + Azure"},
        {"code": "syd1", "label": "Sydney (AU)", "country": "AU", "provider": "AWS"},
        {"code": "cdg1", "label": "Paris (FR)", "country": "FR", "provider": "GCP"},
        {"code": "gru1", "label": "Sao Paulo (BR)", "country": "BR", "provider": "AWS"},
    ]
    _PERF_BROWSER_PROFILES: list[dict[str, Any]] = [
        {
            "browser": "chrome",
            "devices": ["mobile", "desktop"],
            "connection_profiles": ["3g_slow", "3g_fast", "4g", "cable", "fiber"],
        },
        {"browser": "firefox", "devices": ["desktop"], "connection_profiles": ["3g_fast", "4g", "cable", "fiber"]},
        {"browser": "edge", "devices": ["desktop"], "connection_profiles": ["4g", "cable", "fiber"]},
        {"browser": "safari", "devices": ["mobile", "desktop"], "connection_profiles": ["4g", "wifi", "fiber"]},
    ]
    _PERF_ASYNC_TEST_JOBS: dict[str, dict[str, Any]] = {}
    runtime = ContextRuntime(
        _DEFAULT_NEXT_STEPS=_DEFAULT_NEXT_STEPS,
        _MODULE_NEXT_STEPS=_MODULE_NEXT_STEPS,
        _PERF_ASYNC_TEST_JOBS=_PERF_ASYNC_TEST_JOBS,
        _PERF_BROWSER_PROFILES=_PERF_BROWSER_PROFILES,
        _PERF_TEST_LOCATIONS=_PERF_TEST_LOCATIONS,
        _db_dsn_fn=_db_dsn_fn,
        _db_initialized=_db_initialized,
        _db_ready_fn=_db_ready_fn,
        _job_lock=_job_lock,
        _job_store=_job_store,
        audit_log_memory=audit_log_memory,
        enforce_rate_limit=enforce_rate_limit,
        seo_analyses_memory=seo_analyses_memory,
    )
    health.register(router, runtime)
    on_page_analyze.register(router, runtime)
    linkbuilding_analyze.register(router, runtime)
    vso_optimize.register(router, runtime)
    local_seo_optimize.register(router, runtime)
    cxao_analyze.register(router, runtime)
    performance_audit.register(router, runtime)
    performance_alert_events.register(router, runtime)
    agent_run.register(router, runtime)
    competitor_analyze.register(router, runtime)
    agency_platform_analyze.register(router, runtime)
    planner.register(router, runtime)
    backlink_intelligence_analyze.register(router, runtime)
    return router
