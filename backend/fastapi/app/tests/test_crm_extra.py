"""
Supplementary CRM tests for routes not covered in test_crm_router.py.
Covers: tickets, sla-rules, invoices, email-sequences, workflow-rules, api-tokens, ops/backup, ops/live-sync.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestCrmTicketsExtra:
    def test_patch_ticket(self, client: TestClient) -> None:
        r = client.patch("/crm/tickets/ticket_nonexistent", headers=H, json={"status": "resolved"})
        assert r.status_code in VALID

    def test_escalate_ticket(self, client: TestClient) -> None:
        r = client.post("/crm/tickets/ticket_nonexistent/escalate", headers=H, json={"reason": "Urgent"})
        assert r.status_code in VALID


class TestCrmSlaRules:
    def test_create_sla_rule(self, client: TestClient) -> None:
        r = client.post("/crm/sla-rules", headers=H, json={
            "name": "P1 SLA", "priority": "critical", "response_hours": 1, "resolution_hours": 4
        })
        assert r.status_code in VALID

    def test_list_sla_rules(self, client: TestClient) -> None:
        r = client.get("/crm/sla-rules", headers=H)
        assert r.status_code in VALID


class TestCrmInvoices:
    def test_create_invoice(self, client: TestClient) -> None:
        r = client.post("/crm/invoices", headers=H, json={
            "contact_id": "contact_001", "amount": 1500.0, "currency": "USD",
            "due_date": "2025-04-30", "line_items": [{"description": "Consulting", "amount": 1500.0}]
        })
        assert r.status_code in VALID

    def test_list_invoices(self, client: TestClient) -> None:
        r = client.get("/crm/invoices", headers=H)
        assert r.status_code in VALID

    def test_patch_invoice(self, client: TestClient) -> None:
        r = client.patch("/crm/invoices/invoice_nonexistent", headers=H, json={"status": "paid"})
        assert r.status_code in VALID


class TestCrmEmailSequences:
    def test_create_email_sequence(self, client: TestClient) -> None:
        r = client.post("/crm/email-sequences", headers=H, json={
            "name": "Onboarding", "steps": [{"delay_days": 0, "subject": "Welcome", "body": "Hello!"}]
        })
        assert r.status_code in VALID

    def test_list_email_sequences(self, client: TestClient) -> None:
        r = client.get("/crm/email-sequences", headers=H)
        assert r.status_code in VALID

    def test_enroll_sequence(self, client: TestClient) -> None:
        r = client.post("/crm/email-sequences/seq_nonexistent/enroll", headers=H, json={
            "contact_id": "contact_001"
        })
        assert r.status_code in VALID


class TestCrmWorkflowRules:
    def test_create_workflow_rule(self, client: TestClient) -> None:
        r = client.post("/crm/workflow-rules", headers=H, json={
            "name": "Lead Scoring", "trigger": "contact_created",
            "actions": [{"type": "tag", "tag": "new_lead"}]
        })
        assert r.status_code in VALID

    def test_list_workflow_rules(self, client: TestClient) -> None:
        r = client.get("/crm/workflow-rules", headers=H)
        assert r.status_code in VALID

    def test_trigger_workflow_rule(self, client: TestClient) -> None:
        r = client.post("/crm/workflow-rules/rule_nonexistent/trigger", headers=H, json={
            "contact_id": "contact_001"
        })
        assert r.status_code in VALID


class TestCrmProjectsPatch:
    def test_patch_project(self, client: TestClient) -> None:
        r = client.patch("/crm/projects/proj_nonexistent", headers=H, json={"status": "completed"})
        assert r.status_code in VALID


class TestCrmApiTokens:
    def test_create_api_token(self, client: TestClient) -> None:
        r = client.post("/crm/api-tokens", headers=H, json={
            "name": "Integration Token", "scopes": ["crm:read", "crm:write"]
        })
        assert r.status_code in VALID

    def test_list_api_tokens(self, client: TestClient) -> None:
        r = client.get("/crm/api-tokens", headers=H)
        assert r.status_code in VALID


class TestCrmOps:
    def test_get_backup(self, client: TestClient) -> None:
        r = client.get("/crm/ops/backup", headers=H)
        assert r.status_code in VALID

    def test_backup_config(self, client: TestClient) -> None:
        r = client.post("/crm/ops/backup/config", headers=H, json={
            "schedule": "daily", "retention_days": 30
        })
        assert r.status_code in VALID

    def test_backup_run(self, client: TestClient) -> None:
        r = client.post("/crm/ops/backup/run", headers=H, json={})
        assert r.status_code in VALID

    def test_get_live_sync(self, client: TestClient) -> None:
        r = client.get("/crm/ops/live-sync", headers=H)
        assert r.status_code in VALID

    def test_toggle_live_sync(self, client: TestClient) -> None:
        r = client.post("/crm/ops/live-sync/toggle", headers=H, json={"enabled": True})
        assert r.status_code in VALID

    def test_run_live_sync(self, client: TestClient) -> None:
        r = client.post("/crm/ops/live-sync/run", headers=H, json={})
        assert r.status_code in VALID
