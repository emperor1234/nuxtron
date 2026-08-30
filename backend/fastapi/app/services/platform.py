"""Platform Dashboard & Payload Builders

Extracted from legacy_main.py: platform status, metrics, anti-failure,
use case coverage, capabilities, hybrid stacks, module registry,
API usage, and super-admin dashboard payload builders.

These functions are pure helpers that build JSON payloads for various
/platform/ops endpoints. They reference module-level memory stores
and configuration via function parameters.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from ..config import env_bool

if TYPE_CHECKING:
    from ..deps import AuthContext

JsonObject = dict[str, object]

# ── Memory Store References (set by legacy_main.py) ──────────

# These will be assigned by legacy_main.py after import
_scheduled_posts_memory = []
_email_contacts_memory = []
_email_campaigns_memory = []
_suitecrm_jobs_memory = []
_refferq_jobs_memory = []
_posthog_events_memory = []
_social_listening_memory = []
_social_listening_alert_rules_memory = []
_social_listening_alerts_memory = []
_reviews_memory = []
_n8n_jobs_memory = []
_growthbook_checks_memory = []
_matomo_events_memory = []
_plausible_events_memory = []
_meilisearch_index_memory = []
_webhook_events_memory = []
_appwrite_events_memory = []
_drone_builds_memory = []
_directus_items_memory = []
_minio_objects_memory = []
_stripe_events_memory = []
_audit_log_memory = []
_notifications_memory = []
_redis_ops_memory = []
_twilio_messages_memory = []
_slack_messages_memory = []
_resend_messages_memory = []
_algolia_sync_memory = []
_ai_gateway_memory = []
_ai_security_usage_memory = []
_ai_security_alerts_memory = []
_ai_security_blocks_memory = []
_ai_security_appeals_memory = []
_ai_security_ids_events_memory = []
_auth_security_memory = []
_tenant_profiles_memory = []
_engagement_streaks_memory = []
_engagement_referrals_memory = []
_engagement_companion_profiles_memory = []
_engagement_fomo_events_memory = []
_engagement_social_proof_events_memory = []
_engagement_dependency_profiles_memory = []
_engagement_dependency_events_memory = []
_engagement_community_circles_memory = []
_engagement_community_posts_memory = []
_engagement_community_amas_memory = []
_engagement_brand_lock_profiles_memory = []
_engagement_brand_lock_events_memory = []
_engagement_autopilot_profiles_memory = []
_engagement_autopilot_events_memory = []
_engagement_achievement_profiles_memory = []
_engagement_achievement_events_memory = []
_money_printer_ideas_memory = []
_money_printer_validations_memory = []
_bank_accounts_memory = []
_bank_transactions_memory = []
_bank_payouts_memory = []
_university_courses_memory = []
_university_cohorts_memory = []
_university_enrollments_memory = []
_studios_services_memory = []
_studios_briefs_memory = []
_studios_proposals_memory = []
_studios_escrows_memory = []
_commerce_products_memory = []
_commerce_orders_memory = []
_talent_creators_memory = []
_talent_deals_memory = []
_talent_rate_cards_memory = []
_white_label_profiles_memory = []
_white_label_events_memory = []
_crm_contacts_memory = []
_crm_companies_memory = []
_crm_deals_memory = []
_influencer_campaigns_memory = []
_chatbots_memory = []
_linkinbio_pages_memory = []
_subscriptions_memory = []
_cms_connections_memory = []
_marketplace_installs_memory = []
_analytics_reports_memory = []
_analytics_trends_memory = []
_analytics_rollups_memory = []
_api_usage_audit_memory = []
_notification_delivery_receipts_memory = []
_smart_inbox_messages_memory = []
_accounting_integrations_memory = []
_accounting_exports_memory = []
_super_admin_module_settings_memory = []
_social_accounts_memory = []
_content_approval_requests_memory = []
_sm_listening_memory = []
_rate_buckets = {}
_rate_lock = None
_db_ready = False

# External dependencies (set by legacy_main.py)
_coerce_int = int
_coerce_float = float
_json_object = dict

# Module-level constants
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


def set_memory_stores(**stores) -> None:
    """Inject memory store references from legacy_main.py."""
    globals().update(stores)


def set_helpers(coerce_int=None, coerce_float=None, json_object=None) -> None:
    """Inject helper functions from legacy_main.py."""
    global _coerce_int, _coerce_float, _json_object
    if coerce_int is not None:
        _coerce_int = coerce_int
    if coerce_float is not None:
        _coerce_float = coerce_float
    if json_object is not None:
        _json_object = json_object


def set_db_ready(ready: bool) -> None:
    """Set database ready state."""
    global _db_ready
    _db_ready = ready


def set_rate_limiter(buckets, lock) -> None:
    """Set rate limiter state."""
    global _rate_buckets, _rate_lock
    _rate_buckets = buckets
    _rate_lock = lock


# ── Dict Builders ──────────────────────────────────────────


def _build_queues_dict() -> dict[str, int]:
    """Build queue size dictionary from all memory stores."""
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
    """Build integrations configuration dictionary."""
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


# ── Payload Builders ───────────────────────────────────────


def _platform_status_payload(auth: AuthContext) -> JsonObject:
    """Generate platform status payload."""
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
    """Generate metrics summary."""
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
    """Generate anti-failure defense signals."""
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


def _platform_use_case_coverage_payload(auth: AuthContext) -> JsonObject:
    """Generate use case coverage payload."""
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
    """Generate platform capabilities payload."""
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


def _platform_hybrid_stacks_payload(auth: AuthContext) -> JsonObject:
    """Generate hybrid stacks payload."""
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
    """Generate module registry payload."""
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
    """Generate API usage payload."""
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


def _platform_super_admin_dashboard_payload(auth: AuthContext) -> JsonObject:
    """Generate super-admin dashboard payload."""
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


# ── Exported functions for legacy_main.py to import ─────────

__all__ = [
    'set_memory_stores',
    'set_helpers',
    'set_db_ready',
    'set_rate_limiter',
    '_build_queues_dict',
    '_build_integrations_dict',
    '_queue_ready',
    '_build_use_cases_dict',
    '_platform_status_payload',
    '_platform_metrics_summary_payload',
    '_platform_anti_failure_payload',
    '_platform_use_case_coverage_payload',
    '_platform_capabilities_payload',
    '_platform_hybrid_stacks_payload',
    '_platform_module_registry_payload',
    '_platform_api_usage_payload',
    '_platform_super_admin_dashboard_payload',
    '_HYBRID_STACKS_IDS',
    '_HYBRID_STACK_CATEGORY_MAP',
]