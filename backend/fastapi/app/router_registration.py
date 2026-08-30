"""Move all router registrations out of legacy_main.py.

This module contains a single ``register_all_routers(app)`` function that
encapsulates every ``app.include_router(...)`` call that was previously
defined inline inside ``legacy_main.py`` (lines 2132-5319).
"""

from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Request

from . import memory_stores
from . import legacy_main as lg
from .auth_utils import jwt_sign_hs256, jwt_verify_hs256
from .routers.auth import AuthSecurityRecord
from .routers.api_governance import ApiGovernanceContext, create_api_governance_router
from .routers.benchmarks import BenchmarksContext
from .routers.growth_suite import GrowthSuiteContext
from .routers.ira import IRAContext
from .routers.ops import _OpsCallbacks
from .routers.outcome_attribution import OutcomeAttributionContext
from .routers.playbooks import PlaybooksContext
from .routers.trust_center import TrustCenterContext, create_trust_center_router
from .services.ai_providers import _provider_health_metrics

# ── Router factory functions ──────────────────────────────────────────────────
from .routers.ad_generation import router as ad_generation_router
from .routers.ads_control_tower import create_ads_control_tower_router
from .routers.ai import create_ai_router
from .routers.ai_crawler_enablement import create_ai_crawler_enablement_router
from .routers.ai_security import create_ai_security_router
from .routers.analytics_dashboard import create_analytics_router
from .routers.auth import create_auth_router
from .routers.autonomous_workforce import create_autonomous_workforce_router
from .routers.benchmarks import create_benchmarks_router
from .routers.billing import create_billing_router
from .routers.bridges import create_bridges_router
from .routers.chatbot import create_chatbot_router
from .routers.cms_integration import create_cms_router
from .routers.competitive import create_competitive_router
from .routers.content_approval import create_content_approval_router
from .routers.content_integrations import create_content_integrations_router
from .routers.crm import create_crm_router
from .routers.crm_abm import create_crm_abm_router
from .routers.documents import create_documents_router
from .routers.email_provider import create_email_router
from .routers.employee_advocacy import create_employee_advocacy_router
from .routers.engagement import create_engagement_router
from .routers.growth_suite import create_growth_suite_router
from .routers.influencer import create_influencer_router
from .routers.ira import create_ira_router
from .routers.knowledge_base import create_knowledge_base_router
from .routers.linkinbio import create_linkinbio_router
from .routers.live_editor import create_live_editor_router
from .routers.marketplace import create_marketplace_router
from .routers.media_jobs import create_media_jobs_router
from .routers.media_library import create_media_library_router
from .routers.meetings import create_meetings_router
from .routers.neo4j_graph_intelligence import create_neo4j_graph_intelligence_router
from .routers.notifications import create_notifications_router
from .routers.ops import create_ops_router
from .routers.outcome_attribution import create_outcome_attribution_router
from .routers.pentest import create_pentest_router
from .routers.pentest_sync import create_pentest_sync_router
from .routers.platform_integration import create_platform_integration_router
from .routers.platform_intelligence import create_platform_intelligence_router
from .routers.playbooks import create_playbooks_router
from .routers.products import create_products_router
from .routers.revenue_attribution import create_revenue_attribution_router
from .routers.search_everywhere_automation import create_search_everywhere_automation_router
from .routers.seo_platform import create_seo_platform_router
from .routers.sequences import create_sequences_router
from .routers.site_portfolio_manager import create_site_portfolio_router
from .routers.smart_inbox import create_smart_inbox_router
from .routers.social_manychat import create_social_manychat_router
from .routers.social_workspace import create_social_workspace_router
from .routers.stripe_billing import create_stripe_billing_router
from .routers.super_admin_finance import create_super_admin_finance_router
from .routers.surveys import create_surveys_router
from .routers.tenants import create_tenant_router
from .routers.tickets import create_tickets_router
from .routers.tool_integrations import create_tool_integrations_router
from .routers.translation_studio import create_translation_studio_router
from .routers.trend_intelligence import create_trend_intelligence_router
from .routers.utm_builder import create_utm_builder_router
from .routers.v1_loop import create_v1_loop_router
from .routers.viralpost import create_viralpost_router
from .routers.vse import create_vse_router
from .routers.workflows import create_workflows_router

# ── Pre-built router instances ────────────────────────────────────────────────
from .routers.agent_analytics import router as agent_analytics_router
from .routers.agents import router as agents_router
from .routers.answer_engine import router as answer_engine_router
from .routers.backlink_intelligence import router as backlink_intelligence_router
from .routers.brand_hub import router as brand_hub_router
from .routers.brandkit import router as brandkit_router
from .routers.cdn_analytics import router as cdn_analytics_router
from .routers.competitor_analysis import router as competitor_analysis_router
from .routers.predis_features import predis_router
from .routers.prompt_volumes import router as prompt_volumes_router
from .routers.rank_tracker import router as rank_tracker_router
from .routers.social_media_router import router as social_media_router
from .routers.social_posting import router as social_posting_router

# ── Intelligence router ──────────────────────────────────────────────────────
from .intelligence.routes import router as intel_router

# ── SEMrush feature-parity routers ───────────────────────────────────────────
from .routers.client_portal import router as client_portal_router  # noqa: E402
from .routers.contentshake_ai import router as contentshake_ai_router  # noqa: E402
from .routers.domain_overview import router as domain_overview_router  # noqa: E402
from .routers.eyeon_monitor import router as eyeon_monitor_router  # noqa: E402
from .routers.local_heatmap import router as local_heatmap_router  # noqa: E402
from .routers.map_rank_tracker import router as map_rank_tracker_router  # noqa: E402
from .routers.market_explorer import router as market_explorer_router  # noqa: E402
from .routers.one2target import router as one2target_router  # noqa: E402
from .routers.pla_research import router as pla_research_router  # noqa: E402


# ── Thin wrappers for helper functions defined in legacy_main ──────────────────

def _ops_require_super_admin_access(request: Request, x_super_admin_key: str | None) -> None:
    from .security_admin import require_super_admin_access

    require_super_admin_access(request, x_super_admin_key)


def _hashicorp_vault_health() -> dict[str, object]:
    return lg._hashicorp_vault_health()


def _supabase_vault_health() -> dict[str, object]:
    return lg._supabase_vault_health()


def _persist_governance_stores() -> None:
    db = getattr(lg, '_governance_db', None)
    if db is None:
        return
    db.save_all(
        list(lg._api_governance_providers_memory),
        list(lg._api_governance_usage_events_memory),
        list(lg._api_governance_incidents_memory),
    )


# ── Main registration function ────────────────────────────────────────────────

def register_all_routers(app: FastAPI) -> None:
    """Register all API routers on *app*.

    This function moves every ``app.include_router(...)`` call out of
    ``legacy_main.py`` so that the legacy module no longer drives router
    composition directly.  All module-level variables from *legacy_main*
    are accessed via the ``lg`` alias.
    """

    app.include_router(
        create_auth_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            totp_secret=lg._totp_secret,
            totp_verify=lg._totp_verify,
            jwt_sign_hs256=jwt_sign_hs256,
            jwt_verify_hs256=jwt_verify_hs256,
            auth_security_memory=cast(list[AuthSecurityRecord], lg._auth_security_memory),
            hash_password=lg.hash_password,
            verify_password=lg.verify_password,
            encrypt_value=lg.te_encrypt,
            hash_email=lg._hash_email,
            get_db_ready=lambda: lg._db_ready,
            db_dsn=lg._db_dsn,
            users_memory=lg._users_memory,
        )
    )

    app.include_router(
        create_tenant_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            get_db_ready=lambda: lg._db_ready,
            db_dsn=lg._db_dsn,
            encrypt_value=lg.te_encrypt,
            decrypt_value=lg._decrypt_value_or_empty,
            tenant_profiles_memory=lg._tenant_profiles_memory,
        )
    )

    app.include_router(
        create_notifications_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            notifications_memory=lg._notifications_memory,
            audit_log_memory=lg._audit_log_memory,
            notification_preferences_memory=lg._notification_preferences_memory,
            notification_delivery_receipts_memory=lg._notification_delivery_receipts_memory,
            # ENHANCED: enable DB-backed notification durability while retaining memory fallback behavior.
            db_ready_fn=lambda: lg._db_ready,
            db_dsn_fn=lg._db_dsn,
        )
    )

    # NEW: Sandboxed Media Processing Pipeline (Sandboxed_Media_SaaS_Architecture)
    app.include_router(
        create_media_jobs_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            media_jobs_memory=lg._media_jobs_memory,
            media_jobs_dlq_memory=lg._media_jobs_dlq_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_ops_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            hash_password=lg._hash_password_ops,
            verify_password=lg.verify_password,
            get_platform_status=lambda auth: lg._platform_status_payload(auth),
            get_metrics_summary=lambda auth: lg._platform_metrics_summary_payload(auth),
            callbacks=_OpsCallbacks(
                get_anti_failure_status=lambda auth: lg._platform_anti_failure_payload(auth),
                get_use_case_coverage=lambda auth: lg._platform_use_case_coverage_payload(auth),
                get_api_usage_summary=lambda auth, limit: lg._platform_api_usage_payload(auth, limit),
                get_capabilities=lambda auth: lg._platform_capabilities_payload(auth),
                get_super_admin_dashboard=lambda auth: lg._platform_super_admin_dashboard_payload(auth),
                get_siem_data_collection=lambda auth, limit: lg._platform_siem_data_collection_payload(auth, limit),
                get_siem_detection=lambda auth, limit: lg._platform_siem_detection_payload(auth, limit),
                get_siem_investigation=lambda auth, query, limit: lg._platform_siem_investigation_payload(auth, query, limit),
                get_siem_compliance=lambda auth: lg._platform_siem_compliance_payload(auth),
                set_siem_retention_policy=lambda auth, hot_days, warm_days, cold_days, immutable_audit: lg._platform_siem_set_retention_policy_payload(
                    auth, hot_days, warm_days, cold_days, immutable_audit
                ),
                get_siem_architecture=lambda auth: lg._platform_siem_architecture_payload(auth),
                list_siem_cases=lambda auth, status, limit, offset: lg._platform_siem_list_cases_payload(auth, status, limit, offset),
                create_siem_case=lambda auth, title, severity, description, evidence_ids: lg._platform_siem_create_case_payload(
                    auth, title, severity, description, evidence_ids
                ),
                update_siem_case=lambda auth, case_id, status, assignee, note: lg._platform_siem_update_case_payload(
                    auth, case_id, status, assignee, note
                ),
                run_siem_soar_playbook=lambda auth, playbook, case_id, parameters: lg._platform_siem_run_soar_payload(
                    auth, playbook, case_id, parameters
                ),
                get_siem_flow_map=lambda auth, minutes, limit: lg._platform_siem_flow_map_payload(auth, minutes, limit),
                get_siem_security_controls=lambda auth: lg._platform_siem_security_controls_payload(auth),
                update_siem_security_control=lambda auth, control_type, control_id, enabled, mode, action, threshold, notes: lg._platform_siem_update_security_control_payload(
                    auth, control_type, control_id, enabled, mode, action, threshold, notes
                ),
                get_siem_vulnerabilities=lambda auth, severity, status, limit: lg._platform_siem_vulnerabilities_payload(
                    auth, severity, status, limit
                ),
                run_siem_zap_scan=lambda auth, target_url, scan_profile, authenticated: lg._platform_siem_run_zap_scan_payload(
                    auth, target_url, scan_profile, authenticated
                ),
                get_siem_updates=lambda auth: lg._platform_siem_updates_payload(auth),
                apply_siem_update=lambda auth, update_id, strategy: lg._platform_siem_apply_update_payload(
                    auth, update_id, strategy
                ),
                run_siem_auto_pentest=lambda auth, profile, target_scope, include_dependency_scan, include_api_fuzzing: lg._platform_siem_auto_pentest_run_payload(
                    auth, profile, target_scope, include_dependency_scan, include_api_fuzzing
                ),
                list_siem_auto_pentest_jobs=lambda auth, limit: lg._platform_siem_auto_pentest_jobs_payload(auth, limit),
                get_siem_vault_encryption_health=lambda auth: lg._platform_siem_vault_encryption_health_payload(auth),
                apply_siem_endpoint_hardening=lambda auth, strict_mode, enforce_edr_policy, enforce_device_posture, apply_to_assets: lg._platform_siem_apply_endpoint_hardening_payload(
                    auth, strict_mode, enforce_edr_policy, enforce_device_posture, apply_to_assets
                ),
                get_siem_endpoint_hardening_status=lambda auth: lg._platform_siem_endpoint_hardening_status_payload(auth),
                get_siem_network_anomalies=lambda auth, minutes: lg._platform_siem_network_anomalies_payload(auth, minutes),
                run_siem_dead_code_scan=lambda auth, scope, include_frontend, include_backend, severity_floor: lg._platform_siem_dead_code_scan_payload(
                    auth, scope, include_frontend, include_backend, severity_floor
                ),
                list_siem_dead_code_findings=lambda auth, severity, limit: lg._platform_siem_dead_code_findings_payload(auth, severity, limit),
                get_siem_advanced_threat_hunt=lambda auth, minutes: lg._platform_siem_advanced_threat_hunt_payload(auth, minutes),
                get_hybrid_stacks=lambda auth: lg._platform_hybrid_stacks_payload(auth),
                get_module_registry=lambda auth: lg._platform_module_registry_payload(auth),
                require_super_admin_access=_ops_require_super_admin_access,
            ),
        )
    )

    app.include_router(
        create_content_integrations_router(
            handlers={
                'generate_content': lg.generate_content,
                'generate_ads': lg.generate_ads,
                'analyze_seo': lg.analyze_seo,
                'schedule_social_post': lg.schedule_social_post,
                'list_scheduled_posts': lg.list_scheduled_posts,
                'move_scheduled_post': lg.move_scheduled_post,
                'delete_scheduled_post': lg.delete_scheduled_post,
                'ingest_social_listening_mention': lg.ingest_social_listening_mention,
                'list_social_listening_mentions': lg.list_social_listening_mentions,
                'get_social_listening_summary': lg.get_social_listening_summary,
                'create_social_listening_alert_rule': lg.create_social_listening_alert_rule,
                'list_social_listening_alerts': lg.list_social_listening_alerts,
                'get_social_listening_clusters': lg.get_social_listening_clusters,
                'ingest_review': lg.ingest_review,
                'list_reviews': lg.list_reviews,
                'respond_to_review': lg.respond_to_review,
                'get_reviews_summary': lg.get_reviews_summary,
                'create_email_contact': lg.create_email_contact,
                'list_email_contacts': lg.list_email_contacts,
                'create_email_campaign': lg.create_email_campaign,
                'list_email_campaigns': lg.list_email_campaigns,
                'send_test_email_campaign': lg.send_test_email_campaign,
                'upsert_suitecrm_lead': lg.upsert_suitecrm_lead,
                'register_refferq_referral': lg.register_refferq_referral,
                'capture_posthog_event': lg.capture_posthog_event,
                'track_matomo_event': lg.track_matomo_event,
                'track_plausible_event': lg.track_plausible_event,
                'trigger_n8n_webhook': lg.trigger_n8n_webhook,
                'evaluate_growthbook_flag': lg.evaluate_growthbook_flag,
                'receive_webhook': lg.receive_webhook,
                'list_webhook_events': lg.list_webhook_events,
                'appwrite_create_user': lg.appwrite_create_user,
                'appwrite_create_session': lg.appwrite_create_session,
                'drone_trigger_build': lg.drone_trigger_build,
                'directus_create_item': lg.directus_create_item,
                'directus_list_items': lg.directus_list_items,
                'storage_presign': lg.storage_presign,
                'storage_list_objects': lg.storage_list_objects,
                'stripe_create_checkout': lg.stripe_create_checkout,
                'stripe_process_webhook': lg.stripe_process_webhook,
                'stripe_list_events': lg.list_stripe_events,
                'get_audit_log': lg.get_audit_log,
            },
        )
    )

    app.include_router(
        create_seo_platform_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            seo_analyses_memory=lg._seo_analyses_memory,
            db_ready_fn=lambda: lg._db_ready,
            db_dsn_fn=lg._db_dsn,
        )
    )

    app.include_router(
        create_bridges_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            meilisearch_index_memory=lg._meilisearch_index_memory,
            redis_ops_memory=lg._redis_ops_memory,
            twilio_messages_memory=lg._twilio_messages_memory,
            slack_messages_memory=lg._slack_messages_memory,
            resend_messages_memory=lg._resend_messages_memory,
            algolia_sync_memory=lg._algolia_sync_memory,
        )
    )

    # ── New module routers (Part 3 & Part 4) ─────────────────────────────────────

    app.include_router(
        create_engagement_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            streaks_memory=lg._engagement_streaks_memory,
            credit_ledger_memory=lg._credit_ledger_memory,
            notifications_memory=lg._notifications_memory,
            scheduled_posts_memory=lg._scheduled_posts_memory,
            email_campaigns_memory=lg._email_campaigns_memory,
            influencer_campaigns_memory=lg._influencer_campaigns_memory,
            chatbots_memory=lg._chatbots_memory,
            tenant_profiles_memory=lg._tenant_profiles_memory,
            crm_contacts_memory=lg._crm_contacts_memory,
            crm_deals_memory=lg._crm_deals_memory,
            linkinbio_pages_memory=lg._linkinbio_pages_memory,
            linkinbio_links_memory=lg._linkinbio_links_memory,
            cms_pages_memory=lg._cms_pages_memory,
            marketplace_installs_memory=lg._marketplace_installs_memory,
            invoices_memory=lg._invoices_memory,
            companion_profiles_memory=lg._engagement_companion_profiles_memory,
            companion_messages_memory=lg._engagement_companion_messages_memory,
            fomo_rules_memory=lg._engagement_fomo_rules_memory,
            fomo_events_memory=lg._engagement_fomo_events_memory,
            social_proof_events_memory=lg._engagement_social_proof_events_memory,
            dependency_profiles_memory=lg._engagement_dependency_profiles_memory,
            dependency_events_memory=lg._engagement_dependency_events_memory,
            community_circles_memory=lg._engagement_community_circles_memory,
            community_posts_memory=lg._engagement_community_posts_memory,
            community_amas_memory=lg._engagement_community_amas_memory,
            brand_lock_profiles_memory=lg._engagement_brand_lock_profiles_memory,
            brand_lock_events_memory=lg._engagement_brand_lock_events_memory,
            autopilot_profiles_memory=lg._engagement_autopilot_profiles_memory,
            autopilot_events_memory=lg._engagement_autopilot_events_memory,
            achievement_profiles_memory=lg._engagement_achievement_profiles_memory,
            achievement_events_memory=lg._engagement_achievement_events_memory,
            money_printer_ideas_memory=lg._money_printer_ideas_memory,
            money_printer_validations_memory=lg._money_printer_validations_memory,
            bank_accounts_memory=lg._bank_accounts_memory,
            bank_transactions_memory=lg._bank_transactions_memory,
            bank_payouts_memory=lg._bank_payouts_memory,
            university_courses_memory=lg._university_courses_memory,
            university_cohorts_memory=lg._university_cohorts_memory,
            university_enrollments_memory=lg._university_enrollments_memory,
            studios_services_memory=lg._studios_services_memory,
            studios_briefs_memory=lg._studios_briefs_memory,
            studios_proposals_memory=lg._studios_proposals_memory,
            studios_escrows_memory=lg._studios_escrows_memory,
            commerce_products_memory=lg._commerce_products_memory,
            commerce_orders_memory=lg._commerce_orders_memory,
            talent_creators_memory=lg._talent_creators_memory,
            talent_deals_memory=lg._talent_deals_memory,
            talent_rate_cards_memory=lg._talent_rate_cards_memory,
            white_label_profiles_memory=lg._white_label_profiles_memory,
            white_label_events_memory=lg._white_label_events_memory,
            referrals_memory=lg._engagement_referrals_memory,
            referral_claims_memory=lg._engagement_referral_claims_memory,
            refferq_jobs_memory=lg._refferq_jobs_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_crm_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            contacts_memory=lg._crm_contacts_memory,
            companies_memory=lg._crm_companies_memory,
            deals_memory=lg._crm_deals_memory,
            activities_memory=lg._crm_activities_memory,
            webhook_subscriptions_memory=lg._crm_webhook_subscriptions_memory,
            audit_log_memory=lg._audit_log_memory,
            leads_memory=lg._crm_leads_memory,
            tasks_memory=lg._crm_tasks_memory,
            tickets_memory=memory_stores.tickets,
            campaigns_memory=lg._crm_campaigns_memory,
            segments_memory=lg._crm_segments_memory,
            notes_memory=lg._crm_notes_memory,
            quotes_memory=lg._crm_quotes_memory,
            crm_invoices_memory=lg._crm_invoices_memory,
            email_sequences_memory=lg._crm_email_sequences_memory,
            workflow_rules_memory=lg._crm_workflow_rules_memory,
            sla_rules_memory=lg._crm_sla_rules_memory,
            projects_memory=lg._crm_projects_memory,
            custom_entity_types_memory=lg._crm_custom_entity_types_memory,
            custom_entity_records_memory=lg._crm_custom_entity_records_memory,
            automation_recipes_memory=lg._crm_automation_recipes_memory,
            api_tokens_memory=lg._crm_api_tokens_memory,
            backup_snapshots_memory=lg._crm_backup_snapshots_memory,
            live_sync_state_memory=lg._crm_live_sync_state_memory,
        )
    )
    app.include_router(create_crm_abm_router(enforce_rate_limit=lg._enforce_rate_limit))
    app.include_router(
        create_influencer_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            influencers_memory=lg._influencers_memory,
            influencer_campaigns_memory=lg._influencer_campaigns_memory,
            influencer_outreach_memory=lg._influencer_outreach_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_chatbot_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            chatbots_memory=lg._chatbots_memory,
            chatbot_conversations_memory=lg._chatbot_conversations_memory,
            chatbot_leads_memory=lg._chatbot_leads_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_ira_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            ctx=IRAContext(
                audit_log_memory=lg._audit_log_memory,
                tickets_memory=memory_stores.tickets,
                chatbot_conversations_memory=lg._chatbot_conversations_memory,
                credit_ledger_memory=lg._credit_ledger_memory,
                invoices_memory=lg._invoices_memory,
                stripe_events_memory=lg._stripe_events_memory,
                revenue_conversions_memory=lg._revenue_conversions_memory,
                api_usage_audit_memory=lg._api_usage_audit_memory,
                ai_security_usage_memory=lg._ai_security_usage_memory,
                slack_messages_memory=lg._slack_messages_memory,
                resend_messages_memory=lg._resend_messages_memory,
                twilio_messages_memory=lg._twilio_messages_memory,
                ira_events_memory=lg._ira_events_memory,
                ira_sessions_memory=lg._ira_sessions_memory,
                ira_controls_memory=lg._ira_controls_memory,
                ira_connectors_memory=lg._ira_connectors_memory,
                ira_ml_knowledge_memory=lg._ira_ml_knowledge_memory,
                ira_ml_jobs_memory=lg._ira_ml_jobs_memory,
                ira_ml_models_memory=lg._ira_ml_models_memory,
                ira_structured_memory=lg._ira_structured_memory,
                ira_action_snapshots_memory=lg._ira_action_snapshots_memory,
                ira_cost_ledger_memory=lg._ira_cost_ledger_memory,
                ira_ab_tests_memory=lg._ira_ab_tests_memory,
                ira_performance_log_memory=lg._ira_performance_log_memory,
            ),
        )
    )

    app.include_router(
        create_linkinbio_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            linkinbio_pages_memory=lg._linkinbio_pages_memory,
            linkinbio_links_memory=lg._linkinbio_links_memory,
            linkinbio_analytics_memory=lg._linkinbio_analytics_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_billing_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            subscriptions_memory=lg._subscriptions_memory,
            invoices_memory=lg._invoices_memory,
            credit_ledger_memory=lg._credit_ledger_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_stripe_billing_router(
            subscriptions_memory=lg._subscriptions_memory,
            invoices_memory=lg._invoices_memory,
            credit_ledger_memory=lg._credit_ledger_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(create_email_router())

    app.include_router(
        create_super_admin_finance_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            require_super_admin_access=_ops_require_super_admin_access,
            accounting_integrations_memory=lg._accounting_integrations_memory,
            accounting_exports_memory=lg._accounting_exports_memory,
            module_settings_memory=lg._super_admin_module_settings_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_cms_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            cms_connections_memory=lg._cms_connections_memory,
            cms_pages_memory=lg._cms_pages_memory,
            cms_sync_log_memory=lg._cms_sync_log_memory,
            email_sequences_memory=lg._crm_email_sequences_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_marketplace_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            marketplace_catalogue_memory=lg._marketplace_catalogue_memory,
            marketplace_installs_memory=lg._marketplace_installs_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ADDED: Content Approval Workflows (Hootsuite §4.5)
    app.include_router(
        create_content_approval_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            approval_requests_memory=lg._content_approval_requests_memory,
            approval_comments_memory=lg._content_approval_comments_memory,
            approval_configs_memory=lg._content_approval_configs_memory,
        )
    )

    # ADDED: Media Library (Hootsuite §4.3)
    app.include_router(
        create_media_library_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            assets_memory=lg._media_library_assets_memory,
            folders_memory=lg._media_library_folders_memory,
            tags_memory=lg._media_library_tags_memory,
        )
    )

    # ADDED: Employee Advocacy / Hootsuite Amplify (Hootsuite §9)
    app.include_router(
        create_employee_advocacy_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            advocacy_content_memory=lg._advocacy_content_memory,
            advocacy_shares_memory=lg._advocacy_shares_memory,
            advocacy_participants_memory=lg._advocacy_participants_memory,
            advocacy_campaigns_memory=lg._advocacy_campaigns_memory,
        )
    )

    app.include_router(
        create_analytics_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            custom_reports_memory=lg._analytics_reports_memory,
            report_schedules_memory=lg._analytics_report_schedules_memory,
            trends_memory=lg._analytics_trends_memory,
            rollups_memory=lg._analytics_rollups_memory,
            get_queue_counts=lambda: {
                'social_scheduled': len(lg._scheduled_posts_memory),
                'notifications': len(lg._notifications_memory),
                'reviews': len(lg._reviews_memory),
                'social_listening': len(lg._social_listening_memory),
                'email_campaigns': len(lg._email_campaigns_memory),
                'crm_contacts': len(lg._crm_contacts_memory),
                'crm_deals': len(lg._crm_deals_memory),
                'influencer_campaigns': len(lg._influencer_campaigns_memory),
                'chatbots': len(lg._chatbots_memory),
                'cms_connections': len(lg._cms_connections_memory),
                'content_generated': len(lg._ai_gateway_memory),
                'seo_analyses': 0,
                'ad_jobs': 0,
                'bank_payouts': len(lg._bank_payouts_memory),
                'studios_escrows': len(lg._studios_escrows_memory),
                'university_courses': len(lg._university_courses_memory),
                'university_enrollments': len(lg._university_enrollments_memory),
                'studios_services': len(lg._studios_services_memory),
                'commerce_products': len(lg._commerce_products_memory),
                'commerce_orders': len(lg._commerce_orders_memory),
            },
        )
    )

    # ADDED: Smart Inbox — Unified Social Engagement Hub (SproutSocial §3)
    app.include_router(
        create_smart_inbox_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            messages_memory=lg._smart_inbox_messages_memory,
            notes_memory=lg._smart_inbox_notes_memory,
            locks_memory=lg._smart_inbox_locks_memory,
            saved_replies_memory=lg._saved_replies_memory,
            delivery_failures_memory=lg._smart_inbox_delivery_failures_memory,
            delivery_replay_runs_memory=lg._smart_inbox_delivery_replay_runs_memory,
        )
    )

    # ADDED: ViralPost — Optimal Send Time Engine (SproutSocial §2.1.3)
    app.include_router(
        create_viralpost_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            analyses_memory=lg._viralpost_analyses_memory,
            post_history_memory=lg._viralpost_post_history_memory,
        )
    )

    # ADDED: Trend Intelligence — cross-source forecasting, AI content planning, and performance optimization
    app.include_router(
        create_trend_intelligence_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            signals_memory=lg._trend_signals_memory,
            forecasts_memory=lg._trend_forecasts_memory,
            selections_memory=lg._trend_selections_memory,
            content_memory=lg._trend_content_generations_memory,
            performance_memory=lg._trend_performance_tracks_memory,
            recommendations_memory=lg._trend_recommendations_memory,
        )
    )

    # ADDED: Competitive Benchmarking (SproutSocial §5.4)
    app.include_router(
        create_competitive_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            profiles_memory=lg._competitor_profiles_memory,
            snapshots_memory=lg._competitor_snapshots_memory,
        )
    )

    # ADDED: Social Workspace — connected channels, brand details, unified engagement, and autopost
    app.include_router(
        create_social_workspace_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            social_accounts_memory=lg._social_accounts_memory,
            brand_profiles_memory=lg._social_brand_profiles_memory,
            inbox_messages_memory=lg._smart_inbox_messages_memory,
            competitor_profiles_memory=lg._competitor_profiles_memory,
            competitor_snapshots_memory=lg._competitor_snapshots_memory,
            notifications_memory=lg._notifications_memory,
            scheduled_posts_memory=lg._scheduled_posts_memory,
            viralpost_post_history_memory=lg._viralpost_post_history_memory,
            db_ready_fn=lambda: lg._db_ready,
            db_dsn_fn=lg._db_dsn,
        )
    )

    # ADDED: Manychat-style audience + automation entities
    app.include_router(create_social_manychat_router())

    # ADDED: UTM Builder with saved presets (SproutSocial §2.1.1)
    app.include_router(
        create_utm_builder_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            presets_memory=lg._utm_presets_memory,
        )
    )

    app.include_router(
        create_revenue_attribution_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            touchpoints_memory=lg._revenue_touchpoints_memory,
            conversions_memory=lg._revenue_conversions_memory,
            spend_memory=lg._revenue_spend_memory,
            db_ready_fn=lambda: lg._db_ready,
            db_dsn_fn=lg._db_dsn,
        )
    )

    app.include_router(
        create_growth_suite_router(
            ctx=GrowthSuiteContext(
                enforce_rate_limit=lg._enforce_rate_limit,
                growth_suite_memory=lg._growth_suite_memory,
                scheduled_posts_memory=lg._scheduled_posts_memory,
                email_campaigns_memory=lg._email_campaigns_memory,
                chatbots_memory=lg._chatbots_memory,
                chatbot_leads_memory=lg._chatbot_leads_memory,
                linkinbio_pages_memory=lg._linkinbio_pages_memory,
                linkinbio_links_memory=lg._linkinbio_links_memory,
                analytics_reports_memory=lg._analytics_reports_memory,
                crm_contacts_memory=lg._crm_contacts_memory,
                crm_deals_memory=lg._crm_deals_memory,
                revenue_touchpoints_memory=lg._revenue_touchpoints_memory,
                revenue_conversions_memory=lg._revenue_conversions_memory,
                db_ready_fn=lambda: lg._db_ready,
                db_dsn_fn=lg._db_dsn,
            ),
        )
    )

    # ── Viral Singularity Engine (VSE) ────────────────────────────────────────────────────
    app.include_router(
        create_vse_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            vse_viral_events_memory=lg._vse_viral_events_memory,
            vse_briefs_memory=lg._vse_briefs_memory,
            vse_trigger_analyses_memory=lg._vse_trigger_analyses_memory,
            vse_algorithm_models_memory=lg._vse_algorithm_models_memory,
            vse_algorithm_updates_memory=lg._vse_algorithm_updates_memory,
            vse_network_maps_memory=lg._vse_network_maps_memory,
            vse_cascade_simulations_memory=lg._vse_cascade_simulations_memory,
            vse_detonations_memory=lg._vse_detonations_memory,
            vse_swarms_memory=lg._vse_swarms_memory,
            vse_momentum_events_memory=lg._vse_momentum_events_memory,
            vse_content_factory_memory=lg._vse_content_factory_memory,
            vse_emotion_analyses_memory=lg._vse_emotion_analyses_memory,
            vse_trend_alerts_memory=lg._vse_trend_alerts_memory,
            vse_trend_hijacks_memory=lg._vse_trend_hijacks_memory,
            vse_paid_events_memory=lg._vse_paid_events_memory,
            vse_dark_social_seeds_memory=lg._vse_dark_social_seeds_memory,
            vse_immortal_assets_memory=lg._vse_immortal_assets_memory,
            vse_viral_vault_memory=lg._vse_viral_vault_memory,
            db_ready_fn=lambda: lg._db_ready,
            db_dsn_fn=lg._db_dsn,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Sales Sequences (HubSpot Sales Hub §5.3) ─────────────────────────────────
    app.include_router(
        create_sequences_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            sequences_memory=memory_stores.sequences,
            enrollments_memory=memory_stores.sequence_enrollments,
            step_events_memory=memory_stores.sequence_step_events,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Meeting Scheduling (HubSpot Sales Hub §5.4) ──────────────────────────────
    app.include_router(
        create_meetings_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            meeting_links_memory=memory_stores.meeting_links,
            bookings_memory=memory_stores.meeting_bookings,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Help Desk / Ticketing (HubSpot Service Hub §6.1) ─────────────────────────
    app.include_router(
        create_tickets_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            tickets_memory=memory_stores.tickets,
            ticket_comments_memory=memory_stores.ticket_comments,
            sla_configs_memory=memory_stores.sla_configs,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Knowledge Base (HubSpot Service Hub §6.2) ────────────────────────────────
    app.include_router(
        create_knowledge_base_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            kb_categories_memory=memory_stores.kb_categories,
            kb_articles_memory=memory_stores.kb_articles,
            kb_feedback_memory=memory_stores.kb_article_feedback,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── NPS / CSAT Surveys (HubSpot Service Hub §6.4) ────────────────────────────
    app.include_router(
        create_surveys_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            surveys_memory=memory_stores.surveys,
            survey_responses_memory=memory_stores.survey_responses,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Sales Documents & Quotes (HubSpot Sales Hub §5.6) ────────────────────────
    app.include_router(
        create_documents_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            documents_memory=memory_stores.sales_documents,
            document_views_memory=memory_stores.document_shares,
            quotes_memory=memory_stores.sales_quotes,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Marketing Automation Workflows (HubSpot §3.2) ────────────────────────────
    app.include_router(
        create_workflows_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            workflows_memory=memory_stores.workflows,
            workflow_executions_memory=memory_stores.workflow_executions,
            workflow_step_logs_memory=memory_stores.workflow_step_logs,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Product Catalog (HubSpot Commerce Hub §8.2) ───────────────────────────────
    app.include_router(
        create_products_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            products_memory=memory_stores.product_catalog,
            product_categories_memory=memory_stores.product_catalog_categories,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Enterprise Pentest Platform — Phase 1 ────────────────────────────────────
    app.include_router(
        create_pentest_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            findings_memory=memory_stores.pentest_findings,
            risk_policies_memory=memory_stores.pentest_risk_policies,
            sync_queue_memory=memory_stores.pentest_sync_queue,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Enterprise Pentest Platform — Phase 2 ────────────────────────────────────
    app.include_router(
        create_pentest_sync_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            findings_memory=memory_stores.pentest_findings,
            risk_policies_memory=memory_stores.pentest_risk_policies,
            defectdojo_configs_memory=memory_stores.pentest_defectdojo_configs,
            sync_queue_memory=memory_stores.pentest_sync_queue,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Flywheel Module 1: Outcome Attribution & Decision Quality ─────────────────
    app.include_router(
        create_outcome_attribution_router(
            ctx=OutcomeAttributionContext(
                enforce_rate_limit=lg._enforce_rate_limit,
                actions_memory=memory_stores.outcome_actions,
                outcomes_memory=memory_stores.outcome_outcomes,
                quality_scores_memory=memory_stores.outcome_quality_scores,
                audit_log_memory=lg._audit_log_memory,
                get_db_ready=lambda: lg._db_ready,
                db_dsn=lg._db_dsn,
            )
        )
    )

    # ── Flywheel Module 2: Trust Center ──────────────────────────────────────────
    app.include_router(
        create_trust_center_router(
            ctx=TrustCenterContext(
                enforce_rate_limit=lg._enforce_rate_limit,
                policy_history_memory=memory_stores.trust_policy_history,
                approval_chains_memory=memory_stores.trust_approval_chains,
                incidents_memory=memory_stores.trust_incidents,
                governance_snapshots_memory=memory_stores.trust_governance_snapshots,
                audit_log_memory=lg._audit_log_memory,
                get_db_ready=lambda: lg._db_ready,
                db_dsn=lg._db_dsn,
            )
        )
    )

    # ── Flywheel Module 3: Integration Playbooks ─────────────────────────────────
    app.include_router(
        create_playbooks_router(
            ctx=PlaybooksContext(
                enforce_rate_limit=lg._enforce_rate_limit,
                playbooks_memory=memory_stores.playbooks,
                playbook_runs_memory=memory_stores.playbook_runs,
                audit_log_memory=lg._audit_log_memory,
                get_db_ready=lambda: lg._db_ready,
                db_dsn=lg._db_dsn,
            )
        )
    )

    # ── Flywheel Module 4: Performance Benchmarks ────────────────────────────────
    app.include_router(
        create_benchmarks_router(
            ctx=BenchmarksContext(
                enforce_rate_limit=lg._enforce_rate_limit,
                benchmarks_memory=memory_stores.benchmarks,
                segment_benchmarks_memory=memory_stores.segment_benchmarks,
                audit_log_memory=lg._audit_log_memory,
                get_db_ready=lambda: lg._db_ready,
                db_dsn=lg._db_dsn,
            )
        )
    )

    # ── AI Models Integration ────────────────────────────────────────────────────
    # Connects to Ollama (text), ComfyUI (images/video), WhisperX (speech), voice workers
    app.include_router(
        create_ai_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
            credit_ledger_memory=lg._credit_ledger_memory,
        )
    )

    # ── AI Security ─────────────────────────────────────────────────────────────
    app.include_router(
        create_ai_security_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            is_tenant_blocked=lg._is_tenant_blocked,
            prepare_ai_gateway_attempt=lg._prepare_ai_gateway_attempt,
            invoke_ai_provider_generation=lg._invoke_ai_provider_generation,
            update_provider_health=lg._update_provider_health,
            record_ai_gateway_success=lg._record_ai_gateway_success,
            coerce_int=lg._coerce_int,
            coerce_float=lg._coerce_float,
            load_ai_generated_asset_bytes=lg._load_ai_generated_asset_bytes,
            record_ai_security_alert=lg._record_ai_security_alert,
            send_security_email_alert=lg._send_security_email_alert,
            block_tenant=lg._block_tenant,
            disable_provider=lg._disable_provider,
            security_alert_db_queue_enabled=lg._security_alert_db_queue_enabled,
            db_security_alert_email_queue_items=lg._db_security_alert_email_queue_items,
            memory_security_alert_email_queue_items=lg._memory_security_alert_email_queue_items,
            paginate_email_queue_items=lg._paginate_email_queue_items,
            db_requeue_security_alert_email=lg._db_requeue_security_alert_email,
            memory_requeue_security_alert_email=lg._memory_requeue_security_alert_email,
            db_security_alert_email_exists=lg._db_security_alert_email_exists,
            security_alert_delivery_summary=lg._security_alert_delivery_summary,
            is_provider_disabled=lg._is_provider_disabled,
            ai_security_usage_memory=lg._ai_security_usage_memory,
            ai_security_alerts_memory=lg._ai_security_alerts_memory,
            ai_security_blocks_memory=lg._ai_security_blocks_memory,
            ai_security_appeals_memory=lg._ai_security_appeals_memory,
            ai_security_ids_events_memory=lg._ai_security_ids_events_memory,
            ai_provider_keys_memory=lg._ai_provider_keys_memory,
            resend_messages_memory=lg._resend_messages_memory,
            ai_generated_assets_memory=lg._ai_generated_assets_memory,
            ai_generated_assets_lock=lg._ai_generated_assets_lock,
            ai_security_lock=lg._ai_security_lock,
            ai_providers=lg.AI_PROVIDERS,
            ai_model_catalog=lg.AI_MODEL_CATALOG,
            provider_health_metrics=_provider_health_metrics,
            is_production=lg._is_production,
        )
    )

    # ── Ads Control Tower ────────────────────────────────────────────────────────
    app.include_router(
        create_ads_control_tower_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            notifications_memory=lg._notifications_memory,
            audit_log_memory=lg._audit_log_memory,
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
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── Platform Integration (social media publishing / scheduling / analytics) ───
    app.include_router(
        create_platform_integration_router(
            enforce_rate_limit=lg._enforce_rate_limit,
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

    app.include_router(
        create_api_governance_router(
            ApiGovernanceContext(
                enforce_rate_limit=lg._enforce_rate_limit,
                te_encrypt=lg.te_encrypt,
                provider_store=lg._api_governance_providers_memory,
                usage_store=lg._api_governance_usage_events_memory,
                incident_store=lg._api_governance_incidents_memory,
                notification_store=lg._notifications_memory,
                ira_events_store=lg._ira_events_memory,
                siem_cases_store=lg._siem_cases_memory,
                vault_hashicorp_health=_hashicorp_vault_health,
                vault_supabase_health=_supabase_vault_health,
                persist=_persist_governance_stores,
            )
        )
    )

    app.include_router(
        create_ai_crawler_enablement_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            sites_memory=lg._ace_sites_memory,
            crawler_events_memory=lg._ace_crawler_events_memory,
            ssr_cache_memory=lg._ace_ssr_cache_memory,
            crawler_rules_memory=lg._ace_crawler_rules_memory,
            audit_results_memory=lg._ace_audit_results_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_search_everywhere_automation_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            ace_sites_memory=lg._ace_sites_memory,
            cms_connections_memory=lg._cms_connections_memory,
        )
    )

    app.include_router(
        create_neo4j_graph_intelligence_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_site_portfolio_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            portfolio_sites_memory=lg._portfolio_sites_memory,
            portfolio_rules_memory=lg._portfolio_rules_memory,
            portfolio_deployments_memory=lg._portfolio_deployments_memory,
            white_label_memory=lg._white_label_profiles_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_live_editor_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            sessions_memory=lg._live_editor_sessions_memory,
            changes_memory=lg._live_editor_changes_memory,
            history_memory=lg._live_editor_history_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    app.include_router(
        create_autonomous_workforce_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            profiles_memory=lg._autonomous_workforce_profiles_memory,
            integrations_memory=lg._autonomous_workforce_integrations_memory,
            missions_memory=lg._autonomous_workforce_missions_memory,
            feed_memory=lg._autonomous_workforce_feed_memory,
            schedules_memory=lg._autonomous_workforce_schedules_memory,
            knowledge_memory=lg._autonomous_workforce_knowledge_memory,
            outcomes_memory=lg._autonomous_workforce_outcomes_memory,
            audit_log_memory=lg._audit_log_memory,
        )
    )

    # ── SEMrush Feature Parity: New Routers ───────────────────────────────────────
    app.include_router(domain_overview_router)
    app.include_router(market_explorer_router)
    app.include_router(one2target_router)
    app.include_router(eyeon_monitor_router)
    app.include_router(pla_research_router)
    app.include_router(map_rank_tracker_router)
    app.include_router(local_heatmap_router)
    app.include_router(contentshake_ai_router)
    app.include_router(client_portal_router)
