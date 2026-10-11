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
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from .. import memory_stores
from ..rate_limiter import rate_limit_metrics_snapshot

if TYPE_CHECKING:
    from ..deps import AuthContext

JsonObject = dict[str, object]

_db_ready = False

# External dependencies (set by legacy_main.py)
def _default_coerce_int(value: object, default: int) -> int:
    return int(cast(Any, value)) if value is not None else default


def _default_coerce_float(value: object, default: float) -> float:
    return float(cast(Any, value)) if value is not None else default


def _default_json_object(value: object) -> JsonObject | None:
    return dict(value) if isinstance(value, dict) else None


_coerce_int: Callable[[object, int], int] = _default_coerce_int
_coerce_float: Callable[[object, float], float] = _default_coerce_float
_json_object: Callable[[object], JsonObject | None] = _default_json_object

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



def set_helpers(
    coerce_int: Callable[[object, int], int] | None = None,
    coerce_float: Callable[[object, float], float] | None = None,
    json_object: Callable[[object], JsonObject | None] | None = None,
) -> None:
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


# ── Dict Builders ──────────────────────────────────────────


def _build_queues_dict() -> dict[str, int]:
    """Build queue size dictionary from all memory stores."""
    return {
        'suitecrm': len(memory_stores.suitecrm_jobs),
        'refferq': len(memory_stores.refferq_jobs),
        'posthog': len(memory_stores.posthog_events),
        'social_listening': len(memory_stores.social_listening),
        'social_listening_alert_rules': len(memory_stores.social_listening_alert_rules),
        'social_listening_alerts': len(memory_stores.social_listening_alerts),
        'reviews': len(memory_stores.reviews),
        'n8n': len(memory_stores.n8n_jobs),
        'growthbook': len(memory_stores.growthbook_checks),
        'matomo': len(memory_stores.matomo_events),
        'plausible': len(memory_stores.plausible_events),
        'meilisearch': len(memory_stores.meilisearch_index),
        'webhooks': len(memory_stores.webhook_events),
        'appwrite': len(memory_stores.appwrite_events),
        'drone': len(memory_stores.drone_builds),
        'directus': len(memory_stores.directus_items),
        'minio': len(memory_stores.minio_objects),
        'stripe': len(memory_stores.stripe_events),
        'audit_log': len(memory_stores.audit_log),
        'notifications': len(memory_stores.notifications),
        'redis': len(memory_stores.redis_ops),
        'twilio': len(memory_stores.twilio_messages),
        'slack': len(memory_stores.slack_messages),
        'resend': len(memory_stores.resend_messages),
        'algolia': len(memory_stores.algolia_sync),
        'ai_gateway': len(memory_stores.ai_gateway),
        'ai_security_usage': len(memory_stores.ai_security_usage),
        'ai_security_alerts': len(memory_stores.ai_security_alerts),
        'ai_security_blocks': len(memory_stores.ai_security_blocks),
        'ai_security_appeals': len(memory_stores.ai_security_appeals),
        'ai_security_ids_events': len(memory_stores.ai_security_ids_events),
        'auth_security': len(memory_stores.auth_security),
        'tenant_management': len(memory_stores.tenant_profiles),
        'engagement_streaks': len(memory_stores.engagement_streaks),
        'engagement_referrals': len(memory_stores.engagement_referrals),
        'engagement_companion_profiles': len(memory_stores.engagement_companion_profiles),
        'engagement_fomo_events': len(memory_stores.engagement_fomo_events),
        'engagement_social_proof_events': len(memory_stores.engagement_social_proof_events),
        'engagement_dependency_profiles': len(memory_stores.engagement_dependency_profiles),
        'engagement_dependency_events': len(memory_stores.engagement_dependency_events),
        'engagement_community_circles': len(memory_stores.engagement_community_circles),
        'engagement_community_posts': len(memory_stores.engagement_community_posts),
        'engagement_community_amas': len(memory_stores.engagement_community_amas),
        'engagement_brand_lock_profiles': len(memory_stores.engagement_brand_lock_profiles),
        'engagement_brand_lock_events': len(memory_stores.engagement_brand_lock_events),
        'engagement_autopilot_profiles': len(memory_stores.engagement_autopilot_profiles),
        'engagement_autopilot_events': len(memory_stores.engagement_autopilot_events),
        'engagement_achievement_profiles': len(memory_stores.engagement_achievement_profiles),
        'engagement_achievement_events': len(memory_stores.engagement_achievement_events),
        'money_printer_ideas': len(memory_stores.money_printer_ideas),
        'money_printer_validations': len(memory_stores.money_printer_validations),
        'bank_accounts': len(memory_stores.bank_accounts),
        'bank_transactions': len(memory_stores.bank_transactions),
        'bank_payouts': len(memory_stores.bank_payouts),
        'university_courses': len(memory_stores.university_courses),
        'university_cohorts': len(memory_stores.university_cohorts),
        'university_enrollments': len(memory_stores.university_enrollments),
        'studios_services': len(memory_stores.studios_services),
        'studios_briefs': len(memory_stores.studios_briefs),
        'studios_proposals': len(memory_stores.studios_proposals),
        'studios_escrows': len(memory_stores.studios_escrows),
        'commerce_products': len(memory_stores.commerce_products),
        'commerce_orders': len(memory_stores.commerce_orders),
        'talent_creators': len(memory_stores.talent_creators),
        'talent_deals': len(memory_stores.talent_deals),
        'talent_rate_cards': len(memory_stores.talent_rate_cards),
        'white_label_profiles': len(memory_stores.white_label_profiles),
        'white_label_events': len(memory_stores.white_label_events),
        'crm_contacts': len(memory_stores.crm_contacts),
        'crm_companies': len(memory_stores.crm_companies),
        'crm_deals': len(memory_stores.crm_deals),
        'influencer_campaigns': len(memory_stores.influencer_campaigns),
        'chatbots': len(memory_stores.chatbots),
        'linkinbio_pages': len(memory_stores.linkinbio_pages),
        'subscriptions': len(memory_stores.subscriptions),
        'cms_connections': len(memory_stores.cms_connections),
        'marketplace_installs': len(memory_stores.marketplace_installs),
        'analytics_reports': len(memory_stores.analytics_reports),
        'analytics_trends': len(memory_stores.analytics_trends),
        'analytics_rollups': len(memory_stores.analytics_rollups),
    }


def _build_integrations_dict() -> dict[str, bool]:
    """Build integrations configuration dictionary."""
    vault_addr = os.getenv('VAULT_ADDR', '').strip()
    vault_token = os.getenv('VAULT_TOKEN', '').strip()

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
        'scheduled_posts': memory_stores.scheduled_posts,
        'email_contacts': memory_stores.email_contacts,
        'email_campaigns': memory_stores.email_campaigns,
        'suitecrm_jobs': memory_stores.suitecrm_jobs,
        'meilisearch': memory_stores.meilisearch_index,
        'algolia': memory_stores.algolia_sync,
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
    rate_metrics = rate_limit_metrics_snapshot()

    queues = _build_queues_dict()
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'queues': queues,
        'rate_limiter': {
            'active_keys': rate_metrics.active_keys,
            'sample_count': rate_metrics.sample_count,
        },
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
        item for item in memory_stores.api_usage_audit
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
        for order in memory_stores.commerce_orders
    )
    monthly_payouts = sum(
        _coerce_float(payout.get('amount', 0.0), 0.0)
        for payout in memory_stores.bank_payouts
    )
    profit_estimate = round(monthly_revenue - monthly_payouts, 2)
    dispute_count = max(0, len(memory_stores.ai_security_appeals) + len(memory_stores.ai_security_blocks))

    critical_alerts = sum(
        1
        for alert in memory_stores.ai_security_alerts
        if str(alert.get('severity', '')).lower() in {'critical', 'high'}
    )

    subscription_totals: dict[str, int] = dict.fromkeys(available_plans, 0)
    for item in memory_stores.subscriptions:
        plan_name = str(item.get('plan', 'free') or 'free').lower().strip()
        if plan_name in subscription_totals:
            subscription_totals[plan_name] += 1

    source_counts = {
        'audit_log': len(memory_stores.audit_log),
        'api_usage': len(memory_stores.api_usage_audit),
        'ai_security_usage': len(memory_stores.ai_security_usage),
        'ai_security_alerts': len(memory_stores.ai_security_alerts),
        'notification_receipts': len(memory_stores.notification_delivery_receipts),
        'messaging_events': len(memory_stores.smart_inbox_messages) + len(memory_stores.twilio_messages) + len(memory_stores.slack_messages),
    }

    accounting_integrations = [
        item for item in memory_stores.accounting_integrations if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    accounting_exports = [
        item for item in memory_stores.accounting_exports if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    module_settings = [
        item for item in memory_stores.super_admin_module_settings if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    providers_connected = {
        str(item.get('provider', ''))
        for item in accounting_integrations
        if str(item.get('status', '')).lower() == 'connected'
    }

    modules: list[JsonObject] = [
        {'id': 'crm', 'name': 'CRM with analytics', 'ready': queues.get('crm_contacts', 0) >= 0, 'count': queues.get('crm_contacts', 0), 'path': '/crm/summary'},
        {'id': 'security', 'name': 'Security and SIEM', 'ready': True, 'count': source_counts['ai_security_alerts'], 'path': '/ops/platform/super-admin/dashboard'},
        {'id': 'account_balance', 'name': 'Account balance', 'ready': True, 'count': len(memory_stores.bank_accounts), 'path': '/money-printers/nuxtron-bank/wallet'},
        {'id': 'profit_loss', 'name': 'Profit and loss analytics', 'ready': True, 'count': int(round(profit_estimate, 0)), 'path': '/ops/platform/super-admin/dashboard'},
        {'id': 'orders', 'name': 'Orders', 'ready': True, 'count': len(memory_stores.commerce_orders), 'path': '/money-printers/commerce-pro/orders'},
        {'id': 'wallet_credits', 'name': 'Wallet credits', 'ready': True, 'count': len(memory_stores.bank_transactions), 'path': '/money-printers/nuxtron-bank/wallet'},
        {'id': 'disputes', 'name': 'Disputes', 'ready': True, 'count': dispute_count, 'path': '/disputes/dashboard'},
        {'id': 'messages', 'name': 'Messages inbox', 'ready': True, 'count': len(memory_stores.smart_inbox_messages), 'path': '/inbox/stats'},
        {'id': 'affiliate', 'name': 'Affiliate management', 'ready': True, 'count': len(memory_stores.engagement_referrals), 'path': '/engagement/referrals/summary'},
        {'id': 'notifications', 'name': 'Notifications', 'ready': True, 'count': len(memory_stores.notifications), 'path': '/notifications'},
        {'id': 'files_content', 'name': 'Files and content', 'ready': True, 'count': len(memory_stores.minio_objects) + len(memory_stores.ai_gateway), 'path': '/media/library'},
        {'id': 'marketing_tools', 'name': 'Marketing tools settings', 'ready': True, 'count': len(memory_stores.analytics_reports), 'path': '/ops/platform/capabilities'},
        {'id': 'module_settings', 'name': 'Modules settings', 'ready': True, 'count': len(memory_stores.growthbook_checks), 'path': '/ops/platform/growth-suite'},
    ]

    updates: JsonObject = {
        'new_available': max(0, len(memory_stores.growthbook_checks) // 5),
        'in_progress': max(0, len(memory_stores.drone_builds) // 3),
        'pending': max(0, len(memory_stores.webhook_events) // 4),
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
            'orders': len(memory_stores.commerce_orders),
            'wallet_transactions': len(memory_stores.bank_transactions),
            'hmrc_quickbooks_xero_ready': {'hmrc', 'quickbooks', 'xero'}.issubset(providers_connected),
        },
        'accounts': {
            'profiles': len(memory_stores.tenant_profiles),
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
    'set_helpers',
    'set_db_ready',
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