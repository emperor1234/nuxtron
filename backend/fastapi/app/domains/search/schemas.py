"""Search automation request/response contracts."""

from pydantic import BaseModel
from pydantic import Field
from typing import Any


class CostSavingsCalculatorRequest(BaseModel):
    sites_count: int = Field(default=10, ge=1, le=10000)
    pages_per_site: int = Field(default=500, ge=1, le=5000000)
    monthly_deployments: int = Field(default=4, ge=1, le=1000)
    manual_minutes_per_page: float = Field(default=1.5, ge=0.05, le=120)
    hourly_rate_usd: float = Field(default=80.0, ge=1, le=10000)
    automation_coverage_pct: float = Field(default=85.0, ge=1, le=100)
    tool_monthly_cost_usd: float = Field(default=399.0, ge=0, le=1000000)


class AiSearchRevenueImpactRequest(BaseModel):
    monthly_sessions: int = Field(default=100000, ge=1, le=1000000000)
    current_ai_visibility_pct: float = Field(default=1.0, ge=0, le=100)
    target_ai_visibility_pct: float = Field(default=12.0, ge=0, le=100)
    ai_ctr_pct: float = Field(default=18.0, ge=0, le=100)
    conversion_rate_pct: float = Field(default=2.2, ge=0, le=100)
    avg_order_value_usd: float = Field(default=120.0, ge=0, le=1000000)
    gross_margin_pct: float = Field(default=65.0, ge=0, le=100)


class VendorStatus(BaseModel):
    key: str
    display_name: str
    category: str
    configured: bool
    mode: str


class SemrushFullAutomationRequest(BaseModel):
    seed_keyword: str = Field(min_length=2, max_length=200)
    your_domain: str = Field(min_length=3, max_length=253)
    competitor_domains: list[str] = Field(min_length=1, max_length=6)
    location: str = Field(default="United States", max_length=120)
    language: str = Field(default="en", max_length=10)
    include_questions: bool = Field(default=True)
    max_results: int = Field(default=30, ge=5, le=100)
    require_live_providers: bool = Field(
        default=False, description="If true, fail the run when keyword providers fall back to synthetic data."
    )


class SemrushProductionGateRequest(BaseModel):
    seed_keyword: str = Field(default="social media management", min_length=2, max_length=200)
    your_domain: str = Field(default="nuxtron.ai", min_length=3, max_length=253)
    competitor_domains: list[str] = Field(
        default_factory=lambda: ["semrush.com", "ahrefs.com"], min_length=1, max_length=6
    )
    max_results: int = Field(default=10, ge=5, le=100)


class SemrushProviderBootstrapRequest(BaseModel):
    providers: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Optional provider names to scope remediation; empty means all missing providers.",
    )
    include_configured: bool = Field(default=False)


class SemrushProviderProbeRequest(BaseModel):
    providers: list[str] = Field(
        default_factory=list, max_length=20, description="Provider keys to probe; empty probes all keyword providers."
    )
    include_unconfigured: bool = Field(
        default=False, description="If true, probe even when provider is not marked configured."
    )
    max_results: int = Field(default=5, ge=1, le=20)


class SemrushEnvTemplateRequest(BaseModel):
    include_optional: bool = Field(default=False)
    include_configured: bool = Field(default=False)


class AhrefsProductionGateRequest(BaseModel):
    seed_keyword: str = Field(default="seo analytics", min_length=2, max_length=200)
    your_domain: str = Field(default="nuxtron.ai", min_length=3, max_length=253)
    competitor_domains: list[str] = Field(
        default_factory=lambda: ["semrush.com", "moz.com"], min_length=1, max_length=6
    )
    max_results: int = Field(default=10, ge=5, le=100)


class AhrefsProviderBootstrapRequest(BaseModel):
    providers: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Optional provider names to scope remediation; empty means all missing providers.",
    )
    include_configured: bool = Field(default=False)


class AhrefsProviderProbeRequest(BaseModel):
    providers: list[str] = Field(
        default_factory=list, max_length=20, description="Provider keys to probe; empty probes all keyword providers."
    )
    include_unconfigured: bool = Field(
        default=False, description="If true, probe even when provider is not marked configured."
    )
    max_results: int = Field(default=5, ge=1, le=20)


class AhrefsEnvTemplateRequest(BaseModel):
    include_optional: bool = Field(default=False)
    include_configured: bool = Field(default=False)


class AhrefsFullAutomationRequest(BaseModel):
    seed_keyword: str = Field(min_length=2, max_length=200)
    your_domain: str = Field(min_length=3, max_length=253)
    competitor_domains: list[str] = Field(min_length=1, max_length=6)
    location: str = Field(default="United States", max_length=120)
    language: str = Field(default="en", max_length=10)
    include_questions: bool = Field(default=True)
    max_results: int = Field(default=30, ge=5, le=100)
    require_live_providers: bool = Field(
        default=False, description="If true, fail the run when keyword providers fall back to synthetic data."
    )


class SurferProductionGateRequest(BaseModel):
    seed_keyword: str = Field(default="social media management", min_length=2, max_length=200)
    your_domain: str = Field(default="nuxtron.ai", min_length=3, max_length=253)
    competitor_domains: list[str] = Field(
        default_factory=lambda: ["semrush.com", "ahrefs.com"], min_length=1, max_length=6
    )
    max_results: int = Field(default=10, ge=5, le=100)


class SurferProviderBootstrapRequest(BaseModel):
    providers: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Optional provider names to scope remediation; empty means all missing providers.",
    )
    include_configured: bool = Field(default=False)


class SurferProviderProbeRequest(BaseModel):
    providers: list[str] = Field(
        default_factory=list, max_length=20, description="Provider keys to probe; empty probes all keyword providers."
    )
    include_unconfigured: bool = Field(
        default=False, description="If true, probe even when provider is not marked configured."
    )
    max_results: int = Field(default=5, ge=1, le=20)


class SurferEnvTemplateRequest(BaseModel):
    include_optional: bool = Field(default=False)
    include_configured: bool = Field(default=False)


class SurferFullAutomationRequest(BaseModel):
    seed_keyword: str = Field(min_length=2, max_length=200)
    your_domain: str = Field(min_length=3, max_length=253)
    competitor_domains: list[str] = Field(min_length=1, max_length=6)
    location: str = Field(default="United States", max_length=120)
    language: str = Field(default="en", max_length=10)
    include_questions: bool = Field(default=True)
    max_results: int = Field(default=30, ge=5, le=100)
    require_live_providers: bool = Field(
        default=False, description="If true, fail the run when keyword providers fall back to synthetic data."
    )


class FraseProductionGateRequest(SurferProductionGateRequest):
    """Frase production gate input model."""


class FraseProviderBootstrapRequest(SurferProviderBootstrapRequest):
    """Frase provider bootstrap input model."""


class FraseProviderProbeRequest(SurferProviderProbeRequest):
    """Frase provider probe input model."""


class FraseEnvTemplateRequest(SurferEnvTemplateRequest):
    """Frase env template input model."""


class FraseFullAutomationRequest(SurferFullAutomationRequest):
    """Frase full automation input model."""


class SitebulbProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    primary_domain: str = Field(min_length=3, max_length=253)
    crawl_urls: list[str] = Field(default_factory=list, max_length=200)
    render_javascript: bool = Field(default=True)
    emulate_mobile: bool = Field(default=False)
    max_urls: int = Field(default=10000, ge=100, le=5000000)
    default_seed_keyword: str = Field(default="social media management", min_length=2, max_length=200)
    default_competitors: list[str] = Field(default_factory=lambda: ["semrush.com", "ahrefs.com"], max_length=6)


class SitebulbProjectRunRequest(BaseModel):
    seed_keyword: str | None = Field(default=None, min_length=2, max_length=200)
    competitor_domains: list[str] | None = Field(default=None, max_length=6)
    max_results: int = Field(default=20, ge=5, le=100)
    require_live_providers: bool = Field(default=False)


class SitebulbScheduleCreateRequest(BaseModel):
    project_id: str = Field(min_length=3, max_length=120)
    cron: str = Field(default="0 3 * * 1", min_length=5, max_length=120)
    enabled: bool = Field(default=True)


class SitebulbScheduleExecuteRequest(BaseModel):
    due_only: bool = Field(default=False)


class SitebulbEnvTemplateRequest(BaseModel):
    include_optional: bool = Field(default=False)
    include_configured: bool = Field(default=False)


class SitebulbRemediationBundleRequest(BaseModel):
    include_optional: bool = Field(default=False)
    include_configured: bool = Field(default=False)
    top_steps: int = Field(default=10, ge=1, le=100)


class SliceProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    primary_domain: str = Field(min_length=3, max_length=253)
    competitor_domains: list[str] = Field(default_factory=lambda: ["semrush.com", "ahrefs.com"], max_length=6)
    default_seed_keyword: str = Field(default="social media management", min_length=2, max_length=200)


class SliceProjectRunRequest(BaseModel):
    seed_keyword: str | None = Field(default=None, min_length=2, max_length=200)
    max_results: int = Field(default=20, ge=5, le=100)
    require_live_providers: bool = Field(default=False)
    include_assist_summary: bool = Field(default=False)


class SliceScheduleCreateRequest(BaseModel):
    project_id: str = Field(min_length=3, max_length=120)
    cron: str = Field(default="0 4 * * 1", min_length=5, max_length=120)
    enabled: bool = Field(default=True)


class SliceScheduleExecuteRequest(BaseModel):
    due_only: bool = Field(default=False)


class SliceAssistRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=5000)
    project_id: str | None = Field(default=None, max_length=120)
    include_vendor_context: bool = Field(default=True)


class SliceWiringApplyRequest(BaseModel):
    providers: list[str] = Field(default_factory=list, max_length=100)
    include_all_missing: bool = Field(default=True)
    include_optional_auth: bool = Field(default=True)


class ClearscopeContentReportCreateRequest(BaseModel):
    keyword: str = Field(min_length=2, max_length=200)
    locale: str = Field(default="en", max_length=10)
    region: str = Field(default="us", max_length=20)
    content_type: str = Field(default="article", max_length=40)


class ShopifyMagicSidekickRequest(BaseModel):
    objective: str = Field(min_length=2, max_length=200)
    prompt: str = Field(min_length=2, max_length=5000)
    include_shop_snapshot: bool = Field(default=True)


class ShopifyMagicImageRequest(BaseModel):
    image_url: str = Field(min_length=8, max_length=2048)
    transformation: str = Field(min_length=2, max_length=120)
    product_title: str = Field(min_length=2, max_length=200)
    brand_tone: str = Field(default="modern", max_length=200)
    output_size: str = Field(default="1024x1024", max_length=20)


class ShopifyMagicEmailRequest(BaseModel):
    campaign_goal: str = Field(min_length=2, max_length=300)
    audience_segment: str = Field(min_length=2, max_length=200)
    product_highlights: list[str] = Field(default_factory=list, max_length=20)
    brand_voice: str = Field(default="friendly", max_length=120)
    timezone: str = Field(default="UTC", max_length=80)
    preferred_send_windows: list[str] = Field(default_factory=list, max_length=10)


class ShopifyMagicInboxRequest(BaseModel):
    customer_question: str = Field(min_length=2, max_length=5000)
    customer_name: str | None = Field(default=None, max_length=120)
    order_reference: str | None = Field(default=None, max_length=120)
    tone: str = Field(default="friendly", max_length=80)


class HubspotWiringApplyRequest(BaseModel):
    providers: list[str] = Field(default_factory=list, max_length=100)
    include_all_missing: bool = Field(default=True)
    include_optional_auth: bool = Field(default=True)
    values: dict[str, str] = Field(
        default_factory=dict, description="Environment key/value pairs to apply to HubSpot runtime wiring checks."
    )


class HubspotProductRunRequest(BaseModel):
    objective: str = Field(default="activate", min_length=2, max_length=200)
    context: dict[str, Any] = Field(default_factory=dict)


class HootsuiteWiringApplyRequest(BaseModel):
    providers: list[str] = Field(default_factory=list, max_length=100)
    include_all_missing: bool = Field(default=True)
    include_optional_auth: bool = Field(default=True)


class HootsuiteProductRunRequest(BaseModel):
    objective: str = Field(default="publish", min_length=2, max_length=200)
    context: dict[str, Any] = Field(default_factory=dict)


class HootsuiteFeatureAutomationRequest(BaseModel):
    objective: str = Field(default="full-coverage", min_length=2, max_length=200)
    brands: list[str] = Field(default_factory=list, max_length=20)
    competitors: list[str] = Field(default_factory=list, max_length=20)
    networks: list[str] = Field(
        default_factory=lambda: ["facebook", "instagram", "linkedin", "x", "tiktok", "youtube"], max_length=20
    )
    timeframe_days: int = Field(default=30, ge=1, le=3650)
    require_live_providers: bool = Field(default=False)


class AiranklabWiringApplyRequest(BaseModel):
    values: dict[str, str] = Field(
        default_factory=dict, description="Environment key/value pairs to apply to runtime wiring checks."
    )
