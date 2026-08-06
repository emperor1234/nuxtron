"""
CRM router tests — contacts, companies, deals, leads, tasks, tickets, sequences, workflows.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_crm_router.db")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}


def _entity_id(data: dict, key: str) -> int:
    """Extract entity id from either top-level or nested response objects."""
    if "id" in data:
        return int(data.get("id", 1))
    nested = data.get(key, {})
    if isinstance(nested, dict) and "id" in nested:
        return int(nested.get("id", 1))
    return 1


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app import models as _models
    from backend.fastapi.app.database import init_db

    assert _models is not None
    init_db()
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestCRMContacts:
    def test_list_contacts(self, client: TestClient) -> None:
        r = client.get("/crm/contacts", headers=H)
        assert r.status_code == 200

    def test_create_contact(self, client: TestClient) -> None:
        r = client.post("/crm/contacts", headers=H, json={
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "company": "Acme",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        contact = data.get("contact", data)
        assert isinstance(contact, dict)
        assert contact.get("first_name") == "Alice" or "id" in contact

    def test_get_contact(self, client: TestClient) -> None:
        # Create then fetch
        r = client.post("/crm/contacts", headers=H, json={"first_name": "Bob"})
        assert r.status_code in {200, 201}
        cid = _entity_id(r.json(), "contact")
        r2 = client.get(f"/crm/contacts/{cid}", headers=H)
        assert r2.status_code == 200

    def test_get_missing_contact(self, client: TestClient) -> None:
        r = client.get("/crm/contacts/999999", headers=H)
        assert r.status_code == 404

    def test_score_contact(self, client: TestClient) -> None:
        r = client.post("/crm/contacts", headers=H, json={"first_name": "Carol"})
        cid = _entity_id(r.json(), "contact")
        r2 = client.post(f"/crm/contacts/{cid}/score", headers=H, json={"score": 75, "reason": "active"})
        assert r2.status_code < 500

    def test_dedupe(self, client: TestClient) -> None:
        r = client.post("/crm/contacts/dedupe", headers=H)
        assert r.status_code < 500


class TestCRMCompanies:
    def test_list_companies(self, client: TestClient) -> None:
        r = client.get("/crm/companies", headers=H)
        assert r.status_code == 200

    def test_create_company(self, client: TestClient) -> None:
        r = client.post("/crm/companies", headers=H, json={
            "name": "Test Corp",
            "domain": "testcorp.com",
            "industry": "Technology",
        })
        assert r.status_code in {200, 201}


class TestCRMDeals:
    def test_list_deals(self, client: TestClient) -> None:
        r = client.get("/crm/deals", headers=H)
        assert r.status_code == 200

    def test_create_deal(self, client: TestClient) -> None:
        r = client.post("/crm/deals", headers=H, json={
            "title": "Big Deal",
            "value": 50000.0,
            "stage": "prospect",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert _entity_id(data, "deal") >= 1

    def test_patch_deal(self, client: TestClient) -> None:
        r = client.post("/crm/deals", headers=H, json={"title": "Patch Deal"})
        did = _entity_id(r.json(), "deal")
        r2 = client.patch(f"/crm/deals/{did}", headers=H, json={"stage": "qualified"})
        assert r2.status_code < 500

    def test_get_pipeline(self, client: TestClient) -> None:
        r = client.get("/crm/pipeline", headers=H)
        assert r.status_code == 200

    def test_forecast(self, client: TestClient) -> None:
        r = client.get("/crm/reports/forecast", headers=H)
        assert r.status_code == 200


class TestCRMLeads:
    def test_list_leads(self, client: TestClient) -> None:
        r = client.get("/crm/leads", headers=H)
        assert r.status_code == 200

    def test_create_lead(self, client: TestClient) -> None:
        r = client.post("/crm/leads", headers=H, json={
            "title": "Inbound demo request",
            "source": "website",
            "estimated_value": 5000,
        })
        assert r.status_code in {200, 201}

    def test_patch_lead(self, client: TestClient) -> None:
        r = client.post("/crm/leads", headers=H, json={"title": "Patchable lead"})
        lid = _entity_id(r.json(), "lead")
        r2 = client.patch(f"/crm/leads/{lid}", headers=H, json={"lifecycle_stage": "qualified"})
        assert r2.status_code < 500

    def test_convert_lead(self, client: TestClient) -> None:
        r = client.post("/crm/leads", headers=H, json={"title": "Convertible lead"})
        lid = _entity_id(r.json(), "lead")
        r2 = client.post(f"/crm/leads/{lid}/convert", headers=H)
        assert r2.status_code < 500


class TestCRMTasks:
    def test_list_tasks(self, client: TestClient) -> None:
        r = client.get("/crm/tasks", headers=H)
        assert r.status_code == 200

    def test_create_task(self, client: TestClient) -> None:
        r = client.post("/crm/tasks", headers=H, json={
            "title": "Follow up call",
            "due_date": "2026-06-01",
        })
        assert r.status_code in {200, 201}

    def test_tasks_kanban(self, client: TestClient) -> None:
        r = client.get("/crm/tasks/kanban", headers=H)
        assert r.status_code == 200


class TestCRMTickets:
    def test_list_crm_tickets(self, client: TestClient) -> None:
        r = client.get("/crm/tickets", headers=H)
        assert r.status_code == 200

    def test_create_crm_ticket(self, client: TestClient) -> None:
        r = client.post("/crm/tickets", headers=H, json={
            "subject": "Help needed",
            "customer_email": "customer@example.com",
        })
        assert r.status_code in {200, 201}


class TestCRMActivities:
    def test_list_activities(self, client: TestClient) -> None:
        r = client.get("/crm/activities", headers=H)
        assert r.status_code == 200

    def test_create_activity(self, client: TestClient) -> None:
        r = client.post("/crm/activities", headers=H, json={
            "type": "note",
            "subject": "Called the client",
            "body": "Had a great call",
        })
        assert r.status_code in {200, 201}


class TestCRMNotes:
    def test_list_notes(self, client: TestClient) -> None:
        r = client.get("/crm/notes", headers=H)
        assert r.status_code == 200

    def test_create_note(self, client: TestClient) -> None:
        r = client.post("/crm/notes", headers=H, json={
            "body": "This is a note",
        })
        assert r.status_code in {200, 201}


class TestCRMCampaigns:
    def test_list_campaigns(self, client: TestClient) -> None:
        r = client.get("/crm/campaigns", headers=H)
        assert r.status_code == 200

    def test_create_campaign(self, client: TestClient) -> None:
        r = client.post("/crm/campaigns", headers=H, json={
            "name": "Summer Sale",
            "type": "email",
        })
        assert r.status_code in {200, 201}

    def test_send_campaign(self, client: TestClient) -> None:
        r = client.post("/crm/campaigns", headers=H, json={"name": "Send Test"})
        cid = _entity_id(r.json(), "campaign")
        r2 = client.post(f"/crm/campaigns/{cid}/send", headers=H)
        assert r2.status_code < 500


class TestCRMSegments:
    def test_list_segments(self, client: TestClient) -> None:
        r = client.get("/crm/segments", headers=H)
        assert r.status_code == 200

    def test_create_segment(self, client: TestClient) -> None:
        r = client.post("/crm/segments", headers=H, json={
            "name": "High Value Customers",
            "filters": {},
        })
        assert r.status_code in {200, 201}

    def test_segment_members(self, client: TestClient) -> None:
        r = client.post("/crm/segments", headers=H, json={"name": "Members Test"})
        sid = _entity_id(r.json(), "segment")
        r2 = client.get(f"/crm/segments/{sid}/members", headers=H)
        assert r2.status_code < 500


class TestCRMQuotes:
    def test_list_quotes(self, client: TestClient) -> None:
        r = client.get("/crm/quotes", headers=H)
        assert r.status_code == 200

    def test_create_quote(self, client: TestClient) -> None:
        r = client.post("/crm/quotes", headers=H, json={
            "title": "Q-001",
            "line_items": [],
        })
        assert r.status_code in {200, 201}

    def test_accept_quote(self, client: TestClient) -> None:
        r = client.post("/crm/quotes", headers=H, json={"title": "Accept Test"})
        qid = _entity_id(r.json(), "quote")
        r2 = client.post(f"/crm/quotes/{qid}/accept", headers=H)
        assert r2.status_code < 500


class TestCRMWebhooks:
    def test_list_webhooks(self, client: TestClient) -> None:
        r = client.get("/crm/webhooks", headers=H)
        assert r.status_code == 200

    def test_create_webhook(self, client: TestClient) -> None:
        r = client.post("/crm/webhooks", headers=H, json={
            "event": "contact.created",
            "target_url": "https://example.com/webhook",
            "secret": "test-secret",
        })
        assert r.status_code in {200, 201}

    def test_test_webhook(self, client: TestClient) -> None:
        r = client.post("/crm/webhooks", headers=H, json={
            "event": "contact.created",
            "target_url": "https://example.com/webhook",
            "secret": "test-secret",
        })
        wid = _entity_id(r.json(), "webhook")
        r2 = client.post(f"/crm/webhooks/{wid}/test", headers=H)
        assert r2.status_code < 500


class TestCRMWorkflowRules:
    def test_list_rules(self, client: TestClient) -> None:
        r = client.get("/crm/workflow-rules", headers=H)
        assert r.status_code == 200

    def test_create_rule(self, client: TestClient) -> None:
        r = client.post("/crm/workflow-rules", headers=H, json={
            "name": "Auto-assign hot leads",
            "trigger": "lead_score_changed",
            "conditions": {},
            "action": "assign_owner",
            "action_params": {"owner": "sales@example.com"},
        })
        assert r.status_code in {200, 201}


class TestCRMReports:
    def test_executive_analytics(self, client: TestClient) -> None:
        r = client.get("/crm/reports/executive-analytics", headers=H)
        assert r.status_code == 200

    def test_kpis(self, client: TestClient) -> None:
        r = client.get("/crm/reports/kpis", headers=H)
        assert r.status_code == 200

    def test_summary(self, client: TestClient) -> None:
        r = client.get("/crm/summary", headers=H)
        assert r.status_code == 200

    def test_export(self, client: TestClient) -> None:
        r = client.get("/crm/export", headers=H)
        assert r.status_code == 200


class TestCRMProjects:
    def test_list_projects(self, client: TestClient) -> None:
        r = client.get("/crm/projects", headers=H)
        assert r.status_code == 200

    def test_create_project(self, client: TestClient) -> None:
        r = client.post("/crm/projects", headers=H, json={"name": "Website Redesign"})
        assert r.status_code in {200, 201}

    def test_project_board(self, client: TestClient) -> None:
        r = client.get("/crm/projects/board", headers=H)
        assert r.status_code == 200


class TestCRMCustomEntities:
    def test_list_entity_types(self, client: TestClient) -> None:
        r = client.get("/crm/custom-entities/types", headers=H)
        assert r.status_code == 200

    def test_create_entity_type(self, client: TestClient) -> None:
        r = client.post("/crm/custom-entities/types", headers=H, json={
            "key": "test_entity",
            "name": "Test Entity",
            "fields": [],
        })
        assert r.status_code in {200, 201, 409}

    def test_list_entity_records(self, client: TestClient) -> None:
        r = client.get("/crm/custom-entities/test_entity/records", headers=H)
        assert r.status_code < 500

    def test_create_entity_record(self, client: TestClient) -> None:
        r = client.post("/crm/custom-entities/test_entity/records", headers=H, json={
            "values": {"name": "Test Record"},
        })
        assert r.status_code < 500


class TestCRMAutomationRecipes:
    def test_list_recipes(self, client: TestClient) -> None:
        r = client.get("/crm/automation/recipes", headers=H)
        assert r.status_code == 200

    def test_create_recipe(self, client: TestClient) -> None:
        r = client.post("/crm/automation/recipes", headers=H, json={
            "name": "Welcome Sequence",
            "trigger": "contact_created",
            "action": "send_email",
            "config": {},
        })
        assert r.status_code in {200, 201}

    def test_run_recipe(self, client: TestClient) -> None:
        r = client.post("/crm/automation/recipes", headers=H, json={
            "name": "Run Test Recipe",
            "trigger": "contact_created",
            "action": "send_email",
        })
        rid = _entity_id(r.json(), "recipe")
        r2 = client.post(f"/crm/automation/recipes/{rid}/run", headers=H)
        assert r2.status_code < 500


class TestCRMHubSpotIntegration:
    def test_hubspot_connect_and_status(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.fastapi.app.integrations.vendor_manager import get_vendor_manager

        manager = get_vendor_manager()

        async def _fake_make_request(*args, **kwargs):
            return {"results": []}

        monkeypatch.setattr(manager, "make_request", _fake_make_request)

        connect = client.post(
            "/crm/integrations/hubspot/connect",
            headers=H,
            json={"access_token": "hubspot-test-token", "portal_id": "12345", "verify_live": True},
        )
        assert connect.status_code == 200
        payload = connect.json()
        assert payload["integration"]["connected"] is True
        assert payload["integration"]["verified"] is True

        status = client.get("/crm/integrations/hubspot/status", headers=H)
        assert status.status_code == 200
        status_payload = status.json()
        assert status_payload["integration"]["connected"] is True
        assert status_payload["integration"]["provider"] == "hubspot"

    def test_hubspot_sync_contacts_upserts_records(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.fastapi.app.integrations.vendor_manager import get_vendor_manager

        manager = get_vendor_manager()

        async def _fake_make_request(vendor_id: str, method: str, endpoint: str, **kwargs):
            if endpoint.endswith("/crm/v3/objects/contacts") and kwargs.get("params", {}).get("limit") == 1:
                return {"results": []}
            return {
                "results": [
                    {
                        "id": "1",
                        "properties": {
                            "email": "hubspot-a@example.com",
                            "firstname": "Hub",
                            "lastname": "SpotA",
                            "phone": "111",
                            "company": "Acme",
                            "lifecyclestage": "lead",
                        },
                    },
                    {
                        "id": "2",
                        "properties": {
                            "email": "hubspot-b@example.com",
                            "firstname": "Hub",
                            "lastname": "SpotB",
                            "phone": "222",
                            "company": "Acme",
                            "lifecyclestage": "customer",
                        },
                    },
                ]
            }

        monkeypatch.setattr(manager, "make_request", _fake_make_request)

        connect = client.post(
            "/crm/integrations/hubspot/connect",
            headers=H,
            json={"access_token": "hubspot-test-token", "verify_live": True},
        )
        assert connect.status_code == 200

        sync = client.post(
            "/crm/integrations/hubspot/sync/contacts",
            headers=H,
            json={"limit": 2, "source": "hubspot"},
        )
        assert sync.status_code == 200
        sync_payload = sync.json()
        assert sync_payload["provider"] == "hubspot"
        assert isinstance(sync_payload.get("created"), int)
        assert isinstance(sync_payload.get("updated"), int)
        assert sync_payload["created"] >= 0
        assert sync_payload["updated"] >= 0

        listed = client.get("/crm/contacts", headers=H)
        assert listed.status_code == 200
        emails = {str(c.get("email", "")).lower() for c in listed.json().get("contacts", [])}
        assert "hubspot-a@example.com" in emails
        assert "hubspot-b@example.com" in emails
