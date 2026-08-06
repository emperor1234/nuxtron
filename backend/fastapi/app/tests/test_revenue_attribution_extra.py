"""
Tests for revenue_attribution.py pure helper functions.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
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


class TestExtractTouchpoints:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_touchpoints
        return _extract_touchpoints

    def test_finds_pattern_in_string(self) -> None:
        fn = self._fn()
        result = fn("clicked tp_abcdef12 and also tp_xyz98765")
        assert "tp_abcdef12" in result
        assert "tp_xyz98765" in result

    def test_finds_in_nested_dict(self) -> None:
        fn = self._fn()
        result = fn({"a": {"b": "tp_abcdef12"}})
        assert "tp_abcdef12" in result

    def test_finds_in_list(self) -> None:
        fn = self._fn()
        result = fn(["tp_abcdef12", "tp_xyz98765"])
        assert "tp_abcdef12" in result

    def test_empty_returns_empty(self) -> None:
        fn = self._fn()
        assert fn({}) == []
        assert fn([]) == []
        assert fn("no touchpoints here") == []

    def test_finds_in_url_query_param(self) -> None:
        fn = self._fn()
        result = fn("https://example.com/path?nux_touchpoint=tp_abcde12345&other=val")
        assert "tp_abcde12345" in result

    def test_deduplicates(self) -> None:
        fn = self._fn()
        result = fn(["tp_abcdef12", "tp_abcdef12"])
        assert result.count("tp_abcdef12") == 1

    def test_returns_sorted(self) -> None:
        fn = self._fn()
        result = fn("tp_zzzzzzz1 tp_aaaaaaa1")
        assert result == sorted(result)


class TestInjectUtm:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _inject_utm
        return _inject_utm

    def test_adds_utm_params(self) -> None:
        fn = self._fn()
        result = fn(
            url="https://example.com/page",
            source="twitter",
            medium="social",
            campaign="spring sale",
            content="banner ad",
            touchpoint_key="tp_abcdef12",
        )
        assert "utm_source=twitter" in result
        assert "utm_medium=social" in result
        assert "utm_campaign=spring_sale" in result
        assert "utm_content=banner_ad" in result
        assert "nux_touchpoint=tp_abcdef12" in result

    def test_raises_on_invalid_url(self) -> None:
        import fastapi
        fn = self._fn()
        with pytest.raises(fastapi.HTTPException) as exc_info:
            fn(
                url="not-a-url",
                source="test",
                medium="email",
                campaign="test",
                content="test",
                touchpoint_key="tp_abcdef12",
            )
        assert exc_info.value.status_code == 422

    def test_preserves_existing_path(self) -> None:
        fn = self._fn()
        result = fn(
            url="https://example.com/products/shoes",
            source="email",
            medium="email",
            campaign="newsletter",
            content="click",
            touchpoint_key="tp_12345678",
        )
        assert "/products/shoes" in result

    def test_lowercases_source_and_medium(self) -> None:
        fn = self._fn()
        result = fn(
            url="https://example.com/page",
            source="Twitter",
            medium="Social",
            campaign="Test",
            content="Banner",
            touchpoint_key="tp_abcdef12",
        )
        assert "utm_source=twitter" in result
        assert "utm_medium=social" in result


class TestVerifyStripeSignature:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _verify_stripe_signature
        return _verify_stripe_signature

    def test_valid_signature(self) -> None:
        fn = self._fn()
        secret = "test-secret"
        body = b'{"type":"payment_intent.succeeded"}'
        timestamp = "1609459200"
        signed = f"{timestamp}.{body.decode()}"
        sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
        sig_header = f"t={timestamp},v1={sig}"
        assert fn(secret, body, sig_header) is True

    def test_invalid_signature(self) -> None:
        fn = self._fn()
        assert fn("secret", b"body", "t=1234,v1=badsig") is False

    def test_missing_timestamp_returns_false(self) -> None:
        fn = self._fn()
        assert fn("secret", b"body", "v1=somesig") is False

    def test_missing_v1_returns_false(self) -> None:
        fn = self._fn()
        assert fn("secret", b"body", "t=1234,other=val") is False

    def test_malformed_header_returns_false(self) -> None:
        fn = self._fn()
        assert fn("secret", b"body", "notavalidsigheader") is False


class TestVerifyBase64Hmac:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _verify_base64_hmac
        return _verify_base64_hmac

    def test_valid_signature(self) -> None:
        fn = self._fn()
        secret = "shopify-secret"
        body = b'{"id":12345}'
        digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        sig = base64.b64encode(digest).decode()
        assert fn(secret, body, sig) is True

    def test_invalid_signature(self) -> None:
        fn = self._fn()
        assert fn("secret", b"body", "invalidsignature==") is False


class TestExtractStripeConversion:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_stripe_conversion
        return _extract_stripe_conversion

    def test_full_payload(self) -> None:
        fn = self._fn()
        payload = {
            "type": "checkout.session.completed",
            "id": "evt_123",
            "data": {
                "object": {
                    "id": "cs_test_abc",
                    "amount_total": 9900,
                    "currency": "usd",
                    "customer_email": "user@example.com",
                }
            }
        }
        order_id, amount, currency, event_type, customer = fn(payload)
        assert order_id == "cs_test_abc"
        assert amount == 99.0
        assert currency == "USD"
        assert event_type == "checkout.session.completed"
        assert customer == "user@example.com"

    def test_empty_payload_generates_id(self) -> None:
        fn = self._fn()
        order_id, amount, currency, event_type, customer = fn({})
        assert order_id.startswith("stripe-")
        assert amount == 0.0
        assert currency == "USD"
        assert customer is None


class TestExtractShopifyConversion:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_shopify_conversion
        return _extract_shopify_conversion

    def test_full_payload(self) -> None:
        fn = self._fn()
        payload = {
            "topic": "orders/paid",
            "id": 12345,
            "total_price": "99.99",
            "currency": "USD",
            "customer": {"email": "shop@example.com"},
        }
        order_id, amount, currency, event_type, customer = fn(payload)
        assert order_id == "12345"
        assert amount == 99.99
        assert currency == "USD"
        assert event_type == "orders/paid"
        assert customer == "shop@example.com"

    def test_empty_payload(self) -> None:
        fn = self._fn()
        order_id, _, _, event_type, customer = fn({})
        assert order_id.startswith("shopify-")
        assert event_type == "orders/paid"
        assert customer is None


class TestExtractWoocommerceConversion:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_woocommerce_conversion
        return _extract_woocommerce_conversion

    def test_full_payload(self) -> None:
        fn = self._fn()
        payload = {
            "event": "order.created",
            "id": "woo_999",
            "total": "149.99",
            "currency": "EUR",
            "billing": {"email": "woo@example.com"},
        }
        order_id, amount, currency, event_type, customer = fn(payload)
        assert order_id == "woo_999"
        assert amount == 149.99
        assert currency == "EUR"
        assert event_type == "order.created"
        assert customer == "woo@example.com"


class TestExtractConversion:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_conversion
        return _extract_conversion

    def test_stripe_provider(self) -> None:
        fn = self._fn()
        payload = {"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_123", "amount": 5000, "currency": "usd"}}}
        order_id, amount, currency, event_type, customer, touchpoints = fn("stripe", payload)
        assert event_type == "payment_intent.succeeded"

    def test_shopify_provider(self) -> None:
        fn = self._fn()
        payload = {"id": "shop_ord_1", "total_price": "50.0", "currency": "USD"}
        order_id, amount, currency, event_type, customer, touchpoints = fn("shopify", payload)
        assert isinstance(touchpoints, list)

    def test_woocommerce_provider(self) -> None:
        fn = self._fn()
        payload = {"id": "woo_1", "total": "25.0"}
        order_id, _, _, _, _, _ = fn("woocommerce", payload)
        assert "woo_1" in order_id

    def test_unknown_provider_uses_woocommerce(self) -> None:
        fn = self._fn()
        payload = {}
        order_id, amount, currency, event_type, customer, touchpoints = fn("unknown_provider", payload)
        assert isinstance(touchpoints, list)


class TestResolveTenantId:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _resolve_tenant_id
        return _resolve_tenant_id

    def test_header_takes_priority(self) -> None:
        fn = self._fn()
        result = fn("header-tenant", {"tenant_id": "payload-tenant"})
        assert result == "header-tenant"

    def test_falls_back_to_payload(self) -> None:
        fn = self._fn()
        result = fn(None, {"tenant_id": "payload-tenant"})
        assert result == "payload-tenant"

    def test_falls_back_to_metadata(self) -> None:
        fn = self._fn()
        result = fn(None, {"metadata": {"tenant_id": "meta-tenant"}})
        assert result == "meta-tenant"

    def test_default_when_nothing(self) -> None:
        fn = self._fn()
        result = fn(None, {})
        assert result == "tenant-demo"

    def test_empty_header_string(self) -> None:
        fn = self._fn()
        result = fn("   ", {"tenant_id": "payload-tenant"})
        assert result == "payload-tenant"


class TestShapleyContributions:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _shapley_contributions
        return _shapley_contributions

    def test_empty_players_returns_empty(self) -> None:
        fn = self._fn()
        assert fn([], 100.0) == {}

    def test_single_player_gets_all(self) -> None:
        fn = self._fn()
        result = fn(["post_a"], 100.0)
        assert result == {"post_a": 100.0}

    def test_two_equal_players_split_evenly(self) -> None:
        fn = self._fn()
        result = fn(["post_a", "post_b"], 100.0)
        assert abs(result["post_a"] - 50.0) < 0.01
        assert abs(result["post_b"] - 50.0) < 0.01

    def test_many_players_uses_simple_split(self) -> None:
        fn = self._fn()
        players = [f"post_{i}" for i in range(10)]
        result = fn(players, 100.0)
        for v in result.values():
            assert abs(v - 10.0) < 0.01

    def test_deduplicates_players(self) -> None:
        fn = self._fn()
        result = fn(["post_a", "post_a", "post_b"], 100.0)
        assert "post_a" in result
        assert "post_b" in result
        assert len(result) == 2

    def test_zero_revenue(self) -> None:
        fn = self._fn()
        result = fn(["post_a", "post_b"], 0.0)
        for v in result.values():
            assert v == 0.0


class TestRevenueAttributionRoutes:
    def test_create_touchpoint(self, client: TestClient) -> None:
        r = client.post("/analytics/revenue-attribution/touchpoints", headers=H, json={
            "post_id": "post_123",
            "platform": "twitter",
            "destination_url": "https://example.com/product",
        })
        assert r.status_code in VALID

    def test_create_touchpoint_invalid_url(self, client: TestClient) -> None:
        r = client.post("/analytics/revenue-attribution/touchpoints", headers=H, json={
            "post_id": "post_123",
            "platform": "twitter",
            "destination_url": "not-a-url",
        })
        assert r.status_code in VALID

    def test_list_touchpoints(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/touchpoints", headers=H)
        assert r.status_code in VALID

    def test_ingest_conversion(self, client: TestClient) -> None:
        r = client.post("/analytics/revenue-attribution/conversions/ingest", headers=H, json={
            "provider": "stripe",
            "payload": {"type": "checkout.session.completed"},
        })
        assert r.status_code in VALID

    def test_ingest_conversion_unsupported_provider(self, client: TestClient) -> None:
        r = client.post("/analytics/revenue-attribution/conversions/ingest", headers=H, json={
            "provider": "paypal",
            "payload": {},
        })
        assert r.status_code in VALID

    def test_get_report(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/report", headers=H)
        assert r.status_code in VALID

    def test_get_report_with_window(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/report?window_days=30", headers=H)
        assert r.status_code in VALID

    def test_stripe_webhook(self, client: TestClient) -> None:
        r = client.post("/analytics/revenue-attribution/webhooks/stripe", headers={
            **H,
            "Content-Type": "application/json",
        }, content=b'{"type":"test"}')
        assert r.status_code in VALID

    def test_shopify_webhook(self, client: TestClient) -> None:
        r = client.post("/analytics/revenue-attribution/webhooks/shopify", headers={
            **H,
            "Content-Type": "application/json",
        }, content=b'{"id":123}')
        assert r.status_code in VALID
