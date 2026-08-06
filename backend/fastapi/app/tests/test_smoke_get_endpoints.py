"""
Smoke tests — every GET endpoint in the app.

Each test sends a GET with valid auth headers and asserts the response is
not a server crash (status < 500, with 503 allowed for readiness probes).
Path-param placeholders use IDs / slugs that will typically yield 404, which
is fine — we are testing that the handler runs without raising.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("SUPER_ADMIN_API_KEY", "selftest-super-admin-key")

HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
SA_HEADERS = {
    "X-API-Key": "selftest-super-admin-key",
    "X-Tenant-Id": "test-tenant",
    "X-Super-Admin-Key": "selftest-super-admin-key",
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# All GET routes — parametrized
# Uses placeholder IDs for path params; 404 is expected for non-existent items.
# ---------------------------------------------------------------------------

GET_ROUTES = [
    # Advocacy / Employee Advocacy
    "/advocacy/analytics",
    "/advocacy/campaigns",
    "/advocacy/content",
    "/advocacy/participants",
    # Agency
    "/agency/overview",
    # AI
    "/ai/generated-assets/1",
    "/ai/health",
    "/ai/ping",
    "/ai/security/admin/email-queue",
    "/ai/security/admin/ids/state",
    "/ai/security/analytics",
    "/ai/social-studio/job/1",
    # Analytics
    "/analytics/benchmarks",
    "/analytics/dashboard",
    "/analytics/export",
    "/analytics/insights/intelligence",
    "/analytics/insights/kpi",
    "/analytics/metrics",
    "/analytics/predictions",
    "/analytics/reports",
    "/analytics/revenue-attribution/report",
    "/analytics/revenue-attribution/touchpoints",
    # Benchmarks
    "/benchmarks",
    "/benchmarks/compare/enterprise",
    "/benchmarks/segments/enterprise",
    "/benchmarks/summary",
    # Billing
    "/billing/invoices",
    "/billing/plans",
    "/billing/usage",
    # Chatbot
    "/chatbot",
    "/chatbot/1/analytics",
    "/chatbot/1/conversations",
    "/chatbot/1/leads",
    # CMS
    "/cms/connections",
    "/cms/crawler-analytics",
    "/cms/pages",
    # Competitive
    "/competitive/profiles",
    "/competitive/report",
    "/competitive/share-of-voice",
    # Content Approval
    "/content/approval/config",
    "/content/approval/requests",
    "/content/approval/requests/1/comments",
    # CRM
    "/crm/activities",
    "/crm/api-tokens",
    "/crm/automation/recipes",
    "/crm/campaigns",
    "/crm/campaigns/1",
    "/crm/companies",
    "/crm/contacts",
    "/crm/contacts/1",
    "/crm/custom-entities/types",
    "/crm/custom-entities/test-entity/records",
    "/crm/deals",
    "/crm/email-sequences",
    "/crm/export",
    "/crm/invoices",
    "/crm/leads",
    "/crm/leads/1",
    "/crm/notes",
    "/crm/ops/backup",
    "/crm/ops/live-sync",
    "/crm/pipeline",
    "/crm/projects",
    "/crm/projects/board",
    "/crm/quotes",
    "/crm/reports/executive-analytics",
    "/crm/reports/forecast",
    "/crm/reports/kpis",
    "/crm/segments",
    "/crm/segments/1/members",
    "/crm/sla-rules",
    "/crm/summary",
    "/crm/tasks",
    "/crm/tasks/kanban",
    "/crm/tickets",
    "/crm/tickets/1",
    "/crm/webhooks",
    "/crm/workflow-rules",
    # Documents
    "/documents",
    "/documents/1",
    # Email campaigns
    "/email/campaigns",
    "/email/contacts",
    # Engagement
    "/engagement/achievements",
    "/engagement/achievements/leaderboard",
    "/engagement/achievements/timeline",
    "/engagement/ai-best-friend",
    "/engagement/ai-best-friend/history",
    "/engagement/autopilot-dependency/dashboard",
    "/engagement/autopilot-dependency/timeline",
    "/engagement/community",
    "/engagement/community/feed",
    "/engagement/dependency-creator",
    "/engagement/dependency-creator/timeline",
    "/engagement/earnings-ticker",
    "/engagement/fomo/feed",
    "/engagement/fomo/rules",
    "/engagement/personal-brand-lock-in",
    "/engagement/personal-brand-lock-in/timeline",
    "/engagement/referrals",
    "/engagement/referrals/leaderboard",
    "/engagement/social-proof/feed",
    "/engagement/social-proof/leaderboard",
    "/engagement/streak",
    "/engagement/streak/leaderboard",
    "/engagement/withdrawal-preview",
    # Health
    "/health",
    "/health/encryption",
    "/health/live",
    "/health/ready",
    "/health/schema/unified-31",
    "/health/vaults",
    "/healthz",
    # Inbox
    "/inbox/messages",
    "/inbox/messages/1",
    "/inbox/messages/1/notes",
    "/inbox/saved-replies",
    "/inbox/stats",
    # Influencer
    "/influencer/analytics",
    "/influencer/campaigns",
    "/influencer/profile/1",
    # Integrations
    "/integrations/tools",
    "/integrations/tools/dataforseo",
    # IRA
    "/ira/ab-tests",
    "/ira/agent/brain/capabilities",
    "/ira/agent/frameworks",
    "/ira/copilot/catalog",
    "/ira/copilot/env-template",
    "/ira/copilot/health",
    "/ira/costs",
    "/ira/crm/connectors/status",
    "/ira/crm/hybrid-recommendation",
    "/ira/disputes/dashboard",
    "/ira/finance/health",
    "/ira/frontier/env-template",
    "/ira/frontier/stack",
    "/ira/memory/overview",
    "/ira/memory/short-term",
    "/ira/memory/structured",
    "/ira/ml/overview",
    "/ira/monitor",
    "/ira/performance",
    "/ira/risk/score",
    "/ira/status",
    # Knowledge Base
    "/kb/analytics/summary",
    "/kb/articles",
    "/kb/articles/1",
    "/kb/categories",
    "/kb/search",
    # Linkinbio
    "/linkinbio/pages",
    "/linkinbio/pages/1/analytics",
    # Marketplace
    "/marketplace/plugins",
    "/marketplace/themes",
    # Media
    "/media/assets",
    "/media/assets/1",
    "/media/folders",
    "/media/jobs",
    "/media/jobs/dlq",
    "/media/jobs/1",
    "/media/stats",
    # Meetings
    "/meetings/analytics",
    "/meetings/bookings",
    "/meetings/links",
    "/meetings/links/test-slug",
    # Metrics
    "/metrics",
    # Money Printers
    "/money-printers/backlog",
    "/money-printers/commerce-pro/catalog",
    "/money-printers/commerce-pro/orders",
    "/money-printers/commerce-pro/overview",
    "/money-printers/commerce-pro/storefront",
    "/money-printers/nuxtron-bank/payout-preview",
    "/money-printers/nuxtron-bank/payouts",
    "/money-printers/nuxtron-bank/wallet",
    "/money-printers/nuxtron-studios/overview",
    "/money-printers/nuxtron-university/catalog",
    "/money-printers/nuxtron-university/overview",
    "/money-printers/portfolio",
    # Notifications
    "/notifications",
    "/notifications/delivery-health",
    "/notifications/delivery-receipts",
    "/notifications/digest",
    "/notifications/digest/batch-status",
    "/notifications/preferences",
    "/notifications/unread-count",
    # Ops
    "/ops/audit-log",
    "/ops/finance/accounting/integrations",
    "/ops/finance/hub",
    "/ops/platform/anti-failure-status",
    "/ops/platform/capabilities",
    "/ops/platform/growth-suite",
    "/ops/platform/hybrid-stacks",
    "/ops/platform/metrics-summary",
    "/ops/platform/module-registry",
    "/ops/platform/status",
    "/ops/platform/use-case-coverage",
    "/ops/security/api-usage",
    "/ops/siem/architecture",
    "/ops/siem/auto-pentest/jobs",
    "/ops/siem/cases",
    "/ops/siem/compliance",
    "/ops/siem/controls",
    "/ops/siem/data-collection",
    "/ops/siem/dead-code/findings",
    "/ops/siem/detection",
    "/ops/siem/endpoint-hardening/status",
    "/ops/siem/flows",
    "/ops/siem/investigation",
    "/ops/siem/network-anomalies",
    "/ops/siem/threat-hunting/advanced",
    "/ops/siem/updates",
    "/ops/siem/vault-encryption-health",
    "/ops/siem/vulnerabilities",
    # Outcome
    "/outcome/actions/pending",
    "/outcome/graph",
    "/outcome/quality",
    # Pentest
    "/pentest/defectdojo/config",
    "/pentest/defectdojo/queue",
    "/pentest/findings",
    "/pentest/findings/stats",
    "/pentest/findings/1",
    "/pentest/queue",
    "/pentest/risk-policy",
    # Playbooks
    "/playbooks",
    "/playbooks/runs/list",
    "/playbooks/1",
    # Products
    "/products",
    "/products/catalog/stats",
    "/products/categories",
    "/products/1",
    # Publishing / UTM
    "/publishing/optimal-times",
    "/publishing/optimal-times/defaults",
    "/publishing/utm/presets",
    # Quotes
    "/quotes",
    "/quotes/1",
    # Reviews
    "/reviews",
    "/reviews/summary",
    # SEO platform
    "/seo-platform/analyses",
    "/seo-platform/analyses/1",
    "/seo-platform/health",
    "/seo-platform/jobs/1",
    "/seo-platform/modules",
    "/seo-platform/modules/audit",
    "/seo-platform/modules/keyword_research",
    "/seo-platform/performance/history",
    "/seo-platform/schemas/types",
    # Sequences
    "/sequences",
    "/sequences/1",
    "/sequences/1/analytics",
    "/sequences/1/enrollments",
    # Social
    "/social/accounts",
    "/social/accounts/catalog",
    "/social/avatar/catalog",
    "/social/brand-profile",
    "/social/listening/alerts",
    "/social/listening/clusters",
    "/social/listening/mentions",
    "/social/listening/summary",
    "/social/oauth/providers",
    "/social/scheduled",
    "/social/voiceover/catalog",
    "/social/workspace/overview",
    # Surveys
    "/surveys",
    "/surveys/1",
    "/surveys/1/analytics",
    "/surveys/1/responses",
    # Talent Agency
    "/talent-agency/deals",
    "/talent-agency/overview",
    "/talent-agency/roster",
    # Tenants
    "/tenants",
    # Tickets (standalone)
    "/tickets",
    "/tickets/analytics/summary",
    "/tickets/1",
    # Trends
    "/trends/analytics/dashboard",
    "/trends/analytics/indicators",
    "/trends/forecast",
    "/trends/recommendations",
    "/trends/signals",
    # Trust Center
    "/trust-center/approval-chains",
    "/trust-center/incidents",
    "/trust-center/policies",
    "/trust-center/posture",
    # v1 loop
    "/v1/loop/agent-decision-trace/test-site",
    "/v1/loop/agent-decisions/test-site",
    "/v1/loop/rich-results/test-site",
    "/v1/loop/status/nonexistent-run-id",
    "/v1/loop/strategy-snapshots/test-site",
    # VSE
    "/vse/algorithm/models",
    "/vse/algorithm/updates",
    "/vse/brief",
    "/vse/command-centre",
    "/vse/dark-social/measurement",
    "/vse/detonation",
    "/vse/detonation/history",
    "/vse/emotion/audience-state",
    "/vse/engines",
    "/vse/immortalise/vault",
    "/vse/immortalise/1/assets",
    "/vse/momentum/1",
    "/vse/network/superconnectors",
    "/vse/paid/events",
    "/vse/subsystems",
    "/vse/swarm/database/stats",
    "/vse/swarm/1/status",
    "/vse/trends/alerts",
    "/vse/trends/live",
    "/vse/triggers/library",
    # Webhooks
    "/webhooks/events",
    # White label
    "/white-label/profile",
    "/white-label/timeline",
    # Workflows
    "/workflows",
    "/workflows/1",
    "/workflows/1/analytics",
    "/workflows/1/executions",
    # Super admin (requires super-admin key, may return 403 with normal key)
    "/ops/platform/super-admin/audit-log",
    "/ops/platform/super-admin/dashboard",
    "/ops/platform/super-admin/module-settings",
    "/ops/platform/super-admin/accounting/exports",
    "/ops/platform/super-admin/accounting/integrations",
]


@pytest.mark.parametrize("path", GET_ROUTES)
def test_get_not_server_error(client: TestClient, path: str) -> None:
    """GET endpoint returns a non-crash response (< 500, 503 allowed for probes)."""
    r = client.get(path, headers=HEADERS)
    assert r.status_code < 500 or r.status_code == 503, (
        f"GET {path} returned unexpected {r.status_code}: {r.text[:200]}"
    )
