"""
Additional tests for revenue_attribution.py pure helpers that weren't covered.
Focus: _extract_touchpoints, _inject_utm, _verify_stripe_signature,
_verify_base64_hmac, _extract_stripe/shopify/woocommerce_conversion.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest


class TestExtractTouchpoints:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_touchpoints
        return _extract_touchpoints

    def test_empty_node(self) -> None:
        result = self._fn()({})
        assert result == []

    def test_finds_touchpoint_in_string(self) -> None:
        node = {"url": "https://example.com?nux_touchpoint=email_campaign"}
        result = self._fn()(node)
        assert "email_campaign" in result

    def test_finds_touchpoint_in_nested_dict(self) -> None:
        node = {"data": {"url": "https://example.com?nux_touchpoint=banner_ad"}}
        result = self._fn()(node)
        assert "banner_ad" in result

    def test_finds_touchpoint_in_list(self) -> None:
        node = [{"ref": "https://example.com?nux_touchpoint=social_post"}]
        result = self._fn()(node)
        assert "social_post" in result

    def test_returns_sorted_list(self) -> None:
        node = {
            "url1": "https://example.com?nux_touchpoint=zebra",
            "url2": "https://example.com?nux_touchpoint=alpha",
        }
        result = self._fn()(node)
        assert result == sorted(result)

    def test_deduplicates_touchpoints(self) -> None:
        node = {
            "url1": "https://example.com?nux_touchpoint=email",
            "url2": "https://other.com?nux_touchpoint=email",
        }
        result = self._fn()(node)
        assert result.count("email") == 1

    def test_no_touchpoints(self) -> None:
        node = {"value": "no touchpoints here", "amount": 100}
        result = self._fn()(node)
        assert result == []


class TestInjectUtm:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _inject_utm
        return _inject_utm

    def test_injects_utm_params(self) -> None:
        result = self._fn()(
            "https://example.com/page",
            "email", "newsletter", "summer_sale", "cta_button", "tp_001",
        )
        assert "utm_source=email" in result
        assert "utm_medium=newsletter" in result
        assert "utm_campaign=summer_sale" in result
        assert "nux_touchpoint=tp_001" in result

    def test_preserves_existing_params(self) -> None:
        result = self._fn()(
            "https://example.com/page?foo=bar",
            "google", "cpc", "brand", "ad1", "tp_002",
        )
        assert "foo=bar" in result

    def test_replaces_spaces_with_underscores(self) -> None:
        result = self._fn()(
            "https://example.com/",
            "source", "medium", "my campaign", "my content", "tp_003",
        )
        assert "my_campaign" in result
        assert "my_content" in result

    def test_invalid_url_raises(self) -> None:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            self._fn()("not-a-url", "source", "medium", "campaign", "content", "tp_004")
        assert exc.value.status_code == 422


class TestVerifyStripeSignature:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _verify_stripe_signature
        return _verify_stripe_signature

    def test_valid_signature(self) -> None:
        secret = "test_secret"
        body = b'{"event":"payment_intent.succeeded"}'
        timestamp = "1234567890"
        signed = f"{timestamp}.{body.decode()}".encode()
        expected_sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        sig_header = f"t={timestamp},v1={expected_sig}"
        result = self._fn()(secret, body, sig_header)
        assert result is True

    def test_invalid_signature(self) -> None:
        result = self._fn()("secret", b"body", "t=1234,v1=invalidsig")
        assert result is False

    def test_missing_timestamp(self) -> None:
        result = self._fn()("secret", b"body", "v1=somesig")
        assert result is False

    def test_missing_v1(self) -> None:
        result = self._fn()("secret", b"body", "t=1234567890")
        assert result is False

    def test_empty_sig_header(self) -> None:
        result = self._fn()("secret", b"body", "")
        assert result is False


class TestVerifyBase64Hmac:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _verify_base64_hmac
        return _verify_base64_hmac

    def test_valid_signature(self) -> None:
        secret = "shopify_secret"
        body = b'{"order_id": 123}'
        digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()
        assert self._fn()(secret, body, signature) is True

    def test_invalid_signature(self) -> None:
        assert self._fn()("secret", b"body", "invalidsig") is False


class TestExtractStripeConversion:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_stripe_conversion
        return _extract_stripe_conversion

    def test_basic_extraction(self) -> None:
        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "amount_total": 9900,
                    "currency": "usd",
                    "customer_email": "customer@example.com",
                }
            }
        }
        external_id, amount, currency, event_type, customer_ref = self._fn()(payload)
        assert external_id == "cs_test_123"
        assert amount == 99.0
        assert currency == "USD"
        assert event_type == "checkout.session.completed"
        assert customer_ref == "customer@example.com"

    def test_empty_payload_uses_defaults(self) -> None:
        external_id, amount, currency, event_type, customer_ref = self._fn()({})
        assert isinstance(external_id, str)
        assert amount == 0.0
        assert currency == "USD"
        assert customer_ref is None

    def test_amount_total_conversion(self) -> None:
        payload = {"data": {"object": {"amount_total": 5000, "currency": "eur"}}}
        _, amount, currency, _, _ = self._fn()(payload)
        assert amount == 50.0
        assert currency == "EUR"


class TestExtractShopifyConversion:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_shopify_conversion
        return _extract_shopify_conversion

    def test_basic_extraction(self) -> None:
        payload = {
            "topic": "orders/paid",
            "id": 12345,
            "total_price": "149.99",
            "currency": "GBP",
            "customer": {"email": "shopify@example.com"},
        }
        external_id, amount, currency, event_type, customer_ref = self._fn()(payload)
        assert external_id == "12345"
        assert amount == 149.99
        assert currency == "GBP"
        assert customer_ref == "shopify@example.com"

    def test_empty_payload_uses_defaults(self) -> None:
        external_id, amount, currency, event_type, customer_ref = self._fn()({})
        assert isinstance(external_id, str)
        assert amount == 0.0
        assert currency == "USD"


class TestExtractWoocommerceConversion:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_woocommerce_conversion
        return _extract_woocommerce_conversion

    def test_basic_extraction(self) -> None:
        payload = {
            "event": "order.created",
            "id": 9876,
            "total": "75.50",
            "currency": "EUR",
            "billing": {"email": "woo@example.com"},
        }
        external_id, amount, currency, event_type, customer_ref = self._fn()(payload)
        assert external_id == "9876"
        assert amount == 75.5
        assert currency == "EUR"
        assert customer_ref == "woo@example.com"

    def test_empty_payload_uses_defaults(self) -> None:
        external_id, amount, currency, event_type, customer_ref = self._fn()({})
        assert isinstance(external_id, str)
        assert amount == 0.0


class TestExtractConversionDispatcher:
    def _fn(self):
        from backend.fastapi.app.routers.revenue_attribution import _extract_conversion
        return _extract_conversion

    def test_stripe_dispatch(self) -> None:
        payload = {"type": "payment_intent.succeeded", "data": {"object": {}}}
        external_id, amount, currency, event_type, customer_ref, touchpoints = self._fn()("stripe", payload)
        assert event_type == "payment_intent.succeeded"

    def test_shopify_dispatch(self) -> None:
        payload = {"topic": "orders/paid", "id": 111, "total_price": "50.00"}
        _, _, _, event_type, _, _ = self._fn()("shopify", payload)
        assert event_type == "orders/paid"

    def test_unknown_provider_fallback(self) -> None:
        payload = {"event": "order.created", "id": 222}
        _, _, _, event_type, _, _ = self._fn()("unknown_provider", payload)
        assert isinstance(event_type, str)


class TestEntityFirstSeoDeduplicate:
    def test_deduplicates_by_name_type(self) -> None:
        from backend.fastapi.app.modules.entity_first_seo import EntityFirstSEO
        inst = EntityFirstSEO.__new__(EntityFirstSEO)
        entities = [
            {"name": "Apple", "type": "company"},
            {"name": "Apple", "type": "company"},  # duplicate
            {"name": "Apple", "type": "fruit"},    # different type
        ]
        result = inst._deduplicate_entities(entities)
        assert len(result) == 2

    def test_empty_list(self) -> None:
        from backend.fastapi.app.modules.entity_first_seo import EntityFirstSEO
        inst = EntityFirstSEO.__new__(EntityFirstSEO)
        result = inst._deduplicate_entities([])
        assert result == []

    def test_case_insensitive(self) -> None:
        from backend.fastapi.app.modules.entity_first_seo import EntityFirstSEO
        inst = EntityFirstSEO.__new__(EntityFirstSEO)
        entities = [
            {"name": "Google", "type": "company"},
            {"name": "google", "type": "company"},  # same after lower()
        ]
        result = inst._deduplicate_entities(entities)
        assert len(result) == 1
