"""
Tests for revenue_attribution.py router endpoints.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 400, 401, 403, 404, 409, 422, 500)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestTouchpoints:
    def test_create_touchpoint_valid(self, client: TestClient) -> None:
        r = client.post(
            "/analytics/revenue-attribution/touchpoints",
            headers=HEADERS,
            json={
                "name": "Email Campaign",
                "channel": "email",
                "destination_url": "https://example.com/landing?utm_source=test",
                "utm_source": "email",
                "utm_medium": "newsletter",
                "utm_campaign": "spring2025",
                "utm_content": "banner_a",
            },
        )
        assert r.status_code in VALID

    def test_create_touchpoint_missing_name(self, client: TestClient) -> None:
        r = client.post(
            "/analytics/revenue-attribution/touchpoints",
            headers=HEADERS,
            json={"channel": "email"},
        )
        assert r.status_code == 422

    def test_list_touchpoints(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/touchpoints", headers=HEADERS)
        assert r.status_code in VALID

    def test_list_unauthenticated(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/touchpoints")
        assert r.status_code in (401, 403)


class TestConversionIngest:
    def test_ingest_valid(self, client: TestClient) -> None:
        r = client.post(
            "/analytics/revenue-attribution/conversions/ingest",
            headers=HEADERS,
            json={
                "provider": "stripe",
                "external_order_id": "order_123",
                "amount": 99.99,
                "currency": "USD",
                "event_type": "order.paid",
            },
        )
        assert r.status_code in VALID

    def test_ingest_missing_required(self, client: TestClient) -> None:
        r = client.post(
            "/analytics/revenue-attribution/conversions/ingest",
            headers=HEADERS,
            json={"provider": "stripe"},
        )
        assert r.status_code == 422

    def test_ingest_with_touchpoints(self, client: TestClient) -> None:
        r = client.post(
            "/analytics/revenue-attribution/conversions/ingest",
            headers=HEADERS,
            json={
                "provider": "paypal",
                "external_order_id": "pp_456",
                "amount": 49.0,
                "touchpoint_keys": ["tp_abc123"],
            },
        )
        assert r.status_code in VALID


class TestWebhooks:
    def test_stripe_webhook_no_sig(self, client: TestClient) -> None:
        r = client.post(
            "/analytics/revenue-attribution/webhooks/stripe",
            headers={**HEADERS, "stripe-signature": ""},
            content=b'{"type":"charge.succeeded"}',
        )
        assert r.status_code in VALID

    def test_stripe_webhook_invalid_sig(self, client: TestClient) -> None:
        r = client.post(
            "/analytics/revenue-attribution/webhooks/stripe",
            headers={**HEADERS, "stripe-signature": "t=123,v1=invalid"},
            content=b'{"type":"charge.succeeded"}',
        )
        assert r.status_code in VALID


class TestAttributionReport:
    def test_get_report(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/report", headers=HEADERS)
        assert r.status_code in VALID

    def test_get_report_with_params(self, client: TestClient) -> None:
        r = client.get(
            "/analytics/revenue-attribution/report?days=30&model=last_click",
            headers=HEADERS,
        )
        assert r.status_code in VALID

    def test_get_report_unauthenticated(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/report")
        assert r.status_code in (401, 403)
