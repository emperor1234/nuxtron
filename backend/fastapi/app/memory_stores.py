"""
Centralized memory store definitions for all modules.
Reduces main.py complexity and improves organization.
"""

StoreItem = dict[str, object]
StoreList = list[StoreItem]

# ── Social & Content ──────────────────────────────────────
scheduled_posts: StoreList = []
email_contacts: StoreList = []
email_campaigns: StoreList = []
social_listening: StoreList = []
social_listening_alert_rules: StoreList = []
social_listening_alerts: StoreList = []
reviews: StoreList = []
seo_analyses: StoreList = []

# ── Integration Jobs & Events ─────────────────────────────
suitecrm_jobs: StoreList = []
refferq_jobs: StoreList = []
posthog_events: StoreList = []
n8n_jobs: StoreList = []
growthbook_checks: StoreList = []
matomo_events: StoreList = []
plausible_events: StoreList = []
meilisearch_index: StoreList = []
webhook_events: StoreList = []
appwrite_events: StoreList = []
drone_builds: StoreList = []
directus_items: StoreList = []
minio_objects: StoreList = []
stripe_events: StoreList = []

# ── Messaging & Notifications ─────────────────────────────
audit_log: StoreList = []
notifications: StoreList = []
redis_ops: StoreList = []
twilio_messages: StoreList = []
slack_messages: StoreList = []
resend_messages: StoreList = []
algolia_sync: StoreList = []
ai_gateway: StoreList = []
ai_security_usage: StoreList = []
ai_security_alerts: StoreList = []
ai_security_blocks: StoreList = []
ai_security_appeals: StoreList = []
ai_provider_keys: StoreList = []
ai_security_ids_events: StoreList = []
siem_cases: StoreList = []
siem_soar_runs: StoreList = []
siem_retention_policies: StoreList = []
siem_data_lake_exports: StoreList = []
siem_flow_logs: StoreList = []
siem_waf_policies: StoreList = []
siem_firewall_rules: StoreList = []
siem_ids_profiles: StoreList = []
siem_ips_profiles: StoreList = []
siem_vulnerabilities: StoreList = []
siem_zap_scans: StoreList = []
siem_patch_updates: StoreList = []
siem_auto_pentest_jobs: StoreList = []
siem_dead_code_findings: StoreList = []
siem_endpoint_hardening: StoreList = []
notification_preferences: StoreList = []
notification_delivery_receipts: StoreList = []

# ── Auth & Tenants ───────────────────────────────────────
auth_security: StoreList = []
tenant_profiles: StoreList = []
api_usage_audit: StoreList = []
users: StoreList = []

# ── API Governance ──────────────────────────────────────
api_governance_providers: StoreList = []
api_governance_usage_events: StoreList = []
api_governance_incidents: StoreList = []

# ── CRM Module ───────────────────────────────────────────
crm_contacts: StoreList = []
crm_companies: StoreList = []
crm_deals: StoreList = []
crm_activities: StoreList = []
crm_webhook_subscriptions: StoreList = []
crm_leads: StoreList = []
crm_tasks: StoreList = []
crm_campaigns: StoreList = []
crm_segments: StoreList = []
crm_notes: StoreList = []
crm_quotes: StoreList = []
crm_invoices: StoreList = []
crm_email_sequences: StoreList = []
crm_workflow_rules: StoreList = []
crm_sla_rules: StoreList = []
crm_projects: StoreList = []
crm_custom_entity_types: StoreList = []
crm_custom_entity_records: StoreList = []
crm_automation_recipes: StoreList = []
crm_api_tokens: StoreList = []
crm_backup_snapshots: StoreList = []
crm_live_sync_state: StoreList = []

# ── Influencer Module ────────────────────────────────────
influencers: StoreList = []
influencer_campaigns: StoreList = []
influencer_outreach: StoreList = []

# ── Chatbot Module ───────────────────────────────────────
chatbots: StoreList = []
chatbot_conversations: StoreList = []
chatbot_leads: StoreList = []

# ── IRA Autonomous Copilot ───────────────────────────────
ira_events: StoreList = []
ira_sessions: StoreList = []
ira_controls: StoreList = []
ira_connectors: StoreList = []
ira_ml_knowledge: StoreList = []
ira_ml_jobs: StoreList = []
ira_ml_models: StoreList = []
ira_structured_memory: StoreList = []
ira_action_snapshots: StoreList = []
ira_cost_ledger: StoreList = []
ira_ab_tests: StoreList = []
ira_performance_log: StoreList = []

# ── LinkInBio Module ──────────────────────────────────────
linkinbio_pages: StoreList = []
linkinbio_links: StoreList = []
linkinbio_analytics: StoreList = []

# ── Billing Module ───────────────────────────────────────
subscriptions: StoreList = []
invoices: StoreList = []
credit_ledger: StoreList = []
accounting_integrations: StoreList = []
accounting_exports: StoreList = []
super_admin_module_settings: StoreList = []

# ── CMS Module ───────────────────────────────────────────
cms_connections: StoreList = []
cms_pages: StoreList = []
cms_sync_log: StoreList = []

# ── Marketplace Module ───────────────────────────────────
marketplace_catalogue: StoreList = []
marketplace_installs: StoreList = []

# ── Analytics Module ────────────────────────────────────
analytics_reports: StoreList = []
analytics_report_schedules: StoreList = []
analytics_trends: StoreList = []
analytics_rollups: StoreList = []

# ── Engagement Module ───────────────────────────────────
engagement_streaks: StoreList = []
engagement_referrals: StoreList = []
engagement_referral_claims: StoreList = []
engagement_companion_profiles: StoreList = []
engagement_companion_messages: StoreList = []
engagement_fomo_rules: StoreList = []
engagement_fomo_events: StoreList = []
engagement_social_proof_events: StoreList = []
engagement_dependency_profiles: StoreList = []
engagement_dependency_events: StoreList = []
engagement_community_circles: StoreList = []
engagement_community_posts: StoreList = []
engagement_community_amas: StoreList = []
engagement_brand_lock_profiles: StoreList = []
engagement_brand_lock_events: StoreList = []
engagement_autopilot_profiles: StoreList = []
engagement_autopilot_events: StoreList = []
engagement_achievement_profiles: StoreList = []
engagement_achievement_events: StoreList = []

# ── Monetization Modules ────────────────────────────────
money_printer_ideas: StoreList = []
money_printer_validations: StoreList = []
bank_accounts: StoreList = []
bank_transactions: StoreList = []
bank_payouts: StoreList = []

# ── Education Module ────────────────────────────────────
university_courses: StoreList = []
university_cohorts: StoreList = []
university_enrollments: StoreList = []

# ── Services Module ─────────────────────────────────────
studios_services: StoreList = []
studios_briefs: StoreList = []
studios_proposals: StoreList = []
studios_escrows: StoreList = []

# ── Commerce Module ─────────────────────────────────────
commerce_products: StoreList = []
commerce_orders: StoreList = []

# ── Talent Module ───────────────────────────────────────
talent_creators: StoreList = []
talent_deals: StoreList = []
talent_rate_cards: StoreList = []

# ── White Label Module ──────────────────────────────────
white_label_profiles: StoreList = []
white_label_events: StoreList = []

# ── Media Job Queue (Sandboxed Media SaaS Architecture) ──
media_jobs: StoreList = []
media_jobs_dlq: StoreList = []  # dead-letter queue for failed jobs
# tracks job lifecycle — queued → processing → complete/failed
media_jobs: StoreList = []
media_jobs_dlq: StoreList = []  # dead-letter queue for failed jobs

# ── Content Approval Workflows (Hootsuite §4.5) ──────────
# ADDED: multi-level approval chain before social post publishing
content_approval_requests: StoreList = []   # approval requests (pending/approved/rejected)
content_approval_comments: StoreList = []   # inline reviewer comments per request
content_approval_configs: StoreList = []    # per-tenant approval chain configurations

# ── Media Library (Hootsuite §4.3) ───────────────────────
# ADDED: centralised asset repository with folder org + AI tagging
media_library_assets: StoreList = []        # uploaded media assets (image/video/gif/pdf)
media_library_folders: StoreList = []       # folder hierarchy for asset organisation
media_library_tags: StoreList = []          # AI-generated and manual asset tags

# ── Employee Advocacy (Hootsuite Amplify §9) ─────────────
# ADDED: brand ambassador content sharing + analytics + gamification
advocacy_content: StoreList = []            # brand-approved content items for sharing
advocacy_shares: StoreList = []             # employee share events with reach/engagement
advocacy_participants: StoreList = []       # registered employee advocates per tenant
advocacy_campaigns: StoreList = []         # named advocacy campaigns (product launch etc.)

# ── Smart Inbox (SproutSocial §3) ────────────────────────
# ADDED: unified social engagement hub — inbound DMs, comments, mentions with AI features
smart_inbox_messages: StoreList = []        # inbound messages (DM/comment/mention/review)
smart_inbox_notes: StoreList = []           # internal team notes per message (never sent)
smart_inbox_locks: StoreList = []           # collision-prevention locks (who is replying)
saved_replies: StoreList = []              # pre-approved reply templates library
smart_inbox_delivery_failures: StoreList = []  # dead-letter queue for failed approved response deliveries
smart_inbox_delivery_replay_runs: StoreList = []  # replay-pending operation history for auditability

# ── ViralPost / Best Time to Post (SproutSocial §2.1.3) ──
# ADDED: ML-based optimal send-time recommendations per network/profile
viralpost_analyses: StoreList = []          # per-profile optimal-time analysis results
viralpost_post_history: StoreList = []      # historical post performance for ML training

# ── Competitive Benchmarking (SproutSocial §5.4) ─────────
# ADDED: competitor profile tracking + side-by-side benchmarking
competitor_profiles: StoreList = []         # tracked competitor social profiles per tenant
competitor_snapshots: StoreList = []        # periodic metric snapshots per competitor
competitive_scrape_jobs: StoreList = []     # background scrape and enrichment jobs

# ── Social Workspace / Connected Channels ─────────────────
social_accounts: StoreList = []             # connected social profiles and OAuth metadata per tenant
social_brand_profiles: StoreList = []       # brand/business details for social publishing per tenant

# ── UTM Builder (SproutSocial §2.1.1) ────────────────────
# ADDED: UTM parameter builder with saved presets per tenant
utm_presets: StoreList = []                 # saved UTM parameter presets (reusable across posts)

# ── Revenue Attribution (Shapley Multi-Touch) ─────────────
revenue_touchpoints: StoreList = []         # tracked post touchpoints with auto-injected UTM links
revenue_conversions: StoreList = []         # normalized sale/conversion events from provider webhooks
revenue_spend: StoreList = []               # social spend entries for ROI and attribution analytics

# ── AI Growth Suite / Strategic Features ──────────────────
growth_suite_records: StoreList = []        # persisted feature runs, summaries, and strategic outputs

# ── Trend Intelligence / Forecasting Engine ───────────────
trend_signals: StoreList = []               # cross-source trend signals (social, ads, web, model hints)
trend_forecasts: StoreList = []             # generated trend-phase forecasts (upcoming/emerging/current/downfall)
trend_selections: StoreList = []            # user-selected trends and objectives
trend_content_generations: StoreList = []   # AI-ready content outputs generated from selected trends
trend_performance_tracks: StoreList = []    # live post/ad performance tracking for trend plays
trend_recommendations: StoreList = []       # optimization suggestions to improve traction and ROI

# ── Viral Singularity Engine (VSE) ────────────────────────
# 12 VSE Engines + 47 Sub-Systems data stores
vse_viral_events: StoreList = []          # viral event lifecycle records
vse_briefs: StoreList = []               # VS-01 viral briefs
vse_trigger_analyses: StoreList = []     # VSE-1 psychological trigger analyses
vse_algorithm_models: StoreList = []     # VSE-2 platform algorithm models
vse_algorithm_updates: StoreList = []    # VSE-2 algorithm change detections
vse_network_maps: StoreList = []         # VSE-3 network topology maps
vse_cascade_simulations: StoreList = []  # VS-05 pre-publication simulations
vse_detonations: StoreList = []          # VSE-4 cross-platform detonation plans
vse_swarms: StoreList = []               # VSE-5 influencer swarm compositions
vse_momentum_events: StoreList = []      # VSE-6 momentum monitoring records
vse_content_factory: StoreList = []      # VSE-7 generated viral content
vse_emotion_analyses: StoreList = []     # VSE-8 emotional contagion analyses
vse_trend_alerts: StoreList = []         # VSE-9 emerging trend alerts
vse_trend_hijacks: StoreList = []        # VSE-9 trend-hijack content
vse_paid_events: StoreList = []          # VSE-10 paid amplification events
vse_dark_social_seeds: StoreList = []    # VSE-11 dark social seeding records
vse_immortal_assets: StoreList = []      # VSE-12 permanent viral assets
vse_viral_vault: StoreList = []          # VSE-12 viral vault archive

# ── Sales Sequences (HubSpot Sales Hub §5.3) ─────────────
sequences: StoreList = []               # multi-step outreach cadences
sequence_enrollments: StoreList = []    # contact enrollments per sequence
sequence_step_events: StoreList = []    # per-step outcomes (replied, called, etc.)

# ── Meeting Scheduling (HubSpot Sales Hub §5.4) ──────────
meeting_links: StoreList = []           # booking link configurations
meeting_bookings: StoreList = []        # confirmed bookings

# ── Help Desk / Ticketing (HubSpot Service Hub §6.1) ─────
tickets: StoreList = []                 # support tickets
ticket_comments: StoreList = []         # ticket comments and internal notes
sla_configs: StoreList = []             # SLA configuration per priority

# ── Knowledge Base (HubSpot Service Hub §6.2) ────────────
kb_categories: StoreList = []           # KB category tree
kb_articles: StoreList = []             # help center articles
kb_article_feedback: StoreList = []     # helpful/not-helpful votes per article

# ── NPS / CSAT / CES Surveys (HubSpot Service Hub §6.4) ──
surveys: StoreList = []                 # survey definitions
survey_responses: StoreList = []        # collected survey responses

# ── Sales Documents & Quotes (HubSpot Sales Hub §5.6) ────
sales_documents: StoreList = []         # document library (proposals, decks, etc.)
document_shares: StoreList = []         # shared document tracking records
sales_quotes: StoreList = []            # deal-linked sales quotes

# ── Marketing Automation / Workflows (HubSpot §3.2) ──────
workflows: StoreList = []               # automation workflow definitions
workflow_executions: StoreList = []     # per-contact execution history
workflow_step_logs: StoreList = []      # step-level execution logs
workflow_approval_policies: StoreList = []  # per-workflow approval policy definitions
workflow_approval_requests: StoreList = []  # workflow execution approval requests
workflow_connectors: StoreList = []      # connector registry for workflow integrations
workflow_connector_replay_queue: StoreList = []  # failed connector operations pending replay
workflow_connector_sla_alerts: StoreList = []  # reliability/SLO alert events for workflow connectors
workflow_connector_policy_templates: StoreList = []  # tenant-level reliability policy templates
workflow_connector_maintenance_windows: StoreList = []  # connector maintenance windows (UTC hours)
workflow_connector_escalation_rules: StoreList = []  # SLA alert escalation rules
workflow_connector_escalation_events: StoreList = []  # emitted escalation events for alerting channels
workflow_connector_runbooks: StoreList = []  # connector incident/runbook definitions
workflow_connector_runbook_assignments: StoreList = []  # operator assignments for runbooks
workflow_connector_postmortems: StoreList = []  # connector incident postmortems
workflow_connector_postmortem_templates: StoreList = []  # reusable postmortem templates
workflow_connector_postmortem_closure_policies: StoreList = []  # tenant closure approval policies
workflow_connector_postmortem_closure_requests: StoreList = []  # closure approval requests
workflow_connector_postmortem_action_item_escalations: StoreList = []  # overdue action-item escalations
workflow_connector_postmortem_escalation_routing_policies: StoreList = []  # severity/channel routing for overdue actions
workflow_connector_postmortem_escalation_cadence_policies: StoreList = []  # L1/L2/L3 handoff and re-page policies

# ── Autonomous Workforce (Noimos-style control plane) ─────
autonomous_workforce_profiles: StoreList = []
autonomous_workforce_integrations: StoreList = []
autonomous_workforce_missions: StoreList = []
autonomous_workforce_feed: StoreList = []
autonomous_workforce_schedules: StoreList = []
autonomous_workforce_knowledge: StoreList = []
autonomous_workforce_outcomes: StoreList = []

# ── Product Catalog (HubSpot Commerce Hub §8.2) ──────────
product_catalog: StoreList = []         # product/service catalog items
product_catalog_categories: StoreList = []  # product category tree

# ── Enterprise Pentest Platform — Phase 1 ─────────────────
# Canonical finding lifecycle: ingest → normalise → score → triage → remediate
pentest_findings: StoreList = []        # canonical finding records (one per deduped fingerprint)

# ── Enterprise Pentest Platform — Phase 2 ─────────────────
# Risk policy engine + DefectDojo synchronisation layer
pentest_risk_policies: StoreList = []   # per-tenant risk score thresholds and SLA windows
pentest_defectdojo_configs: StoreList = []  # per-tenant DefectDojo connection settings
pentest_sync_queue: StoreList = []      # DefectDojo sync records with retry state

# ── Flywheel Module 1: Outcome Attribution & Decision Quality ──
outcome_actions: StoreList = []         # autonomous actions with recorded outcomes
outcome_outcomes: StoreList = []        # attributed downstream outcomes per action
outcome_quality_scores: StoreList = []  # decision quality scores per action

# ── Flywheel Module 2: Trust Center ──────────────────────────
trust_policy_history: StoreList = []    # policy change audit trail
trust_approval_chains: StoreList = []   # approval chain definitions per action type
trust_incidents: StoreList = []         # incident records with severity and resolution
trust_governance_snapshots: StoreList = []  # periodic governance posture snapshots

# ── Flywheel Module 3: Integration Playbooks ─────────────────
playbooks: StoreList = []               # custom playbook definitions per tenant
playbook_runs: StoreList = []           # playbook activation run records

# ── Flywheel Module 4: Performance Benchmarks ────────────────
benchmarks: StoreList = []              # tenant-level metric data points with uplift
segment_benchmarks: StoreList = []      # published segment-level p50/p75/p90 benchmarks


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
