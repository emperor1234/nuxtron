"""Public request schemas for the Social Workspace bounded context."""

from __future__ import annotations
from .constants import (
    DEFAULT_BACKGROUND_MEDIA,
    DEFAULT_FONT_FAMILY,
    DEFAULT_SOCIAL_AGENT,
    DEFAULT_SUBTITLES_LANGUAGE,
    PUBLISH_MODE_PATTERN,
)


from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_BACKGROUND_MEDIA = "AI Videos"
DEFAULT_SUBTITLES_LANGUAGE = "Auto (detect)"
DEFAULT_FONT_FAMILY = "Hanken Grotesk"
DEFAULT_SOCIAL_AGENT = "Social Desk"
PUBLISH_MODE_PATTERN = r"^(auto|now|draft)$"


class SocialAccountConnectRequest(BaseModel):
    network: str = Field(min_length=2, max_length=40)
    account_name: str = Field(min_length=2, max_length=160)
    handle: str = Field(min_length=1, max_length=120)
    account_type: str = Field(default="business", max_length=80)
    website: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=500)


class BrandProfileRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    industry: str = Field(default="marketing", max_length=120)
    website: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=800)
    tone: str = Field(default="professional", max_length=80)
    logo_url: str | None = Field(default=None, max_length=3000000)
    logo_dark_url: str | None = Field(default=None, max_length=3000000)
    keywords: list[str] = Field(default_factory=list, max_length=25)
    hashtags: list[str] = Field(default_factory=list, max_length=25)
    timezone: str = Field(default="UTC", max_length=80)
    ethnicity: str | None = Field(default=None, max_length=80)
    voiceover: str | None = Field(default=None, max_length=120)
    avatar_profile: dict[str, Any] | None = None
    voiceover_engine: dict[str, Any] | None = None
    ugc_template_profile: dict[str, Any] | None = None
    brand_colors: list[str] = Field(default_factory=list, max_length=12)
    title_font_family: str = Field(default=DEFAULT_FONT_FAMILY, max_length=120)
    subtitle_font_family: str = Field(default=DEFAULT_FONT_FAMILY, max_length=120)
    title_font_weight: str = Field(default="Regular", max_length=80)
    subtitle_font_weight: str = Field(default="Regular", max_length=80)
    title_case_type: str = Field(default="Auto", max_length=40)
    subtitle_case_type: str = Field(default="Auto", max_length=40)
    use_custom_font_title: bool = False
    use_custom_font_subtitle: bool = False
    custom_font_title: str | None = Field(default=None, max_length=300000)
    custom_font_subtitle: str | None = Field(default=None, max_length=300000)


class BrandWebsiteFetchRequest(BaseModel):
    website_url: str = Field(min_length=4, max_length=300)


class UgcTemplateProfileRequest(BaseModel):
    style_category_id: str = Field(default="no-discount-promo", max_length=80)
    preview_template_id: str = Field(default="tpl-value-story", max_length=120)
    caption_pack_id: str = Field(default="ugc-main-launch", max_length=80)
    platform: str = Field(default="Instagram", max_length=40)
    objective: str = Field(default="Sales", max_length=40)
    hook_style: str = Field(default="Announcement", max_length=60)
    script_style: str = Field(default="Storytelling", max_length=80)
    aspect_ratio: str = Field(default="9:16", max_length=20)
    auto_adjust_platforms: bool = True
    background_media: str = Field(default=DEFAULT_BACKGROUND_MEDIA, max_length=80)
    subtitles_auto: bool = True
    subtitles_language: str = Field(default=DEFAULT_SUBTITLES_LANGUAGE, max_length=80)


class SocialEngageRequest(BaseModel):
    account_id: int = Field(ge=1)
    reply_text: str = Field(min_length=2, max_length=1000)
    action: str = Field(default="reply", pattern=r"^(reply|like|share|comment)$")
    agent_name: str = Field(default=DEFAULT_SOCIAL_AGENT, max_length=120)


class AutoPostRequest(BaseModel):
    account_id: int = Field(ge=1)
    content_type: str = Field(default="image", max_length=40)
    headline: str = Field(min_length=2, max_length=180)
    caption: str = Field(min_length=2, max_length=4000)
    media_urls: list[str] = Field(default_factory=list, max_length=12)
    publish_mode: str = Field(default="auto", pattern=PUBLISH_MODE_PATTERN)
    publish_at: datetime | None = None
    recurrence: str = Field(default="none", pattern=r"^(none|daily|weekly|monthly)$")
    recurrence_count: int = Field(default=1, ge=1, le=365)
    recurrence_until: datetime | None = None
    conditional_rules: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    requires_approval: bool = False
    approval_levels: list[str] = Field(default_factory=list, max_length=10)
    auto_publish_on_approval: bool = True
    shorten_links: bool = False
    shortener_provider: str | None = Field(default=None, pattern=r"^(bitly|tinyurl|rebrandly)$")
    shortener_domain: str | None = Field(default=None, max_length=120)


class ReviewReplyRequest(BaseModel):
    reply_text: str = Field(min_length=2, max_length=1000)


class ReviewStatusRequest(BaseModel):
    status: str = Field(pattern=r"^(open|responded|resolved)$")


class ReviewCaseCreateRequest(BaseModel):
    source_review_id: int = Field(ge=1)
    priority: str = Field(default="medium", pattern=r"^(low|medium|high|urgent)$")
    owner: str = Field(default="social-care", min_length=2, max_length=120)


class InfluencerSearchRequest(BaseModel):
    query: str = Field(default="", max_length=200)
    platform: str = Field(default="instagram", max_length=40)
    min_followers: int = Field(default=0, ge=0, le=100000000)


class InfluencerShortlistRequest(BaseModel):
    influencer_id: str = Field(min_length=3, max_length=120)


class InfluencerAdvocacyBridgeRequest(BaseModel):
    campaign: str = Field(min_length=2, max_length=160)
    title: str = Field(min_length=2, max_length=180)
    message_angle: str = Field(default="Partnership opportunity", max_length=200)
    network: str = Field(default="linkedin", max_length=40)


class AdvocacyAssetCreateRequest(BaseModel):
    campaign: str = Field(min_length=2, max_length=160)
    title: str = Field(min_length=2, max_length=180)
    message: str = Field(min_length=2, max_length=4000)
    network: str = Field(default="linkedin", max_length=40)


class AutomationRuleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    trigger_type: str = Field(min_length=2, max_length=80)
    trigger_value: str = Field(min_length=1, max_length=300)
    action_type: str = Field(min_length=2, max_length=80)
    action_payload: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class AutomationRuleStatusRequest(BaseModel):
    enabled: bool


class AIAgentWorkflowExecuteRequest(BaseModel):
    template_key: str = Field(pattern=r"^(social_poster|dm_chatbot|comment_to_dm)$")
    trigger_type: str = Field(default="scheduled", max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)


class BestStackProbeResultRequest(BaseModel):
    key: str = Field(min_length=2, max_length=80)
    label: str = Field(min_length=3, max_length=180)
    ok: bool
    detail: str = Field(default="", max_length=800)


class BestStackReportCreateRequest(BaseModel):
    probe_results: list[BestStackProbeResultRequest] = Field(default_factory=list, max_length=20)
    generated_by: str = Field(default="frontend", max_length=80)


class CommentToDmRequest(BaseModel):
    message_id: int = Field(ge=1)
    keyword: str = Field(min_length=1, max_length=80)
    dm_text: str | None = Field(default=None, max_length=1000)
    offer_link: str | None = Field(default=None, max_length=2048)


class DmChatbotReplyRequest(BaseModel):
    message_id: int = Field(ge=1)
    intent: str = Field(default="support", max_length=80)
    response_tone: str = Field(default="friendly", max_length=80)
    context: dict[str, Any] = Field(default_factory=dict)


class ApprovalCreateRequest(BaseModel):
    post_id: str = Field(min_length=1, max_length=120)
    approvers: list[str] = Field(default_factory=list, min_length=1, max_length=20)
    auto_publish_on_approve: bool = True
    approval_levels: list[str] = Field(default_factory=list, max_length=10)


class ApprovalRejectRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=300)


class LinkShortenRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    provider: str | None = Field(default=None, pattern=r"^(bitly|tinyurl|rebrandly)$")
    domain: str | None = Field(default=None, max_length=120)


class ConditionalRuleEvaluationRequest(BaseModel):
    rules: list[dict[str, Any]] = Field(default_factory=list, min_length=1, max_length=20)


class IntegrationWebhookCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    provider: str = Field(default="custom", pattern=r"^(zapier|make|custom)$")
    url: str = Field(min_length=8, max_length=500)
    event_types: list[str] = Field(default_factory=lambda: ["social.post.published"])
    secret: str | None = Field(default=None, max_length=200)
    action_type: str = Field(default="notify_only", pattern=r"^(notify_only|create_idea|queue_post)$")
    enabled: bool = True


class IntegrationWebhookUpdateRequest(BaseModel):
    enabled: bool | None = None
    event_types: list[str] | None = None
    action_type: str | None = Field(default=None, pattern=r"^(notify_only|create_idea|queue_post)$")


class IntegrationWebhookTestRequest(BaseModel):
    event_type: str = Field(default="social.test_event", max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class CanvaImportRequest(BaseModel):
    account_id: int = Field(ge=1)
    design_id: str | None = Field(default=None, max_length=180)
    design_url: str | None = Field(default=None, max_length=2000)
    caption: str = Field(default="Imported from Canva", min_length=2, max_length=4000)
    headline: str = Field(default="Canva design", min_length=2, max_length=180)
    target_network: str = Field(default="instagram", max_length=60)
    publish_mode: str = Field(default="draft", pattern=PUBLISH_MODE_PATTERN)
    publish_at: datetime | None = None


class BrowserExtensionCaptureRequest(BaseModel):
    source_url: str = Field(min_length=8, max_length=2000)
    title: str = Field(min_length=1, max_length=240)
    selected_text: str | None = Field(default=None, max_length=8000)
    note: str | None = Field(default=None, max_length=2000)
    suggested_network: str = Field(default="linkedin", max_length=60)
    screenshot_url: str | None = Field(default=None, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class BrowserExtensionQueueRequest(BaseModel):
    account_id: int = Field(ge=1)
    publish_mode: str = Field(default="draft", pattern=PUBLISH_MODE_PATTERN)
    publish_at: datetime | None = None
    target_network: str | None = Field(default=None, max_length=60)


class MobileDeviceRegisterRequest(BaseModel):
    device_id: str = Field(min_length=6, max_length=160)
    platform: str = Field(pattern=r"^(ios|android|web)$")
    push_provider: str = Field(default="fcm", pattern=r"^(fcm|onesignal|apns|none)$")
    push_token: str | None = Field(default=None, max_length=400)
    app_version: str | None = Field(default=None, max_length=40)
    locale: str | None = Field(default=None, max_length=30)
    timezone: str = Field(default="UTC", max_length=120)


class MobileQuickPostRequest(BaseModel):
    account_id: int = Field(ge=1)
    text: str = Field(min_length=2, max_length=4000)
    media_urls: list[str] = Field(default_factory=list, max_length=12)
    network: str = Field(default="instagram", max_length=60)
    publish_mode: str = Field(default="draft", pattern=PUBLISH_MODE_PATTERN)
    publish_at: datetime | None = None


class MobileOfflineSyncRequest(BaseModel):
    device_id: str = Field(min_length=6, max_length=160)
    events: list[dict[str, Any]] = Field(default_factory=list, min_length=1, max_length=200)


class PauseAllRequest(BaseModel):
    paused: bool = True
    reason: str = Field(default="Operator initiated pause.", min_length=2, max_length=240)


class AutomationFeedCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    feed_url: str = Field(min_length=8, max_length=500)
    target_networks: list[str] = Field(default_factory=lambda: ["linkedin"])
    cadence_minutes: int = Field(default=180, ge=5, le=10080)
    autopublish: bool = False


class AutomationFeedStatusRequest(BaseModel):
    enabled: bool


class AutomationFeedSyncRequest(BaseModel):
    max_items: int = Field(default=3, ge=1, le=20)


class SocialIdeaCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    body: str = Field(min_length=2, max_length=4000)
    source: str = Field(default="manual", max_length=80)
    tags: list[str] = Field(default_factory=list)


class SocialIdeaQueueRequest(BaseModel):
    network: str = Field(default="linkedin", max_length=60)
    publish_at: datetime | None = None


class SavedReplyCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    body: str = Field(min_length=2, max_length=1000)
    category: str = Field(default="general", max_length=80)


class SavedReplyUpdateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    body: str = Field(min_length=2, max_length=1000)
    category: str = Field(default="general", max_length=80)


class SocialInboxRespondRequest(BaseModel):
    response_text: str = Field(min_length=2, max_length=1000)


class MessageClaimRequest(BaseModel):
    agent_name: str = Field(default=DEFAULT_SOCIAL_AGENT, min_length=2, max_length=120)


class InboxBulkActionRequest(BaseModel):
    message_ids: list[int] = Field(min_length=1)
    action: str = Field(default="complete", max_length=20)
    agent_name: str = Field(default=DEFAULT_SOCIAL_AGENT, min_length=2, max_length=120)


ContactView = dict[str, Any]


class OAuthStartRequest(BaseModel):
    account_name: str | None = Field(default=None, min_length=2, max_length=160)
    handle: str | None = Field(default=None, min_length=1, max_length=120)
    account_type: str = Field(default="business", max_length=80)
    website: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=500)


class OAuthCallbackRequest(BaseModel):
    state: str = Field(min_length=8, max_length=256)
    code: str = Field(min_length=4, max_length=1024)


class ConnectAllRequest(BaseModel):
    account_name_prefix: str = Field(default="Nuxtron", min_length=2, max_length=120)
    handle_prefix: str = Field(default="nuxtron", min_length=2, max_length=60)
    account_type: str = Field(default="business", max_length=80)
    website: str | None = Field(default="https://nuxtron.local", max_length=300)
    description: str | None = Field(
        default="Connected social workspace for publishing, engagement, and analytics.", max_length=500
    )


# ── Social Suite Models ────────────────────────────────────────────────────────


class ListeningKeywordRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    networks: list[str] = Field(default_factory=lambda: ["instagram", "x", "facebook", "linkedin"])
    alert_threshold: int = Field(default=100, ge=1, le=100000)
    alert_on_crisis: bool = True


class ListeningAlertDismissRequest(BaseModel):
    dismissed: bool = True


class StreamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    stream_type: str = Field(default="keyword", max_length=80)
    query: str = Field(min_length=1, max_length=300)
    networks: list[str] = Field(default_factory=lambda: ["instagram", "x", "facebook"])
    column_index: int = Field(default=0, ge=0, le=20)


class StreamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    column_index: int | None = Field(default=None, ge=0, le=20)


class CompetitorTrackRequest(BaseModel):
    handle: str = Field(min_length=2, max_length=120)
    network: str = Field(default="instagram", max_length=60)


class AdCampaignCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    objective: str = Field(default="awareness", max_length=80)
    network: str = Field(default="facebook", max_length=60)
    budget_daily: float = Field(default=50.0, ge=1.0, le=100000.0)
    budget_total: float = Field(default=500.0, ge=1.0, le=10000000.0)
    start_date: str = Field(min_length=8, max_length=30)
    end_date: str = Field(min_length=8, max_length=30)
    audience_targeting: dict[str, Any] = Field(default_factory=dict)
    creative_ids: list[str] = Field(default_factory=list)


class AdBoostRequest(BaseModel):
    post_id: str = Field(min_length=1, max_length=200)
    network: str = Field(default="facebook", max_length=60)
    budget_total: float = Field(default=100.0, ge=5.0, le=100000.0)
    duration_days: int = Field(default=7, ge=1, le=90)
    objective: str = Field(default="engagement", max_length=80)


class ReportCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    report_type: str = Field(default="overview", max_length=80)
    networks: list[str] = Field(default_factory=lambda: ["instagram", "x", "facebook", "linkedin"])
    date_range_days: int = Field(default=30, ge=1, le=365)
    metrics: list[str] = Field(default_factory=lambda: ["impressions", "reach", "engagement", "clicks"])
    schedule: str | None = Field(default=None, max_length=60)
    export_format: str = Field(default="pdf", max_length=20)


class BulkScheduleRequest(BaseModel):
    posts: list[dict[str, Any]] = Field(min_length=1, max_length=500)


class UgcApproveRequest(BaseModel):
    approved: bool = True
    note: str | None = Field(default=None, max_length=500)


class UgcRepublishRequest(BaseModel):
    scheduled_time: datetime | None = None
    target_networks: list[str] = Field(default_factory=list)
    add_credit: bool = True
