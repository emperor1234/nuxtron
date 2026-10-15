"""Social Workspace composition and explicit compatibility exports."""

from fastapi import APIRouter
from .persistence import _SocialWorkspaceState
from .api import (
    get_competitor_insights,
    list_monitoring_streams,
    get_ads_analytics,
    list_bulk_schedule_jobs,
    get_ugc_performance,
    list_social_ai_agent_templates,
    create_social_automation_feed,
    get_social_inbox_stats,
    delete_social_saved_reply,
    update_social_review_status,
    create_social_advocacy_asset,
    social_catalog,
    list_oauth_providers,
    get_brand_profile,
    social_workspace_overview,
    list_hashtag_groups,
    get_publishing_queue,
    create_approval_request,
    receive_incoming_webhook,
    register_mobile_device,
    create_content_template,
    delete_community_saved_reply,
    repurpose_longform_asset,
    track_start_page_link_click,
)
from .services.workspace import _sw_http_error as _sw_http_error
from .services.workspace import _normalized_text as _normalized_text
from .services.workspace import _sw_extract_urls as _sw_extract_urls
from .services.workspace import _sw_conditional_metrics as _sw_conditional_metrics
from .services.workspace import _sw_evaluate_conditions as _sw_evaluate_conditions
from .services.workspace import _sw_deliver_webhook as _sw_deliver_webhook
from .services.workspace import _sw_resolve_canva_asset_url as _sw_resolve_canva_asset_url
from .services.workspace import _sw_seed_notifications as _sw_seed_notifications
from .services.workspace import _sw_seed_inbox_messages as _sw_seed_inbox_messages
from .services.workspace import _sw_seed_post_history as _sw_seed_post_history
from .services.workspace import _sw_seed_listening as _sw_seed_listening
from .services.workspace import _sw_seed_monitoring_streams as _sw_seed_monitoring_streams
from .services.workspace import _sw_seed_ad_campaigns as _sw_seed_ad_campaigns
from .services.workspace import _sw_seed_reports as _sw_seed_reports
from .services.workspace import _sw_seed_competitors as _sw_seed_competitors
from .services.workspace import _sw_seed_reviews as _sw_seed_reviews
from .services.workspace import _sw_seed_influencers as _sw_seed_influencers
from .services.workspace import _sw_seed_saved_replies as _sw_seed_saved_replies
from .services.brand import _normalize_avatar_profile as _normalize_avatar_profile
from .services.brand import _normalize_voiceover_engine as _normalize_voiceover_engine
from .services.brand import _normalize_ugc_template_profile as _normalize_ugc_template_profile
from .services.brand import _sw_profile_defaults as _sw_profile_defaults
from .services.brand import _sw_avatar_catalog as _sw_avatar_catalog
from .services.brand import _sw_voiceover_catalog as _sw_voiceover_catalog
from .services.brand import _sw_build_brand_fields as _sw_build_brand_fields
from .services.brand import _sw_update_brand_profile as _sw_update_brand_profile
from .services.brand import _sw_update_ugc_template as _sw_update_ugc_template
from .services.website import _clean_text as _clean_text
from .services.website import _extract_title as _extract_title
from .services.website import _extract_meta as _extract_meta
from .services.website import _extract_first_tag as _extract_first_tag
from .services.website import _extract_link_href as _extract_link_href
from .services.website import _fetch_html as _fetch_html
from .services.website import _extract_keywords_from_html as _extract_keywords_from_html
from .services.website import _detect_industry as _detect_industry
from .services.website import _parse_website_host as _parse_website_host
from .services.website import _extract_page_content as _extract_page_content
from .services.website import _build_profile_from_website as _build_profile_from_website
from .services.website import _sw_strip_html as _sw_strip_html
from .services.website import _sw_fetch_brand_from_website as _sw_fetch_brand_from_website
from .services.publishing import _sw_humanized_publish_slot as _sw_humanized_publish_slot
from .services.publishing import _sw_resolve_publish_at as _sw_resolve_publish_at
from .services.publishing import _sw_publish_mode_to_status as _sw_publish_mode_to_status
from .services.publishing import _sw_shortener_payload as _sw_shortener_payload
from .services.publishing import _sw_shortener_headers as _sw_shortener_headers
from .services.publishing import _sw_shortener_extract_url as _sw_shortener_extract_url
from .services.publishing import _sw_shortener_request as _sw_shortener_request
from .services.publishing import _sw_shortener_provider_config as _sw_shortener_provider_config
from .services.publishing import _sw_shorten_url as _sw_shorten_url
from .services.publishing import _sw_shift_month as _sw_shift_month
from .services.publishing import _sw_apply_recurrence as _sw_apply_recurrence
from .services.publishing import _sw_autopilot_preview as _sw_autopilot_preview
from .services.publishing import _sw_autopilot_publish_datetime as _sw_autopilot_publish_datetime
from .services.publishing import _sw_autopilot_apply_short_links as _sw_autopilot_apply_short_links
from .services.publishing import _sw_autopilot_approval_state as _sw_autopilot_approval_state
from .services.publishing import _sw_autopilot_post_status as _sw_autopilot_post_status
from .services.publishing import _sw_build_recurring_autopilot_posts as _sw_build_recurring_autopilot_posts
from .services.publishing import _sw_build_autopilot_approval_request as _sw_build_autopilot_approval_request
from .services.publishing import _sw_store_short_links as _sw_store_short_links
from .services.oauth import _oauth_mode as _oauth_mode
from .services.oauth import _require_strict_live_oauth as _require_strict_live_oauth
from .services.oauth import _default_redirect_uri as _default_redirect_uri
from .services.oauth import _provider_is_configured as _provider_is_configured
from .services.oauth import _build_authorization_url as _build_authorization_url
from .services.oauth import _sw_list_oauth_providers as _sw_list_oauth_providers
from .services.oauth import _sw_oauth_start as _sw_oauth_start
from .services.oauth import _sw_oauth_callback as _sw_oauth_callback
from .services.oauth import _sw_oauth_connect_all as _sw_oauth_connect_all
from .services.capabilities import _strict_social_mode_enabled as _strict_social_mode_enabled
from .services.capabilities import _require_openai_for_strict_social as _require_openai_for_strict_social
from .services.capabilities import _require_any_env_for_strict_social as _require_any_env_for_strict_social
from .services.capabilities import _require_hubspot_for_strict_social as _require_hubspot_for_strict_social
from .services.capabilities_strict_social_startup_blockers import (
    _strict_social_startup_blockers as _strict_social_startup_blockers,
)
from .services.ai_policy import _sw_load_ai_policy as _sw_load_ai_policy
from .services.ai_policy import _sw_ai_signal_flags as _sw_ai_signal_flags
from .services.ai_policy import _sw_llm_guard as _sw_llm_guard
from .services.ai_policy import _sw_nemo_guardrails as _sw_nemo_guardrails
from .services.ai_policy import _sw_ai_safety_bundle as _sw_ai_safety_bundle
from .services.ai_policy import _sw_ai_output_guard as _sw_ai_output_guard
from .services.ai_policy import _sw_ai_agent_templates as _sw_ai_agent_templates
from .services.ai_policy import _ai_assistant_fallback as _ai_assistant_fallback
from .services.ai_policy import _sw_run_ai_assistant_text as _sw_run_ai_assistant_text
from .services.workspace_connect_account import _sw_connect_account as _sw_connect_account
from .services.workspace_connect_account import _sw_integration_catalog as _sw_integration_catalog
from .services.workspace_connect_account import _sw_seed_inbox_for_tenant as _sw_seed_inbox_for_tenant
from .services.workspace_connect_account import _sw_seed_automation_rules as _sw_seed_automation_rules
from .services.workspace_connect_account import _sw_seed_automation_feeds as _sw_seed_automation_feeds
from .services.workspace_connect_account import _sw_seed_content_ideas as _sw_seed_content_ideas
from .services.workspace_connect_account import _sw_workspace_overview as _sw_workspace_overview
from .services.workspace_connect_account import _sw_engage_inbox_message as _sw_engage_inbox_message
from .services.workspace_connect_account import _buffer_seed_community_comments as _buffer_seed_community_comments
from .services.publishing_autopilot_publish import _sw_autopilot_publish as _sw_autopilot_publish
from .services.workspace_buffer_compute_comment_score import (
    _buffer_compute_comment_score as _buffer_compute_comment_score,
)
from .services.workspace_buffer_compute_comment_score import _buffer_seed_hashtag_groups as _buffer_seed_hashtag_groups
from .services.workspace_buffer_compute_comment_score import (
    _buffer_seed_posting_schedules as _buffer_seed_posting_schedules,
)
from .services.workspace_buffer_compute_comment_score import _buffer_seed_templates as _buffer_seed_templates
from .services.workspace_buffer_compute_comment_score import _buffer_seed_team_members as _buffer_seed_team_members
from .services.workspace_buffer_compute_comment_score import _buffer_seed_start_page as _buffer_seed_start_page
from .services.workspace_buffer_compute_comment_score import (
    _buffer_get_audience_insights as _buffer_get_audience_insights,
)
from .services.workspace_buffer_compute_comment_score import (
    _buffer_get_channel_analytics as _buffer_get_channel_analytics,
)
from .services.workspace_buffer_compute_comment_score import (
    _buffer_get_best_time_analysis as _buffer_get_best_time_analysis,
)
from .services.workspace_buffer_compute_comment_score import (
    _sw_generate_dm_chatbot_reply as _sw_generate_dm_chatbot_reply,
)
from .services.workspace_buffer_compute_comment_score import (
    _sw_request_longform_variants as _sw_request_longform_variants,
)
from .services.workspace_buffer_compute_comment_score import (
    _sw_build_longform_fallback_variants as _sw_build_longform_fallback_variants,
)
from .services.workspace_parse_longform_variants import _sw_parse_longform_variants as _sw_parse_longform_variants
from .services.workspace_parse_longform_variants import _sw_pad_longform_variants as _sw_pad_longform_variants
from .services.workspace_parse_longform_variants import _sw_generate_longform_variants as _sw_generate_longform_variants
from ...domains.social.persistence import _is_real_production_environment
from ...domains.social.persistence import _sw_audit
from ...domains.social.persistence import _sw_db_enabled
from ...domains.social.persistence import _sw_ensure_brand_profile_table
from ...domains.social.persistence import _sw_get_account
from ...domains.social.persistence import _sw_load_profile_from_db
from ...domains.social.persistence import _sw_save_profile_to_db
from .extended_schemas import CalendarMoveRequest as CalendarMoveRequest
from .extended_schemas import PostingScheduleRequest as PostingScheduleRequest
from .extended_schemas import TeamMemberUpdateRequest as TeamMemberUpdateRequest
from .extended_schemas import LongformRepurposeRequest as LongformRepurposeRequest
from .extended_schemas import HashtagGroupUpdateRequest as HashtagGroupUpdateRequest
from .extended_schemas import SavedCommentReplyCreateRequest as SavedCommentReplyCreateRequest
from .extended_schemas import FirstCommentRequest as FirstCommentRequest
from .extended_schemas import ThreadPostRequest as ThreadPostRequest
from .extended_schemas import ContentTemplateCreateRequest as ContentTemplateCreateRequest
from .extended_schemas import TeamMemberInviteRequest as TeamMemberInviteRequest
from .extended_schemas import QueueReorderRequest as QueueReorderRequest
from .extended_schemas import StartPageUpdateRequest as StartPageUpdateRequest
from .extended_schemas import CalendarAutoPostRequest as CalendarAutoPostRequest
from .extended_schemas import AIAssistantRequest as AIAssistantRequest
from .extended_schemas import HashtagGroupCreateRequest as HashtagGroupCreateRequest
from .extended_schemas import CommunityCommentReplyRequest as CommunityCommentReplyRequest
from .extended_schemas import CustomReportRequest as CustomReportRequest
from .constants import SAVED_REPLY_NOT_FOUND as SAVED_REPLY_NOT_FOUND
from .constants import MESSAGE_NOT_FOUND as MESSAGE_NOT_FOUND
from .constants import _SW_AI_LOGGER as _SW_AI_LOGGER
from .constants import AVATAR_PRESET_CATALOG as AVATAR_PRESET_CATALOG
from .constants import REPORT_NOT_FOUND as REPORT_NOT_FOUND
from .constants import _INDUSTRY_RULES as _INDUSTRY_RULES
from .constants import _SW_AI_ALLOWED_ACTIONS as _SW_AI_ALLOWED_ACTIONS
from .constants import DEFAULT_FONT_FAMILY as DEFAULT_FONT_FAMILY
from .constants import DEFAULT_BACKGROUND_MEDIA as DEFAULT_BACKGROUND_MEDIA
from .constants import _DEFAULT_KEYWORDS as _DEFAULT_KEYWORDS
from .constants import UNSUPPORTED_SOCIAL_NETWORK as UNSUPPORTED_SOCIAL_NETWORK
from .constants import FACEBOOK_OAUTH_AUTHORIZE_URL as FACEBOOK_OAUTH_AUTHORIZE_URL
from .constants import ACCOUNT_NOT_FOUND as ACCOUNT_NOT_FOUND
from .constants import _STOP_WORDS as _STOP_WORDS
from .constants import REVIEW_NOT_FOUND as REVIEW_NOT_FOUND
from .constants import JSON_CONTENT_TYPE as JSON_CONTENT_TYPE
from .constants import OAUTH_PROVIDERS as OAUTH_PROVIDERS
from .constants import GOOGLE_OAUTH_AUTHORIZE_URL as GOOGLE_OAUTH_AUTHORIZE_URL
from .constants import OPENAI_CHAT_COMPLETIONS_URL as OPENAI_CHAT_COMPLETIONS_URL
from .constants import SCHEDULED_POST_NOT_FOUND as SCHEDULED_POST_NOT_FOUND
from .constants import _SW_AI_DEFAULT_POLICY as _SW_AI_DEFAULT_POLICY
from .constants import SUPPORTED_NETWORKS as SUPPORTED_NETWORKS
from .constants import READ_WRITE_SCOPE as READ_WRITE_SCOPE
from .constants import PUBLISH_MODE_PATTERN as PUBLISH_MODE_PATTERN
from .constants import DEFAULT_SUBTITLES_LANGUAGE as DEFAULT_SUBTITLES_LANGUAGE
from .constants import INTEGRATIONS_WEBHOOKS_ROUTE as INTEGRATIONS_WEBHOOKS_ROUTE
from .constants import DEFAULT_SOCIAL_AGENT as DEFAULT_SOCIAL_AGENT
from .constants import AuthDep as AuthDep
from .constants import TEN_AM_LABEL as TEN_AM_LABEL
from .constants import DEFAULT_SOCIAL_TIMEZONE as DEFAULT_SOCIAL_TIMEZONE
from .constants import START_PAGE_NOT_FOUND as START_PAGE_NOT_FOUND
from .constants import UGC_ASSET_NOT_FOUND as UGC_ASSET_NOT_FOUND
from .constants import VOICEOVER_GLOBAL_LIBRARY as VOICEOVER_GLOBAL_LIBRARY
from ...domains.social.schemas import ContactView
from ...domains.social.schemas import SocialAccountConnectRequest
from ...domains.social.schemas import BrandProfileRequest
from ...domains.social.schemas import BrandWebsiteFetchRequest
from ...domains.social.schemas import UgcTemplateProfileRequest
from ...domains.social.schemas import SocialEngageRequest
from ...domains.social.schemas import AutoPostRequest
from ...domains.social.schemas import ReviewReplyRequest
from ...domains.social.schemas import ReviewStatusRequest
from ...domains.social.schemas import ReviewCaseCreateRequest
from ...domains.social.schemas import InfluencerSearchRequest
from ...domains.social.schemas import InfluencerShortlistRequest
from ...domains.social.schemas import InfluencerAdvocacyBridgeRequest
from ...domains.social.schemas import AdvocacyAssetCreateRequest
from ...domains.social.schemas import AutomationRuleCreateRequest
from ...domains.social.schemas import AutomationRuleStatusRequest
from ...domains.social.schemas import AIAgentWorkflowExecuteRequest
from ...domains.social.schemas import BestStackProbeResultRequest
from ...domains.social.schemas import BestStackReportCreateRequest
from ...domains.social.schemas import CommentToDmRequest
from ...domains.social.schemas import DmChatbotReplyRequest
from ...domains.social.schemas import ApprovalCreateRequest
from ...domains.social.schemas import ApprovalRejectRequest
from ...domains.social.schemas import LinkShortenRequest
from ...domains.social.schemas import ConditionalRuleEvaluationRequest
from ...domains.social.schemas import IntegrationWebhookCreateRequest
from ...domains.social.schemas import IntegrationWebhookUpdateRequest
from ...domains.social.schemas import IntegrationWebhookTestRequest
from ...domains.social.schemas import CanvaImportRequest
from ...domains.social.schemas import BrowserExtensionCaptureRequest
from ...domains.social.schemas import BrowserExtensionQueueRequest
from ...domains.social.schemas import MobileDeviceRegisterRequest
from ...domains.social.schemas import MobileQuickPostRequest
from ...domains.social.schemas import MobileOfflineSyncRequest
from ...domains.social.schemas import PauseAllRequest
from ...domains.social.schemas import AutomationFeedCreateRequest
from ...domains.social.schemas import AutomationFeedStatusRequest
from ...domains.social.schemas import AutomationFeedSyncRequest
from ...domains.social.schemas import SocialIdeaCreateRequest
from ...domains.social.schemas import SocialIdeaQueueRequest
from ...domains.social.schemas import SavedReplyCreateRequest
from ...domains.social.schemas import SavedReplyUpdateRequest
from ...domains.social.schemas import SocialInboxRespondRequest
from ...domains.social.schemas import MessageClaimRequest
from ...domains.social.schemas import InboxBulkActionRequest
from ...domains.social.schemas import OAuthStartRequest
from ...domains.social.schemas import OAuthCallbackRequest
from ...domains.social.schemas import ConnectAllRequest
from ...domains.social.schemas import ListeningKeywordRequest
from ...domains.social.schemas import ListeningAlertDismissRequest
from ...domains.social.schemas import StreamCreateRequest
from ...domains.social.schemas import StreamUpdateRequest
from ...domains.social.schemas import CompetitorTrackRequest
from ...domains.social.schemas import AdCampaignCreateRequest
from ...domains.social.schemas import AdBoostRequest
from ...domains.social.schemas import ReportCreateRequest
from ...domains.social.schemas import BulkScheduleRequest
from ...domains.social.schemas import UgcApproveRequest
from ...domains.social.schemas import UgcRepublishRequest


def _register_social_suite_routes(st: _SocialWorkspaceState, router: APIRouter) -> None:
    get_competitor_insights.register(st, router)
    list_monitoring_streams.register(st, router)
    get_ads_analytics.register(st, router)
    list_bulk_schedule_jobs.register(st, router)
    get_ugc_performance.register(st, router)


def _register_enterprise_routes(st: _SocialWorkspaceState, router: APIRouter) -> None:
    list_social_ai_agent_templates.register(st, router)
    create_social_automation_feed.register(st, router)
    get_social_inbox_stats.register(st, router)
    delete_social_saved_reply.register(st, router)
    update_social_review_status.register(st, router)
    create_social_advocacy_asset.register(st, router)


def _register_account_routes(st: _SocialWorkspaceState, router: APIRouter) -> None:
    social_catalog.register(st, router)


def _register_oauth_routes(st: _SocialWorkspaceState, router: APIRouter) -> None:
    list_oauth_providers.register(st, router)


def _register_brand_routes(st: _SocialWorkspaceState, router: APIRouter) -> None:
    get_brand_profile.register(st, router)


def _register_engagement_routes(st: _SocialWorkspaceState, router: APIRouter) -> None:
    social_workspace_overview.register(st, router)


def _register_buffer_parity_routes(st: _SocialWorkspaceState, router: APIRouter) -> None:
    list_hashtag_groups.register(st, router)
    get_publishing_queue.register(st, router)
    create_approval_request.register(st, router)
    receive_incoming_webhook.register(st, router)
    register_mobile_device.register(st, router)
    create_content_template.register(st, router)
    delete_community_saved_reply.register(st, router)
    repurpose_longform_asset.register(st, router)
    track_start_page_link_click.register(st, router)


from ...domains.social.persistence import _SocialWorkspaceState
from ...domains.social.persistence import _is_real_production_environment
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any


def create_social_workspace_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    social_accounts_memory: list[dict[str, Any]],
    brand_profiles_memory: list[dict[str, Any]],
    inbox_messages_memory: list[dict[str, Any]],
    competitor_profiles_memory: list[dict[str, Any]],
    competitor_snapshots_memory: list[dict[str, Any]],
    notifications_memory: list[dict[str, Any]],
    scheduled_posts_memory: list[dict[str, Any]],
    viralpost_post_history_memory: list[dict[str, Any]],
    db_ready_fn: Callable[[], bool] | None = None,
    db_dsn_fn: Callable[[], str] | None = None,
) -> APIRouter:
    db_backing_enabled = False
    try:
        if db_ready_fn is not None and db_dsn_fn is not None:
            db_backing_enabled = bool(db_dsn_fn().strip()) and bool(db_ready_fn())
    except Exception:
        db_backing_enabled = False
    if _is_real_production_environment() and (not db_backing_enabled):
        raise RuntimeError(
            "Social Workspace requires durable PostgreSQL backing in production; memory-backed state is disabled."
        )
    startup_blockers = _strict_social_startup_blockers(db_backing_enabled=db_backing_enabled)
    if startup_blockers:
        joined = "; ".join(startup_blockers)
        raise RuntimeError(f"Strict social startup validation failed: {joined}")
    router = APIRouter()
    st = _SocialWorkspaceState(
        enforce_rate_limit=enforce_rate_limit,
        audit_log=audit_log_memory,
        social_accounts=social_accounts_memory,
        brand_profiles=brand_profiles_memory,
        inbox_messages=inbox_messages_memory,
        competitor_profiles=competitor_profiles_memory,
        competitor_snapshots=competitor_snapshots_memory,
        notifications=notifications_memory,
        scheduled_posts=scheduled_posts_memory,
        viralpost_history=viralpost_post_history_memory,
        db_ready_fn=db_ready_fn if db_ready_fn is not None else lambda: False,
        db_dsn_fn=db_dsn_fn if db_dsn_fn is not None else lambda: "",
    )
    _register_account_routes(st, router)
    _register_oauth_routes(st, router)
    _register_brand_routes(st, router)
    _register_engagement_routes(st, router)
    _register_enterprise_routes(st, router)
    _register_social_suite_routes(st, router)
    _register_buffer_parity_routes(st, router)
    return router
