"""Coverage tests for chatbot.py and cms_integration.py happy paths."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "chatbot-cms-coverage-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestChatbotCoverage:
    """Cover create, list, train, deploy, message, conversations, analytics, leads."""

    def test_create_and_list(self, client: TestClient) -> None:
        # Create a chatbot
        r = client.post(
            "/chatbot",
            headers=H,
            json={
                "name": "Support Bot Coverage",
                "channels": ["website", "slack"],
                "knowledge_base": ["doc1.txt", "doc2.txt"],
                "system_prompt": "You are a friendly support assistant.",
                "language": "en",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["chatbot"]["name"] == "Support Bot Coverage"
        assert data["chatbot"]["trained"] is False

        # List chatbots
        r2 = client.get("/chatbot", headers=H)
        assert r2.status_code == 200
        assert r2.json()["count"] >= 1

    def test_train_chatbot(self, client: TestClient) -> None:
        # Create first
        r = client.post(
            "/chatbot",
            headers=H,
            json={
                "name": "Training Bot",
                "channels": ["website"],
                "knowledge_base": [],
                "system_prompt": "Train me.",
                "language": "en",
            },
        )
        assert r.status_code in (200, 201)
        bot_id = r.json()["chatbot"]["id"]

        # Train it
        r2 = client.post(
            f"/chatbot/{bot_id}/train",
            headers=H,
            json={"documents": ["faq.txt", "terms.txt", "guide.txt"], "source_type": "text"},
        )
        assert r2.status_code in (200, 201)
        data = r2.json()
        assert data["chatbot"]["trained"] is True
        assert data["documents_processed"] == 3

    def test_train_missing_chatbot(self, client: TestClient) -> None:
        r = client.post(
            "/chatbot/9999/train",
            headers=H,
            json={"documents": ["doc.txt"], "source_type": "text"},
        )
        assert r.status_code == 404

    def test_deploy_chatbot(self, client: TestClient) -> None:
        # Create and train first
        r = client.post(
            "/chatbot",
            headers=H,
            json={"name": "Deploy Bot", "channels": ["website"], "knowledge_base": [], "language": "en"},
        )
        assert r.status_code in (200, 201)
        bot_id = r.json()["chatbot"]["id"]

        # Train
        client.post(
            f"/chatbot/{bot_id}/train",
            headers=H,
            json={"documents": ["help.txt"], "source_type": "text"},
        )

        # Deploy
        r2 = client.post(
            f"/chatbot/{bot_id}/deploy",
            headers=H,
            json={"channel": "website", "custom_domain": "support.mycompany.com"},
        )
        assert r2.status_code in (200, 201)
        data = r2.json()
        assert data["chatbot"]["deployed"] is True
        assert "embed_snippet" in data

    def test_deploy_untrained_chatbot(self, client: TestClient) -> None:
        r = client.post(
            "/chatbot",
            headers=H,
            json={"name": "Untrained Bot", "channels": ["website"], "knowledge_base": [], "language": "en"},
        )
        assert r.status_code in (200, 201)
        bot_id = r.json()["chatbot"]["id"]

        r2 = client.post(
            f"/chatbot/{bot_id}/deploy",
            headers=H,
            json={"channel": "website"},
        )
        assert r2.status_code == 422

    def test_deploy_missing_chatbot(self, client: TestClient) -> None:
        r = client.post("/chatbot/9999/deploy", headers=H, json={"channel": "website"})
        assert r.status_code == 404

    def test_message_and_conversations(self, client: TestClient) -> None:
        # Create, train, deploy a bot
        r = client.post(
            "/chatbot",
            headers=H,
            json={"name": "Message Bot", "channels": ["website"], "knowledge_base": ["kb.txt"], "language": "en"},
        )
        assert r.status_code in (200, 201)
        bot_id = r.json()["chatbot"]["id"]
        client.post(f"/chatbot/{bot_id}/train", headers=H, json={"documents": ["kb.txt"], "source_type": "text"})

        # Send message
        r2 = client.post(
            f"/chatbot/{bot_id}/message",
            headers=H,
            json={"message": "What are your hours?", "session_id": "sess-001", "channel": "website"},
        )
        assert r2.status_code in (200, 201)
        data = r2.json()
        assert "reply" in data
        assert data["session_id"] == "sess-001"

        # Send another message without session_id to cover auto-generate
        r3 = client.post(
            f"/chatbot/{bot_id}/message",
            headers=H,
            json={"message": "Tell me more", "session_id": "", "channel": "website"},
        )
        assert r3.status_code in (200, 201)

        # List conversations
        r4 = client.get(f"/chatbot/{bot_id}/conversations", headers=H)
        assert r4.status_code == 200
        assert r4.json()["count"] >= 2

    def test_message_missing_chatbot(self, client: TestClient) -> None:
        r = client.post(
            "/chatbot/9999/message",
            headers=H,
            json={"message": "Hello", "session_id": "sess-x", "channel": "website"},
        )
        assert r.status_code == 404

    def test_conversations_missing_chatbot(self, client: TestClient) -> None:
        r = client.get("/chatbot/9999/conversations", headers=H)
        assert r.status_code == 404

    def test_analytics_and_leads(self, client: TestClient) -> None:
        # Create bot
        r = client.post(
            "/chatbot",
            headers=H,
            json={"name": "Analytics Bot", "channels": ["website"], "knowledge_base": [], "language": "en"},
        )
        assert r.status_code in (200, 201)
        bot_id = r.json()["chatbot"]["id"]

        # Analytics
        r2 = client.get(f"/chatbot/{bot_id}/analytics", headers=H)
        assert r2.status_code == 200
        data = r2.json()
        assert "analytics" in data

        # Leads
        r3 = client.get(f"/chatbot/{bot_id}/leads", headers=H)
        assert r3.status_code == 200
        assert "leads" in r3.json()

    def test_analytics_missing_chatbot(self, client: TestClient) -> None:
        r = client.get("/chatbot/9999/analytics", headers=H)
        assert r.status_code == 404


class TestCmsIntegrationCoverage:
    """Cover add_connection, list, publish, sync, list_pages, schema_inject, crawler_analytics."""

    def test_add_connection_unsupported_cms(self, client: TestClient) -> None:
        r = client.post(
            "/cms/connections",
            headers=H,
            json={
                "cms_type": "totally_unsupported_cms",
                "display_name": "My Blog",
            },
        )
        assert r.status_code == 422

    def test_add_connection_and_list(self, client: TestClient) -> None:
        r = client.post(
            "/cms/connections",
            headers=H,
            json={
                "cms_type": "wordpress",
                "display_name": "My WordPress",
                "api_url": "https://myblog.com/wp-json",
                "api_key": "sk-wp-test-12345",
                "site_id": "site_001",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        conn = data["connection"]
        assert conn["cms_type"] == "wordpress"
        assert conn["api_key_configured"] is True

        # List connections
        r2 = client.get("/cms/connections", headers=H)
        assert r2.status_code == 200
        assert r2.json()["count"] >= 1

        vendors_scoped = client.get(f"/cms/vendors?connection_id={conn['id']}", headers=H)
        assert vendors_scoped.status_code == 200, vendors_scoped.text
        scoped_payload = vendors_scoped.json()
        assert scoped_payload["status"] == "ok"
        assert scoped_payload["connection_id"] == conn["id"]
        assert isinstance(scoped_payload["vendors"], list)
        assert isinstance(scoped_payload.get("vendor_chart"), list)
        assert scoped_payload.get("summary", {}).get("connections") == 1

    def test_cms_vendors_chart_across_connections(self, client: TestClient) -> None:
        first = client.post(
            "/cms/connections",
            headers=H,
            json={"cms_type": "webflow", "display_name": "WF CMS", "api_key": "wf-key"},
        )
        assert first.status_code in (200, 201), first.text

        second = client.post(
            "/cms/connections",
            headers=H,
            json={"cms_type": "shopify", "display_name": "Shop CMS", "api_key": "shop-key"},
        )
        assert second.status_code in (200, 201), second.text

        vendors = client.get("/cms/vendors", headers=H)
        assert vendors.status_code == 200, vendors.text
        payload = vendors.json()
        assert payload["status"] == "ok"
        assert isinstance(payload.get("connections"), list)
        assert isinstance(payload.get("vendor_chart"), list)
        assert payload.get("summary", {}).get("connections", 0) >= 2
        assert any(v.get("vendor") == "crm_bridge" for v in payload.get("vendor_chart", []))
        assert any(v.get("connections_using", 0) >= 2 for v in payload.get("vendor_chart", []))

    def test_publish_content(self, client: TestClient) -> None:
        # First create connection
        r = client.post(
            "/cms/connections",
            headers=H,
            json={"cms_type": "contentful", "display_name": "Contentful CMS", "api_key": "cf-key-123"},
        )
        assert r.status_code in (200, 201)
        conn_id = r.json()["connection"]["id"]

        # Publish content
        r2 = client.post(
            "/cms/publish",
            headers=H,
            json={
                "connection_id": conn_id,
                "title": "My First Post",
                "content": "This is the full content of the post. " * 5,
                "slug": "my-first-post",
                "tags": ["tech", "ai"],
                "inject_schema": True,
                "status": "publish",
            },
        )
        assert r2.status_code in (200, 201)
        data = r2.json()
        assert data["page"]["title"] == "My First Post"
        assert data["page"]["schema_injected"] is True

    def test_publish_auto_slug(self, client: TestClient) -> None:
        # Create connection
        r = client.post(
            "/cms/connections",
            headers=H,
            json={"cms_type": "ghost", "display_name": "Ghost Blog", "api_key": "gh-key"},
        )
        conn_id = r.json()["connection"]["id"]

        # Publish without slug to trigger auto-slug generation
        r2 = client.post(
            "/cms/publish",
            headers=H,
            json={
                "connection_id": conn_id,
                "title": "Auto Slug Title Post",
                "content": "Content here for the auto slug post test case.",
                "slug": "",
                "tags": [],
                "status": "draft",
            },
        )
        assert r2.status_code in (200, 201)
        assert "auto" in r2.json()["page"]["slug"] or len(r2.json()["page"]["slug"]) > 0

    def test_publish_missing_connection(self, client: TestClient) -> None:
        r = client.post(
            "/cms/publish",
            headers=H,
            json={
                "connection_id": 9999,
                "title": "Missing Post",
                "content": "This should fail because connection 9999 does not exist.",
            },
        )
        assert r.status_code == 404

    def test_sync_content(self, client: TestClient) -> None:
        # Create connection
        r = client.post(
            "/cms/connections",
            headers=H,
            json={"cms_type": "strapi", "display_name": "Strapi CMS", "api_key": "strapi-key"},
        )
        conn_id = r.json()["connection"]["id"]

        # Sync
        r2 = client.post(
            "/cms/sync",
            headers=H,
            json={"connection_id": conn_id, "direction": "push"},
        )
        assert r2.status_code in (200, 201)
        data = r2.json()
        assert data["sync"]["direction"] == "push"
        assert data["sync"]["status"] == "queued"

    def test_sync_missing_connection(self, client: TestClient) -> None:
        r = client.post("/cms/sync", headers=H, json={"connection_id": 9999, "direction": "pull"})
        assert r.status_code == 404

    def test_list_pages(self, client: TestClient) -> None:
        r = client.get("/cms/pages", headers=H)
        assert r.status_code == 200
        assert "pages" in r.json()

    def test_schema_inject(self, client: TestClient) -> None:
        # Create connection
        r = client.post(
            "/cms/connections",
            headers=H,
            json={"cms_type": "webflow", "display_name": "Webflow Site", "api_key": "wf-key"},
        )
        conn_id = r.json()["connection"]["id"]

        r2 = client.post(
            "/cms/schema-inject",
            headers=H,
            json={"connection_id": conn_id, "page_id": "page-abc-123", "schema_type": "Article"},
        )
        assert r2.status_code in (200, 201)
        data = r2.json()
        assert data["schema_type"] == "Article"
        assert "@context" in data["schema_preview"]

    def test_schema_inject_missing_connection(self, client: TestClient) -> None:
        r = client.post(
            "/cms/schema-inject",
            headers=H,
            json={"connection_id": 9999, "page_id": "page-xyz", "schema_type": "BlogPosting"},
        )
        assert r.status_code == 404

    def test_crawler_analytics(self, client: TestClient) -> None:
        r = client.get("/cms/crawler-analytics", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "analytics" in data
        assert "total_connections" in data["analytics"]

    def test_attribution_links_events_and_report(self, client: TestClient) -> None:
        conn = client.post(
            "/cms/connections",
            headers=H,
            json={
                "cms_type": "wordpress",
                "display_name": "Attribution CMS",
                "api_url": "https://content.example.com/wp-json",
                "api_key": "cms-key-attr-1",
            },
        )
        assert conn.status_code in (200, 201), conn.text
        conn_id = conn.json()["connection"]["id"]

        page = client.post(
            "/cms/publish",
            headers=H,
            json={
                "connection_id": conn_id,
                "title": "Summer Campaign Landing",
                "content": "Long campaign landing content " * 10,
                "slug": "summer-campaign",
                "tags": ["campaign", "summer"],
                "inject_schema": True,
                "status": "publish",
            },
        )
        assert page.status_code in (200, 201), page.text
        page_id = page.json()["page"]["id"]

        link = client.post(
            "/cms/attribution/links",
            headers=H,
            json={
                "connection_id": conn_id,
                "page_id": page_id,
                "campaign": "Summer 2026",
                "source": "google",
                "medium": "cpc",
                "term": "ai crm",
                "content": "hero-a",
                "landing_page_slug": "summer-funnel",
                "form_template_name": "Demo Request Form",
            },
        )
        assert link.status_code == 200, link.text
        link_payload = link.json()["attribution_link"]
        link_id = link_payload["id"]
        assert link_payload["campaign"] == "Summer 2026"
        assert link_payload["page_id"] == page_id

        list_links = client.get("/cms/attribution/links", headers=H)
        assert list_links.status_code == 200, list_links.text
        assert any(l.get("id") == link_id for l in list_links.json()["links"])

        visit = client.post(
            "/cms/attribution/events",
            headers=H,
            json={
                "attribution_link_id": link_id,
                "event_type": "visit",
                "visitor_id": "v-001",
            },
        )
        assert visit.status_code == 200, visit.text

        lead = client.post(
            "/cms/attribution/events",
            headers=H,
            json={
                "attribution_link_id": link_id,
                "event_type": "lead",
                "contact_email": "lead@example.com",
                "contact_first_name": "Lead",
                "contact_last_name": "Person",
                "company": "Acme Attribution",
                "value": 1200.0,
            },
        )
        assert lead.status_code == 200, lead.text
        lead_bridge = lead.json().get("crm_bridge", {})
        assert lead_bridge.get("synced") is True
        assert int(lead_bridge.get("contact_id") or 0) >= 1
        assert int(lead_bridge.get("activity_id") or 0) >= 1

        customer = client.post(
            "/cms/attribution/events",
            headers=H,
            json={
                "attribution_link_id": link_id,
                "event_type": "customer",
                "contact_email": "buyer@example.com",
                "value": 4500.0,
                "create_deal": True,
                "deal_title": "Summer 2026 Attributed Customer",
                "deal_stage": "closed_won",
            },
        )
        assert customer.status_code == 200, customer.text
        customer_bridge = customer.json().get("crm_bridge", {})
        assert customer_bridge.get("synced") is True
        assert customer_bridge.get("deal_created") is True
        assert int(customer_bridge.get("deal_id") or 0) >= 1

        crm_contact = client.get("/crm/contacts?q=buyer@example.com", headers=H)
        assert crm_contact.status_code == 200, crm_contact.text
        assert crm_contact.json().get("total", 0) >= 1

        crm_deal = client.get("/crm/deals?q=Summer 2026 Attributed Customer", headers=H)
        assert crm_deal.status_code == 200, crm_deal.text
        assert crm_deal.json().get("total", 0) >= 1

        report = client.get("/cms/attribution/report", headers=H)
        assert report.status_code == 200, report.text
        report_payload = report.json()
        assert report_payload["summary"]["campaigns"] >= 1
        assert report_payload["summary"]["events"] >= 3
        assert report_payload["summary"]["revenue"] >= 4500.0
        campaign = next((c for c in report_payload["campaigns"] if c.get("campaign") == "Summer 2026"), None)
        assert campaign is not None
        assert campaign.get("visits", 0) >= 1
        assert campaign.get("leads", 0) >= 2
        assert campaign.get("customers", 0) >= 1

    def test_attribution_automation_rule_sequence_enrollment(self, client: TestClient) -> None:
        seq = client.post(
            "/crm/email-sequences",
            headers=H,
            json={
                "name": "CMS Attribution SQL Sequence",
                "description": "Auto-enroll SQL contacts",
                "steps": [{"day_offset": 0, "subject": "Thanks", "body": "We received your request"}],
            },
        )
        assert seq.status_code in (200, 201), seq.text
        seq_id = seq.json()["sequence"]["id"]

        conn = client.post(
            "/cms/connections",
            headers=H,
            json={
                "cms_type": "webflow",
                "display_name": "Automation CMS",
                "api_url": "https://automation.example.com/api",
                "api_key": "cms-automation-key",
            },
        )
        assert conn.status_code in (200, 201), conn.text
        conn_id = conn.json()["connection"]["id"]

        link = client.post(
            "/cms/attribution/links",
            headers=H,
            json={
                "connection_id": conn_id,
                "campaign": "Automation Campaign",
                "source": "linkedin",
                "medium": "paid",
            },
        )
        assert link.status_code == 200, link.text
        link_id = link.json()["attribution_link"]["id"]

        rule = client.post(
            "/cms/attribution/automation-rules",
            headers=H,
            json={
                "campaign": "Automation Campaign",
                "trigger_event_type": "sql",
                "min_value": 1000,
                "auto_enroll_sequence_id": seq_id,
                "create_deal": True,
                "transition_deal_stage_to": "negotiation",
                "create_followup_task": True,
                "task_title": "Call SQL lead within 24h",
                "task_priority": "high",
                "task_assigned_to": "sales.rep@example.com",
                "task_due_in_days": 1,
                "enabled": True,
            },
        )
        assert rule.status_code == 200, rule.text
        rule_id = rule.json()["rule"]["id"]

        list_rules = client.get("/cms/attribution/automation-rules", headers=H)
        assert list_rules.status_code == 200, list_rules.text
        assert any(r.get("id") == rule_id for r in list_rules.json()["rules"])

        fired = client.post(
            "/cms/attribution/events",
            headers=H,
            json={
                "attribution_link_id": link_id,
                "event_type": "sql",
                "contact_email": "sql.campaign@example.com",
                "contact_first_name": "Sql",
                "contact_last_name": "Campaign",
                "value": 1500,
                "sync_to_crm": True,
            },
        )
        assert fired.status_code == 200, fired.text
        fired_payload = fired.json()
        assert fired_payload["automation"]["matched_rules"] >= 1
        executions = fired_payload["automation"]["executions"]
        assert len(executions) >= 1
        assert any(
            any(a.get("action") == "sequence_enroll" and a.get("success") is True for a in e.get("actions", []))
            for e in executions
        )
        assert any(
            any(a.get("action") == "transition_deal_stage" and a.get("success") is True and a.get("stage") == "negotiation" for a in e.get("actions", []))
            for e in executions
        )
        assert any(
            any(a.get("action") == "create_task" and a.get("success") is True and a.get("priority") == "high" for a in e.get("actions", []))
            for e in executions
        )

        bridge = fired_payload.get("crm_bridge", {})
        contact_id = int(bridge.get("contact_id", 0))
        assert contact_id > 0

        deals = client.get("/crm/deals?q=CMS Attribution Rule Opportunity", headers=H)
        assert deals.status_code == 200, deals.text
        deal_items = deals.json().get("deals", [])
        assert any(d.get("stage") == "negotiation" for d in deal_items)

        sequence_list = client.get("/crm/email-sequences", headers=H)
        assert sequence_list.status_code == 200, sequence_list.text
        matched = next((s for s in sequence_list.json()["sequences"] if s.get("id") == seq_id), None)
        assert matched is not None
        assert int(matched.get("enrollments", 0)) >= 1

        tasks = client.get(f"/crm/tasks?contact_id={contact_id}", headers=H)
        assert tasks.status_code == 200, tasks.text
        assert tasks.json().get("total", 0) >= 1
        assert any(
            t.get("title") == "Call SQL lead within 24h" and t.get("priority") == "high" and t.get("assigned_to") == "sales.rep@example.com"
            for t in tasks.json().get("tasks", [])
        )

        runs = client.get("/cms/attribution/automation-runs", headers=H)
        assert runs.status_code == 200, runs.text
        assert runs.json()["count"] >= 1

        deleted = client.delete(f"/cms/attribution/automation-rules/{rule_id}", headers=H)
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["removed"] is True
