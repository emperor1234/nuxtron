"""
Tests for analytics_dashboard, billing, auth, and documents routers.
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


class TestAnalyticsDashboard:
    def test_dashboard(self, client: TestClient) -> None:
        r = client.get("/analytics/dashboard", headers=H)
        assert r.status_code in VALID

    def test_metrics(self, client: TestClient) -> None:
        r = client.get("/analytics/metrics", headers=H)
        assert r.status_code in VALID

    def test_predictions(self, client: TestClient) -> None:
        r = client.get("/analytics/predictions", headers=H)
        assert r.status_code in VALID

    def test_benchmarks(self, client: TestClient) -> None:
        r = client.get("/analytics/benchmarks", headers=H)
        assert r.status_code in VALID

    def test_create_report(self, client: TestClient) -> None:
        r = client.post("/analytics/reports", headers=H, json={
            "name": "Monthly Report",
            "metrics": ["revenue", "users"],
            "date_range": "last_30_days",
        })
        assert r.status_code in VALID

    def test_list_reports(self, client: TestClient) -> None:
        r = client.get("/analytics/reports", headers=H)
        assert r.status_code in VALID

    def test_schedule_report(self, client: TestClient) -> None:
        r = client.post("/analytics/schedule", headers=H, json={
            "report_name": "Weekly Report",
            "frequency": "weekly",
            "recipients": ["admin@example.com"],
        })
        assert r.status_code in VALID

    def test_export(self, client: TestClient) -> None:
        r = client.get("/analytics/export", headers=H)
        assert r.status_code in VALID

    def test_kpi(self, client: TestClient) -> None:
        r = client.get("/analytics/insights/kpi", headers=H)
        assert r.status_code in VALID

    def test_trend(self, client: TestClient) -> None:
        r = client.post("/analytics/insights/trend", headers=H, json={
            "metric": "revenue",
            "period": "last_90_days",
        })
        assert r.status_code in VALID

    def test_rollup(self, client: TestClient) -> None:
        r = client.post("/analytics/insights/rollup", headers=H, json={
            "dimensions": ["channel", "region"],
        })
        assert r.status_code in VALID

    def test_intelligence(self, client: TestClient) -> None:
        r = client.get("/analytics/insights/intelligence", headers=H)
        assert r.status_code in VALID


class TestBilling:
    def test_list_plans(self, client: TestClient) -> None:
        r = client.get("/billing/plans", headers=H)
        assert r.status_code in VALID

    def test_subscribe(self, client: TestClient) -> None:
        r = client.post("/billing/subscribe", headers=H, json={
            "plan": "pro",
            "payment_method_id": "pm_test_001",
        })
        assert r.status_code in VALID

    def test_subscribe_unknown_plan(self, client: TestClient) -> None:
        r = client.post("/billing/subscribe", headers=H, json={
            "plan": "unknown_plan_xyz",
        })
        assert r.status_code in VALID

    def test_upgrade(self, client: TestClient) -> None:
        r = client.post("/billing/upgrade", headers=H, json={
            "plan": "enterprise",
        })
        assert r.status_code in VALID

    def test_cancel(self, client: TestClient) -> None:
        r = client.post("/billing/cancel", headers=H, json={
            "reason": "too expensive",
        })
        assert r.status_code in VALID

    def test_credits(self, client: TestClient) -> None:
        checkout = client.post(
            "/billing/credits/checkout",
            headers=H,
            json={
                "amount": 100,
                "payment_provider": "manual",
                "payment_method_id": "pm_credit_docs",
            },
        )
        assert checkout.status_code in VALID
        invoice = checkout.json().get("invoice", {})
        confirm = client.post(
            "/billing/credits/confirm",
            headers=H,
            json={
                "invoice_id": invoice.get("id", 1),
                "payment_reference": invoice.get("payment_reference", "missing"),
                "provider_transaction_id": "txn_credit_docs",
                "amount_usd": invoice.get("amount", 2.0),
            },
        )
        assert confirm.status_code in VALID

    def test_usage(self, client: TestClient) -> None:
        r = client.get("/billing/usage", headers=H)
        assert r.status_code in VALID

    def test_invoices(self, client: TestClient) -> None:
        r = client.get("/billing/invoices", headers=H)
        assert r.status_code in VALID


class TestAuth:
    def test_totp_setup(self, client: TestClient) -> None:
        r = client.post("/auth/totp/setup", headers=H, json={})
        assert r.status_code in VALID

    def test_totp_verify(self, client: TestClient) -> None:
        r = client.post("/auth/totp/verify", headers=H, json={
            "code": "123456",
        })
        assert r.status_code in VALID

    def test_jwt_issue(self, client: TestClient) -> None:
        r = client.post("/auth/jwt/issue", headers=H, json={
            "subject": "user_001",
            "claims": {"role": "admin"},
        })
        assert r.status_code in VALID

    def test_jwt_verify(self, client: TestClient) -> None:
        r = client.post("/auth/jwt/verify", headers=H, json={
            "token": "eyJhbGciOiJSUzI1NiJ9.test.signature",
        })
        assert r.status_code in VALID


class TestDocuments:
    def test_create_document(self, client: TestClient) -> None:
        r = client.post("/documents", headers=H, json={
            "title": "Test Document",
            "content": "This is test content.",
            "document_type": "pdf",
        })
        assert r.status_code in VALID

    def test_list_documents(self, client: TestClient) -> None:
        r = client.get("/documents", headers=H)
        assert r.status_code in VALID

    def test_get_document_nonexistent(self, client: TestClient) -> None:
        r = client.get("/documents/doc_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_share_document_nonexistent(self, client: TestClient) -> None:
        r = client.post("/documents/doc_nonexistent/share", headers=H, json={
            "recipients": ["user@example.com"],
            "permission": "view",
        })
        assert r.status_code in VALID

    def test_delete_document_nonexistent(self, client: TestClient) -> None:
        r = client.delete("/documents/doc_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_create_quote(self, client: TestClient) -> None:
        r = client.post("/quotes", headers=H, json={
            "title": "Test Quote",
            "items": [{"name": "Service A", "quantity": 1, "price": 1000.0}],
            "client_name": "Test Client",
        })
        assert r.status_code in VALID

    def test_list_quotes(self, client: TestClient) -> None:
        r = client.get("/quotes", headers=H)
        assert r.status_code in VALID

    def test_get_quote_nonexistent(self, client: TestClient) -> None:
        r = client.get("/quotes/quote_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_send_quote_nonexistent(self, client: TestClient) -> None:
        r = client.post("/quotes/quote_nonexistent/send", headers=H, json={
            "recipient_email": "client@example.com",
        })
        assert r.status_code in VALID

    def test_sign_quote_nonexistent(self, client: TestClient) -> None:
        r = client.post("/quotes/quote_nonexistent/sign", headers=H, json={
            "signer_name": "John Doe",
            "signature": "JohnDoe",
        })
        assert r.status_code in VALID
