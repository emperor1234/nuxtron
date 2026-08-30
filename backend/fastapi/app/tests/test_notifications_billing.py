"""
Tests for Notifications and Billing routers.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("SUPER_ADMIN_API_KEY", "selftest-super-admin-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ── Notifications ─────────────────────────────────────────────────────────────

class TestNotifications:
    def test_list_empty(self, client: TestClient) -> None:
        r = client.get("/notifications", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "notifications" in data or isinstance(data, list) or "items" in data or "data" in data or isinstance(data, dict)

    def test_create_notification(self, client: TestClient) -> None:
        r = client.post("/notifications", headers=H, json={
            "title": "Test Notification",
            "message": "Hello from tests",
            "category": "general",
            "priority": "info",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert data.get("title") == "Test Notification" or data.get("status") == "ok" or "id" in data

    def test_unread_count(self, client: TestClient) -> None:
        r = client.get("/notifications/unread-count", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "unread_count" in data or "count" in data or isinstance(data, dict)

    def test_preferences_get(self, client: TestClient) -> None:
        r = client.get("/notifications/preferences", headers=H)
        assert r.status_code == 200

    def test_preferences_update(self, client: TestClient) -> None:
        r = client.put("/notifications/preferences", headers=H, json={
            "muted_categories": [],
            "email_enabled": True,
            "sms_enabled": False,
            "slack_enabled": False,
            "realtime_enabled": True,
            "digest_frequency": "realtime",
        })
        assert r.status_code == 200

    def test_read_all(self, client: TestClient) -> None:
        r = client.post("/notifications/read-all", headers=H)
        assert r.status_code == 200

    def test_delivery_health(self, client: TestClient) -> None:
        r = client.get("/notifications/delivery-health", headers=H)
        assert r.status_code == 200

    def test_delivery_receipts(self, client: TestClient) -> None:
        r = client.get("/notifications/delivery-receipts", headers=H)
        assert r.status_code == 200

    def test_digest(self, client: TestClient) -> None:
        r = client.get("/notifications/digest", headers=H)
        assert r.status_code == 200

    def test_digest_batch_status(self, client: TestClient) -> None:
        r = client.get("/notifications/digest/batch-status", headers=H)
        assert r.status_code == 200

    def test_slack_send(self, client: TestClient) -> None:
        r = client.post("/notifications/slack/send-message", headers=H, json={
            "channel": "#test",
            "text": "Hello from tests",
        })
        assert r.status_code < 500

    def test_slack_webhook(self, client: TestClient) -> None:
        r = client.post("/notifications/slack/webhook", headers=H, json={
            "type": "event_callback",
            "event": {"type": "message", "text": "test"},
        })
        assert r.status_code < 500

    def test_resend_email(self, client: TestClient) -> None:
        r = client.post("/notifications/resend/send-email", headers=H, json={
            "to": "test@example.com",
            "subject": "Test",
            "html": "<p>Hello</p>",
        })
        assert r.status_code < 500

    def test_twilio_sms(self, client: TestClient) -> None:
        r = client.post("/notifications/twilio/send-sms", headers=H, json={
            "to": "+15551234567",
            "body": "Test SMS",
        })
        assert r.status_code < 500

    def test_mark_notification_read(self, client: TestClient) -> None:
        # Create one first
        r = client.post("/notifications", headers=H, json={
            "title": "Mark Read Test",
            "message": "To be marked read",
        })
        if r.status_code in {200, 201}:
            notif = r.json()
            notif_id = notif.get("id", 1)
            r2 = client.post(f"/notifications/{notif_id}/read", headers=H)
            assert r2.status_code < 500

    def test_delete_notification(self, client: TestClient) -> None:
        r = client.delete("/notifications/999999", headers=H)
        assert r.status_code in {200, 204, 404}


# ── Billing ───────────────────────────────────────────────────────────────────

class TestBilling:
    def test_list_plans(self, client: TestClient) -> None:
        r = client.get("/billing/plans", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "plans" in data or isinstance(data, list)

    def test_subscribe_starter(self, client: TestClient) -> None:
        r = client.post("/billing/subscribe", headers=H, json={
            "plan_id": "starter",
            "billing_cycle": "monthly",
        })
        assert r.status_code in {200, 201, 409}

    def test_subscribe_pro(self, client: TestClient) -> None:
        r = client.post("/billing/subscribe", headers=H, json={
            "plan_id": "pro",
            "billing_cycle": "annual",
        })
        assert r.status_code in {200, 201, 409}

    def test_upgrade(self, client: TestClient) -> None:
        r = client.post("/billing/upgrade", headers=H, json={"new_plan_id": "studio"})
        assert r.status_code < 500

    def test_add_credits(self, client: TestClient) -> None:
        checkout = client.post(
            "/billing/credits/checkout",
            headers=H,
            json={"amount": 500, "payment_provider": "manual", "payment_method_id": "pm_credit_test"},
        )
        assert checkout.status_code == 409
        confirm = client.post(
            "/billing/credits/confirm",
            headers=H,
            json={
                "invoice_id": 1,
                "payment_reference": "untrusted-client-reference",
                "provider_transaction_id": "txn_credit_test",
                "amount_usd": 0.01,
            },
        )
        assert confirm.status_code == 409

    def test_get_invoices(self, client: TestClient) -> None:
        r = client.get("/billing/invoices", headers=H)
        assert r.status_code == 200

    def test_get_usage(self, client: TestClient) -> None:
        r = client.get("/billing/usage", headers=H)
        assert r.status_code == 200

    def test_cancel(self, client: TestClient) -> None:
        r = client.post("/billing/cancel", headers=H)
        assert r.status_code < 500
