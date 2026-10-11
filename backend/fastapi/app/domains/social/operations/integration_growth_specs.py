"""Social use cases: integration growth specs."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from fastapi import APIRouter
from typing import Any
from typing import cast


def operation__integration_growth_specs(st: _SocialWorkspaceState, router: APIRouter) -> list[dict[str, Any]]:
    return [
        {
            "integration": "Slack",
            "integration_key": "slack",
            "category": "communication",
            "impact_stars": 5,
            "roi_priority": 1,
            "phase": "phase_1_growth_activation",
            "why_it_drives_growth": "Team-level virality via alerts, approvals, and workflow fan-out into channel collaboration.",
            "how_it_works": "Uses social webhook ingress/egress and automation rules to trigger Slack notifications and operator workflows.",
            "vendors": ["Slack Web API", "Slack Incoming Webhooks"],
            "required_env_keys": ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET", "SLACK_WEBHOOK_URL"],
            "route_dependencies": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/rules",
            ],
        },
        {
            "integration": "Google Login",
            "integration_key": "google_login",
            "category": "identity_sso",
            "impact_stars": 5,
            "roi_priority": 2,
            "phase": "phase_1_growth_activation",
            "why_it_drives_growth": "Reduces signup friction and improves first-session activation.",
            "how_it_works": "OAuth-based social identity onboarding uses connect-all and account connect routes.",
            "vendors": ["Google OAuth"],
            "required_env_keys": ["GOOGLE_CLIENT_ID"],
            "route_dependencies": [
                "/social/oauth/{network}/start",
                "/social/oauth/{network}/callback",
                "/social/oauth/connect-all",
                "/social/accounts/connect",
            ],
        },
        {
            "integration": "Microsoft Login",
            "integration_key": "microsoft_login",
            "category": "identity_sso",
            "impact_stars": 5,
            "roi_priority": 3,
            "phase": "phase_1_growth_activation",
            "why_it_drives_growth": "Improves enterprise onboarding through Microsoft identity standards.",
            "how_it_works": "Microsoft OAuth login feeds social account auth/connect orchestration.",
            "vendors": ["Microsoft Entra ID OAuth"],
            "required_env_keys": ["MICROSOFT_CLIENT_ID"],
            "route_dependencies": [
                "/social/oauth/{network}/start",
                "/social/oauth/{network}/callback",
                "/social/oauth/connect-all",
                "/social/accounts/connect",
            ],
        },
        {
            "integration": "Zapier",
            "integration_key": "zapier",
            "category": "automation",
            "impact_stars": 5,
            "roi_priority": 4,
            "phase": "phase_1_growth_activation",
            "why_it_drives_growth": "Instantly expands addressable integrations and acquisition from no-code automators.",
            "how_it_works": "Inbound and outbound social integration webhooks provide event triggers and action targets for Zapier flows.",
            "vendors": ["Zapier Platform"],
            "required_env_keys": ["SOCIAL_WEBHOOK_SECRET", "ZAPIER_WEBHOOK_URL"],
            "route_dependencies": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/rules",
                "/social/automation/feeds",
            ],
        },
        {
            "integration": "Make",
            "integration_key": "make",
            "category": "automation",
            "impact_stars": 4,
            "roi_priority": 5,
            "phase": "phase_1_growth_activation",
            "why_it_drives_growth": "Strong adoption among technical operators and agencies with visual multi-step scenarios.",
            "how_it_works": "Shared integration webhook contracts plus queue/rule orchestration power Make scenarios.",
            "vendors": ["Make.com"],
            "required_env_keys": ["SOCIAL_WEBHOOK_SECRET", "MAKE_WEBHOOK_URL"],
            "route_dependencies": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/rules",
                "/social/automation/queue",
            ],
        },
        {
            "integration": "n8n",
            "integration_key": "n8n",
            "category": "automation",
            "impact_stars": 4,
            "roi_priority": 6,
            "phase": "phase_1_growth_activation",
            "why_it_drives_growth": "Developer and self-hosted teams can run private, high-control automations.",
            "how_it_works": "Webhook ingestion and automation queues expose deterministic jobs for n8n workflows.",
            "vendors": ["n8n"],
            "required_env_keys": ["N8N_WEBHOOK_URL", "N8N_API_KEY"],
            "route_dependencies": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/queue",
            ],
        },
        {
            "integration": "Google Drive",
            "integration_key": "google_drive",
            "category": "cloud_storage",
            "impact_stars": 4,
            "roi_priority": 7,
            "phase": "phase_1_growth_activation",
            "why_it_drives_growth": "Cuts content upload friction by reusing existing cloud assets.",
            "how_it_works": "Drive-connected media is routed into content import and browser capture queue flows.",
            "vendors": ["Google Drive API"],
            "required_env_keys": ["GOOGLE_DRIVE_CLIENT_ID"],
            "route_dependencies": [
                "/social/integrations/canva/import",
                "/social/extensions/browser/captures/{capture_id}/queue",
            ],
        },
        {
            "integration": "OneDrive",
            "integration_key": "onedrive",
            "category": "cloud_storage",
            "impact_stars": 4,
            "roi_priority": 8,
            "phase": "phase_1_growth_activation",
            "why_it_drives_growth": "Improves enterprise asset reuse and campaign throughput.",
            "how_it_works": "OneDrive assets are injected into import and queue publishing workflows.",
            "vendors": ["Microsoft OneDrive API"],
            "required_env_keys": ["ONEDRIVE_CLIENT_ID"],
            "route_dependencies": [
                "/social/integrations/canva/import",
                "/social/extensions/browser/captures/{capture_id}/queue",
            ],
        },
        {
            "integration": "Microsoft Teams",
            "integration_key": "microsoft_teams",
            "category": "communication",
            "impact_stars": 5,
            "roi_priority": 9,
            "phase": "phase_2_enterprise_sales",
            "why_it_drives_growth": "Enterprise deployment acceleration where Teams is the standard operational surface.",
            "how_it_works": "Teams connectors ingest webhook events and route automated actions through social automation policies.",
            "vendors": ["Microsoft Teams Workflows", "Microsoft Graph"],
            "required_env_keys": ["MS_TEAMS_WEBHOOK_URL", "MICROSOFT_TEAMS_APP_ID"],
            "route_dependencies": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/rules",
            ],
        },
        {
            "integration": "HubSpot",
            "integration_key": "hubspot",
            "category": "crm",
            "impact_stars": 5,
            "roi_priority": 11,
            "phase": "phase_2_enterprise_sales",
            "why_it_drives_growth": "Improves sales conversion by syncing social intent with CRM lifecycle automation.",
            "how_it_works": "HubSpot-driven webhook events create ideas/queue actions and are enforced in strict social mode.",
            "vendors": ["HubSpot CRM"],
            "required_env_keys": ["HUBSPOT_ACCESS_TOKEN"],
            "route_dependencies": [
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/integrations/webhooks",
                "/social/automation/rules",
                "/social/inbox/contact-views",
            ],
        },
        {
            "integration": "Salesforce",
            "integration_key": "salesforce",
            "category": "crm",
            "impact_stars": 5,
            "roi_priority": 10,
            "phase": "phase_2_enterprise_sales",
            "why_it_drives_growth": "Unlocks enterprise procurement and opportunity pipeline alignment.",
            "how_it_works": "Salesforce events and actions can be mapped through webhook bridges and social automation rules.",
            "vendors": ["Salesforce Platform", "Sales Cloud"],
            "required_env_keys": ["SALESFORCE_CLIENT_ID", "SALESFORCE_ACCESS_TOKEN"],
            "route_dependencies": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/rules",
                "/social/inbox/contact-views",
            ],
        },
        {
            "integration": "Okta",
            "integration_key": "okta",
            "category": "identity_sso",
            "impact_stars": 5,
            "roi_priority": 12,
            "phase": "phase_2_enterprise_sales",
            "why_it_drives_growth": "Enterprise SSO shortens procurement and security review cycles.",
            "how_it_works": "Okta identity config is enforced through OAuth connect and callback contracts.",
            "vendors": ["Okta OAuth/OIDC"],
            "required_env_keys": ["OKTA_CLIENT_ID"],
            "route_dependencies": [
                "/social/oauth/{network}/start",
                "/social/oauth/{network}/callback",
                "/social/oauth/connect-all",
            ],
        },
        {
            "integration": "Azure AD",
            "integration_key": "azure_ad",
            "category": "identity_sso",
            "impact_stars": 5,
            "roi_priority": 13,
            "phase": "phase_2_enterprise_sales",
            "why_it_drives_growth": "Enterprise identity governance and user provisioning support larger account rollouts.",
            "how_it_works": "Azure AD credentials support Microsoft identity onboarding for workspace authentication.",
            "vendors": ["Microsoft Entra ID (Azure AD)"],
            "required_env_keys": ["AZURE_AD_CLIENT_ID"],
            "route_dependencies": [
                "/social/oauth/{network}/start",
                "/social/oauth/{network}/callback",
                "/social/oauth/connect-all",
            ],
        },
        {
            "integration": "Outlook Calendar",
            "integration_key": "outlook_calendar",
            "category": "scheduling",
            "impact_stars": 4,
            "roi_priority": 14,
            "phase": "phase_2_enterprise_sales",
            "why_it_drives_growth": "Enables enterprise campaign planning in the calendar systems teams already use.",
            "how_it_works": "Calendar and posting schedule APIs provide move/replan controls for Outlook-driven workflows.",
            "vendors": ["Outlook Calendar API"],
            "required_env_keys": ["OUTLOOK_CLIENT_ID"],
            "route_dependencies": ["/social/calendar", "/social/calendar/{item_id}/move", "/social/posting-schedules"],
        },
        {
            "integration": "Google Calendar",
            "integration_key": "google_calendar",
            "category": "scheduling",
            "impact_stars": 4,
            "roi_priority": 15,
            "phase": "phase_2_enterprise_sales",
            "why_it_drives_growth": "Improves campaign consistency and scheduling adoption for content teams.",
            "how_it_works": "Calendar and posting schedule APIs provide move/replan controls for Google Calendar workflows.",
            "vendors": ["Google Calendar API"],
            "required_env_keys": ["GOOGLE_CALENDAR_CLIENT_ID"],
            "route_dependencies": ["/social/calendar", "/social/calendar/{item_id}/move", "/social/posting-schedules"],
        },
        {
            "integration": "Notion",
            "integration_key": "notion",
            "category": "knowledge_workflow",
            "impact_stars": 4,
            "roi_priority": 16,
            "phase": "phase_3_power_users_creators",
            "why_it_drives_growth": "Startup and content teams centralize planning where they already work.",
            "how_it_works": "Notion-triggered content events can be ingested via webhook bridge and transformed into queued social drafts.",
            "vendors": ["Notion API"],
            "required_env_keys": ["NOTION_API_KEY", "NOTION_WEBHOOK_SECRET"],
            "route_dependencies": [
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/ideas",
                "/social/ideas/{idea_id}/queue",
            ],
        },
        {
            "integration": "Discord",
            "integration_key": "discord",
            "category": "communication_community",
            "impact_stars": 4,
            "roi_priority": 17,
            "phase": "phase_3_power_users_creators",
            "why_it_drives_growth": "Community-native notifications and bots drive creator and AI-tool retention.",
            "how_it_works": "Discord OAuth/network support plus webhook automations enable community campaign fan-out.",
            "vendors": ["Discord API"],
            "required_env_keys": ["SOCIAL_OAUTH_DISCORD_CLIENT_ID", "DISCORD_BOT_TOKEN"],
            "route_dependencies": [
                "/social/oauth/{network}/start",
                "/social/integrations/webhooks",
                "/social/automation/rules",
            ],
        },
        {
            "integration": "GitHub",
            "integration_key": "github",
            "category": "developer_collaboration",
            "impact_stars": 4,
            "roi_priority": 18,
            "phase": "phase_3_power_users_creators",
            "why_it_drives_growth": "Brings engineering teams through release-driven social automation hooks.",
            "how_it_works": "GitHub release and issue events can post into webhook ingress and queue social actions.",
            "vendors": ["GitHub"],
            "required_env_keys": ["GITHUB_APP_ID", "WEBHOOK_GITHUB_SECRET"],
            "route_dependencies": [
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/rules",
                "/social/automation/feeds",
            ],
        },
        {
            "integration": "GitLab",
            "integration_key": "gitlab",
            "category": "developer_collaboration",
            "impact_stars": 4,
            "roi_priority": 19,
            "phase": "phase_3_power_users_creators",
            "why_it_drives_growth": "Supports developer-centric teams using GitLab-native release flows.",
            "how_it_works": "GitLab webhooks can trigger social idea creation and queue scheduling pipelines.",
            "vendors": ["GitLab"],
            "required_env_keys": ["GITLAB_CLIENT_ID"],
            "route_dependencies": [
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/rules",
                "/social/automation/feeds",
            ],
        },
        {
            "integration": "Trello / Asana / ClickUp",
            "integration_key": "project_management",
            "category": "project_management",
            "impact_stars": 4,
            "roi_priority": 20,
            "phase": "phase_3_power_users_creators",
            "why_it_drives_growth": "Embedding social execution into PM systems increases team stickiness and repeat usage.",
            "how_it_works": "Task-state webhooks route into social ideas, queues, and rule-based publishing flows.",
            "vendors": ["Trello API", "Asana API", "ClickUp API"],
            "required_env_keys": ["TRELLO_API_KEY", "ASANA_ACCESS_TOKEN", "CLICKUP_API_KEY"],
            "route_dependencies": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/rules",
                "/social/ideas/{idea_id}/queue",
            ],
        },
    ]


def operation__build_best_stack_rows(
    st: _SocialWorkspaceState, router: APIRouter, readiness: dict[str, Any]
) -> list[dict[str, Any]]:
    capability_matrix = cast(list[dict[str, Any]], readiness.get("capability_matrix") or [])
    vendor_registry = cast(
        list[dict[str, Any]], cast(dict[str, Any], readiness.get("vendors") or {}).get("registry") or []
    )
    capability_by_key = {str(item.get("capability_key") or ""): item for item in capability_matrix}
    vendor_by_key = {str(item.get("vendor_key") or ""): item for item in vendor_registry}
    scheduling = cast(dict[str, Any], capability_by_key.get("ai_scheduling") or {})
    repurpose = cast(dict[str, Any], capability_by_key.get("ai_repurposing") or {})
    content = cast(dict[str, Any], capability_by_key.get("ai_content_engines") or {})
    listening = cast(dict[str, Any], capability_by_key.get("ai_social_listening") or {})
    brandwatch_vendor = cast(dict[str, Any], vendor_by_key.get("brandwatch_meltwater") or {})
    openai_vendor = cast(dict[str, Any], vendor_by_key.get("openai") or {})
    canva_vendor = cast(dict[str, Any], vendor_by_key.get("canva") or {})
    return [
        {
            "stack_key": "sprout_ops",
            "label": "Sprout Social (ops)",
            "completion_percent": int(
                cast(dict[str, Any], readiness.get("capability_summary") or {}).get("average_completion_percent") or 0
            ),
            "status": "done" if bool(readiness.get("production_ready")) else "partial",
            "how_it_works": "Publishing, inbox, listening, analytics, and automation queue routes are scored for completion and vendor readiness.",
            "vendors": ["OAuth providers", "OpenAI", "optional shorteners", "optional Canva"],
        },
        {
            "stack_key": "lately_repurpose",
            "label": "Lately (AI repurposing)",
            "completion_percent": int(repurpose.get("completion_percent") or 0),
            "status": str(repurpose.get("status") or "missing"),
            "how_it_works": "Longform assets are transformed into social-ready variants through repurpose workflows and queue handoff.",
            "vendors": ["OpenAI"],
        },
        {
            "stack_key": "jasper_copy",
            "label": "Jasper (AI copy)",
            "completion_percent": int(content.get("completion_percent") or 0),
            "status": str(content.get("status") or "missing"),
            "how_it_works": "AI assistant and content engines generate/rewrite copy with platform and tone constraints.",
            "vendors": [
                "OpenAI configured" if bool(openai_vendor.get("configured")) else "OpenAI missing",
                "Canva configured" if bool(canva_vendor.get("configured")) else "Canva optional",
            ],
        },
        {
            "stack_key": "brandwatch_listening",
            "label": "Brandwatch (listening intelligence)",
            "completion_percent": int(listening.get("completion_percent") or 0),
            "status": str(listening.get("status") or "missing"),
            "how_it_works": "Listening keywords, mention ingestion, and sentiment APIs run natively with optional Brandwatch/Meltwater enrichment.",
            "vendors": [
                "Brandwatch/Meltwater configured"
                if bool(brandwatch_vendor.get("configured"))
                else "Brandwatch/Meltwater optional"
            ],
        },
        {
            "stack_key": "buffer_later_scheduling",
            "label": "Buffer/Later (visual scheduling)",
            "completion_percent": int(scheduling.get("completion_percent") or 0),
            "status": str(scheduling.get("status") or "missing"),
            "how_it_works": "Calendar, queue, posting schedules, and best-time routes coordinate visual planning and timed distribution.",
            "vendors": ["OAuth providers", "optional shorteners"],
        },
    ]


def operation_list_best_stack_reports(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:production-readiness:best-stack-report:list", 120, 60)
    with st.lock:
        items = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "generated_at": item.get("generated_at"),
                "export_url": item.get("export_url"),
            }
            for item in st.reports
            if item.get("tenant_id") == auth.tenant_id and item.get("report_type") == "best_stack_probe"
        ]
    items.sort(key=lambda item: str(item.get("generated_at") or ""), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "reports": items, "count": len(items)}
