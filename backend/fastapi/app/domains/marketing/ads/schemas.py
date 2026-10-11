"""Marketing/Ads request contracts."""

from __future__ import annotations
from pydantic import BaseModel
from pydantic import Field
from typing import Any
from typing import Literal


class ConnectorStartResponse(BaseModel):
    platform: str
    state: str
    authorization_url: str
    callback_path: str


class ConnectorCallbackRequest(BaseModel):
    state: str = Field(min_length=8, max_length=256)
    code: str = Field(min_length=4, max_length=2000)
    account_name: str = Field(default="Primary Account", min_length=2, max_length=160)
    account_id: str = Field(default="", max_length=200)
    scopes: list[str] = Field(default_factory=list, max_length=40)
    credit_total: float = Field(default=0.0, ge=0)
    credit_remaining: float = Field(default=0.0, ge=0)
    credit_currency: str = Field(default="USD", min_length=3, max_length=8)


class ConnectorListResponse(BaseModel):
    status: str
    tenant_id: str
    connectors: list[dict[str, Any]]


class KeywordConfig(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    cpc_bid: float = Field(default=0.0, ge=0)
    cost_today: float = Field(default=0.0, ge=0)
    rank: int = Field(default=0, ge=0)


class CampaignCreative(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=2, max_length=2000)
    cta: str = Field(default="Learn More", min_length=2, max_length=80)
    media_urls: list[str] = Field(default_factory=list, max_length=20)


class CampaignSchedule(BaseModel):
    timezone: str = Field(default="UTC", min_length=2, max_length=80)
    start_at: str | None = None
    end_at: str | None = None
    auto_post: bool = True
    posting_dates: list[str] = Field(default_factory=list, max_length=366)


class CampaignCreateRequest(BaseModel):
    platform: str = Field(pattern="^(google_ads|microsoft_ads|amazon_ads|apple_search_ads|youtube_ads)$")
    campaign_name: str = Field(min_length=2, max_length=180)
    objective: str = Field(default="conversions", min_length=2, max_length=80)
    status: Literal["draft", "active", "paused"] = "draft"
    budget_daily: float = Field(default=0.0, ge=0)
    budget_total: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=8)
    keywords: list[KeywordConfig] = Field(default_factory=list, max_length=300)
    creative: CampaignCreative
    schedule: CampaignSchedule = Field(default_factory=CampaignSchedule)
    connected_accounts: list[str] = Field(default_factory=list, max_length=20)


class CampaignUpdateRequest(BaseModel):
    campaign_name: str | None = Field(default=None, min_length=2, max_length=180)
    objective: str | None = Field(default=None, min_length=2, max_length=80)
    status: Literal["draft", "active", "paused"] | None = None
    budget_daily: float | None = Field(default=None, ge=0)
    budget_total: float | None = Field(default=None, ge=0)
    keywords: list[KeywordConfig] | None = Field(default=None, max_length=300)
    creative: CampaignCreative | None = None
    schedule: CampaignSchedule | None = None


class CampaignPublishRequest(BaseModel):
    publish_all_connected_accounts: bool = True


class CampaignMetricsPatchRequest(BaseModel):
    likes: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    impressions: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    spend: float = Field(default=0.0, ge=0)
    revenue: float = Field(default=0.0, ge=0)


class CalendarRescheduleRequest(BaseModel):
    campaign_id: str = Field(min_length=8, max_length=120)
    from_date: str = Field(min_length=8, max_length=40)
    to_date: str = Field(min_length=8, max_length=40)
    auto_select_window_days: int = Field(default=7, ge=1, le=90)


class AssetAutoResizeRequest(BaseModel):
    asset_url: str = Field(min_length=5, max_length=1200)
    platforms: list[str] = Field(default_factory=lambda: ["google_ads", "amazon_ads", "microsoft_ads"], max_length=10)


class ApprovalRequestModel(BaseModel):
    reviewer_email: str = Field(min_length=5, max_length=254)
    message: str = Field(default="", max_length=1000)
    auto_publish_on_approve: bool = True


class ApprovalDecisionModel(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(default="", max_length=1000)
    reviewer_name: str = Field(default="Reviewer", min_length=2, max_length=120)


class CampaignDuplicateRequest(BaseModel):
    new_name: str = Field(min_length=2, max_length=180)
    status: Literal["draft", "active", "paused"] = "draft"


class ForecastResponse(BaseModel):
    status: str
    tenant_id: str
    horizon_days: int
    projected_spend: float
    projected_clicks: int
    projected_conversions: int
    projected_roi_pct: float
