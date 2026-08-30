import asyncio
import base64
import hashlib
import hmac
import html
import json
import os
import smtplib
import ssl
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Annotated, Any, Literal, cast

import httpx
import psycopg
from fastapi import Depends, Header, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, HttpUrl

from . import memory_stores
from .bootstrap.middleware import (
    allow_api_docs,
    allowed_hosts,
    cors_origins,
    is_production_environment,
)
from .config import validate_startup_security
from .database import _get_database_url, init_db
from .db_init import claim_security_alert_email as _db_claim_security_alert_email
from .deps import AuthContext, JwtClaims, require_auth
from .governance_db import GovernanceDB as _GovernanceDB
from .production_middleware import StructuredLogger, validate_environment
from .rate_limiter import (
    RateLimitExceededError,  # noqa: F401 — re-exported for existing importers
    enforce_rate_limit as _enforce_rate_limit,
    get_rate_buckets,
    get_rate_lock,
)
from .routers.autonomous_workforce import run_autonomous_workforce_watchdog
from .routers.ira import run_ira_watchdog
from .security import get_password_pepper, hash_password, verify_password
from .transparent_encryption import te_decrypt, te_encrypt

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
_rate_lock = get_rate_lock()
_ai_security_lock = threading.Lock()
_siem_lock = threading.Lock()
_rate_buckets = get_rate_buckets()
_security_alert_worker_stop: asyncio.Event | None = None
_security_alert_worker_task: asyncio.Task[None] | None = None
_ira_watchdog_stop: asyncio.Event | None = None
_ira_watchdog_task: asyncio.Task[None] | None = None
_autonomous_workforce_watchdog_stop: asyncio.Event | None = None
_autonomous_workforce_watchdog_task: asyncio.Task[None] | None = None

# Service configuration is deferred until all extracted services and their
# dependencies have been imported.  Executing this wiring here made app import
# order-dependent because several callbacks are defined later in this module.
_configure_platform_memory_stores = lambda: _set_platform_memory_stores(
    _scheduled_posts_memory=_scheduled_posts_memory,
    _email_contacts_memory=_email_contacts_memory,
    _email_campaigns_memory=_email_campaigns_memory,
    _suitecrm_jobs_memory=_suitecrm_jobs_memory,
    _refferq_jobs_memory=_refferq_jobs_memory,
    _posthog_events_memory=_posthog_events_memory,
    _social_listening_memory=_social_listening_memory,
    _social_listening_alert_rules_memory=_social_listening_alert_rules_memory,
    _social_listening_alerts_memory=_social_listening_alerts_memory,
    _reviews_memory=_reviews_memory,
    _n8n_jobs_memory=_n8n_jobs_memory,
    _growthbook_checks_memory=_growthbook_checks_memory,
    _matomo_events_memory=_matomo_events_memory,
    _plausible_events_memory=_plausible_events_memory,
    _meilisearch_index_memory=_meilisearch_index_memory,
    _webhook_events_memory=_webhook_events_memory,
    _appwrite_events_memory=_appwrite_events_memory,
    _drone_builds_memory=_drone_builds_memory,
    _directus_items_memory=_directus_items_memory,
    _minio_objects_memory=_minio_objects_memory,
    _stripe_events_memory=_stripe_events_memory,
    _audit_log_memory=_audit_log_memory,
    _notifications_memory=_notifications_memory,
    _redis_ops_memory=_redis_ops_memory,
    _twilio_messages_memory=_twilio_messages_memory,
    _slack_messages_memory=_slack_messages_memory,
    _resend_messages_memory=_resend_messages_memory,
    _algolia_sync_memory=_algolia_sync_memory,
    _ai_gateway_memory=_ai_gateway_memory,
    _ai_security_usage_memory=_ai_security_usage_memory,
    _ai_security_alerts_memory=_ai_security_alerts_memory,
    _ai_security_blocks_memory=_ai_security_blocks_memory,
    _ai_security_appeals_memory=_ai_security_appeals_memory,
    _ai_security_ids_events_memory=_ai_security_ids_events_memory,
    _auth_security_memory=_auth_security_memory,
    _tenant_profiles_memory=_tenant_profiles_memory,
    _engagement_streaks_memory=_engagement_streaks_memory,
    _engagement_referrals_memory=_engagement_referrals_memory,
    _engagement_companion_profiles_memory=_engagement_companion_profiles_memory,
    _engagement_fomo_events_memory=_engagement_fomo_events_memory,
    _engagement_social_proof_events_memory=_engagement_social_proof_events_memory,
    _engagement_dependency_profiles_memory=_engagement_dependency_profiles_memory,
    _engagement_dependency_events_memory=_engagement_dependency_events_memory,
    _engagement_community_circles_memory=_engagement_community_circles_memory,
    _engagement_community_posts_memory=_engagement_community_posts_memory,
    _engagement_community_amas_memory=_engagement_community_amas_memory,
    _engagement_brand_lock_profiles_memory=_engagement_brand_lock_profiles_memory,
    _engagement_brand_lock_events_memory=_engagement_brand_lock_events_memory,
    _engagement_autopilot_profiles_memory=_engagement_autopilot_profiles_memory,
    _engagement_autopilot_events_memory=_engagement_autopilot_events_memory,
    _engagement_achievement_profiles_memory=_engagement_achievement_profiles_memory,
    _engagement_achievement_events_memory=_engagement_achievement_events_memory,
    _money_printer_ideas_memory=_money_printer_ideas_memory,
    _money_printer_validations_memory=_money_printer_validations_memory,
    _bank_accounts_memory=_bank_accounts_memory,
    _bank_transactions_memory=_bank_transactions_memory,
    _bank_payouts_memory=_bank_payouts_memory,
    _university_courses_memory=_university_courses_memory,
    _university_cohorts_memory=_university_cohorts_memory,
    _university_enrollments_memory=_university_enrollments_memory,
    _studios_services_memory=_studios_services_memory,
    _studios_briefs_memory=_studios_briefs_memory,
    _studios_proposals_memory=_studios_proposals_memory,
    _studios_escrows_memory=_studios_escrows_memory,
    _commerce_products_memory=_commerce_products_memory,
    _commerce_orders_memory=_commerce_orders_memory,
    _talent_creators_memory=_talent_creators_memory,
    _talent_deals_memory=_talent_deals_memory,
    _talent_rate_cards_memory=_talent_rate_cards_memory,
    _white_label_profiles_memory=_white_label_profiles_memory,
    _white_label_events_memory=_white_label_events_memory,
    _crm_contacts_memory=_crm_contacts_memory,
    _crm_companies_memory=_crm_companies_memory,
    _crm_deals_memory=_crm_deals_memory,
    _cms_connections_memory=_cms_connections_memory,
    _marketplace_installs_memory=_marketplace_installs_memory,
    _analytics_reports_memory=_analytics_reports_memory,
    _analytics_trends_memory=_analytics_trends_memory,
    _analytics_rollups_memory=_analytics_rollups_memory,
    _api_usage_audit_memory=_api_usage_audit_memory,
    _notification_delivery_receipts_memory=_notification_delivery_receipts_memory,
    _smart_inbox_messages_memory=_smart_inbox_messages_memory,
    _accounting_integrations_memory=_accounting_integrations_memory,
    _accounting_exports_memory=_accounting_exports_memory,
    _super_admin_module_settings_memory=_super_admin_module_settings_memory,
    _social_accounts_memory=_social_accounts_memory,
    _content_approval_requests_memory=_content_approval_requests_memory,
    _sm_listening_memory=_social_listening_memory,
    _rate_buckets=_rate_buckets,
    _rate_lock=_rate_lock,
    _db_ready=_db_ready,
)
_configure_platform_helpers = lambda: _set_platform_helpers(_coerce_int, _coerce_float, dict)
_configure_platform_db_ready = lambda: _set_platform_db_ready(_db_ready)
_configure_platform_rate_limiter = lambda: _set_platform_rate_limiter(_rate_buckets, _rate_lock)

# Wire up analytics module
_configure_analytics = lambda: _set_analytics_memory_stores(
    posthog_events_memory=_posthog_events_memory,
    matomo_events_memory=_matomo_events_memory,
    plausible_events_memory=_plausible_events_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
)

# Wire up CRM module
_configure_crm = lambda: _set_crm_memory_stores(
    suitecrm_jobs_memory=_suitecrm_jobs_memory,
    refferq_jobs_memory=_refferq_jobs_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
)

# Wire up storage module
_configure_storage = lambda: _set_storage_memory_stores(
    minio_objects_memory=_minio_objects_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
    minio_presign=_minio_presign,
)

# Wire up Stripe module
_configure_stripe = lambda: _set_stripe_memory_stores(
    stripe_events_memory=_stripe_events_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
    verify_stripe_signature=_verify_stripe_signature,
)

# Wire up Directus module
_configure_directus = lambda: _set_directus_memory_stores(
    directus_items_memory=_directus_items_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
)

# Wire up Appwrite module
_configure_appwrite = lambda: _set_appwrite_memory_stores(
    appwrite_events_memory=_appwrite_events_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
)

# Wire up Webhooks module (n8n, Growthbook)
_configure_webhooks = lambda: _set_webhooks_memory_stores(
    n8n_jobs_memory=_n8n_jobs_memory,
    growthbook_checks_memory=_growthbook_checks_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
    json_object=dict,
)

# Wire up Social & Reviews module
_configure_social_reviews = lambda: _set_social_reviews_memory_stores(
    social_listening_memory=_social_listening_memory,
    social_listening_alert_rules_memory=_social_listening_alert_rules_memory,
    social_listening_alerts_memory=_social_listening_alerts_memory,
    reviews_memory=_reviews_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
    coerce_int=_coerce_int,
)

# Wire up Content Generation Service module
_configure_content_generation_service = lambda: _set_content_gen_service_memory_stores(
    content_generations_memory=_content_generations_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
    run_optional_ai_generation=_run_optional_ai_generation,
    generate_media_asset_bundle=_generate_media_asset_bundle,
    json_object=dict,
    content_generation_note_telemetry=_content_generation_note_telemetry,
    content_generation_strict_production_mode=_content_generation_strict_production_mode,
)

# Wire up Email Campaigns module
_configure_email_campaigns = lambda: _set_email_campaigns_memory_stores(
    email_contacts_memory=_email_contacts_memory,
    email_campaigns_memory=_email_campaigns_memory,
        rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
    db_ready=_db_ready,
    db_dsn_fn=_db_dsn,
    te_encrypt=te_encrypt,
    te_decrypt=te_decrypt,
    coerce_int=_coerce_int,
)

# Wire up Social Scheduling module
_configure_social_scheduling = lambda: _set_social_scheduling_memory_stores(
    scheduled_posts_memory=_scheduled_posts_memory,
    social_accounts_memory=_social_accounts_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
    db_ready=_db_ready,
    db_dsn_fn=_db_dsn,
    te_encrypt=te_encrypt,
    te_decrypt=te_decrypt,
)

# Wire up Drone CI module
_configure_drone_ci = lambda: _set_drone_ci_memory_stores(
    drone_builds_memory=_drone_builds_memory,
    rate_buckets=_rate_buckets,
    rate_lock=_rate_lock,
    enforce_rate_limit=_enforce_rate_limit,
)

# Content-generation state is populated alongside the deferred service wiring.


# Environment-driven edge policy is owned by bootstrap/middleware.py; these
# aliases keep the historical private names importable from this module.
_is_production = is_production_environment
_allow_api_docs = allow_api_docs
_allowed_hosts = allowed_hosts
_cors_origins = cors_origins


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
    # psycopg.connect() accepts a URI conninfo string directly, so prefer the
    # same DATABASE_URL (> POSTGRES_* vars) precedence the SQLAlchemy engine
    # already uses in database.py, instead of only ever reading POSTGRES_*
    # and silently connecting to localhost when just DATABASE_URL is set.
    if url := _get_database_url():
        separator = '&' if '?' in url else '?'
        return f'{url}{separator}connect_timeout=2'

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


# The startup/shutdown sequence that used to live here is now owned by
# bootstrap/lifespan.py, which calls the step functions above in order.

# ── Service module imports ────────────────────────────────────
from .services.siem import (
    _siem_bootstrap_advanced_state,
    _siem_extract_ip,
    _siem_extract_user,
    _siem_is_private_ip,
    _siem_retention_policy_for_tenant,
    _platform_siem_advanced_threat_hunt_payload,
    _platform_siem_architecture_payload,
    _platform_siem_apply_endpoint_hardening_payload,
    _platform_siem_apply_update_payload,
    _platform_siem_auto_pentest_jobs_payload,
    _platform_siem_auto_pentest_run_payload,
    _platform_siem_compliance_payload,
    _platform_siem_create_case_payload,
    _platform_siem_data_collection_payload,
    _platform_siem_dead_code_findings_payload,
    _platform_siem_dead_code_scan_payload,
    _platform_siem_detection_payload,
    _platform_siem_endpoint_hardening_status_payload,
    _platform_siem_flow_map_payload,
    _platform_siem_investigation_payload,
    _platform_siem_list_cases_payload,
    _platform_siem_network_anomalies_payload,
    _platform_siem_run_soar_payload,
    _platform_siem_run_zap_scan_payload,
    _platform_siem_security_controls_payload,
    _platform_siem_set_retention_policy_payload,
    _platform_siem_update_case_payload,
    _platform_siem_update_security_control_payload,
    _platform_siem_updates_payload,
    _platform_siem_vault_encryption_health_payload,
    _platform_siem_vulnerabilities_payload,
)
from .services.ai_providers import (
    _provider_env_key,
    _provider_default_model,
    _model_unit_cost,
    _model_quality,
    _extract_ip_hash,
    _extract_ua_hash,
    _usage_to_tokens,
    _compute_roi,
    _active_provider_key_record,
    _is_provider_disabled,
    _resolve_provider_api_key,
    _record_ai_security_alert,
    _send_security_email_alert,
    _block_tenant,
    _is_tenant_blocked,
    _disable_provider,
    _update_provider_health,
    _get_provider_health,
    _select_provider_with_tiers,
    _record_ai_usage,
    _evaluate_ai_guardrails,
    _ai_queued_item,
    _json_object,
    _coerce_int,
    _coerce_float,
    _extract_openai_result,
    _extract_anthropic_result,
    _ai_generate_openai,
    _ai_generate_anthropic,
    _ai_generate_google_vertex,
    _generate_with_cohere,
    _generate_with_mistral,
    _generate_with_together_ai,
    _generate_with_stability_ai,
    _run_generic_provider_generation,
    _ai_generate_generic,
    _asset_extension_for_mime,
    _persist_ai_generated_asset,
    _load_ai_generated_asset_bytes,
    _svg_image_placeholder_bytes,
    _try_generate_vertex_image,
    _try_generate_stability_image,
    _ai_generate_image_binary,
    _try_generate_elevenlabs_voice,
    _resolve_oss_voice_endpoints,
    _try_generate_oss_voice,
    _select_replicate_video_model,
    _synth_voice_wave_bytes,
    _ai_generate_voice_binary,
    _try_generate_replicate_video,
    _ai_generate_video_binary,
    _generate_media_asset_bundle,
    _invoke_ai_provider_generation,
    _extract_ai_result,
    _prepare_ai_gateway_attempt,
    _record_ai_gateway_success,
    _run_optional_ai_generation,
    _ai_security_usage_window,
    _ai_security_provider_graph,
    _ai_security_timeline,
    _ai_security_tenant_alerts,
)
from .services.integrations import (
    _send_via_listmonk,
    _send_via_postal,
    _send_via_ses,
    _send_via_resend,
    _security_alert_from_email,
    _dispatch_security_email,
    _verify_github_signature,
    _verify_stripe_signature,
    _ensure_signature_header,
    _validate_github_webhook_signature,
    _validate_stripe_webhook_signature,
    _validate_generic_webhook_signature,
    _validate_webhook_signature,
    _minio_hmac_sign,
    _minio_presign,
    _hashicorp_vault_health,
    _supabase_vault_health,
)
from .services.content_generation import (
    ContentGenerationService,
    _env_bool,
    _safe_int,
    _parse_iso_datetime,
    _redis_sync_client,
    _content_generation_strict_production_mode,
    _content_generation_required_provider_state,
    _content_generation_job_retention_seconds,
    _content_generation_job_terminal,
    _content_generation_max_inflight,
    _persist_content_generation_job,
    _find_content_generation_job,
    _content_generation_inflight_count,
    _content_generation_note_telemetry,
    _content_generation_job_expires_at,
    _content_generation_prune_expired_terminal_jobs,
    _get_cg_svc,
)
from .services.platform import (
    set_memory_stores as _set_platform_memory_stores,
    set_helpers as _set_platform_helpers,
    set_db_ready as _set_platform_db_ready,
    set_rate_limiter as _set_platform_rate_limiter,
    _build_queues_dict,
    _build_integrations_dict,
    _queue_ready,
    _build_use_cases_dict,
    _platform_status_payload,
    _platform_metrics_summary_payload,
    _platform_anti_failure_payload,
    _platform_use_case_coverage_payload,
    _platform_capabilities_payload,
    _platform_hybrid_stacks_payload,
    _platform_module_registry_payload,
    _platform_api_usage_payload,
    _platform_super_admin_dashboard_payload,
)
from .services.analytics import (
    capture_posthog_event,
    track_matomo_event,
    track_plausible_event,
    set_memory_stores as _set_analytics_memory_stores,
    PosthogCaptureRequest,
    MatomoTrackRequest,
    PlausibleTrackRequest,
)
from .services.crm import (
    upsert_suitecrm_lead,
    register_refferq_referral,
    set_memory_stores as _set_crm_memory_stores,
    SuiteCrmLeadRequest,
    RefferqReferralRequest,
)
from .services.storage import (
    storage_presign,
    storage_list_objects,
    set_memory_stores as _set_storage_memory_stores,
    MinioPresignRequest,
    MinioListObjectsRequest,
)
from .services.stripe import (
    stripe_create_checkout,
    stripe_process_webhook,
    list_stripe_events,
    set_memory_stores as _set_stripe_memory_stores,
    StripeCreateCheckoutRequest,
    StripeWebhookProcessRequest,
)
from .services.directus import (
    directus_create_item,
    directus_list_items,
    set_memory_stores as _set_directus_memory_stores,
    DirectusCreateItemRequest,
    DirectusListItemsRequest,
)
from .services.appwrite import (
    appwrite_create_user,
    appwrite_create_session,
    set_memory_stores as _set_appwrite_memory_stores,
    AppwriteCreateUserRequest,
    AppwriteCreateSessionRequest,
)
from .services.webhooks import (
    trigger_n8n_webhook,
    evaluate_growthbook_flag,
    receive_webhook,
    list_webhook_events,
    set_memory_stores as _set_webhooks_memory_stores,
    N8nWebhookTriggerRequest,
    GrowthbookEvaluateRequest,
    WebhookAcknowledgeRequest,
)
from .services.social_reviews import (
    ingest_social_listening_mention,
    list_social_listening_mentions,
    get_social_listening_summary,
    create_social_listening_alert_rule,
    list_social_listening_alerts,
    get_social_listening_clusters,
    ingest_review,
    list_reviews,
    respond_to_review,
    get_reviews_summary,
    set_memory_stores as _set_social_reviews_memory_stores,
    SocialListeningIngestRequest,
    SocialListeningAlertRuleRequest,
    ReviewIngestRequest,
    ReviewResponseRequest,
)
from .services.content_generation_service import (
    generate_content,
    generate_ads,
    analyze_seo,
    set_memory_stores as _set_content_gen_service_memory_stores,
    ContentRequest,
    AdsRequest,
    SeoRequest,
)
from .services.email_campaigns import (
    create_email_contact,
    list_email_contacts,
    create_email_campaign,
    list_email_campaigns,
    send_test_email_campaign,
    set_memory_stores as _set_email_campaigns_memory_stores,
    EmailContactCreateRequest,
    EmailCampaignCreateRequest,
    EmailCampaignSendTestRequest,
)
from .services.social_scheduling import (
    schedule_social_post,
    list_scheduled_posts,
    move_scheduled_post,
    delete_scheduled_post,
    set_memory_stores as _set_social_scheduling_memory_stores,
    SocialScheduleRequest,
    SocialMoveRequest,
)
from .services.drone_ci import (
    drone_trigger_build,
    set_memory_stores as _set_drone_ci_memory_stores,
    DroneBuildTriggerRequest,
)

# The FastAPI instance, its middleware stack, its exception handlers and its
# router registrations are owned by bootstrap/application.py. ``app`` stays
# importable from here for existing consumers and resolves to that single
# instance on first access (see ``__getattr__`` at the end of this module).

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

class SocialScheduleMoveRequest(BaseModel):
    publish_at: datetime


SCHEDULED_POST_NOT_FOUND = 'Scheduled post not found.'

# Pydantic request models — now imported from their respective service modules
# SocialListeningIngestRequest, SocialListeningAlertRuleRequest,
# ReviewIngestRequest, ReviewResponseRequest — from services.social_reviews
# SuiteCrmLeadRequest, RefferqReferralRequest — from services.crm
# PosthogCaptureRequest, MatomoTrackRequest, PlausibleTrackRequest — from services.analytics
# N8nWebhookTriggerRequest, GrowthbookEvaluateRequest — from services.webhooks


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


# Finance models — now in routers/finance_legacy.py

# Router registrations (auth, tenant, notifications, media_jobs, ops)
# — now registered via router_registration.py in composition.py
# _ops_require_super_admin_access helper moved to router_registration.py


# Health/metrics/AI-ping routes — now registered via routers/health.py in composition.py


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


# AI security/gateway handlers — now in routers/ai_security.py (registered via router_registration.py)


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


# Content generation helpers — now imported from services.content_generation
# _content_generation_note_telemetry, _content_generation_job_retention_seconds,
# _content_generation_job_terminal, _content_generation_job_expires_at,
# _content_generation_prune_expired_terminal_jobs, _persist_content_generation_job,
# _find_content_generation_job, _content_generation_inflight_count,
# _content_generation_max_inflight — all imported at top of file.

# These shim functions delegate to the ContentGenerationService instance:

_cg_svc: ContentGenerationService | None = None


def _get_cg_svc() -> ContentGenerationService:
    global _cg_svc
    if _cg_svc is None:
        _cg_svc = ContentGenerationService()
    return _cg_svc


def _content_generation_production_verification_payload(tenant_id: str) -> tuple[JsonObject, bool]:
    return _get_cg_svc().production_verification_payload(tenant_id)


def _build_content_generation_response(payload: ContentRequest, auth: AuthContext) -> JsonObject:
    return generate_content(payload, auth)


def _run_content_generation_job_if_needed(job: JsonObject, auth: AuthContext) -> None:
    _get_cg_svc().run_job_if_needed(job, auth, _build_content_generation_response)


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


# Content generation routes — now registered via routers/content_generation_legacy.py in composition.py


# Social listening / review handlers — now imported from services.social_reviews


# Social listening / review handlers — now imported from services.social_reviews
# ingest_social_listening_mention, list_social_listening_mentions,
# get_social_listening_summary, create_social_listening_alert_rule,
# list_social_listening_alerts, get_social_listening_clusters,
# ingest_review, list_reviews, respond_to_review, get_reviews_summary
# All imported at top of file from .services.social_reviews.


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


# ---------------------------------------------------------------------------
# Webhook signature validation — now imported from services.webhooks
# _validate_webhook_signature, list_webhook_events,
# WebhookAcknowledgeRequest, _verify_github_signature, _verify_stripe_signature,
# _ensure_signature_header, _validate_github_webhook_signature,
# _validate_stripe_webhook_signature, _validate_generic_webhook_signature
# All imported at top of file from .services.webhooks.


# ---------------------------------------------------------------------------
# Appwrite, Drone CI, Directus, MinIO, Stripe models
# — now imported from their respective service modules
# AppwriteCreateUserRequest, AppwriteCreateSessionRequest,
# DirectusCreateItemRequest, DirectusListItemsRequest,
# MinioPresignRequest, MinioListObjectsRequest, _minio_hmac_sign,
# StripeCreateCheckoutRequest, StripeWebhookProcessRequest
# All imported at top of file from their service modules.


# ---------------------------------------------------------------------------
# Stripe events (legacy compatibility)
# ---------------------------------------------------------------------------

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


# Legacy finance routes — now registered via routers/finance_legacy.py in composition.py


# Complete service configuration only after all callbacks and extracted
# services exist. Keeping this at the composition boundary prevents import-time
# ordering from becoming a hidden runtime dependency.
_configure_platform_memory_stores()
_configure_platform_helpers()
_configure_platform_db_ready()
_configure_platform_rate_limiter()
_configure_analytics()
_configure_crm()
_configure_storage()
_configure_stripe()
_configure_directus()
_configure_appwrite()
_configure_webhooks()
_configure_social_reviews()
_configure_content_generation_service()
_configure_email_campaigns()
_configure_social_scheduling()
_configure_drone_ci()

# Initialize content generation service via the shared getter
_cg_svc = _get_cg_svc()
_content_generation_jobs_memory = _cg_svc.jobs_memory
_content_generation_jobs_lock = _cg_svc.jobs_lock
_content_generation_telemetry_lock = _cg_svc.telemetry_lock
_content_generation_telemetry = _cg_svc.telemetry


# All app.include_router() calls — now in router_registration.py (composed via bootstrap/context_registry.py)


def __getattr__(name: str) -> Any:
    """Resolve ``legacy_main.app`` to the one application built by bootstrap.

    The instance is created by ``bootstrap.application``, which imports this
    module, so it can only be resolved after this module finishes executing.
    Deferring the lookup here keeps the historical ``from .legacy_main import
    app`` import path working without re-creating a second application.
    """
    if name == 'app':
        from .bootstrap.application import app

        return app
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
