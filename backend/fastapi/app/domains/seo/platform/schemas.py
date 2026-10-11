"""SEO Platform request contracts."""

from __future__ import annotations


from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from typing import Any


class KeywordResearchReq(BaseModel):
    seed_keyword: str = Field(..., min_length=1, max_length=200)
    domain: str = ""
    country: str = "US"
    count: int = Field(default=20, ge=1, le=100)


class OnPageReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="", max_length=10000)
    focus_keyword: str = Field(default="", max_length=200)
    keyword: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def _resolve_focus_keyword(self) -> OnPageReq:
        kw = self.focus_keyword.strip() or self.keyword.strip()
        if not kw:
            raise ValueError("focus_keyword or keyword is required")
        self.focus_keyword = kw
        return self


class TechnicalAuditReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    issues_raw: list[dict[str, Any]] = []
    sitemap_url: str = Field(default="", max_length=500)
    crawl_depth: int = Field(default=3, ge=1, le=10)
    check_mobile_friendly: bool = True
    check_core_web_vitals: bool = True


class SchemaGenReq(BaseModel):
    schema_type: str = "Article"
    content: str = Field(default="", max_length=5000)
    url: str = ""
    page_url: str = ""

    @model_validator(mode="after")
    def _normalize_schema(self) -> SchemaGenReq:
        if self.page_url.strip() and (not self.url.strip()):
            self.url = self.page_url.strip()
        if not self.content.strip():
            if self.url.strip():
                self.content = f"Generate {self.schema_type} schema for {self.url}"
            else:
                raise ValueError("content or page_url is required")
        return self


class LinkBuildingReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=200)
    competitors: list[str] = Field(default_factory=list)
    niche: str = ""
    target_keywords: list[str] = Field(default_factory=list, max_length=20)
    opportunity_types: list[str] = Field(default_factory=list, max_length=12)


class ContentBriefReq(BaseModel):
    topic: str = Field(..., min_length=1, max_length=300)
    keywords: list[str] = []
    word_count: int = Field(default=1500, ge=300, le=10000)
    audience: str = ""


class AIWriterReq(BaseModel):
    topic: str = Field(..., min_length=1, max_length=300)
    keywords: list[str] = []
    word_count: int = Field(default=1200, ge=300, le=5000)
    tone: str = "professional"
    brief: str = ""


class GEOReq(BaseModel):
    content: str = Field(..., max_length=8000)
    topic: str = Field(..., max_length=300)
    target_engines: list[str] = ["ChatGPT", "Perplexity", "Gemini", "Google AI Overview"]
    ai_model: str = Field(default="deepseek-r1:8b", max_length=100)
    rag_enabled: bool = True
    serp_context: str = Field(default="", max_length=3000)
    site_content_context: str = Field(default="", max_length=3000)


class AEOReq(BaseModel):
    content: str = Field(..., max_length=8000)
    topic: str = Field(..., max_length=300)
    target_questions: list[str] = []
    entity_targets: list[str] = Field(default_factory=list, max_length=20)
    schema_types: list[str] = Field(default_factory=lambda: ["FAQPage", "HowTo", "QAPage"], max_length=10)
    use_openlens: bool = True
    use_playwright_validation: bool = True
    retrieval_framework: str = Field(default="llamaindex", max_length=100)


class AIOReq(BaseModel):
    content: str = Field(..., max_length=8000)
    topic: str = Field(default="", max_length=300)


class LLMOReq(BaseModel):
    brand: str = Field(..., max_length=200)
    domain: str = ""
    key_claims: list[str] = []
    competitors: list[str] = []


class VSOReq(BaseModel):
    content: str = Field(..., max_length=8000)
    topic: str = Field(..., max_length=300)
    local_area: str = ""


class SXOReq(BaseModel):
    url: str = Field(..., max_length=500)
    content: str = Field(default="", max_length=8000)
    keywords: list[str] = []


class GXOReq(BaseModel):
    content: str = Field(..., max_length=8000)
    topic: str = Field(..., max_length=300)
    url: str = ""


class EEATReq(BaseModel):
    content: str = Field(..., max_length=8000)
    author_bio: str = ""
    domain: str = ""
    niche: str = ""


class EntityReq(BaseModel):
    content: str = Field(..., max_length=8000)
    topic: str = Field(default="", max_length=300)


class LocalSEOReq(BaseModel):
    business_name: str = Field(..., max_length=200)
    category: str = ""
    location: str = ""
    website: str = ""
    description: str = Field(default="", max_length=2000)


class VideoSEOReq(BaseModel):
    title: str = Field(..., max_length=300)
    description: str = Field(default="", max_length=5000)
    transcript: str = Field(default="", max_length=10000)
    platform: str = "youtube"
    keywords: list[str] = []


class InternationalMultilingualReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    locales: list[str] = Field(default_factory=list, max_length=15)
    current_hreflang_map: str = Field(default="", max_length=3000)
    notes: str = Field(default="", max_length=1000)


class SiteMigrationReq(BaseModel):
    source_domain: str = Field(..., min_length=1, max_length=300)
    target_domain: str = Field(..., min_length=1, max_length=300)
    sample_urls: list[str] = Field(default_factory=list, max_length=20)
    launch_window: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=1000)


class RevenueAttributionReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    channels: list[str] = Field(default_factory=list, max_length=12)
    conversion_events: list[str] = Field(default_factory=list, max_length=12)
    revenue_window_days: int = Field(default=30, ge=1, le=365)
    notes: str = Field(default="", max_length=1000)


class GrowthPlaybooksReq(BaseModel):
    objective: str = Field(..., min_length=1, max_length=300)
    domain: str = Field(default="", max_length=300)
    target_channels: list[str] = Field(default_factory=list, max_length=12)
    weekly_capacity_hours: int = Field(default=20, ge=1, le=200)
    notes: str = Field(default="", max_length=1000)


class TrustRiskGovernanceReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    policy_scope: str = Field(default="seo-and-ai", max_length=200)
    controls: list[str] = Field(default_factory=list, max_length=20)
    incidents_last_90d: int = Field(default=0, ge=0, le=1000)
    notes: str = Field(default="", max_length=1000)


class MultiChannelActivationReq(BaseModel):
    campaign_name: str = Field(..., min_length=1, max_length=300)
    primary_offer: str = Field(default="", max_length=300)
    channels: list[str] = Field(default_factory=list, max_length=12)
    audience_segments: list[str] = Field(default_factory=list, max_length=12)
    notes: str = Field(default="", max_length=1000)


class CxaoReq(BaseModel):
    assistant_surface: str = Field(default="chat_assistant", max_length=120)
    primary_intent: str = Field(..., min_length=1, max_length=300)
    conversation_context: str = Field(..., min_length=1, max_length=4000)
    success_criteria: list[str] = Field(default_factory=list, max_length=12)
    ai_model: str = Field(default="deepseek-r1:8b", max_length=100)
    rag_enabled: bool = True
    chat_ui_framework: str = Field(default="nextjs", max_length=100)
    posthog_enabled: bool = True
    posthog_events: list[str] = Field(default_factory=list, max_length=20)


class SeoAbTestingReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    hypothesis: str = Field(..., min_length=1, max_length=500)
    primary_metric: str = Field(default="conversion_rate", max_length=120)
    variant_a: str = Field(..., min_length=1, max_length=2000)
    variant_b: str = Field(..., min_length=1, max_length=2000)
    test_duration_days: int = Field(default=21, ge=7, le=90)
    notes: str = Field(default="", max_length=1000)
    feature_flag_provider: str = Field(default="posthog", max_length=120)
    experiment_platform: str = Field(default="posthog", max_length=120)
    ai_analyst_model: str = Field(default="deepseek-r1:8b", max_length=100)
    variant_payloads: list[dict[str, Any]] = Field(default_factory=list, max_length=10)


class ProgrammaticSEOReq(BaseModel):
    template_topic: str = Field(default="", max_length=300)
    variable_sets: list[dict[str, str]] = Field(default_factory=list)
    page_count: int = Field(default=10, ge=1, le=100)
    url_template: str = Field(default="", max_length=500)
    title_template: str = Field(default="", max_length=500)
    meta_description_template: str = Field(default="", max_length=1000)
    variables: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_template_source(self) -> ProgrammaticSEOReq:
        if not self.template_topic.strip() and (not self.url_template.strip()) and (not self.title_template.strip()):
            raise ValueError("template_topic, url_template, or title_template is required")
        return self


class EcommerceSEOReq(BaseModel):
    product_name: str = Field(..., max_length=300)
    category: str = ""
    description: str = Field(default="", max_length=3000)
    keywords: list[str] = []


class AgentRunReq(BaseModel):
    goal: str = Field(..., min_length=5, max_length=1000)
    domain: str = ""
    workspace_id: str = ""


class PlannerExecuteReq(BaseModel):
    goal: str = Field(..., min_length=5, max_length=1000)
    domain: str = ""
    primary_keyword: str = Field(default="", max_length=200)
    market: str = Field(default="", max_length=200)


class PlannerExecuteAllReq(BaseModel):
    goal: str = Field(..., min_length=5, max_length=1000)
    domain: str = ""
    primary_keyword: str = Field(default="", max_length=200)
    market: str = Field(default="", max_length=200)
    include_groups: list[str] = Field(default_factory=list, max_length=20)
    exclude_module_keys: list[str] = Field(default_factory=list, max_length=62)


class PerformanceAuditReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    target_device: str = Field(default="mobile", max_length=20)
    target_region: str = Field(default="lhr1", max_length=20)
    connection: str = Field(default="4g", max_length=20)
    browser: str = Field(default="chrome", max_length=20)
    include_video: bool = True
    adblock_enabled: bool = False
    capture_har: bool = True
    require_live_providers: bool = False
    notes: str = Field(default="", max_length=1000)


class PerformanceAutoFixReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    candidates: list[dict] = Field(default_factory=list)


class PerformanceRumIngestReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    page_url: str = Field(default="", max_length=500)
    metric_name: str = Field(..., min_length=1, max_length=100)
    value: float = Field(..., ge=0)
    rating: str = Field(default="", max_length=40)
    delta: float = Field(default=0.0)
    metric_id: str = Field(default="", max_length=200)
    navigation_type: str = Field(default="", max_length=40)
    session_id: str = Field(default="", max_length=100)
    device_type: str = Field(default="", max_length=40)
    effective_connection_type: str = Field(default="", max_length=40)
    country: str = Field(default="", max_length=80)
    region: str = Field(default="", max_length=120)
    isp: str = Field(default="", max_length=120)
    user_agent: str = Field(default="", max_length=500)


class PerformanceMonitorCreateReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    name: str = Field(default="Primary Monitor", min_length=1, max_length=120)
    schedule: str = Field(default="daily", max_length=40)
    target_device: str = Field(default="mobile", max_length=20)
    target_region: str = Field(default="lhr1", max_length=20)
    connection: str = Field(default="4g", max_length=20)
    browser: str = Field(default="chrome", max_length=20)
    include_video: bool = True
    adblock_enabled: bool = False
    capture_har: bool = True
    alerts_enabled: bool = True
    alert_channels: list[str] = Field(default_factory=lambda: ["email"])
    alert_targets: list[str] = Field(default_factory=list)
    alert_lcp_ms_threshold: int = Field(default=2500, ge=500, le=20000)
    alert_inp_ms_threshold: int = Field(default=200, ge=50, le=5000)
    alert_cls_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    notes: str = Field(default="", max_length=1000)


class PerformanceReportShareReq(BaseModel):
    expires_hours: int = Field(default=168, ge=1, le=720)
    visibility: str = Field(default="token", max_length=20)


class PerformanceCompareReq(BaseModel):
    baseline_analysis_id: str = Field(..., min_length=1, max_length=120)
    candidate_analysis_id: str = Field(..., min_length=1, max_length=120)


class AccessibilityAuditReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    standard: str = Field(default="WCAG2.1AA", max_length=30)
    notes: str = Field(default="", max_length=1000)


class MediaSeoAuditReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    check_compression: bool = Field(default=True)
    notes: str = Field(default="", max_length=1000)


class SocialSeoAuditReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    platforms: list[str] = Field(default_factory=lambda: ["twitter", "facebook", "linkedin"])
    notes: str = Field(default="", max_length=1000)


class LandingPageGenerateReq(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    target_keyword: str = Field(..., min_length=1, max_length=200)
    audience: str = Field(default="general", max_length=200)
    schema_types: list[str] = Field(default_factory=lambda: ["Product", "FAQPage"])
    notes: str = Field(default="", max_length=1000)


class SecuritySeoAuditReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    check_cloaking: bool = Field(default=True)
    notes: str = Field(default="", max_length=1000)


class TopicalMapReq(BaseModel):
    seed_topic: str = Field(..., min_length=1, max_length=300)
    domain: str = Field(default="", max_length=300)
    depth: int = Field(default=2, ge=1, le=4)
    notes: str = Field(default="", max_length=1000)


class LogFileAnalysisReq(BaseModel):
    log_snippet: str = Field(..., min_length=1, max_length=5000)
    domain: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=1000)


class ReviewReputationReq(BaseModel):
    brand: str = Field(..., min_length=1, max_length=300)
    reviews_text: str = Field(default="", max_length=5000)
    platforms: list[str] = Field(default=["google", "trustpilot"])
    notes: str = Field(default="", max_length=1000)


class BrandVoiceReq(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    brand_name: str = Field(default="", max_length=300)
    tone: str = Field(default="professional", max_length=100)
    target_audience: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=1000)


class UxConversionReq(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    page_type: str = Field(default="landing", max_length=100)
    traffic_source: str = Field(default="organic", max_length=100)
    notes: str = Field(default="", max_length=1000)


class RagSearchReq(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    site_domain: str = Field(default="", max_length=300)
    content_corpus: str = Field(default="", max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)
    notes: str = Field(default="", max_length=1000)


class CompetitorIntelReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    competitors: list[str] = Field(default=[], max_length=10)
    target_keyword: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=1000)


class RealtimeMonitoringReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    tracked_queries: list[str] = Field(default_factory=list, max_length=15)
    lookback_hours: int = Field(default=24, ge=1, le=168)
    notes: str = Field(default="", max_length=1000)


class ContentAuditorReq(BaseModel):
    content: str = Field(default="", max_length=6000)
    source_url: str = Field(default="", max_length=500)
    url: str = Field(default="", max_length=500)
    topic: str = Field(default="", max_length=300)
    target_model: str = Field(default="gpt-4o|claude|gemini", max_length=200)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _normalize_content_auditor(self) -> ContentAuditorReq:
        if self.url.strip() and (not self.source_url.strip()):
            self.source_url = self.url.strip()
        if not self.content.strip():
            if self.source_url.strip():
                self.content = f"Content audit request for URL: {self.source_url}. Topic: {self.topic.strip() or 'general SEO content quality review'}."
            else:
                raise ValueError("content or url is required")
        return self


class KnowledgeGraphReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    seed_entities: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=1000)


class InternalLinkingReq(BaseModel):
    page_url: str = Field(default="", max_length=500)
    site_url: str = Field(default="", max_length=500)
    page_content: str = Field(default="", max_length=5000)
    target_urls: list[str] = Field(default_factory=list, max_length=30)
    url_list: list[str] = Field(default_factory=list, max_length=30)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _normalize_internal_linking(self) -> InternalLinkingReq:
        if self.site_url.strip() and (not self.page_url.strip()):
            self.page_url = self.site_url.strip()
        if self.url_list and (not self.target_urls):
            self.target_urls = self.url_list
        if not self.page_url.strip():
            raise ValueError("page_url or site_url is required")
        return self


class CrawlBudgetReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    sample_urls: list[str] = Field(default_factory=list, max_length=50)
    log_snippet: str = Field(default="", max_length=5000)
    notes: str = Field(default="", max_length=1000)


class NewsDiscoverReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    recent_headlines: list[str] = Field(default_factory=list, max_length=25)
    focus_topics: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=1000)


class AgencyPlatformReq(BaseModel):
    agency_name: str = Field(..., min_length=1, max_length=300)
    workspaces: list[str] = Field(default_factory=list, max_length=25)
    governance_focus: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=1000)


class IntegrationsAutomationReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    integrations: list[str] = Field(default_factory=list, max_length=30)
    automation_goals: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=1000)


class SeoAiCoreReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    primary_keyword: str = Field(..., min_length=1, max_length=200)
    business_goal: str = Field(default="growth", max_length=200)
    content_excerpt: str = Field(default="", max_length=4000)
    notes: str = Field(default="", max_length=1000)


class SageoReq(BaseModel):
    topic: str = Field(..., min_length=1, max_length=300)
    search_intent: str = Field(default="informational", max_length=120)
    source_material: str = Field(default="", max_length=4000)
    target_engines: list[str] = Field(
        default_factory=lambda: ["Google AI Overview", "ChatGPT", "Perplexity"], max_length=10
    )
    notes: str = Field(default="", max_length=1000)


class PeaoReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    primary_keyword: str = Field(..., min_length=1, max_length=200)
    recent_signals: str = Field(default="", max_length=3000)
    forecast_horizon_days: int = Field(default=30, ge=7, le=180)
    notes: str = Field(default="", max_length=1000)


class MsvoReq(BaseModel):
    brand: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=300)
    target_surfaces: list[str] = Field(
        default_factory=lambda: ["google", "chatgpt", "perplexity", "linkedin"], max_length=12
    )
    owned_channels: list[str] = Field(default_factory=list, max_length=12)
    notes: str = Field(default="", max_length=1000)


class DaeoReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    protocol_targets: list[str] = Field(
        default_factory=lambda: ["self_hosted_search", "federated_index", "knowledge_api"], max_length=12
    )
    canonical_facts: list[str] = Field(default_factory=list, max_length=20)
    federation_notes: str = Field(default="", max_length=3000)
    notes: str = Field(default="", max_length=1000)


class BacklinkIntelligenceReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    competitor_domains: list[str] = Field(default_factory=list, max_length=12)
    link_analysis_depth: str = Field(default="standard", max_length=20)
    include_topical_clusters: bool = Field(default=True)
    notes: str = Field(default="", max_length=1000)


class RankTrackingReq(BaseModel):
    domain: str = Field(..., min_length=1, max_length=300)
    tracked_keywords: list[str] = Field(default_factory=list, max_length=25)
    historical_lookback_days: int = Field(default=90, ge=7, le=365)
    include_competitor_tracking: bool = Field(default=False)
    competitor_domains: list[str] = Field(default_factory=list, max_length=8)
    notes: str = Field(default="", max_length=1000)


class ContentCreationBloggingReq(BaseModel):
    topic: str = Field(..., min_length=1, max_length=300)
    content_pillars: list[str] = Field(default_factory=list, max_length=12)
    target_keywords: list[str] = Field(default_factory=list, max_length=25)
    ai_model: str = Field(default="deepseek-r1:8b", max_length=50)
    word_count_target: int = Field(default=2000, ge=500, le=8000)
    include_multimedia_plan: bool = Field(default=True)
    publication_frequency: str = Field(default="weekly", max_length=30)
    seo_brief: str = Field(default="", max_length=3000)
    notes: str = Field(default="", max_length=1000)
