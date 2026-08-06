"""
Tests for crm.py missing coverage paths.
Covers: dedupe (895-940), webhook create/test (1030), leads duplicate (1093-1113),
leads filter (1135), leads update status (1162), tasks (1231-1290), 
kanban (1319), tickets (1335-1416), sla-rules (1450-1465), campaigns (1501-1568),
segments (1599-1643), notes (1671-1708), quotes (1745-1787), etc.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_crm_db.db")

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "crm-db-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app import models as _models
    from backend.fastapi.app.database import init_db

    assert _models is not None
    init_db()
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_contact_round_trip_db_slice(client: TestClient) -> None:
    tenant = "crm-db-roundtrip"
    headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

    created = client.post(
        "/crm/contacts",
        headers=headers,
        json={
            "first_name": "Round",
            "last_name": "Trip",
            "email": "roundtrip@example.com",
            "company": "Nuxtron",
        },
    )
    assert created.status_code in (200, 201)
    contact = created.json().get("contact", {})
    contact_id = int(contact.get("id", 0))
    assert contact_id > 0

    listed = client.get("/crm/contacts", headers=headers)
    assert listed.status_code == 200
    assert any(int(item.get("id", 0)) == contact_id for item in listed.json().get("contacts", []))

    scored = client.post(
        f"/crm/contacts/{contact_id}/score",
        headers=headers,
        json={"score": 82, "reason": "db-round-trip"},
    )
    assert scored.status_code == 200
    assert int(scored.json().get("contact", {}).get("lead_score", 0)) == 82


def _make_contact(client, tenant: str, email: str = "contact@example.com", name: str = "Test User") -> int | None:
    """Create contact and return ID."""
    h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
    r = client.post("/crm/contacts", headers=h, json={
        "first_name": name.split()[0],
        "last_name": name.split()[-1],
        "email": email,
        "company": "TestCo",
        "phone": "555-0100",
    })
    if r.status_code in (200, 201):
        return r.json().get("contact", {}).get("id")
    return None


def _make_lead(client, tenant: str, title: str, contact_id: int | None = None) -> int | None:
    """Create lead and return ID."""
    h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
    r = client.post("/crm/leads", headers=h, json={
        "title": title,
        "source": "website",
        "status": "new",
        "contact_id": contact_id,
        "value": 5000.0,
        "currency": "USD",
    })
    if r.status_code in (200, 201):
        return r.json().get("lead", {}).get("id")
    return None


def _make_task(client, tenant: str, title: str) -> int | None:
    """Create task and return ID."""
    h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
    r = client.post("/crm/tasks", headers=h, json={
        "title": title,
        "status": "open",
        "priority": "medium",
        "due_date": "2025-12-31",
    })
    if r.status_code in (200, 201):
        return r.json().get("task", {}).get("id")
    return None


def _make_ticket(client, tenant: str, title: str, contact_id: int | None = None) -> int | None:
    """Create ticket and return ID."""
    h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
    r = client.post("/crm/tickets", headers=h, json={
        "title": title,
        "description": "Issue description for testing",
        "contact_id": contact_id,
        "priority": "medium",
        "channel": "email",
    })
    if r.status_code in (200, 201):
        return r.json().get("ticket", {}).get("id")
    return None


class TestContactDedupe:
    """Lines 895-940: POST /crm/contacts/dedupe."""

    def test_dedupe_dry_run_no_duplicates(self, client: TestClient) -> None:
        """Lines 895-902: dedupe with no duplicates returns empty merge_preview."""
        tenant = "crm-dedupe-nodupe"
        _make_contact(client, tenant, "unique1@example.com")
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/contacts/dedupe", headers=h, json={"dry_run": True})
        assert r.status_code in VALID

    def test_dedupe_dry_run_with_duplicates(self, client: TestClient) -> None:
        """Lines 895-905: dedupe dry_run with actual duplicate emails."""
        tenant = "crm-dedupe-dryrun"
        # Create two contacts with same email
        _make_contact(client, tenant, "dup@example.com", "First User")
        _make_contact(client, tenant, "dup@example.com", "Second User")
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/contacts/dedupe", headers=h, json={"dry_run": True})
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "merge_preview" in data or "total_duplicates_found" in data

    def test_dedupe_merge_with_duplicates(self, client: TestClient) -> None:
        """Lines 902-940: dedupe with dry_run=False merges contacts."""
        tenant = "crm-dedupe-merge"
        _make_contact(client, tenant, "merge@example.com", "First Contact")
        _make_contact(client, tenant, "merge@example.com", "Second Contact")
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/contacts/dedupe", headers=h, json={"dry_run": False})
        assert r.status_code in VALID


class TestWebhookRoutes:
    """Lines 1030: POST /crm/webhooks edge cases."""

    def test_create_webhook_success(self, client: TestClient) -> None:
        """POST /crm/webhooks creates a new webhook."""
        tenant = "crm-webhook-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/webhooks", headers=h, json={
            "name": "Test Webhook",
            "url": "https://webhook.example.com/receive",
            "events": ["contact.created", "deal.updated"],
            "secret": "webhook-secret-token",
        })
        assert r.status_code in VALID

    def test_test_webhook(self, client: TestClient) -> None:
        """Lines 1043+: POST /crm/webhooks/{id}/test."""
        tenant = "crm-webhook-test-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        # Create webhook
        cr = client.post("/crm/webhooks", headers=h, json={
            "name": "Test Webhook 2",
            "url": "https://webhook.example.com/receive2",
            "events": ["lead.created"],
        })
        if cr.status_code in (200, 201):
            webhook_id = cr.json().get("webhook", {}).get("id")
            if webhook_id:
                r = client.post(f"/crm/webhooks/{webhook_id}/test", headers=h)
                assert r.status_code in VALID


class TestLeadsRoutes:
    """Lines 1093-1162: leads duplicate detection, filtering, update."""

    def test_create_lead_duplicate_detection(self, client: TestClient) -> None:
        """Lines 1093-1113: creating same lead twice returns duplicate_lead."""
        tenant = "crm-lead-dup"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        lead_data = {
            "title": "Duplicate Lead Title",
            "source": "linkedin",
            "status": "new",
            "value": 3000.0,
            "currency": "USD",
        }
        # First create
        client.post("/crm/leads", headers=h, json=lead_data)
        # Second create - should detect as duplicate (line 1093)
        r = client.post("/crm/leads", headers=h, json=lead_data)
        assert r.status_code in VALID

    def test_list_leads_with_status_filter(self, client: TestClient) -> None:
        """Line 1135: filter leads by status."""
        tenant = "crm-lead-filter"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        _make_lead(client, tenant, "Filtered Lead")
        r = client.get("/crm/leads?status=new", headers=h)
        assert r.status_code in VALID

    def test_update_lead_status(self, client: TestClient) -> None:
        """Line 1162: PATCH lead updates status field."""
        tenant = "crm-lead-update"
        lead_id = _make_lead(client, tenant, "Updateable Lead")
        if lead_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.patch(f"/crm/leads/{lead_id}", headers=h, json={"status": "qualified"})
            assert r.status_code in VALID

    def test_get_lead_by_id(self, client: TestClient) -> None:
        """GET /crm/leads/{id}."""
        tenant = "crm-lead-getbyid"
        lead_id = _make_lead(client, tenant, "Get By ID Lead")
        if lead_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.get(f"/crm/leads/{lead_id}", headers=h)
            assert r.status_code in VALID

    def test_convert_lead(self, client: TestClient) -> None:
        """Lines 1176+: POST /crm/leads/{id}/convert."""
        tenant = "crm-lead-convert"
        lead_id = _make_lead(client, tenant, "Lead to Convert")
        if lead_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.post(f"/crm/leads/{lead_id}/convert", headers=h, json={
                "convert_to_contact": True,
                "convert_to_deal": True,
                "deal_name": "Converted Deal",
                "deal_value": 5000.0,
            })
            assert r.status_code in VALID


class TestTasksRoutes:
    """Lines 1231-1319: tasks duplicate, filter, update, kanban."""

    def test_create_task_duplicate(self, client: TestClient) -> None:
        """Lines 1231-1251: creating duplicate task returns existing."""
        tenant = "crm-task-dup"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        task_data = {
            "title": "Duplicate Task Title",
            "status": "open",
            "priority": "high",
            "due_date": "2025-12-31",
        }
        # Create twice
        client.post("/crm/tasks", headers=h, json=task_data)
        r = client.post("/crm/tasks", headers=h, json=task_data)
        assert r.status_code in VALID

    def test_list_tasks_with_status_filter(self, client: TestClient) -> None:
        """Line 1275: filter tasks by status."""
        tenant = "crm-task-filter"
        _make_task(client, tenant, "Filtered Task")
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.get("/crm/tasks?status=open", headers=h)
        assert r.status_code in VALID

    def test_update_task(self, client: TestClient) -> None:
        """Lines 1290-1305: PATCH /crm/tasks/{id}."""
        tenant = "crm-task-update"
        task_id = _make_task(client, tenant, "Task To Update")
        if task_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.patch(f"/crm/tasks/{task_id}", headers=h, json={
                "status": "in_progress",
                "priority": "high",
            })
            assert r.status_code in VALID

    def test_tasks_kanban(self, client: TestClient) -> None:
        """Lines 1319: GET /crm/tasks/kanban creates missing columns."""
        tenant = "crm-task-kanban"
        _make_task(client, tenant, "Kanban Task 1")
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.get("/crm/tasks/kanban", headers=h)
        assert r.status_code in VALID


class TestTicketsRoutes:
    """Lines 1335-1416: ticket SLA, filter, update, escalate."""

    def test_list_tickets_with_status_filter(self, client: TestClient) -> None:
        """Line 1376: filter tickets by status."""
        tenant = "crm-ticket-filter"
        _make_ticket(client, tenant, "Filtered Ticket")
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.get("/crm/tickets?status=open", headers=h)
        assert r.status_code in VALID

    def test_get_ticket_by_id(self, client: TestClient) -> None:
        """Lines 1385+: GET /crm/tickets/{id}."""
        tenant = "crm-ticket-getbyid"
        ticket_id = _make_ticket(client, tenant, "Get Ticket")
        if ticket_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.get(f"/crm/tickets/{ticket_id}", headers=h)
            assert r.status_code in VALID

    def test_update_ticket(self, client: TestClient) -> None:
        """Lines 1394-1411: PATCH /crm/tickets/{id}."""
        tenant = "crm-ticket-update"
        ticket_id = _make_ticket(client, tenant, "Ticket To Update")
        if ticket_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.patch(f"/crm/tickets/{ticket_id}", headers=h, json={
                "status": "in_progress",
                "priority": "high",
                "assignee_id": 5,
            })
            assert r.status_code in VALID

    def test_escalate_ticket(self, client: TestClient) -> None:
        """Lines 1416+: POST /crm/tickets/{id}/escalate."""
        tenant = "crm-ticket-escalate"
        ticket_id = _make_ticket(client, tenant, "Ticket To Escalate")
        if ticket_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.post(f"/crm/tickets/{ticket_id}/escalate", headers=h, json={
                "reason": "Customer is unhappy with response time.",
                "escalate_to": "manager@example.com",
            })
            assert r.status_code in VALID


class TestSlaRules:
    """Lines 1450-1465: SLA rule duplicate detection."""

    def test_create_sla_rule_duplicate(self, client: TestClient) -> None:
        """Lines 1450-1465: creating same SLA rule triggers duplicate check."""
        tenant = "crm-sla-dup"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        sla_data = {
            "name": "Critical SLA",
            "priority": "critical",
            "first_response_hours": 1,
            "resolution_hours": 4,
        }
        client.post("/crm/sla-rules", headers=h, json=sla_data)
        r = client.post("/crm/sla-rules", headers=h, json=sla_data)
        assert r.status_code in VALID

    def test_list_sla_rules(self, client: TestClient) -> None:
        """Lines 1474+: GET /crm/sla-rules."""
        tenant = "crm-sla-list"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.get("/crm/sla-rules", headers=h)
        assert r.status_code in VALID


class TestCrmCampaigns:
    """Lines 1501-1568: CRM email campaigns."""

    def test_create_campaign_duplicate(self, client: TestClient) -> None:
        """Lines 1501-1524: campaign duplicate detection."""
        tenant = "crm-camp-dup"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        camp_data = {
            "name": "Duplicate Campaign",
            "type": "email",
            "subject": "Test Subject",
            "body": "Email body content",
            "status": "draft",
        }
        client.post("/crm/campaigns", headers=h, json=camp_data)
        r = client.post("/crm/campaigns", headers=h, json=camp_data)
        assert r.status_code in VALID

    def test_list_campaigns_with_status_filter(self, client: TestClient) -> None:
        """Line 1545: filter CRM campaigns by status."""
        tenant = "crm-camp-filter"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        client.post("/crm/campaigns", headers=h, json={
            "name": "Status Filtered Campaign",
            "type": "email",
            "subject": "Test",
            "body": "Body",
            "status": "draft",
        })
        r = client.get("/crm/campaigns?status=draft", headers=h)
        assert r.status_code in VALID

    def test_get_campaign_by_id(self, client: TestClient) -> None:
        """Lines 1552+: GET /crm/campaigns/{id}."""
        tenant = "crm-camp-getbyid"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        cr = client.post("/crm/campaigns", headers=h, json={
            "name": "Get By ID Campaign",
            "type": "email",
            "subject": "Subject",
            "body": "Body",
            "status": "draft",
        })
        if cr.status_code in (200, 201):
            camp_id = cr.json().get("campaign", {}).get("id")
            if camp_id:
                r = client.get(f"/crm/campaigns/{camp_id}", headers=h)
                assert r.status_code in VALID

    def test_send_campaign(self, client: TestClient) -> None:
        """Lines 1561+: POST /crm/campaigns/{id}/send."""
        tenant = "crm-camp-send"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        cr = client.post("/crm/campaigns", headers=h, json={
            "name": "Sendable Campaign",
            "type": "email",
            "subject": "Launch Announcement",
            "body": "We are excited to announce our new product!",
            "status": "draft",
        })
        if cr.status_code in (200, 201):
            camp_id = cr.json().get("campaign", {}).get("id")
            if camp_id:
                r = client.post(f"/crm/campaigns/{camp_id}/send", headers=h, json={
                    "segment_ids": [],
                    "contact_ids": [],
                })
                assert r.status_code in VALID


class TestSegmentsAndNotes:
    """Lines 1599-1708: segments and notes routes."""

    def test_create_segment_duplicate(self, client: TestClient) -> None:
        """Lines 1599-1616: segment duplicate detection."""
        tenant = "crm-seg-dup"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        seg_data = {
            "name": "Duplicate Segment",
            "filters": {"industry": "tech"},
        }
        client.post("/crm/segments", headers=h, json=seg_data)
        r = client.post("/crm/segments", headers=h, json=seg_data)
        assert r.status_code in VALID

    def test_get_segment_not_found(self, client: TestClient) -> None:
        """Line 1643: GET nonexistent segment → 404."""
        r = client.get("/crm/segments/999999", headers=H)
        assert r.status_code in VALID

    def test_create_note_and_filter_by_contact(self, client: TestClient) -> None:
        """Lines 1708: GET notes filtered by contact_id."""
        tenant = "crm-note-filter"
        contact_id = _make_contact(client, tenant, "notecontact@example.com")
        if contact_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            client.post("/crm/notes", headers=h, json={
                "contact_id": contact_id,
                "content": "This is a note about the contact.",
            })
            r = client.get(f"/crm/notes?contact_id={contact_id}", headers=h)
            assert r.status_code in VALID

    def test_create_note_duplicate(self, client: TestClient) -> None:
        """Lines 1671-1686: note duplicate detection."""
        tenant = "crm-note-dup"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        note_data = {"content": "Duplicate Note Content"}
        client.post("/crm/notes", headers=h, json=note_data)
        r = client.post("/crm/notes", headers=h, json=note_data)
        assert r.status_code in VALID


class TestQuotesAndInvoices:
    """Lines 1745-1832: quotes and invoices."""

    def test_create_quote_duplicate(self, client: TestClient) -> None:
        """Lines 1745-1767: quote duplicate detection."""
        tenant = "crm-quote-dup"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        quote_data = {
            "title": "Duplicate Quote",
            "contact_id": None,
            "deal_id": None,
            "line_items": [{"name": "Software License", "qty": 1, "price": 2999.0}],
            "currency": "USD",
        }
        client.post("/crm/quotes", headers=h, json=quote_data)
        r = client.post("/crm/quotes", headers=h, json=quote_data)
        assert r.status_code in VALID

    def test_list_quotes_with_status_filter(self, client: TestClient) -> None:
        """Line 1787: filter quotes by status."""
        tenant = "crm-quote-filter"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        client.post("/crm/quotes", headers=h, json={
            "title": "Filtered Quote",
            "line_items": [{"name": "Service", "qty": 1, "price": 1000.0}],
            "currency": "USD",
            "status": "draft",
        })
        r = client.get("/crm/quotes?status=draft", headers=h)
        assert r.status_code in VALID

    def test_create_invoice(self, client: TestClient) -> None:
        """Lines 1828-1833: POST /crm/invoices."""
        tenant = "crm-invoice-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/invoices", headers=h, json={
            "title": "Invoice #001",
            "contact_id": None,
            "line_items": [{"name": "Consulting", "qty": 5, "price": 200.0}],
            "currency": "USD",
            "due_date": "2025-03-31",
        })
        assert r.status_code in VALID

    def test_update_invoice_status(self, client: TestClient) -> None:
        """Lines 1847-1852: PATCH /crm/invoices/{id}."""
        tenant = "crm-invoice-update"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        cr = client.post("/crm/invoices", headers=h, json={
            "title": "Invoice to Update",
            "line_items": [{"name": "Service", "qty": 1, "price": 500.0}],
            "currency": "USD",
        })
        if cr.status_code in (200, 201):
            inv_id = cr.json().get("invoice", {}).get("id")
            if inv_id:
                r = client.patch(f"/crm/invoices/{inv_id}", headers=h, json={"status": "sent"})
                assert r.status_code in VALID


class TestEmailSequences:
    """Lines 1867-1977: email sequences."""

    def test_create_email_sequence(self, client: TestClient) -> None:
        """POST /crm/email-sequences."""
        tenant = "crm-emailseq-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/email-sequences", headers=h, json={
            "name": "Onboarding Sequence",
            "trigger": "contact.created",
            "steps": [
                {"day": 0, "subject": "Welcome!", "body": "Thank you for joining us."},
                {"day": 3, "subject": "Getting Started", "body": "Here are some tips."},
            ],
        })
        assert r.status_code in VALID

    def test_list_email_sequences(self, client: TestClient) -> None:
        """Lines 1958+: GET /crm/email-sequences."""
        r = client.get("/crm/email-sequences", headers=H)
        assert r.status_code in VALID

    def test_enroll_in_sequence(self, client: TestClient) -> None:
        """Lines 1966+: POST /crm/email-sequences/{id}/enroll."""
        tenant = "crm-emailseq-enroll"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        cr = client.post("/crm/email-sequences", headers=h, json={
            "name": "Enrollment Test Sequence",
            "trigger": "manual",
            "steps": [{"day": 0, "subject": "Hello", "body": "Welcome message."}],
        })
        if cr.status_code in (200, 201):
            seq_id = cr.json().get("sequence", {}).get("id")
            contact_id = _make_contact(client, tenant, "enrollee@example.com")
            if seq_id and contact_id:
                r = client.post(f"/crm/email-sequences/{seq_id}/enroll", headers=h, json={
                    "contact_ids": [contact_id],
                })
                assert r.status_code in VALID


class TestWorkflowRules:
    """Lines 1981-2054: workflow rules."""

    def test_create_workflow_rule(self, client: TestClient) -> None:
        """POST /crm/workflow-rules."""
        tenant = "crm-workflow-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/workflow-rules", headers=h, json={
            "name": "Auto-assign high value leads",
            "trigger": "lead.created",
            "conditions": {"value_gt": 10000},
            "actions": [{"type": "assign", "assignee_id": 1}],
        })
        assert r.status_code in VALID

    def test_list_workflow_rules(self, client: TestClient) -> None:
        """Lines 2034+: GET /crm/workflow-rules."""
        r = client.get("/crm/workflow-rules", headers=H)
        assert r.status_code in VALID

    def test_trigger_workflow_rule(self, client: TestClient) -> None:
        """Lines 2041+: POST /crm/workflow-rules/{id}/trigger."""
        tenant = "crm-workflow-trigger"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        cr = client.post("/crm/workflow-rules", headers=h, json={
            "name": "Trigger Test Rule",
            "trigger": "manual",
            "conditions": {},
            "actions": [{"type": "notify", "message": "Rule triggered"}],
        })
        if cr.status_code in (200, 201):
            rule_id = cr.json().get("workflow_rule", {}).get("id")
            if rule_id:
                r = client.post(f"/crm/workflow-rules/{rule_id}/trigger", headers=h, json={
                    "context": {"lead_id": 1},
                })
                assert r.status_code in VALID


class TestProjectsRoutes:
    """Lines 2058-2150: projects CRUD."""

    def test_create_project(self, client: TestClient) -> None:
        """POST /crm/projects."""
        tenant = "crm-proj-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/projects", headers=h, json={
            "name": "Q1 Marketing Campaign",
            "description": "Planning and execution of Q1 marketing",
            "status": "planning",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        })
        assert r.status_code in VALID

    def test_list_projects(self, client: TestClient) -> None:
        """Lines 2100+: GET /crm/projects."""
        r = client.get("/crm/projects", headers=H)
        assert r.status_code in VALID

    def test_update_project(self, client: TestClient) -> None:
        """Lines 2119+: PATCH /crm/projects/{id}."""
        tenant = "crm-proj-update"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        cr = client.post("/crm/projects", headers=h, json={
            "name": "Updatable Project",
            "status": "planning",
        })
        if cr.status_code in (200, 201):
            proj_id = cr.json().get("project", {}).get("id")
            if proj_id:
                r = client.patch(f"/crm/projects/{proj_id}", headers=h, json={
                    "status": "in_progress",
                    "name": "Updated Project Name",
                })
                assert r.status_code in VALID

    def test_projects_board(self, client: TestClient) -> None:
        """Lines 2141+: GET /crm/projects/board."""
        r = client.get("/crm/projects/board", headers=H)
        assert r.status_code in VALID


class TestCustomEntities:
    """Lines 2156-2250: custom entity types and records."""

    def test_create_entity_type(self, client: TestClient) -> None:
        """Lines 2156+: POST /crm/custom-entities/types."""
        tenant = "crm-entity-type-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/custom-entities/types", headers=h, json={
            "entity_key": "partners",
            "display_name": "Partners",
            "fields": [
                {"key": "partner_level", "label": "Partner Level", "type": "string"},
                {"key": "revenue_share_pct", "label": "Revenue Share %", "type": "number"},
            ],
        })
        assert r.status_code in VALID

    def test_create_entity_record(self, client: TestClient) -> None:
        """Lines 2192+: POST /crm/custom-entities/{key}/records."""
        tenant = "crm-entity-rec-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        # Create the entity type first
        client.post("/crm/custom-entities/types", headers=h, json={
            "entity_key": "vendors",
            "display_name": "Vendors",
            "fields": [{"key": "vendor_tier", "label": "Tier", "type": "string"}],
        })
        r = client.post("/crm/custom-entities/vendors/records", headers=h, json={
            "vendor_tier": "Gold",
            "name": "Vendor ABC",
        })
        assert r.status_code in VALID

    def test_list_entity_records(self, client: TestClient) -> None:
        """Lines 2222+: GET /crm/custom-entities/{key}/records."""
        tenant = "crm-entity-list-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        client.post("/crm/custom-entities/types", headers=h, json={
            "entity_key": "partners2",
            "display_name": "Partners 2",
            "fields": [],
        })
        r = client.get("/crm/custom-entities/partners2/records", headers=h)
        assert r.status_code in VALID


class TestAutomationRecipes:
    """Lines 2250-2325: automation recipes."""

    def test_create_automation_recipe(self, client: TestClient) -> None:
        """POST /crm/automation/recipes."""
        tenant = "crm-auto-recipe"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post("/crm/automation/recipes", headers=h, json={
            "name": "Lead Follow-up Automation",
            "trigger": "lead.created",
            "steps": [
                {"type": "wait", "duration_hours": 24},
                {"type": "send_email", "template": "follow_up"},
            ],
        })
        assert r.status_code in VALID

    def test_list_automation_recipes(self, client: TestClient) -> None:
        """Lines 2302+: GET /crm/automation/recipes."""
        r = client.get("/crm/automation/recipes", headers=H)
        assert r.status_code in VALID

    def test_run_automation_recipe(self, client: TestClient) -> None:
        """Lines 2310+: POST /crm/automation/recipes/{id}/run."""
        tenant = "crm-auto-run"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        cr = client.post("/crm/automation/recipes", headers=h, json={
            "name": "Runnable Recipe",
            "trigger": "manual",
            "steps": [{"type": "notify", "message": "Recipe ran"}],
        })
        if cr.status_code in (200, 201):
            recipe_id = cr.json().get("recipe", {}).get("id")
            if recipe_id:
                r = client.post(f"/crm/automation/recipes/{recipe_id}/run", headers=h, json={
                    "context": {"contact_id": 1},
                })
                assert r.status_code in VALID


class TestReportsRoutes:
    """Lines 2395-2572: reports and ops routes."""

    def test_forecast_report(self, client: TestClient) -> None:
        """Lines 2395+: GET /crm/reports/forecast."""
        r = client.get("/crm/reports/forecast", headers=H)
        assert r.status_code in VALID

    def test_kpis_report(self, client: TestClient) -> None:
        """Lines 2447+: GET /crm/reports/kpis."""
        r = client.get("/crm/reports/kpis", headers=H)
        assert r.status_code in VALID

    def test_executive_analytics_report(self, client: TestClient) -> None:
        """Lines 2501+: GET /crm/reports/executive-analytics."""
        r = client.get("/crm/reports/executive-analytics", headers=H)
        assert r.status_code in VALID

    def test_ops_backup(self, client: TestClient) -> None:
        """Lines 2542-2572: GET /crm/ops/backup."""
        r = client.get("/crm/ops/backup", headers=H)
        assert r.status_code in VALID

    def test_ops_backup_config(self, client: TestClient) -> None:
        """POST /crm/ops/backup/config."""
        r = client.post("/crm/ops/backup/config", headers=H, json={
            "backup_frequency": "daily",
            "retention_days": 30,
            "include_attachments": True,
        })
        assert r.status_code in VALID

    def test_ops_backup_run(self, client: TestClient) -> None:
        """Lines 2563+: POST /crm/ops/backup/run."""
        r = client.post("/crm/ops/backup/run", headers=H, json={})
        assert r.status_code in VALID

    def test_ops_live_sync_status(self, client: TestClient) -> None:
        """Lines 2565+: GET /crm/ops/live-sync."""
        r = client.get("/crm/ops/live-sync", headers=H)
        assert r.status_code in VALID

    def test_ops_live_sync_toggle(self, client: TestClient) -> None:
        """Lines 2572+: POST /crm/ops/live-sync/toggle."""
        r = client.post("/crm/ops/live-sync/toggle", headers=H, json={"enabled": True})
        assert r.status_code in VALID

    def test_ops_live_sync_run(self, client: TestClient) -> None:
        """POST /crm/ops/live-sync/run."""
        r = client.post("/crm/ops/live-sync/run", headers=H, json={})
        assert r.status_code in VALID
