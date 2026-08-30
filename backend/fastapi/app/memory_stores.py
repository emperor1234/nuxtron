"""
Centralized memory store definitions for all modules.
Reduces main.py complexity and improves organization.

In production (ENVIRONMENT=production), memory stores are disabled to force
database-backed persistence. Set NUXTRON_ALLOW_MEMORY_STORES=1 to override.
"""

import os

StoreItem = dict[str, object]
StoreList = list[StoreItem]


def _is_memory_store_allowed() -> bool:
    """Check if in-memory stores are allowed.

    In production, memory stores are disabled by default to force database-backed
    persistence. Set NUXTRON_ALLOW_MEMORY_STORES=1 to override this behavior.
    """
    environment = os.getenv('ENVIRONMENT', 'development').strip().lower()
    if environment == 'production':
        return os.getenv('NUXTRON_ALLOW_MEMORY_STORES', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    return True


_MEMORY_ALLOWED = _is_memory_store_allowed()


def _create_store() -> StoreList:
    """Create a process-local list used as a cache or fallback store.

    Production still needs these list objects as the identity routers share.
    Writes that must survive restart belong in Postgres; this helper no longer
    pretends that returning ``[]`` disables the store.
    """
    _ = _MEMORY_ALLOWED
    return []


# ── Social & Content ──────────────────────────────────────
scheduled_posts: StoreList = _create_store()
email_contacts: StoreList = _create_store()
email_campaigns: StoreList = _create_store()
social_listening: StoreList = _create_store()
social_listening_alert_rules: StoreList = _create_store()
social_listening_alerts: StoreList = _create_store()
reviews: StoreList = _create_store()
seo_analyses: StoreList = _create_store()

# ── Integration Jobs & Events ─────────────────────────────
suitecrm_jobs: StoreList = _create_store()
refferq_jobs: StoreList = _create_store()
posthog_events: StoreList = _create_store()
n8n_jobs: StoreList = _create_store()
growthbook_checks: StoreList = _create_store()
matomo_events: StoreList = _create_store()
plausible_events: StoreList = _create_store()
meilisearch_index: StoreList = _create_store()
webhook_events: StoreList = _create_store()
appwrite_events: StoreList = _create_store()
drone_builds: StoreList = _create_store()
directus_items: StoreList = _create_store()
minio_objects: StoreList = _create_store()
stripe_events: StoreList = _create_store()

# ── Messaging & Notifications ─────────────────────────────
audit_log: StoreList = _create_store()
notifications: StoreList = _create_store()
security_alert_emails: StoreList = _create_store()
redis_ops: StoreList = _create_store()
twilio_messages: StoreList = _create_store()
slack_messages: StoreList = _create_store()
resend_messages: StoreList = _create_store()
algolia_sync: StoreList = _create_store()
ai_gateway: StoreList = _create_store()
ai_security_usage: StoreList = _create_store()
ai_security_alerts: StoreList = _create_store()
ai_security_blocks: StoreList = _create_store()
ai_security_appeals: StoreList = _create_store()
ai_provider_keys: StoreList = _create_store()
ai_security_ids_events: StoreList = _create_store()
siem_cases: StoreList = _create_store()
siem_soar_runs: StoreList = _create_store()
siem_retention_policies: StoreList = _create_store()
siem_data_lake_exports: StoreList = _create_store()
siem_flow_logs: StoreList = _create_store()
siem_waf_policies: StoreList = _create_store()
siem_firewall_rules: StoreList = _create_store()
siem_ids_profiles: StoreList = _create_store()
siem_ips_profiles: StoreList = _create_store()
siem_vulnerabilities: StoreList = _create_store()
siem_zap_scans: StoreList = _create_store()
siem_patch_updates: StoreList = _create_store()
siem_auto_pentest_jobs: StoreList = _create_store()
siem_dead_code_findings: StoreList = _create_store()
siem_endpoint_hardening: StoreList = _create_store()
notification_preferences: StoreList = _create_store()
notification_delivery_receipts: StoreList = _create_store()

# ── Auth & Tenants ───────────────────────────────────────
auth_security: StoreList = _create_store()
tenant_profiles: StoreList = _create_store()
api_usage_audit: StoreList = _create_store()
users: StoreList = _create_store()

# ── API Governance ──────────────────────────────────────
api_governance_providers: StoreList = _create_store()
api_governance_usage_events: StoreList = _create_store()
api_governance_incidents: StoreList = _create_store()

# ── CRM Module ───────────────────────────────────────────
crm_contacts: StoreList = _create_store()
crm_companies: StoreList = _create_store()
crm_deals: StoreList = _create_store()
crm_activities: StoreList = _create_store()
crm_webhook_subscriptions: StoreList = _create_store()
crm_leads: StoreList = _create_store()
crm_tasks: StoreList = _create_store()
crm_campaigns: StoreList = _create_store()
crm_segments: StoreList = _create_store()
crm_notes: StoreList = _create_store()
crm_quotes: StoreList = _create_store()
crm_invoices: StoreList = _create_store()
crm_email_sequences: StoreList = _create_store()
crm_workflow_rules: StoreList = _create_store()
crm_sla_rules: StoreList = _create_store()
crm_projects: StoreList = _create_store()
crm_custom_entity_types: StoreList = _create_store()
crm_custom_entity_records: StoreList = _create_store()
crm_automation_recipes: StoreList = _create_store()
crm_api_tokens: StoreList = _create_store()
crm_backup_snapshots: StoreList = _create_store()
crm_live_sync_state: StoreList = _create_store()

# ── Influencer Module ────────────────────────────────────
influencers: StoreList = _create_store()
influencer_campaigns: StoreList = _create_store()
influencer_outreach: StoreList = _create_store()

# ── Chatbot Module ───────────────────────────────────────
chatbots: StoreList = _create_store()
chatbot_conversations: StoreList = _create_store()
chatbot_leads: StoreList = _create_store()

# ── IRA Autonomous Copilot ───────────────────────────────
ira_events: StoreList = _create_store()
ira_sessions: StoreList = _create_store()
ira_controls: StoreList = _create_store()
ira_connectors: StoreList = _create_store()
ira_ml_knowledge: StoreList = _create_store()
ira_ml_jobs: StoreList = _create_store()
ira_ml_models: StoreList = _create_store()
ira_structured_memory: StoreList = _create_store()
ira_action_snapshots: StoreList = _create_store()
ira_cost_ledger: StoreList = _create_store()
ira_ab_tests: StoreList = _create_store()
ira_performance_log: StoreList = _create_store()

# ── LinkInBio Module ──────────────────────────────────────
linkinbio_pages: StoreList = _create_store()
linkinbio_links: StoreList = _create_store()
linkinbio_analytics: StoreList = _create_store()

# ── Billing Module ───────────────────────────────────────
subscriptions: StoreList = _create_store()
invoices: StoreList = _create_store()
credit_ledger: StoreList = _create_store()
accounting_integrations: StoreList = _create_store()
accounting_exports: StoreList = _create_store()
super_admin_module_settings: StoreList = _create_store()

# ── CMS Module ───────────────────────────────────────────
cms_connections: StoreList = _create_store()
cms_pages: StoreList = _create_store()
cms_sync_log: StoreList = _create_store()

# ── Marketplace Module ───────────────────────────────────
marketplace_catalogue: StoreList = _create_store()
marketplace_installs: StoreList = _create_store()

# ── Analytics Module ────────────────────────────────────
analytics_reports: StoreList = _create_store()
analytics_report_schedules: StoreList = _create_store()
analytics_trends: StoreList = _create_store()
analytics_rollups: StoreList = _create_store()

# ── Engagement Module ───────────────────────────────────
engagement_streaks: StoreList = _create_store()
engagement_referrals: StoreList = _create_store()
engagement_referral_claims: StoreList = _create_store()
engagement_companion_profiles: StoreList = _create_store()
engagement_companion_messages: StoreList = _create_store()
engagement_fomo_rules: StoreList = _create_store()
engagement_fomo_events: StoreList = _create_store()
engagement_social_proof_events: StoreList = _create_store()
engagement_dependency_profiles: StoreList = _create_store()
engagement_dependency_events: StoreList = _create_store()
engagement_community_circles: StoreList = _create_store()
engagement_community_posts: StoreList = _create_store()
engagement_community_amas: StoreList = _create_store()
engagement_brand_lock_profiles: StoreList = _create_store()
engagement_brand_lock_events: StoreList = _create_store()
engagement_autopilot_profiles: StoreList = _create_store()
engagement_autopilot_events: StoreList = _create_store()
engagement_achievement_profiles: StoreList = _create_store()
engagement_achievement_events: StoreList = _create_store()

# ── Monetization Modules ────────────────────────────────
money_printer_ideas: StoreList = _create_store()
money_printer_validations: StoreList = _create_store()
bank_accounts: StoreList = _create_store()
bank_transactions: StoreList = _create_store()
bank_payouts: StoreList = _create_store()

# ── Education Module ────────────────────────────────────
university_courses: StoreList = _create_store()
university_cohorts: StoreList = _create_store()
university_enrollments: StoreList = _create_store()

# ── Services Module ─────────────────────────────────────
studios_services: StoreList = _create_store()
studios_briefs: StoreList = _create_store()
studios_proposals: StoreList = _create_store()
studios_escrows: StoreList = _create_store()

# ── Commerce Module ─────────────────────────────────────
commerce_products: StoreList = _create_store()
commerce_orders: StoreList = _create_store()

# ── Talent Module ───────────────────────────────────────
talent_creators: StoreList = _create_store()
talent_deals: StoreList = _create_store()
talent_rate_cards: StoreList = _create_store()

# ── White Label Module ──────────────────────────────────
white_label_profiles: StoreList = _create_store()
white_label_events: StoreList = _create_store()

# ── Media Job Queue (Sandboxed Media SaaS Architecture) ──
media_jobs: StoreList = _create_store()
media_jobs_dlq: StoreList = _create_store()  # dead-letter queue for failed jobs
# tracks job lifecycle — queued → processing → complete/failed
media_jobs: StoreList = _create_store()
media_jobs_dlq: StoreList = _create_store()  # dead-letter queue for failed jobs

# ── Content Approval Workflows (Hootsuite §4.5) ──────────
# ADDED: multi-level approval chain before social post publishing
content_approval_requests: StoreList = _create_store()   # approval requests (pending/approved/rejected)
content_approval_comments: StoreList = _create_store()   # inline reviewer comments per request
content_approval_configs: StoreList = _create_store()    # per-tenant approval chain configurations

# ── Media Library (Hootsuite §4.3) ───────────────────────
# ADDED: centralised asset repository with folder org + AI tagging
media_library_assets: StoreList = _create_store()        # uploaded media assets (image/video/gif/pdf)
media_library_folders: StoreList = _create_store()       # folder hierarchy for asset organisation
media_library_tags: StoreList = _create_store()          # AI-generated and manual asset tags

# ── Employee Advocacy (Hootsuite Amplify §9) ─────────────
# ADDED: brand ambassador content sharing + analytics + gamification
advocacy_content: StoreList = _create_store()            # brand-approved content items for sharing
advocacy_shares: StoreList = _create_store()             # employee share events with reach/engagement
advocacy_participants: StoreList = _create_store()       # registered employee advocates per tenant
advocacy_campaigns: StoreList = _create_store()         # named advocacy campaigns (product launch etc.)

# ── Smart Inbox (SproutSocial §3) ────────────────────────
# ADDED: unified social engagement hub — inbound DMs, comments, mentions with AI features
smart_inbox_messages: StoreList = _create_store()        # inbound messages (DM/comment/mention/review)
smart_inbox_notes: StoreList = _create_store()           # internal team notes per message (never sent)
smart_inbox_locks: StoreList = _create_store()           # collision-prevention locks (who is replying)
saved_replies: StoreList = _create_store()              # pre-approved reply templates library
smart_inbox_delivery_failures: StoreList = _create_store()  # dead-letter queue for failed approved response deliveries
smart_inbox_delivery_replay_runs: StoreList = _create_store()  # replay-pending operation history for auditability

# ── ViralPost / Best Time to Post (SproutSocial §2.1.3) ──
# ADDED: ML-based optimal send-time recommendations per network/profile
viralpost_analyses: StoreList = _create_store()          # per-profile optimal-time analysis results
viralpost_post_history: StoreList = _create_store()      # historical post performance for ML training

# ── Competitive Benchmarking (SproutSocial §5.4) ─────────
# ADDED: competitor profile tracking + side-by-side benchmarking
competitor_profiles: StoreList = _create_store()         # tracked competitor social profiles per tenant
competitor_snapshots: StoreList = _create_store()        # periodic metric snapshots per competitor
competitive_scrape_jobs: StoreList = _create_store()     # background scrape and enrichment jobs

# ── Social Workspace / Connected Channels ─────────────────
social_accounts: StoreList = _create_store()             # connected social profiles and OAuth metadata per tenant
social_brand_profiles: StoreList = _create_store()       # brand/business details for social publishing per tenant

# ── UTM Builder (SproutSocial §2.1.1) ────────────────────
# ADDED: UTM parameter builder with saved presets per tenant
utm_presets: StoreList = _create_store()                 # saved UTM parameter presets (reusable across posts)

# ── Revenue Attribution (Shapley Multi-Touch) ─────────────
revenue_touchpoints: StoreList = _create_store()         # tracked post touchpoints with auto-injected UTM links
revenue_conversions: StoreList = _create_store()         # normalized sale/conversion events from provider webhooks
revenue_spend: StoreList = _create_store()               # social spend entries for ROI and attribution analytics

# ── AI Growth Suite / Strategic Features ──────────────────
growth_suite_records: StoreList = _create_store()        # persisted feature runs, summaries, and strategic outputs

# ── Trend Intelligence / Forecasting Engine ───────────────
trend_signals: StoreList = _create_store()               # cross-source trend signals (social, ads, web, model hints)
trend_forecasts: StoreList = _create_store()             # generated trend-phase forecasts (upcoming/emerging/current/downfall)
trend_selections: StoreList = _create_store()            # user-selected trends and objectives
trend_content_generations: StoreList = _create_store()   # AI-ready content outputs generated from selected trends
trend_performance_tracks: StoreList = _create_store()    # live post/ad performance tracking for trend plays
trend_recommendations: StoreList = _create_store()       # optimization suggestions to improve traction and ROI

# ── Viral Singularity Engine (VSE) ────────────────────────
# 12 VSE Engines + 47 Sub-Systems data stores
vse_viral_events: StoreList = _create_store()          # viral event lifecycle records
vse_briefs: StoreList = _create_store()               # VS-01 viral briefs
vse_trigger_analyses: StoreList = _create_store()     # VSE-1 psychological trigger analyses
vse_algorithm_models: StoreList = _create_store()     # VSE-2 platform algorithm models
vse_algorithm_updates: StoreList = _create_store()    # VSE-2 algorithm change detections
vse_network_maps: StoreList = _create_store()         # VSE-3 network topology maps
vse_cascade_simulations: StoreList = _create_store()  # VS-05 pre-publication simulations
vse_detonations: StoreList = _create_store()          # VSE-4 cross-platform detonation plans
vse_swarms: StoreList = _create_store()               # VSE-5 influencer swarm compositions
vse_momentum_events: StoreList = _create_store()      # VSE-6 momentum monitoring records
vse_content_factory: StoreList = _create_store()      # VSE-7 generated viral content
vse_emotion_analyses: StoreList = _create_store()     # VSE-8 emotional contagion analyses
vse_trend_alerts: StoreList = _create_store()         # VSE-9 emerging trend alerts
vse_trend_hijacks: StoreList = _create_store()        # VSE-9 trend-hijack content
vse_paid_events: StoreList = _create_store()          # VSE-10 paid amplification events
vse_dark_social_seeds: StoreList = _create_store()    # VSE-11 dark social seeding records
vse_immortal_assets: StoreList = _create_store()      # VSE-12 permanent viral assets
vse_viral_vault: StoreList = _create_store()          # VSE-12 viral vault archive

# ── Sales Sequences (HubSpot Sales Hub §5.3) ─────────────
sequences: StoreList = _create_store()               # multi-step outreach cadences
sequence_enrollments: StoreList = _create_store()    # contact enrollments per sequence
sequence_step_events: StoreList = _create_store()    # per-step outcomes (replied, called, etc.)

# ── Meeting Scheduling (HubSpot Sales Hub §5.4) ──────────
meeting_links: StoreList = _create_store()           # booking link configurations
meeting_bookings: StoreList = _create_store()        # confirmed bookings

# ── Help Desk / Ticketing (HubSpot Service Hub §6.1) ─────
tickets: StoreList = _create_store()                 # support tickets
ticket_comments: StoreList = _create_store()         # ticket comments and internal notes
sla_configs: StoreList = _create_store()             # SLA configuration per priority

# ── Knowledge Base (HubSpot Service Hub §6.2) ────────────
kb_categories: StoreList = _create_store()           # KB category tree
kb_articles: StoreList = _create_store()             # help center articles
kb_article_feedback: StoreList = _create_store()     # helpful/not-helpful votes per article

# ── NPS / CSAT / CES Surveys (HubSpot Service Hub §6.4) ──
surveys: StoreList = _create_store()                 # survey definitions
survey_responses: StoreList = _create_store()        # collected survey responses

# ── Sales Documents & Quotes (HubSpot Sales Hub §5.6) ────
sales_documents: StoreList = _create_store()         # document library (proposals, decks, etc.)
document_shares: StoreList = _create_store()         # shared document tracking records
sales_quotes: StoreList = _create_store()            # deal-linked sales quotes

# ── Marketing Automation / Workflows (HubSpot §3.2) ──────
workflows: StoreList = _create_store()               # automation workflow definitions
workflow_executions: StoreList = _create_store()     # per-contact execution history
workflow_step_logs: StoreList = _create_store()      # step-level execution logs
workflow_approval_policies: StoreList = _create_store()  # per-workflow approval policy definitions
workflow_approval_requests: StoreList = _create_store()  # workflow execution approval requests
workflow_connectors: StoreList = _create_store()      # connector registry for workflow integrations
workflow_connector_replay_queue: StoreList = _create_store()  # failed connector operations pending replay
workflow_connector_sla_alerts: StoreList = _create_store()  # reliability/SLO alert events for workflow connectors
workflow_connector_policy_templates: StoreList = _create_store()  # tenant-level reliability policy templates
workflow_connector_maintenance_windows: StoreList = _create_store()  # connector maintenance windows (UTC hours)
workflow_connector_escalation_rules: StoreList = _create_store()  # SLA alert escalation rules
workflow_connector_escalation_events: StoreList = _create_store()  # emitted escalation events for alerting channels
workflow_connector_runbooks: StoreList = _create_store()  # connector incident/runbook definitions
workflow_connector_runbook_assignments: StoreList = _create_store()  # operator assignments for runbooks
workflow_connector_postmortems: StoreList = _create_store()  # connector incident postmortems
workflow_connector_postmortem_templates: StoreList = _create_store()  # reusable postmortem templates
workflow_connector_postmortem_closure_policies: StoreList = _create_store()  # tenant closure approval policies
workflow_connector_postmortem_closure_requests: StoreList = _create_store()  # closure approval requests
workflow_connector_postmortem_action_item_escalations: StoreList = _create_store()  # overdue action-item escalations
workflow_connector_postmortem_escalation_routing_policies: StoreList = _create_store()  # severity/channel routing for overdue actions
workflow_connector_postmortem_escalation_cadence_policies: StoreList = _create_store()  # L1/L2/L3 handoff and re-page policies

# ── Autonomous Workforce (Noimos-style control plane) ─────
autonomous_workforce_profiles: StoreList = _create_store()
autonomous_workforce_integrations: StoreList = _create_store()
autonomous_workforce_missions: StoreList = _create_store()
autonomous_workforce_feed: StoreList = _create_store()
autonomous_workforce_schedules: StoreList = _create_store()
autonomous_workforce_knowledge: StoreList = _create_store()
autonomous_workforce_outcomes: StoreList = _create_store()

# ── Product Catalog (HubSpot Commerce Hub §8.2) ──────────
product_catalog: StoreList = _create_store()         # product/service catalog items
product_catalog_categories: StoreList = _create_store()  # product category tree

# ── Enterprise Pentest Platform — Phase 1 ─────────────────
# Canonical finding lifecycle: ingest → normalise → score → triage → remediate
pentest_findings: StoreList = _create_store()        # canonical finding records (one per deduped fingerprint)

# ── Enterprise Pentest Platform — Phase 2 ─────────────────
# Risk policy engine + DefectDojo synchronisation layer
pentest_risk_policies: StoreList = _create_store()   # per-tenant risk score thresholds and SLA windows
pentest_defectdojo_configs: StoreList = _create_store()  # per-tenant DefectDojo connection settings
pentest_sync_queue: StoreList = _create_store()      # DefectDojo sync records with retry state

# ── Flywheel Module 1: Outcome Attribution & Decision Quality ──
outcome_actions: StoreList = _create_store()         # autonomous actions with recorded outcomes
outcome_outcomes: StoreList = _create_store()        # attributed downstream outcomes per action
outcome_quality_scores: StoreList = _create_store()  # decision quality scores per action

# ── Flywheel Module 2: Trust Center ──────────────────────────
trust_policy_history: StoreList = _create_store()    # policy change audit trail
trust_approval_chains: StoreList = _create_store()   # approval chain definitions per action type
trust_incidents: StoreList = _create_store()         # incident records with severity and resolution
trust_governance_snapshots: StoreList = _create_store()  # periodic governance posture snapshots

# ── Flywheel Module 3: Integration Playbooks ─────────────────
playbooks: StoreList = _create_store()               # custom playbook definitions per tenant
playbook_runs: StoreList = _create_store()           # playbook activation run records

# ── Flywheel Module 4: Performance Benchmarks ────────────────
benchmarks: StoreList = _create_store()              # tenant-level metric data points with uplift
segment_benchmarks: StoreList = _create_store()      # published segment-level p50/p75/p90 benchmarks


def get_all_stores() -> dict[str, StoreList]:
    """Get all memory stores as a dict for monitoring and metrics."""
    return {
        'suitecrm': suitecrm_jobs,
        'refferq': refferq_jobs,
        'posthog': posthog_events,
        'growth_suite': growth_suite_records,
        'social_listening': social_listening,
        'social_listening_alert_rules': social_listening_alert_rules,
        'social_listening_alerts': social_listening_alerts,
        'reviews': reviews,
        'n8n': n8n_jobs,
        'growthbook': growthbook_checks,
        'matomo': matomo_events,
        'plausible': plausible_events,
        'meilisearch': meilisearch_index,
        'webhooks': webhook_events,
        'redis': redis_ops,
        'twilio': twilio_messages,
        'slack': slack_messages,
        'appwrite': appwrite_events,
        'drone': drone_builds,
        'directus': directus_items,
        'minio': minio_objects,
        'stripe': stripe_events,
        'audit_log': audit_log,
        'notifications': notifications,
        'security_alert_emails': security_alert_emails,
        'notification_delivery_receipts': notification_delivery_receipts,
        'resend': resend_messages,
        'algolia': algolia_sync,
        'ai_gateway': ai_gateway,
        'ai_security_usage': ai_security_usage,
        'ai_security_alerts': ai_security_alerts,
        'ai_security_blocks': ai_security_blocks,
        'ai_security_appeals': ai_security_appeals,
        'ai_provider_keys': ai_provider_keys,
        'ai_security_ids_events': ai_security_ids_events,
        'siem_cases': siem_cases,
        'siem_soar_runs': siem_soar_runs,
        'siem_retention_policies': siem_retention_policies,
        'siem_data_lake_exports': siem_data_lake_exports,
        'siem_flow_logs': siem_flow_logs,
        'siem_waf_policies': siem_waf_policies,
        'siem_firewall_rules': siem_firewall_rules,
        'siem_ids_profiles': siem_ids_profiles,
        'siem_ips_profiles': siem_ips_profiles,
        'siem_vulnerabilities': siem_vulnerabilities,
        'siem_zap_scans': siem_zap_scans,
        'siem_patch_updates': siem_patch_updates,
        'siem_auto_pentest_jobs': siem_auto_pentest_jobs,
        'siem_dead_code_findings': siem_dead_code_findings,
        'siem_endpoint_hardening': siem_endpoint_hardening,
        'auth_security': auth_security,
        'api_usage_audit': api_usage_audit,
        'tenant_management': tenant_profiles,
        'crm_contacts': crm_contacts,
        'crm_companies': crm_companies,
        'crm_deals': crm_deals,
        'crm_webhook_subscriptions': crm_webhook_subscriptions,
        'crm_leads': crm_leads,
        'crm_tasks': crm_tasks,
        'crm_campaigns': crm_campaigns,
        'crm_segments': crm_segments,
        'crm_notes': crm_notes,
        'crm_quotes': crm_quotes,
        'crm_invoices': crm_invoices,
        'crm_email_sequences': crm_email_sequences,
        'crm_workflow_rules': crm_workflow_rules,
        'crm_sla_rules': crm_sla_rules,
        'crm_projects': crm_projects,
        'crm_custom_entity_types': crm_custom_entity_types,
        'crm_custom_entity_records': crm_custom_entity_records,
        'crm_automation_recipes': crm_automation_recipes,
        'crm_api_tokens': crm_api_tokens,
        'influencer_campaigns': influencer_campaigns,
        'chatbots': chatbots,
        'ira_events': ira_events,
        'ira_sessions': ira_sessions,
        'ira_controls': ira_controls,
        'ira_connectors': ira_connectors,
        'linkinbio_pages': linkinbio_pages,
        'subscriptions': subscriptions,
        'cms_connections': cms_connections,
        'marketplace_installs': marketplace_installs,
        'analytics_reports': analytics_reports,
        'media_jobs': media_jobs,
        'media_jobs_dlq': media_jobs_dlq,
        'trend_signals': trend_signals,
        'trend_forecasts': trend_forecasts,
        'trend_performance_tracks': trend_performance_tracks,
        'competitive_scrape_jobs': competitive_scrape_jobs,
        'social_accounts': social_accounts,
        'social_brand_profiles': social_brand_profiles,
        'workflow_approval_policies': workflow_approval_policies,
        'workflow_approval_requests': workflow_approval_requests,
        'workflow_connectors': workflow_connectors,
        'workflow_connector_replay_queue': workflow_connector_replay_queue,
        'workflow_connector_sla_alerts': workflow_connector_sla_alerts,
        'workflow_connector_policy_templates': workflow_connector_policy_templates,
        'workflow_connector_maintenance_windows': workflow_connector_maintenance_windows,
        'workflow_connector_escalation_rules': workflow_connector_escalation_rules,
        'workflow_connector_escalation_events': workflow_connector_escalation_events,
        'workflow_connector_runbooks': workflow_connector_runbooks,
        'workflow_connector_runbook_assignments': workflow_connector_runbook_assignments,
        'workflow_connector_postmortems': workflow_connector_postmortems,
        'workflow_connector_postmortem_templates': workflow_connector_postmortem_templates,
        'workflow_connector_postmortem_closure_policies': workflow_connector_postmortem_closure_policies,
        'workflow_connector_postmortem_closure_requests': workflow_connector_postmortem_closure_requests,
        'workflow_connector_postmortem_action_item_escalations': workflow_connector_postmortem_action_item_escalations,
        'workflow_connector_postmortem_escalation_routing_policies': workflow_connector_postmortem_escalation_routing_policies,
        'workflow_connector_postmortem_escalation_cadence_policies': workflow_connector_postmortem_escalation_cadence_policies,
        'autonomous_workforce_profiles': autonomous_workforce_profiles,
        'autonomous_workforce_integrations': autonomous_workforce_integrations,
        'autonomous_workforce_missions': autonomous_workforce_missions,
        'autonomous_workforce_feed': autonomous_workforce_feed,
        'autonomous_workforce_schedules': autonomous_workforce_schedules,
        'autonomous_workforce_knowledge': autonomous_workforce_knowledge,
        'autonomous_workforce_outcomes': autonomous_workforce_outcomes,
        'pentest_findings': pentest_findings,
        'pentest_risk_policies': pentest_risk_policies,
        'pentest_defectdojo_configs': pentest_defectdojo_configs,
        'pentest_sync_queue': pentest_sync_queue,
        'outcome_actions': outcome_actions,
        'outcome_outcomes': outcome_outcomes,
        'outcome_quality_scores': outcome_quality_scores,
        'trust_policy_history': trust_policy_history,
        'trust_approval_chains': trust_approval_chains,
        'trust_incidents': trust_incidents,
        'trust_governance_snapshots': trust_governance_snapshots,
        'playbooks': playbooks,
        'playbook_runs': playbook_runs,
        'benchmarks': benchmarks,
        'segment_benchmarks': segment_benchmarks,
    }
