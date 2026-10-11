import psycopg
import httpx
import asyncio
import subprocess

"""Seo/Platform HTTP composition and legacy import exports."""

from .constants import _shared_job_store
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    health,
    on_page_analyze,
    linkbuilding_analyze,
    vso_optimize,
    local_seo_optimize,
    cxao_analyze,
    performance_audit,
    performance_alert_events,
    agent_run,
    competitor_analyze,
    agency_platform_analyze,
    backlink_intelligence_analyze,
)
from .services.get_shared_job_store import get_shared_job_store as get_shared_job_store
from .services.get_shared_job_store import _strict_no_mock_mode as _strict_no_mock_mode
from .services.get_shared_job_store import _upstash_rest_base_url as _upstash_rest_base_url
from .services.get_shared_job_store import _upstash_rest_token as _upstash_rest_token
from .services.get_shared_job_store import _seo_analysis_dist_cache_enabled as _seo_analysis_dist_cache_enabled
from .services.get_shared_job_store import _upstash_command as _upstash_command
from .services.get_shared_job_store import _seo_analysis_cache_key as _seo_analysis_cache_key
from .services.get_shared_job_store import _perf_int as _perf_int
from .services.get_shared_job_store import _perf_float as _perf_float
from .services.get_shared_job_store import _perf_percentile as _perf_percentile
from .services.get_shared_job_store import _normalize_perf_metric_name as _normalize_perf_metric_name
from .services.get_shared_job_store import _performance_score_from_field as _performance_score_from_field
from .services.get_shared_job_store import _lighthouse_command_candidates as _lighthouse_command_candidates
from .services.get_shared_job_store import _run_lighthouse_sync as _run_lighthouse_sync
from .services.get_shared_job_store import _run_lighthouse as _run_lighthouse
from .services.get_shared_job_store import _run_pagespeed as _run_pagespeed
from .services.get_shared_job_store import _run_crux as _run_crux
from .services.get_shared_job_store import _run_webpagetest as _run_webpagetest
from .services.get_shared_job_store import _run_http_probe as _run_http_probe
from .services.get_shared_job_store import _run_network_probe_sync as _run_network_probe_sync
from .services.get_shared_job_store import _run_network_probe as _run_network_probe
from .services.get_shared_job_store import _extract_scores as _extract_scores
from .services.get_shared_job_store import _extract_core_vitals as _extract_core_vitals
from .services.get_shared_job_store import _clean as _clean
from .services.extract_waterfall import _extract_waterfall as _extract_waterfall
from .services.extract_waterfall import _extract_filmstrip as _extract_filmstrip
from .services.extract_waterfall import _extract_crux_field as _extract_crux_field
from .services.extract_waterfall import _run_free_performance_stack as _run_free_performance_stack
from .services.extract_waterfall import _ollama_json as _ollama_json
from .services.rollup_performance_rum import _rollup_performance_rum as _rollup_performance_rum
from .schemas import TrustRiskGovernanceReq as TrustRiskGovernanceReq
from .schemas import SiteMigrationReq as SiteMigrationReq
from .schemas import EntityReq as EntityReq
from .schemas import LocalSEOReq as LocalSEOReq
from .schemas import CrawlBudgetReq as CrawlBudgetReq
from .schemas import AgencyPlatformReq as AgencyPlatformReq
from .schemas import EcommerceSEOReq as EcommerceSEOReq
from .schemas import BacklinkIntelligenceReq as BacklinkIntelligenceReq
from .schemas import AIWriterReq as AIWriterReq
from .schemas import PlannerExecuteAllReq as PlannerExecuteAllReq
from .schemas import MediaSeoAuditReq as MediaSeoAuditReq
from .schemas import PlannerExecuteReq as PlannerExecuteReq
from .schemas import SchemaGenReq as SchemaGenReq
from .schemas import AgentRunReq as AgentRunReq
from .schemas import AEOReq as AEOReq
from .schemas import AccessibilityAuditReq as AccessibilityAuditReq
from .schemas import SeoAbTestingReq as SeoAbTestingReq
from .schemas import GXOReq as GXOReq
from .schemas import LLMOReq as LLMOReq
from .schemas import ProgrammaticSEOReq as ProgrammaticSEOReq
from .schemas import LogFileAnalysisReq as LogFileAnalysisReq
from .schemas import UxConversionReq as UxConversionReq
from .schemas import KeywordResearchReq as KeywordResearchReq
from .schemas import ContentBriefReq as ContentBriefReq
from .schemas import EEATReq as EEATReq
from .schemas import GrowthPlaybooksReq as GrowthPlaybooksReq
from .schemas import PerformanceAuditReq as PerformanceAuditReq
from .schemas import PerformanceCompareReq as PerformanceCompareReq
from .schemas import ContentCreationBloggingReq as ContentCreationBloggingReq
from .schemas import CxaoReq as CxaoReq
from .schemas import InternationalMultilingualReq as InternationalMultilingualReq
from .schemas import MultiChannelActivationReq as MultiChannelActivationReq
from .schemas import LinkBuildingReq as LinkBuildingReq
from .schemas import PerformanceMonitorCreateReq as PerformanceMonitorCreateReq
from .schemas import TopicalMapReq as TopicalMapReq
from .schemas import ContentAuditorReq as ContentAuditorReq
from .schemas import SecuritySeoAuditReq as SecuritySeoAuditReq
from .schemas import SageoReq as SageoReq
from .schemas import PeaoReq as PeaoReq
from .schemas import DaeoReq as DaeoReq
from .schemas import RankTrackingReq as RankTrackingReq
from .schemas import TechnicalAuditReq as TechnicalAuditReq
from .schemas import VSOReq as VSOReq
from .schemas import InternalLinkingReq as InternalLinkingReq
from .schemas import SeoAiCoreReq as SeoAiCoreReq
from .schemas import KnowledgeGraphReq as KnowledgeGraphReq
from .schemas import VideoSEOReq as VideoSEOReq
from .schemas import RealtimeMonitoringReq as RealtimeMonitoringReq
from .schemas import CompetitorIntelReq as CompetitorIntelReq
from .schemas import IntegrationsAutomationReq as IntegrationsAutomationReq
from .schemas import MsvoReq as MsvoReq
from .schemas import PerformanceRumIngestReq as PerformanceRumIngestReq
from .schemas import BrandVoiceReq as BrandVoiceReq
from .schemas import OnPageReq as OnPageReq
from .schemas import RagSearchReq as RagSearchReq
from .schemas import AIOReq as AIOReq
from .schemas import ReviewReputationReq as ReviewReputationReq
from .schemas import SXOReq as SXOReq
from .schemas import PerformanceAutoFixReq as PerformanceAutoFixReq
from .schemas import RevenueAttributionReq as RevenueAttributionReq
from .schemas import LandingPageGenerateReq as LandingPageGenerateReq
from .schemas import NewsDiscoverReq as NewsDiscoverReq
from .schemas import PerformanceReportShareReq as PerformanceReportShareReq
from .schemas import SocialSeoAuditReq as SocialSeoAuditReq
from .schemas import GEOReq as GEOReq
from .constants import SEO_DEFAULT_MODEL as SEO_DEFAULT_MODEL
from .constants import _STRICT_NO_MOCK_FALSY as _STRICT_NO_MOCK_FALSY
from .constants import _MULTI_CHANNEL_ACTIVATION_SYS as _MULTI_CHANNEL_ACTIVATION_SYS
from .constants import SEO_ANALYSIS_CACHE_TTL_SEC as SEO_ANALYSIS_CACHE_TTL_SEC
from .constants import _PERFORMANCE_SYS as _PERFORMANCE_SYS
from .constants import _AGENCY_PLATFORM_SYS as _AGENCY_PLATFORM_SYS
from .constants import _SOCIAL_SEO_SYS as _SOCIAL_SEO_SYS
from .constants import _CXAO_SYS as _CXAO_SYS
from .constants import _CONTENT_CREATION_BLOGGING_SYS as _CONTENT_CREATION_BLOGGING_SYS
from .constants import SEO_OLLAMA_CACHE_TTL_SEC as SEO_OLLAMA_CACHE_TTL_SEC
from .constants import _ONPAGE_SYS as _ONPAGE_SYS
from .constants import _GEO_SYS as _GEO_SYS
from .constants import _TOPICAL_MAP_SYS as _TOPICAL_MAP_SYS
from .constants import _UX_CONVERSION_SYS as _UX_CONVERSION_SYS
from .constants import _ANALYTICS_REPORTING_SYS as _ANALYTICS_REPORTING_SYS
from .constants import _LANDING_SYS as _LANDING_SYS
from .constants import _KNOWLEDGE_GRAPH_SYS as _KNOWLEDGE_GRAPH_SYS
from .constants import _REALTIME_MONITORING_SYS as _REALTIME_MONITORING_SYS
from .constants import _SAGEO_SYS as _SAGEO_SYS
from .constants import _ECOMMERCE_SYS as _ECOMMERCE_SYS
from .constants import _AEO_SYS as _AEO_SYS
from .constants import _LOG_FILE_SYS as _LOG_FILE_SYS
from .constants import _VSO_SYS as _VSO_SYS
from .constants import _GROWTH_PLAYBOOKS_SYS as _GROWTH_PLAYBOOKS_SYS
from .constants import _MEDIA_SEO_SYS as _MEDIA_SEO_SYS
from .constants import _BLOCKED as _BLOCKED
from .constants import _RANK_TRACKING_SYS as _RANK_TRACKING_SYS
from .constants import SEO_PERF_FREE_TIMEOUT_SEC as SEO_PERF_FREE_TIMEOUT_SEC
from .constants import _MSVO_SYS as _MSVO_SYS
from .constants import _BRAND_VOICE_SYS as _BRAND_VOICE_SYS
from .constants import _CRAWL_BUDGET_SYS as _CRAWL_BUDGET_SYS
from .constants import SEO_PERF_LIGHTHOUSE_PATH as SEO_PERF_LIGHTHOUSE_PATH
from .constants import _BRIEF_SYS as _BRIEF_SYS
from .constants import _shared_job_store as _shared_job_store
from .constants import OLLAMA_BASE_URL as OLLAMA_BASE_URL
from .constants import _GXO_SYS as _GXO_SYS
from .constants import _TECHNICAL_SYS as _TECHNICAL_SYS
from .constants import SEO_OLLAMA_CACHE_MAX_ENTRIES as SEO_OLLAMA_CACHE_MAX_ENTRIES
from .constants import logger as logger
from .constants import OLLAMA_TIMEOUT as OLLAMA_TIMEOUT
from .constants import _WRITER_SYS as _WRITER_SYS
from .constants import SEO_PERF_CRUX_API_KEY as SEO_PERF_CRUX_API_KEY
from .constants import _KEYWORD_SYS as _KEYWORD_SYS
from .constants import _INTERNAL_LINKING_SYS as _INTERNAL_LINKING_SYS
from .constants import _AGENT_SYS as _AGENT_SYS
from .constants import _EEAT_SYS as _EEAT_SYS
from .constants import _SEO_AI_CORE_SYS as _SEO_AI_CORE_SYS
from .constants import _REVIEW_REPUTATION_SYS as _REVIEW_REPUTATION_SYS
from .constants import _BACKLINK_INTELLIGENCE_SYS as _BACKLINK_INTELLIGENCE_SYS
from .constants import SEO_MODULE_COUNT as SEO_MODULE_COUNT
from .constants import _ACCESSIBILITY_SYS as _ACCESSIBILITY_SYS
from .constants import _NEWS_DISCOVER_SYS as _NEWS_DISCOVER_SYS
from .constants import _LOCAL_SYS as _LOCAL_SYS
from .constants import _REVENUE_ATTRIBUTION_SYS as _REVENUE_ATTRIBUTION_SYS
from .constants import _SITE_MIGRATION_SYS as _SITE_MIGRATION_SYS
from .constants import _LINKBUILDING_SYS as _LINKBUILDING_SYS
from .constants import SEO_UPSTASH_TIMEOUT_SEC as SEO_UPSTASH_TIMEOUT_SEC
from .constants import _PROGRAMMATIC_SYS as _PROGRAMMATIC_SYS
from .constants import SEO_PERF_WEBPAGETEST_API_KEY as SEO_PERF_WEBPAGETEST_API_KEY
from .constants import _VIDEO_SYS as _VIDEO_SYS
from .constants import _COMPETITOR_INTEL_SYS as _COMPETITOR_INTEL_SYS
from .constants import _INTERNATIONAL_MULTILINGUAL_SYS as _INTERNATIONAL_MULTILINGUAL_SYS
from .constants import _ENTITY_SYS as _ENTITY_SYS
from .constants import _RAG_SEARCH_SYS as _RAG_SEARCH_SYS
from .constants import _DAEO_SYS as _DAEO_SYS
from .constants import _SECURITY_SEO_SYS as _SECURITY_SEO_SYS
from .constants import _SCHEMA_SYS as _SCHEMA_SYS
from .constants import _INTEGRATIONS_AUTOMATION_SYS as _INTEGRATIONS_AUTOMATION_SYS
from .constants import SEO_PERF_PSI_API_KEY as SEO_PERF_PSI_API_KEY
from .constants import _SEO_AB_TESTING_SYS as _SEO_AB_TESTING_SYS
from .constants import _TRUST_RISK_GOVERNANCE_SYS as _TRUST_RISK_GOVERNANCE_SYS
from .constants import _PEAO_SYS as _PEAO_SYS
from .constants import _SXO_SYS as _SXO_SYS
from .constants import _AIO_SYS as _AIO_SYS
from .constants import _LLMO_SYS as _LLMO_SYS
from .constants import _OLLAMA_INFLIGHT as _OLLAMA_INFLIGHT
from .constants import _OLLAMA_CACHE_LOCK as _OLLAMA_CACHE_LOCK
from .constants import _OLLAMA_CACHE as _OLLAMA_CACHE
from .constants import _CONTENT_AUDITOR_SYS as _CONTENT_AUDITOR_SYS
from .constants import SEO_PERF_CHROME_PATH as SEO_PERF_CHROME_PATH
from ....deps import AuthContext
from ....deps import require_auth
from ....domains.seo.services.seo_ab_testing_service import analyze_seo_ab_testing
from ....domains.seo.services.seo_accessibility_service import audit_accessibility
from ....domains.seo.services.seo_aeo_service import analyze_aeo_optimize
from ....domains.seo.services.seo_agency_platform_service import analyze_agency_platform
from ....domains.seo.services.seo_agent_service import analyze_agent_plan
from ....domains.seo.services.seo_ai_service import analyze_seo_ai_core
from ....domains.seo.services.seo_aio_service import analyze_aio_score
from ....domains.seo.services.seo_analytics_reporting_service import generate_analytics_report
from ....domains.seo.services.seo_backlink_intelligence_service import analyze_backlink_intelligence
from ....domains.seo.services.seo_brand_voice_service import rewrite_brand_voice
from ....domains.seo.services.seo_competitor_service import analyze_competitor_intel
from ....domains.seo.services.seo_content_auditor_service import analyze_content_auditor
from ....domains.seo.services.seo_content_brief_service import generate_content_brief
from ....domains.seo.services.seo_content_creation_blogging_service import plan_content_creation_blogging
from ....domains.seo.services.seo_content_writer_service import write_seo_article
from ....domains.seo.services.seo_crawl_budget_service import analyze_crawl_budget
from ....domains.seo.services.seo_cxao_service import analyze_cxao_experience
from ....domains.seo.services.seo_daeo_service import analyze_daeo_readiness
from ....domains.seo.services.seo_ecommerce_service import optimize_ecommerce_seo
from ....domains.seo.services.seo_eeat_service import analyze_eeat_score
from ....domains.seo.services.seo_entity_service import analyze_entity_seo
from ....domains.seo.services.seo_geo_service import analyze_geo_optimize
from ....domains.seo.services.seo_growth_playbooks_service import analyze_growth_playbooks
from ....domains.seo.services.seo_gxo_service import analyze_gxo_optimize
from ....domains.seo.services.seo_integrations_automation_service import analyze_integrations_automation
from ....domains.seo.services.seo_internal_linking_service import suggest_internal_linking
from ....domains.seo.services.seo_international_multilingual_service import analyze_international_multilingual
from ....domains.seo.services.seo_keyword_research_service import research_keywords
from ....domains.seo.services.seo_knowledge_graph_service import analyze_knowledge_graph
from ....domains.seo.services.seo_landing_service import generate_landing_page
from ....domains.seo.services.seo_linkbuilding_service import analyze_linkbuilding
from ....domains.seo.services.seo_llmo_service import analyze_llmo_brand
from ....domains.seo.services.seo_local_seo_service import optimize_local_seo
from ....domains.seo.services.seo_log_file_service import analyze_log_file
from ....domains.seo.services.seo_media_service import audit_media_seo
from ....domains.seo.seo_module_registry import SEO_MODULE_MAP
from ....domains.seo.seo_module_registry import SEO_MODULE_REGISTRY
from ....domains.seo.seo_module_registry import audit_ahrefs_core_tool_parity
from ....domains.seo.seo_module_registry import audit_seo_module_registry
from ....domains.seo.seo_module_registry import grouped_seo_modules
from ....domains.seo.services.seo_msvo_service import analyze_msvo_visibility
from ....domains.seo.services.seo_multi_channel_activation_service import analyze_multi_channel_activation
from ....domains.seo.services.seo_news_discover_service import analyze_news_discover
from ....domains.seo.services.seo_on_page_service import analyze_on_page
from ....domains.seo.services.seo_peao_service import analyze_peao_forecast
from ....domains.seo.services.seo_performance_service import apply_performance_auto_fix
from ....domains.seo.services.seo_planner_service import default_planner_workflow
from ....domains.seo.services.seo_planner_service import execute_planner
from ....domains.seo.services.seo_planner_service import execute_planner_all_modules
from ....domains.seo.services.seo_programmatic_service import generate_programmatic_seo
from ....domains.seo.services.seo_rag_search_service import query_rag_search
from ....domains.seo.services.seo_rank_tracking_service import analyze_rank_tracking
from ....domains.seo.services.seo_realtime_monitoring_service import analyze_realtime_monitoring
from ....domains.seo.services.seo_revenue_attribution_service import analyze_revenue_attribution
from ....domains.seo.services.seo_reviews_service import analyze_review_reputation
from ....domains.seo.services.seo_sageo_service import analyze_sageo_plan
from ....domains.seo.services.seo_schema_service import generate_schema_markup
from ....domains.seo.services.seo_security_service import audit_security_seo
from ....domains.seo.services.seo_site_migration_service import analyze_site_migration
from ....domains.seo.services.seo_social_service import audit_social_seo
from ....domains.seo.services.seo_sxo_service import analyze_sxo_experience
from ....domains.seo.services.seo_technical_audit_service import analyze_technical_audit
from ....domains.seo.services.seo_topical_map_service import build_topical_map
from ....domains.seo.services.seo_trust_risk_governance_service import analyze_trust_risk_governance
from ....domains.seo.services.seo_ux_service import audit_ux_conversion
from ....domains.seo.services.seo_video_seo_service import optimize_video_seo
from ....domains.seo.services.seo_vso_service import analyze_vso_optimize


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
    backlink_intelligence_analyze.register(router, runtime)
    return router
