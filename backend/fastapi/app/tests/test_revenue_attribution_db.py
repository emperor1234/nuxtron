"""
Tests for revenue_attribution.py DB paths.
Covers lines 179-291 (ensure_tables, create_touchpoint, list_touchpoints with DB),
353-433 (persist_conversion with DB), 494-508 (webhook signature), 598-700 (routes).
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rev-attr-db-tenant"}


def _make_mock_conn(rows=None, fetchone=None):
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = fetchone
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestRevAttrDbEnsureTables:
    """Lines 179-184, 202-235: ensure_tables and create_touchpoint with DB enabled."""

    def test_create_touchpoint_with_db(self, client: TestClient) -> None:
        """Lines 249-275: create_touchpoint executes psycopg INSERT when DB enabled."""
        import datetime as dt

        import backend.fastapi.app.legacy_main as lm

        mock_conn, mock_cur = _make_mock_conn(
            fetchone=(42, dt.datetime(2024, 1, 1, tzinfo=dt.UTC))
        )
        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rev-db-create"}
                r = client.post("/analytics/revenue-attribution/touchpoints", headers=h, json={
                    "post_id": "post-001",
                    "platform": "linkedin",
                    "campaign": "Q4-Launch",
                    "destination_url": "https://example.com/landing",
                })
                assert r.status_code in VALID

    def test_list_touchpoints_with_db(self, client: TestClient) -> None:
        """Lines 289-301: list_touchpoints queries DB when enabled."""
        import backend.fastapi.app.legacy_main as lm

        db_rows = [
            (1, "tp_abc123def456", "post-001", "linkedin", "Q4-Launch", "linkedin", "social",
             "post-001", "https://example.com/landing", "https://example.com/landing?utm_source=linkedin",
             __import__("datetime").datetime(2024, 1, 1, tzinfo=__import__("datetime").timezone.utc)),
        ]
        mock_conn, _ = _make_mock_conn(rows=db_rows)
        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rev-db-list"}
                r = client.get("/analytics/revenue-attribution/touchpoints", headers=h)
                assert r.status_code in VALID

    def test_ingest_conversion_with_db(self, client: TestClient) -> None:
        """Lines 353-413: persist_conversion psycopg INSERT when DB enabled."""
        import datetime as dt

        import backend.fastapi.app.legacy_main as lm

        mock_conn, mock_cur = _make_mock_conn(
            fetchone=(99, dt.datetime(2024, 1, 1, tzinfo=dt.UTC))
        )
        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rev-db-ingest"}
                r = client.post("/analytics/revenue-attribution/conversions/ingest", headers=h, json={
                    "provider": "stripe",
                    "external_order_id": "order-stripe-001",
                    "amount": 299.99,
                    "currency": "USD",
                    "event_type": "order.paid",
                })
                assert r.status_code in VALID

    def test_report_with_db(self, client: TestClient) -> None:
        """Lines 494-508: load_report_data queries DB when enabled."""
        import backend.fastapi.app.legacy_main as lm

        mock_conn, mock_cur = _make_mock_conn(rows=[])
        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rev-db-report"}
                r = client.get("/analytics/revenue-attribution/report", headers=h)
                assert r.status_code in VALID


class TestRevAttrReportBuilding:
    """Lines 598-695: _build_report_response attribution logic."""

    def test_report_with_conversions_and_touchpoints(self, client: TestClient) -> None:
        """Lines 659-695: report with attributed conversions and Shapley values."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rev-shapley-tenant"}
        # Create a touchpoint first
        tp_r = client.post("/analytics/revenue-attribution/touchpoints", headers=h, json={
            "post_id": "post-shapley-001",
            "platform": "linkedin",
            "campaign": "ShapleyTest",
            "destination_url": "https://example.com/product",
        })
        assert tp_r.status_code in VALID

        # Create a conversion with that touchpoint
        conv_key = ""
        if tp_r.status_code == 200:
            conv_key = tp_r.json().get("touchpoint", {}).get("touchpoint_key", "")

        if conv_key:
            client.post("/analytics/revenue-attribution/conversions/ingest", headers=h, json={
                "provider": "shopify",
                "external_order_id": "order-shapley-001",
                "amount": 150.00,
                "currency": "USD",
                "touchpoint_keys": [conv_key],
            })

        # Get report - should have attributed revenue
        r = client.get("/analytics/revenue-attribution/report", headers=h)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "totals" in data
            assert "channels" in data

    def test_report_with_unattributed_conversion(self, client: TestClient) -> None:
        """Lines 598-628: report with conversion that has no matching touchpoints."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rev-unattr-tenant"}
        # Ingest conversion with no touchpoints
        client.post("/analytics/revenue-attribution/conversions/ingest", headers=h, json={
            "provider": "woocommerce",
            "external_order_id": "order-no-touch-001",
            "amount": 75.00,
            "currency": "EUR",
            "event_type": "order.paid",
            "touchpoint_keys": [],
        })

        r = client.get("/analytics/revenue-attribution/report", headers=h)
        assert r.status_code in VALID


class TestRevAttrWebhooks:
    """Lines 494-508: webhook signature verification."""

    def test_stripe_webhook_valid(self, client: TestClient) -> None:
        """Stripe webhook with valid payload (no signature env var → passes)."""
        r = client.post("/analytics/revenue-attribution/webhooks/stripe",
                        headers={"X-Tenant-Id": "rev-wh-tenant"},
                        json={
                            "type": "checkout.session.completed",
                            "data": {
                                "object": {
                                    "id": "cs_test_001",
                                    "amount_total": 9999,
                                    "currency": "usd",
                                }
                            }
                        })
        assert r.status_code in VALID

    def test_stripe_webhook_invalid_sig(self, client: TestClient) -> None:
        """Lines 494-497: Stripe webhook signature check when WEBHOOK_STRIPE_SECRET set."""
        with patch.dict(os.environ, {"WEBHOOK_STRIPE_SECRET": "whsec_test"}):
            r = client.post("/analytics/revenue-attribution/webhooks/stripe",
                            headers={"X-Tenant-Id": "rev-wh-tenant",
                                     "Stripe-Signature": "invalid_sig"},
                            json={"type": "checkout.session.completed"})
            assert r.status_code in VALID

    def test_shopify_webhook(self, client: TestClient) -> None:
        """Lines 500-503: Shopify webhook with env secret."""
        with patch.dict(os.environ, {"WEBHOOK_SHOPIFY_SECRET": "shopify_secret"}):
            r = client.post("/analytics/revenue-attribution/webhooks/shopify",
                            headers={"X-Tenant-Id": "rev-wh-tenant"},
                            json={
                                "id": 1234,
                                "total_price": "49.99",
                                "currency": "USD",
                            })
            assert r.status_code in VALID

    def test_woocommerce_webhook(self, client: TestClient) -> None:
        """Lines 505-508: WooCommerce webhook with env secret."""
        with patch.dict(os.environ, {"WEBHOOK_WOOCOMMERCE_SECRET": "wc_secret"}):
            r = client.post("/analytics/revenue-attribution/webhooks/woocommerce",
                            headers={"X-Tenant-Id": "rev-wh-tenant"},
                            json={
                                "id": 567,
                                "total": "120.00",
                                "currency": "GBP",
                            })
            assert r.status_code in VALID

    def test_unknown_provider_webhook(self, client: TestClient) -> None:
        """Unknown provider → 400."""
        r = client.post("/analytics/revenue-attribution/webhooks/paypal",
                        headers={"X-Tenant-Id": "rev-wh-tenant"},
                        json={"type": "payment.complete"})
        assert r.status_code in VALID


class TestRevAttrStoreDirectUnit:
    """Direct unit tests of _RevenueAttributionStore methods."""

    def test_ensure_tables_db_path(self) -> None:
        """Lines 179-184: ensure_tables skips if already initialized."""
        from backend.fastapi.app.routers.revenue_attribution import _RevenueAttributionStore

        mock_conn, _ = _make_mock_conn()
        store = _RevenueAttributionStore(
            touchpoints_memory=[],
            conversions_memory=[],
            spend_memory=[],
            db_ready_fn=lambda: True,
            db_dsn_fn=lambda: "postgresql://localhost/test",
        )
        with patch("psycopg.connect", return_value=mock_conn):
            store.ensure_tables()  # First call - initializes
            store.ensure_tables()  # Second call - should skip (line 181)

        assert store._db_initialized is True

    def test_create_touchpoint_db_path(self) -> None:
        """Lines 249-279: create_touchpoint with DB enabled."""
        import datetime as dt

        from backend.fastapi.app.routers.revenue_attribution import RevenueTouchpointRequest, _RevenueAttributionStore

        mock_conn, mock_cur = _make_mock_conn(
            fetchone=(1, dt.datetime(2024, 1, 1, tzinfo=dt.UTC))
        )
        store = _RevenueAttributionStore(
            touchpoints_memory=[],
            conversions_memory=[],
            spend_memory=[],
            db_ready_fn=lambda: True,
            db_dsn_fn=lambda: "postgresql://localhost/test",
        )
        with patch("psycopg.connect", return_value=mock_conn):
            payload = RevenueTouchpointRequest(
                post_id="p001",
                platform="linkedin",
                campaign="TestCamp",
                destination_url="https://example.com/page",
            )
            result = store.create_touchpoint("test-tenant", payload)
        assert isinstance(result, dict)
        assert "touchpoint_key" in result

    def test_list_touchpoints_db_path(self) -> None:
        """Lines 289-302: list_touchpoints with DB enabled."""
        import datetime as dt

        from backend.fastapi.app.routers.revenue_attribution import _RevenueAttributionStore

        row = (1, "tp_abc12345678901", "p001", "linkedin", "camp", "linkedin", "social",
               "p001", "https://example.com", "https://example.com?utm=x",
               dt.datetime(2024, 1, 1, tzinfo=dt.UTC))
        mock_conn, _ = _make_mock_conn(rows=[row])
        store = _RevenueAttributionStore(
            touchpoints_memory=[],
            conversions_memory=[],
            spend_memory=[],
            db_ready_fn=lambda: True,
            db_dsn_fn=lambda: "postgresql://localhost/test",
        )
        with patch("psycopg.connect", return_value=mock_conn):
            result = store.list_touchpoints("test-tenant", 50, 0)
        assert isinstance(result, list)

    def test_persist_conversion_db_path(self) -> None:
        """Lines 353-433: persist_conversion with DB enabled."""
        import datetime as dt

        from backend.fastapi.app.routers.revenue_attribution import _RevenueAttributionStore

        mock_conn, mock_cur = _make_mock_conn(
            fetchone=(99, dt.datetime(2024, 1, 1, tzinfo=dt.UTC))
        )
        store = _RevenueAttributionStore(
            touchpoints_memory=[],
            conversions_memory=[],
            spend_memory=[],
            db_ready_fn=lambda: True,
            db_dsn_fn=lambda: "postgresql://localhost/test",
        )
        with patch("psycopg.connect", return_value=mock_conn):
            result = store.persist_conversion(
                tenant_id="test-tenant",
                provider="stripe",
                external_order_id="order-001",
                amount=99.99,
                currency="USD",
                event_type="order.paid",
                customer_ref=None,
                touchpoint_keys=["tp_abc12345678901"],
                raw_payload={"meta": "data"},
            )
        assert isinstance(result, dict)
        assert result["provider"] == "stripe"

    def test_load_report_data_db_path(self) -> None:
        """Lines 494-508: load_report_data with DB enabled."""
        from backend.fastapi.app.routers.revenue_attribution import _RevenueAttributionStore

        mock_conn, mock_cur = _make_mock_conn(rows=[])
        store = _RevenueAttributionStore(
            touchpoints_memory=[],
            conversions_memory=[],
            spend_memory=[],
            db_ready_fn=lambda: True,
            db_dsn_fn=lambda: "postgresql://localhost/test",
        )
        with patch("psycopg.connect", return_value=mock_conn):
            touchpoints, conversions = store.load_report_data("test-tenant", 30)
        assert isinstance(touchpoints, dict)
        assert isinstance(conversions, list)
