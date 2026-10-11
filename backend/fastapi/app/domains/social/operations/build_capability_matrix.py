"""Social use cases: build capability matrix."""

from ....domains.social.persistence import _SocialWorkspaceState
from fastapi import APIRouter
from typing import Any


def operation__build_capability_matrix(
    st: _SocialWorkspaceState,
    router: APIRouter,
    available_paths: set[str],
    vendor_flags: dict[str, bool],
    oauth_mode: str,
    db_backing_enabled: bool,
) -> list[dict[str, Any]]:
    capability_specs: list[dict[str, Any]] = [
        {
            "capability": "AI content engines",
            "capability_key": "ai_content_engines",
            "automation_level_percent": 88,
            "how_it_works": "Brand profile, AI assistant, templates, and Canva imports produce ready-to-queue content assets.",
            "routes": [
                "/social/ai-assistant",
                "/social/templates",
                "/social/integrations/canva/import",
                "/social/ideas",
            ],
            "required_vendors": ["openai"],
            "optional_vendors": ["canva"],
        },
        {
            "capability": "AI scheduling",
            "capability_key": "ai_scheduling",
            "automation_level_percent": 90,
            "how_it_works": "Queue ordering, best-time scoring, posting schedules, and autopilot publish coordinate timing.",
            "routes": [
                "/social/queue",
                "/social/queue/reorder",
                "/social/best-time",
                "/social/posting-schedules",
                "/social/autopilot/publish",
            ],
            "required_vendors": ["oauth_providers"],
            "optional_vendors": ["shorteners"],
        },
        {
            "capability": "AI repurposing",
            "capability_key": "ai_repurposing",
            "automation_level_percent": 87,
            "how_it_works": "Longform sources are transformed into multi-variant social drafts and can be auto-queued.",
            "routes": ["/social/automation/repurpose", "/social/ideas", "/social/ideas/{idea_id}/queue"],
            "required_vendors": ["openai"],
            "optional_vendors": [],
        },
        {
            "capability": "AI video",
            "capability_key": "ai_video",
            "automation_level_percent": 82,
            "how_it_works": "Media assets are imported and routed into publishing workflows with caption/headline metadata.",
            "routes": ["/social/integrations/canva/import", "/social/automation/repurpose", "/social/templates"],
            "required_vendors": ["canva"],
            "optional_vendors": ["openai"],
        },
        {
            "capability": "AI analytics",
            "capability_key": "ai_analytics",
            "automation_level_percent": 86,
            "how_it_works": "Operational analytics, report generation, exports, and best-time insights are exposed via API.",
            "routes": [
                "/social/analytics/overview",
                "/social/reports",
                "/social/reports/{report_id}/export",
                "/social/ads/analytics",
            ],
            "required_vendors": ["oauth_providers"],
            "optional_vendors": ["meta_ads", "tiktok_ads"],
        },
        {
            "capability": "AI social listening",
            "capability_key": "ai_social_listening",
            "automation_level_percent": 84,
            "how_it_works": "Keyword streams, mention ingestion, and sentiment scoring drive listening dashboards and alerts.",
            "routes": [
                "/social/listening/keywords",
                "/social/listening/mentions",
                "/social/listening/sentiment",
                "/social/streams",
            ],
            "required_vendors": [],
            "optional_vendors": ["brandwatch_meltwater"],
        },
        {
            "capability": "AI agents",
            "capability_key": "ai_agents",
            "automation_level_percent": 89,
            "how_it_works": "Template-driven agent workflows execute posting, DM response, and comment-to-DM actions.",
            "routes": [
                "/social/ai-agents/templates",
                "/social/ai-agents/workflows/execute",
                "/social/inbox/agents/dm-chatbot/respond",
            ],
            "required_vendors": ["openai"],
            "optional_vendors": ["manychat"],
        },
        {
            "capability": "AI automation",
            "capability_key": "ai_automation",
            "automation_level_percent": 91,
            "how_it_works": "Webhook ingress, feed sync, rule execution, and queue controls orchestrate multi-step automations.",
            "routes": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/automation/feeds",
                "/social/automation/rules",
                "/social/automation/queue",
            ],
            "required_vendors": ["zapier", "make"],
            "optional_vendors": ["shorteners"],
        },
        {
            "capability": "AI competitor intelligence",
            "capability_key": "ai_competitor_intelligence",
            "automation_level_percent": 83,
            "how_it_works": "Competitor tracking endpoints persist observed entities and expose comparative insight snapshots.",
            "routes": ["/social/competitors/track", "/social/competitors/insights", "/social/listening/mentions"],
            "required_vendors": [],
            "optional_vendors": ["brandwatch_meltwater"],
        },
        {
            "capability": "AI brand monitoring",
            "capability_key": "ai_brand_monitoring",
            "automation_level_percent": 85,
            "how_it_works": "Brand-profile metadata, monitoring streams, and review/case flows monitor brand health in near real-time.",
            "routes": ["/social/brand-profile", "/social/streams", "/social/reviews", "/social/care/cases"],
            "required_vendors": [],
            "optional_vendors": ["brandwatch_meltwater"],
        },
        {
            "capability": "AI inbox automation",
            "capability_key": "ai_inbox_automation",
            "automation_level_percent": 92,
            "how_it_works": "Inbox triage, AI replies, saved replies, claim/complete flows, and bulk actions automate engagement.",
            "routes": [
                "/social/inbox",
                "/social/inbox/agents/dm-chatbot/respond",
                "/social/inbox/comment-to-dm",
                "/social/inbox/bulk-action",
                "/social/inbox/saved-replies",
            ],
            "required_vendors": ["openai"],
            "optional_vendors": ["manychat"],
        },
        {
            "capability": "AI ad optimization",
            "capability_key": "ai_ad_optimization",
            "automation_level_percent": 81,
            "how_it_works": "Ad campaign create/boost and analytics endpoints support optimization loops and reporting.",
            "routes": ["/social/ads/campaigns", "/social/ads/boost", "/social/ads/analytics", "/social/reports"],
            "required_vendors": ["meta_ads"],
            "optional_vendors": ["tiktok_ads", "shorteners"],
        },
        {
            "capability": "AI CRM-connected social",
            "capability_key": "ai_crm_connected_social",
            "automation_level_percent": 80,
            "how_it_works": "Incoming/outgoing webhooks, contact views, and automation rules bridge social events to CRM pipelines.",
            "routes": [
                "/social/integrations/webhooks",
                "/social/integrations/webhooks/incoming/{provider}",
                "/social/inbox/contact-views",
                "/social/automation/rules",
            ],
            "required_vendors": ["hubspot"],
            "optional_vendors": ["zapier", "make"],
        },
    ]
    matrix: list[dict[str, Any]] = []
    for spec in capability_specs:
        routes: list[str] = spec["routes"]
        route_hits = sum((1 for route in routes if route in available_paths))
        route_coverage = int(round(route_hits / len(routes) * 100)) if routes else 100
        required_vendors: list[str] = spec["required_vendors"]
        optional_vendors: list[str] = spec["optional_vendors"]
        required_missing = [key for key in required_vendors if not vendor_flags.get(key, False)]
        required_configured = [key for key in required_vendors if vendor_flags.get(key, False)]
        optional_configured = [key for key in optional_vendors if vendor_flags.get(key, False)]
        completion = route_coverage
        if required_missing:
            completion -= min(35, 15 * len(required_missing))
        if spec["capability_key"] in {"ai_scheduling", "ai_analytics"} and oauth_mode != "live":
            completion -= 10
        if not db_backing_enabled:
            completion -= 5
        completion = max(0, min(100, completion))
        status = "done"
        if completion < 100:
            status = "partial"
        if route_coverage < 100:
            status = "missing"
        matrix.append(
            {
                "capability": spec["capability"],
                "capability_key": spec["capability_key"],
                "status": status,
                "completion_percent": completion,
                "automation_level_percent": spec["automation_level_percent"],
                "how_it_works": spec["how_it_works"],
                "route_coverage_percent": route_coverage,
                "routes_required": routes,
                "routes_available": [route for route in routes if route in available_paths],
                "required_vendors": required_vendors,
                "optional_vendors": optional_vendors,
                "required_vendors_configured": required_configured,
                "optional_vendors_configured": optional_configured,
                "required_vendors_missing": required_missing,
                "fully_wired": completion == 100 and route_coverage == 100 and (not required_missing),
            }
        )
    return matrix
