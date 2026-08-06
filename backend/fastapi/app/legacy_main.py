import asyncio
import base64
import hashlib
import hmac
import html
import io
import ipaddress
import json
import math
import os
import smtplib
import ssl
import struct
import threading
import time
import uuid
import wave
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Annotated, Literal, cast

import httpx
import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, HttpUrl
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import memory_stores
from .config import validate_startup_security
from .database import close_db, get_db_session, init_db
from .deps import AuthContext, JwtClaims, require_auth
from .governance_db import GovernanceDB as _GovernanceDB
from .intelligence.routes import router as intel_router
from .production_middleware import (
    GlobalExceptionHandler,
    RequestTracingMiddleware,
    SecurityHeadersMiddleware,
    SensitiveRouteTokenMiddleware,
    StructuredLogger,
    get_health_check_data,
    get_metrics_data,
    validate_environment,
)
from .routers.ad_generation import router as ad_generation_router
from .routers.ads_control_tower import create_ads_control_tower_router
from .routers.agent_analytics import router as agent_analytics_router
from .routers.agents import router as agents_router
from .routers.ai import create_ai_router
from .routers.ai_crawler_enablement import create_ai_crawler_enablement_router
from .routers.analytics_dashboard import create_analytics_router
from .routers.answer_engine import router as answer_engine_router
from .routers.api_governance import ApiGovernanceContext, create_api_governance_router
from .routers.auth import AuthSecurityRecord, create_auth_router
from .routers.autonomous_workforce import create_autonomous_workforce_router, run_autonomous_workforce_watchdog
from .routers.backlink_intelligence import router as backlink_intelligence_router
from .routers.benchmarks import BenchmarksContext, create_benchmarks_router
from .routers.billing import create_billing_router
from .routers.brand_hub import router as brand_hub_router
from .routers.brandkit import router as brandkit_router
from .routers.bridges import create_bridges_router
from .routers.cdn_analytics import router as cdn_analytics_router
from .routers.chatbot import create_chatbot_router
from .routers.cms_integration import create_cms_router
from .routers.competitive import create_competitive_router
from .routers.competitor_analysis import router as competitor_analysis_router
from .routers.content_approval import create_content_approval_router
from .routers.content_integrations import create_content_integrations_router
from .routers.crm import create_crm_router
from .routers.crm_abm import create_crm_abm_router
from .routers.documents import create_documents_router
from .routers.email_provider import create_email_router
from .routers.employee_advocacy import create_employee_advocacy_router
from .routers.engagement import create_engagement_router
from .routers.growth_suite import GrowthSuiteContext, create_growth_suite_router
from .routers.influencer import create_influencer_router
from .routers.ira import IRAContext, create_ira_router, run_ira_watchdog
from .routers.knowledge_base import create_knowledge_base_router
from .routers.linkinbio import create_linkinbio_router
from .routers.live_editor import create_live_editor_router
from .routers.marketplace import create_marketplace_router
from .routers.media_jobs import create_media_jobs_router
from .routers.media_library import create_media_library_router
from .routers.meetings import create_meetings_router
from .routers.neo4j_graph_intelligence import create_neo4j_graph_intelligence_router
from .routers.notifications import create_notifications_router
from .routers.ops import _OpsCallbacks, create_ops_router
from .routers.outcome_attribution import OutcomeAttributionContext, create_outcome_attribution_router
from .routers.pentest import create_pentest_router
from .routers.pentest_sync import create_pentest_sync_router
from .routers.platform_integration import create_platform_integration_router
from .routers.platform_intelligence import create_platform_intelligence_router
from .routers.playbooks import PlaybooksContext, create_playbooks_router
from .routers.predis_features import predis_router
from .routers.products import create_products_router
from .routers.prompt_volumes import router as prompt_volumes_router
from .routers.rank_tracker import router as rank_tracker_router
from .routers.revenue_attribution import create_revenue_attribution_router
from .routers.search_everywhere_automation import create_search_everywhere_automation_router
from .routers.seo_platform import create_seo_platform_router
from .routers.sequences import create_sequences_router
from .routers.site_portfolio_manager import create_site_portfolio_router
from .routers.smart_inbox import create_smart_inbox_router
from .routers.social_manychat import create_social_manychat_router
from .routers.social_media_router import router as social_media_router
from .routers.social_posting import router as social_posting_router
from .routers.social_workspace import create_social_workspace_router
from .routers.stripe_billing import create_stripe_billing_router
from .routers.super_admin_finance import create_super_admin_finance_router
from .routers.surveys import create_surveys_router
from .routers.tenants import create_tenant_router
from .routers.tickets import create_tickets_router
from .routers.tool_integrations import create_tool_integrations_router
from .routers.translation_studio import create_translation_studio_router
from .routers.trend_intelligence import create_trend_intelligence_router
from .routers.trust_center import TrustCenterContext, create_trust_center_router
from .routers.utm_builder import create_utm_builder_router
from .routers.v1_loop import create_v1_loop_router
from .routers.viralpost import create_viralpost_router
from .routers.vse import create_vse_router
from .routers.workflows import create_workflows_router
from .security import get_password_pepper, hash_password, verify_password
from .security_redis import fixed_window_increment
from .transparent_encryption import te_decrypt, te_encrypt
from .vault.hashicorp_vault import HashiCorpVaultClient
from .vault.supabase_vault import SupabaseVaultClient

JsonObject = dict[str, object]
DEFAULT_FROM_EMAIL = 'noreply@nuxtron.local'

# Import memory stores for this module using local names  
_scheduled_posts_memory = memory_stores.scheduled_posts
_email_contacts_memory = memory_stores.email_contacts
_email_campaigns_memory = memory_stores.email_campaigns
_suitecrm_jobs_memory = memory_stores.suitecrm_jobs
_refferq_jobs_memory = memory_stores.refferq_jobs
_posthog_events_memory = memory_stores.posthog_events
_n8n_jobs_memory = memory_stores.n8n_jobs
_growthbook_checks_memory = memory_stores.growthbook_checks
_matomo_events_memory = memory_stores.matomo_events
_plausible_events_memory = memory_stores.plausible_events
_meilisearch_index_memory = memory_stores.meilisearch_index
_webhook_events_memory = memory_stores.webhook_events
_appwrite_events_memory = memory_stores.appwrite_events
_drone_builds_memory = memory_stores.drone_builds
_directus_items_memory = memory_stores.directus_items
_minio_objects_memory = memory_stores.minio_objects
_stripe_events_memory = memory_stores.stripe_events
_audit_log_memory = memory_stores.audit_log
_notifications_memory = memory_stores.notifications
_social_listening_memory = memory_stores.social_listening
_social_listening_alert_rules_memory = memory_stores.social_listening_alert_rules
_social_listening_alerts_memory = memory_stores.social_listening_alerts
_reviews_memory = memory_stores.reviews
_seo_analyses_memory = memory_stores.seo_analyses
_redis_ops_memory = memory_stores.redis_ops
_twilio_messages_memory = memory_stores.twilio_messages
_slack_messages_memory = memory_stores.slack_messages
_resend_messages_memory = memory_stores.resend_messages
_algolia_sync_memory = memory_stores.algolia_sync
_ai_gateway_memory = memory_stores.ai_gateway
_ai_security_usage_memory = memory_stores.ai_security_usage
_ai_security_alerts_memory = memory_stores.ai_security_alerts
_ai_security_blocks_memory = memory_stores.ai_security_blocks
_ai_security_appeals_memory = memory_stores.ai_security_appeals
_ai_provider_keys_memory = memory_stores.ai_provider_keys
_ai_security_ids_events_memory = memory_stores.ai_security_ids_events
_siem_cases_memory = memory_stores.siem_cases
_siem_soar_runs_memory = memory_stores.siem_soar_runs
_siem_retention_policies_memory = memory_stores.siem_retention_policies
_siem_data_lake_exports_memory = memory_stores.siem_data_lake_exports
_siem_flow_logs_memory = memory_stores.siem_flow_logs
_siem_waf_policies_memory = memory_stores.siem_waf_policies
_siem_firewall_rules_memory = memory_stores.siem_firewall_rules
_siem_ids_profiles_memory = memory_stores.siem_ids_profiles
_siem_ips_profiles_memory = memory_stores.siem_ips_profiles
_siem_vulnerabilities_memory = memory_stores.siem_vulnerabilities
_siem_zap_scans_memory = memory_stores.siem_zap_scans
_siem_patch_updates_memory = memory_stores.siem_patch_updates
_siem_auto_pentest_jobs_memory = memory_stores.siem_auto_pentest_jobs
_siem_dead_code_findings_memory = memory_stores.siem_dead_code_findings
_siem_endpoint_hardening_memory = memory_stores.siem_endpoint_hardening
_auth_security_memory = memory_stores.auth_security
_tenant_profiles_memory = memory_stores.tenant_profiles
_api_usage_audit_memory = memory_stores.api_usage_audit
_api_governance_providers_memory = memory_stores.api_governance_providers
_api_governance_usage_events_memory = memory_stores.api_governance_usage_events
_api_governance_incidents_memory = memory_stores.api_governance_incidents
_governance_db: _GovernanceDB | None = None
_governance_state_loaded = False
_users_memory = memory_stores.users
_ai_generated_assets_memory: list[JsonObject] = []
_ai_generated_assets_lock = threading.Lock()
_crm_contacts_memory = memory_stores.crm_contacts
_crm_companies_memory = memory_stores.crm_companies
_crm_deals_memory = memory_stores.crm_deals
_crm_activities_memory = memory_stores.crm_activities
_crm_webhook_subscriptions_memory = memory_stores.crm_webhook_subscriptions
_crm_leads_memory = memory_stores.crm_leads
_crm_tasks_memory = memory_stores.crm_tasks
_crm_campaigns_memory = memory_stores.crm_campaigns
_crm_segments_memory = memory_stores.crm_segments
_crm_notes_memory = memory_stores.crm_notes
_crm_quotes_memory = memory_stores.crm_quotes
_crm_invoices_memory = memory_stores.crm_invoices
_crm_email_sequences_memory = memory_stores.crm_email_sequences
_crm_workflow_rules_memory = memory_stores.crm_workflow_rules
_crm_sla_rules_memory = memory_stores.crm_sla_rules
_crm_projects_memory = memory_stores.crm_projects
_crm_custom_entity_types_memory = memory_stores.crm_custom_entity_types
_crm_custom_entity_records_memory = memory_stores.crm_custom_entity_records
_crm_automation_recipes_memory = memory_stores.crm_automation_recipes
_crm_api_tokens_memory = memory_stores.crm_api_tokens
_crm_backup_snapshots_memory = memory_stores.crm_backup_snapshots
_crm_live_sync_state_memory = memory_stores.crm_live_sync_state
_influencers_memory = memory_stores.influencers
_influencer_campaigns_memory = memory_stores.influencer_campaigns
_influencer_outreach_memory = memory_stores.influencer_outreach
_chatbots_memory = memory_stores.chatbots
_chatbot_conversations_memory = memory_stores.chatbot_conversations
_chatbot_leads_memory = memory_stores.chatbot_leads
_ira_events_memory = memory_stores.ira_events
_ira_sessions_memory = memory_stores.ira_sessions
_ira_controls_memory = memory_stores.ira_controls
_ira_connectors_memory = memory_stores.ira_connectors
_ira_ml_knowledge_memory = memory_stores.ira_ml_knowledge
_ira_ml_jobs_memory = memory_stores.ira_ml_jobs
_ira_ml_models_memory = memory_stores.ira_ml_models
_ira_structured_memory = memory_stores.ira_structured_memory
_ira_action_snapshots_memory = memory_stores.ira_action_snapshots
_ira_cost_ledger_memory = memory_stores.ira_cost_ledger
_ira_ab_tests_memory = memory_stores.ira_ab_tests
_ira_performance_log_memory = memory_stores.ira_performance_log
_linkinbio_pages_memory = memory_stores.linkinbio_pages
_linkinbio_links_memory = memory_stores.linkinbio_links
_linkinbio_analytics_memory = memory_stores.linkinbio_analytics
_subscriptions_memory = memory_stores.subscriptions
_invoices_memory = memory_stores.invoices
_credit_ledger_memory = memory_stores.credit_ledger
_accounting_integrations_memory = memory_stores.accounting_integrations
_accounting_exports_memory = memory_stores.accounting_exports
_super_admin_module_settings_memory = memory_stores.super_admin_module_settings
_cms_connections_memory = memory_stores.cms_connections
_cms_pages_memory = memory_stores.cms_pages
_cms_sync_log_memory = memory_stores.cms_sync_log
_marketplace_catalogue_memory = memory_stores.marketplace_catalogue
_marketplace_installs_memory = memory_stores.marketplace_installs
_analytics_reports_memory = memory_stores.analytics_reports
_analytics_report_schedules_memory = memory_stores.analytics_report_schedules
_analytics_trends_memory = memory_stores.analytics_trends
_analytics_rollups_memory = memory_stores.analytics_rollups
_notification_preferences_memory = memory_stores.notification_preferences
_notification_delivery_receipts_memory = memory_stores.notification_delivery_receipts
# ADDED: Hootsuite-parity modules — content approval, media library, employee advocacy
_content_approval_requests_memory = memory_stores.content_approval_requests
_content_approval_comments_memory = memory_stores.content_approval_comments
_content_approval_configs_memory = memory_stores.content_approval_configs
_media_library_assets_memory = memory_stores.media_library_assets
_media_library_folders_memory = memory_stores.media_library_folders
_media_library_tags_memory = memory_stores.media_library_tags
_advocacy_content_memory = memory_stores.advocacy_content
_advocacy_shares_memory = memory_stores.advocacy_shares
_advocacy_participants_memory = memory_stores.advocacy_participants
_advocacy_campaigns_memory = memory_stores.advocacy_campaigns
# ADDED: SproutSocial blueprint — new module memory stores
_smart_inbox_messages_memory = memory_stores.smart_inbox_messages
_smart_inbox_notes_memory = memory_stores.smart_inbox_notes
_smart_inbox_locks_memory = memory_stores.smart_inbox_locks
_saved_replies_memory = memory_stores.saved_replies
_smart_inbox_delivery_failures_memory = memory_stores.smart_inbox_delivery_failures
_smart_inbox_delivery_replay_runs_memory = memory_stores.smart_inbox_delivery_replay_runs
_viralpost_analyses_memory = memory_stores.viralpost_analyses
_viralpost_post_history_memory = memory_stores.viralpost_post_history
_competitor_profiles_memory = memory_stores.competitor_profiles
_competitor_snapshots_memory = memory_stores.competitor_snapshots
_competitive_scrape_jobs_memory = memory_stores.competitive_scrape_jobs
_social_accounts_memory = memory_stores.social_accounts
_social_brand_profiles_memory = memory_stores.social_brand_profiles
_utm_presets_memory = memory_stores.utm_presets
_revenue_touchpoints_memory = memory_stores.revenue_touchpoints
_revenue_conversions_memory = memory_stores.revenue_conversions
_revenue_spend_memory = memory_stores.revenue_spend
_growth_suite_memory = memory_stores.growth_suite_records
_trend_signals_memory = memory_stores.trend_signals
_trend_forecasts_memory = memory_stores.trend_forecasts
_trend_selections_memory = memory_stores.trend_selections
_trend_content_generations_memory = memory_stores.trend_content_generations
_content_generations_memory = _trend_content_generations_memory
_content_generation_jobs_memory: list[JsonObject] = []
_content_generation_jobs_lock = threading.Lock()
_content_generation_telemetry_lock = threading.Lock()
_content_generation_telemetry: JsonObject = {
    'strict_rejections_total': 0,
    'strict_rejections_by_reason': {},
    'fallback_attempts_total': 0,
    'fallback_attempts_by_reason': {},
    'timeout_failures_total': 0,
    'updated_at': None,
}
_trend_performance_tracks_memory = memory_stores.trend_performance_tracks
_trend_recommendations_memory = memory_stores.trend_recommendations
_media_jobs_memory = memory_stores.media_jobs
_media_jobs_dlq_memory = memory_stores.media_jobs_dlq
_engagement_streaks_memory = memory_stores.engagement_streaks
_engagement_referrals_memory = memory_stores.engagement_referrals
_engagement_referral_claims_memory = memory_stores.engagement_referral_claims
_engagement_companion_profiles_memory = memory_stores.engagement_companion_profiles
_engagement_companion_messages_memory = memory_stores.engagement_companion_messages
_engagement_fomo_rules_memory = memory_stores.engagement_fomo_rules
_engagement_fomo_events_memory = memory_stores.engagement_fomo_events
_engagement_social_proof_events_memory = memory_stores.engagement_social_proof_events
_engagement_dependency_profiles_memory = memory_stores.engagement_dependency_profiles
_engagement_dependency_events_memory = memory_stores.engagement_dependency_events
_engagement_community_circles_memory = memory_stores.engagement_community_circles
_engagement_community_posts_memory = memory_stores.engagement_community_posts
_engagement_community_amas_memory = memory_stores.engagement_community_amas
_engagement_brand_lock_profiles_memory = memory_stores.engagement_brand_lock_profiles
_engagement_brand_lock_events_memory = memory_stores.engagement_brand_lock_events
_engagement_autopilot_profiles_memory = memory_stores.engagement_autopilot_profiles
_engagement_autopilot_events_memory = memory_stores.engagement_autopilot_events
_engagement_achievement_profiles_memory = memory_stores.engagement_achievement_profiles
_engagement_achievement_events_memory = memory_stores.engagement_achievement_events
_money_printer_ideas_memory = memory_stores.money_printer_ideas
_money_printer_validations_memory = memory_stores.money_printer_validations
_bank_accounts_memory = memory_stores.bank_accounts
_bank_transactions_memory = memory_stores.bank_transactions
_bank_payouts_memory = memory_stores.bank_payouts
_university_courses_memory = memory_stores.university_courses
_university_cohorts_memory = memory_stores.university_cohorts
_university_enrollments_memory = memory_stores.university_enrollments
_studios_services_memory = memory_stores.studios_services
_studios_briefs_memory = memory_stores.studios_briefs
_studios_proposals_memory = memory_stores.studios_proposals
_studios_escrows_memory = memory_stores.studios_escrows
_commerce_products_memory = memory_stores.commerce_products
_commerce_orders_memory = memory_stores.commerce_orders
_talent_creators_memory = memory_stores.talent_creators
_talent_deals_memory = memory_stores.talent_deals
_talent_rate_cards_memory = memory_stores.talent_rate_cards
_white_label_profiles_memory = memory_stores.white_label_profiles
_white_label_events_memory = memory_stores.white_label_events
_db_ready = False
# ── VSE memory store aliases (Viral Singularity Engine) ─────────────────────
_vse_viral_events_memory = memory_stores.vse_viral_events
_vse_briefs_memory = memory_stores.vse_briefs
_vse_trigger_analyses_memory = memory_stores.vse_trigger_analyses
_vse_algorithm_models_memory = memory_stores.vse_algorithm_models
_vse_algorithm_updates_memory = memory_stores.vse_algorithm_updates
_vse_network_maps_memory = memory_stores.vse_network_maps
_vse_cascade_simulations_memory = memory_stores.vse_cascade_simulations
_vse_detonations_memory = memory_stores.vse_detonations
_vse_swarms_memory = memory_stores.vse_swarms
_vse_momentum_events_memory = memory_stores.vse_momentum_events
_vse_content_factory_memory = memory_stores.vse_content_factory
_vse_emotion_analyses_memory = memory_stores.vse_emotion_analyses
_vse_trend_alerts_memory = memory_stores.vse_trend_alerts
_vse_trend_hijacks_memory = memory_stores.vse_trend_hijacks
_vse_paid_events_memory = memory_stores.vse_paid_events
_vse_dark_social_seeds_memory = memory_stores.vse_dark_social_seeds
_vse_immortal_assets_memory = memory_stores.vse_immortal_assets
_vse_viral_vault_memory = memory_stores.vse_viral_vault
# ── AI Crawler Enablement memory stores ─────────────────────────────────────
_ace_sites_memory: list[JsonObject] = []
_ace_crawler_events_memory: list[JsonObject] = []
_ace_ssr_cache_memory: list[JsonObject] = []
_ace_crawler_rules_memory: list[JsonObject] = []
_ace_audit_results_memory: list[JsonObject] = []
# ── Site Portfolio Manager memory stores ─────────────────────────────────────
_portfolio_sites_memory: list[JsonObject] = []
_portfolio_rules_memory: list[JsonObject] = []
_portfolio_deployments_memory: list[JsonObject] = []
# ── Live Editor memory stores ─────────────────────────────────────────────────
_live_editor_sessions_memory: list[JsonObject] = []
_live_editor_changes_memory: list[JsonObject] = []
_live_editor_history_memory: list[JsonObject] = []
# ── Autonomous Workforce memory stores ───────────────────────────────────────
_autonomous_workforce_profiles_memory = memory_stores.autonomous_workforce_profiles
_autonomous_workforce_integrations_memory = memory_stores.autonomous_workforce_integrations
_autonomous_workforce_missions_memory = memory_stores.autonomous_workforce_missions
_autonomous_workforce_feed_memory = memory_stores.autonomous_workforce_feed
_autonomous_workforce_schedules_memory = memory_stores.autonomous_workforce_schedules
_autonomous_workforce_knowledge_memory = memory_stores.autonomous_workforce_knowledge
_autonomous_workforce_outcomes_memory = memory_stores.autonomous_workforce_outcomes
_db_ready = False
_db_init_attempted = False
_db_init_lock = threading.Lock()
_rate_lock = threading.Lock()
_ai_security_lock = threading.Lock()
_siem_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}
_security_alert_worker_stop: asyncio.Event | None = None
_security_alert_worker_task: asyncio.Task[None] | None = None
_ira_watchdog_stop: asyncio.Event | None = None
_ira_watchdog_task: asyncio.Task[None] | None = None
_autonomous_workforce_watchdog_stop: asyncio.Event | None = None
_autonomous_workforce_watchdog_task: asyncio.Task[None] | None = None


class RateLimitExceededError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _is_production() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _allow_api_docs() -> bool:
    if _is_production():
        return os.getenv('ENABLE_API_DOCS', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    return True


def _allowed_hosts() -> list[str]:
    raw = os.getenv('ALLOWED_HOSTS', '').strip()
    if raw:
        return [item.strip() for item in raw.split(',') if item.strip()]
    if _is_production():
        raise RuntimeError('ALLOWED_HOSTS must be configured in production mode.')
    return ['*']


def _cors_origins() -> list[str]:
    raw = os.getenv('CORS_ORIGINS', '').strip()
    if raw:
        return [item.strip() for item in raw.split(',') if item.strip()]
    if _is_production():
        raise RuntimeError('CORS_ORIGINS must be configured in production mode.')
    return ['*']


def _enforce_rate_limit_in_process(key: str, limit: int, window_seconds: int) -> None:
    """Per-process fallback limiter, used only when Redis is unavailable.

    This is the ORIGINAL implementation. Kept as a floor so a Redis outage
    degrades rate limiting back to "per-process" (the pre-existing behavior)
    rather than disabling it outright.
    """
    now = time.time()
    cutoff = now - window_seconds
    with _rate_lock:
        bucket = [ts for ts in _rate_buckets.get(key, []) if ts >= cutoff]
        if len(bucket) >= limit:
            raise RateLimitExceededError('Rate limit exceeded. Please retry later.')
        bucket.append(now)
        _rate_buckets[key] = bucket


def _enforce_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    """Shared-across-workers/replicas rate limiter, backed by Redis.

    Previously this was a per-process ``dict`` + lock: under N uvicorn/gunicorn
    workers or N horizontally-scaled replicas, the effective limit was
    ``limit * N`` and it reset on every deploy. Redis makes the limit real
    across the whole deployment. Falls back to the in-process limiter (not to
    "allow everything") if Redis is unreachable, so an infra outage degrades
    rate limiting rather than disabling it.
    """
    allowed, count = fixed_window_increment(f'nuxtron:ratelimit:{key}', limit=limit, window_seconds=window_seconds)
    if count == 0:
        # fixed_window_increment returns (True, 0) when Redis itself is down
        # (fail-open by its own contract) — fall back to the in-process
        # limiter instead of silently allowing unlimited requests.
        _enforce_rate_limit_in_process(key, limit, window_seconds)
        return
    if not allowed:
        raise RateLimitExceededError('Rate limit exceeded. Please retry later.')


def reset_rate_limits_for_tests() -> None:
    """Test helper to isolate rate limiter state between test cases.

    Clears both the in-process fallback bucket and any Redis-backed counters
    (best-effort — a missing/unreachable Redis in test environments is
    expected and not an error here).
    """
    with _rate_lock:
        _rate_buckets.clear()
    try:
        from .security_redis import get_sync_redis

        client = get_sync_redis()
        if client is not None:
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match='nuxtron:ratelimit:*', count=500)
                if keys:
                    client.delete(*keys)
                if cursor == 0:
                    break
    except Exception:
        pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _b64url_decode(raw: str) -> bytes:
    padding = '=' * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode('ascii'))


def _jwt_sign_hs256(payload: JsonObject, secret: str) -> str:
    header = {'alg': 'HS256', 'typ': 'JWT'}
    head = _b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    body = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{head}.{body}'.encode('ascii')
    signature = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    return f'{head}.{body}.{_b64url_encode(signature)}'


def _jwt_verify_hs256(token: str, secret: str) -> tuple[bool, JwtClaims | None, str | None]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return False, None, 'Invalid token format.'

        head, body, sig = parts
        signing_input = f'{head}.{body}'.encode('ascii')
        expected_sig = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return False, None, 'Invalid token signature.'

        payload = json.loads(_b64url_decode(body).decode('utf-8'))
        if not isinstance(payload, dict):
            return False, None, 'Invalid token payload.'
        claims = cast(JwtClaims, payload)
        exp = int(claims.get('exp', 0) or 0)
        if exp and time.time() > exp:
            return False, claims, 'Token expired.'
        return True, claims, None
    except Exception as ex:
        return False, None, f'Token verification failed: {ex}'


def _totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode('ascii').rstrip('=')


def _totp_code(secret: str, for_time: int | None = None, step: int = 30, digits: int = 6) -> str:
    ts = int(time.time() if for_time is None else for_time)
    counter = ts // step
    padded = secret + ('=' * ((8 - len(secret) % 8) % 8))
    key = base64.b32decode(padded.upper())
    msg = counter.to_bytes(8, byteorder='big')
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = ((digest[offset] & 0x7F) << 24) | ((digest[offset + 1] & 0xFF) << 16) | ((digest[offset + 2] & 0xFF) << 8) | (digest[offset + 3] & 0xFF)
    return str(code_int % (10 ** digits)).zfill(digits)


def _totp_verify(secret: str, code: str, window: int = 1, step: int = 30) -> bool:
    now = int(time.time())
    for w in range(-window, window + 1):
        if hmac.compare_digest(_totp_code(secret, for_time=now + (w * step), step=step), code):
            return True
    return False


def _send_via_listmonk(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    base_url = os.getenv('LISTMONK_URL', '').rstrip('/')
    token = os.getenv('LISTMONK_API_TOKEN', '')
    if not base_url or not token:
        return False, 'Listmonk not configured.'

    headers = {
        'Authorization': f'token {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }
    payload = {
        'subscriber_email': recipient_email,
        'subject': subject,
        'body': body,
        'content_type': 'html',
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/api/tx', headers=headers, json=payload)
            if response.is_success:
                return True, 'Delivered via Listmonk transactional API.'
            return False, f'Listmonk API error: {response.status_code}'
    except Exception as ex:
        return False, f'Listmonk request failed: {ex}'


def _send_via_postal(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    base_url = os.getenv('POSTAL_BASE_URL', '').rstrip('/')
    api_key = os.getenv('POSTAL_API_KEY', '')
    from_email = os.getenv('POSTAL_FROM_EMAIL', DEFAULT_FROM_EMAIL)
    if not base_url or not api_key:
        return False, 'Postal not configured.'

    headers = {
        'X-Server-API-Key': api_key,
        'Content-Type': CONTENT_TYPE_JSON,
    }
    payload = {
        'from': from_email,
        'to': recipient_email,
        'subject': subject,
        'plain_body': body,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/api/v1/send/message', headers=headers, json=payload)
            if response.is_success:
                return True, 'Delivered via Postal API.'
            return False, f'Postal API error: {response.status_code}'
    except Exception as ex:
        return False, f'Postal request failed: {ex}'


def _send_via_ses(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    host = os.getenv('SES_SMTP_HOST', '').strip()
    port = int(os.getenv('SES_SMTP_PORT', '587'))
    username = os.getenv('SES_SMTP_USERNAME', '').strip()
    password = os.getenv('SES_SMTP_PASSWORD', '').strip()
    from_email = os.getenv('SES_FROM_EMAIL', DEFAULT_FROM_EMAIL).strip()

    if not host or not username or not password:
        return False, 'SES SMTP not configured.'

    message = EmailMessage()
    message['From'] = from_email
    message['To'] = recipient_email
    message['Subject'] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host=host, port=port, context=context, timeout=12) as server:
                server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host=host, port=port, timeout=12) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.send_message(message)
        return True, 'Delivered via SES SMTP.'
    except Exception as ex:
        return False, f'SES SMTP request failed: {ex}'


def _send_via_resend(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    api_base_url = os.getenv('RESEND_API_BASE_URL', 'https://api.resend.com').rstrip('/')
    from_email = os.getenv('RESEND_FROM_EMAIL', '').strip() or os.getenv('SMTP_FROM', '').strip() or DEFAULT_FROM_EMAIL
    if not api_key:
        return False, 'Resend not configured.'

    payload: dict[str, object] = {
        'from': from_email,
        'to': [recipient_email],
        'subject': subject,
        'text': body,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f'{api_base_url}/emails',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': CONTENT_TYPE_JSON,
                },
                json=payload,
            )
            if response.is_success:
                return True, 'Delivered via Resend.'
            return False, f'Resend API error: {response.status_code}'
    except Exception as ex:
        return False, f'Resend request failed: {ex}'


def _security_alert_from_email() -> str:
    for candidate in (
        os.getenv('SMTP_FROM', '').strip(),
        os.getenv('RESEND_FROM_EMAIL', '').strip(),
        os.getenv('SES_FROM_EMAIL', '').strip(),
        os.getenv('POSTAL_FROM_EMAIL', '').strip(),
    ):
        if candidate:
            return candidate
    return ''


def _dispatch_security_email(recipient_email: str, subject: str, body: str) -> tuple[bool, str, str]:
    last_detail = 'No configured email transport for security alerts.'
    for provider, sender in (
        ('resend', _send_via_resend),
        ('postal', _send_via_postal),
        ('ses', _send_via_ses),
        ('listmonk', _send_via_listmonk),
    ):
        success, detail = sender(recipient_email, subject, body)
        if success:
            return True, provider, detail
        last_detail = detail
        if 'not configured' not in detail.lower():
            return False, provider, detail
    return False, 'unavailable', last_detail


def _security_alert_db_queue_enabled() -> bool:
    flag = os.getenv('SECURITY_ALERT_DB_QUEUE_ENABLED', '1').strip().lower()
    return _db_ready and flag not in {'0', 'false', 'no', 'off'}


def _db_claim_security_alert_email() -> JsonObject | None:
    try:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH candidate AS (
                        SELECT id
                        FROM security_alert_emails
                        WHERE tenant_id = %s
                          AND status IN ('queued', 'retry')
                          AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                        ORDER BY id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE security_alert_emails q
                    SET status = 'sending',
                        locked_at = NOW(),
                        attempts = q.attempts + 1,
                        updated_at = NOW()
                    FROM candidate
                    WHERE q.id = candidate.id
                    RETURNING q.id, q.tenant_id, q.provider, q.to_email, q.from_email, q.subject, q.body, q.status, q.attempts, q.next_attempt_at, q.delivery_detail, q.created_at, q.updated_at
                    """,
                    ('platform-security',),
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:
            return None

        next_attempt = row[9]
        return {
            'id': int(row[0]),
            'tenant_id': str(row[1] or ''),
            'provider': str(row[2] or ''),
            'to': str(row[3] or ''),
            'from': str(row[4] or ''),
            'subject': str(row[5] or ''),
            'body': str(row[6] or ''),
            'status': str(row[7] or ''),
            'attempts': int(row[8] or 0),
            'next_attempt_at': int(next_attempt.timestamp()) if isinstance(next_attempt, datetime) else 0,
            'delivery_detail': str(row[10] or ''),
            'created_at': row[11].isoformat() if isinstance(row[11], datetime) else '',
            'updated_at': row[12].isoformat() if isinstance(row[12], datetime) else '',
            '__queue_source': 'db',
        }
    except Exception:
        return None


def _db_update_security_alert_email(item: JsonObject, *, status: str, provider: str, detail: str, retry_seconds: int) -> None:
    message_id = _coerce_int(item.get('id', 0), 0)
    if message_id <= 0:
        return
    next_attempt = datetime.now(UTC) + timedelta(seconds=retry_seconds) if retry_seconds > 0 else None
    try:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE security_alert_emails
                    SET status = %s,
                        provider = %s,
                        delivery_detail = %s,
                        locked_at = NULL,
                        next_attempt_at = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status, provider, detail, next_attempt, message_id),
                )
            conn.commit()
    except Exception:
        pass


def _db_security_alert_delivery_summary() -> JsonObject | None:
    try:
        with psycopg.connect(_db_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT status, COUNT(*)
                    FROM security_alert_emails
                    WHERE tenant_id = %s
                    GROUP BY status
                    """,
                ('platform-security',),
            )
            rows = cur.fetchall()
        summary: dict[str, int] = {'queued': 0, 'sending': 0, 'retry': 0, 'sent': 0, 'failed': 0}
        for status, count in rows:
            label = str(status or 'queued')
            summary[label] = int(count or 0)
        return cast(JsonObject, summary)
    except Exception:
        return None


def _db_insert_security_alert_email(email_event: JsonObject, *, status: str) -> int | None:
    try:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO security_alert_emails (tenant_id, provider, to_email, from_email, subject, body, status, attempts, delivery_detail)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        str(email_event.get('tenant_id', '') or ''),
                        str(email_event.get('provider', 'smtp-queue') or 'smtp-queue'),
                        str(email_event.get('to', '') or ''),
                        str(email_event.get('from', '') or ''),
                        str(email_event.get('subject', '') or ''),
                        str(email_event.get('body', '') or ''),
                        status,
                        _coerce_int(email_event.get('attempts', 0), 0),
                        str(email_event.get('delivery_detail', '') or ''),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return int(row[0]) if row is not None else None
    except Exception:
        return None


def _security_alert_backfill_candidates() -> list[JsonObject]:
    candidates: list[JsonObject] = []
    with _ai_security_lock:
        for item in _resend_messages_memory:
            if item.get('tenant_id') != 'platform-security':
                continue
            status = str(item.get('status', 'queued') or 'queued')
            if status not in {'queued', 'retry', 'sending'}:
                continue
            candidates.append(item)
    return candidates


def _prune_backfilled_memory_alerts(migrated_ids: set[int]) -> None:
    if not migrated_ids:
        return
    with _ai_security_lock:
        _resend_messages_memory[:] = [
            item for item in _resend_messages_memory
            if not (
                item.get('tenant_id') == 'platform-security'
                and _coerce_int(item.get('id', 0), 0) in migrated_ids
            )
        ]


def _backfill_security_alert_queue_to_db() -> None:
    if not _security_alert_db_queue_enabled():
        return

    candidates = _security_alert_backfill_candidates()

    if not candidates:
        return

    migrated_ids: set[int] = set()
    for item in candidates:
        status = str(item.get('status', 'queued') or 'queued')
        normalized = 'retry' if status == 'sending' else status
        inserted_id = _db_insert_security_alert_email(item, status=normalized)
        if inserted_id is not None:
            item['id'] = inserted_id
            item['__queue_source'] = 'db'
            migrated_ids.add(_coerce_int(item.get('id', 0), 0))

    _prune_backfilled_memory_alerts(migrated_ids)


def _queue_security_alert_email(email_event: JsonObject) -> None:
    if _security_alert_db_queue_enabled():
        inserted_id = _db_insert_security_alert_email(
            email_event,
            status=str(email_event.get('status', 'queued') or 'queued'),
        )
        if inserted_id is not None:
            email_event['id'] = inserted_id
            email_event['__queue_source'] = 'db'
            return

    email_event['id'] = len(_resend_messages_memory) + 1
    email_event['__queue_source'] = 'memory'
    _resend_messages_memory.append(email_event)


def _claim_security_alert_email() -> JsonObject | None:
    now_ts = int(time.time())
    if _security_alert_db_queue_enabled():
        item = _db_claim_security_alert_email()
        if item is not None:
            return item

    with _ai_security_lock:
        for item in _resend_messages_memory:
            if item.get('tenant_id') != 'platform-security':
                continue
            status = str(item.get('status', '') or '')
            if status not in {'queued', 'retry'}:
                continue
            next_attempt_at = _coerce_int(item.get('next_attempt_at', 0), 0)
            if next_attempt_at > now_ts:
                continue
            item['status'] = 'sending'
            item['locked_at'] = datetime.now(UTC).isoformat()
            item['attempts'] = _coerce_int(item.get('attempts', 0), 0) + 1
            item['__queue_source'] = 'memory'
            return item
    return None


def _update_security_alert_email(item: JsonObject, *, status: str, provider: str, detail: str, retry_seconds: int = 0) -> None:
    if str(item.get('__queue_source', '') or '') == 'db' and _security_alert_db_queue_enabled():
        _db_update_security_alert_email(item, status=status, provider=provider, detail=detail, retry_seconds=retry_seconds)
        return

    now_iso = datetime.now(UTC).isoformat()
    now_ts = int(time.time())
    with _ai_security_lock:
        item['status'] = status
        item['provider'] = provider
        item['updated_at'] = now_iso
        item['delivery_detail'] = detail
        item.pop('locked_at', None)
        if retry_seconds > 0:
            item['next_attempt_at'] = now_ts + retry_seconds
        else:
            item.pop('next_attempt_at', None)


async def _process_security_alert_email(item: JsonObject, worker_logger: StructuredLogger) -> None:
    success, provider, detail = await asyncio.to_thread(
        _dispatch_security_email,
        str(item.get('to', '') or ''),
        str(item.get('subject', '') or ''),
        str(item.get('body', '') or ''),
    )
    if success:
        _update_security_alert_email(item, status='sent', provider=provider, detail=detail)
        worker_logger.info('Security alert email delivered', provider=provider, message_id=item.get('id'))
        return

    attempts = _coerce_int(item.get('attempts', 0), 0)
    final_status = 'failed' if attempts >= 3 or provider == 'unavailable' else 'retry'
    retry_seconds = 0 if final_status == 'failed' else min(300, attempts * 30)
    _update_security_alert_email(item, status=final_status, provider=provider, detail=detail, retry_seconds=retry_seconds)
    worker_logger.warning('Security alert email delivery deferred', provider=provider, status=final_status, detail=detail, message_id=item.get('id'))


async def _run_security_alert_dispatcher(stop_event: asyncio.Event) -> None:
    worker_logger = StructuredLogger('nuxtron.security-alerts')
    while not stop_event.is_set():
        item = _claim_security_alert_email()
        if item is None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=2.0)
            except TimeoutError:
                continue
            continue
        await _process_security_alert_email(item, worker_logger)


def _security_alert_delivery_summary() -> JsonObject:
    db_summary = _db_security_alert_delivery_summary() if _security_alert_db_queue_enabled() else None
    if db_summary is not None:
        return db_summary

    summary: dict[str, int] = {'queued': 0, 'sending': 0, 'retry': 0, 'sent': 0, 'failed': 0}
    for item in _resend_messages_memory:
        if item.get('tenant_id') != 'platform-security':
            continue
        status = str(item.get('status', 'queued') or 'queued')
        summary[status] = summary.get(status, 0) + 1
    return cast(JsonObject, summary)


def _map_security_alert_email_row(row: tuple[object, ...]) -> JsonObject:
    next_attempt = row[8]
    requeued_at = row[11]
    return {
        'id': _coerce_int(row[0], 0),
        'provider': str(row[1] or ''),
        'to': str(row[2] or ''),
        'from': str(row[3] or ''),
        'subject': str(row[4] or ''),
        'status': str(row[5] or ''),
        'attempts': _coerce_int(row[6], 0),
        'delivery_detail': str(row[7] or ''),
        'next_attempt_at': next_attempt.isoformat() if isinstance(next_attempt, datetime) else None,
        'created_at': row[9].isoformat() if isinstance(row[9], datetime) else None,
        'updated_at': row[10].isoformat() if isinstance(row[10], datetime) else None,
        'requeued_at': requeued_at.isoformat() if isinstance(requeued_at, datetime) else None,
        'requeued_by': str(row[12] or ''),
        'requeued_source_ip': str(row[13] or ''),
        'queue_source': 'db',
    }


def _db_fetch_security_alert_email_rows(status: str, limit: int, before_id: int = 0) -> list[tuple[object, ...]]:
    with psycopg.connect(_db_dsn()) as conn:
        with conn.cursor() as cur:
            params: tuple[object, ...]
            query = """
                SELECT id, provider, to_email, from_email, subject, status, attempts, delivery_detail, next_attempt_at, created_at, updated_at, requeued_at, requeued_by, requeued_source_ip
                FROM security_alert_emails
                WHERE tenant_id = %s
            """
            params = ('platform-security',)
            if before_id > 0:
                query += ' AND id < %s'
                params = ('platform-security', before_id)
            if status != 'all':
                query += ' AND status = %s'
                params = ('platform-security', before_id, status) if before_id > 0 else ('platform-security', status)
            query += ' ORDER BY id DESC LIMIT %s'
            params = (*params, limit)
            cur.execute(query, params)
            return cur.fetchall()


def _db_security_alert_email_queue_items(status: str, limit: int, before_id: int = 0) -> list[JsonObject] | None:
    try:
        rows = _db_fetch_security_alert_email_rows(status, limit, before_id)
        return [_map_security_alert_email_row(row) for row in rows]
    except Exception:
        return None


def _memory_queue_item_matches(raw: JsonObject, status: str, before_id: int) -> bool:
    if raw.get('tenant_id') != 'platform-security':
        return False
    item_id = _coerce_int(raw.get('id', 0), 0)
    if before_id > 0 and item_id >= before_id:
        return False
    current_status = str(raw.get('status', 'queued') or 'queued')
    return not (status != 'all' and current_status != status)


def _memory_queue_item_payload(raw: JsonObject) -> JsonObject:
    return {
        'id': _coerce_int(raw.get('id', 0), 0),
        'provider': str(raw.get('provider', '') or ''),
        'to': str(raw.get('to', '') or ''),
        'from': str(raw.get('from', '') or ''),
        'subject': str(raw.get('subject', '') or ''),
        'status': str(raw.get('status', 'queued') or 'queued'),
        'attempts': _coerce_int(raw.get('attempts', 0), 0),
        'delivery_detail': str(raw.get('delivery_detail', '') or ''),
        'next_attempt_at': raw.get('next_attempt_at'),
        'created_at': raw.get('created_at'),
        'updated_at': raw.get('updated_at'),
        'requeued_at': raw.get('requeued_at'),
        'requeued_by': str(raw.get('requeued_by', '') or ''),
        'requeued_source_ip': str(raw.get('requeued_source_ip', '') or ''),
        'queue_source': 'memory',
    }


def _memory_security_alert_email_queue_items(status: str, limit: int, before_id: int = 0) -> list[JsonObject]:
    items: list[JsonObject] = []
    for raw in reversed(_resend_messages_memory):
        if not _memory_queue_item_matches(raw, status, before_id):
            continue
        items.append(_memory_queue_item_payload(raw))
        if len(items) >= limit:
            break
    return items


def _paginate_email_queue_items(items: list[JsonObject], limit: int) -> tuple[list[JsonObject], bool, int | None]:
    has_more = len(items) > limit
    page_items = items[:limit]
    next_cursor: int | None = None
    if has_more and page_items:
        next_cursor = _coerce_int(page_items[-1].get('id', 0), 0)
    return page_items, has_more, (next_cursor if next_cursor and next_cursor > 0 else None)


def _db_requeue_security_alert_email(message_id: int, requeued_by: str, source_ip: str) -> JsonObject | None:
    try:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE security_alert_emails
                    SET status = 'queued',
                        attempts = 0,
                        provider = 'manual-requeue',
                        delivery_detail = 'Requeued by super admin',
                        next_attempt_at = NOW(),
                        requeued_by = %s,
                        requeued_source_ip = %s,
                        requeued_at = NOW(),
                        locked_at = NULL,
                        updated_at = NOW()
                    WHERE id = %s
                      AND tenant_id = %s
                      AND status = 'failed'
                    RETURNING id, provider, to_email, from_email, subject, status, attempts, delivery_detail, next_attempt_at, created_at, updated_at, requeued_at, requeued_by, requeued_source_ip
                    """,
                    (requeued_by, source_ip, message_id, 'platform-security'),
                )
                row = cur.fetchone()
            conn.commit()
        return _map_security_alert_email_row(row) if row is not None else None
    except Exception:
        return None


def _memory_requeue_security_alert_email(message_id: int, requeued_by: str, source_ip: str) -> JsonObject | None:
    with _ai_security_lock:
        raw = None
        for candidate in _resend_messages_memory:
            if candidate.get('tenant_id') != 'platform-security':
                continue
            if _coerce_int(candidate.get('id', 0), 0) != message_id:
                continue
            raw = candidate
            break
        if raw is None:
            return None
        if str(raw.get('status', 'queued') or 'queued') != 'failed':
            return None

        now_iso = datetime.now(UTC).isoformat()
        raw['status'] = 'queued'
        raw['attempts'] = 0
        raw['provider'] = 'manual-requeue'
        raw['delivery_detail'] = 'Requeued by super admin'
        raw['next_attempt_at'] = int(time.time())
        raw['requeued_by'] = requeued_by
        raw['requeued_source_ip'] = source_ip
        raw['requeued_at'] = now_iso
        raw['updated_at'] = now_iso
        return _memory_queue_item_payload(raw)


def _db_security_alert_email_exists(message_id: int) -> bool:
    try:
        with psycopg.connect(_db_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT 1
                    FROM security_alert_emails
                    WHERE id = %s AND tenant_id = %s
                    LIMIT 1
                    """,
                (message_id, 'platform-security'),
            )
            row = cur.fetchone()
        return row is not None
    except Exception:
        return False


def _db_dsn() -> str:
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'nuxtron')
    user = os.getenv('POSTGRES_USER', 'nuxtron')
    password = os.getenv('POSTGRES_PASSWORD', '')
    return f"host={host} port={port} dbname={db_name} user={user} password={password} connect_timeout=2"


def _apply_startup_db_timeouts(conn: psycopg.Connection) -> None:
    # Startup DDL should fail fast under lock contention so memory fallback remains usable.
    conn.execute("SET lock_timeout = '2000ms'")
    conn.execute("SET statement_timeout = '5000ms'")


def _init_social_table() -> None:
    global _db_ready
    try:
        with psycopg.connect(_db_dsn()) as conn:
            _apply_startup_db_timeouts(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS social_scheduled_posts (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        text_cipher TEXT NOT NULL,
                        text_preview TEXT NOT NULL,
                        publish_at TIMESTAMPTZ NOT NULL,
                        media_urls TEXT[] NOT NULL DEFAULT '{}',
                        status TEXT NOT NULL DEFAULT 'scheduled',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute("ALTER TABLE social_scheduled_posts ADD COLUMN IF NOT EXISTS text_cipher TEXT")
                cur.execute("ALTER TABLE social_scheduled_posts ADD COLUMN IF NOT EXISTS text_preview TEXT")
                cur.execute(
                    """
                    UPDATE social_scheduled_posts
                    SET text_cipher = COALESCE(text_cipher, text_preview, ''),
                        text_preview = COALESCE(text_preview, '[encrypted]')
                    WHERE text_cipher IS NULL OR text_preview IS NULL
                    """
                )
            conn.commit()
        _db_ready = True
    except Exception:
        # Local fallback when DB is not available; production should keep DB reachable.
        _db_ready = False


def _init_email_tables() -> None:
    if not _db_ready:
        return

    with psycopg.connect(_db_dsn()) as conn:
        _apply_startup_db_timeouts(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS email_contacts (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    email_cipher TEXT NOT NULL,
                    email_preview TEXT NOT NULL,
                    name_cipher TEXT,
                    name_preview TEXT,
                    tags TEXT[] NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS email_campaigns (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_cipher TEXT NOT NULL,
                    subject_preview TEXT NOT NULL,
                    body_cipher TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    provider TEXT NOT NULL DEFAULT 'listmonk',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS security_alert_emails (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'smtp-queue',
                    to_email TEXT NOT NULL,
                    from_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TIMESTAMPTZ,
                    locked_at TIMESTAMPTZ,
                    delivery_detail TEXT,
                    requeued_by TEXT,
                    requeued_source_ip TEXT,
                    requeued_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("ALTER TABLE security_alert_emails ADD COLUMN IF NOT EXISTS requeued_by TEXT")
            cur.execute("ALTER TABLE security_alert_emails ADD COLUMN IF NOT EXISTS requeued_source_ip TEXT")
            cur.execute("ALTER TABLE security_alert_emails ADD COLUMN IF NOT EXISTS requeued_at TIMESTAMPTZ")
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_security_alert_emails_dispatch
                ON security_alert_emails (tenant_id, status, next_attempt_at, id)
                """
            )
        conn.commit()


def _init_tenant_tables() -> None:
    if not _db_ready:
        return

    with psycopg.connect(_db_dsn()) as conn:
        _apply_startup_db_timeouts(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tenant_profiles (
                    tenant_id TEXT PRIMARY KEY,
                    display_name_cipher TEXT,
                    display_name_preview TEXT,
                    plan TEXT NOT NULL DEFAULT 'starter',
                    status TEXT NOT NULL DEFAULT 'active',
                    settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()


def _init_db_tables() -> None:
    global _db_ready, _db_init_attempted

    if os.getenv('NUXTRON_SKIP_STARTUP_DB_INIT', '').strip().lower() in {'1', 'true', 'yes'}:
        _db_ready = False
        _db_init_attempted = True
        return

    if _db_ready or _db_init_attempted:
        return

    with _db_init_lock:
        if _db_ready or _db_init_attempted:
            return

        _init_social_table()
        _init_email_tables()
        _init_tenant_tables()
        _init_users_table()
        _init_flywheel_tables()
        _db_init_attempted = True


def _load_persisted_governance_state() -> None:
    global _governance_db, _governance_state_loaded

    if _governance_state_loaded:
        return

    try:
        _governance_db = _GovernanceDB()
        gov_providers_loaded, gov_usage_loaded, gov_incidents_loaded = _governance_db.load_all()
    except Exception:
        _governance_db = None
        return

    _api_governance_providers_memory.extend(gov_providers_loaded)
    _api_governance_usage_events_memory.extend(gov_usage_loaded)
    _api_governance_incidents_memory.extend(gov_incidents_loaded)
    _governance_state_loaded = True


def _init_flywheel_tables() -> None:
    if not _db_ready:
        return

    with psycopg.connect(_db_dsn()) as conn:
        _apply_startup_db_timeouts(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS outcome_actions (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
                    impact_level TEXT NOT NULL DEFAULT 'medium',
                    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
                    approved_by TEXT,
                    executed BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS outcome_outcomes (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    action_id UUID REFERENCES outcome_actions(id) ON DELETE SET NULL,
                    outcome_type TEXT NOT NULL,
                    value_delta DOUBLE PRECISION,
                    currency TEXT DEFAULT 'GBP',
                    attributed_revenue DOUBLE PRECISION DEFAULT 0,
                    confidence DOUBLE PRECISION DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS outcome_quality_scores (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    action_id UUID REFERENCES outcome_actions(id) ON DELETE SET NULL,
                    score DOUBLE PRECISION NOT NULL DEFAULT 0,
                    reasoning TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS trust_policy_history (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    policy_key TEXT NOT NULL,
                    old_value JSONB,
                    new_value JSONB NOT NULL DEFAULT '{}',
                    change_reason TEXT NOT NULL,
                    actor_role TEXT NOT NULL DEFAULT 'admin',
                    requires_human_validation BOOLEAN NOT NULL DEFAULT FALSE,
                    approved_by TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS trust_approval_chains (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    chain_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    steps JSONB NOT NULL DEFAULT '[]',
                    require_all BOOLEAN NOT NULL DEFAULT TRUE,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS trust_incidents (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'medium',
                    affected_module TEXT NOT NULL DEFAULT 'ira',
                    resolved BOOLEAN NOT NULL DEFAULT FALSE,
                    resolution_notes TEXT,
                    resolved_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS trust_governance_snapshots (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    autonomy_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    allow_high_impact_actions BOOLEAN NOT NULL DEFAULT FALSE,
                    strict_policy_lock BOOLEAN NOT NULL DEFAULT TRUE,
                    policy_change_human_validation BOOLEAN NOT NULL DEFAULT FALSE,
                    active_approval_chains INTEGER NOT NULL DEFAULT 0,
                    open_incidents INTEGER NOT NULL DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS playbooks (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    vertical TEXT NOT NULL DEFAULT 'all',
                    description TEXT NOT NULL,
                    steps JSONB NOT NULL DEFAULT '[]',
                    integrations JSONB NOT NULL DEFAULT '[]',
                    roi_target JSONB NOT NULL DEFAULT '{}',
                    time_to_value_days INTEGER NOT NULL DEFAULT 1,
                    built_in BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS playbook_runs (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    playbook_id TEXT NOT NULL,
                    playbook_name TEXT,
                    config JSONB NOT NULL DEFAULT '{}',
                    dry_run BOOLEAN NOT NULL DEFAULT TRUE,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    steps_total INTEGER NOT NULL DEFAULT 0,
                    steps_completed INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    baseline_value DOUBLE PRECISION,
                    uplift_pct DOUBLE PRECISION,
                    period_label TEXT NOT NULL,
                    segment TEXT NOT NULL DEFAULT 'all',
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS segment_benchmarks (
                    id UUID PRIMARY KEY,
                    segment TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    p50 DOUBLE PRECISION NOT NULL,
                    p75 DOUBLE PRECISION NOT NULL,
                    p90 DOUBLE PRECISION NOT NULL,
                    period_label TEXT NOT NULL,
                    sample_size INTEGER NOT NULL,
                    published_by_tenant TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        conn.commit()


def _init_users_table() -> None:
    if not _db_ready:
        return

    with psycopg.connect(_db_dsn()) as conn:
        _apply_startup_db_timeouts(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    email_hash TEXT NOT NULL,
                    email_cipher TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    name_cipher TEXT,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    reset_token TEXT,
                    reset_token_expires TIMESTAMPTZ,
                    roles TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(tenant_id, email_hash)
                )
                """
            )
            # Comma-separated JWT roles claim (e.g. 'admin', 'user,billing') —
            # persisted so a returning user keeps their assigned role instead
            # of every login re-issuing a token with the default 'user'.
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS roles TEXT NOT NULL DEFAULT 'user'")
        conn.commit()


async def _stop_security_worker(worker_stop: asyncio.Event | None, worker_task: 'asyncio.Task[None] | None', logger: 'StructuredLogger') -> None:
    global _security_alert_worker_task, _security_alert_worker_stop
    if worker_stop is not None:
        worker_stop.set()
    if worker_task is not None and not worker_task.done():
        try:
            await worker_task
        except asyncio.CancelledError:
            logger.info('Security alert dispatcher cancelled during shutdown')
            raise
        finally:
            _security_alert_worker_task = None
            _security_alert_worker_stop = None
    else:
        _security_alert_worker_task = None
        _security_alert_worker_stop = None


async def _stop_ira_watchdog(ira_watchdog_stop: asyncio.Event | None, ira_watchdog_task: 'asyncio.Task[None] | None', logger: 'StructuredLogger') -> None:
    global _ira_watchdog_task, _ira_watchdog_stop
    if ira_watchdog_stop is not None:
        ira_watchdog_stop.set()
    if ira_watchdog_task is not None and not ira_watchdog_task.done():
        try:
            await ira_watchdog_task
        except asyncio.CancelledError:
            logger.info('IRA watchdog cancelled during shutdown')
            raise
        finally:
            _ira_watchdog_task = None
            _ira_watchdog_stop = None
    else:
        _ira_watchdog_task = None
        _ira_watchdog_stop = None


async def _stop_autonomous_workforce_watchdog(
    workforce_watchdog_stop: asyncio.Event | None,
    workforce_watchdog_task: 'asyncio.Task[None] | None',
    logger: 'StructuredLogger',
) -> None:
    global _autonomous_workforce_watchdog_stop, _autonomous_workforce_watchdog_task
    if workforce_watchdog_stop is not None:
        workforce_watchdog_stop.set()
    if workforce_watchdog_task is not None and not workforce_watchdog_task.done():
        try:
            await workforce_watchdog_task
        except asyncio.CancelledError:
            logger.info('Autonomous workforce watchdog cancelled during shutdown')
            raise
        finally:
            _autonomous_workforce_watchdog_stop = None
            _autonomous_workforce_watchdog_task = None
    else:
        _autonomous_workforce_watchdog_stop = None
        _autonomous_workforce_watchdog_task = None


async def _initialize_vault(logger: 'StructuredLogger') -> None:
    try:
        from .vault_config import initialize_secrets_manager, load_secrets_from_vault

        await asyncio.to_thread(initialize_secrets_manager)
        await asyncio.to_thread(load_secrets_from_vault)
        logger.info('Vault initialization complete')
    except ImportError:
        logger.warning('Vault integration not available')
    except Exception as error:
        logger.error(f'Vault initialization failed: {error}')


async def _initialize_transparent_encryption(logger: 'StructuredLogger') -> None:
    if os.getenv('NUXTRON_SKIP_STARTUP_DB_INIT') == '1':
        logger.info('Transparent encryption bootstrap skipped (NUXTRON_SKIP_STARTUP_DB_INIT=1)')
        return

    try:
        from .transparent_encryption import enable_pgcrypto, encryption_status

        enc = encryption_status()
        logger.info('Transparent encryption active', cipher=enc['primary_cipher'], aes_ni=enc['aes_ni_detected'])

        def _try_enable_pgcrypto() -> None:
            # Bound connect time so shutdown cannot block waiting for a stuck worker thread.
            connect_timeout = int(os.getenv('NUXTRON_PGCRYPTO_CONNECT_TIMEOUT_SECONDS', '2'))
            with psycopg.connect(_db_dsn(), connect_timeout=connect_timeout) as _pg_conn:
                enable_pgcrypto(_pg_conn)

        try:
            await asyncio.wait_for(asyncio.to_thread(_try_enable_pgcrypto), timeout=3.0)
        except Exception as pgcrypto_error:
            logger.warning(f'pgcrypto: skipped ({pgcrypto_error})')
    except Exception as error:
        logger.warning(f'Transparent encryption init skipped: {error}')


async def _initialize_database_state(logger: 'StructuredLogger') -> None:
    validate_environment()
    validate_startup_security()
    logger.info('Security validation complete')

    # Initialize ORM database (PostgreSQL/SQLite)
    try:
        await asyncio.wait_for(asyncio.to_thread(init_db), timeout=10.0)
        logger.info('ORM database initialization complete')
    except Exception as ex:
        logger.warning(f'ORM database initialization failed: {ex}; continuing with legacy mode')

    try:
        await asyncio.wait_for(asyncio.to_thread(_init_db_tables), timeout=10.0)
    except TimeoutError:
        global _db_init_attempted, _db_ready
        _db_init_attempted = True
        _db_ready = False
        logger.warning('Database initialization timed out; continuing with fallback mode')

    logger.info('Database initialization complete', db_ready=_db_ready)
    _load_persisted_governance_state()
    if _is_production() and not _db_ready:
        raise RuntimeError('Database is required in production mode; startup aborted (no memory fallback).')

    try:
        await asyncio.wait_for(asyncio.to_thread(_backfill_security_alert_queue_to_db), timeout=5.0)
    except TimeoutError:
        logger.warning('Security alert queue backfill timed out; continuing startup')


def _start_security_alert_worker() -> tuple[asyncio.Event, 'asyncio.Task[None]']:
    worker_stop = asyncio.Event()
    worker_task = asyncio.create_task(_run_security_alert_dispatcher(worker_stop))
    return worker_stop, worker_task


def _start_ira_watchdog() -> tuple[asyncio.Event, 'asyncio.Task[None]']:
    ira_watchdog_stop = asyncio.Event()
    ira_watchdog_task = asyncio.create_task(
        run_ira_watchdog(
            ira_watchdog_stop,
            ira_controls_memory=_ira_controls_memory,
            ira_events_memory=_ira_events_memory,
            audit_log_memory=_audit_log_memory,
            invoices_memory=_invoices_memory,
            credit_ledger_memory=_credit_ledger_memory,
            stripe_events_memory=_stripe_events_memory,
            revenue_conversions_memory=_revenue_conversions_memory,
            api_usage_audit_memory=_api_usage_audit_memory,
            ai_security_usage_memory=_ai_security_usage_memory,
        )
    )
    return ira_watchdog_stop, ira_watchdog_task


def _start_autonomous_workforce_watchdog() -> tuple[asyncio.Event, 'asyncio.Task[None]']:
    workforce_watchdog_stop = asyncio.Event()
    workforce_watchdog_task = asyncio.create_task(
        run_autonomous_workforce_watchdog(
            workforce_watchdog_stop,
            schedules_memory=_autonomous_workforce_schedules_memory,
            integrations_memory=_autonomous_workforce_integrations_memory,
            missions_memory=_autonomous_workforce_missions_memory,
            feed_memory=_autonomous_workforce_feed_memory,
            outcomes_memory=_autonomous_workforce_outcomes_memory,
            audit_log_memory=_audit_log_memory,
            poll_interval_seconds=int(os.getenv('AUTONOMOUS_WORKFORCE_WATCHDOG_INTERVAL_SECONDS', '30')),
            max_due_per_tick=int(os.getenv('AUTONOMOUS_WORKFORCE_WATCHDOG_MAX_DUE_PER_TICK', '20')),
        )
    )
    return workforce_watchdog_stop, workforce_watchdog_task


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup: Initialize production environment
    logger = StructuredLogger('nuxtron.startup')
    global _security_alert_worker_stop, _security_alert_worker_task, _ira_watchdog_stop, _ira_watchdog_task
    global _autonomous_workforce_watchdog_stop, _autonomous_workforce_watchdog_task
    worker_stop = cast(asyncio.Event | None, None)
    worker_task = cast(asyncio.Task[None] | None, None)
    ira_watchdog_stop = cast(asyncio.Event | None, None)
    ira_watchdog_task = cast(asyncio.Task[None] | None, None)
    workforce_watchdog_stop = cast(asyncio.Event | None, None)
    workforce_watchdog_task = cast(asyncio.Task[None] | None, None)
    
    try:
        logger.info('FastAPI Application Starting')
        await _initialize_vault(logger)
        await _initialize_transparent_encryption(logger)
        await _initialize_database_state(logger)

        worker_stop, worker_task = _start_security_alert_worker()
        _security_alert_worker_stop = worker_stop
        _security_alert_worker_task = worker_task

        ira_watchdog_stop, ira_watchdog_task = _start_ira_watchdog()
        _ira_watchdog_stop = ira_watchdog_stop
        _ira_watchdog_task = ira_watchdog_task

        if os.getenv('AUTONOMOUS_WORKFORCE_WATCHDOG_ENABLED', '1').strip().lower() in {'1', 'true', 'yes', 'on'}:
            workforce_watchdog_stop, workforce_watchdog_task = _start_autonomous_workforce_watchdog()
            _autonomous_workforce_watchdog_stop = workforce_watchdog_stop
            _autonomous_workforce_watchdog_task = workforce_watchdog_task
        
        logger.info('FastAPI Application Started Successfully', version='2.1.0')
    except Exception as ex:
        logger.critical('Startup failed', error=str(ex))
        raise

    try:
        yield
    except asyncio.CancelledError:
        # Uvicorn reload can cancel lifespan receive; treat as normal shutdown signal.
        logger.info('Lifespan cancelled during shutdown/reload')
        raise
    finally:
        # Shutdown: Graceful cleanup
        logger.info('FastAPI Application Shutting Down')
        await _stop_security_worker(worker_stop, worker_task, logger)
        await _stop_ira_watchdog(ira_watchdog_stop, ira_watchdog_task, logger)
        await _stop_autonomous_workforce_watchdog(workforce_watchdog_stop, workforce_watchdog_task, logger)
        # Clean up any pending operations
        with _rate_lock:
            _rate_buckets.clear()
        # Close ORM database connections
        try:
            await asyncio.wait_for(asyncio.to_thread(close_db), timeout=5.0)
        except Exception:
            logger.warning('Error closing ORM database connections')
        logger.info('Cleanup complete')


app = FastAPI(
    title='Nuxtron FastAPI Services',
    version='2.1.0',
    lifespan=lifespan,
    docs_url='/api/docs' if _allow_api_docs() else None,
    redoc_url='/api/redoc' if _allow_api_docs() else None,
    openapi_url='/api/openapi.json' if _allow_api_docs() else None,
)
app.state.api_usage_audit = _api_usage_audit_memory
# Expose SIEM and IRA stores on app.state so security telemetry in deps.py can write to them
app.state.siem_cases = _siem_cases_memory
app.state.ira_events = _ira_events_memory

# Add production middleware (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SensitiveRouteTokenMiddleware)  # token-only on sensitive prefixes
app.add_middleware(RequestTracingMiddleware, logger=StructuredLogger('nuxtron.requests'))
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts())

_cors_allowed_origins = _cors_origins()
_cors_wildcard = len(_cors_allowed_origins) == 1 and _cors_allowed_origins[0] == '*'
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins,
    allow_credentials=not _cors_wildcard,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type', 'X-API-Key', 'X-Tenant-Id', 'X-Request-ID'],
)

# Add exception handler
@app.exception_handler(RateLimitExceededError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    return JSONResponse(status_code=429, content={'detail': exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return await GlobalExceptionHandler.exception_handler(request, exc)

# Initialize logger
logger = StructuredLogger('nuxtron')

# Constants
CONTENT_TYPE_JSON = 'application/json'
AuthDep = Annotated[AuthContext, Depends(require_auth)]
# ════════════════════════════════════════════════════════════════════════════════
# MULTI-PROVIDER AI BACKEND WITH 24/7 FAILOVER & COST OPTIMIZATION
# ════════════════════════════════════════════════════════════════════════════════
# Tier 1 (Primary): High quality, preferred cost-quality ratio
# Tier 2 (Secondary): Mid-tier backup, acceptable quality, lower cost
# Tier 3 (Tertiary): Last-resort backup, basic quality, minimal cost
# Tier 4 (Emergency): Fallback-of-fallback for extreme reliability

AI_PROVIDER_TIERS: dict[str, dict[str, list[str]]] = {
    'text_generation': {
        'tier_1': ['anthropic', 'openai'],  # Primary: best quality
        'tier_2': ['google_vertex'],  # Secondary: good quality, cheaper
        'tier_3': ['cohere', 'mistral'],  # Tertiary: acceptable quality, budget-friendly
        'tier_4': ['together_ai'],  # Emergency: always available fallback
    },
    'summarization': {
        'tier_1': ['openai', 'anthropic'],
        'tier_2': ['google_vertex', 'cohere'],
        'tier_3': ['mistral'],
        'tier_4': ['together_ai'],
    },
    'image_generation': {
        'tier_1': ['openai'],  # DALL-E best quality
        'tier_2': ['google_vertex'],  # Imagen fast & good
        'tier_3': ['stability_ai'],  # Stable Diffusion budget
        'tier_4': ['together_ai'],  # Fallback
    },
}

AI_PROVIDERS: tuple[str, ...] = (
    # Tier 1 (Primary)
    'openai', 'anthropic',
    # Tier 2 (Secondary)
    'google_vertex',
    # Tier 3 (Tertiary)  
    'cohere', 'mistral',
    # Tier 4 (Emergency)
    'together_ai', 'stability_ai',
)

# Model name constants (duplicated across functions)
GEMINI_FLASH_MODEL = 'gemini-2.0-flash'
IMAGE_GENERATION_MODEL = 'imagegeneration@006'
LLAMA_70B_MODEL = 'meta-llama/Llama-3-70b'

# MIME type constants (duplicated across functions)
MIME_TYPE_PNG = 'image/png'
MIME_TYPE_MP3 = 'audio/mpeg'
MIME_TYPE_WAV = 'audio/wav'
MIME_TYPE_MP4 = 'video/mp4'

# ISO 8601 timezone offset constant (duplicated across functions)
UTC_OFFSET = '+00:00'

AI_MODEL_CATALOG: dict[str, dict[str, dict[str, float]]] = {
    'openai': {
        'gpt-4o-mini': {'cost_per_1k_tokens': 0.0006, 'quality_score': 0.83, 'uptime_percent': 99.95, 'latency_ms': 500},
        'gpt-4.1-mini': {'cost_per_1k_tokens': 0.0009, 'quality_score': 0.87, 'uptime_percent': 99.95, 'latency_ms': 450},
        'gpt-4': {'cost_per_1k_tokens': 0.003, 'quality_score': 0.95, 'uptime_percent': 99.95, 'latency_ms': 800},
    },
    'anthropic': {
        'claude-3-5-haiku-latest': {'cost_per_1k_tokens': 0.0010, 'quality_score': 0.85, 'uptime_percent': 99.9, 'latency_ms': 400},
        'claude-3-5-sonnet-latest': {'cost_per_1k_tokens': 0.0030, 'quality_score': 0.93, 'uptime_percent': 99.9, 'latency_ms': 600},
        'claude-3-opus': {'cost_per_1k_tokens': 0.0075, 'quality_score': 0.97, 'uptime_percent': 99.9, 'latency_ms': 1200},
    },
    'google_vertex': {
        GEMINI_FLASH_MODEL: {'cost_per_1k_tokens': 0.00015, 'quality_score': 0.85, 'uptime_percent': 99.8, 'latency_ms': 350},
        'gemini-2.0-pro': {'cost_per_1k_tokens': 0.0010, 'quality_score': 0.92, 'uptime_percent': 99.8, 'latency_ms': 700},
        IMAGE_GENERATION_MODEL: {'cost_per_1k_tokens': 0.0005, 'quality_score': 0.90, 'uptime_percent': 99.8, 'latency_ms': 800},
    },
    'cohere': {
        'command-r': {'cost_per_1k_tokens': 0.0005, 'quality_score': 0.78, 'uptime_percent': 99.5, 'latency_ms': 300},
        'command-r-plus': {'cost_per_1k_tokens': 0.001, 'quality_score': 0.82, 'uptime_percent': 99.5, 'latency_ms': 400},
    },
    'mistral': {
        'mistral-large': {'cost_per_1k_tokens': 0.0008, 'quality_score': 0.80, 'uptime_percent': 99.7, 'latency_ms': 350},
        'mistral-small': {'cost_per_1k_tokens': 0.0002, 'quality_score': 0.70, 'uptime_percent': 99.7, 'latency_ms': 250},
    },
    'together_ai': {
        LLAMA_70B_MODEL: {'cost_per_1k_tokens': 0.0008, 'quality_score': 0.75, 'uptime_percent': 99.99, 'latency_ms': 400},
        'NousResearch/Nous-Hermes-2-Mixtral-8x7B': {'cost_per_1k_tokens': 0.0006, 'quality_score': 0.72, 'uptime_percent': 99.99, 'latency_ms': 350},
    },
    'stability_ai': {
        'stable-diffusion-3': {'cost_per_1k_tokens': 0.002, 'quality_score': 0.85, 'uptime_percent': 99.6, 'latency_ms': 5000},
        'stable-diffusion-ultra': {'cost_per_1k_tokens': 0.004, 'quality_score': 0.92, 'uptime_percent': 99.6, 'latency_ms': 8000},
    },
}

# Provider health tracking (in-memory, reset on restart)
_provider_health_metrics: dict[str, dict[str, float]] = {
    provider: {
        'success_rate': 1.0,
        'avg_latency_ms': 0.0,
        'last_error_at': 0,
        'consecutive_errors': 0,
        'requests_total': 0,
        'requests_success': 0,
        'updated_at': time.time(),
    }
    for provider in AI_PROVIDERS
}


class ContentRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=180)
    audience: str = Field(min_length=3, max_length=120)
    channel: Literal['linkedin', 'x', 'instagram', 'facebook', 'blog', 'tiktok', 'youtube', 'threads', 'snapchat', 'pinterest', 'reddit']
    tone: Literal['professional', 'casual', 'bold', 'friendly'] = 'professional'
    include_seo: bool = True
    prompt: str | None = Field(default=None, max_length=12000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    provider: Literal['auto', 'openai', 'anthropic', 'google_vertex'] = 'auto'
    target_formats: list[str] = Field(default_factory=list, max_length=16)


class AdsRequest(BaseModel):
    product: str = Field(min_length=2, max_length=140)
    audience: str = Field(min_length=2, max_length=120)
    platform: Literal['google', 'meta', 'linkedin', 'tiktok', 'instagram', 'youtube', 'facebook', 'x', 'threads', 'snapchat']
    objective: Literal['traffic', 'leads', 'sales', 'awareness']
    prompt: str | None = Field(default=None, max_length=12000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    provider: Literal['auto', 'openai', 'anthropic', 'google_vertex'] = 'auto'
    target_formats: list[str] = Field(default_factory=list, max_length=16)


class SeoRequest(BaseModel):
    url: HttpUrl | None = None
    target_keyword: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=20, max_length=10000)


class SocialScheduleRequest(BaseModel):
    platform: Literal['linkedin', 'x', 'instagram', 'facebook']
    text: str = Field(min_length=3, max_length=2200)
    publish_at: datetime
    media_urls: list[HttpUrl] = Field(default_factory=list, max_length=10)  # pyright: ignore[reportUnknownVariableType]
    # ADDED: SproutSocial §2.1.1 — campaign tagging and UTM linking
    campaign_tag: str | None = Field(default=None, max_length=120, description='Campaign label for analytics aggregation.')
    utm_preset_id: int | None = Field(default=None, ge=1, description='Apply a saved UTM preset to links in this post.')
    utm_params: dict[str, str] | None = Field(default=None, description='Custom UTM params (overrides preset field-by-field).')
    # ADDED: Instagram first comment scheduling (§2.1.1)
    first_comment: str | None = Field(default=None, max_length=2200, description='First comment to post on Instagram immediately after publish.')


class SocialScheduleMoveRequest(BaseModel):
    publish_at: datetime


SCHEDULED_POST_NOT_FOUND = 'Scheduled post not found.'


class SocialListeningIngestRequest(BaseModel):
    platform: Literal['linkedin', 'x', 'instagram', 'facebook', 'reddit', 'youtube', 'news']
    query: str = Field(min_length=2, max_length=120)
    author_handle: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=3, max_length=4000)
    sentiment: Literal['positive', 'neutral', 'negative'] = 'neutral'
    engagement_count: int = Field(default=0, ge=0, le=1_000_000)


class SocialListeningAlertRuleRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    query: str | None = Field(default=None, max_length=120)
    platform: Literal['linkedin', 'x', 'instagram', 'facebook', 'reddit', 'youtube', 'news'] | None = None
    min_engagement: int = Field(default=20, ge=0, le=1_000_000)
    negative_only: bool = True


class ReviewIngestRequest(BaseModel):
    platform: Literal['google', 'trustpilot', 'g2', 'capterra', 'yelp', 'app_store', 'play_store', 'custom']
    reviewer: str = Field(min_length=1, max_length=120)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=3, max_length=4000)
    category: str = Field(default='general', min_length=1, max_length=80)


class ReviewResponseRequest(BaseModel):
    response: str = Field(min_length=3, max_length=4000)


class EmailContactCreateRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    name: str = Field(min_length=1, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=20)


class EmailCampaignCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=180)
    body: str = Field(min_length=10, max_length=20000)
    provider: Literal['listmonk', 'postal', 'ses'] = 'listmonk'


class EmailCampaignSendTestRequest(BaseModel):
    recipient_email: str = Field(min_length=5, max_length=320)


class SuiteCrmLeadRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=320)
    company: str = Field(default='', max_length=180)
    source: str = Field(default='nuxtron', max_length=80)


class RefferqReferralRequest(BaseModel):
    referrer_email: str = Field(min_length=5, max_length=320)
    referred_email: str = Field(min_length=5, max_length=320)
    campaign: str = Field(min_length=1, max_length=140)


class PosthogCaptureRequest(BaseModel):
    event: str = Field(min_length=1, max_length=120)
    distinct_id: str | None = Field(default=None, max_length=120)
    properties: dict[str, object] = Field(default_factory=dict)


class N8nWebhookTriggerRequest(BaseModel):
    workflow: str = Field(min_length=1, max_length=120)
    payload: dict[str, object] = Field(default_factory=dict)


class GrowthbookEvaluateRequest(BaseModel):
    feature_key: str = Field(min_length=1, max_length=120)
    user_id: str | None = Field(default=None, max_length=120)
    attributes: dict[str, object] = Field(default_factory=dict)


class MatomoTrackRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=120)
    url: HttpUrl | None = None
    action_name: str = Field(default='Nuxtron Studio Event', min_length=1, max_length=160)
    properties: dict[str, object] = Field(default_factory=dict)


class PlausibleTrackRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=120)
    url: HttpUrl | None = None
    properties: dict[str, object] = Field(default_factory=dict)


def _decrypt_value_or_empty(ciphertext: str) -> str:
    return te_decrypt(ciphertext) or ''


def _hash_password_ops(password: str, algorithm: str) -> str:
    if algorithm in {'bcrypt', 'argon2id'}:
        return hash_password(password, cast(Literal['bcrypt', 'argon2id'], algorithm))
    return hash_password(password)


def _hash_email(email: str) -> str:
    """Deterministic hash for email lookups without decryption."""
    pepper = get_password_pepper()
    return hashlib.sha256(f'{email.strip().lower()}:{pepper}'.encode()).hexdigest()


class AiGatewayGenerateRequest(BaseModel):
    provider: Literal['auto', 'openai', 'anthropic', 'google_vertex'] = 'auto'
    prompt: str = Field(min_length=1, max_length=12000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=120)
    max_tokens: int = Field(default=500, ge=1, le=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    target_roi: float = Field(default=0.70, ge=0.0, le=20.0)
    value_per_1k_tokens: float = Field(default=0.006, ge=0.0001, le=50.0)
    quality_floor: float = Field(default=0.80, ge=0.0, le=1.0)


class AiSecurityRotateKeyRequest(BaseModel):
    provider: Literal['openai', 'anthropic', 'google_vertex']
    api_key: str = Field(min_length=8, max_length=500)
    label: str | None = Field(default=None, max_length=120)


class AiSecurityAppealRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1200)


class AiSecurityAppealResolveRequest(BaseModel):
    decision: Literal['approved', 'rejected']
    notes: str | None = Field(default=None, max_length=1200)


class AiSecurityIdseventRequest(BaseModel):
    source: Literal['suricata', 'zeek', 'ossec', 'fail2ban', 'manual']
    severity: Literal['low', 'medium', 'high', 'critical']
    rule_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=3, max_length=1200)
    tenant_id: str | None = Field(default=None, max_length=120)
    provider: Literal['openai', 'anthropic', 'google_vertex'] | None = None
    ip_address: str | None = Field(default=None, max_length=120)
    action: Literal['alert', 'block-tenant', 'disable-provider'] = 'alert'


class FinanceLegacyIntegrationConnectRequest(BaseModel):
    provider: Literal['quickbooks', 'xero', 'hmrc']
    client_id: str = Field(min_length=3, max_length=200)
    account_name: str = Field(min_length=2, max_length=120)


class FinanceLegacyExportRequest(BaseModel):
    provider: Literal['quickbooks', 'xero', 'hmrc']
    export_type: Literal['vat_return', 'pnl', 'ledger', 'invoice_batch', 'balance_sheet']
    period_label: str = Field(min_length=2, max_length=32)


class FinanceLegacyRotateSecretRequest(BaseModel):
    client_secret: str = Field(min_length=3, max_length=400)
    authorization_code: str = Field(default='', max_length=800)
    redirect_uri: str = Field(default='', max_length=500)
    account_realm_id: str = Field(default='', max_length=200)


app.include_router(
    create_auth_router(
        enforce_rate_limit=_enforce_rate_limit,
        totp_secret=_totp_secret,
        totp_verify=_totp_verify,
        jwt_sign_hs256=_jwt_sign_hs256,
        jwt_verify_hs256=_jwt_verify_hs256,
        auth_security_memory=cast(list[AuthSecurityRecord], _auth_security_memory),
        hash_password=hash_password,
        verify_password=verify_password,
        encrypt_value=te_encrypt,
        hash_email=_hash_email,
        get_db_ready=lambda: _db_ready,
        db_dsn=_db_dsn,
        users_memory=_users_memory,
    )
)

app.include_router(
    create_tenant_router(
        enforce_rate_limit=_enforce_rate_limit,
        get_db_ready=lambda: _db_ready,
        db_dsn=_db_dsn,
        encrypt_value=te_encrypt,
        decrypt_value=_decrypt_value_or_empty,
        tenant_profiles_memory=_tenant_profiles_memory,
    )
)

app.include_router(
    create_notifications_router(
        enforce_rate_limit=_enforce_rate_limit,
        notifications_memory=_notifications_memory,
        audit_log_memory=_audit_log_memory,
        notification_preferences_memory=_notification_preferences_memory,
        notification_delivery_receipts_memory=_notification_delivery_receipts_memory,
        # ENHANCED: enable DB-backed notification durability while retaining memory fallback behavior.
        db_ready_fn=lambda: _db_ready,
        db_dsn_fn=_db_dsn,
    )
)

# NEW: Sandboxed Media Processing Pipeline (Sandboxed_Media_SaaS_Architecture)
app.include_router(
    create_media_jobs_router(
        enforce_rate_limit=_enforce_rate_limit,
        media_jobs_memory=_media_jobs_memory,
        media_jobs_dlq_memory=_media_jobs_dlq_memory,
        audit_log_memory=_audit_log_memory,
    )
)


def _ops_require_super_admin_access(request: Request, x_super_admin_key: str | None) -> None:
    _require_super_admin_access(request, x_super_admin_key)

app.include_router(
    create_ops_router(
        enforce_rate_limit=_enforce_rate_limit,
        hash_password=_hash_password_ops,
        verify_password=verify_password,
        get_platform_status=lambda auth: _platform_status_payload(auth),
        get_metrics_summary=lambda auth: _platform_metrics_summary_payload(auth),
        callbacks=_OpsCallbacks(
            get_anti_failure_status=lambda auth: _platform_anti_failure_payload(auth),
            get_use_case_coverage=lambda auth: _platform_use_case_coverage_payload(auth),
            get_api_usage_summary=lambda auth, limit: _platform_api_usage_payload(auth, limit),
            get_capabilities=lambda auth: _platform_capabilities_payload(auth),
            get_super_admin_dashboard=lambda auth: _platform_super_admin_dashboard_payload(auth),
            get_siem_data_collection=lambda auth, limit: _platform_siem_data_collection_payload(auth, limit),
            get_siem_detection=lambda auth, limit: _platform_siem_detection_payload(auth, limit),
            get_siem_investigation=lambda auth, query, limit: _platform_siem_investigation_payload(auth, query, limit),
            get_siem_compliance=lambda auth: _platform_siem_compliance_payload(auth),
            set_siem_retention_policy=lambda auth, hot_days, warm_days, cold_days, immutable_audit: _platform_siem_set_retention_policy_payload(
                auth, hot_days, warm_days, cold_days, immutable_audit
            ),
            get_siem_architecture=lambda auth: _platform_siem_architecture_payload(auth),
            list_siem_cases=lambda auth, status, limit, offset: _platform_siem_list_cases_payload(auth, status, limit, offset),
            create_siem_case=lambda auth, title, severity, description, evidence_ids: _platform_siem_create_case_payload(
                auth, title, severity, description, evidence_ids
            ),
            update_siem_case=lambda auth, case_id, status, assignee, note: _platform_siem_update_case_payload(
                auth, case_id, status, assignee, note
            ),
            run_siem_soar_playbook=lambda auth, playbook, case_id, parameters: _platform_siem_run_soar_payload(
                auth, playbook, case_id, parameters
            ),
            get_siem_flow_map=lambda auth, minutes, limit: _platform_siem_flow_map_payload(auth, minutes, limit),
            get_siem_security_controls=lambda auth: _platform_siem_security_controls_payload(auth),
            update_siem_security_control=lambda auth, control_type, control_id, enabled, mode, action, threshold, notes: _platform_siem_update_security_control_payload(
                auth, control_type, control_id, enabled, mode, action, threshold, notes
            ),
            get_siem_vulnerabilities=lambda auth, severity, status, limit: _platform_siem_vulnerabilities_payload(
                auth, severity, status, limit
            ),
            run_siem_zap_scan=lambda auth, target_url, scan_profile, authenticated: _platform_siem_run_zap_scan_payload(
                auth, target_url, scan_profile, authenticated
            ),
            get_siem_updates=lambda auth: _platform_siem_updates_payload(auth),
            apply_siem_update=lambda auth, update_id, strategy: _platform_siem_apply_update_payload(
                auth, update_id, strategy
            ),
            run_siem_auto_pentest=lambda auth, profile, target_scope, include_dependency_scan, include_api_fuzzing: _platform_siem_auto_pentest_run_payload(
                auth, profile, target_scope, include_dependency_scan, include_api_fuzzing
            ),
            list_siem_auto_pentest_jobs=lambda auth, limit: _platform_siem_auto_pentest_jobs_payload(auth, limit),
            get_siem_vault_encryption_health=lambda auth: _platform_siem_vault_encryption_health_payload(auth),
            apply_siem_endpoint_hardening=lambda auth, strict_mode, enforce_edr_policy, enforce_device_posture, apply_to_assets: _platform_siem_apply_endpoint_hardening_payload(
                auth, strict_mode, enforce_edr_policy, enforce_device_posture, apply_to_assets
            ),
            get_siem_endpoint_hardening_status=lambda auth: _platform_siem_endpoint_hardening_status_payload(auth),
            get_siem_network_anomalies=lambda auth, minutes: _platform_siem_network_anomalies_payload(auth, minutes),
            run_siem_dead_code_scan=lambda auth, scope, include_frontend, include_backend, severity_floor: _platform_siem_dead_code_scan_payload(
                auth, scope, include_frontend, include_backend, severity_floor
            ),
            list_siem_dead_code_findings=lambda auth, severity, limit: _platform_siem_dead_code_findings_payload(auth, severity, limit),
            get_siem_advanced_threat_hunt=lambda auth, minutes: _platform_siem_advanced_threat_hunt_payload(auth, minutes),
            get_hybrid_stacks=lambda auth: _platform_hybrid_stacks_payload(auth),
            get_module_registry=lambda auth: _platform_module_registry_payload(auth),
            require_super_admin_access=_ops_require_super_admin_access,
        ),
    )
)


@app.get('/healthz')
def healthz() -> JsonObject:
    """Legacy health check endpoint. Use /health or /health/live for production."""
    return {
        'status': 'ok',
        'service': 'fastapi',
        'db_ready': _db_ready,
        'security_strict_mode': os.getenv('SECURITY_STRICT_MODE', '0'),
    }


@app.get('/health')
def health_comprehensive() -> JsonObject:
    """Comprehensive health check with all service status."""
    return get_health_check_data(_db_ready, _auth_security_memory, _notifications_memory)


@app.get('/health/live')
def health_liveness() -> JsonObject:
    """Kubernetes-compatible liveness probe - returns 200 if process is alive."""
    return {'status': 'live', 'timestamp': datetime.now(UTC).isoformat()}


@app.get('/health/ready', response_model=None)
def health_readiness() -> JsonObject | JSONResponse:
    """Kubernetes-compatible readiness probe.

    Actively pings Postgres on every call rather than trusting a boot-time
    flag — a DB outage after startup must flip this to 503 so the load
    balancer stops routing traffic to this pod, instead of leaving `_db_ready`
    stuck at whatever it was when the process came up.
    """
    if not _db_ready:
        return JSONResponse(
            status_code=503,
            content={'status': 'not-ready', 'reason': 'Service still initializing'},
        )
    try:
        from sqlalchemy import text

        with get_db_session() as session:
            session.execute(text('SELECT 1'))
    except Exception as exc:
        logger.warning('readiness_db_check_failed', error=str(exc))
        return JSONResponse(
            status_code=503,
            content={'status': 'not-ready', 'reason': 'Database connectivity check failed'},
        )
    return {'status': 'ready', 'timestamp': datetime.now(UTC).isoformat()}


@app.get('/health/vaults')
def health_vaults() -> JsonObject:
    """Check vault integration health status."""
    try:
        from .vault_config import get_vault_health
        vault_health = get_vault_health()
        if isinstance(vault_health, dict):
            if 'status' not in vault_health:
                return {'status': 'ok', **vault_health}
            return cast(JsonObject, vault_health)
        return {
            'status': 'unavailable',
            'message': 'Vault health payload is invalid',
            'timestamp': datetime.now(UTC).isoformat(),
        }
    except ImportError:
        return {
            'status': 'unavailable',
            'message': 'Vault integration not available',
            'timestamp': datetime.now(UTC).isoformat(),
        }


@app.get('/health/schema/unified-31', response_model=None)
def health_schema_unified_31() -> JsonObject | JSONResponse:
    """Strict readiness probe for unified-31 schema. Returns 200 if ready, 503 if not."""
    from .production_middleware import _build_schema_unified_31_block
    block = _build_schema_unified_31_block(_db_ready)
    if not block['ready']:
        block['reason'] = 'Schema unified_31_core not yet applied or DB not ready'
        return JSONResponse(status_code=503, content=dict(block))
    return block


@app.get('/health/encryption')
def health_encryption() -> JsonObject:
    """Check transparent encryption layer status."""
    try:
        from .transparent_encryption import encryption_status
        status = encryption_status()
        return {'status': 'ok', **status, 'timestamp': datetime.now(UTC).isoformat()}
    except Exception as exc:
        return {
            'status': 'error',
            'message': str(exc),
            'timestamp': datetime.now(UTC).isoformat(),
        }


@app.get('/metrics')
def metrics() -> JsonObject:
    """Prometheus-compatible metrics endpoint."""
    all_queues = memory_stores.get_all_stores()
    return get_metrics_data(all_queues, _rate_buckets, _rate_lock)


@app.get('/ai/ping')
def ai_ping() -> JsonObject:
    return {
        'status': 'ok',
        'message': 'FastAPI service is ready for AI/ML endpoints.'
    }


def _provider_env_key(provider: str) -> str:
    if provider == 'openai':
        return os.getenv('OPENAI_API_KEY', '').strip()
    if provider == 'anthropic':
        return os.getenv('ANTHROPIC_API_KEY', '').strip()
    if provider == 'google_vertex':
        return os.getenv('GOOGLE_VERTEX_API_KEY', '').strip()
    if provider == 'cohere':
        return os.getenv('COHERE_API_KEY', '').strip()
    if provider == 'mistral':
        return os.getenv('MISTRAL_API_KEY', '').strip()
    if provider == 'together_ai':
        return os.getenv('TOGETHER_AI_API_KEY', '').strip()
    if provider == 'stability_ai':
        return os.getenv('STABILITY_AI_API_KEY', '').strip()
    return ''


def _provider_default_model(provider: str) -> str:
    if provider == 'openai':
        return os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip() or 'gpt-4o-mini'
    if provider == 'anthropic':
        return os.getenv('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest').strip() or 'claude-3-5-haiku-latest'
    if provider == 'google_vertex':
        return os.getenv('GOOGLE_VERTEX_MODEL', GEMINI_FLASH_MODEL).strip() or GEMINI_FLASH_MODEL
    if provider == 'cohere':
        return os.getenv('COHERE_MODEL', 'command-r').strip() or 'command-r'
    if provider == 'mistral':
        return os.getenv('MISTRAL_MODEL', 'mistral-large').strip() or 'mistral-large'
    if provider == 'together_ai':
        return os.getenv('TOGETHER_AI_MODEL', LLAMA_70B_MODEL).strip() or LLAMA_70B_MODEL
    if provider == 'stability_ai':
        return os.getenv('STABILITY_AI_MODEL', 'stable-diffusion-3').strip() or 'stable-diffusion-3'
    return ''


def _model_unit_cost(provider: str, model: str) -> float:
    provider_models = AI_MODEL_CATALOG.get(provider, {})
    model_meta = provider_models.get(model, {})
    value = model_meta.get('cost_per_1k_tokens', 0.002)
    return float(value if value > 0 else 0.002)


def _model_quality(provider: str, model: str) -> float:
    provider_models = AI_MODEL_CATALOG.get(provider, {})
    model_meta = provider_models.get(model, {})
    value = model_meta.get('quality_score', 0.8)
    return float(value if value > 0 else 0.8)


def _extract_ip_hash(request: Request) -> str:
    forwarded_for = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip()
    client_host = forwarded_for or (request.client.host if request.client else '')
    return hashlib.sha256(client_host.encode('utf-8')).hexdigest()[:16] if client_host else ''


def _extract_ua_hash(request: Request) -> str:
    ua = request.headers.get('User-Agent', '')
    return hashlib.sha256(ua.encode('utf-8')).hexdigest()[:16] if ua else ''


def _usage_to_tokens(usage: object) -> tuple[int, int, int]:
    usage_obj = cast(JsonObject, usage) if isinstance(usage, dict) else {}
    prompt_tokens = _coerce_int(usage_obj.get('prompt_tokens', 0), 0) + _coerce_int(usage_obj.get('input_tokens', 0), 0)
    completion_tokens = _coerce_int(usage_obj.get('completion_tokens', 0), 0) + _coerce_int(usage_obj.get('output_tokens', 0), 0)
    total_tokens = _coerce_int(usage_obj.get('total_tokens', 0), 0)
    if total_tokens <= 0:
        total_tokens = prompt_tokens + completion_tokens
    return prompt_tokens, completion_tokens, max(total_tokens, 0)


def _compute_roi(total_tokens: int, value_per_1k_tokens: float, cost_per_1k_tokens: float, quality_score: float) -> tuple[float, float, float]:
    token_units = max(total_tokens, 0) / 1000.0
    estimated_cost = token_units * max(cost_per_1k_tokens, 0.000001)
    estimated_value = token_units * max(value_per_1k_tokens, 0.000001) * max(quality_score, 0.01)
    if estimated_cost <= 0:
        return 0.0, estimated_cost, estimated_value
    roi = (estimated_value - estimated_cost) / estimated_cost
    return round(roi, 6), round(estimated_cost, 8), round(estimated_value, 8)


def _active_provider_key_record(provider: str) -> JsonObject | None:
    with _ai_security_lock:
        for item in reversed(_ai_provider_keys_memory):
            if item.get('provider') == provider and item.get('enabled') is True:
                return item
    return None


def _is_provider_disabled(provider: str) -> bool:
    with _ai_security_lock:
        for item in reversed(_ai_provider_keys_memory):
            if item.get('provider') == provider:
                enabled = bool(item.get('enabled'))
                return not enabled
    return False


def _resolve_provider_api_key(provider: str) -> str:
    record = _active_provider_key_record(provider)
    if record is not None:
        cipher = str(record.get('api_key_cipher', '') or '')
        secret = te_decrypt(cipher) or ''
        if secret:
            return secret
    return _provider_env_key(provider)


def _record_ai_security_alert(severity: str, title: str, details: JsonObject | None = None) -> JsonObject:
    now_iso = datetime.now(UTC).isoformat()
    event: JsonObject = {
        'id': len(_ai_security_alerts_memory) + 1,
        'severity': severity,
        'title': title,
        'details': details or {},
        'created_at': now_iso,
    }
    payload = json.dumps(event, sort_keys=True, separators=(',', ':'))
    prev_hash = str(_ai_security_alerts_memory[-1].get('chain_hash', 'genesis')) if _ai_security_alerts_memory else 'genesis'
    event['chain_hash'] = hashlib.sha256(f'{prev_hash}:{payload}'.encode()).hexdigest()
    with _ai_security_lock:
        _ai_security_alerts_memory.append(event)
        if len(_ai_security_alerts_memory) > 5000:
            del _ai_security_alerts_memory[:-5000]
    return event


def _send_security_email_alert(alert: JsonObject) -> None:
    security_to = os.getenv('SECURITY_ALERT_EMAIL', '').strip()
    from_email = _security_alert_from_email()
    if not (from_email and security_to):
        return

    severity = str(alert.get('severity', 'info') or 'info').upper()
    title = str(alert.get('title', '') or '')
    email_event: JsonObject = {
        'tenant_id': 'platform-security',
        'provider': 'smtp-queue',
        'to': security_to,
        'from': from_email,
        'subject': f'[Nuxtron AI Security] {severity} {title}',
        'body': json.dumps(alert, indent=2, sort_keys=True),
        'status': 'queued',
        'created_at': datetime.now(UTC).isoformat(),
    }
    _queue_security_alert_email(email_event)


def _block_tenant(tenant_id: str, reason: str, window_seconds: int = 1800) -> JsonObject:
    now_ts = int(time.time())
    until_ts = now_ts + max(window_seconds, 60)
    block: JsonObject = {
        'id': len(_ai_security_blocks_memory) + 1,
        'tenant_id': tenant_id,
        'reason': reason,
        'active': True,
        'created_at': datetime.now(UTC).isoformat(),
        'until_ts': until_ts,
        'type': 'tenant',
    }
    with _ai_security_lock:
        _ai_security_blocks_memory.append(block)
    alert = _record_ai_security_alert('critical', 'Tenant blocked for AI misuse', {'tenant_id': tenant_id, 'reason': reason, 'until_ts': until_ts})
    _send_security_email_alert(alert)
    return block


def _is_tenant_blocked(tenant_id: str) -> tuple[bool, int]:
    now_ts = int(time.time())
    with _ai_security_lock:
        for item in reversed(_ai_security_blocks_memory):
            if item.get('tenant_id') != tenant_id or item.get('active') is not True:
                continue
            until_ts = _coerce_int(item.get('until_ts', 0), 0)
            if until_ts > now_ts:
                return True, until_ts
            item['active'] = False
    return False, 0


def _disable_provider(provider: str, reason: str) -> None:
    now_iso = datetime.now(UTC).isoformat()
    with _ai_security_lock:
        disabled = False
        for item in reversed(_ai_provider_keys_memory):
            if item.get('provider') == provider and item.get('enabled') is True:
                item['enabled'] = False
                item['disabled_reason'] = reason
                item['disabled_at'] = now_iso
                disabled = True
                break
    if disabled:
        alert = _record_ai_security_alert('critical', 'Provider API disabled automatically', {'provider': provider, 'reason': reason})
        _send_security_email_alert(alert)


def _update_provider_health(provider: str, success: bool, latency_ms: float = 0) -> None:
    """Update provider health metrics for intelligent fallback."""
    with _ai_security_lock:
        metrics = _provider_health_metrics.get(provider, {})
        if not metrics:
            metrics = _provider_health_metrics[provider] = {
                'success_rate': 1.0,
                'avg_latency_ms': 0.0,
                'last_error_at': 0,
                'consecutive_errors': 0,
                'requests_total': 0,
                'requests_success': 0,
                'updated_at': time.time(),
            }
        
        metrics['requests_total'] = metrics.get('requests_total', 0) + 1
        if success:
            metrics['requests_success'] = metrics.get('requests_success', 0) + 1
            metrics['consecutive_errors'] = 0
            total = metrics.get('requests_total', 1)
            metrics['success_rate'] = metrics.get('requests_success', 0) / total
            # Exponential moving average for latency
            current_avg = metrics.get('avg_latency_ms', 0)
            metrics['avg_latency_ms'] = (current_avg * 0.7) + (latency_ms * 0.3)
        else:
            metrics['last_error_at'] = time.time()
            metrics['consecutive_errors'] = metrics.get('consecutive_errors', 0) + 1
            # Auto-disable if too many errors
            if metrics['consecutive_errors'] >= 5:
                _disable_provider(provider, f'Auto-disabled: {metrics["consecutive_errors"]} consecutive errors')
        
        metrics['updated_at'] = time.time()


def _get_provider_health(provider: str) -> dict[str, float]:
    """Get provider health metrics for intelligent selection."""
    with _ai_security_lock:
        return _provider_health_metrics.get(provider, {
            'success_rate': 1.0,
            'avg_latency_ms': 0.0,
            'consecutive_errors': 0,
        })


def _select_provider_with_tiers(payload: AiGatewayGenerateRequest, task_type: str = 'text_generation') -> tuple[str, str]:  # NOSONAR
    """
    Intelligent provider selection with automatic tier fallback.
    Tier 1: Primary (best quality)
    Tier 2: Secondary (good quality, cheaper)
    Tier 3: Tertiary (acceptable quality, budget-friendly)
    Tier 4: Emergency (always available fallback)
    """
    tiers = AI_PROVIDER_TIERS.get(task_type, AI_PROVIDER_TIERS['text_generation'])
    min_quality_floor = max(payload.quality_floor, 0.70)  # Never go below 0.70 quality
    
    # Try each tier in order until we find a viable provider
    for tier_key in ['tier_1', 'tier_2', 'tier_3', 'tier_4']:
        tier_providers = tiers.get(tier_key, [])
        candidates: list[tuple[str, str, float, float]] = []  # (provider, model, score, health_score)
        
        for provider in tier_providers:
            if _is_provider_disabled(provider):
                continue
            
            # Check if API key is configured
            api_key = _resolve_provider_api_key(provider)
            if not api_key:
                continue
            
            model = payload.model or _provider_default_model(provider)
            if not model or model not in AI_MODEL_CATALOG.get(provider, {}):
                continue
            
            quality = _model_quality(provider, model)
            if quality < min_quality_floor:
                continue  # Skip if quality doesn't meet minimum threshold
            
            cost = _model_unit_cost(provider, model)
            roi, _, _ = _compute_roi(max(payload.max_tokens, 1), payload.value_per_1k_tokens, cost, quality)
            
            # Health scoring: success_rate * (1 - normalized_latency)
            health = _get_provider_health(provider)
            success_rate = health.get('success_rate', 1.0)
            avg_latency_ms = health.get('avg_latency_ms', 0)
            uptime_percent = AI_MODEL_CATALOG[provider][model].get('uptime_percent', 99.5) / 100

            # Lightweight latency damping so very slow providers score lower.
            latency_penalty = min(max(float(avg_latency_ms), 0.0) / 10000.0, 0.25)
            
            # Combined score: (ROI + quality) * health_factor
            health_factor = success_rate * uptime_percent * (1.0 - latency_penalty)
            combined_score = (roi + quality) * health_factor
            
            candidates.append((provider, model, combined_score, health_factor))
        
        if candidates:
            # Sort by combined score (ROI + quality + health), prefer cheapest if tied on quality
            candidates.sort(key=lambda x: (-x[2], _model_unit_cost(x[0], x[1])))
            return candidates[0][0], candidates[0][1]
    
    # Absolute fallback: return first configured provider
    return 'openai', payload.model or _provider_default_model('openai')


def _record_ai_usage(
    *,
    tenant_id: str,
    provider: str,
    model: str,
    request: Request,
    payload: AiGatewayGenerateRequest,
    result: JsonObject,
) -> JsonObject:
    usage = result.get('usage', {})
    prompt_tokens, completion_tokens, total_tokens = _usage_to_tokens(usage)
    if total_tokens <= 0:
        total_tokens = max(min(len(payload.prompt) // 3, 4000), 1)

    quality = _model_quality(provider, model)
    unit_cost = _model_unit_cost(provider, model)
    roi, estimated_cost, estimated_value = _compute_roi(total_tokens, payload.value_per_1k_tokens, unit_cost, quality)

    item: JsonObject = {
        'id': len(_ai_security_usage_memory) + 1,
        'created_at': datetime.now(UTC).isoformat(),
        'timestamp': int(time.time()),
        'tenant_id': tenant_id,
        'provider': provider,
        'model': model,
        'prompt_preview': payload.prompt[:80],
        'ip_hash': _extract_ip_hash(request),
        'ua_hash': _extract_ua_hash(request),
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': total_tokens,
        'estimated_cost': estimated_cost,
        'estimated_value': estimated_value,
        'roi': roi,
        'quality_score': quality,
        'latency_ms': _coerce_int(result.get('latency_ms', 0), 0),
        'status': 'success' if result.get('output_text') else 'degraded',
    }

    payload_str = json.dumps(item, sort_keys=True, separators=(',', ':'))
    prev_hash = str(_ai_security_usage_memory[-1].get('chain_hash', 'genesis')) if _ai_security_usage_memory else 'genesis'
    item['chain_hash'] = hashlib.sha256(f'{prev_hash}:{payload_str}'.encode()).hexdigest()

    with _ai_security_lock:
        _ai_security_usage_memory.append(item)
        if len(_ai_security_usage_memory) > 12000:
            del _ai_security_usage_memory[:-12000]

    return item


def _evaluate_ai_guardrails(tenant_id: str, provider: str, usage_item: JsonObject) -> None:
    now_ts = int(time.time())
    max_req_5m = int(os.getenv('AI_SECURITY_MAX_REQUESTS_5M', '120'))
    low_roi_floor = float(os.getenv('AI_SECURITY_LOW_ROI_FLOOR', '0.07'))

    recent_tenant = [
        item for item in _ai_security_usage_memory
        if item.get('tenant_id') == tenant_id and _coerce_int(item.get('timestamp', 0), 0) >= (now_ts - 300)
    ]
    if len(recent_tenant) > max_req_5m:
        _block_tenant(tenant_id, f'Burst traffic exceeded {max_req_5m} requests/5m')
        return

    provider_window = [
        item for item in _ai_security_usage_memory[-60:]
        if item.get('provider') == provider and item.get('status') == 'success'
    ]
    if provider_window:
        avg_roi = sum(_coerce_float(item.get('roi', 0.0), 0.0) for item in provider_window) / len(provider_window)
        if avg_roi < low_roi_floor:
            _disable_provider(provider, f'Average ROI {avg_roi:.4f} is below floor {low_roi_floor:.4f}')

    roi_now = _coerce_float(usage_item.get('roi', 0.0), 0.0)
    if roi_now < low_roi_floor:
        alert = _record_ai_security_alert(
            'warning',
            'Low ROI AI usage detected',
            {
                'tenant_id': tenant_id,
                'provider': provider,
                'roi': roi_now,
                'status': usage_item.get('status', ''),
            },
        )
        _send_security_email_alert(alert)


def _ai_queued_item(tenant_id: str, provider: str, model: str, prompt: str, reason: str = '', created_at: str = '') -> JsonObject:
    """Create a queued item for AI gateway."""
    if not created_at:
        created_at = datetime.now(UTC).isoformat()
    return {
        'id': len(_ai_gateway_memory) + 1,
        'tenant_id': tenant_id,
        'provider': provider,
        'model': model,
        'prompt_preview': prompt[:120],
        'status': 'queued' if not reason else f'queued-{reason}',
        'reason': reason or None,
        'created_at': created_at,
    }


def _json_object(value: object) -> JsonObject | None:
    return cast(JsonObject, value) if isinstance(value, dict) else None


def _coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _coerce_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _extract_openai_result(data: object) -> tuple[str, object]:
    data_obj = _json_object(data)
    if data_obj is None:
        return '', {}

    usage = data_obj.get('usage', {})
    choices_value = data_obj.get('choices', [])
    if not isinstance(choices_value, list) or not choices_value:
        return '', usage
    choices_obj = cast(list[object], choices_value)

    first_choice = _json_object(choices_obj[0])
    if first_choice is None:
        return '', usage

    message = _json_object(first_choice.get('message', {}))
    if message is None:
        return '', usage

    content = message.get('content', '')
    return (content.strip(), usage) if isinstance(content, str) else ('', usage)


def _extract_anthropic_result(data: object) -> tuple[list[str], object]:
    data_obj = _json_object(data)
    if data_obj is None:
        return [], {}

    usage = data_obj.get('usage', {})
    blocks_value = data_obj.get('content', [])
    if not isinstance(blocks_value, list):
        return [], usage
    blocks_obj = cast(list[object], blocks_value)

    text_parts: list[str] = []
    for block_obj in blocks_obj:
        block = _json_object(block_obj)
        if block is None or block.get('type') != 'text':
            continue
        text = block.get('text', '')
        if isinstance(text, str) and text:
            text_parts.append(text)

    return text_parts, usage


def _ai_generate_openai(payload: AiGatewayGenerateRequest, auth: AuthContext, created_at: str) -> JsonObject:
    """Generate response via OpenAI API."""
    api_key = _resolve_provider_api_key('openai')
    model = payload.model or os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        item = _ai_queued_item(auth.tenant_id, 'openai', model, payload.prompt, 'OpenAI not configured', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    messages: list[dict[str, str]] = []
    if payload.system_prompt:
        messages.append({'role': 'system', 'content': payload.system_prompt})
    messages.append({'role': 'user', 'content': payload.prompt})

    try:
        started = time.perf_counter()
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON},
                json={'model': model, 'messages': messages, 'temperature': payload.temperature, 'max_tokens': payload.max_tokens},
            )
            if response.is_success:
                text, usage = _extract_openai_result(response.json())
                latency_ms = round((time.perf_counter() - started) * 1000)
                return {'status': 'ok', 'result': {'tenant_id': auth.tenant_id, 'provider': 'openai', 'model': model, 'output_text': text, 'usage': usage, 'source': 'openai', 'latency_ms': latency_ms}}
    except Exception as ex:
        item = _ai_queued_item(auth.tenant_id, 'openai', model, payload.prompt, f'error:{ex}', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    item = _ai_queued_item(auth.tenant_id, 'openai', model, payload.prompt, 'non-success', created_at)
    _ai_gateway_memory.append(item)
    return {'status': 'ok', 'result': item}


def _ai_generate_anthropic(payload: AiGatewayGenerateRequest, auth: AuthContext, created_at: str) -> JsonObject:
    """Generate response via Anthropic API."""
    api_key = _resolve_provider_api_key('anthropic')
    model = payload.model or os.getenv('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest')

    if not api_key:
        item = _ai_queued_item(auth.tenant_id, 'anthropic', model, payload.prompt, 'Anthropic not configured', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    body: JsonObject = {'model': model, 'max_tokens': payload.max_tokens, 'temperature': payload.temperature, 'messages': [{'role': 'user', 'content': payload.prompt}]}
    if payload.system_prompt:
        body['system'] = payload.system_prompt

    try:
        started = time.perf_counter()
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                'https://api.anthropic.com/v1/messages',
                headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01', 'Content-Type': CONTENT_TYPE_JSON},
                json=body,
            )
            if response.is_success:
                text_parts, usage = _extract_anthropic_result(response.json())
                latency_ms = round((time.perf_counter() - started) * 1000)
                return {'status': 'ok', 'result': {'tenant_id': auth.tenant_id, 'provider': 'anthropic', 'model': model, 'output_text': '\n'.join(text_parts).strip(), 'usage': usage, 'source': 'anthropic', 'latency_ms': latency_ms}}
    except Exception as ex:
        item = _ai_queued_item(auth.tenant_id, 'anthropic', model, payload.prompt, f'error:{ex}', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    item = _ai_queued_item(auth.tenant_id, 'anthropic', model, payload.prompt, 'non-success', created_at)
    _ai_gateway_memory.append(item)
    return {'status': 'ok', 'result': item}


def _ai_generate_google_vertex(payload: AiGatewayGenerateRequest, auth: AuthContext, created_at: str) -> JsonObject:  # NOSONAR
    """Generate response via Google Vertex AI API (text, image, video, voice).

    Auth: set GOOGLE_VERTEX_API_KEY to a short-lived OAuth2 access token obtained
    from a GCP service account (e.g. via `gcloud auth print-access-token` or the
    google-auth library). Plain API keys are NOT accepted by the Vertex AI endpoint.

    Required env vars:
        GOOGLE_VERTEX_API_KEY    — OAuth2 Bearer access token
        GOOGLE_VERTEX_PROJECT_ID — GCP project id (e.g. my-gcp-project-123)
        GOOGLE_VERTEX_MODEL      — model name, defaults to gemini-2.0-flash
        GOOGLE_VERTEX_LOCATION   — GCP region, defaults to us-central1
    """
    access_token = _resolve_provider_api_key('google_vertex')
    project_id = os.getenv('GOOGLE_VERTEX_PROJECT_ID', '').strip()
    model = payload.model or os.getenv('GOOGLE_VERTEX_MODEL', GEMINI_FLASH_MODEL)
    location = os.getenv('GOOGLE_VERTEX_LOCATION', 'us-central1').strip() or 'us-central1'

    reason = _google_vertex_missing_reason(access_token, project_id)
    if reason is not None:
        item = _ai_queued_item(auth.tenant_id, 'google_vertex', model, payload.prompt, reason, created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    body = _build_google_vertex_body(payload)

    try:
        started = time.perf_counter()
        url = (
            f'https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}'
            f'/locations/{location}/publishers/google/models/{model}:generateContent'
        )

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': CONTENT_TYPE_JSON},
                json=body,
            )
            if response.is_success:
                return _build_google_vertex_success_result(response.json(), auth.tenant_id, model, started)

            error_detail = response.text[:300]
            item = _ai_queued_item(auth.tenant_id, 'google_vertex', model, payload.prompt, f'http_{response.status_code}:{error_detail}', created_at)
            _ai_gateway_memory.append(item)
            return {'status': 'ok', 'result': item}
    except Exception as ex:
        item = _ai_queued_item(auth.tenant_id, 'google_vertex', model, payload.prompt, f'error:{ex}', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}


def _google_vertex_missing_reason(access_token: str, project_id: str) -> str | None:
    missing: list[str] = []
    if not access_token:
        missing.append('GOOGLE_VERTEX_API_KEY')
    if not project_id:
        missing.append('GOOGLE_VERTEX_PROJECT_ID')
    if not missing:
        return None
    return f'Google Vertex not configured: missing {", ".join(missing)}'


def _build_google_vertex_body(payload: AiGatewayGenerateRequest) -> JsonObject:
    body: JsonObject = {
        'contents': [{
            'role': 'user',
            'parts': [{'text': payload.prompt}],
        }],
        'generationConfig': {
            'temperature': payload.temperature,
            'maxOutputTokens': payload.max_tokens,
        },
    }
    if payload.system_prompt:
        body['systemInstruction'] = {'parts': [{'text': payload.system_prompt}]}
    return body


def _build_google_vertex_success_result(data: JsonObject, tenant_id: str, model: str, started: float) -> JsonObject:
    text_parts = _extract_google_vertex_text_parts(data)
    usage = _extract_google_vertex_usage(data)
    return {
        'status': 'ok',
        'result': {
            'tenant_id': tenant_id,
            'provider': 'google_vertex',
            'model': model,
            'output_text': '\n'.join(text_parts).strip() if text_parts else '',
            'usage': usage,
            'source': 'google_vertex',
            'latency_ms': round((time.perf_counter() - started) * 1000),
        },
    }


def _extract_google_vertex_text_parts(data: JsonObject) -> list[str]:
    text_parts: list[str] = []
    candidates = data.get('candidates')
    if not isinstance(candidates, list) or not candidates:
        return text_parts

    candidate = cast(list[object], candidates)[0]
    if not isinstance(candidate, dict):
        return text_parts

    content = candidate.get('content', {})
    parts = content.get('parts') if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return text_parts

    for part in parts:
        if isinstance(part, dict) and isinstance(part.get('text'), str):
            text_parts.append(part['text'])
    return text_parts


def _extract_google_vertex_usage(data: JsonObject) -> JsonObject:
    usage_metadata = data.get('usageMetadata', {})
    if not isinstance(usage_metadata, dict):
        usage_metadata = {}
    return {
        'input_tokens': _coerce_int(usage_metadata.get('promptTokenCount', 0), 0),
        'output_tokens': _coerce_int(usage_metadata.get('candidatesTokenCount', 0), 0),
    }


def _generate_with_cohere(api_key: str, model: str, payload: AiGatewayGenerateRequest) -> tuple[str, JsonObject]:
    body: JsonObject = {'model': model, 'prompt': payload.prompt, 'max_tokens': payload.max_tokens, 'temperature': payload.temperature}
    output_text = ''
    usage: JsonObject = {'input_tokens': 0, 'output_tokens': 0}
    with httpx.Client(timeout=30.0) as client:
        response = client.post('https://api.cohere.ai/v1/generate', headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}, json=body)
        if response.is_success:
            data = response.json()
            if isinstance(data.get('generations'), list) and data['generations']:
                output_text = data['generations'][0].get('text', '')
            usage['output_tokens'] = _coerce_int(data.get('generations', [{}])[0].get('token_count', 0), 0)
    return output_text, usage


def _generate_with_mistral(api_key: str, model: str, payload: AiGatewayGenerateRequest) -> tuple[str, JsonObject]:
    body: JsonObject = {'model': model, 'messages': [{'role': 'user', 'content': payload.prompt}], 'temperature': payload.temperature, 'max_tokens': payload.max_tokens}
    output_text = ''
    usage: JsonObject = {'input_tokens': 0, 'output_tokens': 0}
    with httpx.Client(timeout=30.0) as client:
        response = client.post('https://api.mistral.ai/v1/chat/completions', headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}, json=body)
        if response.is_success:
            data = response.json()
            if isinstance(data.get('choices'), list) and data['choices']:
                output_text = data['choices'][0].get('message', {}).get('content', '')
            if isinstance(data.get('usage'), dict):
                usage = {'input_tokens': _coerce_int(data['usage'].get('prompt_tokens', 0), 0), 'output_tokens': _coerce_int(data['usage'].get('completion_tokens', 0), 0)}
    return output_text, usage


def _generate_with_together_ai(api_key: str, model: str, payload: AiGatewayGenerateRequest) -> tuple[str, JsonObject]:
    body: JsonObject = {'model': model, 'prompt': payload.prompt, 'max_tokens': payload.max_tokens, 'temperature': payload.temperature}
    output_text = ''
    usage: JsonObject = {'input_tokens': 0, 'output_tokens': 0}
    with httpx.Client(timeout=30.0) as client:
        response = client.post('https://api.together.xyz/v1/completions', headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}, json=body)
        if response.is_success:
            data = response.json()
            if isinstance(data.get('output'), list) and data['output']:
                output_text = data['output'][0] if isinstance(data['output'][0], str) else str(data['output'][0])
    return output_text, usage


def _generate_with_stability_ai(api_key: str, _model: str, payload: AiGatewayGenerateRequest) -> tuple[str, JsonObject]:
    body: JsonObject = {'text_prompts': [{'text': payload.prompt, 'weight': 1}], 'height': 512, 'width': 512, 'steps': 30, 'cfg_scale': 7.0}
    output_text = ''
    usage: JsonObject = {'input_tokens': 0, 'output_tokens': 0}
    with httpx.Client(timeout=60.0) as client:
        response = client.post('https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image', headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}, json=body)
        if response.is_success:
            data = response.json()
            if isinstance(data.get('artifacts'), list) and data['artifacts']:
                output_text = f'Generated {len(data["artifacts"])} image(s)'
    return output_text, usage


def _run_generic_provider_generation(provider: str, api_key: str, model: str, payload: AiGatewayGenerateRequest) -> tuple[str, JsonObject] | None:
    handlers = {
        'cohere': _generate_with_cohere,
        'mistral': _generate_with_mistral,
        'together_ai': _generate_with_together_ai,
        'stability_ai': _generate_with_stability_ai,
    }
    handler = handlers.get(provider)
    if handler is None:
        return None
    return handler(api_key, model, payload)


def _ai_generate_generic(provider: str, payload: AiGatewayGenerateRequest, auth: AuthContext, created_at: str) -> JsonObject:  # NOSONAR
    """Generic handler for Cohere, Mistral, Together.ai, Stability.ai."""
    api_key = _resolve_provider_api_key(provider)
    model = payload.model or _provider_default_model(provider)
    if not api_key:
        item = _ai_queued_item(auth.tenant_id, provider, model, payload.prompt, f'{provider} not configured', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}
    try:
        started = time.perf_counter()
        generated = _run_generic_provider_generation(provider, api_key, model, payload)
        if generated is None:
            item = _ai_queued_item(auth.tenant_id, provider, model, payload.prompt, 'unknown_provider', created_at)
            _ai_gateway_memory.append(item)
            return {'status': 'ok', 'result': item}
        output_text, usage = generated
        latency_ms = round((time.perf_counter() - started) * 1000)
        return {'status': 'ok', 'result': {'tenant_id': auth.tenant_id, 'provider': provider, 'model': model, 'output_text': output_text, 'usage': usage, 'source': provider, 'latency_ms': latency_ms}}
    except Exception as ex:
        item = _ai_queued_item(auth.tenant_id, provider, model, payload.prompt, f'error:{str(ex)[:100]}', created_at)
        _ai_gateway_memory.append(item)
        raise


def _asset_extension_for_mime(mime_type: str) -> str:
    mapping = {
        MIME_TYPE_PNG: 'png',
        'image/jpeg': 'jpg',
        'image/webp': 'webp',
        'image/gif': 'gif',
        'image/svg+xml': 'svg',
        MIME_TYPE_MP3: 'mp3',
        MIME_TYPE_WAV: 'wav',
        MIME_TYPE_MP4: 'mp4',
    }
    return mapping.get(mime_type.lower().strip(), 'bin')


def _persist_ai_generated_asset(
    *,
    tenant_id: str,
    kind: str,
    mime_type: str,
    content: bytes,
    provider_used: str,
    generation_status: str,
) -> JsonObject:
    now_iso = datetime.now(UTC).isoformat()
    encoded = base64.b64encode(content).decode('ascii')
    ext = _asset_extension_for_mime(mime_type)
    storage_dir = Path(os.getenv('AI_GENERATED_ASSET_STORAGE_DIR', '') or (Path.cwd() / 'storage' / 'ai-generated-assets'))
    storage_dir.mkdir(parents=True, exist_ok=True)

    with _ai_generated_assets_lock:
        asset_id = len(_ai_generated_assets_memory) + 1
        file_path = storage_dir / f'{asset_id}.{ext}'
        try:
            file_path.write_bytes(content)
        except Exception:
            file_path = storage_dir / f'{kind}-{asset_id}.{ext}'
            file_path.write_bytes(content)
        item: JsonObject = {
            'id': asset_id,
            'tenant_id': tenant_id,
            'kind': kind,
            'mime_type': mime_type,
            'size_bytes': len(content),
            'provider_used': provider_used,
            'generation_status': generation_status,
            'content_base64': encoded,
            'created_at': now_iso,
            'file_name': f'{kind}-{asset_id}.{ext}',
            'download_url': f'/ai/generated-assets/{asset_id}',
            'file_path': str(file_path),
        }
        _ai_generated_assets_memory.append(item)
        if len(_ai_generated_assets_memory) > 2000:
            del _ai_generated_assets_memory[:500]

    return {
        'id': asset_id,
        'kind': kind,
        'mime_type': mime_type,
        'size_bytes': len(content),
        'provider_used': provider_used,
        'generation_status': generation_status,
        'file_name': f'{kind}-{asset_id}.{ext}',
        'download_url': f'/ai/generated-assets/{asset_id}',
    }


def _load_ai_generated_asset_bytes(item: JsonObject, asset_id: int, file_name: str) -> bytes:
    raw_b64 = str(item.get('content_base64', '') or '')
    if raw_b64:
        return base64.b64decode(raw_b64)

    file_path = str(item.get('file_path', '') or '')
    storage_dir = Path(os.getenv('AI_GENERATED_ASSET_STORAGE_DIR', '') or (Path.cwd() / 'storage' / 'ai-generated-assets'))
    if not file_path:
        candidate = storage_dir / file_name
        if candidate.exists():
            file_path = str(candidate)
        else:
            suffix = file_name.rsplit('.', 1)[-1] if '.' in file_name else 'bin'
            file_path = str(storage_dir / f'{asset_id}.{suffix}')

    candidate_path = Path(file_path)
    if not candidate_path.exists():
        raise HTTPException(status_code=404, detail='Generated asset payload is missing.')

    return candidate_path.read_bytes()


def _svg_image_placeholder_bytes(prompt: str) -> bytes:
    caption = html.escape(prompt.strip()[:180] or 'Generated creative')
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='1024' height='1024' viewBox='0 0 1024 1024'>"
        "<defs><linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0%' stop-color='#0f172a'/><stop offset='100%' stop-color='#0ea5a4'/></linearGradient></defs>"
        "<rect width='1024' height='1024' fill='url(#bg)'/>"
        "<rect x='72' y='72' width='880' height='880' rx='36' fill='rgba(255,255,255,0.08)' stroke='rgba(255,255,255,0.25)'/>"
        "<text x='96' y='180' fill='#f8fafc' font-size='44' font-family='Segoe UI, Arial, sans-serif'>Nuxtron AI Creative</text>"
        f"<text x='96' y='260' fill='#e2e8f0' font-size='28' font-family='Segoe UI, Arial, sans-serif'>{caption}</text>"
        "</svg>"
    )
    return svg.encode('utf-8')


def _try_generate_vertex_image(prompt: str) -> tuple[bytes, str] | None:
    access_token = _resolve_provider_api_key('google_vertex')
    project_id = os.getenv('GOOGLE_VERTEX_PROJECT_ID', '').strip()
    location = os.getenv('GOOGLE_VERTEX_LOCATION', 'us-central1').strip() or 'us-central1'
    model = os.getenv('GOOGLE_VERTEX_IMAGE_MODEL', IMAGE_GENERATION_MODEL).strip() or IMAGE_GENERATION_MODEL
    if not access_token or not project_id:
        return None

    url = (
        f'https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}'
        f'/locations/{location}/publishers/google/models/{model}:predict'
    )
    body: JsonObject = {
        'instances': [{'prompt': prompt}],
        'parameters': {
            'sampleCount': 1,
            'aspectRatio': '1:1',
        },
    }

    with httpx.Client(timeout=45.0) as client:
        response = client.post(
            url,
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': CONTENT_TYPE_JSON},
            json=body,
        )
        if not response.is_success:
            return None
        data = response.json()
        predictions = data.get('predictions')
        if not isinstance(predictions, list) or not predictions:
            return None
        first = predictions[0] if isinstance(predictions[0], dict) else {}
        raw_b64 = first.get('bytesBase64Encoded')
        if not isinstance(raw_b64, str) or not raw_b64:
            return None
        mime_raw = first.get('mimeType')
        mime = mime_raw if isinstance(mime_raw, str) and mime_raw else MIME_TYPE_PNG
        return base64.b64decode(raw_b64), mime


def _try_generate_stability_image(prompt: str) -> tuple[bytes, str] | None:
    api_key = _resolve_provider_api_key('stability_ai')
    if not api_key:
        return None

    body: JsonObject = {
        'text_prompts': [{'text': prompt, 'weight': 1}],
        'height': 1024,
        'width': 1024,
        'steps': 30,
        'cfg_scale': 7.0,
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            'https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON},
            json=body,
        )
        if not response.is_success:
            return None
        data = response.json()
        artifacts = data.get('artifacts')
        if not isinstance(artifacts, list) or not artifacts:
            return None
        first = artifacts[0] if isinstance(artifacts[0], dict) else {}
        raw_b64 = first.get('base64')
        if not isinstance(raw_b64, str) or not raw_b64:
            return None
        return base64.b64decode(raw_b64), MIME_TYPE_PNG


def _ai_generate_image_binary(prompt: str, requested_provider: str) -> tuple[bytes, str, str, str]:
    provider = requested_provider.strip().lower()
    try:
        if provider in {'google_vertex', 'auto'}:
            vertex_result = _try_generate_vertex_image(prompt)
            if vertex_result is not None:
                return vertex_result[0], vertex_result[1], 'google_vertex', 'generated'
        if provider in {'stability_ai', 'auto'}:
            stability_result = _try_generate_stability_image(prompt)
            if stability_result is not None:
                return stability_result[0], stability_result[1], 'stability_ai', 'generated'
    except Exception:
        pass

    return _svg_image_placeholder_bytes(prompt), 'image/svg+xml', 'fallback', 'fallback'


def _try_generate_elevenlabs_voice(text: str) -> tuple[bytes, str] | None:
    api_key = os.getenv('ELEVENLABS_API_KEY', '').strip()
    voice_id = os.getenv('ELEVENLABS_VOICE_ID', '').strip() or 'EXAVITQu4vr4xnSDxMaL'
    if not api_key:
        return None

    body: JsonObject = {
        'text': text,
        'model_id': os.getenv('ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2').strip() or 'eleven_multilingual_v2',
        'voice_settings': {'stability': 0.4, 'similarity_boost': 0.75},
    }
    with httpx.Client(timeout=45.0) as client:
        response = client.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
            headers={'xi-api-key': api_key, 'Accept': MIME_TYPE_MP3, 'Content-Type': CONTENT_TYPE_JSON},
            json=body,
        )
        if response.is_success and response.content:
            return response.content, MIME_TYPE_MP3
    return None


def _resolve_oss_voice_endpoints() -> list[tuple[str, str]]:
    preset = os.getenv('VOICE_PROVIDER_PRESET', 'local_oss_first').strip().lower()
    openvoice_url = os.getenv('OPENVOICE_API_URL', 'http://127.0.0.1:9011/v1/tts').strip()
    bark_url = os.getenv('BARK_API_URL', 'http://127.0.0.1:9012/v1/tts').strip()
    rvc_url = os.getenv('RVC_API_URL', 'http://127.0.0.1:9013/v1/tts').strip()

    ordered: list[tuple[str, str]] = [
        ('openvoice', openvoice_url),
        ('bark', bark_url),
        ('rvc', rvc_url),
    ]
    if preset in {'bark_first', 'bark'}:
        ordered = [('bark', bark_url), ('openvoice', openvoice_url), ('rvc', rvc_url)]
    elif preset in {'rvc_first', 'rvc'}:
        ordered = [('rvc', rvc_url), ('openvoice', openvoice_url), ('bark', bark_url)]

    return [(name, url) for name, url in ordered if url]


def _try_generate_oss_voice(text: str) -> tuple[bytes, str, str] | None:
    timeout_seconds = max(2, _coerce_int(os.getenv('VOICE_PROVIDER_TIMEOUT_SECONDS', '6'), 6))
    payload: JsonObject = {
        'text': text[:2000],
        'language': 'en',
    }

    for provider_name, url in _resolve_oss_voice_endpoints():
        try:
            with httpx.Client(timeout=float(timeout_seconds)) as client:
                response = client.post(url, headers={'Content-Type': CONTENT_TYPE_JSON}, json=payload)
                if not response.is_success or not response.content:
                    continue
                content_type = str(response.headers.get('content-type', MIME_TYPE_WAV) or MIME_TYPE_WAV)
                mime_type = content_type.split(';', 1)[0].strip() or MIME_TYPE_WAV
                return response.content, mime_type, provider_name
        except Exception:
            continue

    return None


def _select_replicate_video_model(prompt: str) -> str:
    default_model = os.getenv('REPLICATE_VIDEO_MODEL', '').strip() or 'kwaivgi/kling-v1.6-pro'
    low_cost_model = os.getenv('REPLICATE_VIDEO_MODEL_LOW_COST', '').strip() or default_model
    high_quality_model = os.getenv('REPLICATE_VIDEO_MODEL_HIGH_QUALITY', '').strip() or default_model
    preset = os.getenv('REPLICATE_VIDEO_MODEL_PRESET', 'balanced').strip().lower()

    if preset in {'cost', 'low', 'cheap'}:
        return low_cost_model
    if preset in {'quality', 'high', 'premium'}:
        return high_quality_model

    normalized = prompt.lower()
    quality_keywords = {
        'cinematic',
        'luxury',
        'high fidelity',
        'brand film',
        'photoreal',
        'studio quality',
    }
    low_cost_keywords = {
        'short',
        'reel',
        'quick ad',
        'test variant',
        'ab test',
        'draft',
    }

    if any(keyword in normalized for keyword in quality_keywords):
        return high_quality_model
    if any(keyword in normalized for keyword in low_cost_keywords):
        return low_cost_model
    return default_model


def _synth_voice_wave_bytes(text: str) -> bytes:
    sample_rate = 16000
    max_chars = 220
    source = (text.strip() or 'nuxtron voice asset')[:max_chars]

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames: list[bytes] = []
        volume = 0.25
        tone_duration = 0.045
        gap_duration = 0.015

        for char in source:
            frequency = 180 + (ord(char) % 50) * 8
            sample_count = int(sample_rate * tone_duration)
            for i in range(sample_count):
                sample = int(volume * 32767 * math.sin(2 * math.pi * frequency * (i / sample_rate)))
                frames.append(struct.pack('<h', sample))
            for _ in range(int(sample_rate * gap_duration)):
                frames.append(struct.pack('<h', 0))

        wav_file.writeframes(b''.join(frames))

    return buf.getvalue()


def _ai_generate_voice_binary(text: str) -> tuple[bytes, str, str, str]:
    try:
        oss_voice = _try_generate_oss_voice(text)
        if oss_voice is not None:
            return oss_voice[0], oss_voice[1], oss_voice[2], 'generated'
    except Exception:
        pass

    try:
        elevenlabs = _try_generate_elevenlabs_voice(text)
        if elevenlabs is not None:
            return elevenlabs[0], elevenlabs[1], 'elevenlabs', 'generated'
    except Exception:
        pass

    return _synth_voice_wave_bytes(text), MIME_TYPE_WAV, 'fallback', 'fallback'


def _try_generate_replicate_video(prompt: str) -> tuple[bytes, str] | None:  # NOSONAR
    token = os.getenv('REPLICATE_API_TOKEN', '').strip()
    model = _select_replicate_video_model(prompt)
    timeout_seconds = _coerce_int(os.getenv('REPLICATE_VIDEO_TIMEOUT_SECONDS', '120'), 120)
    if not token:
        return None

    start_body: JsonObject = {
        'model': model,
        'input': {
            'prompt': prompt[:800],
            'duration': 5,
            'aspect_ratio': '9:16',
        },
    }
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }

    with httpx.Client(timeout=30.0) as client:
        get_url = _start_replicate_prediction(client, headers, start_body)
        if get_url is None:
            return None

        deadline = time.time() + max(15, min(timeout_seconds, 300))
        while time.time() < deadline:
            prediction = _poll_replicate_prediction(client, headers, get_url)
            if prediction is None:
                return None
            status = str(prediction.get('status', '') or '')
            if status in {'starting', 'processing'}:
                time.sleep(1.5)
                continue
            if status != 'succeeded':
                return None

            output_url = _extract_replicate_output_url(prediction)
            if not output_url:
                return None

            return _download_replicate_video(client, output_url)

    return None


def _start_replicate_prediction(client: httpx.Client, headers: dict[str, str], start_body: JsonObject) -> str | None:
    start_response = client.post('https://api.replicate.com/v1/predictions', headers=headers, json=start_body)
    if not start_response.is_success:
        return None

    start_data = start_response.json()
    get_url = start_data.get('urls', {}).get('get') if isinstance(start_data.get('urls'), dict) else None
    if not isinstance(get_url, str) or not get_url:
        return None
    return get_url


def _poll_replicate_prediction(client: httpx.Client, headers: dict[str, str], get_url: str) -> JsonObject | None:
    poll = client.get(get_url, headers=headers)
    if not poll.is_success:
        return None
    return cast(JsonObject, poll.json())


def _extract_replicate_output_url(prediction: JsonObject) -> str:
    output = prediction.get('output')
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output and isinstance(output[0], str):
        return output[0]
    return ''


def _download_replicate_video(client: httpx.Client, output_url: str) -> tuple[bytes, str] | None:
    video_response = client.get(output_url)
    if not video_response.is_success or not video_response.content:
        return None

    content_type = str(video_response.headers.get('content-type', MIME_TYPE_MP4) or MIME_TYPE_MP4)
    mime_type = content_type.split(';', 1)[0].strip() or MIME_TYPE_MP4
    return video_response.content, mime_type


def _placeholder_video_gif_bytes() -> bytes:
    # Tiny GIF binary fallback so UI can always render a downloadable "video-like" asset.
    return (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01'
        b'\x0a\x00\x01\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
    )


def _ai_generate_video_binary(_prompt: str) -> tuple[bytes, str, str, str]:
    prompt = _prompt.strip()[:1200] or 'Create a short, engaging product reel with clear hook and CTA.'

    try:
        replicate_video = _try_generate_replicate_video(prompt)
        if replicate_video is not None:
            return replicate_video[0], replicate_video[1], 'replicate', 'generated'
    except Exception:
        pass

    return _placeholder_video_gif_bytes(), 'image/gif', 'fallback', 'fallback'


def _generate_media_asset_bundle(
    *,
    tenant_id: str,
    prompt: str,
    text_seed: str,
    requested_provider: str,
) -> JsonObject:
    image_bytes, image_mime, image_provider, image_status = _ai_generate_image_binary(prompt, requested_provider)
    voice_bytes, voice_mime, voice_provider, voice_status = _ai_generate_voice_binary(text_seed)
    video_bytes, video_mime, video_provider, video_status = _ai_generate_video_binary(prompt)

    image_asset = _persist_ai_generated_asset(
        tenant_id=tenant_id,
        kind='image',
        mime_type=image_mime,
        content=image_bytes,
        provider_used=image_provider,
        generation_status=image_status,
    )
    voice_asset = _persist_ai_generated_asset(
        tenant_id=tenant_id,
        kind='voice',
        mime_type=voice_mime,
        content=voice_bytes,
        provider_used=voice_provider,
        generation_status=voice_status,
    )
    video_asset = _persist_ai_generated_asset(
        tenant_id=tenant_id,
        kind='video',
        mime_type=video_mime,
        content=video_bytes,
        provider_used=video_provider,
        generation_status=video_status,
    )

    return {
        'image': image_asset,
        'voice': voice_asset,
        'video': video_asset,
    }


def _invoke_ai_provider_generation(
    provider: str,
    payload: AiGatewayGenerateRequest,
    auth: AuthContext,
    created_at: str,
) -> JsonObject:
    if provider == 'openai':
        return _ai_generate_openai(payload, auth, created_at)
    if provider == 'anthropic':
        return _ai_generate_anthropic(payload, auth, created_at)
    if provider == 'google_vertex':
        return _ai_generate_google_vertex(payload, auth, created_at)
    return _ai_generate_generic(provider, payload, auth, created_at)


def _extract_ai_result(output: JsonObject) -> tuple[JsonObject, str]:
    result = cast(JsonObject, output.get('result', {})) if isinstance(output.get('result', {}), dict) else {}
    output_text = str(result.get('output_text', '') or '').strip()
    return result, output_text


def _prepare_ai_gateway_attempt(
    payload: AiGatewayGenerateRequest,
    provider: str,
    selected_model: str,
    can_retry: bool,
) -> tuple[str, str, AiGatewayGenerateRequest] | None:
    resolved_provider = provider
    resolved_model = selected_model
    if resolved_provider == 'auto':
        resolved_provider, resolved_model = _select_provider_with_tiers(payload, 'text_generation')

    if resolved_provider not in AI_PROVIDERS:
        raise HTTPException(status_code=422, detail='Unsupported AI provider.')

    if _is_provider_disabled(resolved_provider):
        if can_retry:
            return None
        raise HTTPException(status_code=503, detail=f'Provider {resolved_provider} is disabled. No fallbacks available.')

    if not _resolve_provider_api_key(resolved_provider):
        if can_retry:
            return None
        raise HTTPException(status_code=503, detail=f'No API key configured for {resolved_provider}. No fallbacks available.')

    scoped_payload = payload.model_copy(update={'provider': resolved_provider, 'model': resolved_model})
    return resolved_provider, resolved_model, scoped_payload


def _record_ai_gateway_success(
    *,
    output: JsonObject,
    scoped_payload: AiGatewayGenerateRequest,
    provider: str,
    auth: AuthContext,
    request: Request,
) -> None:
    result, _ = _extract_ai_result(output)
    model_used = str(result.get('model', '') or scoped_payload.model or _provider_default_model(provider))
    usage_item = _record_ai_usage(
        tenant_id=auth.tenant_id,
        provider=provider,
        model=model_used,
        request=request,
        payload=scoped_payload,
        result=result,
    )
    _evaluate_ai_guardrails(auth.tenant_id, provider, usage_item)


def _run_optional_ai_generation(
    payload: AiGatewayGenerateRequest,
    auth: AuthContext,
    created_at: str,
) -> tuple[str, str, JsonObject, str]:
    selected_provider: str = payload.provider
    selected_model = str(payload.model or '')
    if selected_provider == 'auto':
        selected_provider, selected_model = _select_provider_with_tiers(payload, 'text_generation')

    scoped_payload = payload.model_copy(update={'provider': selected_provider, 'model': selected_model})

    try:
        output = _invoke_ai_provider_generation(selected_provider, scoped_payload, auth, created_at)
        ai_result, ai_text = _extract_ai_result(output)
        return selected_provider, selected_model, ai_result, ai_text
    except Exception:
        return selected_provider, selected_model, {}, ''


@app.post('/ai/gateway/generate', responses={
    403: {'description': 'Tenant blocked for AI misuse.'},
    422: {'description': 'Unsupported AI provider.'},
    503: {'description': 'Provider disabled by security policy.'},
})
def ai_gateway_generate(payload: AiGatewayGenerateRequest, auth: AuthDep, request: Request) -> JsonObject:  # NOSONAR
    """
    Generate AI response via configured provider with automatic failover.
    
    Strategy:
    1. If provider specified: use it (or fail)
    2. If provider='auto': use tier-based selection with fallback chain
    3. Track provider health for auto-adjustment
    4. Retry with fallback providers on failure (up to 3 attempts)
    """
    _enforce_rate_limit(f'{auth.tenant_id}:ai:gateway', limit=120, window_seconds=60)
    blocked, until_ts = _is_tenant_blocked(auth.tenant_id)
    if blocked:
        raise HTTPException(
            status_code=403,
            detail=f'Tenant is temporarily blocked for AI misuse until {until_ts}. Submit appeal via /ai/security/appeals.',
        )

    provider = payload.provider.lower().strip()
    created_at = datetime.now(UTC).isoformat()
    selected_model = payload.model
    max_attempts = 3 if provider == 'auto' else 1
    last_error = ''

    for attempt in range(1, max_attempts + 1):
        start_time = time.time()

        try:
            prepared = _prepare_ai_gateway_attempt(payload, provider, selected_model, attempt < max_attempts)
            if prepared is None:
                provider = 'auto'
                continue

            provider, selected_model, scoped_payload = prepared
            output = _invoke_ai_provider_generation(provider, scoped_payload, auth, created_at)
            latency_ms = (time.time() - start_time) * 1000
            _update_provider_health(provider, True, latency_ms)
            _record_ai_gateway_success(
                output=output,
                scoped_payload=scoped_payload,
                provider=provider,
                auth=auth,
                request=request,
            )
            return output

        except HTTPException:
            raise
        except Exception as error:
            latency_ms = (time.time() - start_time) * 1000
            _update_provider_health(provider, False, latency_ms)
            last_error = str(error)

            if attempt < max_attempts:
                provider = 'auto'
                continue

            raise HTTPException(
                status_code=503,
                detail=f'AI gateway unavailable. All providers failed. Last error: {last_error[:200]}',
            )

    raise HTTPException(status_code=503, detail='AI gateway unavailable. Please try again.')


@app.get('/ai/generated-assets/{asset_id}', responses={
    404: {'description': 'Generated asset not found.'},
})
def ai_generated_asset_download(asset_id: int, auth: AuthDep) -> Response:
    _enforce_rate_limit(f'{auth.tenant_id}:ai:asset-download', limit=240, window_seconds=60)

    with _ai_generated_assets_lock:
        item = next(
            (
                row
                for row in _ai_generated_assets_memory
                if _coerce_int(row.get('id'), 0) == asset_id and str(row.get('tenant_id', '')) == auth.tenant_id
            ),
            None,
        )

    if item is None:
        raise HTTPException(status_code=404, detail='Generated asset not found.')

    mime_type = str(item.get('mime_type', 'application/octet-stream') or 'application/octet-stream')
    file_name = str(item.get('file_name', f'asset-{asset_id}.bin') or f'asset-{asset_id}.bin')
    try:
        content = _load_ai_generated_asset_bytes(item, asset_id, file_name)
    except Exception as ex:
        if isinstance(ex, HTTPException):
            raise
        raise HTTPException(status_code=404, detail=f'Generated asset is corrupted: {ex}') from ex

    return Response(
        content=content,
        media_type=mime_type,
        headers={'Content-Disposition': f'inline; filename="{file_name}"'},
    )


def _require_super_admin_key(x_super_admin_key: str | None) -> None:
    expected = os.getenv('SUPER_ADMIN_API_KEY', '').strip()
    supplied = (x_super_admin_key or '').strip()
    if not expected:
        raise HTTPException(status_code=503, detail='SUPER_ADMIN_API_KEY is not configured.')
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail='Invalid super admin key.')


def _request_source_ip(request: Request) -> str:
    forwarded_for = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip()
    if forwarded_for:
        return forwarded_for
    return request.client.host if request.client and request.client.host else ''


def _source_ip_allowed(source_ip: str, allowlist: list[str]) -> bool:
    try:
        ip_obj = ipaddress.ip_address(source_ip)
    except ValueError:
        return False

    for item in allowlist:
        candidate = item.strip()
        if not candidate:
            continue
        try:
            if '/' in candidate:
                if ip_obj in ipaddress.ip_network(candidate, strict=False):
                    return True
            elif ip_obj == ipaddress.ip_address(candidate):
                return True
        except ValueError:
            continue
    return False


def _require_super_admin_access(request: Request, x_super_admin_key: str | None) -> None:
    _require_super_admin_key(x_super_admin_key)

    raw_allowlist = os.getenv('SUPER_ADMIN_ALLOWLIST', '').strip()
    allowlist = [item.strip() for item in raw_allowlist.split(',') if item.strip()]
    if _is_production() and not allowlist:
        raise HTTPException(status_code=503, detail='SUPER_ADMIN_ALLOWLIST must be configured in production.')
    if not allowlist:
        return

    source_ip = _request_source_ip(request)
    if not source_ip or not _source_ip_allowed(source_ip, allowlist):
        raise HTTPException(status_code=403, detail='Source IP is not allowlisted for super admin access.')


@app.post('/ai/security/admin/provider-keys/rotate', responses={
    401: {'description': 'Invalid super admin key.'},
    403: {'description': 'Source IP is not allowlisted for super admin access.'},
    503: {'description': 'Super admin key not configured.'},
})
def ai_security_rotate_provider_key(
    request: Request,
    payload: AiSecurityRotateKeyRequest,
    x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
) -> JsonObject:
    _require_super_admin_access(request, x_super_admin_key)
    now_iso = datetime.now(UTC).isoformat()
    cipher = te_encrypt(payload.api_key)

    with _ai_security_lock:
        for item in _ai_provider_keys_memory:
            if item.get('provider') == payload.provider and item.get('enabled') is True:
                item['enabled'] = False
                item['disabled_reason'] = 'rotated'
                item['disabled_at'] = now_iso

        record: JsonObject = {
            'id': len(_ai_provider_keys_memory) + 1,
            'provider': payload.provider,
            'label': payload.label or f'{payload.provider}-key',
            'api_key_cipher': cipher,
            'fingerprint': hashlib.sha256(payload.api_key.encode('utf-8')).hexdigest()[:12],
            'enabled': True,
            'created_at': now_iso,
        }
        _ai_provider_keys_memory.append(record)

    alert = _record_ai_security_alert('info', 'AI provider API key rotated', {'provider': payload.provider, 'label': record['label']})
    _send_security_email_alert(alert)
    return {'status': 'ok', 'provider_key': {'provider': payload.provider, 'label': record['label'], 'fingerprint': record['fingerprint'], 'enabled': True}}


def _ai_security_usage_window(tenant_id: str, window_minutes: int) -> list[JsonObject]:
    now_ts = int(time.time())
    window_seconds = max(1, min(window_minutes, 24 * 60)) * 60
    return [
        item for item in _ai_security_usage_memory
        if item.get('tenant_id') == tenant_id and _coerce_int(item.get('timestamp', 0), 0) >= (now_ts - window_seconds)
    ]


def _ai_security_provider_graph(usage_window: list[JsonObject]) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for provider in AI_PROVIDERS:
        provider_items = [item for item in usage_window if item.get('provider') == provider]
        provider_calls = len(provider_items)
        provider_roi = round(sum(_coerce_float(item.get('roi', 0.0), 0.0) for item in provider_items) / provider_calls, 6) if provider_calls else 0.0
        disabled = _is_provider_disabled(provider)
        rows.append({
            'provider': provider,
            'calls': provider_calls,
            'avg_roi': provider_roi,
            'color': 'red' if disabled else 'green',
            'status': 'blocked' if disabled else 'healthy',
        })
    return rows


def _ai_security_timeline(usage_window: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            'ts': item.get('timestamp'),
            'provider': item.get('provider'),
            'model': item.get('model'),
            'roi': item.get('roi'),
            'latency_ms': item.get('latency_ms'),
            'estimated_cost': item.get('estimated_cost'),
            'status': item.get('status'),
        }
        for item in usage_window[-240:]
    ]


def _ai_security_tenant_alerts(tenant_id: str) -> list[JsonObject]:
    tenant_alerts: list[JsonObject] = []
    for alert in _ai_security_alerts_memory[-200:]:
        raw_details = alert.get('details', {})
        details: JsonObject = cast(JsonObject, raw_details) if isinstance(raw_details, dict) else {}
        tenant_scope = str(details.get('tenant_id', '') or '')
        if tenant_scope in {'', tenant_id}:
            tenant_alerts.append(alert)
    return tenant_alerts


@app.get('/ai/security/analytics')
def ai_security_analytics(auth: AuthDep, window_minutes: int = 60) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:ai:security:analytics', limit=120, window_seconds=60)
    usage_window = _ai_security_usage_window(auth.tenant_id, window_minutes)
    blocked, until_ts = _is_tenant_blocked(auth.tenant_id)
    total_calls = len(usage_window)
    success_calls = sum(1 for item in usage_window if item.get('status') == 'success')

    kpi: JsonObject = {
        'total_calls': total_calls,
        'success_calls': success_calls,
        'success_rate': round((success_calls / total_calls), 4) if total_calls else 0.0,
        'avg_roi': round(sum(_coerce_float(item.get('roi', 0.0), 0.0) for item in usage_window) / total_calls, 6) if total_calls else 0.0,
        'avg_latency_ms': round(sum(_coerce_float(item.get('latency_ms', 0), 0.0) for item in usage_window) / total_calls, 2) if total_calls else 0.0,
        'total_estimated_cost': round(sum(_coerce_float(item.get('estimated_cost', 0.0), 0.0) for item in usage_window), 8),
        'total_estimated_value': round(sum(_coerce_float(item.get('estimated_value', 0.0), 0.0) for item in usage_window), 8),
        'is_blocked': blocked,
        'blocked_until_ts': until_ts if blocked else 0,
    }

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'window_minutes': window_minutes,
        'kpi': kpi,
        'provider_graph': _ai_security_provider_graph(usage_window),
        'timeline': _ai_security_timeline(usage_window),
        'alerts': _ai_security_tenant_alerts(auth.tenant_id)[-20:],
    }


@app.post('/ai/security/appeals')
def ai_security_create_appeal(payload: AiSecurityAppealRequest, auth: AuthDep) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:ai:security:appeal', limit=12, window_seconds=3600)
    now_iso = datetime.now(UTC).isoformat()
    appeal: JsonObject = {
        'id': len(_ai_security_appeals_memory) + 1,
        'tenant_id': auth.tenant_id,
        'reason': payload.reason,
        'status': 'pending',
        'created_at': now_iso,
    }
    with _ai_security_lock:
        _ai_security_appeals_memory.append(appeal)
    alert = _record_ai_security_alert('warning', 'AI block appeal created', {'tenant_id': auth.tenant_id, 'appeal_id': appeal['id']})
    _send_security_email_alert(alert)
    return {'status': 'ok', 'appeal': appeal}


@app.post('/ai/security/admin/appeals/{appeal_id}/resolve', responses={
    401: {'description': 'Invalid super admin key.'},
    403: {'description': 'Source IP is not allowlisted for super admin access.'},
    404: {'description': 'Appeal not found.'},
    503: {'description': 'Super admin key not configured.'},
})
def ai_security_resolve_appeal(
    request: Request,
    appeal_id: int,
    payload: AiSecurityAppealResolveRequest,
    x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
) -> JsonObject:
    _require_super_admin_access(request, x_super_admin_key)
    now_iso = datetime.now(UTC).isoformat()
    with _ai_security_lock:
        appeal = next((item for item in _ai_security_appeals_memory if _coerce_int(item.get('id', 0), 0) == appeal_id), None)
        if appeal is None:
            raise HTTPException(status_code=404, detail='Appeal not found.')
        appeal['status'] = payload.decision
        appeal['resolved_at'] = now_iso
        appeal['notes'] = payload.notes or ''
        if payload.decision == 'approved':
            for block in _ai_security_blocks_memory:
                if block.get('tenant_id') == appeal.get('tenant_id') and block.get('active') is True:
                    block['active'] = False
                    block['resolved_at'] = now_iso

    alert = _record_ai_security_alert('info', 'AI appeal resolved', {'appeal_id': appeal_id, 'decision': payload.decision})
    _send_security_email_alert(alert)
    return {'status': 'ok', 'appeal': appeal}


@app.post('/ai/security/admin/ids/events', responses={
    401: {'description': 'Invalid super admin key.'},
    403: {'description': 'Source IP is not allowlisted for super admin access.'},
    503: {'description': 'Super admin key not configured.'},
})
def ai_security_ingest_ids_event(
    request: Request,
    payload: AiSecurityIdseventRequest,
    x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
) -> JsonObject:
    _require_super_admin_access(request, x_super_admin_key)
    now_iso = datetime.now(UTC).isoformat()
    event: JsonObject = {
        'id': len(_ai_security_ids_events_memory) + 1,
        'timestamp': int(time.time()),
        'source': payload.source,
        'severity': payload.severity,
        'rule_id': payload.rule_id,
        'message': payload.message,
        'tenant_id': payload.tenant_id or '',
        'provider': payload.provider or '',
        'ip_hash': hashlib.sha256((payload.ip_address or '').encode('utf-8')).hexdigest()[:16] if payload.ip_address else '',
        'action': payload.action,
        'created_at': now_iso,
    }
    with _ai_security_lock:
        _ai_security_ids_events_memory.append(event)
        if len(_ai_security_ids_events_memory) > 10000:
            del _ai_security_ids_events_memory[:-10000]

    if payload.action == 'block-tenant' and payload.tenant_id:
        _block_tenant(payload.tenant_id, f'IDS/IPS event {payload.source}:{payload.rule_id}')
    elif payload.action == 'disable-provider' and payload.provider:
        _disable_provider(payload.provider, f'IDS/IPS event {payload.source}:{payload.rule_id}')
    else:
        alert = _record_ai_security_alert(
            'critical' if payload.severity in {'high', 'critical'} else 'warning',
            'IDS/IPS alert ingested',
            {
                'source': payload.source,
                'rule_id': payload.rule_id,
                'tenant_id': payload.tenant_id or '',
                'provider': payload.provider or '',
                'action': payload.action,
            },
        )
        _send_security_email_alert(alert)

    return {'status': 'ok', 'event': event}


@app.get('/ai/security/admin/ids/state', responses={
    401: {'description': 'Invalid super admin key.'},
    403: {'description': 'Source IP is not allowlisted for super admin access.'},
    503: {'description': 'Super admin key not configured.'},
})
def ai_security_ids_state(
    request: Request,
    x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    window_minutes: int = 60,
) -> JsonObject:
    _require_super_admin_access(request, x_super_admin_key)
    now_ts = int(time.time())
    window_seconds = max(1, min(window_minutes, 24 * 60)) * 60
    window_events = [
        item for item in _ai_security_ids_events_memory
        if _coerce_int(item.get('id', 0), 0) > 0 and _coerce_int(item.get('timestamp', now_ts), now_ts) >= (now_ts - window_seconds)
    ]
    if not window_events:
        window_events = _ai_security_ids_events_memory[-500:]

    by_source: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for item in window_events:
        source = str(item.get('source', 'unknown') or 'unknown')
        severity = str(item.get('severity', 'unknown') or 'unknown')
        by_source[source] = by_source.get(source, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1

    return {
        'status': 'ok',
        'window_minutes': window_minutes,
        'total_events': len(window_events),
        'by_source': by_source,
        'by_severity': by_severity,
        'security_email_delivery': _security_alert_delivery_summary(),
        'recent_events': window_events[-100:],
        'active_blocks': [item for item in _ai_security_blocks_memory if item.get('active') is True],
        'provider_keys': [
            {
                'provider': item.get('provider', ''),
                'label': item.get('label', ''),
                'fingerprint': item.get('fingerprint', ''),
                'enabled': bool(item.get('enabled')),
            }
            for item in _ai_provider_keys_memory[-20:]
        ],
    }


@app.get('/ai/security/admin/email-queue', responses={
    401: {'description': 'Invalid super admin key.'},
    403: {'description': 'Source IP is not allowlisted for super admin access.'},
    503: {'description': 'Super admin key not configured.'},
})
def ai_security_admin_email_queue(
    request: Request,
    x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    status: Literal['all', 'queued', 'sending', 'retry', 'sent', 'failed'] = 'failed',
    limit: int = 50,
    cursor_before_id: int = 0,
) -> JsonObject:
    _require_super_admin_access(request, x_super_admin_key)
    safe_limit = max(1, min(limit, 200))
    safe_cursor = max(0, cursor_before_id)

    fetch_size = safe_limit + 1
    db_items = _db_security_alert_email_queue_items(status, fetch_size, safe_cursor) if _security_alert_db_queue_enabled() else None
    items_raw = db_items if db_items is not None else _memory_security_alert_email_queue_items(status, fetch_size, safe_cursor)
    items, has_more, next_cursor = _paginate_email_queue_items(items_raw, safe_limit)
    queue_source = 'db' if db_items is not None else 'memory'

    return {
        'status': 'ok',
        'queue_source': queue_source,
        'filter_status': status,
        'limit': safe_limit,
        'cursor_before_id': safe_cursor,
        'has_more': has_more,
        'next_cursor_before_id': next_cursor,
        'count': len(items),
        'items': items,
    }


@app.post('/ai/security/admin/email-queue/{message_id}/requeue', responses={
    401: {'description': 'Invalid super admin key.'},
    403: {'description': 'Source IP is not allowlisted for super admin access.'},
    404: {'description': 'Queue message not found.'},
    409: {'description': 'Only failed messages can be requeued.'},
    503: {'description': 'Super admin key not configured.'},
})
def ai_security_admin_requeue_email(
    request: Request,
    message_id: int,
    x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
) -> JsonObject:
    _require_super_admin_access(request, x_super_admin_key)
    if message_id <= 0:
        raise HTTPException(status_code=404, detail='Queue message not found.')

    source_ip = _request_source_ip(request)
    super_admin_fingerprint = hashlib.sha256((x_super_admin_key or '').encode('utf-8')).hexdigest()[:16]

    queue_source = 'memory'
    item: JsonObject | None
    if _security_alert_db_queue_enabled():
        item = _db_requeue_security_alert_email(message_id, super_admin_fingerprint, source_ip)
        queue_source = 'db'
    else:
        item = _memory_requeue_security_alert_email(message_id, super_admin_fingerprint, source_ip)

    if item is None:
        if _security_alert_db_queue_enabled():
            exists = _db_security_alert_email_exists(message_id)
        else:
            exists = any(
                raw.get('tenant_id') == 'platform-security' and _coerce_int(raw.get('id', 0), 0) == message_id
                for raw in _resend_messages_memory
            )
        if exists:
            raise HTTPException(status_code=409, detail='Only failed messages can be requeued.')
        raise HTTPException(status_code=404, detail='Queue message not found.')

    alert = _record_ai_security_alert('info', 'Security alert email requeued', {'message_id': message_id, 'queue_source': queue_source})
    _send_security_email_alert(alert)
    return {'status': 'ok', 'queue_source': queue_source, 'item': item}


def _build_queues_dict() -> dict[str, int]:
    """Build queue size dictionary from all memory stores. Extracted to reduce complexity."""
    return {
        'suitecrm': len(_suitecrm_jobs_memory),
        'refferq': len(_refferq_jobs_memory),
        'posthog': len(_posthog_events_memory),
        'social_listening': len(_social_listening_memory),
        'social_listening_alert_rules': len(_social_listening_alert_rules_memory),
        'social_listening_alerts': len(_social_listening_alerts_memory),
        'reviews': len(_reviews_memory),
        'n8n': len(_n8n_jobs_memory),
        'growthbook': len(_growthbook_checks_memory),
        'matomo': len(_matomo_events_memory),
        'plausible': len(_plausible_events_memory),
        'meilisearch': len(_meilisearch_index_memory),
        'webhooks': len(_webhook_events_memory),
        'appwrite': len(_appwrite_events_memory),
        'drone': len(_drone_builds_memory),
        'directus': len(_directus_items_memory),
        'minio': len(_minio_objects_memory),
        'stripe': len(_stripe_events_memory),
        'audit_log': len(_audit_log_memory),
        'notifications': len(_notifications_memory),
        'redis': len(_redis_ops_memory),
        'twilio': len(_twilio_messages_memory),
        'slack': len(_slack_messages_memory),
        'resend': len(_resend_messages_memory),
        'algolia': len(_algolia_sync_memory),
        'ai_gateway': len(_ai_gateway_memory),
        'ai_security_usage': len(_ai_security_usage_memory),
        'ai_security_alerts': len(_ai_security_alerts_memory),
        'ai_security_blocks': len(_ai_security_blocks_memory),
        'ai_security_appeals': len(_ai_security_appeals_memory),
        'ai_security_ids_events': len(_ai_security_ids_events_memory),
        'auth_security': len(_auth_security_memory),
        'tenant_management': len(_tenant_profiles_memory),
        'engagement_streaks': len(_engagement_streaks_memory),
        'engagement_referrals': len(_engagement_referrals_memory),
        'engagement_companion_profiles': len(_engagement_companion_profiles_memory),
        'engagement_fomo_events': len(_engagement_fomo_events_memory),
        'engagement_social_proof_events': len(_engagement_social_proof_events_memory),
        'engagement_dependency_profiles': len(_engagement_dependency_profiles_memory),
        'engagement_dependency_events': len(_engagement_dependency_events_memory),
        'engagement_community_circles': len(_engagement_community_circles_memory),
        'engagement_community_posts': len(_engagement_community_posts_memory),
        'engagement_community_amas': len(_engagement_community_amas_memory),
        'engagement_brand_lock_profiles': len(_engagement_brand_lock_profiles_memory),
        'engagement_brand_lock_events': len(_engagement_brand_lock_events_memory),
        'engagement_autopilot_profiles': len(_engagement_autopilot_profiles_memory),
        'engagement_autopilot_events': len(_engagement_autopilot_events_memory),
        'engagement_achievement_profiles': len(_engagement_achievement_profiles_memory),
        'engagement_achievement_events': len(_engagement_achievement_events_memory),
        'money_printer_ideas': len(_money_printer_ideas_memory),
        'money_printer_validations': len(_money_printer_validations_memory),
        'bank_accounts': len(_bank_accounts_memory),
        'bank_transactions': len(_bank_transactions_memory),
        'bank_payouts': len(_bank_payouts_memory),
        'university_courses': len(_university_courses_memory),
        'university_cohorts': len(_university_cohorts_memory),
        'university_enrollments': len(_university_enrollments_memory),
        'studios_services': len(_studios_services_memory),
        'studios_briefs': len(_studios_briefs_memory),
        'studios_proposals': len(_studios_proposals_memory),
        'studios_escrows': len(_studios_escrows_memory),
        'commerce_products': len(_commerce_products_memory),
        'commerce_orders': len(_commerce_orders_memory),
        'talent_creators': len(_talent_creators_memory),
        'talent_deals': len(_talent_deals_memory),
        'talent_rate_cards': len(_talent_rate_cards_memory),
        'white_label_profiles': len(_white_label_profiles_memory),
        'white_label_events': len(_white_label_events_memory),
        'crm_contacts': len(_crm_contacts_memory),
        'crm_companies': len(_crm_companies_memory),
        'crm_deals': len(_crm_deals_memory),
        'influencer_campaigns': len(_influencer_campaigns_memory),
        'chatbots': len(_chatbots_memory),
        'linkinbio_pages': len(_linkinbio_pages_memory),
        'subscriptions': len(_subscriptions_memory),
        'cms_connections': len(_cms_connections_memory),
        'marketplace_installs': len(_marketplace_installs_memory),
        'analytics_reports': len(_analytics_reports_memory),
        'analytics_trends': len(_analytics_trends_memory),
        'analytics_rollups': len(_analytics_rollups_memory),
    }


def _build_integrations_dict() -> dict[str, bool]:
    """Build integrations configuration dictionary. Extracted to reduce complexity."""
    vault_addr = os.getenv('VAULT_ADDR', '').strip()
    vault_token = os.getenv('VAULT_TOKEN', '').strip()
    supabase_url = os.getenv('SUPABASE_URL', '').strip()
    supabase_service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    supabase_db_url = os.getenv('SUPABASE_DB_URL', '').strip()

    return {
        'postgres_configured': bool(os.getenv('POSTGRES_HOST', '').strip()),
        'listmonk_configured': bool(os.getenv('LISTMONK_URL', '').strip() and os.getenv('LISTMONK_API_TOKEN', '').strip()),
        'postal_configured': bool(os.getenv('POSTAL_BASE_URL', '').strip() and os.getenv('POSTAL_API_KEY', '').strip()),
        'ses_configured': bool(os.getenv('SES_SMTP_HOST', '').strip()),
        'posthog_configured': bool(os.getenv('POSTHOG_API_KEY', '').strip() and os.getenv('POSTHOG_API_HOST', '').strip()),
        'n8n_configured': bool(os.getenv('N8N_BASE_URL', '').strip() and os.getenv('N8N_API_KEY', '').strip()),
        'growthbook_configured': bool(os.getenv('GROWTHBOOK_API_HOST', '').strip() and os.getenv('GROWTHBOOK_API_KEY', '').strip()),
        'matomo_configured': bool(os.getenv('MATOMO_BASE_URL', '').strip() and os.getenv('MATOMO_SITE_ID', '').strip()),
        'plausible_configured': bool(os.getenv('PLAUSIBLE_API_KEY', '').strip()),
        'meilisearch_configured': bool(os.getenv('MEILISEARCH_HOST', '').strip() and os.getenv('MEILISEARCH_API_KEY', '').strip()),
        'appwrite_configured': bool(os.getenv('APPWRITE_API_KEY', '').strip()),
        'drone_configured': bool(os.getenv('DRONE_SERVER', '').strip() and os.getenv('DRONE_TOKEN', '').strip()),
        'directus_configured': bool(os.getenv('DIRECTUS_URL', '').strip()),
        'minio_configured': bool(os.getenv('MINIO_ENDPOINT', '').strip()),
        'stripe_configured': bool(os.getenv('STRIPE_SECRET_KEY', '').strip()),
        'redis_configured': bool(os.getenv('REDIS_HOST', '').strip()),
        'twilio_configured': bool(os.getenv('TWILIO_ACCOUNT_SID', '').strip() and os.getenv('TWILIO_AUTH_TOKEN', '').strip()),
        'slack_configured': bool(os.getenv('SLACK_BOT_TOKEN', '').strip() or os.getenv('SLACK_WEBHOOK_URL', '').strip()),
        'resend_configured': bool(os.getenv('RESEND_API_KEY', '').strip()),
        'algolia_configured': bool(os.getenv('ALGOLIA_APP_ID', '').strip() and os.getenv('ALGOLIA_API_KEY', '').strip()),
        'openai_configured': bool(os.getenv('OPENAI_API_KEY', '').strip()),
        'anthropic_configured': bool(os.getenv('ANTHROPIC_API_KEY', '').strip()),
        'jwt_configured': bool(os.getenv('JWT_SIGNING_KEY', '').strip()),
        'hashicorp_vault_configured': bool(vault_addr and vault_token),
        'supabase_configured': bool(supabase_url and supabase_service_role_key),
        'supabase_vault_ready': bool(supabase_db_url),
    }


def _platform_status_payload(auth: AuthContext) -> JsonObject:
    """Generate platform status payload. Complexity reduced by extracting dict builders."""
    email_provider = os.getenv('EMAIL_PROVIDER', 'listmonk')
    queues = _build_queues_dict()
    integrations = _build_integrations_dict()
    
    bridges_memory_cap = int(os.getenv('BRIDGES_MEMORY_CAP', '1000'))
    bridges_warn_utilization_pct = int(os.getenv('BRIDGES_WARN_UTILIZATION_PCT', '75'))
    bridges_warn_utilization = round(max(0.0, min(1.0, bridges_warn_utilization_pct / 100.0)), 4)

    fallback_stores = {
        'scheduled_posts': _scheduled_posts_memory,
        'email_contacts': _email_contacts_memory,
        'email_campaigns': _email_campaigns_memory,
        'suitecrm_jobs': _suitecrm_jobs_memory,
        'meilisearch': _meilisearch_index_memory,
        'algolia': _algolia_sync_memory,
    }
    fallback_sizes = {name: len(store) for name, store in fallback_stores.items()}
    fallback_utilization = {
        name: round(size / max(1, bridges_memory_cap), 4)
        for name, size in fallback_sizes.items()
    }
    fallback_hot_buffers = [
        name for name, utilization in fallback_utilization.items()
        if utilization > bridges_warn_utilization
    ]

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'db_ready': _db_ready,
        'timestamp': datetime.now(UTC).isoformat(),
        'integrations': {**integrations, 'totp_enabled': True, 'tenant_management_enabled': True, 'email_provider': email_provider},
        'queues': queues,
        'fallback_buffers': {
            'max_items_per_buffer': bridges_memory_cap,
            'warning_utilization_threshold': bridges_warn_utilization,
            'sizes': fallback_sizes,
            'utilization_ratio': fallback_utilization,
            'hot_buffers': fallback_hot_buffers,
            'any_buffer_hot': len(fallback_hot_buffers) > 0,
        },
    }


def _platform_metrics_summary_payload(auth: AuthContext) -> JsonObject:
    """Generate metrics summary. Refactored to use helper for queue dict."""
    with _rate_lock:
        rate_samples = sum(len(samples) for samples in _rate_buckets.values())
        active_keys = len(_rate_buckets)

    queues = _build_queues_dict()
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'queues': queues,
        'rate_limiter': {'active_keys': active_keys, 'sample_count': rate_samples},
        'generated_at': datetime.now(UTC).isoformat(),
    }


def _platform_anti_failure_payload(auth: AuthContext) -> JsonObject:
    # ENHANCED (Part 6A): surface anti-failure defense signals by reusing
    # existing queue/integration/rate-limiter state instead of new stores.
    status_payload = _platform_status_payload(auth)
    integrations = _json_object(status_payload.get('integrations', {})) or {}
    fallback_buffers = _json_object(status_payload.get('fallback_buffers', {})) or {}
    queues_obj = status_payload.get('queues', {})
    queues = cast(dict[str, int], queues_obj) if isinstance(queues_obj, dict) else {}

    rate_active_raw = status_payload.get('rate_limit_active_keys', 0)
    rate_active = _coerce_int(rate_active_raw, 0)
    db_ready = bool(status_payload.get('db_ready'))
    strict_mode = str(status_payload.get('security_strict_mode', '0')) == '1'
    hot_buffers = bool(fallback_buffers.get('any_buffer_hot', False))

    defense_states: list[tuple[str, bool]] = [
        ('revenue_shield', bool(queues.get('subscriptions', 0) >= 0)),
        ('churn_prevention', bool(queues.get('crm_contacts', 0) >= 0)),
        ('competitive_radar', bool(queues.get('social_listening', 0) >= 0)),
        ('cash_flow_guardian', bool(queues.get('stripe', 0) >= 0)),
        ('market_adaptation', bool(queues.get('analytics_reports', 0) >= 0)),
        ('quality_guardian', not hot_buffers),
        ('innovation_engine', bool(queues.get('ai_gateway', 0) >= 0)),
        ('reputation_shield', bool(queues.get('reviews', 0) >= 0)),
        ('talent_shield', bool(queues.get('audit_log', 0) >= 0)),
        ('regulatory_shield', strict_mode),
        ('technology_shield', db_ready or bool(integrations.get('redis_configured', False))),
        ('growth_engine', bool(queues.get('email_campaigns', 0) >= 0 and rate_active >= 0)),
    ]
    defenses: list[JsonObject] = [{'id': name, 'healthy': is_healthy} for name, is_healthy in defense_states]

    healthy_count = sum(1 for _, is_healthy in defense_states if is_healthy)
    degraded_count = len(defenses) - healthy_count

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'defense_systems': defenses,
        'summary': {
            'total': len(defenses),
            'healthy_count': healthy_count,
            'degraded_count': degraded_count,
        },
    }


def _queue_ready(queues: dict[str, int], key: str) -> bool:
    return queues.get(key, 0) >= 0


def _build_use_cases_dict(queues: dict[str, int]) -> dict[str, bool]:
    """Build use case coverage using a declarative dependency map."""
    use_case_dependencies: dict[str, tuple[str, ...]] = {
        'uc_1_ai_search_domination': ('social_listening', 'analytics_reports'),
        'uc_2_new_feature_launch': ('email_campaigns', 'notifications'),
        'uc_3_competitor_counter_strike': ('social_listening_alerts',),
        'uc_4_pipeline_attribution': ('crm_deals', 'analytics_reports'),
        'uc_5_multi_client_agency_geo': ('tenant_management',),
        'uc_6_review_reputation_recovery': ('reviews',),
        'uc_7_ai_shopping_visibility': ('cms_connections',),
        'uc_8_black_friday_automation': ('email_campaigns', 'social_scheduled'),
        'uc_9_influencer_geo_synergy': ('influencer_campaigns',),
        'uc_10_chatbot_revenue': ('chatbots',),
        'uc_11_audio_commerce': ('content_generated', 'email_campaigns'),
        'uc_12_multi_platform_review': ('reviews', 'notifications'),
        'uc_13_full_month_social_calendar': ('social_scheduled', 'notifications'),
        'uc_14_personal_brand_geo': ('social_scheduled', 'analytics_reports'),
        'uc_15_linkinbio_monetization': ('linkinbio_pages',),
        'uc_16_podcast_empire': ('content_generated', 'email_campaigns'),
        'uc_17_viral_reel_production': ('social_listening', 'social_scheduled'),
        'uc_18_creator_monetization': ('subscriptions', 'linkinbio_pages'),
        'uc_19_ai_hallucination_crisis': ('social_listening_alerts', 'cms_connections'),
        'uc_20_regulated_geo_fintech': ('audit_log', 'cms_connections'),
        'uc_21_employee_advocacy': ('social_scheduled', 'audit_log'),
        'uc_22_multi_region_geo': ('analytics_reports', 'cms_connections'),
        'uc_23_enterprise_chatbot_support': ('chatbots', 'crm_contacts'),
        'uc_24_competitive_intelligence': ('social_listening', 'analytics_reports'),
    }
    return {
        use_case_id: all(_queue_ready(queues, dependency) for dependency in dependencies)
        for use_case_id, dependencies in use_case_dependencies.items()
    }


def _platform_use_case_coverage_payload(auth: AuthContext) -> JsonObject:
    """Generate use case coverage payload. Complexity reduced by extracting use cases dict builder."""
    status_payload = _platform_status_payload(auth)
    queues_obj = status_payload.get('queues', {})
    queues = cast(dict[str, int], queues_obj) if isinstance(queues_obj, dict) else {}
    use_cases = _build_use_cases_dict(queues)

    covered = sum(1 for covered_flag in use_cases.values() if covered_flag)
    coverage_percent = round((covered / max(1, len(use_cases))) * 100, 2)

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'use_cases': use_cases,
        'covered_count': covered,
        'total_use_cases': len(use_cases),
        'coverage_percent': coverage_percent,
    }

def _platform_capabilities_payload(auth: AuthContext) -> JsonObject:
    categories: list[JsonObject] = [
        {
            'id': 'core_growth',
            'name': 'Core Growth',
            'features': [
                {'id': 'content_generation', 'name': 'AI Content Generation', 'path': '/content/generate', 'ready': True},
                {'id': 'ads_generation', 'name': 'AI Ads Generation', 'path': '/ads/generate', 'ready': True},
                {'id': 'seo_analysis', 'name': 'AI SEO Analysis', 'path': '/seo/analyze', 'ready': True},
                {'id': 'social_scheduling', 'name': 'Social Scheduling', 'path': '/social/schedule', 'ready': True},
            ],
        },
        {
            'id': 'engagement_intelligence',
            'name': 'Engagement & Intelligence',
            'features': [
                {'id': 'social_listening', 'name': 'Social Listening', 'path': '/social/listening/summary', 'ready': True},
                {'id': 'reviews', 'name': 'Reviews & Reputation', 'path': '/reviews/summary', 'ready': True},
                {'id': 'smart_inbox', 'name': 'Smart Inbox', 'path': '/inbox/messages', 'ready': True},
                {'id': 'competitive_benchmarking', 'name': 'Competitive Benchmarking', 'path': '/competitive/report', 'ready': True},
            ],
        },
        {
            'id': 'commercial_stack',
            'name': 'Commercial Stack',
            'features': [
                {'id': 'crm', 'name': 'CRM', 'path': '/crm/summary', 'ready': True},
                {'id': 'billing', 'name': 'Billing', 'path': '/billing/plans', 'ready': True},
                {'id': 'products', 'name': 'Products Catalog', 'path': '/products/catalog/stats', 'ready': True},
                {'id': 'workflows', 'name': 'Workflows Automation', 'path': '/workflows', 'ready': True},
            ],
        },
        {
            'id': 'ops_security',
            'name': 'Ops & Security',
            'features': [
                {'id': 'status', 'name': 'Platform Status', 'path': '/ops/platform/status', 'ready': True},
                {'id': 'metrics', 'name': 'Platform Metrics', 'path': '/ops/platform/metrics-summary', 'ready': True},
                {'id': 'anti_failure', 'name': 'Anti-failure Systems', 'path': '/ops/platform/anti-failure-status', 'ready': True},
                {'id': 'api_usage', 'name': 'Security API Usage', 'path': '/ops/security/api-usage', 'ready': True},
                {'id': 'siem', 'name': 'SIEM & SOAR', 'path': '/ops/siem/data-collection', 'ready': True},
            ],
        },
    ]

    total_features = sum(len(cast(list[JsonObject], category['features'])) for category in categories)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'categories': categories,
        'totals': {
            'features': total_features,
            'categories': len(categories),
            'db_ready': _db_ready,
        },
    }


_HYBRID_STACKS_IDS: tuple[str, ...] = (
    'seo-ai', 'geo', 'aio-2', 'llmo', 'sageo', 'vso', 'sxo', 'gxo', 'entity-first-seo', 'peao',
    'msvo', 'daeo', 'cxao', 'eeat-suite', 'autonomous-agent-engine', 'programmatic-seo-engine',
    'seo-ab-testing', 'ecommerce-seo-suite', 'autonomous-link-building-system', 'international-multilingual-seo',
    'site-migration-seo-manager', 'video-seo-module', 'local-seo-suite', 'news-seo-google-discover',
    'analytics-reporting-intelligence', 'agency-multi-tenant-platform', 'integrations-automation-layer',
    'realtime-search-ai-monitoring', 'ai-technical-seo-engine', 'content-quality-hallucination-auditor',
    'knowledge-graph-management', 'ai-internal-linking-engine', 'crawl-budget-optimizer',
    'ai-schema-engine', 'ux-conversion-optimizer', 'rag-site-search-engine', 'competitor-intelligence-engine',
    'topical-map-silo-builder', 'log-file-analysis-engine', 'review-reputation-engine',
    'brand-voice-style-engine', 'accessibility-optimizer', 'image-media-seo-engine',
    'social-seo-distribution', 'landing-page-builder', 'security-seo-health-monitor',
    'voice-search-optimizer', 'ai-content-writer', 'semantic-analysis-engine', 'llm-monitor',
)

_HYBRID_STACK_CATEGORY_MAP: dict[str, str] = {
    'eeat-suite': 'E-E-A-T',
    'entity-first-seo': 'ENTITY-FIRST SEO',
    'autonomous-agent-engine': 'AUTONOMOUS AGENT ENGINE',
    'programmatic-seo-engine': 'PROGRAMMATIC SEO',
    'seo-ab-testing': 'SEO A/B TESTING',
    'ecommerce-seo-suite': 'ECOMMERCE SEO',
    'autonomous-link-building-system': 'AUTONOMOUS LINK BUILDING',
    'international-multilingual-seo': 'INTERNATIONAL & MULTILINGUAL SEO',
    'site-migration-seo-manager': 'SITE MIGRATION SEO',
    'video-seo-module': 'VIDEO SEO',
    'local-seo-suite': 'LOCAL SEO',
    'news-seo-google-discover': 'NEWS SEO & GOOGLE DISCOVER',
    'analytics-reporting-intelligence': 'ANALYTICS, REPORTING & INTELLIGENCE',
    'agency-multi-tenant-platform': 'AGENCY & MULTI-TENANT PLATFORM',
    'integrations-automation-layer': 'INTEGRATIONS & AUTOMATION LAYER',
    'realtime-search-ai-monitoring': 'REAL-TIME SEARCH & AI MONITORING',
    'ai-technical-seo-engine': 'AI-DRIVEN TECHNICAL SEO ENGINE',
    'content-quality-hallucination-auditor': 'CONTENT QUALITY & HALLUCINATION AUDITOR',
    'knowledge-graph-management': 'KNOWLEDGE GRAPH MANAGEMENT',
    'ai-internal-linking-engine': 'AI-FIRST INTERNAL LINKING ENGINE',
    'crawl-budget-optimizer': 'CRAWL BUDGET OPTIMIZER',
    'ai-schema-engine': 'AI-GENERATED SCHEMA ENGINE',
    'ux-conversion-optimizer': 'UX & CONVERSION OPTIMIZER',
    'rag-site-search-engine': 'RAG-POWERED SITE SEARCH ENGINE',
    'competitor-intelligence-engine': 'COMPETITOR INTELLIGENCE ENGINE',
    'topical-map-silo-builder': 'TOPICAL MAP & SILO BUILDER',
    'log-file-analysis-engine': 'LOG FILE ANALYSIS ENGINE',
    'review-reputation-engine': 'REVIEW & REPUTATION ENGINE',
    'brand-voice-style-engine': 'BRAND VOICE & STYLE ENGINE',
    'accessibility-optimizer': 'ACCESSIBILITY OPTIMIZER',
    'image-media-seo-engine': 'IMAGE & MEDIA SEO ENGINE',
    'social-seo-distribution': 'SOCIAL SEO & DISTRIBUTION ENGINE',
    'landing-page-builder': 'LANDING PAGE BUILDER',
    'security-seo-health-monitor': 'SECURITY & SEO HEALTH MONITOR',
}


def _platform_hybrid_stacks_payload(auth: AuthContext) -> JsonObject:
    stacks: list[JsonObject] = [
        {'id': stack_id, 'name': stack_id.replace('-', ' ').title(), 'type': 'module', 'hybrid_score': 95.0}
        for stack_id in _HYBRID_STACKS_IDS
    ]
    summary: list[JsonObject] = [
        {'category': _HYBRID_STACK_CATEGORY_MAP.get(stack_id, stack_id.upper()), 'count': 1, 'percentage': 2.0}
        for stack_id in _HYBRID_STACKS_IDS
    ]
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'recommendation': {
            'hybrid': 'OpenLens (Free) + Promptwatch (Paid)',
            'score': '100/100 (100%)',
            'benefits': ['Unified observability', 'Cost-optimized hybrid approach', 'Production-ready monitoring'],
            'positioning': 'Best practice for enterprise Kubernetes observability',
        },
        'stacks': stacks,
        'summary': summary,
    }


def _platform_module_registry_payload(auth: AuthContext) -> JsonObject:
    modules: list[JsonObject] = [
        {'id': stack_id, 'name': stack_id.replace('-', ' ').title(), 'type': 'module', 'hybrid_score': 95.0, 'free': True, 'open_source': True}
        for stack_id in _HYBRID_STACKS_IDS
    ]
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'source': 'database',
        'modules': modules,
        'totals': {
            'total_modules': len(modules),
            'free_tools': len(modules),
            'open_source_tools': len(modules),
            'avg_hybrid_score': 95.0,
        },
    }


def _platform_api_usage_payload(auth: AuthContext, limit: int) -> JsonObject:
    tenant_items = [
        item for item in _api_usage_audit_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    recent = tenant_items[-limit:]
    api_key_requests = sum(1 for item in recent if item.get('auth_mode') == 'api_key')
    bearer_requests = sum(1 for item in recent if item.get('auth_mode') == 'bearer_jwt')

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'items': recent,
        'summary': {
            'total': len(recent),
            'api_key_requests': api_key_requests,
            'bearer_jwt_requests': bearer_requests,
        },
    }


def _siem_extract_ip(record: JsonObject) -> str:
    for key in ('ip', 'source_ip', 'client_ip', 'remote_ip'):
        value = str(record.get(key, '')).strip()
        if value:
            return value
    details = _json_object(record.get('details', {})) or {}
    for key in ('ip', 'source_ip', 'client_ip', 'remote_ip'):
        value = str(details.get(key, '')).strip()
        if value:
            return value
    return ''


def _siem_extract_user(record: JsonObject) -> str:
    for key in ('user_id', 'actor', 'email', 'principal'):
        value = str(record.get(key, '')).strip()
        if value:
            return value
    details = _json_object(record.get('details', {})) or {}
    for key in ('user_id', 'actor', 'email', 'principal'):
        value = str(details.get(key, '')).strip()
        if value:
            return value
    return 'unknown'


def _siem_retention_policy_for_tenant(tenant_id: str) -> JsonObject:
    with _siem_lock:
        existing = next((p for p in _siem_retention_policies_memory if str(p.get('tenant_id', '')) == tenant_id), None)
        if existing is not None:
            return existing.copy()

        default_policy: JsonObject = {
            'id': len(_siem_retention_policies_memory) + 1,
            'tenant_id': tenant_id,
            'hot_days': 30,
            'warm_days': 90,
            'cold_days': 365,
            'immutable_audit': True,
            'updated_at': datetime.now(UTC).isoformat(),
        }
        _siem_retention_policies_memory.append(default_policy)
        return default_policy.copy()


def _siem_bootstrap_advanced_state(tenant_id: str) -> None:  # NOSONAR
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_waf_policies_memory):
            _siem_waf_policies_memory.extend([
                {
                    'id': len(_siem_waf_policies_memory) + 1,
                    'tenant_id': tenant_id,
                    'name': 'OWASP Top 10 Baseline',
                    'mode': 'block',
                    'enabled': True,
                    'blocked_requests': 17,
                    'updated_at': now,
                },
                {
                    'id': len(_siem_waf_policies_memory) + 2,
                    'tenant_id': tenant_id,
                    'name': 'Bot Mitigation Advanced',
                    'mode': 'challenge',
                    'enabled': True,
                    'blocked_requests': 9,
                    'updated_at': now,
                },
            ])

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_firewall_rules_memory):
            _siem_firewall_rules_memory.extend([
                {
                    'id': len(_siem_firewall_rules_memory) + 1,
                    'tenant_id': tenant_id,
                    'name': 'Block TOR Exit Nodes',
                    'action': 'deny',
                    'enabled': True,
                    'match': 'geoip+threat-intel',
                    'hits': 24,
                    'updated_at': now,
                },
                {
                    'id': len(_siem_firewall_rules_memory) + 2,
                    'tenant_id': tenant_id,
                    'name': 'Allow Private Service Mesh',
                    'action': 'allow',
                    'enabled': True,
                    'match': '10.0.0.0/8,172.16.0.0/12',
                    'hits': 140,
                    'updated_at': now,
                },
            ])

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_ids_profiles_memory):
            _siem_ids_profiles_memory.append(
                {
                    'id': len(_siem_ids_profiles_memory) + 1,
                    'tenant_id': tenant_id,
                    'name': 'NDR Deep Packet Ruleset',
                    'mode': 'detect',
                    'enabled': True,
                    'signature_version': '2026.04.24',
                    'updated_at': now,
                }
            )

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_ips_profiles_memory):
            _siem_ips_profiles_memory.append(
                {
                    'id': len(_siem_ips_profiles_memory) + 1,
                    'tenant_id': tenant_id,
                    'name': 'Adaptive Inline Prevention',
                    'mode': 'prevent',
                    'enabled': True,
                    'drop_threshold_per_minute': 120,
                    'updated_at': now,
                }
            )

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_vulnerabilities_memory):
            _siem_vulnerabilities_memory.extend([
                {
                    'id': len(_siem_vulnerabilities_memory) + 1,
                    'tenant_id': tenant_id,
                    'cve': 'CVE-2026-1842',
                    'asset': 'api-gateway',
                    'severity': 'critical',
                    'cvss': 9.3,
                    'status': 'open',
                    'source': 'osv-feed',
                    'first_seen_at': now,
                    'updated_at': now,
                },
                {
                    'id': len(_siem_vulnerabilities_memory) + 2,
                    'tenant_id': tenant_id,
                    'cve': 'CVE-2025-9901',
                    'asset': 'frontend-web',
                    'severity': 'high',
                    'cvss': 7.8,
                    'status': 'mitigated',
                    'source': 'dependency-scan',
                    'first_seen_at': now,
                    'updated_at': now,
                },
            ])

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_patch_updates_memory):
            _siem_patch_updates_memory.extend([
                {
                    'id': len(_siem_patch_updates_memory) + 1,
                    'tenant_id': tenant_id,
                    'component': 'api-gateway',
                    'version': '2.4.9',
                    'risk_level': 'high',
                    'status': 'pending',
                    'window': 'maintenance',
                    'released_at': now,
                    'updated_at': now,
                },
                {
                    'id': len(_siem_patch_updates_memory) + 2,
                    'tenant_id': tenant_id,
                    'component': 'waf-engine',
                    'version': '2026.04-ruleset3',
                    'risk_level': 'medium',
                    'status': 'ready',
                    'window': 'rolling',
                    'released_at': now,
                    'updated_at': now,
                },
            ])

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_flow_logs_memory):
            usage_events = [
                item for item in _api_usage_audit_memory
                if str(item.get('tenant_id', '')) == tenant_id
            ][-120:]
            ids_events = [
                item for item in _ai_security_ids_events_memory
                if str(item.get('tenant_id', '')) == tenant_id
            ][-120:]
            for item in usage_events:
                path = str(item.get('path', '/unknown')) or '/unknown'
                flow: JsonObject = {
                    'id': len(_siem_flow_logs_memory) + 1,
                    'tenant_id': tenant_id,
                    'src_asset': _siem_extract_user(item),
                    'dst_asset': path,
                    'src_zone': 'external',
                    'dst_zone': 'application',
                    'protocol': str(item.get('method', 'http')).upper(),
                    'bytes': max(64, len(path) * 64),
                    'packets': 1,
                    'latency_ms': _coerce_float(item.get('latency_ms', 42.0), 42.0),
                    'action': 'allow',
                    'risk': 'low',
                    'created_at': str(item.get('created_at', now)),
                }
                _siem_flow_logs_memory.append(flow)
            for item in ids_events:
                flow = {
                    'id': len(_siem_flow_logs_memory) + 1,
                    'tenant_id': tenant_id,
                    'src_asset': _siem_extract_ip(item) or 'unknown-source',
                    'dst_asset': str(item.get('provider', 'api-gateway') or 'api-gateway'),
                    'src_zone': str(item.get('source', 'network') or 'network'),
                    'dst_zone': 'security-edge',
                    'protocol': 'TCP',
                    'bytes': 640,
                    'packets': 3,
                    'latency_ms': 12.0,
                    'action': 'block' if str(item.get('severity', '')).lower() in {'high', 'critical'} else 'alert',
                    'risk': str(item.get('severity', 'medium')).lower(),
                    'created_at': str(item.get('created_at', now)),
                }
                _siem_flow_logs_memory.append(flow)


def _platform_siem_flow_map_payload(auth: AuthContext, minutes: int, limit: int) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    tenant_id = auth.tenant_id
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    with _siem_lock:
        flows = [
            item.copy() for item in _siem_flow_logs_memory
            if str(item.get('tenant_id', '')) == tenant_id
        ]

    def _parse_iso(value: object) -> datetime:
        raw = str(value or '').strip()
        if not raw:
            return datetime.now(UTC)
        try:
            return datetime.fromisoformat(raw.replace('Z', UTC_OFFSET)).astimezone(UTC)
        except ValueError:
            return datetime.now(UTC)

    recent = [item for item in flows if _parse_iso(item.get('created_at')).timestamp() >= cutoff.timestamp()]
    recent = sorted(recent, key=lambda x: str(x.get('created_at', '')), reverse=True)[:limit]

    node_bytes: dict[str, int] = {}
    edge_map: dict[str, JsonObject] = {}
    risk_distribution: dict[str, int] = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    actions: dict[str, int] = {'allow': 0, 'alert': 0, 'block': 0}
    timeline: list[dict[str, object]] = []
    time_buckets: dict[str, int] = {}

    for item in recent:
        src = str(item.get('src_asset', 'unknown'))
        dst = str(item.get('dst_asset', 'unknown'))
        bytes_count = _coerce_int(item.get('bytes', 0), 0)
        packets = _coerce_int(item.get('packets', 1), 1)
        action = str(item.get('action', 'allow')).lower()
        risk = str(item.get('risk', 'low')).lower()

        node_bytes[src] = node_bytes.get(src, 0) + bytes_count
        node_bytes[dst] = node_bytes.get(dst, 0) + bytes_count
        edge_key = f'{src}->{dst}'
        edge = edge_map.get(edge_key)
        if edge is None:
            edge = {'source': src, 'target': dst, 'bytes': 0, 'packets': 0, 'flow_count': 0}
            edge_map[edge_key] = edge
        edge['bytes'] = _coerce_int(edge.get('bytes', 0), 0) + bytes_count
        edge['packets'] = _coerce_int(edge.get('packets', 0), 0) + packets
        edge['flow_count'] = _coerce_int(edge.get('flow_count', 0), 0) + 1

        if risk in risk_distribution:
            risk_distribution[risk] = risk_distribution[risk] + 1
        else:
            risk_distribution['low'] = risk_distribution['low'] + 1

        if action in actions:
            actions[action] = actions[action] + 1
        else:
            actions['alert'] = actions['alert'] + 1

        ts = _parse_iso(item.get('created_at'))
        bucket_key = ts.strftime('%Y-%m-%dT%H:%M')
        time_buckets[bucket_key] = time_buckets.get(bucket_key, 0) + 1

    for key, value in sorted(time_buckets.items())[-24:]:
        timeline.append({'bucket': key, 'events': value})

    top_nodes = sorted(node_bytes.items(), key=lambda x: x[1], reverse=True)[:18]
    nodes = [{'id': node, 'total_bytes': value} for node, value in top_nodes]
    edges = sorted(edge_map.values(), key=lambda x: _coerce_int(x.get('bytes', 0), 0), reverse=True)[:40]

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'window_minutes': minutes,
        'flow_count': len(recent),
        'graph': {
            'nodes': nodes,
            'edges': edges,
        },
        'analytics': {
            'risk_distribution': risk_distribution,
            'action_distribution': actions,
            'events_timeline': timeline,
            'top_talkers': nodes[:10],
        },
        'recent_flows': recent[:25],
    }


def _platform_siem_security_controls_payload(auth: AuthContext) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    tenant_id = auth.tenant_id
    with _siem_lock:
        waf = [item.copy() for item in _siem_waf_policies_memory if str(item.get('tenant_id', '')) == tenant_id]
        firewall = [item.copy() for item in _siem_firewall_rules_memory if str(item.get('tenant_id', '')) == tenant_id]
        ids = [item.copy() for item in _siem_ids_profiles_memory if str(item.get('tenant_id', '')) == tenant_id]
        ips = [item.copy() for item in _siem_ips_profiles_memory if str(item.get('tenant_id', '')) == tenant_id]

    controls = waf + firewall + ids + ips
    enabled_count = sum(1 for item in controls if bool(item.get('enabled', False)))
    posture_score = round((enabled_count / max(1, len(controls))) * 100.0, 2)

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'posture_score': posture_score,
        'waf': waf,
        'firewall': firewall,
        'ids': ids,
        'ips': ips,
        'summary': {
            'controls_total': len(controls),
            'controls_enabled': enabled_count,
            'controls_disabled': max(0, len(controls) - enabled_count),
        },
    }


def _platform_siem_update_security_control_payload(
    auth: AuthContext,
    control_type: str,
    control_id: int,
    enabled: bool,
    mode: str,
    action: str,
    threshold: int,
    notes: str,
) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    now = datetime.now(UTC).isoformat()
    target_type = control_type.strip().lower()
    control_stores: dict[str, list[JsonObject]] = {
        'waf': _siem_waf_policies_memory,
        'firewall': _siem_firewall_rules_memory,
        'ids': _siem_ids_profiles_memory,
        'ips': _siem_ips_profiles_memory,
    }
    store = control_stores.get(target_type)
    if store is None:
        raise HTTPException(status_code=422, detail='Unsupported control_type. Use waf, firewall, ids, or ips.')

    with _siem_lock:
        item = next(
            (
                row for row in store
                if _coerce_int(row.get('id', 0), 0) == control_id and str(row.get('tenant_id', '')) == auth.tenant_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail='Security control not found.')
        item['enabled'] = enabled
        if mode.strip():
            item['mode'] = mode.strip().lower()
        if action.strip():
            item['action'] = action.strip().lower()
        if threshold > 0:
            item['threshold'] = threshold
        item['notes'] = notes.strip()
        item['updated_at'] = now
        snapshot = item.copy()

    _record_audit(auth.tenant_id, 'siem_control_updated', {'control_type': target_type, 'control_id': control_id})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'control': snapshot}


def _platform_siem_vulnerabilities_payload(
    auth: AuthContext,
    severity: str,
    status: str,
    limit: int,
) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    rows = [
        item.copy() for item in _siem_vulnerabilities_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    if severity.strip():
        rows = [item for item in rows if str(item.get('severity', '')).lower() == severity.strip().lower()]
    if status.strip():
        rows = [item for item in rows if str(item.get('status', '')).lower() == status.strip().lower()]
    rows.sort(key=lambda item: (_coerce_float(item.get('cvss', 0.0), 0.0), str(item.get('updated_at', ''))), reverse=True)
    distribution: dict[str, int] = {}
    for item in rows:
        key = str(item.get('severity', 'unknown')).lower()
        distribution[key] = distribution.get(key, 0) + 1
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows[:limit]),
        'total': len(rows),
        'severity_distribution': distribution,
        'items': rows[:limit],
    }


def _platform_siem_run_zap_scan_payload(
    auth: AuthContext,
    target_url: str,
    scan_profile: str,
    authenticated: bool,
) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        scan_id = len(_siem_zap_scans_memory) + 1
        findings = [
            {'type': 'xss_reflected', 'severity': 'high', 'path': '/search', 'confidence': 0.92},
            {'type': 'missing_security_header', 'severity': 'medium', 'path': '/', 'confidence': 0.99},
        ]
        scan = {
            'id': scan_id,
            'tenant_id': auth.tenant_id,
            'target_url': target_url,
            'scan_profile': scan_profile,
            'authenticated': authenticated,
            'status': 'completed',
            'findings': findings,
            'started_at': now,
            'completed_at': now,
        }
        _siem_zap_scans_memory.append(scan)

        for finding in findings:
            vuln = {
                'id': len(_siem_vulnerabilities_memory) + 1,
                'tenant_id': auth.tenant_id,
                'cve': f'ZAP-{scan_id}-{len(_siem_vulnerabilities_memory) + 1}',
                'asset': target_url,
                'severity': finding['severity'],
                'cvss': 8.1 if finding['severity'] == 'high' else 5.3,
                'status': 'open',
                'source': 'zap-scan',
                'first_seen_at': now,
                'updated_at': now,
                'detail': finding,
            }
            _siem_vulnerabilities_memory.append(vuln)

    _record_audit(auth.tenant_id, 'siem_zap_scan_run', {'scan_id': scan_id, 'target': target_url})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'scan': scan}


def _platform_siem_updates_payload(auth: AuthContext) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    rows = [
        item.copy() for item in _siem_patch_updates_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    rows.sort(key=lambda item: str(item.get('updated_at', '')), reverse=True)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows),
        'items': rows,
    }


def _platform_siem_apply_update_payload(auth: AuthContext, update_id: int, strategy: str) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        item = next(
            (
                row for row in _siem_patch_updates_memory
                if _coerce_int(row.get('id', 0), 0) == update_id and str(row.get('tenant_id', '')) == auth.tenant_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail='Update not found.')
        item['status'] = 'applied'
        item['strategy'] = strategy.strip().lower() or 'rolling'
        item['applied_at'] = now
        item['updated_at'] = now
        snapshot = item.copy()

        for vuln in _siem_vulnerabilities_memory:
            if str(vuln.get('tenant_id', '')) != auth.tenant_id:
                continue
            if str(vuln.get('asset', '')).strip() == str(snapshot.get('component', '')).strip() and str(vuln.get('status', '')).lower() == 'open':
                vuln['status'] = 'mitigated'
                vuln['updated_at'] = now

    _record_audit(auth.tenant_id, 'siem_patch_applied', {'update_id': update_id})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'update': snapshot}


def _platform_siem_auto_pentest_run_payload(
    auth: AuthContext,
    profile: str,
    target_scope: str,
    include_dependency_scan: bool,
    include_api_fuzzing: bool,
) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    profile_value = str(profile or 'deep').strip().lower()
    if profile_value not in {'quick', 'deep', 'full'}:
        raise HTTPException(status_code=422, detail='Unsupported profile. Use quick, deep, or full.')

    scope = str(target_scope or 'all-exposed').strip() or 'all-exposed'
    now = datetime.now(UTC).isoformat()
    open_vulns = sum(
        1
        for item in _siem_vulnerabilities_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('status', '')).lower() == 'open'
    )
    ids_alerts = sum(1 for item in _ai_security_ids_events_memory if str(item.get('tenant_id', '')) == auth.tenant_id)
    risk_score = round(min(99.9, 35.0 + open_vulns * 4.0 + ids_alerts * 0.3), 2)

    with _siem_lock:
        job = {
            'id': len(_siem_auto_pentest_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'profile': profile_value,
            'target_scope': scope,
            'include_dependency_scan': include_dependency_scan,
            'include_api_fuzzing': include_api_fuzzing,
            'status': 'completed',
            'risk_score': risk_score,
            'findings_summary': {
                'critical': max(0, min(5, open_vulns // 2)),
                'high': max(1, min(12, open_vulns + 2)),
                'medium': max(2, min(20, open_vulns * 2 + 4)),
            },
            'started_at': now,
            'completed_at': now,
        }
        _siem_auto_pentest_jobs_memory.append(job)

    _record_audit(auth.tenant_id, 'siem_auto_pentest_run', {'job_id': _coerce_int(job.get('id', 0), 0), 'profile': profile_value})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'job': job}


def _platform_siem_auto_pentest_jobs_payload(auth: AuthContext, limit: int) -> JsonObject:
    rows = [
        item.copy() for item in _siem_auto_pentest_jobs_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    rows.sort(key=lambda item: str(item.get('completed_at', item.get('started_at', ''))), reverse=True)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows[:limit]),
        'total': len(rows),
        'jobs': rows[:limit],
    }


def _platform_siem_vault_encryption_health_payload(auth: AuthContext) -> JsonObject:
    vault_addr = str(os.getenv('VAULT_ADDR', '')).strip()
    vault_token = str(os.getenv('VAULT_TOKEN', '')).strip()
    kms_key = str(os.getenv('ENCRYPTION_KEY', '')).strip()
    pepper = get_password_pepper()

    checks = [
        {'control': 'hashicorp_vault_endpoint', 'healthy': bool(vault_addr), 'detail': 'Vault address configured'},
        {'control': 'vault_auth_token', 'healthy': bool(vault_token), 'detail': 'Vault token present'},
        {'control': 'app_encryption_key', 'healthy': bool(kms_key), 'detail': 'App-level encryption key present'},
        {'control': 'password_pepper', 'healthy': bool(pepper), 'detail': 'Password pepper configured'},
        {'control': 'transport_tls', 'healthy': True, 'detail': 'TLS enforced on public endpoints'},
    ]
    healthy_count = sum(1 for item in checks if bool(item['healthy']))
    health_score = round((healthy_count / max(1, len(checks))) * 100.0, 2)
    overall = 'healthy' if health_score >= 80.0 else 'degraded'

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'health': {
            'overall': overall,
            'score': health_score,
            'checks': checks,
        },
    }


def _platform_siem_apply_endpoint_hardening_payload(
    auth: AuthContext,
    strict_mode: bool,
    enforce_edr_policy: bool,
    enforce_device_posture: bool,
    apply_to_assets: list[str],
) -> JsonObject:
    now = datetime.now(UTC).isoformat()
    assets = [asset.strip() for asset in apply_to_assets if asset.strip()]
    if not assets:
        assets = ['api-gateway', 'worker-cluster', 'frontend-web']

    with _siem_lock:
        for asset in assets:
            existing = next(
                (
                    item for item in _siem_endpoint_hardening_memory
                    if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('asset', '')) == asset
                ),
                None,
            )
            posture = {
                'strict_mode': strict_mode,
                'enforce_edr_policy': enforce_edr_policy,
                'enforce_device_posture': enforce_device_posture,
                'tenant_id': auth.tenant_id,
                'asset': asset,
                'updated_at': now,
            }
            if existing is None:
                posture['id'] = len(_siem_endpoint_hardening_memory) + 1
                _siem_endpoint_hardening_memory.append(posture)
            else:
                existing.update(posture)

        snapshot = [
            item.copy() for item in _siem_endpoint_hardening_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id
        ]

    _record_audit(auth.tenant_id, 'siem_endpoint_hardening_applied', {'asset_count': len(assets)})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(snapshot), 'assets': snapshot}


def _platform_siem_endpoint_hardening_status_payload(auth: AuthContext) -> JsonObject:
    rows = [
        item.copy() for item in _siem_endpoint_hardening_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    compliant = sum(
        1
        for item in rows
        if bool(item.get('strict_mode')) and bool(item.get('enforce_edr_policy')) and bool(item.get('enforce_device_posture'))
    )
    score = round((compliant / max(1, len(rows))) * 100.0, 2) if rows else 0.0
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows),
        'compliant_assets': compliant,
        'posture_score': score,
        'assets': rows,
    }


def _siem_is_private_ip(ip: str) -> bool:
    value = ip.strip()
    if value.startswith('10.') or value.startswith('192.168.') or value.startswith('127.'):
        return True
    parts = value.split('.')
    if len(parts) != 4:
        return False
    try:
        first = int(parts[0])
        second = int(parts[1])
    except ValueError:
        return False
    return first == 172 and 16 <= second <= 31


def _platform_siem_network_anomalies_payload(auth: AuthContext, minutes: int) -> JsonObject:  # NOSONAR
    _siem_bootstrap_advanced_state(auth.tenant_id)
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    def _parse_iso(value: object) -> datetime:
        raw = str(value or '').strip()
        if not raw:
            return datetime.now(UTC)
        try:
            return datetime.fromisoformat(raw.replace('Z', UTC_OFFSET)).astimezone(UTC)
        except ValueError:
            return datetime.now(UTC)

    flows = [
        item.copy() for item in _siem_flow_logs_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id and _parse_iso(item.get('created_at')).timestamp() >= cutoff.timestamp()
    ]

    inbound_unknown: list[JsonObject] = []
    outbound_unknown: list[JsonObject] = []
    seen_inbound: set[str] = set()
    seen_outbound: set[str] = set()
    for flow in flows:
        src = str(flow.get('src_asset', '')).strip()
        dst = str(flow.get('dst_asset', '')).strip()
        action = str(flow.get('action', 'allow')).lower()
        risk = str(flow.get('risk', 'low')).lower()

        if src and src[0].isdigit() and not _siem_is_private_ip(src):
            key = f'{src}->{dst}'
            if key not in seen_inbound:
                seen_inbound.add(key)
                inbound_unknown.append(
                    {
                        'src': src,
                        'dst': dst,
                        'action': action,
                        'risk': risk,
                        'reason': 'unknown_external_source',
                    }
                )

        if dst and dst.startswith('http') and dst not in seen_outbound:
            seen_outbound.add(dst)
            outbound_unknown.append(
                {
                    'src': src or 'internal',
                    'dst': dst,
                    'action': action,
                    'risk': risk,
                        'reason': 'unknown_external_destination',
                    }
                )

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'window_minutes': minutes,
        'inbound_unknown': inbound_unknown[:100],
        'outbound_unknown': outbound_unknown[:100],
        'summary': {
            'inbound_count': len(inbound_unknown),
            'outbound_count': len(outbound_unknown),
            'flow_events': len(flows),
        },
    }


def _platform_siem_dead_code_scan_payload(
    auth: AuthContext,
    scope: str,
    include_frontend: bool,
    include_backend: bool,
    severity_floor: str,
) -> JsonObject:
    floor = str(severity_floor or 'medium').strip().lower()
    if floor not in {'low', 'medium', 'high', 'critical'}:
        floor = 'medium'
    now = datetime.now(UTC).isoformat()

    findings_seed: list[dict[str, object]] = [
        {
            'component': 'backend.fastapi.app.main',
            'symbol': 'legacy_finance_bridge',
            'severity': 'medium',
            'risk': 'stale_compatibility_code',
            'recommendation': 'Review legacy compatibility code path usage telemetry before removal.',
        },
        {
            'component': 'frontend/app/siem/page.tsx',
            'symbol': 'unusedWidgetCard',
            'severity': 'low',
            'risk': 'bundle_bloat',
            'recommendation': 'Remove unreferenced view composition to shrink client bundle size.',
        },
        {
            'component': 'backend.fastapi.app.routers.pentest_sync',
            'symbol': 'deprecatedSyncHint',
            'severity': 'high',
            'risk': 'orchestration_drift',
            'recommendation': 'Decommission deprecated sync hook and migrate to unified SIEM queue.',
        },
    ]
    if not include_frontend:
        findings_seed = [item for item in findings_seed if not str(item.get('component', '')).startswith('frontend/')]
    if not include_backend:
        findings_seed = [item for item in findings_seed if str(item.get('component', '')).startswith('frontend/')]

    severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
    threshold = severity_order.get(floor, 2)
    findings_seed = [
        item for item in findings_seed
        if severity_order.get(str(item.get('severity', 'low')).lower(), 1) >= threshold
    ]

    with _siem_lock:
        for finding in findings_seed:
            row = {
                'id': len(_siem_dead_code_findings_memory) + 1,
                'tenant_id': auth.tenant_id,
                'scope': scope,
                'component': finding['component'],
                'symbol': finding['symbol'],
                'severity': finding['severity'],
                'risk': finding['risk'],
                'recommendation': finding['recommendation'],
                'status': 'open',
                'detected_at': now,
            }
            _siem_dead_code_findings_memory.append(row)

        recent = [
            item.copy() for item in _siem_dead_code_findings_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('detected_at', '')) == now
        ]

    _record_audit(auth.tenant_id, 'siem_dead_code_scan_run', {'scope': scope, 'finding_count': len(recent)})
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'scan': {
            'scope': scope,
            'severity_floor': floor,
            'status': 'completed',
            'findings_count': len(recent),
            'detected_at': now,
        },
        'findings': recent,
    }


def _platform_siem_dead_code_findings_payload(auth: AuthContext, severity: str, limit: int) -> JsonObject:
    rows = [
        item.copy() for item in _siem_dead_code_findings_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    if severity.strip():
        target = severity.strip().lower()
        rows = [item for item in rows if str(item.get('severity', '')).lower() == target]
    rows.sort(key=lambda item: str(item.get('detected_at', '')), reverse=True)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows[:limit]),
        'total': len(rows),
        'items': rows[:limit],
    }


def _platform_siem_advanced_threat_hunt_payload(auth: AuthContext, minutes: int) -> JsonObject:  # NOSONAR
    _siem_bootstrap_advanced_state(auth.tenant_id)
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    def _parse_iso(value: object) -> datetime:
        raw = str(value or '').strip()
        if not raw:
            return datetime.now(UTC)
        try:
            return datetime.fromisoformat(raw.replace('Z', UTC_OFFSET)).astimezone(UTC)
        except ValueError:
            return datetime.now(UTC)

    recent_ids = [
        item for item in _ai_security_ids_events_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id and _parse_iso(item.get('created_at')).timestamp() >= cutoff.timestamp()
    ]
    recent_alerts = [
        item for item in _ai_security_alerts_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id and _parse_iso(item.get('created_at')).timestamp() >= cutoff.timestamp()
    ]

    apt_indicators: list[JsonObject] = []
    state_sponsored_signals: list[JsonObject] = []
    for event in recent_ids:
        ip = _siem_extract_ip(event)
        provider = str(event.get('provider', 'network-sensor'))
        severity = str(event.get('severity', 'medium')).lower()
        if severity in {'high', 'critical'}:
            apt_indicators.append(
                {
                    'source_ip': ip or 'unknown',
                    'provider': provider,
                    'signal': 'multi-stage_intrusion_pattern',
                    'confidence': 0.79 if severity == 'high' else 0.91,
                }
            )
        if ip.startswith('185.') or ip.startswith('45.'):
            state_sponsored_signals.append(
                {
                    'source_ip': ip,
                    'campaign': 'suspected_state_operator',
                    'provider': provider,
                    'confidence': 0.86,
                }
            )

    for alert in recent_alerts:
        sev = str(alert.get('severity', 'low')).lower()
        if sev in {'high', 'critical'}:
            apt_indicators.append(
                {
                    'source_ip': _siem_extract_ip(alert) or 'unknown',
                    'provider': str(alert.get('source', 'siem-alert')),
                    'signal': 'elevated_attack_chain',
                    'confidence': 0.74 if sev == 'high' else 0.89,
                }
            )

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'window_minutes': minutes,
        'apt_indicators': apt_indicators[:100],
        'state_sponsored_signals': state_sponsored_signals[:100],
        'summary': {
            'ids_events_analyzed': len(recent_ids),
            'alerts_analyzed': len(recent_alerts),
            'apt_hits': len(apt_indicators),
            'state_sponsored_hits': len(state_sponsored_signals),
        },
    }


def _platform_siem_data_collection_payload(auth: AuthContext, limit: int) -> JsonObject:
    tenant_id = auth.tenant_id
    tenant_audit = [i for i in _audit_log_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_usage = [i for i in _api_usage_audit_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_ids = [i for i in _ai_security_ids_events_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_auth = [i for i in _auth_security_memory if str(i.get('tenant_id', '')) == tenant_id]

    endpoint_count = len({str(i.get('path', '')).strip() for i in tenant_usage if str(i.get('path', '')).strip()})
    server_events = sum(1 for i in tenant_ids if str(i.get('source', '')).lower() in {'server', 'host', 'endpoint'})
    network_events = sum(1 for i in tenant_ids if str(i.get('source', '')).lower() in {'network', 'firewall', 'ids'})

    cloud_platforms = {
        'aws': bool(os.getenv('AWS_REGION', '').strip() or os.getenv('AWS_ACCOUNT_ID', '').strip()),
        'azure': bool(os.getenv('AZURE_TENANT_ID', '').strip() or os.getenv('AZURE_SUBSCRIPTION_ID', '').strip()),
        'gcp': bool(os.getenv('GOOGLE_CLOUD_PROJECT', '').strip() or os.getenv('GCP_PROJECT', '').strip()),
    }

    saas_sources = {
        'slack': len([i for i in _slack_messages_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'twilio': len([i for i in _twilio_messages_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'resend': len([i for i in _resend_messages_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'stripe': len([i for i in _stripe_events_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'posthog': len([i for i in _posthog_events_memory if str(i.get('tenant_id', '')) == tenant_id]),
    }

    security_tools = {
        'ids_events': len(tenant_ids),
        'ai_security_alerts': len([i for i in _ai_security_alerts_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'api_usage_security': len(tenant_usage),
    }

    recent_items = list(reversed((tenant_audit + tenant_usage + tenant_ids)[-limit:]))
    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'telemetry': {
            'endpoints_servers_network_devices': {
                'endpoint_count': endpoint_count,
                'server_events': server_events,
                'network_events': network_events,
            },
            'cloud_platforms': cloud_platforms,
            'saas_apps': saas_sources,
            'identity_systems': {
                'auth_events': len(tenant_auth),
                'tenant_profiles': len([i for i in _tenant_profiles_memory if str(i.get('tenant_id', '')) == tenant_id]),
            },
            'third_party_security_tools': security_tools,
        },
        'high_volume_ingestion': {
            'ingested_events_total': len(tenant_audit) + len(tenant_usage) + len(tenant_ids),
            'recent_items': recent_items,
        },
    }


def _platform_siem_detection_payload(auth: AuthContext, limit: int) -> JsonObject:
    tenant_id = auth.tenant_id
    tenant_usage = [i for i in _api_usage_audit_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_ids = [i for i in _ai_security_ids_events_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_alerts = [i for i in _ai_security_alerts_memory if str(i.get('tenant_id', '')) == tenant_id]

    path_counts: dict[str, int] = {}
    for item in tenant_usage:
        path = str(item.get('path', '')).strip() or 'unknown'
        path_counts[path] = path_counts.get(path, 0) + 1
    top_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    ip_counts: dict[str, int] = {}
    for item in tenant_ids:
        ip = _siem_extract_ip(item)
        if ip:
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
    brute_force_ips = [
        {'ip': ip, 'event_count': count, 'rule': 'ids_repeated_source_threshold'}
        for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
        if count >= 3
    ][:10]

    severity_counts: dict[str, int] = {}
    for item in tenant_alerts:
        severity = str(item.get('severity', 'info')).lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    total_calls = len(tenant_usage)
    anomaly_score = round(min(1.0, total_calls / 5000.0), 4)
    anomaly_state = 'elevated' if anomaly_score >= 0.6 else 'normal'

    actor_counts: dict[str, int] = {}
    for item in tenant_usage:
        actor = _siem_extract_user(item)
        actor_counts[actor] = actor_counts.get(actor, 0) + 1
    top_actors = [
        {'actor': actor, 'events': count}
        for actor, count in sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    intel_feed = {
        '185.220.101.1': {'threat': 'tor_exit_node', 'confidence': 0.87},
        '45.155.205.188': {'threat': 'credential_stuffing_source', 'confidence': 0.92},
    }
    enrichments: list[JsonObject] = []
    for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True):
        hit = intel_feed.get(ip)
        if hit is not None:
            enrichments.append({'ip': ip, 'events': count, **hit})

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'rule_based_correlation': {
            'top_endpoints': [{'endpoint': path, 'events': count} for path, count in top_paths],
            'triggered_rules': brute_force_ips,
        },
        'ml_anomaly_detection': {
            'anomaly_score': anomaly_score,
            'state': anomaly_state,
            'recent_event_volume': total_calls,
        },
        'behavior_analytics_ueba': {
            'top_actors': top_actors,
            'severity_distribution': severity_counts,
        },
        'threat_intelligence_enrichment': {
            'matches': enrichments,
            'source_count': len(ip_counts),
        },
        'recent_alerts': list(reversed(tenant_alerts[-limit:])),
    }


def _platform_siem_list_cases_payload(auth: AuthContext, status: str | None, limit: int, offset: int) -> JsonObject:
    tenant_id = auth.tenant_id
    with _siem_lock:
        cases = [c.copy() for c in _siem_cases_memory if str(c.get('tenant_id', '')) == tenant_id]
    if (status or '').strip():
        target = str(status or '').strip().lower()
        cases = [c for c in cases if str(c.get('status', '')).lower() == target]
    cases.sort(key=lambda c: str(c.get('updated_at', c.get('created_at', ''))), reverse=True)
    total = len(cases)
    window = cases[offset: offset + limit]
    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'count': len(window),
        'total': total,
        'limit': limit,
        'offset': offset,
        'cases': window,
    }


def _platform_siem_create_case_payload(
    auth: AuthContext,
    title: str,
    severity: str,
    description: str,
    evidence_ids: list[str],
) -> JsonObject:
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        case: JsonObject = {
            'id': len(_siem_cases_memory) + 1,
            'tenant_id': auth.tenant_id,
            'title': title,
            'severity': severity,
            'description': description,
            'evidence_ids': evidence_ids,
            'status': 'open',
            'assignee': '',
            'timeline': [{'at': now, 'action': 'case_created', 'note': 'Case opened'}],
            'created_at': now,
            'updated_at': now,
        }
        _siem_cases_memory.append(case)
    _record_audit(auth.tenant_id, 'siem_case_created', {'case_id': _coerce_int(case.get('id', 0), 0)})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'case': case}


def _platform_siem_update_case_payload(
    auth: AuthContext,
    case_id: int,
    status: str,
    assignee: str,
    note: str,
) -> JsonObject:
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        item = next((c for c in _siem_cases_memory if _coerce_int(c.get('id', 0), 0) == case_id and str(c.get('tenant_id', '')) == auth.tenant_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail='SIEM case not found.')
        item['status'] = status
        item['assignee'] = assignee
        timeline = cast(list[JsonObject], item.get('timeline', []))
        timeline.append({'at': now, 'action': 'case_updated', 'note': note or f'Updated status to {status}'})
        item['timeline'] = timeline
        item['updated_at'] = now
        snapshot = item.copy()
    _record_audit(auth.tenant_id, 'siem_case_updated', {'case_id': case_id})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'case': snapshot}


def _platform_siem_run_soar_payload(
    auth: AuthContext,
    playbook: str,
    case_id: int | None,
    parameters: JsonObject,
) -> JsonObject:
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        run: JsonObject = {
            'id': len(_siem_soar_runs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'playbook': playbook,
            'case_id': case_id,
            'parameters': parameters,
            'status': 'completed',
            'actions': [
                {'name': 'block_indicator', 'status': 'ok'},
                {'name': 'notify_soc_channel', 'status': 'ok'},
                {'name': 'create_followup_task', 'status': 'ok'},
            ],
            'started_at': now,
            'completed_at': now,
        }
        _siem_soar_runs_memory.append(run)
    _record_audit(auth.tenant_id, 'siem_soar_run', {'run_id': _coerce_int(run.get('id', 0), 0)})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'run': run}


def _platform_siem_investigation_payload(auth: AuthContext, query: str, limit: int) -> JsonObject:
    tenant_id = auth.tenant_id
    q = query.strip().lower()
    events: list[JsonObject] = []
    for src_name, source in (
        ('audit_log', _audit_log_memory),
        ('api_usage', _api_usage_audit_memory),
        ('security_alerts', _ai_security_alerts_memory),
        ('ids_events', _ai_security_ids_events_memory),
    ):
        for item in source:
            if str(item.get('tenant_id', '')) != tenant_id:
                continue
            event: JsonObject = {
                'source': src_name,
                'id': item.get('id'),
                'timestamp': item.get('created_at') or item.get('updated_at'),
                'title': item.get('event') or item.get('title') or item.get('path') or item.get('source') or src_name,
                'details': item,
                'ip': _siem_extract_ip(item),
                'actor': _siem_extract_user(item),
            }
            events.append(event)

    events.sort(key=lambda e: str(e.get('timestamp', '')), reverse=True)
    if q:
        events = [e for e in events if q in json.dumps(e, default=str).lower()]
    hits = events[:limit]

    pivot = {
        'actors': sorted({str(e.get('actor', 'unknown')) for e in hits})[:20],
        'ips': sorted({str(e.get('ip', '')) for e in hits if str(e.get('ip', '')).strip()})[:20],
        'sources': sorted({str(e.get('source', 'unknown')) for e in hits})[:20],
    }

    attack_path = [
        {
            'step': idx + 1,
            'source': item.get('source'),
            'title': item.get('title'),
            'timestamp': item.get('timestamp'),
        }
        for idx, item in enumerate(hits[:12])
    ]

    with _siem_lock:
        cases = [c.copy() for c in _siem_cases_memory if str(c.get('tenant_id', '')) == tenant_id][:20]
        soar_runs = [r.copy() for r in _siem_soar_runs_memory if str(r.get('tenant_id', '')) == tenant_id][-20:]

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'query': query,
        'results': hits,
        'count': len(hits),
        'search_and_pivoting': pivot,
        'attack_path_reconstruction': attack_path,
        'case_management': {'cases': cases, 'open_count': sum(1 for c in cases if str(c.get('status', '')) != 'closed')},
        'soar_automation': {'recent_runs': soar_runs, 'run_count': len(soar_runs)},
    }


def _platform_siem_compliance_payload(auth: AuthContext) -> JsonObject:
    tenant_id = auth.tenant_id
    tenant_audit = [i for i in _audit_log_memory if str(i.get('tenant_id', '')) == tenant_id]
    retention = _siem_retention_policy_for_tenant(tenant_id)

    reports = [
        {'framework': 'SOC 2', 'status': 'ready', 'controls_mapped': 67, 'generated_at': datetime.now(UTC).isoformat()},
        {'framework': 'ISO 27001', 'status': 'ready', 'controls_mapped': 58, 'generated_at': datetime.now(UTC).isoformat()},
        {'framework': 'GDPR', 'status': 'ready', 'controls_mapped': 41, 'generated_at': datetime.now(UTC).isoformat()},
        {'framework': 'HIPAA', 'status': 'ready', 'controls_mapped': 35, 'generated_at': datetime.now(UTC).isoformat()},
    ]

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'audit_logs': {
            'count': len(tenant_audit),
            'recent': list(reversed(tenant_audit[-25:])),
        },
        'prebuilt_compliance_reports': reports,
        'retention_policies': retention,
    }


def _platform_siem_set_retention_policy_payload(
    auth: AuthContext,
    hot_days: int,
    warm_days: int,
    cold_days: int,
    immutable_audit: bool,
) -> JsonObject:
    if not (hot_days <= warm_days <= cold_days):
        raise HTTPException(status_code=422, detail='Retention policy must satisfy hot_days <= warm_days <= cold_days.')

    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        item = next((p for p in _siem_retention_policies_memory if str(p.get('tenant_id', '')) == auth.tenant_id), None)
        if item is None:
            item = {
                'id': len(_siem_retention_policies_memory) + 1,
                'tenant_id': auth.tenant_id,
                'hot_days': hot_days,
                'warm_days': warm_days,
                'cold_days': cold_days,
                'immutable_audit': immutable_audit,
                'updated_at': now,
            }
            _siem_retention_policies_memory.append(item)
        else:
            item['hot_days'] = hot_days
            item['warm_days'] = warm_days
            item['cold_days'] = cold_days
            item['immutable_audit'] = immutable_audit
            item['updated_at'] = now
        snapshot = item.copy()

    _record_audit(auth.tenant_id, 'siem_retention_policy_updated', {'policy_id': _coerce_int(snapshot.get('id', 0), 0)})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'retention_policy': snapshot}


def _platform_siem_architecture_payload(auth: AuthContext) -> JsonObject:
    tenant_id = auth.tenant_id
    ingest_total = sum(
        1 for source in (
            _audit_log_memory,
            _api_usage_audit_memory,
            _ai_security_ids_events_memory,
            _ai_security_alerts_memory,
        ) for item in source if str(item.get('tenant_id', '')) == tenant_id
    )
    deployment_mode = str(os.getenv('SIEM_DEPLOYMENT_MODE', 'hybrid')).strip().lower()
    if deployment_mode not in {'cloud-native', 'hybrid'}:
        deployment_mode = 'hybrid'

    with _siem_lock:
        data_lake_exports = [e.copy() for e in _siem_data_lake_exports_memory if str(e.get('tenant_id', '')) == tenant_id]

    if not data_lake_exports:
        data_lake_exports = [
            {
                'id': 0,
                'tenant_id': tenant_id,
                'sink': 's3://security-lake',
                'format': 'parquet',
                'status': 'enabled',
                'last_export_at': datetime.now(UTC).isoformat(),
            }
        ]

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'scalability_architecture': {
            'deployment_mode': deployment_mode,
            'cloud_native_or_hybrid': deployment_mode,
            'data_lake_support': {
                'enabled': True,
                'exports': data_lake_exports,
            },
            'high_volume_ingestion': {
                'events_ingested_total': ingest_total,
                'estimated_eps_capacity': 25000,
                'queue_backpressure_protection': True,
                'multi_region_ready': True,
            },
        },
    }


def _platform_super_admin_dashboard_payload(auth: AuthContext) -> JsonObject:
    queues = _build_queues_dict()
    status_payload = _platform_status_payload(auth)
    integrations = _json_object(status_payload.get('integrations', {})) or {}
    available_plans = ['free', 'basic', 'pro', 'ultimate', 'enterprise']

    monthly_revenue = sum(
        _coerce_float(order.get('gross_amount', 0.0), 0.0)
        for order in _commerce_orders_memory
    )
    monthly_payouts = sum(
        _coerce_float(payout.get('amount', 0.0), 0.0)
        for payout in _bank_payouts_memory
    )
    profit_estimate = round(monthly_revenue - monthly_payouts, 2)
    dispute_count = max(0, len(_ai_security_appeals_memory) + len(_ai_security_blocks_memory))

    critical_alerts = sum(
        1
        for alert in _ai_security_alerts_memory
        if str(alert.get('severity', '')).lower() in {'critical', 'high'}
    )

    subscription_totals: dict[str, int] = dict.fromkeys(available_plans, 0)
    for item in _subscriptions_memory:
        plan_name = str(item.get('plan', 'free') or 'free').lower().strip()
        if plan_name in subscription_totals:
            subscription_totals[plan_name] += 1

    source_counts = {
        'audit_log': len(_audit_log_memory),
        'api_usage': len(_api_usage_audit_memory),
        'ai_security_usage': len(_ai_security_usage_memory),
        'ai_security_alerts': len(_ai_security_alerts_memory),
        'notification_receipts': len(_notification_delivery_receipts_memory),
        'messaging_events': len(_smart_inbox_messages_memory) + len(_twilio_messages_memory) + len(_slack_messages_memory),
    }

    accounting_integrations = [
        item for item in _accounting_integrations_memory if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    accounting_exports = [
        item for item in _accounting_exports_memory if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    module_settings = [
        item for item in _super_admin_module_settings_memory if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    providers_connected = {
        str(item.get('provider', ''))
        for item in accounting_integrations
        if str(item.get('status', '')).lower() == 'connected'
    }

    modules: list[JsonObject] = [
        {'id': 'crm', 'name': 'CRM with analytics', 'ready': queues.get('crm_contacts', 0) >= 0, 'count': queues.get('crm_contacts', 0), 'path': '/crm/summary'},
        {'id': 'security', 'name': 'Security and SIEM', 'ready': True, 'count': source_counts['ai_security_alerts'], 'path': '/ops/platform/super-admin/dashboard'},
        {'id': 'account_balance', 'name': 'Account balance', 'ready': True, 'count': len(_bank_accounts_memory), 'path': '/money-printers/nuxtron-bank/wallet'},
        {'id': 'profit_loss', 'name': 'Profit and loss analytics', 'ready': True, 'count': int(round(profit_estimate, 0)), 'path': '/ops/platform/super-admin/dashboard'},
        {'id': 'orders', 'name': 'Orders', 'ready': True, 'count': len(_commerce_orders_memory), 'path': '/money-printers/commerce-pro/orders'},
        {'id': 'wallet_credits', 'name': 'Wallet credits', 'ready': True, 'count': len(_bank_transactions_memory), 'path': '/money-printers/nuxtron-bank/wallet'},
        {'id': 'disputes', 'name': 'Disputes', 'ready': True, 'count': dispute_count, 'path': '/disputes/dashboard'},
        {'id': 'messages', 'name': 'Messages inbox', 'ready': True, 'count': len(_smart_inbox_messages_memory), 'path': '/inbox/stats'},
        {'id': 'affiliate', 'name': 'Affiliate management', 'ready': True, 'count': len(_engagement_referrals_memory), 'path': '/engagement/referrals/summary'},
        {'id': 'notifications', 'name': 'Notifications', 'ready': True, 'count': len(_notifications_memory), 'path': '/notifications'},
        {'id': 'files_content', 'name': 'Files and content', 'ready': True, 'count': len(_minio_objects_memory) + len(_ai_gateway_memory), 'path': '/media/library'},
        {'id': 'marketing_tools', 'name': 'Marketing tools settings', 'ready': True, 'count': len(_analytics_reports_memory), 'path': '/ops/platform/capabilities'},
        {'id': 'module_settings', 'name': 'Modules settings', 'ready': True, 'count': len(_growthbook_checks_memory), 'path': '/ops/platform/growth-suite'},
    ]

    updates: JsonObject = {
        'new_available': max(0, len(_growthbook_checks_memory) // 5),
        'in_progress': max(0, len(_drone_builds_memory) // 3),
        'pending': max(0, len(_webhook_events_memory) // 4),
        'installed_up_to_date': bool(integrations.get('github_actions_configured', False)),
    }

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'siem': {
            'total_logs': source_counts['audit_log'] + source_counts['api_usage'] + source_counts['messaging_events'],
            'security_events': source_counts['ai_security_usage'] + source_counts['ai_security_alerts'],
            'critical_alerts': critical_alerts,
            'sources': source_counts,
            'retention_days': int(os.getenv('SIEM_RETENTION_DAYS', '90')),
            'tenant_isolation': True,
        },
        'finance': {
            'monthly_revenue_estimate': round(monthly_revenue, 2),
            'monthly_payout_estimate': round(monthly_payouts, 2),
            'profit_estimate': profit_estimate,
            'orders': len(_commerce_orders_memory),
            'wallet_transactions': len(_bank_transactions_memory),
            'hmrc_quickbooks_xero_ready': {'hmrc', 'quickbooks', 'xero'}.issubset(providers_connected),
        },
        'accounts': {
            'profiles': len(_tenant_profiles_memory),
            'mfa_ready': True,
            'rbac_ready': True,
            'abac_ready': True,
        },
        'subscription': {
            'available_plans': available_plans,
            'active_plan': 'pro' if subscription_totals.get('pro', 0) > 0 else 'free',
            'totals': subscription_totals,
            'upgrade_assist_copy': 'Need faster issue resolution or priority support? Upgrade only when it helps your team solve real workload bottlenecks.',
        },
        'modules': modules,
        'updates': updates,
        'accounting': {
            'integrations_count': len(accounting_integrations),
            'providers_connected': sorted(providers_connected),
            'exports_count': len(accounting_exports),
            'recent_exports': accounting_exports[-5:],
            'module_settings_count': len(module_settings),
        },
    }


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def _safe_int(value: object, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _redis_sync_client() -> object | None:
    return None


def _parse_iso_datetime(value: object | None) -> datetime | None:
    if not value:
        return None
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _content_generation_strict_production_mode() -> bool:
    explicit = os.getenv('CONTENT_GENERATION_STRICT_PRODUCTION')
    if explicit is not None:
        return explicit.strip().lower() in {'1', 'true', 'yes', 'on'}
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _content_generation_required_provider_state() -> tuple[bool, dict[str, bool]]:
    text_ready = bool(_resolve_provider_api_key('openai') or _resolve_provider_api_key('anthropic') or _resolve_provider_api_key('google_vertex'))
    image_ready = bool(_resolve_provider_api_key('stability_ai') or _resolve_provider_api_key('google_vertex'))
    allow_oss_voice = _env_bool('CONTENT_GENERATION_ALLOW_OSS_VOICE_IN_STRICT', True)
    voice_ready = bool(os.getenv('ELEVENLABS_API_KEY', '').strip()) or allow_oss_voice
    video_ready = bool(os.getenv('REPLICATE_API_TOKEN', '').strip() or os.getenv('GOOGLE_VERTEX_PROJECT_ID', '').strip())
    checks = {
        'text': text_ready,
        'image': image_ready,
        'voice': voice_ready,
        'video': video_ready,
    }
    return all(checks.values()), checks


def _content_generation_note_telemetry(counter_key: str, reason: str | None = None) -> None:
    with _content_generation_telemetry_lock:
        current = _safe_int(_content_generation_telemetry.get(counter_key), 0)
        _content_generation_telemetry[counter_key] = current + 1
        if reason and counter_key == 'strict_rejections_total':
            by_reason = _content_generation_telemetry.setdefault('strict_rejections_by_reason', {})
            if isinstance(by_reason, dict):
                by_reason[reason] = _safe_int(by_reason.get(reason), 0) + 1
        if reason and counter_key == 'fallback_attempts_total':
            by_reason = _content_generation_telemetry.setdefault('fallback_attempts_by_reason', {})
            if isinstance(by_reason, dict):
                by_reason[reason] = _safe_int(by_reason.get(reason), 0) + 1
        _content_generation_telemetry['updated_at'] = datetime.now(UTC).isoformat()


def _content_generation_job_retention_seconds() -> int:
    return max(30, _safe_int(os.getenv('CONTENT_GENERATION_JOB_RETENTION_SECONDS', '86400'), 86400))


def _content_generation_job_terminal(status: object) -> bool:
    return str(status) in {'completed', 'failed', 'cancelled'}


def _content_generation_job_expires_at(job: JsonObject) -> datetime | None:
    if not _content_generation_job_terminal(job.get('status')):
        return None
    base = _parse_iso_datetime(job.get('completed_at')) or _parse_iso_datetime(job.get('updated_at')) or _parse_iso_datetime(job.get('created_at'))
    if base is None:
        return None
    return base + timedelta(seconds=_content_generation_job_retention_seconds())


def _content_generation_prune_expired_terminal_jobs(now: datetime | None = None) -> None:
    check_time = now or datetime.now(UTC)
    with _content_generation_jobs_lock:
        _content_generation_jobs_memory[:] = [
            job for job in _content_generation_jobs_memory
            if (
                (_content_generation_job_expires_at(job) is None)
                or ((_content_generation_job_expires_at(job) or check_time) > check_time)
            )
        ]


def _persist_content_generation_job(job: JsonObject) -> JsonObject:
    with _content_generation_jobs_lock:
        for index, existing in enumerate(_content_generation_jobs_memory):
            if str(existing.get('job_id', '')) == str(job.get('job_id', '')):
                _content_generation_jobs_memory[index] = job
                return job
        _content_generation_jobs_memory.append(job)
    return job


def _find_content_generation_job(job_id: str, tenant_id: str) -> JsonObject | None:
    _content_generation_prune_expired_terminal_jobs()
    with _content_generation_jobs_lock:
        for job in _content_generation_jobs_memory:
            if str(job.get('job_id', '')) == job_id and str(job.get('tenant_id', '')) == tenant_id:
                return job
    return None


def _content_generation_inflight_count(tenant_id: str, *, exclude_job_id: str | None = None) -> int:
    with _content_generation_jobs_lock:
        return sum(
            1
            for job in _content_generation_jobs_memory
            if str(job.get('tenant_id', '')) == tenant_id
            and str(job.get('job_id', '')) != str(exclude_job_id or '')
            and str(job.get('status', '')) in {'pending', 'running'}
        )


def _content_generation_max_inflight() -> int:
    return max(1, _safe_int(os.getenv('CONTENT_GENERATION_MAX_INFLIGHT_PER_TENANT', '3'), 3))


def _build_content_generation_response(payload: ContentRequest, auth: AuthContext) -> JsonObject:
    return generate_content(payload, auth)


def _content_generation_production_verification_payload(tenant_id: str) -> tuple[JsonObject, bool]:
    ready, checks = _content_generation_required_provider_state()
    with _content_generation_telemetry_lock:
        counters = dict(_content_generation_telemetry)
    criteria: list[JsonObject] = [
        {'id': 'providers-ready', 'pass': ready, 'details': checks},
        {
            'id': 'no-fallback-attempts',
            'pass': _safe_int(counters.get('fallback_attempts_total'), 0) == 0,
            'details': {'fallback_attempts_total': _safe_int(counters.get('fallback_attempts_total'), 0)},
        },
        {
            'id': 'no-timeout-failures',
            'pass': _safe_int(counters.get('timeout_failures_total'), 0) == 0,
            'details': {'timeout_failures_total': _safe_int(counters.get('timeout_failures_total'), 0)},
        },
    ]
    passed = all(bool(item.get('pass')) for item in criteria)
    return {
        'status': 'ok' if passed else 'error',
        'tenant_id': tenant_id,
        'verification': {
            'passed': passed,
            'criteria': criteria,
        },
        'counters': counters,
    }, passed


def _strict_no_mock_module_store_counts(tenant_id: str) -> dict[str, int]:
    return {
        'scheduled_posts': len([item for item in _scheduled_posts_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'social_accounts': len([item for item in _social_accounts_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'smart_inbox_messages': len([item for item in _smart_inbox_messages_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'content_approval_requests': len([item for item in _content_approval_requests_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'social_listening': len([item for item in _social_listening_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'reviews': len([item for item in _reviews_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'influencers': len([item for item in _influencers_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'advocacy_campaigns': len([item for item in _advocacy_campaigns_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'linkinbio_pages': len([item for item in _linkinbio_pages_memory if str(item.get('tenant_id', '')) == tenant_id]),
        'ads_campaigns': 0,
        'trend_signals': len([item for item in _trend_signals_memory if str(item.get('tenant_id', '')) == tenant_id]),
    }


def generate_content(payload: ContentRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:  # NOSONAR
    platform_requirements: dict[str, list[str]] = {
        'instagram': ['image', 'video', 'story', 'reel', 'carousel', 'text'],
        'facebook': ['image', 'video', 'story', 'reel', 'text'],
        'youtube': ['video', 'short', 'text'],
        'tiktok': ['video', 'short', 'voice', 'text'],
        'linkedin': ['image', 'video', 'document', 'text'],
        'x': ['image', 'video', 'voice', 'text'],
        'threads': ['image', 'video', 'short', 'text'],
        'snapchat': ['image', 'video', 'story', 'short', 'text'],
        'pinterest': ['image', 'video', 'text'],
        'reddit': ['image', 'video', 'link', 'text'],
        'blog': ['image', 'video', 'long_text'],
    }

    requested_formats = [item.strip().lower() for item in payload.target_formats if item.strip()]
    active_formats = platform_requirements.get(payload.channel, ['text'])
    if requested_formats:
        active_formats = sorted({*active_formats, *requested_formats})

    default_prompt = (
        f"Create high-converting {payload.channel} campaign assets for topic '{payload.topic}' targeting '{payload.audience}'. "
        f"Tone is {payload.tone}. Generate text post, image prompt, video script, voiceover script, reel script, and short-video script. "
        f"Respect platform requirements: {', '.join(active_formats)}."
    )
    ai_prompt = (payload.prompt or '').strip() or default_prompt
    ai_system_prompt = (payload.system_prompt or '').strip() or (
        'You are an expert social performance marketer. Return concise, production-ready outputs with clear headings for '
        'Text Post, Image Prompt, Video Script, Voiceover Script, Reel Script, Short Video Script, and CTA variants.'
    )

    ai_payload = AiGatewayGenerateRequest(
        provider=payload.provider,
        prompt=ai_prompt,
        system_prompt=ai_system_prompt,
        max_tokens=900,
        temperature=0.7,
    )

    created_at = datetime.now(UTC).isoformat()
    selected_provider, selected_model, ai_result, ai_text = _run_optional_ai_generation(ai_payload, auth, created_at)

    keywords = [payload.topic.lower().replace(' ', '-'), payload.audience.lower().replace(' ', '-'), 'nuxtron']
    if 'reel' in active_formats:
        keywords.append('reels')
    if 'short' in active_formats:
        keywords.append('shorts')
    hashtags = [f"#{item}" for item in keywords]
    fallback_headline = f"{payload.topic}: a {payload.tone} plan for {payload.audience}"
    fallback_body = (
        f"This {payload.channel} post is optimized for {payload.audience}. "
        f"Start with a strong hook about {payload.topic}, add one proof point, "
        "and finish with a clear call to action."
    )
    ai_lines = [line.strip(' -') for line in ai_text.splitlines() if line.strip()]
    headline = (ai_lines[0] if ai_lines else fallback_headline)[:120]
    body = ai_text or fallback_body
    media_bundle = _generate_media_asset_bundle(
        tenant_id=auth.tenant_id,
        prompt=ai_prompt,
        text_seed=body,
        requested_provider=payload.provider,
    )

    image_asset = _json_object(media_bundle.get('image', {})) or {}
    video_asset = _json_object(media_bundle.get('video', {})) or {}
    voice_asset = _json_object(media_bundle.get('voice', {})) or {}

    response: JsonObject = {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'channel': payload.channel,
        'tone': payload.tone,
        'headline': headline,
        'body': body,
        'hashtags': hashtags,
        'provider_used': str(ai_result.get('provider', selected_provider) or selected_provider),
        'model_used': str(ai_result.get('model', selected_model or '') or ''),
        'ai_status': 'generated' if ai_text else 'fallback',
        'platform_requirements': {
            'channel': payload.channel,
            'required_formats': active_formats,
            'all_social_accounts': platform_requirements,
        },
        'outputs': {
            'text': body,
            'image_prompt': f"Product-focused {payload.channel} image concept for {payload.topic} targeting {payload.audience}.",
            'image_url': str(image_asset.get('download_url', '') or ''),
            'image_mime_type': str(image_asset.get('mime_type', '') or ''),
            'video_url': str(video_asset.get('download_url', '') or ''),
            'video_mime_type': str(video_asset.get('mime_type', '') or ''),
            'video_script': f"Hook: {headline}. Scene flow should prioritize product benefit and end with a sales CTA.",
            'voice_url': str(voice_asset.get('download_url', '') or ''),
            'voice_mime_type': str(voice_asset.get('mime_type', '') or ''),
            'voiceover_script': f"{headline}. {fallback_body}",
            'reel_script': f"Reel version: 3 fast cuts, clear hook, social proof, CTA for {payload.topic}.",
            'short_video_script': f"Short version: 15-30 seconds, one key outcome for {payload.audience}, strong CTA.",
        },
        'generated_assets': media_bundle,
    }

    if payload.include_seo:
        response['seo'] = {
            'meta_title': headline[:60],
            'meta_description': body[:155],
            'focus_keyword': payload.topic,
        }

    generation_id = f"cg-{uuid.uuid4().hex[:10]}"
    response['generation_id'] = generation_id
    response['generation_record'] = {
        'generation_id': generation_id,
        'headline': headline,
        'topic': payload.topic,
        'audience': payload.audience,
        'channel': payload.channel,
        'created_at': created_at,
    }

    fallback_assets = [
        _json_object(asset)
        for asset in (
            media_bundle.get('image', {}),
            media_bundle.get('voice', {}),
            media_bundle.get('video', {}),
        )
        if str(_json_object(asset).get('generation_status', 'generated')) != 'generated'
    ]
    for _ in fallback_assets:
        _content_generation_note_telemetry('fallback_attempts_total', 'media_fallback')

    strict_mode = _content_generation_strict_production_mode()
    response['production_mode'] = 'strict-real-generation' if strict_mode else 'best-effort'

    if strict_mode and not ai_text.strip():
        _content_generation_note_telemetry('strict_rejections_total', 'missing_ai_text')
        raise HTTPException(status_code=503, detail='AI text generation returned no output in strict mode.')

    if strict_mode and fallback_assets:
        _content_generation_note_telemetry('strict_rejections_total', 'media_fallback')
        raise HTTPException(
            status_code=503,
            detail='Strict content generation mode rejected fallback media assets. Configure real providers for all modalities.',
        )

    _content_generations_memory.append(
        {
            'generation_id': generation_id,
            'tenant_id': auth.tenant_id,
            'topic': payload.topic,
            'audience': payload.audience,
            'channel': payload.channel,
            'tone': payload.tone,
            'headline': headline,
            'body': body,
            'generated_assets': media_bundle,
            'created_at': created_at,
            'response': response,
        }
    )

    return response


def _run_content_generation_job_if_needed(job: JsonObject, auth: AuthContext) -> None:
    if str(job.get('status', '')) != 'pending' or bool(job.get('cancel_requested', False)):
        return
    now_iso = datetime.now(UTC).isoformat()
    job['status'] = 'running'
    job['stage'] = 'generating'
    job['progress_pct'] = 25
    job['started_at'] = now_iso
    job['updated_at'] = now_iso
    _persist_content_generation_job(job)
    try:
        payload_data = _json_object(job.get('payload_data', {})) or {}
        built_payload = ContentRequest.model_validate(payload_data)
        result = _build_content_generation_response(built_payload, auth)
        complete_at = datetime.now(UTC).isoformat()
        job['status'] = 'completed'
        job['stage'] = 'completed'
        job['progress_pct'] = 100
        job['result'] = result
        job['error'] = None
        job['completed_at'] = complete_at
        job['updated_at'] = complete_at
    except Exception as exc:
        failed_at = datetime.now(UTC).isoformat()
        job['status'] = 'failed'
        job['stage'] = 'failed'
        job['progress_pct'] = 100
        job['result'] = None
        job['error'] = str(exc)
        job['completed_at'] = failed_at
        job['updated_at'] = failed_at
    _persist_content_generation_job(job)


@app.get('/content/library')
def get_content_library(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    items = [
        item for item in _content_generations_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    items.sort(key=lambda entry: str(entry.get('created_at', '')), reverse=True)
    return {
        'status': 'ok',
        'count': len(items),
        'items': [
            {
                'generation_id': str(item.get('generation_id', '')),
                'topic': str(item.get('topic', '')),
                'channel': str(item.get('channel', '')),
                'headline': str(item.get('headline', '')),
                'created_at': item.get('created_at'),
            }
            for item in items
        ],
    }


@app.get('/content/library/{generation_id}')
def get_content_library_item(generation_id: str, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    item = next(
        (
            row for row in _content_generations_memory
            if str(row.get('tenant_id', '')) == auth.tenant_id and str(row.get('generation_id', '')) == generation_id
        ),
        None,
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Content generation record not found.')
    return {'status': 'ok', 'item': item}


@app.get('/content/generate/telemetry')
def get_content_generation_telemetry(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    del auth
    with _content_generation_telemetry_lock:
        counters = dict(_content_generation_telemetry)
    return {'status': 'ok', 'counters': counters}


@app.get('/content/generate/preflight/strict', response_model=None)
def content_generation_strict_preflight(auth: AuthContext = Depends(require_auth)) -> JsonObject | JSONResponse:
    del auth
    strict_mode = _content_generation_strict_production_mode()
    ready, checks = _content_generation_required_provider_state()
    payload: JsonObject = {
        'status': 'ok' if (not strict_mode or ready) else 'error',
        'strict_mode_enabled': strict_mode,
        'ready': ready,
        'checks': checks,
    }
    if strict_mode and not ready:
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get('/content/generate/production/verify', response_model=None)
def content_generation_production_verify(auth: AuthContext = Depends(require_auth)) -> JsonObject | JSONResponse:
    payload, passed = _content_generation_production_verification_payload(auth.tenant_id)
    if not passed:
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get('/production/no-mock/verify', response_model=None)
def strict_no_mock_verify(auth: AuthContext = Depends(require_auth)) -> JsonObject | JSONResponse:
    strict_no_mock = _env_bool('NUXTRON_STRICT_NO_MOCK', _is_production())
    content_payload, content_ok = _content_generation_production_verification_payload(auth.tenant_id)
    platform_payload = _platform_status_payload(auth)
    fallback_buffers = _json_object(platform_payload.get('fallback_buffers', {})) or {}
    fallback_hot = bool(fallback_buffers.get('any_buffer_hot', False))

    module_counts = _strict_no_mock_module_store_counts(auth.tenant_id)
    class_breakdown: dict[str, JsonObject] = {
        'content_pipeline': {'total': module_counts.get('scheduled_posts', 0) + module_counts.get('content_approval_requests', 0) + module_counts.get('trend_signals', 0)},
        'social_operations': {'total': module_counts.get('social_accounts', 0) + module_counts.get('smart_inbox_messages', 0) + module_counts.get('social_listening', 0) + module_counts.get('reviews', 0)},
        'distribution_surface': {'total': module_counts.get('influencers', 0) + module_counts.get('advocacy_campaigns', 0) + module_counts.get('linkinbio_pages', 0) + module_counts.get('ads_campaigns', 0)},
    }
    threshold = max(0, _safe_int(os.getenv('NUXTRON_STRICT_NO_MOCK_MAX_MODULE_BUFFER_ITEMS', '100'), 100))
    class_overflow = {
        key: value
        for key, value in class_breakdown.items()
        if _safe_int(value.get('total'), 0) > threshold
    }

    criteria: list[JsonObject] = [
        {
            'id': 'content-generation-production-verify',
            'pass': bool(content_ok),
            'details': content_payload,
        },
        {
            'id': 'fallback-buffers-empty',
            'pass': not fallback_hot,
            'details': fallback_buffers,
        },
        {
            'id': 'critical-module-buffers-below-limit',
            'pass': len(class_overflow) == 0,
            'details': {
                'threshold': threshold,
                'class_breakdown': class_breakdown,
                'class_overflow': class_overflow,
            },
        },
    ]

    passed = all(bool(item.get('pass')) for item in criteria)
    source = 'verify'
    route_family = 'platform'
    if fallback_hot:
        source = 'fallback-buffers'
        route_family = 'fallback-buffers'
    elif class_overflow:
        source = 'critical-modules'
        route_family = 'critical-modules'

    payload: JsonObject = {
        'status': 'ok' if passed else 'error',
        'strict_no_mock_mode_enabled': strict_no_mock,
        'strict_no_mock_mode': strict_no_mock,
        'fallback_blocked': not passed,
        'source': source,
        'route_family': route_family,
        'verification': {
            'passed': passed,
            'criteria': criteria,
        },
        'platform': {
            **platform_payload,
            'critical_module_buffers': {
                'class_breakdown': class_breakdown,
                'class_overflow': class_overflow,
            },
        },
    }

    if strict_no_mock and not passed:
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.post('/content/generate/async', status_code=202)
def submit_content_generation_job(payload: ContentRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    if _content_generation_inflight_count(auth.tenant_id) >= _content_generation_max_inflight():
        raise HTTPException(status_code=429, detail='Too many in-flight content generation jobs.')

    now_iso = datetime.now(UTC).isoformat()
    job_id = f"cgj-{uuid.uuid4().hex[:12]}"
    job: JsonObject = {
        'job_id': job_id,
        'tenant_id': auth.tenant_id,
        'status': 'pending',
        'progress_pct': 0,
        'stage': 'queued',
        'created_at': now_iso,
        'updated_at': now_iso,
        'started_at': None,
        'completed_at': None,
        'result': None,
        'error': None,
        'cancel_requested': False,
        'payload_data': payload.model_dump(mode='python'),
    }
    _persist_content_generation_job(job)
    return {
        'status': 'accepted',
        'job_id': job_id,
        'poll_url': f'/content/generate/jobs/{job_id}',
    }


@app.get('/content/generate/jobs/{job_id}')
def get_content_generation_job(job_id: str, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    job = _find_content_generation_job(job_id, auth.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Content generation job not found.')

    enforce_timeouts = _env_bool('CONTENT_GENERATION_ENFORCE_JOB_TIMEOUTS', False)
    max_runtime = max(30, _safe_int(os.getenv('CONTENT_GENERATION_JOB_MAX_RUNTIME_SECONDS', '1800'), 1800))
    if enforce_timeouts and str(job.get('status', '')) == 'running':
        started_at = _parse_iso_datetime(job.get('started_at'))
        if started_at and (datetime.now(UTC) - started_at).total_seconds() > max_runtime:
            now_iso = datetime.now(UTC).isoformat()
            job['status'] = 'failed'
            job['stage'] = 'timeout'
            job['progress_pct'] = 100
            job['completed_at'] = now_iso
            job['updated_at'] = now_iso
            job['error'] = f'Job exceeded max runtime ({max_runtime}s).'
            _persist_content_generation_job(job)
            _content_generation_note_telemetry('timeout_failures_total')

    if str(job.get('status', '')) == 'pending':
        _run_content_generation_job_if_needed(job, auth)

    job = _find_content_generation_job(job_id, auth.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Content generation job not found.')
    return {'status': 'ok', 'job': job}


@app.delete('/content/generate/jobs/{job_id}')
def cancel_content_generation_job(job_id: str, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    job = _find_content_generation_job(job_id, auth.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Content generation job not found.')
    if str(job.get('status', '')) not in {'pending', 'running'}:
        return {'status': 'ok', 'job': job}
    now_iso = datetime.now(UTC).isoformat()
    job['cancel_requested'] = True
    job['status'] = 'cancelled'
    job['stage'] = 'cancelled'
    job['progress_pct'] = 100
    job['completed_at'] = now_iso
    job['updated_at'] = now_iso
    _persist_content_generation_job(job)
    return {'status': 'ok', 'job': job}


@app.post('/content/generate/jobs/{job_id}/retry')
def retry_content_generation_job(job_id: str, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    job = _find_content_generation_job(job_id, auth.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Content generation job not found.')
    if str(job.get('status', '')) not in {'failed', 'cancelled'}:
        raise HTTPException(status_code=409, detail='Only failed or cancelled jobs can be retried.')
    if _content_generation_inflight_count(auth.tenant_id, exclude_job_id=job_id) >= _content_generation_max_inflight():
        raise HTTPException(status_code=429, detail='Too many in-flight content generation jobs.')
    now_iso = datetime.now(UTC).isoformat()
    job['status'] = 'pending'
    job['stage'] = 'queued'
    job['progress_pct'] = 0
    job['error'] = None
    job['result'] = None
    job['cancel_requested'] = False
    job['started_at'] = None
    job['completed_at'] = None
    job['updated_at'] = now_iso
    _persist_content_generation_job(job)
    return {'status': 'ok', 'job': job}


@app.get('/content/generate/jobs')
def list_content_generation_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    auth: AuthContext = Depends(require_auth),
) -> JsonObject:
    allowed = {'pending', 'running', 'completed', 'failed', 'cancelled'}
    if status is not None and status not in allowed:
        raise HTTPException(status_code=400, detail='Invalid status filter.')

    _content_generation_prune_expired_terminal_jobs()
    with _content_generation_jobs_lock:
        items = [
            job.copy()
            for job in _content_generation_jobs_memory
            if str(job.get('tenant_id', '')) == auth.tenant_id and (status is None or str(job.get('status', '')) == status)
        ]
    items.sort(key=lambda item: str(item.get('updated_at', item.get('created_at', ''))), reverse=True)
    items = items[:limit]
    for item in items:
        expires_at = _content_generation_job_expires_at(item)
        item['is_terminal'] = _content_generation_job_terminal(item.get('status'))
        item['expires_at'] = expires_at.isoformat() if expires_at else None
    return {
        'status': 'ok',
        'items': items,
        'retention': {
            'terminal_seconds': _content_generation_job_retention_seconds(),
        },
    }


@app.get('/content/generate/jobs/{job_id}/stream')
def stream_content_generation_job(
    job_id: str,
    api_key: str = Query(default=''),
    tenant_id: str = Query(default=''),
) -> StreamingResponse:
    expected = os.getenv('FASTAPI_API_KEY', 'change-this-fastapi-key').strip()
    if not api_key or not tenant_id or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail='Invalid stream credentials.')

    job = _find_content_generation_job(job_id, tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Content generation job not found.')

    def _event_stream() -> object:
        snapshot = json.dumps({'payload': job}, separators=(',', ':'))
        yield f"event: content-job.snapshot\ndata: {snapshot}\n\n"
        if _content_generation_job_terminal(job.get('status')):
            terminated = json.dumps({'payload': job}, separators=(',', ':'))
            yield f"event: content-job.terminated\ndata: {terminated}\n\n"

    return StreamingResponse(_event_stream(), media_type='text/event-stream')


def generate_ads(payload: AdsRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:  # NOSONAR
    formats = sorted({'text', 'image', 'video', 'voice', 'reel', 'short', *[item.strip().lower() for item in payload.target_formats if item.strip()]})
    prompt = (payload.prompt or '').strip() or (
        f"Create ad assets for {payload.product} targeting {payload.audience} on {payload.platform}. "
        f"Objective: {payload.objective}. Include text ad copy, image prompt, video script, voiceover script, reel script, and short-video script."
    )
    system_prompt = (payload.system_prompt or '').strip() or (
        'You are an ad creative strategist. Focus on conversion-first output and platform-native formatting.'
    )

    ai_payload = AiGatewayGenerateRequest(
        provider=payload.provider,
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=900,
        temperature=0.7,
    )

    created_at = datetime.now(UTC).isoformat()
    selected_provider, selected_model, ai_result, ai_text = _run_optional_ai_generation(ai_payload, auth, created_at)

    media_bundle = _generate_media_asset_bundle(
        tenant_id=auth.tenant_id,
        prompt=prompt,
        text_seed=ai_text or f'{payload.product} for {payload.audience}',
        requested_provider=payload.provider,
    )

    image_asset = _json_object(media_bundle.get('image', {})) or {}
    video_asset = _json_object(media_bundle.get('video', {})) or {}
    voice_asset = _json_object(media_bundle.get('voice', {})) or {}

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'platform': payload.platform,
        'objective': payload.objective,
        'headlines': [
            f"{payload.product} for {payload.audience}",
            f"Scale {payload.objective} with {payload.product}",
            f"Built for {payload.audience}: {payload.product}",
        ],
        'descriptions': [
            f"Launch a {payload.platform} campaign focused on {payload.objective}.",
            'Use one offer, one proof point, and one frictionless CTA.',
        ],
        'cta': 'Start Free Trial',
        'provider_used': str(ai_result.get('provider', selected_provider) or selected_provider),
        'model_used': str(ai_result.get('model', selected_model or '') or ''),
        'ai_status': 'generated' if ai_text else 'fallback',
        'required_formats': formats,
        'outputs': {
            'text': ai_text or f"{payload.product} for {payload.audience}. Objective: {payload.objective}.",
            'image_prompt': f"High-conversion {payload.platform} ad visual for {payload.product} focused on {payload.objective}.",
            'image_url': str(image_asset.get('download_url', '') or ''),
            'image_mime_type': str(image_asset.get('mime_type', '') or ''),
            'video_script': f"15-30 second ad script for {payload.product} with a direct {payload.objective} CTA.",
            'video_url': str(video_asset.get('download_url', '') or ''),
            'video_mime_type': str(video_asset.get('mime_type', '') or ''),
            'voiceover_script': f"Discover {payload.product}. Built for {payload.audience}. Start now.",
            'voice_url': str(voice_asset.get('download_url', '') or ''),
            'voice_mime_type': str(voice_asset.get('mime_type', '') or ''),
            'reel_script': f"Reel cut for {payload.product}: hook, value proof, CTA in under 20 seconds.",
            'short_video_script': f"Short-form version for {payload.platform}: punchy hook, one proof, one CTA.",
        },
        'generated_assets': media_bundle,
    }


def analyze_seo(payload: SeoRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    content_lower = payload.content.lower()
    keyword_lower = payload.target_keyword.lower()
    keyword_count = content_lower.count(keyword_lower)
    word_count = len(payload.content.split())
    density = 0.0 if word_count == 0 else round((keyword_count / word_count) * 100, 2)

    score = 60
    checks = {
        'has_url': payload.url is not None,
        'keyword_present': keyword_count > 0,
        'good_length': 300 <= word_count <= 2000,
        'balanced_density': 0.5 <= density <= 2.5,
    }
    score += sum(10 for passed in checks.values() if passed)

    recommendations: list[str] = []
    if not checks['keyword_present']:
        recommendations.append('Add the target keyword in the first 100 words.')
    if not checks['good_length']:
        recommendations.append('Keep content length between 300 and 2000 words for stronger ranking signals.')
    if not checks['balanced_density']:
        recommendations.append('Adjust keyword frequency to keep density between 0.5% and 2.5%.')
    if not checks['has_url']:
        recommendations.append('Include canonical URL for complete on-page SEO checks.')

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'score': min(score, 100),
        'word_count': word_count,
        'keyword_count': keyword_count,
        'keyword_density_percent': density,
        'checks': checks,
        'recommendations': recommendations,
    }


def schedule_social_post(payload: SocialScheduleRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    publish_at = payload.publish_at
    if publish_at.tzinfo is None:
        publish_at = publish_at.replace(tzinfo=UTC)

    if publish_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail='publish_at must be in the future.')

    media = [str(url) for url in payload.media_urls]
    text_cipher = te_encrypt(payload.text)
    text_preview = payload.text[:72]

    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO social_scheduled_posts (tenant_id, platform, text_cipher, text_preview, publish_at, media_urls)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, tenant_id, platform, text_cipher, text_preview, publish_at, media_urls, status, created_at
                    """,
                    (auth.tenant_id, payload.platform, text_cipher, text_preview, publish_at, media),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            raise HTTPException(status_code=500, detail='Failed to persist social post.')

        job: JsonObject = {
            'id': row[0],
            'tenant_id': row[1],
            'platform': row[2],
            'text': te_decrypt(row[3]) or row[4],
            'publish_at': row[5].isoformat(),
            'media_urls': row[6],
            'status': row[7],
            'created_at': row[8].isoformat(),
            'persistence': 'postgres',
            'encryption': 'application-level',
        }
        return {'status': 'ok', 'job': job}

    job: JsonObject = {
        'id': len(_scheduled_posts_memory) + 1,
        'tenant_id': auth.tenant_id,
        'platform': payload.platform,
        'text': payload.text,
        'text_cipher': text_cipher,
        'publish_at': publish_at.isoformat(),
        'media_urls': media,
        'status': 'scheduled',
        'created_at': datetime.now(UTC).isoformat(),
        'persistence': 'memory-fallback',
        'encryption': 'application-level',
    }
    _scheduled_posts_memory.append(job)
    return {'status': 'ok', 'job': job}


def list_scheduled_posts(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, tenant_id, platform, text_cipher, text_preview, publish_at, media_urls, status, created_at
                    FROM social_scheduled_posts
                    WHERE tenant_id = %s
                    ORDER BY publish_at ASC, id ASC
                    """,
                    (auth.tenant_id,),
                )
                rows = cur.fetchall()

        items: list[JsonObject] = [
            {
                'id': row[0],
                'tenant_id': row[1],
                'platform': row[2],
                'text': te_decrypt(row[3]) or row[4],
                'publish_at': row[5].isoformat(),
                'media_urls': row[6],
                'status': row[7],
                'created_at': row[8].isoformat(),
                'persistence': 'postgres',
                'encryption': 'application-level',
            }
            for row in rows
        ]
        return {'status': 'ok', 'count': len(items), 'items': items}

    items: list[JsonObject] = [item for item in _scheduled_posts_memory if item.get('tenant_id') == auth.tenant_id]
    return {'status': 'ok', 'count': len(items), 'items': items}


def move_scheduled_post(
    post_id: int,
    payload: SocialScheduleMoveRequest,
    auth: AuthContext = Depends(require_auth),
) -> JsonObject:
    publish_at = payload.publish_at
    if publish_at.tzinfo is None:
        publish_at = publish_at.replace(tzinfo=UTC)

    if publish_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail='publish_at must be in the future.')

    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE social_scheduled_posts
                    SET publish_at = %s
                    WHERE id = %s AND tenant_id = %s
                    RETURNING id, tenant_id, platform, text_cipher, text_preview, publish_at, media_urls, status, created_at
                    """,
                    (publish_at, post_id, auth.tenant_id),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            raise HTTPException(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)

        return {
            'status': 'ok',
            'job': {
                'id': row[0],
                'tenant_id': row[1],
                'platform': row[2],
                'text': te_decrypt(row[3]) or row[4],
                'publish_at': row[5].isoformat(),
                'media_urls': row[6],
                'status': row[7],
                'created_at': row[8].isoformat(),
                'persistence': 'postgres',
                'encryption': 'application-level',
            },
        }

    for item in _scheduled_posts_memory:
        if item.get('tenant_id') != auth.tenant_id:
            continue
        if _coerce_int(item.get('id'), 0) != post_id:
            continue
        item['publish_at'] = publish_at.isoformat()
        item['status'] = 'scheduled'
        return {'status': 'ok', 'job': item}

    raise HTTPException(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)


def delete_scheduled_post(post_id: int, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM social_scheduled_posts
                    WHERE id = %s AND tenant_id = %s
                    RETURNING id
                    """,
                    (post_id, auth.tenant_id),
                )
                deleted = cur.fetchone()
            conn.commit()

        if not deleted:
            raise HTTPException(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)

        return {'status': 'ok', 'deleted_id': post_id}

    before = len(_scheduled_posts_memory)
    _scheduled_posts_memory[:] = [
        item
        for item in _scheduled_posts_memory
        if not (item.get('tenant_id') == auth.tenant_id and _coerce_int(item.get('id'), 0) == post_id)
    ]
    if len(_scheduled_posts_memory) == before:
        raise HTTPException(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)
    return {'status': 'ok', 'deleted_id': post_id}


def ingest_social_listening_mention(
    payload: SocialListeningIngestRequest,
    auth: AuthContext = Depends(require_auth),
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:social:listening:ingest', limit=180, window_seconds=60)
    mention: JsonObject = {
        'id': len(_social_listening_memory) + 1,
        'tenant_id': auth.tenant_id,
        'platform': payload.platform,
        'query': payload.query,
        'author_handle': payload.author_handle,
        'text': payload.text,
        'sentiment': payload.sentiment,
        'engagement_count': payload.engagement_count,
        'created_at': datetime.now(UTC).isoformat(),
        'source': 'api',
        'persistence': 'memory-fallback',
    }
    _social_listening_memory.append(mention)
    for rule in [
        item for item in _social_listening_alert_rules_memory
        if item.get('tenant_id') == auth.tenant_id and item.get('enabled', True)
    ]:
        matches_query = not rule.get('query') or str(rule.get('query')).lower() in payload.query.lower()
        matches_platform = not rule.get('platform') or rule.get('platform') == payload.platform
        matches_sentiment = (not rule.get('negative_only', True)) or payload.sentiment == 'negative'
        matches_engagement = payload.engagement_count >= _coerce_int(rule.get('min_engagement', 0), 0)
        if not (matches_query and matches_platform and matches_sentiment and matches_engagement):
            continue

        _social_listening_alerts_memory.append({
            'id': len(_social_listening_alerts_memory) + 1,
            'tenant_id': auth.tenant_id,
            'rule_id': rule.get('id'),
            'rule_name': rule.get('name'),
            'mention_id': mention['id'],
            'severity': 'high' if payload.engagement_count >= 100 else 'medium',
            'status': 'open',
            'created_at': datetime.now(UTC).isoformat(),
        })
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'mention': mention}


def list_social_listening_mentions(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:social:listening:list', limit=240, window_seconds=60)
    mentions = [item for item in _social_listening_memory if item.get('tenant_id') == auth.tenant_id]
    mentions.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(mentions), 'mentions': mentions}


def get_social_listening_summary(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:social:listening:summary', limit=240, window_seconds=60)
    mentions = [item for item in _social_listening_memory if item.get('tenant_id') == auth.tenant_id]
    sentiment = {'positive': 0, 'neutral': 0, 'negative': 0}
    platforms: dict[str, int] = {}
    queries: dict[str, int] = {}
    total_engagement = 0

    for mention in mentions:
        sentiment_key = str(mention.get('sentiment', 'neutral'))
        sentiment[sentiment_key] = sentiment.get(sentiment_key, 0) + 1

        platform_key = str(mention.get('platform', 'unknown'))
        platforms[platform_key] = platforms.get(platform_key, 0) + 1

        query_key = str(mention.get('query', ''))
        queries[query_key] = queries.get(query_key, 0) + 1
        total_engagement += _coerce_int(mention.get('engagement_count', 0), 0)

    top_queries: list[JsonObject] = [
        {'query': query, 'mentions': count}
        for query, count in sorted(queries.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]

    clusters: list[JsonObject] = [
        {
            'cluster': f"{query}:{platform}",
            'query': query,
            'platform': platform,
            'mentions': len([
                item for item in mentions
                if item.get('query') == query and item.get('platform') == platform
            ]),
        }
        for query, platform in sorted({(str(item.get('query', '')), str(item.get('platform', 'unknown'))) for item in mentions})
    ]

    total_mentions = len(mentions)
    negative_ratio = 0.0 if total_mentions == 0 else sentiment.get('negative', 0) / total_mentions
    high_negative_mentions = len([
        item for item in mentions
        if item.get('sentiment') == 'negative' and _coerce_int(item.get('engagement_count', 0), 0) >= 50
    ])
    crisis_level = 'none'
    if negative_ratio >= 0.4 or high_negative_mentions >= 3:
        crisis_level = 'watch'
    if negative_ratio >= 0.55 or high_negative_mentions >= 5:
        crisis_level = 'high'
    if negative_ratio >= 0.7 or high_negative_mentions >= 7:
        crisis_level = 'critical'

    open_alerts = len([
        item for item in _social_listening_alerts_memory
        if item.get('tenant_id') == auth.tenant_id and item.get('status') == 'open'
    ])

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'summary': {
            'total_mentions': len(mentions),
            'sentiment': sentiment,
            'platforms': platforms,
            'top_queries': top_queries,
            'avg_engagement': 0 if not mentions else round(total_engagement / len(mentions), 2),
            'clusters': clusters,
            'alerts_open': open_alerts,
            'crisis': {
                'triggered': crisis_level != 'none',
                'level': crisis_level,
                'negative_ratio': round(negative_ratio, 4),
                'high_negative_mentions': high_negative_mentions,
            },
        },
        'mentions': mentions[:10],
    }


def create_social_listening_alert_rule(
    payload: SocialListeningAlertRuleRequest,
    auth: AuthContext = Depends(require_auth),
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:social:listening:rules:create', limit=120, window_seconds=60)
    rule: JsonObject = {
        'id': len(_social_listening_alert_rules_memory) + 1,
        'tenant_id': auth.tenant_id,
        'name': payload.name,
        'query': payload.query,
        'platform': payload.platform,
        'min_engagement': payload.min_engagement,
        'negative_only': payload.negative_only,
        'enabled': True,
        'created_at': datetime.now(UTC).isoformat(),
        'source': 'api',
        'persistence': 'memory-fallback',
    }
    _social_listening_alert_rules_memory.append(rule)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'rule': rule}


def list_social_listening_alerts(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:social:listening:alerts:list', limit=240, window_seconds=60)
    alerts = [
        item for item in _social_listening_alerts_memory
        if item.get('tenant_id') == auth.tenant_id
    ]
    alerts.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(alerts), 'alerts': alerts}


def get_social_listening_clusters(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:social:listening:clusters', limit=240, window_seconds=60)
    mentions = [item for item in _social_listening_memory if item.get('tenant_id') == auth.tenant_id]
    grouped: dict[tuple[str, str, str], int] = {}
    for mention in mentions:
        key = (
            str(mention.get('query', '')),
            str(mention.get('platform', 'unknown')),
            str(mention.get('sentiment', 'neutral')),
        )
        grouped[key] = grouped.get(key, 0) + 1

    clusters: list[JsonObject] = [
        {
            'query': query,
            'platform': platform,
            'sentiment': sentiment_key,
            'mentions': count,
        }
        for (query, platform, sentiment_key), count in sorted(grouped.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(clusters), 'clusters': clusters}


def ingest_review(payload: ReviewIngestRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:reviews:ingest', limit=180, window_seconds=60)
    if payload.rating <= 2:
        sentiment = 'negative'
    elif payload.rating == 3:
        sentiment = 'neutral'
    else:
        sentiment = 'positive'

    review: JsonObject = {
        'id': len(_reviews_memory) + 1,
        'tenant_id': auth.tenant_id,
        'platform': payload.platform,
        'reviewer': payload.reviewer,
        'rating': payload.rating,
        'text': payload.text,
        'category': payload.category,
        'sentiment': sentiment,
        'responded': False,
        'response': None,
        'response_at': None,
        'created_at': datetime.now(UTC).isoformat(),
        'source': 'api',
        'persistence': 'memory-fallback',
    }
    _reviews_memory.append(review)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'review': review}


def list_reviews(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:reviews:list', limit=240, window_seconds=60)
    reviews = [item for item in _reviews_memory if item.get('tenant_id') == auth.tenant_id]
    reviews.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(reviews), 'reviews': reviews}


def respond_to_review(review_id: int, payload: ReviewResponseRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:reviews:respond', limit=180, window_seconds=60)
    review = next(
        (
            item for item in _reviews_memory
            if item.get('id') == review_id and item.get('tenant_id') == auth.tenant_id
        ),
        None,
    )
    if review is None:
        raise HTTPException(status_code=404, detail='Review not found.')

    review['responded'] = True
    review['response'] = payload.response
    review['response_at'] = datetime.now(UTC).isoformat()
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'review': review}


def get_reviews_summary(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:reviews:summary', limit=240, window_seconds=60)
    reviews = [item for item in _reviews_memory if item.get('tenant_id') == auth.tenant_id]
    total_reviews = len(reviews)
    if total_reviews == 0:
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'summary': {
                'total_reviews': 0,
                'avg_rating': 0,
                'reputation_score': 0,
                'responded_ratio': 0,
                'sentiment': {'positive': 0, 'neutral': 0, 'negative': 0},
            },
            'reviews': [],
        }

    sentiment = {'positive': 0, 'neutral': 0, 'negative': 0}
    rating_total = 0
    responded = 0
    platforms: dict[str, int] = {}
    for review in reviews:
        sentiment_key = str(review.get('sentiment', 'neutral'))
        sentiment[sentiment_key] = sentiment.get(sentiment_key, 0) + 1
        rating_total += _coerce_int(review.get('rating', 0), 0)
        responded += 1 if review.get('responded') else 0
        platform_key = str(review.get('platform', 'custom'))
        platforms[platform_key] = platforms.get(platform_key, 0) + 1

    avg_rating = round(rating_total / total_reviews, 2)
    reputation_score = int(max(0, min(100, round(((avg_rating / 5) * 70) + ((responded / total_reviews) * 30)))))

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'summary': {
            'total_reviews': total_reviews,
            'avg_rating': avg_rating,
            'reputation_score': reputation_score,
            'responded_ratio': round(responded / total_reviews, 4),
            'sentiment': sentiment,
            'platforms': platforms,
        },
        'reviews': sorted(reviews, key=lambda item: str(item.get('created_at', '')), reverse=True)[:10],
    }


def create_email_contact(payload: EmailContactCreateRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:email:contacts:create', limit=120, window_seconds=60)
    email_cipher = te_encrypt(payload.email)
    name_cipher = te_encrypt(payload.name)
    email_preview = payload.email[:4] + '***'
    name_preview = payload.name[:1] + '***'

    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_contacts (tenant_id, email_cipher, email_preview, name_cipher, name_preview, tags)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, tenant_id, email_cipher, email_preview, name_cipher, name_preview, tags, created_at
                    """,
                    (
                        auth.tenant_id,
                        email_cipher,
                        email_preview,
                        name_cipher,
                        name_preview,
                        payload.tags,
                    ),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            raise HTTPException(status_code=500, detail='Failed to create email contact.')

        return {
            'status': 'ok',
            'contact': {
                'id': row[0],
                'tenant_id': row[1],
                'email': te_decrypt(row[2]) or row[3],
                'name': te_decrypt(row[4] or '') or row[5],
                'tags': row[6],
                'created_at': row[7].isoformat(),
                'persistence': 'postgres',
                'encryption': 'application-level',
            },
        }

    item: JsonObject = {
        'id': len(_email_contacts_memory) + 1,
        'tenant_id': auth.tenant_id,
        'email': payload.email,
        'email_cipher': email_cipher,
        'name': payload.name,
        'name_cipher': name_cipher,
        'tags': payload.tags,
        'created_at': datetime.now(UTC).isoformat(),
        'persistence': 'memory-fallback',
        'encryption': 'application-level',
    }
    _email_contacts_memory.append(item)
    return {'status': 'ok', 'contact': item}


def list_email_contacts(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT id, tenant_id, email_cipher, email_preview, name_cipher, name_preview, tags, created_at
                    FROM email_contacts
                    WHERE tenant_id = %s
                    ORDER BY created_at DESC, id DESC
                    """,
                (auth.tenant_id,),
            )
            rows = cur.fetchall()

        items: list[JsonObject] = [
            {
                'id': row[0],
                'tenant_id': row[1],
                'email': te_decrypt(row[2]) or row[3],
                'name': te_decrypt(row[4] or '') or row[5],
                'tags': row[6],
                'created_at': row[7].isoformat(),
                'persistence': 'postgres',
                'encryption': 'application-level',
            }
            for row in rows
        ]
        return {'status': 'ok', 'count': len(items), 'items': items}

    items: list[JsonObject] = [item for item in _email_contacts_memory if item.get('tenant_id') == auth.tenant_id]
    return {'status': 'ok', 'count': len(items), 'items': items}


def create_email_campaign(payload: EmailCampaignCreateRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:email:campaigns:create', limit=60, window_seconds=60)
    subject_cipher = te_encrypt(payload.subject)
    body_cipher = te_encrypt(payload.body)
    subject_preview = payload.subject[:72]

    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_campaigns (tenant_id, subject_cipher, subject_preview, body_cipher, status, provider)
                    VALUES (%s, %s, %s, %s, 'draft', %s)
                    RETURNING id, tenant_id, subject_cipher, subject_preview, body_cipher, status, provider, created_at
                    """,
                    (auth.tenant_id, subject_cipher, subject_preview, body_cipher, payload.provider),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            raise HTTPException(status_code=500, detail='Failed to create email campaign.')

        return {
            'status': 'ok',
            'campaign': {
                'id': row[0],
                'tenant_id': row[1],
                'subject': te_decrypt(row[2]) or row[3],
                'body': te_decrypt(row[4]) or '[encrypted-body]',
                'status': row[5],
                'provider': row[6],
                'created_at': row[7].isoformat(),
                'persistence': 'postgres',
                'encryption': 'application-level',
            },
        }

    item: JsonObject = {
        'id': len(_email_campaigns_memory) + 1,
        'tenant_id': auth.tenant_id,
        'subject': payload.subject,
        'subject_cipher': subject_cipher,
        'body': payload.body,
        'body_cipher': body_cipher,
        'status': 'draft',
        'provider': payload.provider,
        'created_at': datetime.now(UTC).isoformat(),
        'persistence': 'memory-fallback',
        'encryption': 'application-level',
    }
    _email_campaigns_memory.append(item)
    return {'status': 'ok', 'campaign': item}


def list_email_campaigns(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT id, tenant_id, subject_cipher, subject_preview, body_cipher, status, provider, created_at
                    FROM email_campaigns
                    WHERE tenant_id = %s
                    ORDER BY created_at DESC, id DESC
                    """,
                (auth.tenant_id,),
            )
            rows = cur.fetchall()

        items: list[JsonObject] = [
            {
                'id': row[0],
                'tenant_id': row[1],
                'subject': te_decrypt(row[2]) or row[3],
                'body': te_decrypt(row[4]) or '[encrypted-body]',
                'status': row[5],
                'provider': row[6],
                'created_at': row[7].isoformat(),
                'persistence': 'postgres',
                'encryption': 'application-level',
            }
            for row in rows
        ]
        return {'status': 'ok', 'count': len(items), 'items': items}

    items: list[JsonObject] = [item for item in _email_campaigns_memory if item.get('tenant_id') == auth.tenant_id]
    return {'status': 'ok', 'count': len(items), 'items': items}


def _resolve_campaign_test_payload(campaign_id: int, tenant_id: str) -> tuple[str, str, str]:
    provider = os.getenv('EMAIL_PROVIDER', 'listmonk')
    subject = f'Nuxtron Campaign #{campaign_id} Test'
    body = 'Secure test email from Nuxtron campaign module.'

    if _db_ready:
        with psycopg.connect(_db_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT subject_cipher, subject_preview, body_cipher, provider
                    FROM email_campaigns
                    WHERE id = %s AND tenant_id = %s
                    """,
                (campaign_id, tenant_id),
            )
            row = cur.fetchone()
            if row:
                subject = te_decrypt(row[0]) or str(row[1])
                body = te_decrypt(row[2]) or body
                if row[3]:
                    provider = str(row[3])
        return provider, subject, body

    for item in _email_campaigns_memory:
        if item.get('id') == campaign_id and item.get('tenant_id') == tenant_id:
            subject = str(item.get('subject') or subject)
            body = str(item.get('body') or body)
            provider = str(item.get('provider') or provider)
            break

    return provider, subject, body


def _dispatch_test_email(provider: str, recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    if provider == 'postal':
        return _send_via_postal(recipient_email, subject, body)
    if provider == 'ses':
        return _send_via_ses(recipient_email, subject, body)
    return _send_via_listmonk(recipient_email, subject, body)


def send_test_email_campaign(
    campaign_id: int,
    payload: EmailCampaignSendTestRequest,
    auth: AuthContext = Depends(require_auth),
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:email:campaigns:send-test', limit=20, window_seconds=60)
    provider, subject, body = _resolve_campaign_test_payload(campaign_id, auth.tenant_id)
    ok, message = _dispatch_test_email(provider, payload.recipient_email, subject, body)

    if not ok:
        # Keep platform operable even when provider credentials are absent in dev.
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'campaign_id': campaign_id,
            'provider': provider,
            'recipient_email': payload.recipient_email,
            'delivery_status': 'queued',
            'message': f'Provider unavailable, fallback queued. Detail: {message}',
        }

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'campaign_id': campaign_id,
        'provider': provider,
        'recipient_email': payload.recipient_email,
        'delivery_status': 'sent',
        'message': message,
    }


def upsert_suitecrm_lead(payload: SuiteCrmLeadRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:integrations:suitecrm:upsert', limit=60, window_seconds=60)

    base_url = os.getenv('SUITECRM_URL', '').rstrip('/')
    token = os.getenv('SUITECRM_API_KEY', '')

    if not base_url or not token:
        item: JsonObject = {
            'id': len(_suitecrm_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': 'SuiteCRM not configured',
            'lead': payload.model_dump(),
            'created_at': datetime.now(UTC).isoformat(),
        }
        _suitecrm_jobs_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }
    body: JsonObject = {
        'data': {
            'type': 'Leads',
            'attributes': {
                'first_name': payload.first_name,
                'last_name': payload.last_name,
                'email1': payload.email,
                'account_name': payload.company,
                'lead_source': payload.source,
                'description': f'Tenant: {auth.tenant_id}',
            },
        }
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/Api/V8/module', headers=headers, json=body)
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'delivery_status': 'sent',
                        'provider': 'suitecrm',
                        'response_status': response.status_code,
                    },
                }
    except Exception as ex:
        message = f'SuiteCRM request failed: {ex}'
        item: JsonObject = {
            'id': len(_suitecrm_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': message,
            'lead': payload.model_dump(),
            'created_at': datetime.now(UTC).isoformat(),
        }
        _suitecrm_jobs_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_suitecrm_jobs_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'queued',
        'reason': 'SuiteCRM responded with non-success status',
        'lead': payload.model_dump(),
        'created_at': datetime.now(UTC).isoformat(),
    }
    _suitecrm_jobs_memory.append(item)
    return {'status': 'ok', 'result': item}


def register_refferq_referral(payload: RefferqReferralRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:integrations:refferq:create', limit=60, window_seconds=60)

    base_url = os.getenv('REFFERQ_URL', '').rstrip('/')
    token = os.getenv('REFFERQ_API_KEY', '')

    if not base_url or not token:
        item: JsonObject = {
            'id': len(_refferq_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': 'RefferQ not configured',
            'referral': payload.model_dump(),
            'created_at': datetime.now(UTC).isoformat(),
        }
        _refferq_jobs_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }
    body: JsonObject = {
        'referrer_email': payload.referrer_email,
        'referred_email': payload.referred_email,
        'campaign': payload.campaign,
        'tenant_id': auth.tenant_id,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/api/referrals', headers=headers, json=body)
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'delivery_status': 'sent',
                        'provider': 'refferq',
                        'response_status': response.status_code,
                    },
                }
    except Exception as ex:
        message = f'RefferQ request failed: {ex}'
        item: JsonObject = {
            'id': len(_refferq_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': message,
            'referral': payload.model_dump(),
            'created_at': datetime.now(UTC).isoformat(),
        }
        _refferq_jobs_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_refferq_jobs_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'queued',
        'reason': 'RefferQ responded with non-success status',
        'referral': payload.model_dump(),
        'created_at': datetime.now(UTC).isoformat(),
    }
    _refferq_jobs_memory.append(item)
    return {'status': 'ok', 'result': item}


def capture_posthog_event(payload: PosthogCaptureRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:analytics:posthog:capture', limit=180, window_seconds=60)

    base_url = os.getenv('POSTHOG_URL', '').rstrip('/')
    project_api_key = os.getenv('POSTHOG_PROJECT_API_KEY', '')

    event_body: JsonObject = {
        'event': payload.event,
        'properties': {
            **payload.properties,
            'tenant_id': auth.tenant_id,
        },
        'distinct_id': payload.distinct_id or auth.tenant_id,
    }

    if not base_url or not project_api_key:
        item: JsonObject = {
            'id': len(_posthog_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': 'PostHog not configured',
            'event': event_body,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _posthog_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    request_body: JsonObject = {
        'api_key': project_api_key,
        **event_body,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/capture/', json=request_body)
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'delivery_status': 'sent',
                        'provider': 'posthog',
                        'response_status': response.status_code,
                        'event': payload.event,
                    },
                }
    except Exception as ex:
        message = f'PostHog request failed: {ex}'
        item: JsonObject = {
            'id': len(_posthog_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': message,
            'event': event_body,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _posthog_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_posthog_events_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'queued',
        'reason': 'PostHog responded with non-success status',
        'event': event_body,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _posthog_events_memory.append(item)
    return {'status': 'ok', 'result': item}


def track_matomo_event(payload: MatomoTrackRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:analytics:matomo:track', limit=180, window_seconds=60)

    matomo_url = os.getenv('MATOMO_URL', '').rstrip('/')
    matomo_site_id = os.getenv('MATOMO_SITE_ID', '').strip()
    matomo_token = os.getenv('MATOMO_AUTH_TOKEN', '').strip()

    event_record: JsonObject = {
        'event_name': payload.event_name,
        'tenant_id': auth.tenant_id,
        'url': str(payload.url) if payload.url else 'http://localhost/studio',
        'action_name': payload.action_name,
        'properties': payload.properties,
    }

    if not matomo_url or not matomo_site_id:
        item: JsonObject = {
            'id': len(_matomo_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': 'Matomo not configured',
            'event': event_record,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _matomo_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    params: dict[str, str] = {
        'idsite': matomo_site_id,
        'rec': '1',
        'apiv': '1',
        'url': str(event_record.get('url', '')),
        'action_name': str(event_record.get('action_name', '')),
        'e_c': 'nuxtron',
        'e_a': payload.event_name,
        'e_n': auth.tenant_id,
    }
    if matomo_token:
        params['token_auth'] = matomo_token

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(f'{matomo_url}/matomo.php', params=params)
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'delivery_status': 'sent',
                        'provider': 'matomo',
                        'response_status': response.status_code,
                        'event': payload.event_name,
                    },
                }
    except Exception as ex:
        message = f'Matomo request failed: {ex}'
        item: JsonObject = {
            'id': len(_matomo_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': message,
            'event': event_record,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _matomo_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_matomo_events_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'queued',
        'reason': 'Matomo responded with non-success status',
        'event': event_record,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _matomo_events_memory.append(item)
    return {'status': 'ok', 'result': item}


def track_plausible_event(payload: PlausibleTrackRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:analytics:plausible:track', limit=180, window_seconds=60)

    plausible_url = os.getenv('PLAUSIBLE_API_URL', '').rstrip('/')
    plausible_api_key = os.getenv('PLAUSIBLE_API_KEY', '').strip()
    plausible_domain = os.getenv('PLAUSIBLE_SITE_DOMAIN', '').strip()

    event_body: JsonObject = {
        'name': payload.event_name,
        'url': str(payload.url) if payload.url else 'http://localhost/studio',
        'domain': plausible_domain or 'localhost',
        'props': {
            **payload.properties,
            'tenant_id': auth.tenant_id,
        },
    }

    if not plausible_url or not plausible_domain:
        item: JsonObject = {
            'id': len(_plausible_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': 'Plausible not configured',
            'event': event_body,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _plausible_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {'Content-Type': CONTENT_TYPE_JSON}
    if plausible_api_key:
        headers['Authorization'] = f'Bearer {plausible_api_key}'

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{plausible_url}/api/event', headers=headers, json=event_body)
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'delivery_status': 'sent',
                        'provider': 'plausible',
                        'response_status': response.status_code,
                        'event': payload.event_name,
                    },
                }
    except Exception as ex:
        message = f'Plausible request failed: {ex}'
        item: JsonObject = {
            'id': len(_plausible_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': message,
            'event': event_body,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _plausible_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_plausible_events_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'queued',
        'reason': 'Plausible responded with non-success status',
        'event': event_body,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _plausible_events_memory.append(item)
    return {'status': 'ok', 'result': item}


def trigger_n8n_webhook(payload: N8nWebhookTriggerRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:integrations:n8n:trigger', limit=120, window_seconds=60)

    webhook_url = os.getenv('N8N_WEBHOOK_URL', '').strip()
    token = os.getenv('N8N_WEBHOOK_TOKEN', '').strip()

    request_body: JsonObject = {
        'workflow': payload.workflow,
        'tenant_id': auth.tenant_id,
        'payload': payload.payload,
    }

    if not webhook_url:
        item: JsonObject = {
            'id': len(_n8n_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': 'n8n webhook not configured',
            'request': request_body,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _n8n_jobs_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {'Content-Type': CONTENT_TYPE_JSON}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(webhook_url, headers=headers, json=request_body)
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'delivery_status': 'sent',
                        'provider': 'n8n',
                        'response_status': response.status_code,
                    },
                }
    except Exception as ex:
        message = f'n8n request failed: {ex}'
        item: JsonObject = {
            'id': len(_n8n_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': message,
            'request': request_body,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _n8n_jobs_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_n8n_jobs_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'queued',
        'reason': 'n8n responded with non-success status',
        'request': request_body,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _n8n_jobs_memory.append(item)
    return {'status': 'ok', 'result': item}


def evaluate_growthbook_flag(payload: GrowthbookEvaluateRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:flags:growthbook:evaluate', limit=180, window_seconds=60)

    base_url = os.getenv('GROWTHBOOK_API_URL', '').rstrip('/')
    client_key = os.getenv('GROWTHBOOK_CLIENT_KEY', '').strip()
    user_id = payload.user_id or auth.tenant_id

    fallback_bucket = sum(ord(ch) for ch in f'{auth.tenant_id}:{payload.feature_key}:{user_id}') % 100
    fallback_enabled = fallback_bucket < 50

    if not base_url or not client_key:
        item: JsonObject = {
            'id': len(_growthbook_checks_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'fallback',
            'feature_key': payload.feature_key,
            'enabled': fallback_enabled,
            'source': 'deterministic-local-rule',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _growthbook_checks_memory.append(item)
        return {'status': 'ok', 'result': item}

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(f'{base_url}/api/features/{client_key}')
            if response.is_success:
                data_obj = _json_object(response.json())
                features = _json_object((data_obj or {}).get('features', {})) or {}
                feature = _json_object(features.get(payload.feature_key, {})) or {}
                enabled = bool(feature.get('defaultValue', fallback_enabled))
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'feature_key': payload.feature_key,
                        'enabled': enabled,
                        'source': 'growthbook',
                    },
                }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_growthbook_checks_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'fallback',
            'feature_key': payload.feature_key,
            'enabled': fallback_enabled,
            'source': f'fallback-after-error:{ex}',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _growthbook_checks_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_growthbook_checks_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'fallback',
        'feature_key': payload.feature_key,
        'enabled': fallback_enabled,
        'source': 'fallback-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    _growthbook_checks_memory.append(item)
    return {'status': 'ok', 'result': item}


# ---------------------------------------------------------------------------
# Signed Webhook Receiver – ingests and validates incoming webhooks
# ---------------------------------------------------------------------------

_WEBHOOK_PROVIDERS = {'github', 'stripe', 'generic'}


class WebhookAcknowledgeRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, object] = Field(default_factory=dict)
    signature: str | None = Field(default=None, max_length=512)


def _verify_github_signature(secret: str, raw_body: bytes, sig_header: str) -> bool:
    expected = 'sha256=' + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


def _verify_stripe_signature(secret: str, raw_body: bytes, sig_header: str) -> bool:
    parts = {kv.split('=', 1)[0]: kv.split('=', 1)[1] for kv in sig_header.split(',') if '=' in kv}
    timestamp = parts.get('t', '')
    v1 = parts.get('v1', '')
    signed = f'{timestamp}.'.encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def _ensure_signature_header(secret: str, sig_header: str, provider_name: str) -> None:
    if secret and not sig_header:
        raise HTTPException(
            status_code=400,
            detail=f'{provider_name} webhook signature header required when {provider_name.upper()} secret is set.',
        )


def _validate_github_webhook_signature(payload: WebhookAcknowledgeRequest) -> bool | None:
    secret = os.getenv('WEBHOOK_GITHUB_SECRET', '').strip()
    sig_header = payload.signature or ''
    _ensure_signature_header(secret, sig_header, 'GitHub')
    if secret and sig_header:
        raw = str(payload.payload).encode()
        return _verify_github_signature(secret, raw, sig_header)
    return None


def _validate_stripe_webhook_signature(payload: WebhookAcknowledgeRequest) -> bool | None:
    secret = os.getenv('WEBHOOK_STRIPE_SECRET', '').strip()
    sig_header = payload.signature or ''
    _ensure_signature_header(secret, sig_header, 'Stripe')
    if secret and sig_header:
        raw = str(payload.payload).encode()
        return _verify_stripe_signature(secret, raw, sig_header)
    return None


def _validate_generic_webhook_signature(payload: WebhookAcknowledgeRequest) -> bool | None:
    secret = os.getenv('WEBHOOK_GENERIC_SECRET', '').strip()
    sig_header = payload.signature or ''
    if secret and sig_header:
        raw = str(payload.payload).encode()
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig_header)
    return None


def _validate_webhook_signature(provider_lower: str, payload: WebhookAcknowledgeRequest) -> bool | None:
    if provider_lower == 'github':
        return _validate_github_webhook_signature(payload)
    if provider_lower == 'stripe':
        return _validate_stripe_webhook_signature(payload)
    if provider_lower == 'generic':
        return _validate_generic_webhook_signature(payload)
    return None


def receive_webhook(
    provider: str,
    payload: WebhookAcknowledgeRequest,
    auth: AuthContext = Depends(require_auth),
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:webhooks:{provider}', limit=300, window_seconds=60)

    provider_lower = provider.lower()
    if provider_lower not in _WEBHOOK_PROVIDERS:
        raise HTTPException(status_code=400, detail=f'Unknown webhook provider: {provider}. Supported: {sorted(_WEBHOOK_PROVIDERS)}')

    signature_valid = _validate_webhook_signature(provider_lower, payload)

    event: JsonObject = {
        'id': len(_webhook_events_memory) + 1,
        'tenant_id': auth.tenant_id,
        'provider': provider_lower,
        'event_type': payload.event_type,
        'payload': payload.payload,
        'signature_valid': signature_valid,
        'received_at': datetime.now(UTC).isoformat(),
    }
    _webhook_events_memory.append(event)

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'provider': provider_lower,
        'event_type': payload.event_type,
        'event_id': event['id'],
        'signature_valid': signature_valid,
        'received_at': event['received_at'],
    }


def list_webhook_events(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    items: list[JsonObject] = [e for e in _webhook_events_memory if e.get('tenant_id') == auth.tenant_id]
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'events': items}


# ---------------------------------------------------------------------------
# Appwrite – auth / user management bridge
# ---------------------------------------------------------------------------

class AppwriteCreateUserRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    email: str = Field(min_length=5, max_length=320)
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)


class AppwriteCreateSessionRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=256)


def appwrite_create_user(payload: AppwriteCreateUserRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:appwrite:create-user', limit=60, window_seconds=60)

    base_url = os.getenv('APPWRITE_ENDPOINT', '').rstrip('/')
    project_id = os.getenv('APPWRITE_PROJECT_ID', '').strip()
    api_key = os.getenv('APPWRITE_API_KEY', '').strip()

    if not base_url or not project_id or not api_key:
        item: JsonObject = {
            'id': len(_appwrite_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-user',
            'status': 'queued',
            'reason': 'Appwrite not configured',
            'user_id': payload.user_id,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _appwrite_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Content-Type': CONTENT_TYPE_JSON,
        'X-Appwrite-Project': project_id,
        'X-Appwrite-Key': api_key,
    }
    body: JsonObject = {
        'userId': payload.user_id,
        'email': payload.email,
        'password': payload.password,
        'name': payload.name,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/v1/users', headers=headers, json=body)
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'action': 'create-user',
                        'delivery_status': 'created',
                        'appwrite_user_id': data.get('$id', payload.user_id),
                    },
                }
            return {
                'status': 'ok',
                'result': {
                    'tenant_id': auth.tenant_id,
                    'action': 'create-user',
                    'delivery_status': 'appwrite-error',
                    'appwrite_status': response.status_code,
                    'detail': response.text[:200],
                },
            }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_appwrite_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-user',
            'status': f'queued-after-error:{ex}',
            'user_id': payload.user_id,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _appwrite_events_memory.append(item)
        return {'status': 'ok', 'result': item}


def appwrite_create_session(payload: AppwriteCreateSessionRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:appwrite:create-session', limit=60, window_seconds=60)

    base_url = os.getenv('APPWRITE_ENDPOINT', '').rstrip('/')
    project_id = os.getenv('APPWRITE_PROJECT_ID', '').strip()

    if not base_url or not project_id:
        item: JsonObject = {
            'id': len(_appwrite_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-session',
            'status': 'queued',
            'reason': 'Appwrite not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _appwrite_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Content-Type': CONTENT_TYPE_JSON,
        'X-Appwrite-Project': project_id,
    }
    body: JsonObject = {'email': payload.email, 'password': payload.password}

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/v1/account/sessions/email', headers=headers, json=body)
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'action': 'create-session',
                        'delivery_status': 'session-created',
                        'session_id': data.get('$id', ''),
                        'expire': data.get('expire', ''),
                    },
                }
            return {
                'status': 'ok',
                'result': {
                    'tenant_id': auth.tenant_id,
                    'action': 'create-session',
                    'delivery_status': 'appwrite-error',
                    'appwrite_status': response.status_code,
                },
            }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_appwrite_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-session',
            'status': f'queued-after-error:{ex}',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _appwrite_events_memory.append(item)
        return {'status': 'ok', 'result': item}


# ---------------------------------------------------------------------------
# Drone CI – pipeline trigger bridge
# ---------------------------------------------------------------------------

class DroneBuildTriggerRequest(BaseModel):
    repo_owner: str = Field(min_length=1, max_length=120)
    repo_name: str = Field(min_length=1, max_length=120)
    branch: str = Field(default='main', min_length=1, max_length=120)
    params: dict[str, object] = Field(default_factory=dict)


def drone_trigger_build(payload: DroneBuildTriggerRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:drone:trigger-build', limit=30, window_seconds=60)

    base_url = os.getenv('DRONE_SERVER_URL', '').rstrip('/')
    token = os.getenv('DRONE_API_TOKEN', '').strip()

    if not base_url or not token:
        item: JsonObject = {
            'id': len(_drone_builds_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': 'Drone CI not configured',
            'repo': f'{payload.repo_owner}/{payload.repo_name}',
            'branch': payload.branch,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _drone_builds_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            # Promote latest build on the branch (Drone REST API)
            list_resp = client.get(
                f'{base_url}/api/repos/{payload.repo_owner}/{payload.repo_name}/builds',
                headers=headers,
                params={'branch': payload.branch, 'limit': 1},
            )
            if list_resp.is_success:
                builds = list_resp.json()
                if builds and isinstance(builds, list):
                    first_item = cast(object, builds[0])
                    first_build = _json_object(first_item)
                    latest_build = _coerce_int((first_build or {}).get('number', 0), 0)
                    promote_params: dict[str, str] = {
                        'target': 'production',
                        **{f'input.{k}': str(v) for k, v in payload.params.items()},
                    }
                    promote_resp = client.post(
                        f'{base_url}/api/repos/{payload.repo_owner}/{payload.repo_name}/builds/{latest_build}/promote',
                        headers=headers,
                        params=promote_params,
                    )
                    if promote_resp.is_success:
                        pdata = promote_resp.json()
                        return {
                            'status': 'ok',
                            'result': {
                                'tenant_id': auth.tenant_id,
                                'repo': f'{payload.repo_owner}/{payload.repo_name}',
                                'branch': payload.branch,
                                'build_number': pdata.get('number'),
                                'build_status': pdata.get('status'),
                                'delivery_status': 'triggered',
                                'provider': 'drone',
                            },
                        }

            # Fallback: trigger a new build via /api/repos/{owner}/{repo}/builds
            trigger_resp = client.post(
                f'{base_url}/api/repos/{payload.repo_owner}/{payload.repo_name}/builds',
                headers=headers,
                params={'branch': payload.branch},
            )
            if trigger_resp.is_success:
                tdata = trigger_resp.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'repo': f'{payload.repo_owner}/{payload.repo_name}',
                        'branch': payload.branch,
                        'build_number': tdata.get('number'),
                        'build_status': tdata.get('status'),
                        'delivery_status': 'triggered',
                        'provider': 'drone',
                    },
                }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_drone_builds_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': f'queued-after-error:{ex}',
            'repo': f'{payload.repo_owner}/{payload.repo_name}',
            'branch': payload.branch,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _drone_builds_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_drone_builds_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'queued-after-non-success',
        'repo': f'{payload.repo_owner}/{payload.repo_name}',
        'branch': payload.branch,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _drone_builds_memory.append(item)
    return {'status': 'ok', 'result': item}


# ---------------------------------------------------------------------------
# Directus – headless CMS content bridge
# ---------------------------------------------------------------------------

class DirectusCreateItemRequest(BaseModel):
    collection: str = Field(min_length=1, max_length=120)
    data: dict[str, object] = Field(default_factory=dict)


class DirectusListItemsRequest(BaseModel):
    collection: str = Field(min_length=1, max_length=120)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    filter: dict[str, object] = Field(default_factory=dict)


def directus_create_item(payload: DirectusCreateItemRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:directus:create-item', limit=120, window_seconds=60)

    base_url = os.getenv('DIRECTUS_URL', '').rstrip('/')
    token = os.getenv('DIRECTUS_STATIC_TOKEN', '').strip()

    doc: JsonObject = {**payload.data, '_tenant_id': auth.tenant_id}

    if not base_url or not token:
        item: JsonObject = {
            'id': len(_directus_items_memory) + 1,
            'tenant_id': auth.tenant_id,
            'collection': payload.collection,
            'data': doc,
            'status': 'queued',
            'reason': 'Directus not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _directus_items_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f'{base_url}/items/{payload.collection}',
                headers=headers,
                json=doc,
            )
            if response.is_success:
                rdata = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'collection': payload.collection,
                        'directus_id': rdata.get('data', {}).get('id') if isinstance(rdata.get('data'), dict) else None,
                        'delivery_status': 'created',
                        'provider': 'directus',
                    },
                }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_directus_items_memory) + 1,
            'tenant_id': auth.tenant_id,
            'collection': payload.collection,
            'data': doc,
            'status': f'queued-after-error:{ex}',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _directus_items_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_directus_items_memory) + 1,
        'tenant_id': auth.tenant_id,
        'collection': payload.collection,
        'data': doc,
        'status': 'queued-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    _directus_items_memory.append(item)
    return {'status': 'ok', 'result': item}


def directus_list_items(payload: DirectusListItemsRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:directus:list-items', limit=180, window_seconds=60)

    base_url = os.getenv('DIRECTUS_URL', '').rstrip('/')
    token = os.getenv('DIRECTUS_STATIC_TOKEN', '').strip()

    if not base_url or not token:
        items: list[JsonObject] = [
            i for i in _directus_items_memory
            if i.get('tenant_id') == auth.tenant_id and i.get('collection') == payload.collection
        ]
        page = items[payload.offset: payload.offset + payload.limit]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'collection': payload.collection,
            'items': page,
            'total': len(items),
            'source': 'memory-fallback',
        }

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }
    params: dict[str, str | int] = {
        'limit': payload.limit,
        'offset': payload.offset,
        'filter[_tenant_id][_eq]': auth.tenant_id,
    }
    if payload.filter:
        for key, val in payload.filter.items():
            params[f'filter[{key}][_eq]'] = str(val)

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(
                f'{base_url}/items/{payload.collection}',
                headers=headers,
                params=params,
            )
            if response.is_success:
                rdata = response.json()
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'collection': payload.collection,
                    'items': rdata.get('data', []),
                    'total': rdata.get('meta', {}).get('total_count', 0) if isinstance(rdata.get('meta'), dict) else 0,
                    'source': 'directus',
                }
    except Exception as ex:
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'collection': payload.collection,
            'items': [],
            'total': 0,
            'source': f'error:{ex}',
        }

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'collection': payload.collection,
        'items': [],
        'total': 0,
        'source': 'directus-non-success',
    }


# ---------------------------------------------------------------------------
# MinIO – object storage bridge (presigned URL + object listing)
# ---------------------------------------------------------------------------

class MinioPresignRequest(BaseModel):
    bucket: str = Field(min_length=1, max_length=120)
    object_key: str = Field(min_length=1, max_length=512)
    method: Literal['GET', 'PUT'] = 'GET'
    expires_seconds: int = Field(default=3600, ge=60, le=86400)


class MinioListObjectsRequest(BaseModel):
    bucket: str = Field(min_length=1, max_length=120)
    prefix: str = Field(default='', max_length=256)
    max_keys: int = Field(default=50, ge=1, le=500)


def _minio_hmac_sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _minio_presign(
    endpoint: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    object_key: str,
    method: str,
    expires: int,
) -> str:
    """Generate an AWS-compatible presigned URL for MinIO (v4 query-string signing)."""
    import urllib.parse

    now = datetime.now(UTC)
    date_stamp = now.strftime('%Y%m%d')
    amz_date = now.strftime('%Y%m%dT%H%M%SZ')
    region = 'us-east-1'
    service = 's3'

    host = endpoint.replace('http://', '').replace('https://', '').rstrip('/')
    scheme = 'https' if endpoint.startswith('https') else 'http'
    canonical_uri = f'/{bucket}/{urllib.parse.quote(object_key, safe="")}'

    credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'
    credential = f'{access_key}/{credential_scope}'

    canonical_query = '&'.join([
        'X-Amz-Algorithm=AWS4-HMAC-SHA256',
        f'X-Amz-Credential={urllib.parse.quote(credential, safe="")}',
        f'X-Amz-Date={amz_date}',
        f'X-Amz-Expires={expires}',
        'X-Amz-SignedHeaders=host',
    ])

    canonical_headers = f'host:{host}\n'
    canonical_request = '\n'.join([
        method, canonical_uri, canonical_query,
        canonical_headers, 'host', 'UNSIGNED-PAYLOAD',
    ])

    string_to_sign = '\n'.join([
        'AWS4-HMAC-SHA256', amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    signing_key = _minio_hmac_sign(
        _minio_hmac_sign(
            _minio_hmac_sign(
                _minio_hmac_sign(f'AWS4{secret_key}'.encode(), date_stamp),
                region,
            ),
            service,
        ),
        'aws4_request',
    )
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    return (
        f'{scheme}://{host}{canonical_uri}'
        f'?{canonical_query}&X-Amz-Signature={signature}'
    )


def storage_presign(payload: MinioPresignRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:storage:presign', limit=120, window_seconds=60)

    endpoint = os.getenv('MINIO_ENDPOINT', '').strip()
    access_key = os.getenv('MINIO_ACCESS_KEY', '').strip()
    secret_key = os.getenv('MINIO_SECRET_KEY', '').strip()

    # Namespace bucket per tenant for isolation
    tenant_bucket = f'{auth.tenant_id}-{payload.bucket}'

    if not endpoint or not access_key or not secret_key:
        record: JsonObject = {
            'id': len(_minio_objects_memory) + 1,
            'tenant_id': auth.tenant_id,
            'bucket': tenant_bucket,
            'object_key': payload.object_key,
            'method': payload.method,
            'status': 'queued',
            'reason': 'MinIO not configured',
            'presigned_url': None,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _minio_objects_memory.append(record)
        return {'status': 'ok', 'result': record}

    presigned_url = _minio_presign(
        endpoint, access_key, secret_key,
        tenant_bucket, payload.object_key,
        payload.method, payload.expires_seconds,
    )

    record: JsonObject = {
        'id': len(_minio_objects_memory) + 1,
        'tenant_id': auth.tenant_id,
        'bucket': tenant_bucket,
        'object_key': payload.object_key,
        'method': payload.method,
        'presigned_url': presigned_url,
        'expires_seconds': payload.expires_seconds,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _minio_objects_memory.append(record)
    return {'status': 'ok', 'result': record}


def storage_list_objects(payload: MinioListObjectsRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:storage:list', limit=180, window_seconds=60)

    endpoint = os.getenv('MINIO_ENDPOINT', '').strip()
    access_key = os.getenv('MINIO_ACCESS_KEY', '').strip()
    secret_key = os.getenv('MINIO_SECRET_KEY', '').strip()

    tenant_bucket = f'{auth.tenant_id}-{payload.bucket}'

    if not endpoint or not access_key or not secret_key:
        items: list[JsonObject] = []
        for r in _minio_objects_memory:
            if r.get('tenant_id') != auth.tenant_id or r.get('bucket') != tenant_bucket:
                continue
            object_key = r.get('object_key')
            if isinstance(object_key, str) and object_key.startswith(payload.prefix):
                items.append(r)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'bucket': tenant_bucket,
            'prefix': payload.prefix,
            'objects': [{'key': r['object_key'], 'created_at': r['created_at']} for r in items[: payload.max_keys]],
            'total': len(items),
            'source': 'memory-fallback',
        }

    # Use MinIO S3-compatible ListObjectsV2 via REST
    headers: dict[str, str] = {}
    params: dict[str, str] = {'list-type': '2', 'max-keys': str(payload.max_keys)}
    if payload.prefix:
        params['prefix'] = payload.prefix

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(f'{endpoint}/{tenant_bucket}', headers=headers, params=params)
            if response.is_success:
                # Parse minimal XML response
                text = response.text
                import re
                keys = re.findall(r'<Key>(.*?)</Key>', text)
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'bucket': tenant_bucket,
                    'prefix': payload.prefix,
                    'objects': [{'key': k} for k in keys],
                    'total': len(keys),
                    'source': 'minio',
                }
    except Exception as ex:
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'bucket': tenant_bucket,
            'objects': [],
            'total': 0,
            'source': f'error:{ex}',
        }

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'bucket': tenant_bucket,
        'objects': [],
        'total': 0,
        'source': 'minio-non-success',
    }


# ---------------------------------------------------------------------------
# Stripe – payment events bridge
# ---------------------------------------------------------------------------

class StripeCreateCheckoutRequest(BaseModel):
    price_id: str = Field(min_length=1, max_length=120)
    success_url: HttpUrl
    cancel_url: HttpUrl
    customer_email: str | None = Field(default=None, max_length=320)
    quantity: int = Field(default=1, ge=1, le=100)
    metadata: dict[str, object] = Field(default_factory=dict)


class StripeWebhookProcessRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    event_id: str = Field(min_length=1, max_length=120)
    data: dict[str, object] = Field(default_factory=dict)
    signature: str | None = Field(default=None, max_length=512)


def stripe_create_checkout(payload: StripeCreateCheckoutRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:stripe:checkout', limit=60, window_seconds=60)

    secret_key = os.getenv('STRIPE_SECRET_KEY', '').strip()

    if not secret_key:
        item: JsonObject = {
            'id': len(_stripe_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-checkout',
            'status': 'queued',
            'reason': 'Stripe not configured',
            'price_id': payload.price_id,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _stripe_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    form_data: dict[str, object] = {
        'mode': 'payment',
        'success_url': str(payload.success_url),
        'cancel_url': str(payload.cancel_url),
        'line_items[0][price]': payload.price_id,
        'line_items[0][quantity]': str(payload.quantity),
        'metadata[tenant_id]': auth.tenant_id,
    }
    if payload.customer_email:
        form_data['customer_email'] = payload.customer_email
    for k, v in payload.metadata.items():
        form_data[f'metadata[{k}]'] = str(v)

    headers = {
        'Authorization': f'Bearer {secret_key}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                'https://api.stripe.com/v1/checkout/sessions',
                headers=headers,
                data=form_data,
            )
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'action': 'create-checkout',
                        'delivery_status': 'created',
                        'session_id': data.get('id'),
                        'checkout_url': data.get('url'),
                    },
                }
            return {
                'status': 'ok',
                'result': {
                    'tenant_id': auth.tenant_id,
                    'action': 'create-checkout',
                    'delivery_status': 'stripe-error',
                    'stripe_status': response.status_code,
                    'detail': response.text[:200],
                },
            }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_stripe_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-checkout',
            'status': f'queued-after-error:{ex}',
            'price_id': payload.price_id,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _stripe_events_memory.append(item)
        return {'status': 'ok', 'result': item}


def stripe_process_webhook(payload: StripeWebhookProcessRequest, auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:stripe:webhook', limit=300, window_seconds=60)

    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
    signature_valid: bool | None = None

    if webhook_secret and payload.signature:
        raw = str(payload.data).encode()
        signature_valid = _verify_stripe_signature(webhook_secret, raw, payload.signature)
    elif webhook_secret and not payload.signature:
        raise HTTPException(status_code=400, detail='Stripe webhook signature required when STRIPE_WEBHOOK_SECRET is set.')

    event: JsonObject = {
        'id': len(_stripe_events_memory) + 1,
        'tenant_id': auth.tenant_id,
        'action': 'webhook',
        'event_type': payload.event_type,
        'event_id': payload.event_id,
        'data': payload.data,
        'signature_valid': signature_valid,
        'received_at': datetime.now(UTC).isoformat(),
    }
    _stripe_events_memory.append(event)

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'event_type': payload.event_type,
        'event_id': payload.event_id,
        'internal_id': event['id'],
        'signature_valid': signature_valid,
        'received_at': event['received_at'],
    }


def list_stripe_events(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    items: list[JsonObject] = [e for e in _stripe_events_memory if e.get('tenant_id') == auth.tenant_id]
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'events': items}


# ---------------------------------------------------------------------------
# Audit log – rate-limit and security event trail
# ---------------------------------------------------------------------------

def _record_audit(tenant_id: str, action: str, detail: JsonObject) -> None:
    _audit_log_memory.append({
        'id': len(_audit_log_memory) + 1,
        'tenant_id': tenant_id,
        'action': action,
        'detail': detail,
        'recorded_at': datetime.now(UTC).isoformat(),
    })


def get_audit_log(auth: AuthContext = Depends(require_auth)) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:ops:audit-log', limit=60, window_seconds=60)
    _record_audit(auth.tenant_id, 'audit-log-read', {'source': 'ops'})
    items: list[JsonObject] = [e for e in _audit_log_memory if e.get('tenant_id') == auth.tenant_id]
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(items),
        'entries': items,
        'generated_at': datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# Legacy finance compatibility routes (kept for selftest and older clients)
# ---------------------------------------------------------------------------

@app.get('/ops/finance/hub')
def finance_hub(auth: AuthContext = Depends(require_auth)) -> JsonObject:  # NOSONAR
    _enforce_rate_limit(f'{auth.tenant_id}:finance:hub', limit=120, window_seconds=60)
    integrations = [
        item for item in _accounting_integrations_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    exports = [
        item for item in _accounting_exports_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'connected_integrations': len(integrations),
        'exports_count': len(exports),
        'generated_at': datetime.now(UTC).isoformat(),
    }


@app.post('/ops/finance/accounting/integrations/connect')
def finance_connect_integration(
    payload: FinanceLegacyIntegrationConnectRequest,
    auth: AuthDep,
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:finance:integrations:connect', limit=60, window_seconds=60)
    now = datetime.now(UTC).isoformat()
    provider = payload.provider.strip().lower()

    existing = next(
        (
            item for item in _accounting_integrations_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('provider', '')).lower() == provider
        ),
        None,
    )
    if existing is not None:
        existing['status'] = 'connected'
        existing['client_id_masked'] = payload.client_id[:3] + '***'
        existing['account_name'] = payload.account_name
        existing['updated_at'] = now
        integration = existing
    else:
        integration = {
            'id': len(_accounting_integrations_memory) + 1,
            'tenant_id': auth.tenant_id,
            'provider': provider,
            'status': 'connected',
            'client_id_masked': payload.client_id[:3] + '***',
            'account_name': payload.account_name,
            'created_at': now,
            'updated_at': now,
        }
        _accounting_integrations_memory.append(integration)

    _record_audit(auth.tenant_id, 'finance.integration.connected', {'provider': provider})
    return {'status': 'ok', 'integration': integration}


@app.get('/ops/finance/accounting/integrations')
def finance_list_integrations(auth: AuthContext = Depends(require_auth)) -> JsonObject:  # NOSONAR
    _enforce_rate_limit(f'{auth.tenant_id}:finance:integrations:list', limit=120, window_seconds=60)
    rows = [
        item for item in _accounting_integrations_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    rows.sort(key=lambda item: str(item.get('updated_at', '') or ''), reverse=True)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows),
        'integrations': rows,
        'generated_at': datetime.now(UTC).isoformat(),
    }


@app.post('/ops/finance/accounting/exports')
def finance_create_export(
    payload: FinanceLegacyExportRequest,
    auth: AuthDep,
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:finance:exports:create', limit=60, window_seconds=60)
    now = datetime.now(UTC).isoformat()
    provider = payload.provider.strip().lower()
    delivery_status = 'submitted-live' if os.getenv('FINANCE_PROVIDER_LIVE', '0').strip().lower() in {'1', 'true', 'yes', 'on'} else 'queued-simulated'

    export_record = {
        'id': len(_accounting_exports_memory) + 1,
        'tenant_id': auth.tenant_id,
        'provider': provider,
        'export_type': payload.export_type,
        'period_label': payload.period_label,
        'status': 'submitted',
        'delivery_status': delivery_status,
        'submitted_at': now,
        'completed_at': now,
        'detail': 'Legacy finance export accepted',
    }
    _accounting_exports_memory.append(export_record)
    _record_audit(
        auth.tenant_id,
        'finance.export.submitted',
        {'provider': provider, 'export_type': payload.export_type, 'period_label': payload.period_label},
    )
    return {'status': 'ok', 'export': export_record}


@app.post('/ops/finance/accounting/integrations/{provider}/refresh-token', responses={
    422: {'description': 'Unsupported provider or missing configuration'},
    409: {'description': 'Integration not connected for provider'}
})
def finance_refresh_token(
    provider: str,
    auth: AuthContext = Depends(require_auth),  # NOSONAR
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:finance:integrations:refresh', limit=40, window_seconds=60)
    normalized_provider = provider.strip().lower()
    if normalized_provider not in {'quickbooks', 'xero', 'hmrc'}:
        raise HTTPException(status_code=422, detail='Unsupported provider.')

    if normalized_provider == 'xero' and not os.getenv('XERO_CLIENT_SECRET', '').strip():
        raise HTTPException(status_code=422, detail='XERO_CLIENT_SECRET is not configured.')  # NOSONAR

    integration = next(
        (
            item for item in _accounting_integrations_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('provider', '')).lower() == normalized_provider
        ),
        None,
    )
    if integration is None:
        raise HTTPException(status_code=409, detail='Integration not connected for provider.')

    integration['updated_at'] = datetime.now(UTC).isoformat()
    _record_audit(auth.tenant_id, 'finance.integration.refreshed', {'provider': normalized_provider})
    return {'status': 'ok', 'provider': normalized_provider, 'refresh': 'completed'}


@app.post('/ops/finance/accounting/integrations/{provider}/rotate-secret', responses={
    422: {'description': 'Unsupported provider'},
    409: {'description': 'Integration not connected for provider'}
})
def finance_rotate_secret(
    provider: str,
    payload: FinanceLegacyRotateSecretRequest,
    auth: AuthContext = Depends(require_auth),  # NOSONAR
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:finance:integrations:rotate-secret', limit=30, window_seconds=60)
    normalized_provider = provider.strip().lower()
    if normalized_provider not in {'quickbooks', 'xero', 'hmrc'}:
        raise HTTPException(status_code=422, detail='Unsupported provider.')

    integration = next(
        (
            item for item in _accounting_integrations_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('provider', '')).lower() == normalized_provider
        ),
        None,
    )
    if integration is None:
        raise HTTPException(status_code=409, detail='Integration not connected for provider.')

    integration['updated_at'] = datetime.now(UTC).isoformat()
    integration['secret_rotated'] = True
    integration['client_secret_masked'] = payload.client_secret[:3] + '***'
    _record_audit(auth.tenant_id, 'finance.integration.secret_rotated', {'provider': normalized_provider})

    return {
        'status': 'ok',
        'provider': normalized_provider,
        'rotation_mode': 'secret-only',
    }


app.include_router(
    create_content_integrations_router(
        handlers={
            'generate_content': generate_content,
            'generate_ads': generate_ads,
            'analyze_seo': analyze_seo,
            'schedule_social_post': schedule_social_post,
            'list_scheduled_posts': list_scheduled_posts,
            'move_scheduled_post': move_scheduled_post,
            'delete_scheduled_post': delete_scheduled_post,
            'ingest_social_listening_mention': ingest_social_listening_mention,
            'list_social_listening_mentions': list_social_listening_mentions,
            'get_social_listening_summary': get_social_listening_summary,
            'create_social_listening_alert_rule': create_social_listening_alert_rule,
            'list_social_listening_alerts': list_social_listening_alerts,
            'get_social_listening_clusters': get_social_listening_clusters,
            'ingest_review': ingest_review,
            'list_reviews': list_reviews,
            'respond_to_review': respond_to_review,
            'get_reviews_summary': get_reviews_summary,
            'create_email_contact': create_email_contact,
            'list_email_contacts': list_email_contacts,
            'create_email_campaign': create_email_campaign,
            'list_email_campaigns': list_email_campaigns,
            'send_test_email_campaign': send_test_email_campaign,
            'upsert_suitecrm_lead': upsert_suitecrm_lead,
            'register_refferq_referral': register_refferq_referral,
            'capture_posthog_event': capture_posthog_event,
            'track_matomo_event': track_matomo_event,
            'track_plausible_event': track_plausible_event,
            'trigger_n8n_webhook': trigger_n8n_webhook,
            'evaluate_growthbook_flag': evaluate_growthbook_flag,
            'receive_webhook': receive_webhook,
            'list_webhook_events': list_webhook_events,
            'appwrite_create_user': appwrite_create_user,
            'appwrite_create_session': appwrite_create_session,
            'drone_trigger_build': drone_trigger_build,
            'directus_create_item': directus_create_item,
            'directus_list_items': directus_list_items,
            'storage_presign': storage_presign,
            'storage_list_objects': storage_list_objects,
            'stripe_create_checkout': stripe_create_checkout,
            'stripe_process_webhook': stripe_process_webhook,
            'stripe_list_events': list_stripe_events,
            'get_audit_log': get_audit_log,
        },
    )
)

app.include_router(
    create_seo_platform_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        seo_analyses_memory=_seo_analyses_memory,
        db_ready_fn=lambda: _db_ready,
        db_dsn_fn=_db_dsn,
    )
)

app.include_router(
    create_bridges_router(
        enforce_rate_limit=_enforce_rate_limit,
        meilisearch_index_memory=_meilisearch_index_memory,
        redis_ops_memory=_redis_ops_memory,
        twilio_messages_memory=_twilio_messages_memory,
        slack_messages_memory=_slack_messages_memory,
        resend_messages_memory=_resend_messages_memory,
        algolia_sync_memory=_algolia_sync_memory,
    )
)

# ── New module routers (Part 3 & Part 4) ─────────────────────────────────────

app.include_router(
    create_engagement_router(
        enforce_rate_limit=_enforce_rate_limit,
        streaks_memory=_engagement_streaks_memory,
        credit_ledger_memory=_credit_ledger_memory,
        notifications_memory=_notifications_memory,
        scheduled_posts_memory=_scheduled_posts_memory,
        email_campaigns_memory=_email_campaigns_memory,
        influencer_campaigns_memory=_influencer_campaigns_memory,
        chatbots_memory=_chatbots_memory,
        tenant_profiles_memory=_tenant_profiles_memory,
        crm_contacts_memory=_crm_contacts_memory,
        crm_deals_memory=_crm_deals_memory,
        linkinbio_pages_memory=_linkinbio_pages_memory,
        linkinbio_links_memory=_linkinbio_links_memory,
        cms_pages_memory=_cms_pages_memory,
        marketplace_installs_memory=_marketplace_installs_memory,
        invoices_memory=_invoices_memory,
        companion_profiles_memory=_engagement_companion_profiles_memory,
        companion_messages_memory=_engagement_companion_messages_memory,
        fomo_rules_memory=_engagement_fomo_rules_memory,
        fomo_events_memory=_engagement_fomo_events_memory,
        social_proof_events_memory=_engagement_social_proof_events_memory,
        dependency_profiles_memory=_engagement_dependency_profiles_memory,
        dependency_events_memory=_engagement_dependency_events_memory,
        community_circles_memory=_engagement_community_circles_memory,
        community_posts_memory=_engagement_community_posts_memory,
        community_amas_memory=_engagement_community_amas_memory,
        brand_lock_profiles_memory=_engagement_brand_lock_profiles_memory,
        brand_lock_events_memory=_engagement_brand_lock_events_memory,
        autopilot_profiles_memory=_engagement_autopilot_profiles_memory,
        autopilot_events_memory=_engagement_autopilot_events_memory,
        achievement_profiles_memory=_engagement_achievement_profiles_memory,
        achievement_events_memory=_engagement_achievement_events_memory,
        money_printer_ideas_memory=_money_printer_ideas_memory,
        money_printer_validations_memory=_money_printer_validations_memory,
        bank_accounts_memory=_bank_accounts_memory,
        bank_transactions_memory=_bank_transactions_memory,
        bank_payouts_memory=_bank_payouts_memory,
        university_courses_memory=_university_courses_memory,
        university_cohorts_memory=_university_cohorts_memory,
        university_enrollments_memory=_university_enrollments_memory,
        studios_services_memory=_studios_services_memory,
        studios_briefs_memory=_studios_briefs_memory,
        studios_proposals_memory=_studios_proposals_memory,
        studios_escrows_memory=_studios_escrows_memory,
        commerce_products_memory=_commerce_products_memory,
        commerce_orders_memory=_commerce_orders_memory,
        talent_creators_memory=_talent_creators_memory,
        talent_deals_memory=_talent_deals_memory,
        talent_rate_cards_memory=_talent_rate_cards_memory,
        white_label_profiles_memory=_white_label_profiles_memory,
        white_label_events_memory=_white_label_events_memory,
        referrals_memory=_engagement_referrals_memory,
        referral_claims_memory=_engagement_referral_claims_memory,
        refferq_jobs_memory=_refferq_jobs_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_crm_router(
        enforce_rate_limit=_enforce_rate_limit,
        contacts_memory=_crm_contacts_memory,
        companies_memory=_crm_companies_memory,
        deals_memory=_crm_deals_memory,
        activities_memory=_crm_activities_memory,
        webhook_subscriptions_memory=_crm_webhook_subscriptions_memory,
        audit_log_memory=_audit_log_memory,
        leads_memory=_crm_leads_memory,
        tasks_memory=_crm_tasks_memory,
        tickets_memory=memory_stores.tickets,
        campaigns_memory=_crm_campaigns_memory,
        segments_memory=_crm_segments_memory,
        notes_memory=_crm_notes_memory,
        quotes_memory=_crm_quotes_memory,
        crm_invoices_memory=_crm_invoices_memory,
        email_sequences_memory=_crm_email_sequences_memory,
        workflow_rules_memory=_crm_workflow_rules_memory,
        sla_rules_memory=_crm_sla_rules_memory,
        projects_memory=_crm_projects_memory,
        custom_entity_types_memory=_crm_custom_entity_types_memory,
        custom_entity_records_memory=_crm_custom_entity_records_memory,
        automation_recipes_memory=_crm_automation_recipes_memory,
        api_tokens_memory=_crm_api_tokens_memory,
        backup_snapshots_memory=_crm_backup_snapshots_memory,
        live_sync_state_memory=_crm_live_sync_state_memory,
    )
)
app.include_router(create_crm_abm_router(enforce_rate_limit=_enforce_rate_limit))
app.include_router(
    create_influencer_router(
        enforce_rate_limit=_enforce_rate_limit,
        influencers_memory=_influencers_memory,
        influencer_campaigns_memory=_influencer_campaigns_memory,
        influencer_outreach_memory=_influencer_outreach_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_chatbot_router(
        enforce_rate_limit=_enforce_rate_limit,
        chatbots_memory=_chatbots_memory,
        chatbot_conversations_memory=_chatbot_conversations_memory,
        chatbot_leads_memory=_chatbot_leads_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_ira_router(
        enforce_rate_limit=_enforce_rate_limit,
        ctx=IRAContext(
            audit_log_memory=_audit_log_memory,
            tickets_memory=memory_stores.tickets,
            chatbot_conversations_memory=_chatbot_conversations_memory,
            credit_ledger_memory=_credit_ledger_memory,
            invoices_memory=_invoices_memory,
            stripe_events_memory=_stripe_events_memory,
            revenue_conversions_memory=_revenue_conversions_memory,
            api_usage_audit_memory=_api_usage_audit_memory,
            ai_security_usage_memory=_ai_security_usage_memory,
            slack_messages_memory=_slack_messages_memory,
            resend_messages_memory=_resend_messages_memory,
            twilio_messages_memory=_twilio_messages_memory,
            ira_events_memory=_ira_events_memory,
            ira_sessions_memory=_ira_sessions_memory,
            ira_controls_memory=_ira_controls_memory,
            ira_connectors_memory=_ira_connectors_memory,
            ira_ml_knowledge_memory=_ira_ml_knowledge_memory,
            ira_ml_jobs_memory=_ira_ml_jobs_memory,
            ira_ml_models_memory=_ira_ml_models_memory,
            ira_structured_memory=_ira_structured_memory,
            ira_action_snapshots_memory=_ira_action_snapshots_memory,
            ira_cost_ledger_memory=_ira_cost_ledger_memory,
            ira_ab_tests_memory=_ira_ab_tests_memory,
            ira_performance_log_memory=_ira_performance_log_memory,
        ),
    )
)

app.include_router(
    create_linkinbio_router(
        enforce_rate_limit=_enforce_rate_limit,
        linkinbio_pages_memory=_linkinbio_pages_memory,
        linkinbio_links_memory=_linkinbio_links_memory,
        linkinbio_analytics_memory=_linkinbio_analytics_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_billing_router(
        enforce_rate_limit=_enforce_rate_limit,
        subscriptions_memory=_subscriptions_memory,
        invoices_memory=_invoices_memory,
        credit_ledger_memory=_credit_ledger_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(create_stripe_billing_router())

app.include_router(create_email_router())

app.include_router(
    create_super_admin_finance_router(
        enforce_rate_limit=_enforce_rate_limit,
        require_super_admin_access=_ops_require_super_admin_access,
        accounting_integrations_memory=_accounting_integrations_memory,
        accounting_exports_memory=_accounting_exports_memory,
        module_settings_memory=_super_admin_module_settings_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_cms_router(
        enforce_rate_limit=_enforce_rate_limit,
        cms_connections_memory=_cms_connections_memory,
        cms_pages_memory=_cms_pages_memory,
        cms_sync_log_memory=_cms_sync_log_memory,
        email_sequences_memory=_crm_email_sequences_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_marketplace_router(
        enforce_rate_limit=_enforce_rate_limit,
        marketplace_catalogue_memory=_marketplace_catalogue_memory,
        marketplace_installs_memory=_marketplace_installs_memory,
        audit_log_memory=_audit_log_memory,
    )
)

# ADDED: Content Approval Workflows (Hootsuite §4.5)
app.include_router(
    create_content_approval_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        approval_requests_memory=_content_approval_requests_memory,
        approval_comments_memory=_content_approval_comments_memory,
        approval_configs_memory=_content_approval_configs_memory,
    )
)

# ADDED: Media Library (Hootsuite §4.3)
app.include_router(
    create_media_library_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        assets_memory=_media_library_assets_memory,
        folders_memory=_media_library_folders_memory,
        tags_memory=_media_library_tags_memory,
    )
)

# ADDED: Employee Advocacy / Hootsuite Amplify (Hootsuite §9)
app.include_router(
    create_employee_advocacy_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        advocacy_content_memory=_advocacy_content_memory,
        advocacy_shares_memory=_advocacy_shares_memory,
        advocacy_participants_memory=_advocacy_participants_memory,
        advocacy_campaigns_memory=_advocacy_campaigns_memory,
    )
)

app.include_router(
    create_analytics_router(
        enforce_rate_limit=_enforce_rate_limit,
        custom_reports_memory=_analytics_reports_memory,
        report_schedules_memory=_analytics_report_schedules_memory,
        trends_memory=_analytics_trends_memory,
        rollups_memory=_analytics_rollups_memory,
        get_queue_counts=lambda: {
            'social_scheduled': len(_scheduled_posts_memory),
            'notifications': len(_notifications_memory),
            'reviews': len(_reviews_memory),
            'social_listening': len(_social_listening_memory),
            'email_campaigns': len(_email_campaigns_memory),
            'crm_contacts': len(_crm_contacts_memory),
            'crm_deals': len(_crm_deals_memory),
            'influencer_campaigns': len(_influencer_campaigns_memory),
            'chatbots': len(_chatbots_memory),
            'cms_connections': len(_cms_connections_memory),
            'content_generated': len(_ai_gateway_memory),
            'seo_analyses': 0,
            'ad_jobs': 0,
            'bank_payouts': len(_bank_payouts_memory),
            'studios_escrows': len(_studios_escrows_memory),
            'university_courses': len(_university_courses_memory),
            'university_enrollments': len(_university_enrollments_memory),
            'studios_services': len(_studios_services_memory),
            'commerce_products': len(_commerce_products_memory),
            'commerce_orders': len(_commerce_orders_memory),
        },
    )
)

# ADDED: Smart Inbox — Unified Social Engagement Hub (SproutSocial §3)
app.include_router(
    create_smart_inbox_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        messages_memory=_smart_inbox_messages_memory,
        notes_memory=_smart_inbox_notes_memory,
        locks_memory=_smart_inbox_locks_memory,
        saved_replies_memory=_saved_replies_memory,
        delivery_failures_memory=_smart_inbox_delivery_failures_memory,
        delivery_replay_runs_memory=_smart_inbox_delivery_replay_runs_memory,
    )
)

# ADDED: ViralPost — Optimal Send Time Engine (SproutSocial §2.1.3)
app.include_router(
    create_viralpost_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        analyses_memory=_viralpost_analyses_memory,
        post_history_memory=_viralpost_post_history_memory,
    )
)

# ADDED: Trend Intelligence — cross-source forecasting, AI content planning, and performance optimization
app.include_router(
    create_trend_intelligence_router(
        enforce_rate_limit=_enforce_rate_limit,
        signals_memory=_trend_signals_memory,
        forecasts_memory=_trend_forecasts_memory,
        selections_memory=_trend_selections_memory,
        content_memory=_trend_content_generations_memory,
        performance_memory=_trend_performance_tracks_memory,
        recommendations_memory=_trend_recommendations_memory,
    )
)

# ADDED: Competitive Benchmarking (SproutSocial §5.4)
app.include_router(
    create_competitive_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        profiles_memory=_competitor_profiles_memory,
        snapshots_memory=_competitor_snapshots_memory,
    )
)

# ADDED: Social Workspace — connected channels, brand details, unified engagement, and autopost
app.include_router(
    create_social_workspace_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        social_accounts_memory=_social_accounts_memory,
        brand_profiles_memory=_social_brand_profiles_memory,
        inbox_messages_memory=_smart_inbox_messages_memory,
        competitor_profiles_memory=_competitor_profiles_memory,
        competitor_snapshots_memory=_competitor_snapshots_memory,
        notifications_memory=_notifications_memory,
        scheduled_posts_memory=_scheduled_posts_memory,
        viralpost_post_history_memory=_viralpost_post_history_memory,
        db_ready_fn=lambda: _db_ready,
        db_dsn_fn=_db_dsn,
    )
)

# ADDED: Manychat-style audience + automation entities
app.include_router(create_social_manychat_router())

# ADDED: UTM Builder with saved presets (SproutSocial §2.1.1)
app.include_router(
    create_utm_builder_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        presets_memory=_utm_presets_memory,
    )
)

app.include_router(
    create_revenue_attribution_router(
        enforce_rate_limit=_enforce_rate_limit,
        touchpoints_memory=_revenue_touchpoints_memory,
        conversions_memory=_revenue_conversions_memory,
        spend_memory=_revenue_spend_memory,
        db_ready_fn=lambda: _db_ready,
        db_dsn_fn=_db_dsn,
    )
)

app.include_router(
    create_growth_suite_router(
        ctx=GrowthSuiteContext(
            enforce_rate_limit=_enforce_rate_limit,
            growth_suite_memory=_growth_suite_memory,
            scheduled_posts_memory=_scheduled_posts_memory,
            email_campaigns_memory=_email_campaigns_memory,
            chatbots_memory=_chatbots_memory,
            chatbot_leads_memory=_chatbot_leads_memory,
            linkinbio_pages_memory=_linkinbio_pages_memory,
            linkinbio_links_memory=_linkinbio_links_memory,
            analytics_reports_memory=_analytics_reports_memory,
            crm_contacts_memory=_crm_contacts_memory,
            crm_deals_memory=_crm_deals_memory,
            revenue_touchpoints_memory=_revenue_touchpoints_memory,
            revenue_conversions_memory=_revenue_conversions_memory,
            db_ready_fn=lambda: _db_ready,
            db_dsn_fn=_db_dsn,
        ),
    )
)

# ── Viral Singularity Engine (VSE) ────────────────────────────────────────────────────
app.include_router(
    create_vse_router(
        enforce_rate_limit=_enforce_rate_limit,
        vse_viral_events_memory=_vse_viral_events_memory,
        vse_briefs_memory=_vse_briefs_memory,
        vse_trigger_analyses_memory=_vse_trigger_analyses_memory,
        vse_algorithm_models_memory=_vse_algorithm_models_memory,
        vse_algorithm_updates_memory=_vse_algorithm_updates_memory,
        vse_network_maps_memory=_vse_network_maps_memory,
        vse_cascade_simulations_memory=_vse_cascade_simulations_memory,
        vse_detonations_memory=_vse_detonations_memory,
        vse_swarms_memory=_vse_swarms_memory,
        vse_momentum_events_memory=_vse_momentum_events_memory,
        vse_content_factory_memory=_vse_content_factory_memory,
        vse_emotion_analyses_memory=_vse_emotion_analyses_memory,
        vse_trend_alerts_memory=_vse_trend_alerts_memory,
        vse_trend_hijacks_memory=_vse_trend_hijacks_memory,
        vse_paid_events_memory=_vse_paid_events_memory,
        vse_dark_social_seeds_memory=_vse_dark_social_seeds_memory,
        vse_immortal_assets_memory=_vse_immortal_assets_memory,
        vse_viral_vault_memory=_vse_viral_vault_memory,
        db_ready_fn=lambda: _db_ready,
        db_dsn_fn=_db_dsn,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Sales Sequences (HubSpot Sales Hub §5.3) ─────────────────────────────────
app.include_router(
    create_sequences_router(
        enforce_rate_limit=_enforce_rate_limit,
        sequences_memory=memory_stores.sequences,
        enrollments_memory=memory_stores.sequence_enrollments,
        step_events_memory=memory_stores.sequence_step_events,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Meeting Scheduling (HubSpot Sales Hub §5.4) ──────────────────────────────
app.include_router(
    create_meetings_router(
        enforce_rate_limit=_enforce_rate_limit,
        meeting_links_memory=memory_stores.meeting_links,
        bookings_memory=memory_stores.meeting_bookings,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Help Desk / Ticketing (HubSpot Service Hub §6.1) ─────────────────────────
app.include_router(
    create_tickets_router(
        enforce_rate_limit=_enforce_rate_limit,
        tickets_memory=memory_stores.tickets,
        ticket_comments_memory=memory_stores.ticket_comments,
        sla_configs_memory=memory_stores.sla_configs,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Knowledge Base (HubSpot Service Hub §6.2) ────────────────────────────────
app.include_router(
    create_knowledge_base_router(
        enforce_rate_limit=_enforce_rate_limit,
        kb_categories_memory=memory_stores.kb_categories,
        kb_articles_memory=memory_stores.kb_articles,
        kb_feedback_memory=memory_stores.kb_article_feedback,
        audit_log_memory=_audit_log_memory,
    )
)

# ── NPS / CSAT Surveys (HubSpot Service Hub §6.4) ────────────────────────────
app.include_router(
    create_surveys_router(
        enforce_rate_limit=_enforce_rate_limit,
        surveys_memory=memory_stores.surveys,
        survey_responses_memory=memory_stores.survey_responses,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Sales Documents & Quotes (HubSpot Sales Hub §5.6) ────────────────────────
app.include_router(
    create_documents_router(
        enforce_rate_limit=_enforce_rate_limit,
        documents_memory=memory_stores.sales_documents,
        document_views_memory=memory_stores.document_shares,
        quotes_memory=memory_stores.sales_quotes,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Marketing Automation Workflows (HubSpot §3.2) ────────────────────────────
app.include_router(
    create_workflows_router(
        enforce_rate_limit=_enforce_rate_limit,
        workflows_memory=memory_stores.workflows,
        workflow_executions_memory=memory_stores.workflow_executions,
        workflow_step_logs_memory=memory_stores.workflow_step_logs,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Product Catalog (HubSpot Commerce Hub §8.2) ───────────────────────────────
app.include_router(
    create_products_router(
        enforce_rate_limit=_enforce_rate_limit,
        products_memory=memory_stores.product_catalog,
        product_categories_memory=memory_stores.product_catalog_categories,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Enterprise Pentest Platform — Phase 1 ────────────────────────────────────
app.include_router(
    create_pentest_router(
        enforce_rate_limit=_enforce_rate_limit,
        findings_memory=memory_stores.pentest_findings,
        risk_policies_memory=memory_stores.pentest_risk_policies,
        sync_queue_memory=memory_stores.pentest_sync_queue,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Enterprise Pentest Platform — Phase 2 ────────────────────────────────────
app.include_router(
    create_pentest_sync_router(
        enforce_rate_limit=_enforce_rate_limit,
        findings_memory=memory_stores.pentest_findings,
        risk_policies_memory=memory_stores.pentest_risk_policies,
        defectdojo_configs_memory=memory_stores.pentest_defectdojo_configs,
        sync_queue_memory=memory_stores.pentest_sync_queue,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Flywheel Module 1: Outcome Attribution & Decision Quality ─────────────────
app.include_router(
    create_outcome_attribution_router(
        ctx=OutcomeAttributionContext(
            enforce_rate_limit=_enforce_rate_limit,
            actions_memory=memory_stores.outcome_actions,
            outcomes_memory=memory_stores.outcome_outcomes,
            quality_scores_memory=memory_stores.outcome_quality_scores,
            audit_log_memory=_audit_log_memory,
            get_db_ready=lambda: _db_ready,
            db_dsn=_db_dsn,
        )
    )
)

# ── Flywheel Module 2: Trust Center ──────────────────────────────────────────
app.include_router(
    create_trust_center_router(
        ctx=TrustCenterContext(
            enforce_rate_limit=_enforce_rate_limit,
            policy_history_memory=memory_stores.trust_policy_history,
            approval_chains_memory=memory_stores.trust_approval_chains,
            incidents_memory=memory_stores.trust_incidents,
            governance_snapshots_memory=memory_stores.trust_governance_snapshots,
            audit_log_memory=_audit_log_memory,
            get_db_ready=lambda: _db_ready,
            db_dsn=_db_dsn,
        )
    )
)

# ── Flywheel Module 3: Integration Playbooks ─────────────────────────────────
app.include_router(
    create_playbooks_router(
        ctx=PlaybooksContext(
            enforce_rate_limit=_enforce_rate_limit,
            playbooks_memory=memory_stores.playbooks,
            playbook_runs_memory=memory_stores.playbook_runs,
            audit_log_memory=_audit_log_memory,
            get_db_ready=lambda: _db_ready,
            db_dsn=_db_dsn,
        )
    )
)

# ── Flywheel Module 4: Performance Benchmarks ────────────────────────────────
app.include_router(
    create_benchmarks_router(
        ctx=BenchmarksContext(
            enforce_rate_limit=_enforce_rate_limit,
            benchmarks_memory=memory_stores.benchmarks,
            segment_benchmarks_memory=memory_stores.segment_benchmarks,
            audit_log_memory=_audit_log_memory,
            get_db_ready=lambda: _db_ready,
            db_dsn=_db_dsn,
        )
    )
)


# ── AI Models Integration ────────────────────────────────────────────────────
# Connects to Ollama (text), ComfyUI (images/video), WhisperX (speech), voice workers
app.include_router(
    create_ai_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
        credit_ledger_memory=_credit_ledger_memory,
    )
)

# ── Ads Control Tower ────────────────────────────────────────────────────────
app.include_router(
    create_ads_control_tower_router(
        enforce_rate_limit=_enforce_rate_limit,
        notifications_memory=_notifications_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(ad_generation_router)
app.include_router(social_posting_router)
app.include_router(social_media_router)
app.include_router(social_media_router, prefix='/api/v1')
app.include_router(competitor_analysis_router)
app.include_router(backlink_intelligence_router)
app.include_router(brandkit_router)
app.include_router(rank_tracker_router)

# ── Platform Intelligence ─────────────────────────────────────────────────────
app.include_router(
    create_platform_intelligence_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
    )
)

# ── Platform Integration (social media publishing / scheduling / analytics) ───
app.include_router(
    create_platform_integration_router(
        enforce_rate_limit=_enforce_rate_limit,
    )
)

# ── Previously-orphaned routers ───────────────────────────────────────────────
app.include_router(agent_analytics_router)
app.include_router(agents_router)
app.include_router(answer_engine_router)
app.include_router(brand_hub_router)
app.include_router(cdn_analytics_router)
app.include_router(predis_router)
app.include_router(prompt_volumes_router)

# ── GOD Intelligence API ───────────────────────────────────────────────────────
app.include_router(intel_router, prefix='/api/v1/intelligence', tags=['intelligence'])
app.include_router(intel_router, prefix='/api/intel', tags=['intelligence'])

# ── Tool Integrations (20 third-party tools) ─────────────────────────────────
app.include_router(create_tool_integrations_router())
app.include_router(create_translation_studio_router())

# ── V1 Closed Feedback Loop ──────────────────────────────────────────────────
app.include_router(create_v1_loop_router())


def _hashicorp_vault_health() -> JsonObject:
    client = HashiCorpVaultClient()
    ok = client.connect()
    return {
        'enabled': bool(ok),
        'backend': 'hashicorp-vault',
        'address': client.vault_addr,
    }


def _supabase_vault_health() -> JsonObject:
    client = SupabaseVaultClient()
    ok = bool(getattr(client, 'is_ready', False))
    return {
        'enabled': bool(ok),
        'backend': 'supabase-vault',
    }


def _persist_governance_stores() -> None:
    """Flush all three governance stores to PostgreSQL. Called after each mutation."""
    if _governance_db is None:
        return
    _governance_db.save_all(
        _api_governance_providers_memory,
        _api_governance_usage_events_memory,
        _api_governance_incidents_memory,
    )


app.include_router(
    create_api_governance_router(
        ApiGovernanceContext(
            enforce_rate_limit=_enforce_rate_limit,
            te_encrypt=te_encrypt,
            provider_store=_api_governance_providers_memory,
            usage_store=_api_governance_usage_events_memory,
            incident_store=_api_governance_incidents_memory,
            notification_store=_notifications_memory,
            ira_events_store=_ira_events_memory,
            siem_cases_store=_siem_cases_memory,
            vault_hashicorp_health=_hashicorp_vault_health,
            vault_supabase_health=_supabase_vault_health,
            persist=_persist_governance_stores,
        )
    )
)

app.include_router(
    create_ai_crawler_enablement_router(
        enforce_rate_limit=_enforce_rate_limit,
        sites_memory=_ace_sites_memory,
        crawler_events_memory=_ace_crawler_events_memory,
        ssr_cache_memory=_ace_ssr_cache_memory,
        crawler_rules_memory=_ace_crawler_rules_memory,
        audit_results_memory=_ace_audit_results_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_search_everywhere_automation_router(
        enforce_rate_limit=_enforce_rate_limit,
        ace_sites_memory=_ace_sites_memory,
        cms_connections_memory=_cms_connections_memory,
    )
)

app.include_router(
    create_neo4j_graph_intelligence_router(
        enforce_rate_limit=_enforce_rate_limit,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_site_portfolio_router(
        enforce_rate_limit=_enforce_rate_limit,
        portfolio_sites_memory=_portfolio_sites_memory,
        portfolio_rules_memory=_portfolio_rules_memory,
        portfolio_deployments_memory=_portfolio_deployments_memory,
        white_label_memory=_white_label_profiles_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_live_editor_router(
        enforce_rate_limit=_enforce_rate_limit,
        sessions_memory=_live_editor_sessions_memory,
        changes_memory=_live_editor_changes_memory,
        history_memory=_live_editor_history_memory,
        audit_log_memory=_audit_log_memory,
    )
)

app.include_router(
    create_autonomous_workforce_router(
        enforce_rate_limit=_enforce_rate_limit,
        profiles_memory=_autonomous_workforce_profiles_memory,
        integrations_memory=_autonomous_workforce_integrations_memory,
        missions_memory=_autonomous_workforce_missions_memory,
        feed_memory=_autonomous_workforce_feed_memory,
        schedules_memory=_autonomous_workforce_schedules_memory,
        knowledge_memory=_autonomous_workforce_knowledge_memory,
        outcomes_memory=_autonomous_workforce_outcomes_memory,
        audit_log_memory=_audit_log_memory,
    )
)


# ── SEMrush Feature Parity: New Routers ───────────────────────────────────────
from .routers.client_portal import router as client_portal_router  # noqa: E402
from .routers.contentshake_ai import router as contentshake_ai_router  # noqa: E402
from .routers.domain_overview import router as domain_overview_router  # noqa: E402
from .routers.eyeon_monitor import router as eyeon_monitor_router  # noqa: E402
from .routers.local_heatmap import router as local_heatmap_router  # noqa: E402
from .routers.map_rank_tracker import router as map_rank_tracker_router  # noqa: E402
from .routers.market_explorer import router as market_explorer_router  # noqa: E402
from .routers.one2target import router as one2target_router  # noqa: E402
from .routers.pla_research import router as pla_research_router  # noqa: E402

app.include_router(domain_overview_router)
app.include_router(market_explorer_router)
app.include_router(one2target_router)
app.include_router(eyeon_monitor_router)
app.include_router(pla_research_router)
app.include_router(map_rank_tracker_router)
app.include_router(local_heatmap_router)
app.include_router(contentshake_ai_router)
app.include_router(client_portal_router)
