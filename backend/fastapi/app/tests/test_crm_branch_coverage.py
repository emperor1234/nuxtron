"""Focused CRM branch tests: duplicate-creation paths, 404s, and CSV export."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "crm-branch-coverage-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestCRMBranchCoverage:
    # ── Webhook duplicate-creation path (line ~1030) ─────────────────────────

    def test_create_webhook_then_duplicate(self, client: TestClient) -> None:
        payload = {
            "event": "contact.created",
            "target_url": "https://hooks.example.com/crm-branch",
            "secret": "s3cr3t",
        }
        r1 = client.post("/crm/webhooks", headers=H, json=payload)
        assert r1.status_code in (200, 201)
        assert r1.json()["duplicate"] is False

        r2 = client.post("/crm/webhooks", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    # ── CSV export paths ──────────────────────────────────────────────────────

    def test_export_contacts_csv_with_data(self, client: TestClient) -> None:
        # Create at least one contact first.
        client.post(
            "/crm/contacts",
            headers=H,
            json={"email": "csvtest@branch.com", "first_name": "CSV", "last_name": "Test"},
        )
        r = client.get("/crm/export?resource=contacts&format=csv", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["format"] == "csv"
        assert "csv" in data

    def test_export_empty_csv(self, client: TestClient) -> None:
        # Use a tenant with no contacts.
        h_empty = {"X-API-Key": "test-api-key", "X-Tenant-Id": "crm-empty-csv-tenant"}
        r = client.get("/crm/export?resource=contacts&format=csv", headers=h_empty)
        assert r.status_code == 200
        assert r.json()["csv"] == ""

    # ── Dedup contact with no email (skips merge) → line ~895 ────────────────

    def test_dedup_contact_no_email_skipped(self, client: TestClient) -> None:
        # Create a contact with blank email — it should appear as a "no email" group but be skipped.
        client.post(
            "/crm/contacts",
            headers=H,
            json={"email": "", "first_name": "NoEmail", "last_name": "Test"},
        )
        r = client.post("/crm/contacts/dedupe", headers=H, json={"dry_run": True})
        assert r.status_code in (200, 201, 422)

    # ── Lead duplicate and 404 paths ──────────────────────────────────────────

    def test_create_lead_then_duplicate(self, client: TestClient) -> None:
        unique_title = f"Dupe Lead Branch {datetime.now(UTC).isoformat()}"
        payload = {"title": unique_title, "source": "referral", "status": "new"}
        r1 = client.post("/crm/leads", headers=H, json=payload)
        assert r1.status_code in (200, 201)
        assert r1.json()["duplicate"] is False

        r2 = client.post("/crm/leads", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_get_lead_not_found(self, client: TestClient) -> None:
        r = client.get("/crm/leads/999999", headers=H)
        assert r.status_code == 404

    def test_update_lead_not_found(self, client: TestClient) -> None:
        r = client.patch("/crm/leads/999999", headers=H, json={"status": "qualified"})
        assert r.status_code == 404

    def test_convert_lead_not_found(self, client: TestClient) -> None:
        r = client.post("/crm/leads/999999/convert", headers=H)
        assert r.status_code == 404

    def test_lead_list_with_filters(self, client: TestClient) -> None:
        r = client.get("/crm/leads?status=new&assigned_to=nobody&q=Dupe", headers=H)
        assert r.status_code == 200

    # ── SLA rule duplicate path ───────────────────────────────────────────────

    def test_create_sla_rule_then_duplicate(self, client: TestClient) -> None:
        payload = {
            "name": "Branch SLA Rule",
            "applies_to": "tickets",
            "priority": "high",
            "first_response_hours": 2,
            "resolution_hours": 8,
        }
        r1 = client.post("/crm/sla-rules", headers=H, json=payload)
        assert r1.status_code in (200, 201)
        assert r1.json()["duplicate"] is False

        r2 = client.post("/crm/sla-rules", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    # ── Campaign duplicate path and 404 ──────────────────────────────────────

    def test_create_campaign_then_duplicate(self, client: TestClient) -> None:
        payload = {
            "name": "Dupe Campaign",
            "type": "email",
            "subject": "Branch Coverage Email",
            "body": "Test body",
        }
        r1 = client.post("/crm/campaigns", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/campaigns", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_get_campaign_not_found(self, client: TestClient) -> None:
        r = client.get("/crm/campaigns/999999", headers=H)
        assert r.status_code == 404

    def test_campaign_list_filters(self, client: TestClient) -> None:
        r = client.get("/crm/campaigns?status=draft&type=email", headers=H)
        assert r.status_code == 200

    # ── Email sequence duplicate and 404 paths ────────────────────────────────

    def test_create_sequence_then_duplicate(self, client: TestClient) -> None:
        payload = {
            "name": "Dupe Sequence Branch",
            "steps": [{"day": 1, "subject": "Hello", "body": "Hello there"}],
        }
        r1 = client.post("/crm/email-sequences", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/email-sequences", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_enroll_sequence_not_found(self, client: TestClient) -> None:
        r = client.post("/crm/email-sequences/999999/enroll?contact_id=1", headers=H)
        assert r.status_code == 404

    # ── Ticket and CRM-ticket 404s ────────────────────────────────────────────

    def test_update_crm_ticket_not_found(self, client: TestClient) -> None:
        r = client.patch("/crm/tickets/999999", headers=H, json={"status": "closed"})
        assert r.status_code == 404

    def test_escalate_crm_ticket_not_found(self, client: TestClient) -> None:
        r = client.post("/crm/tickets/999999/escalate", headers=H)
        assert r.status_code == 404

    # ── Notes duplicate path ──────────────────────────────────────────────────

    def test_create_note_then_duplicate(self, client: TestClient) -> None:
        payload = {"body": "Branch Coverage Note", "pinned": False}
        r1 = client.post("/crm/notes", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/notes", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_list_notes_filters(self, client: TestClient) -> None:
        r = client.get("/crm/notes?contact_id=1&deal_id=1&company_id=1", headers=H)
        assert r.status_code == 200

    # ── Quotes duplicate path and 404 ────────────────────────────────────────

    def test_create_quote_then_duplicate(self, client: TestClient) -> None:
        payload = {
            "title": "Dupe Quote Branch",
            "currency": "USD",
            "line_items": [{"description": "Service", "quantity": 1, "unit_price": 500, "discount_pct": 0}],
        }
        r1 = client.post("/crm/quotes", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/quotes", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_accept_quote_not_found(self, client: TestClient) -> None:
        r = client.post("/crm/quotes/999999/accept", headers=H)
        assert r.status_code == 404

    def test_list_quotes_with_status_filter(self, client: TestClient) -> None:
        r = client.get("/crm/quotes?status=draft", headers=H)
        assert r.status_code == 200

    # ── Invoice duplicate path ────────────────────────────────────────────────

    def test_create_invoice_then_duplicate(self, client: TestClient) -> None:
        payload = {
            "title": "Dupe Invoice Branch",
            "amount": 1500.0,
            "currency": "USD",
        }
        r1 = client.post("/crm/invoices", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/invoices", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_update_invoice_not_found(self, client: TestClient) -> None:
        r = client.patch("/crm/invoices/999999", headers=H, json={"status": "paid"})
        assert r.status_code == 404

    def test_list_invoices_with_status_filter(self, client: TestClient) -> None:
        r = client.get("/crm/invoices?status=pending", headers=H)
        assert r.status_code == 200

    # ── Workflow rule duplicate and 404 ──────────────────────────────────────

    def test_create_workflow_rule_then_duplicate(self, client: TestClient) -> None:
        payload = {
            "name": "Dupe Workflow Rule",
            "trigger": "contact.created",
            "action": "send_email",
        }
        r1 = client.post("/crm/workflow-rules", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/workflow-rules", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_trigger_workflow_rule_not_found(self, client: TestClient) -> None:
        r = client.post("/crm/workflow-rules/999999/trigger", headers=H)
        assert r.status_code == 404

    # ── Project duplicate and 404 ─────────────────────────────────────────────

    def test_create_project_then_duplicate(self, client: TestClient) -> None:
        payload = {"name": "Dupe Project Branch", "owner": "owner@branch.com"}
        r1 = client.post("/crm/projects", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/projects", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_update_project_not_found(self, client: TestClient) -> None:
        r = client.patch("/crm/projects/999999", headers=H, json={"status": "done"})
        assert r.status_code == 404

    def test_project_list_with_filters(self, client: TestClient) -> None:
        r = client.get("/crm/projects?status=planning&owner=owner@branch.com", headers=H)
        assert r.status_code == 200

    # ── Dedupe merge path with duplicate contacts (not dry-run) ─────────────

    def test_dedupe_contacts_real_merge(self, client: TestClient) -> None:
        from backend.fastapi.app.memory_stores import crm_contacts

        h_merge = {"X-API-Key": "test-api-key", "X-Tenant-Id": "crm-real-merge-tenant"}
        # Inject two contacts with the same email directly to bypass the CRM create-idempotency.
        crm_contacts.append({
            "id": 900001,
            "tenant_id": "crm-real-merge-tenant",
            "email": "dedupemerge@branch.com",
            "first_name": "Alice",
            "last_name": "One",
            "phone": "",
            "tags": [],
            "company": "",
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
        })
        crm_contacts.append({
            "id": 900002,
            "tenant_id": "crm-real-merge-tenant",
            "email": "dedupemerge@branch.com",
            "first_name": "Alice",
            "last_name": "Two",
            "phone": "+1-555-0001",
            "tags": ["vip"],
            "company": "Acme",
            "created_at": "2025-01-02T00:00:00+00:00",
            "updated_at": "2025-01-02T00:00:00+00:00",
        })
        r = client.post("/crm/contacts/dedupe", headers=h_merge, json={"dry_run": False})
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["dry_run"] is False
        assert data["merged_contacts"] >= 1

    # ── Task duplicate and 404 ────────────────────────────────────────────────

    def test_create_task_then_duplicate(self, client: TestClient) -> None:
        payload = {"title": "Dupe Task Branch", "priority": "medium", "status": "open"}
        r1 = client.post("/crm/tasks", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/tasks", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    def test_update_task_not_found(self, client: TestClient) -> None:
        r = client.patch("/crm/tasks/999999", headers=H, json={"status": "done"})
        assert r.status_code == 404

    def test_list_tasks_with_filters(self, client: TestClient) -> None:
        r = client.get("/crm/tasks?status=open&priority=medium&assigned_to=nobody&contact_id=1&deal_id=1", headers=H)
        assert r.status_code == 200

    # ── Webhook test 404 ──────────────────────────────────────────────────────

    def test_webhook_test_not_found(self, client: TestClient) -> None:
        r = client.post("/crm/webhooks/999999/test", headers=H)
        assert r.status_code == 404

    def test_webhook_test_success(self, client: TestClient) -> None:
        r1 = client.post(
            "/crm/webhooks",
            headers=H,
            json={"event": "task.completed", "target_url": "https://hooks.example.com/crm-test-success"},
        )
        webhook_id = r1.json()["webhook"]["id"]
        r2 = client.post(f"/crm/webhooks/{webhook_id}/test", headers=H)
        assert r2.status_code == 200
        assert r2.json()["delivery"]["status"] == "delivered"

    # ── Segment members 404 ────────────────────────────────────────────────────

    def test_get_segment_members_not_found(self, client: TestClient) -> None:
        r = client.get("/crm/segments/999999/members", headers=H)
        assert r.status_code == 404

    # ── Segment duplicate and members success ──────────────────────────────────

    def test_create_segment_then_duplicate(self, client: TestClient) -> None:
        payload = {"name": "Dupe Segment Branch", "filters": {"tags": ["vip"]}, "description": "branch test"}
        r1 = client.post("/crm/segments", headers=H, json=payload)
        assert r1.status_code in (200, 201)

        r2 = client.post("/crm/segments", headers=H, json=payload)
        assert r2.status_code in (200, 201)
        assert r2.json()["duplicate"] is True

    # ── Enroll in sequence success ─────────────────────────────────────────────

    def test_enroll_sequence_success(self, client: TestClient) -> None:
        r_seq = client.post(
            "/crm/email-sequences",
            headers=H,
            json={"name": "Enroll Test Seq", "steps": [{"day": 1, "subject": "Hi", "body": "Hello"}]},
        )
        seq_id = r_seq.json()["sequence"]["id"]
        r = client.post(f"/crm/email-sequences/{seq_id}/enroll?contact_id=1", headers=H)
        assert r.status_code in (200, 201)
        assert r.json()["sequence_id"] == seq_id

    def test_dedupe_merge_reassigns_deals_and_activities(self, client: TestClient) -> None:
        from backend.fastapi.app.memory_stores import crm_activities, crm_contacts, crm_deals

        tenant = "crm-dedupe-reassign-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

        crm_contacts.append(
            {
                "id": 910001,
                "tenant_id": tenant,
                "email": "merge2@branch.com",
                "first_name": "Core",
                "last_name": "Contact",
                "phone": "",
                "company": "",
                "tags": ["alpha"],
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
            }
        )
        crm_contacts.append(
            {
                "id": 910002,
                "tenant_id": tenant,
                "email": "merge2@branch.com",
                "first_name": "Dup",
                "last_name": "Contact",
                "phone": "+1-555-2222",
                "company": "Branch Co",
                "tags": ["beta"],
                "created_at": "2025-01-02T00:00:00+00:00",
                "updated_at": "2025-01-02T00:00:00+00:00",
            }
        )
        crm_deals.append(
            {
                "id": 910003,
                "tenant_id": tenant,
                "title": "Deal linked to duplicate",
                "contact_id": 910002,
                "value": 100.0,
                "created_at": "2025-01-02T00:00:00+00:00",
                "updated_at": "2025-01-02T00:00:00+00:00",
            }
        )
        crm_activities.append(
            {
                "id": 910004,
                "tenant_id": tenant,
                "type": "call",
                "contact_id": 910002,
                "created_at": "2025-01-02T00:00:00+00:00",
                "updated_at": "2025-01-02T00:00:00+00:00",
            }
        )

        r = client.post("/crm/contacts/dedupe", headers=headers, json={"dry_run": False})
        assert r.status_code == 200
        assert r.json()["merged_contacts"] >= 1

        merged = next(c for c in crm_contacts if c.get("tenant_id") == tenant and int(c.get("id", 0)) == 910001)
        assert merged.get("phone") == "+1-555-2222"
        assert merged.get("company") == "Branch Co"
        assert set(merged.get("tags", [])) == {"alpha", "beta"}

        deal = next(d for d in crm_deals if d.get("tenant_id") == tenant and int(d.get("id", 0)) == 910003)
        activity = next(a for a in crm_activities if a.get("tenant_id") == tenant and int(a.get("id", 0)) == 910004)
        assert int(deal.get("contact_id", 0)) == 910001
        assert int(activity.get("contact_id", 0)) == 910001

    def test_reports_kpis_window_and_datetime_parse_branches(self, client: TestClient) -> None:
        from backend.fastapi.app.memory_stores import crm_contacts, crm_deals, crm_leads, crm_tasks, tickets

        tenant = "crm-kpi-parse-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

        crm_contacts.extend(
            [
                {"id": 920001, "tenant_id": tenant, "email": "a@x.com", "created_at": "2025-01-01"},
                {"id": 920002, "tenant_id": tenant, "email": "b@x.com", "created_at": "not-a-date"},
                {"id": 920003, "tenant_id": tenant, "email": "c@x.com", "created_at": "2025-01-01T00:00:00"},
            ]
        )
        crm_deals.extend(
            [
                {
                    "id": 920010,
                    "tenant_id": tenant,
                    "title": "Won",
                    "stage": "closed_won",
                    "value": 1200,
                    "probability": 100,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": 920011,
                    "tenant_id": tenant,
                    "title": "Lost",
                    "stage": "closed_lost",
                    "value": 300,
                    "probability": 10,
                    "created_at": "bad-date",
                    "updated_at": "bad-date",
                },
            ]
        )
        crm_leads.extend(
            [
                {"id": 920020, "tenant_id": tenant, "title": "L1", "source": "web", "status": "converted", "created_at": "2025-01-01"},
                {"id": 920021, "tenant_id": tenant, "title": "L2", "source": "web", "status": "new", "created_at": "invalid"},
            ]
        )
        tickets.extend(
            [
                {"id": 920030, "tenant_id": tenant, "subject": "T1", "status": "open", "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"},
                {"id": 920031, "tenant_id": tenant, "subject": "T2", "status": "closed", "created_at": "bad", "updated_at": "bad"},
            ]
        )
        crm_tasks.extend(
            [
                {
                    "id": 920040,
                    "tenant_id": tenant,
                    "title": "Task 1",
                    "status": "open",
                    "priority": "medium",
                    "due_date": "2025-01-01",
                    "created_at": "2025-01-01",
                    "updated_at": "2025-01-01",
                },
                {
                    "id": 920041,
                    "tenant_id": tenant,
                    "title": "Task 2",
                    "status": "open",
                    "priority": "medium",
                    "due_date": "not-a-date",
                    "created_at": "not-a-date",
                    "updated_at": "not-a-date",
                },
            ]
        )

        r7 = client.get("/crm/reports/kpis?days=7", headers=headers)
        assert r7.status_code == 200
        assert r7.json()["window_days"] == 7

        r365 = client.get("/crm/reports/kpis?days=365", headers=headers)
        assert r365.status_code == 200
        assert r365.json()["window_days"] == 365

    def test_backup_next_full_rolls_to_next_week_when_candidate_is_past(self, client: TestClient) -> None:
        from backend.fastapi.app.memory_stores import crm_backup_snapshots

        tenant = "crm-backup-next-week-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        now = datetime.now(UTC)
        weekday = now.strftime("%A").lower()

        crm_backup_snapshots.append(
            {
                "id": 930001,
                "tenant_id": tenant,
                "type": "config",
                "incremental_minutes": 5,
                "full_backup_weekday": weekday,
                "full_backup_hour_utc": now.hour,
                "retention_days": 30,
                "enabled": True,
                "updated_at": now.isoformat(),
            }
        )

        r = client.get("/crm/ops/backup", headers=headers)
        assert r.status_code == 200
        next_full = datetime.fromisoformat(r.json()["next_runs"]["full_at"])
        # If candidate hour for today is <= now, route should schedule next week.
        assert (next_full - now).days >= 6

    def test_tasks_kanban_creates_dynamic_status_column(self, client: TestClient) -> None:
        from backend.fastapi.app.memory_stores import crm_tasks

        tenant = "crm-kanban-dynamic-status-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

        crm_tasks.append(
            {
                "id": 940001,
                "tenant_id": tenant,
                "title": "Blocked custom",
                "status": "blocked",
                "priority": "high",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )

        board = client.get("/crm/tasks/kanban", headers=headers)
        assert board.status_code == 200
        assert "blocked" in board.json()["kanban"]

    def test_create_ticket_with_sla_sets_deadlines(self, client: TestClient) -> None:
        tenant = "crm-ticket-sla-deadline-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

        sla = client.post(
            "/crm/sla-rules",
            headers=headers,
            json={
                "name": "P1 SLA",
                "applies_to": "tickets",
                "priority": "high",
                "first_response_hours": 1,
                "resolution_hours": 2,
            },
        )
        assert sla.status_code in (200, 201)

        ticket = client.post(
            "/crm/tickets",
            headers=headers,
            json={"subject": "SLA Deadline Test", "priority": "high", "status": "open"},
        )
        assert ticket.status_code in (200, 201)
        ticket_row = ticket.json()["ticket"]
        assert ticket_row.get("first_response_deadline")
        assert ticket_row.get("resolution_deadline")

    def test_get_ticket_not_found(self, client: TestClient) -> None:
        r = client.get("/crm/tickets/999999", headers=H)
        assert r.status_code == 404

    def test_send_campaign_not_found(self, client: TestClient) -> None:
        r = client.post("/crm/campaigns/999999/send", headers=H)
        assert r.status_code == 404

    def test_update_invoice_with_paid_at_branch(self, client: TestClient) -> None:
        tenant = "crm-invoice-paid-at-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

        created = client.post(
            "/crm/invoices",
            headers=headers,
            json={"title": "Invoice PaidAt", "amount": 99.0, "currency": "USD"},
        )
        assert created.status_code in (200, 201)
        invoice_id = created.json()["invoice"]["id"]

        patched = client.patch(
            f"/crm/invoices/{invoice_id}",
            headers=headers,
            json={"status": "paid", "paid_at": "2025-01-01T00:00:00+00:00"},
        )
        assert patched.status_code == 200
        assert patched.json()["invoice"].get("paid_at") == "2025-01-01T00:00:00+00:00"

    def test_workflow_trigger_success_branch(self, client: TestClient) -> None:
        tenant = "crm-workflow-trigger-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

        created = client.post(
            "/crm/workflow-rules",
            headers=headers,
            json={"name": "Trigger Me", "trigger": "contact.created", "action": "send_email"},
        )
        assert created.status_code in (200, 201)
        rule_id = created.json()["workflow_rule"]["id"]

        triggered = client.post(f"/crm/workflow-rules/{rule_id}/trigger", headers=headers)
        assert triggered.status_code == 200
        assert int(triggered.json()["workflow_rule"].get("run_count", 0)) >= 1

    def test_update_project_fields_and_board_dynamic_column(self, client: TestClient) -> None:
        tenant = "crm-project-patch-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

        created = client.post(
            "/crm/projects",
            headers=headers,
            json={"name": "Project A", "owner": "ops@example.com", "status": "planning"},
        )
        assert created.status_code in (200, 201)
        project_id = created.json()["project"]["id"]

        patched = client.patch(
            f"/crm/projects/{project_id}",
            headers=headers,
            json={
                "description": "Updated desc",
                "owner": "owner2@example.com",
                "due_date": "2025-12-31",
                "status": "qa review",
            },
        )
        assert patched.status_code == 200
        row = patched.json()["project"]
        assert row.get("description") == "Updated desc"
        assert row.get("owner") == "owner2@example.com"
        assert row.get("due_date") == "2025-12-31"

        board = client.get("/crm/projects/board", headers=headers)
        assert board.status_code == 200
        assert "qa_review" in board.json()["board"]

    def test_custom_entity_type_duplicate_branch(self, client: TestClient) -> None:
        tenant = "crm-entity-type-duplicate-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        payload = {"key": "books", "name": "Books", "description": "Custom type", "fields": [{"key": "title", "type": "text"}]}

        first = client.post("/crm/custom-entities/types", headers=headers, json=payload)
        assert first.status_code == 200

        second = client.post("/crm/custom-entities/types", headers=headers, json=payload)
        assert second.status_code == 200
        assert second.json()["duplicate"] is True

    def test_automation_recipe_duplicate_and_not_found_run(self, client: TestClient) -> None:
        tenant = "crm-automation-duplicate-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        payload = {"name": "Auto R", "trigger": "deal.created", "action": "notify", "config": {}, "enabled": True}

        first = client.post("/crm/automation/recipes", headers=headers, json=payload)
        assert first.status_code == 200

        second = client.post("/crm/automation/recipes", headers=headers, json=payload)
        assert second.status_code == 200
        assert second.json()["duplicate"] is True

        missing = client.post("/crm/automation/recipes/999999/run", headers=headers)
        assert missing.status_code == 404

    def test_api_token_duplicate_branch(self, client: TestClient) -> None:
        tenant = "crm-token-duplicate-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        payload = {"name": "Server Token", "scopes": ["contacts.read", "contacts.write"]}

        first = client.post("/crm/api-tokens", headers=headers, json=payload)
        assert first.status_code == 200

        second = client.post("/crm/api-tokens", headers=headers, json=payload)
        assert second.status_code == 200
        assert second.json()["duplicate"] is True

    def test_executive_analytics_revenue_and_anomalies(self, client: TestClient) -> None:
        tenant = "crm-exec-anomaly-tenant"
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}

        contact = client.post(
            "/crm/contacts",
            headers=headers,
            json={"email": "exec@branch.com", "first_name": "Exec", "last_name": "Case"},
        )
        assert contact.status_code in (200, 201)
        contact_id = contact.json()["contact"]["id"]

        # Seed open and closed won deals to drive revenue trend + pipeline congestion.
        client.post(
            "/crm/deals",
            headers=headers,
            json={
                "title": "Won Deal",
                "value": 1000,
                "stage": "closed_won",
                "probability": 100,
                "contact_id": contact_id,
                "close_date": datetime.now(UTC).date().isoformat(),
            },
        )
        client.post(
            "/crm/deals",
            headers=headers,
            json={"title": "Neg 1", "value": 300, "stage": "negotiation", "probability": 50, "contact_id": contact_id},
        )
        client.post(
            "/crm/deals",
            headers=headers,
            json={"title": "Neg 2", "value": 320, "stage": "negotiation", "probability": 60, "contact_id": contact_id},
        )

        # Escalation ratio and overdue task anomaly inputs.
        ticket_open = client.post(
            "/crm/tickets",
            headers=headers,
            json={"subject": "Escalated", "priority": "high", "status": "open"},
        )
        assert ticket_open.status_code in (200, 201)
        ticket_id = ticket_open.json()["ticket"]["id"]
        client.post(f"/crm/tickets/{ticket_id}/escalate", headers=headers)
        client.post(
            "/crm/tickets",
            headers=headers,
            json={"subject": "Normal", "priority": "low", "status": "open"},
        )
        client.post(
            "/crm/tasks",
            headers=headers,
            json={"title": "Overdue Task", "priority": "high", "status": "open", "due_date": "2020-01-01"},
        )

        analytics = client.get("/crm/reports/executive-analytics?days=365", headers=headers)
        assert analytics.status_code == 200
        data = analytics.json()
        anomaly_types = {a["type"] for a in data["anomalies"]}
        assert "task_overdue" in anomaly_types
        assert "support_risk" in anomaly_types
        assert "pipeline_congestion" in anomaly_types
        assert len(data["charts"]["monthly_closed_won"]) >= 1
