"""Comprehensive coverage tests for tickets.py — all endpoints and branches."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "tickets-coverage-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _create_ticket(client: TestClient, **kwargs: object) -> dict:
    payload = {
        "subject": "Test ticket",
        "customer_email": "user@example.com",
        **kwargs,
    }
    r = client.post("/tickets", headers=H, json=payload)
    assert r.status_code in (200, 201)
    return r.json()["ticket"]


class TestTicketsCoverage:
    def test_create_ticket_default_priority_and_channel(self, client: TestClient) -> None:
        """Invalid priority and channel should default to 'normal' and 'api'."""
        r = client.post(
            "/tickets",
            headers=H,
            json={
                "subject": "Bad priority ticket",
                "customer_email": "a@example.com",
                "priority": "invalid",  # invalid → 'normal' (max_length=10)
                "channel": "fax",  # invalid → 'api'
            },
        )
        assert r.status_code in (200, 201)
        t = r.json()["ticket"]
        assert t["priority"] == "normal"
        assert t["channel"] == "api"
        assert t["status"] == "open"
        assert "ticket_number" in t
        assert "first_response_due" in t

    def test_create_ticket_valid_priority_high(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="High priority", priority="high", channel="email",
                           customer_email="high@example.com", customer_name="High User",
                           contact_id="contact-123", tags=["billing"], attachments=[])
        assert t["priority"] == "high"
        assert t["channel"] == "email"
        assert t["customer_name"] == "High User"

    def test_create_ticket_urgent_priority(self, client: TestClient) -> None:
        t = _create_ticket(client, priority="urgent", customer_email="urgent@example.com")
        assert t["priority"] == "urgent"
        # Urgent SLA: 1h first response, 8h resolution
        assert t["sla_first_response_hours"] == 1
        assert t["sla_resolution_hours"] == 8

    def test_list_tickets_no_filter(self, client: TestClient) -> None:
        r = client.get("/tickets", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "tickets" in data
        assert data["total"] >= 1

    def test_list_tickets_filter_by_status(self, client: TestClient) -> None:
        r = client.get("/tickets", headers=H, params={"status": "open"})
        assert r.status_code == 200
        tickets = r.json()["tickets"]
        assert all(t["status"] == "open" for t in tickets)

    def test_list_tickets_filter_by_priority(self, client: TestClient) -> None:
        r = client.get("/tickets", headers=H, params={"priority": "high"})
        assert r.status_code == 200
        tickets = r.json()["tickets"]
        assert all(t["priority"] == "high" for t in tickets)

    def test_list_tickets_filter_by_assigned_to(self, client: TestClient) -> None:
        # Assign one ticket first
        t = _create_ticket(client, subject="Assigned ticket", customer_email="assign@example.com")
        tid = t["id"]
        client.patch(f"/tickets/{tid}", headers=H, json={"assigned_to": "agent-007"})
        r = client.get("/tickets", headers=H, params={"assigned_to": "agent-007"})
        assert r.status_code == 200
        tickets = r.json()["tickets"]
        assert any(t["assigned_to"] == "agent-007" for t in tickets)

    def test_get_ticket_success(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Get me", customer_email="getme@example.com")
        r = client.get(f"/tickets/{t['id']}", headers=H)
        assert r.status_code == 200
        assert r.json()["ticket"]["id"] == t["id"]
        assert "comments" in r.json()["ticket"]

    def test_get_ticket_not_found(self, client: TestClient) -> None:
        r = client.get("/tickets/999999", headers=H)
        assert r.status_code == 404

    def test_update_ticket_subject(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Old subject", customer_email="subj@example.com")
        r = client.patch(f"/tickets/{t['id']}", headers=H, json={"subject": "New subject"})
        assert r.status_code == 200
        assert r.json()["ticket"]["subject"] == "New subject"

    def test_update_ticket_status_to_resolved(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Resolve me", customer_email="resolve@example.com")
        r = client.patch(
            f"/tickets/{t['id']}", headers=H,
            json={"status": "resolved", "resolution_notes": "Fixed in v2.3"}
        )
        assert r.status_code == 200
        updated = r.json()["ticket"]
        assert updated["status"] == "resolved"
        assert updated["resolved_at"] is not None
        assert updated["resolution_notes"] == "Fixed in v2.3"

    def test_update_ticket_status_to_closed(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Close me", customer_email="close@example.com")
        r = client.patch(f"/tickets/{t['id']}", headers=H, json={"status": "closed"})
        assert r.status_code == 200
        assert r.json()["ticket"]["status"] == "closed"

    def test_update_ticket_priority_recalculates_sla(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="SLA recalc", customer_email="sla@example.com", priority="low")
        r = client.patch(f"/tickets/{t['id']}", headers=H, json={"priority": "urgent"})
        assert r.status_code == 200
        updated = r.json()["ticket"]
        assert updated["priority"] == "urgent"
        assert updated["sla_first_response_hours"] == 1

    def test_update_ticket_assigned_to_sets_first_response(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Assign agent", customer_email="agent@example.com")
        assert t["first_response_at"] is None
        r = client.patch(f"/tickets/{t['id']}", headers=H, json={"assigned_to": "agent-alice"})
        assert r.status_code == 200
        updated = r.json()["ticket"]
        assert updated["assigned_to"] == "agent-alice"
        assert updated["first_response_at"] is not None

    def test_update_ticket_tags(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Tag me", customer_email="tags@example.com")
        r = client.patch(f"/tickets/{t['id']}", headers=H, json={"tags": ["billing", "urgent"]})
        assert r.status_code == 200
        assert r.json()["ticket"]["tags"] == ["billing", "urgent"]

    def test_update_ticket_not_found(self, client: TestClient) -> None:
        r = client.patch("/tickets/999999", headers=H, json={"subject": "ghost"})
        assert r.status_code == 404

    def test_add_public_comment_sets_first_response(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Comment test", customer_email="cmt@example.com")
        assert t["first_response_at"] is None
        r = client.post(
            f"/tickets/{t['id']}/comments",
            headers=H,
            json={"body": "We are looking into this.", "is_internal": False},
        )
        assert r.status_code in (200, 201)
        comment = r.json()["comment"]
        assert comment["is_internal"] is False
        # Verify first_response_at was set on the ticket
        r2 = client.get(f"/tickets/{t['id']}", headers=H)
        assert r2.json()["ticket"]["first_response_at"] is not None

    def test_add_internal_comment_does_not_set_first_response(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Internal note", customer_email="internal@example.com")
        r = client.post(
            f"/tickets/{t['id']}/comments",
            headers=H,
            json={"body": "Internal agent note only.", "is_internal": True},
        )
        assert r.status_code in (200, 201)
        assert r.json()["comment"]["is_internal"] is True
        # first_response_at should still be None (internal note doesn't count)
        r2 = client.get(f"/tickets/{t['id']}", headers=H)
        assert r2.json()["ticket"]["first_response_at"] is None

    def test_add_comment_not_found(self, client: TestClient) -> None:
        r = client.post(
            "/tickets/999999/comments",
            headers=H,
            json={"body": "Comment on ghost ticket"},
        )
        assert r.status_code == 404

    def test_list_comments_success(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="Comment list", customer_email="cmtlist@example.com")
        client.post(f"/tickets/{t['id']}/comments", headers=H, json={"body": "First comment"})
        client.post(f"/tickets/{t['id']}/comments", headers=H, json={"body": "Second comment"})
        r = client.get(f"/tickets/{t['id']}/comments", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_list_comments_not_found(self, client: TestClient) -> None:
        r = client.get("/tickets/999999/comments", headers=H)
        assert r.status_code == 404

    def test_submit_csat_score(self, client: TestClient) -> None:
        t = _create_ticket(client, subject="CSAT ticket", customer_email="csat@example.com")
        r = client.post(f"/tickets/{t['id']}/csat", headers=H, params={"score": 5})
        assert r.status_code == 200
        data = r.json()
        assert data["csat_score"] == 5

    def test_submit_csat_not_found(self, client: TestClient) -> None:
        r = client.post("/tickets/999999/csat", headers=H, params={"score": 4})
        assert r.status_code == 404

    def test_configure_sla_create_new(self, client: TestClient) -> None:
        r = client.put(
            "/tickets/sla-config",
            headers=H,
            json={"priority": "urgent", "first_response_hours": 2, "resolution_hours": 12},
        )
        assert r.status_code == 200
        cfg = r.json()["sla_config"]
        assert cfg["priority"] == "urgent"
        assert cfg["first_response_hours"] == 2

    def test_configure_sla_update_existing(self, client: TestClient) -> None:
        # Configure normal SLA once, then update it
        client.put(
            "/tickets/sla-config",
            headers=H,
            json={"priority": "normal", "first_response_hours": 6, "resolution_hours": 36},
        )
        r = client.put(
            "/tickets/sla-config",
            headers=H,
            json={"priority": "normal", "first_response_hours": 4, "resolution_hours": 24},
        )
        assert r.status_code == 200
        cfg = r.json()["sla_config"]
        assert cfg["first_response_hours"] == 4

    def test_create_ticket_uses_custom_sla(self, client: TestClient) -> None:
        """Ensure _get_sla() takes tenant config branch when present."""
        r_cfg = client.put(
            "/tickets/sla-config",
            headers=H,
            json={"priority": "high", "first_response_hours": 3, "resolution_hours": 10},
        )
        assert r_cfg.status_code == 200

        t = _create_ticket(client, subject="Custom SLA", customer_email="custom-sla@example.com", priority="high")
        assert t["sla_first_response_hours"] == 3
        assert t["sla_resolution_hours"] == 10

    def test_configure_sla_invalid_priority(self, client: TestClient) -> None:
        r = client.put(
            "/tickets/sla-config",
            headers=H,
            json={"priority": "superhigh", "first_response_hours": 1, "resolution_hours": 5},
        )
        assert r.status_code == 422

    def test_ticket_analytics(self, client: TestClient) -> None:
        r = client.get("/tickets/analytics/summary", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "total_tickets" in data
        assert "open" in data
        assert "priority_breakdown" in data
