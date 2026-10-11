"""Marketing/Growth request contracts."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from pydantic import BaseModel
from pydantic import Field
from typing import Any
from typing import Literal


@dataclass(frozen=True)
class GrowthSuiteContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    growth_suite_memory: list[dict[str, Any]]
    scheduled_posts_memory: list[dict[str, Any]]
    email_campaigns_memory: list[dict[str, Any]]
    chatbots_memory: list[dict[str, Any]]
    chatbot_leads_memory: list[dict[str, Any]]
    linkinbio_pages_memory: list[dict[str, Any]]
    linkinbio_links_memory: list[dict[str, Any]]
    analytics_reports_memory: list[dict[str, Any]]
    crm_contacts_memory: list[dict[str, Any]]
    crm_deals_memory: list[dict[str, Any]]
    revenue_touchpoints_memory: list[dict[str, Any]]
    revenue_conversions_memory: list[dict[str, Any]]
    db_ready_fn: Callable[[], bool]
    db_dsn_fn: Callable[[], str]


class BrandVoiceRequest(BaseModel):
    profile_name: str = Field(default="Primary Voice", min_length=2, max_length=120)
    sample_posts: list[str] = Field(min_length=3, max_length=30)
    ai_output: str = Field(default="", max_length=5000)


class ABTestRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    base_content: str = Field(min_length=10, max_length=5000)
    channel: str = Field(default="linkedin", max_length=80)
    goal: str = Field(default="engagement", max_length=80)


class ABTestEvaluationRequest(BaseModel):
    engagement_scores: list[float] = Field(default_factory=list, max_length=5)
    republish: bool = True


class RoiForecastRequest(BaseModel):
    content_title: str = Field(min_length=2, max_length=200)
    platform: str = Field(default="linkedin", max_length=80)
    expected_impressions: int = Field(default=12000, ge=100)
    historical_revenue: list[float] = Field(default_factory=lambda: [320.0, 410.0, 515.0], min_length=1, max_length=24)
    historical_engagement_rate: list[float] = Field(
        default_factory=lambda: [0.041, 0.052, 0.048], min_length=1, max_length=24
    )


class CounterStrikeRequest(BaseModel):
    competitor_handle: str = Field(min_length=2, max_length=120)
    platform: str = Field(default="linkedin", max_length=80)
    competitor_post: str = Field(min_length=10, max_length=5000)


class ContentCalendarRequest(BaseModel):
    topics: list[str] = Field(min_length=3, max_length=20)
    days: int = Field(default=90, ge=30, le=90)
    primary_channel: str = Field(default="linkedin", max_length=80)


class AgencyWorkspaceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    owner_email: str = Field(min_length=5, max_length=240)
    clients: list[str] = Field(default_factory=list, max_length=20)


class AgencyMemberRequest(BaseModel):
    email: str = Field(min_length=5, max_length=240)
    role: str = Field(pattern="^(Owner|Admin|Editor|Viewer|Client)$")


class AgencyMrrRequest(BaseModel):
    client_name: str = Field(min_length=2, max_length=160)
    monthly_recurring_revenue: float = Field(gt=0)


class AudienceDnaRequest(BaseModel):
    audience_handles: list[str] = Field(default_factory=list, max_length=200)
    product_price: float = Field(default=99.0, gt=0)


class IraBrainRequest(BaseModel):
    focus: str = Field(default="growth", max_length=120)


class AdsDraftRequest(BaseModel):
    campaign_name: str = Field(min_length=2, max_length=160)
    offer: str = Field(min_length=5, max_length=500)
    primary_message: str = Field(min_length=10, max_length=2000)


class RepurposeRequest(BaseModel):
    source_content: str = Field(min_length=20, max_length=6000)


class GeoSeoRequest(BaseModel):
    content: str = Field(min_length=20, max_length=6000)
    competitors: list[str] = Field(default_factory=list, max_length=20)


class EmailMarketingRequest(BaseModel):
    source_content: str = Field(min_length=20, max_length=6000)
    audience: str = Field(default="warm leads", max_length=120)
    cta: str = Field(default="Book a strategy call", max_length=160)


class SmartSchedulerRequest(BaseModel):
    drafts: list[str] = Field(min_length=1, max_length=20)
    platform: str = Field(default="linkedin", max_length=80)
    fill_days: int = Field(default=7, ge=1, le=14)


class PodcastRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    source_text: str = Field(min_length=20, max_length=6000)


class VideoScriptRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=160)
    audience: str = Field(min_length=3, max_length=160)
    objective: str = Field(min_length=3, max_length=160)


class AdvancedReportRequest(BaseModel):
    client_name: str = Field(min_length=2, max_length=160)
    reporting_window_days: int = Field(default=30, ge=7, le=90)


class BrandVoiceFeedbackRequest(BaseModel):
    signal: Literal["thumbs_up", "thumbs_down"]
    edited_output: str | None = Field(default=None, max_length=2200)


class KeywordTrackRequest(BaseModel):
    keyword: str = Field(min_length=2, max_length=120)
    impressions: int = Field(default=0, ge=0)
    engagement: int = Field(default=0, ge=0)
    platform: str = Field(default="linkedin", max_length=80)


class BrandHierarchyRequest(BaseModel):
    child_brand_name: str = Field(min_length=2, max_length=160)
    parent_brand_key: str = Field(default="root", max_length=120)
    region: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    voice_profile_key: str | None = Field(default=None, max_length=120)
