"""Tests for pure helpers in outcome_attribution.py and revenue_attribution.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from backend.fastapi.app.routers.outcome_attribution import (
    _quality_band,
    compute_decision_quality_score,
)
from backend.fastapi.app.routers.revenue_attribution import (
    _build_report_response,
    _extract_shopify_conversion,
    _extract_stripe_conversion,
    _extract_touchpoints,
    _extract_woocommerce_conversion,
    _inject_utm,
    _resolve_tenant_id,
    _shapley_contributions,
    _verify_base64_hmac,
    _verify_stripe_signature,
)
from fastapi import HTTPException

# ─── _quality_band ───────────────────────────────────────────────────────────

class TestQualityBand:
    def test_high_score(self):
        result = _quality_band(90.0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_medium_score(self):
        result = _quality_band(50.0)
        assert isinstance(result, str)

    def test_zero_score(self):
        result = _quality_band(0.0)
        assert result == "poor"


# ─── compute_decision_quality_score ──────────────────────────────────────────

class TestComputeDecisionQualityScore:
    def test_high_accuracy_safety(self):
        score = compute_decision_quality_score(
            accuracy=90.0, safety=90.0, speed_ms=100, revenue_impact_gbp=500.0, human_override=False
        )
        assert score > 0
        assert score <= 100.0

    def test_override_penalty(self):
        score_no_override = compute_decision_quality_score(
            accuracy=80.0, safety=80.0, speed_ms=100, revenue_impact_gbp=0.0, human_override=False
        )
        score_override = compute_decision_quality_score(
            accuracy=80.0, safety=80.0, speed_ms=100, revenue_impact_gbp=0.0, human_override=True
        )
        assert score_override < score_no_override

    def test_result_clamped_to_0_100(self):
        score = compute_decision_quality_score(
            accuracy=0.0, safety=0.0, speed_ms=100000, revenue_impact_gbp=-10000.0, human_override=True
        )
        assert score >= 0.0

        score_max = compute_decision_quality_score(
            accuracy=100.0, safety=100.0, speed_ms=0, revenue_impact_gbp=10000.0, human_override=False
        )
        assert score_max <= 100.0

    def test_slow_speed_penalized(self):
        fast = compute_decision_quality_score(
            accuracy=80.0, safety=80.0, speed_ms=100, revenue_impact_gbp=0.0, human_override=False
        )
        slow = compute_decision_quality_score(
            accuracy=80.0, safety=80.0, speed_ms=50000, revenue_impact_gbp=0.0, human_override=False
        )
        assert fast >= slow


# ─── _extract_touchpoints ────────────────────────────────────────────────────

class TestExtractTouchpoints:
    def test_finds_touchpoint_in_url(self):
        # Depends on _TOUCHPOINT_PATTERN — test with nux_touchpoint param
        payload = {"url": "https://example.com?nux_touchpoint=tp_abc123"}
        result = _extract_touchpoints(payload)
        assert "tp_abc123" in result

    def test_nested_dict(self):
        payload = {"data": {"link": "https://example.com?nux_touchpoint=tp_xyz789"}}
        result = _extract_touchpoints(payload)
        assert "tp_xyz789" in result

    def test_empty_payload(self):
        result = _extract_touchpoints({})
        assert result == []

    def test_returns_sorted(self):
        payload = {
            "link1": "https://example.com?nux_touchpoint=tp_bbb",
            "link2": "https://example.com?nux_touchpoint=tp_aaa"
        }
        result = _extract_touchpoints(payload)
        if len(result) >= 2:
            assert result == sorted(result)


# ─── _inject_utm ─────────────────────────────────────────────────────────────

class TestInjectUtm:
    def test_appends_utm_params(self):
        result = _inject_utm("https://example.com/page", "linkedin", "social", "campaign1", "post1", "tp_abc")
        assert "utm_source=linkedin" in result
        assert "utm_medium=social" in result
        assert "nux_touchpoint=tp_abc" in result

    def test_invalid_url_raises(self):
        with pytest.raises(HTTPException) as exc:
            _inject_utm("not-a-url", "linkedin", "social", "campaign", "post", "tp_abc")
        assert exc.value.status_code == 422

    def test_existing_params_preserved_or_overwritten(self):
        result = _inject_utm("https://example.com?existing=1", "twitter", "organic", "camp", "content", "tp_key")
        assert "utm_source=twitter" in result


# ─── _verify_stripe_signature ────────────────────────────────────────────────

class TestVerifyStripeSignature:
    def test_missing_fields_returns_false(self):
        assert _verify_stripe_signature("secret", b"body", "no-valid-sig") is False

    def test_invalid_signature_returns_false(self):
        assert _verify_stripe_signature("secret", b"test body", "t=1234,v1=invalidsig") is False

    def test_empty_sig_header_returns_false(self):
        assert _verify_stripe_signature("secret", b"body", "") is False


# ─── _verify_base64_hmac ─────────────────────────────────────────────────────

class TestVerifyBase64Hmac:
    def test_valid_signature(self):
        import base64
        import hashlib
        import hmac as hmac_lib

        secret = "test-secret"
        body = b"test body"
        digest = hmac_lib.new(secret.encode(), body, hashlib.sha256).digest()
        sig = base64.b64encode(digest).decode()

        assert _verify_base64_hmac(secret, body, sig) is True

    def test_invalid_signature_returns_false(self):
        assert _verify_base64_hmac("secret", b"body", "invalidsig") is False

    def test_wrong_secret_returns_false(self):
        import base64
        import hashlib
        import hmac as hmac_lib

        body = b"test body"
        digest = hmac_lib.new(b"correct-secret", body, hashlib.sha256).digest()
        sig = base64.b64encode(digest).decode()
        assert _verify_base64_hmac("wrong-secret", body, sig) is False


# ─── _extract_stripe_conversion ──────────────────────────────────────────────

class TestExtractStripeConversion:
    def test_basic(self):
        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "amount_total": 10000,
                    "currency": "usd",
                    "customer_email": "user@example.com",
                }
            }
        }
        order_id, amount, currency, event_type, customer = _extract_stripe_conversion(payload)
        assert order_id == "cs_test_123"
        assert amount == 100.0
        assert currency == "USD"
        assert customer == "user@example.com"

    def test_empty_payload(self):
        order_id, amount, currency, event_type, customer = _extract_stripe_conversion({})
        assert amount == 0.0
        assert currency == "USD"


# ─── _extract_shopify_conversion ─────────────────────────────────────────────

class TestExtractShopifyConversion:
    def test_basic(self):
        payload = {
            "topic": "orders/paid",
            "id": "shop_order_456",
            "total_price": "59.99",
            "currency": "USD",
            "customer": {"email": "buyer@example.com"}
        }
        order_id, amount, currency, event_type, customer = _extract_shopify_conversion(payload)
        assert order_id == "shop_order_456"
        assert amount == pytest.approx(59.99)
        assert currency == "USD"
        assert customer == "buyer@example.com"


# ─── _extract_woocommerce_conversion ─────────────────────────────────────────

class TestExtractWoocommerceConversion:
    def test_basic(self):
        payload = {
            "event": "order.completed",
            "id": "woo_789",
            "total": "25.00",
            "currency": "EUR",
            "billing": {"email": "woo@example.com"}
        }
        order_id, amount, currency, event_type, customer = _extract_woocommerce_conversion(payload)
        assert order_id == "woo_789"
        assert amount == pytest.approx(25.0)
        assert currency == "EUR"
        assert customer == "woo@example.com"


# ─── _resolve_tenant_id ──────────────────────────────────────────────────────

class TestResolveTenantId:
    def test_header_takes_priority(self):
        result = _resolve_tenant_id("header-tenant", {"tenant_id": "body-tenant"})
        assert result == "header-tenant"

    def test_payload_fallback(self):
        result = _resolve_tenant_id(None, {"tenant_id": "payload-tenant"})
        assert result == "payload-tenant"

    def test_metadata_fallback(self):
        result = _resolve_tenant_id(None, {"metadata": {"tenant_id": "meta-tenant"}})
        assert result == "meta-tenant"

    def test_default_demo(self):
        result = _resolve_tenant_id(None, {})
        assert result == "tenant-demo"

    def test_empty_header_falls_through(self):
        result = _resolve_tenant_id("", {"tenant_id": "payload-tenant"})
        assert result == "payload-tenant"


# ─── _shapley_contributions ──────────────────────────────────────────────────

class TestShapleyContributions:
    def test_single_player(self):
        result = _shapley_contributions(["post_a"], 100.0)
        assert result == {"post_a": 100.0}

    def test_two_players_equal_split(self):
        result = _shapley_contributions(["post_a", "post_b"], 100.0)
        assert abs(result["post_a"] - result["post_b"]) < 0.01
        assert abs(sum(result.values()) - 100.0) < 0.01

    def test_empty_players(self):
        assert _shapley_contributions([], 100.0) == {}

    def test_duplicate_players_deduplicated(self):
        result = _shapley_contributions(["post_a", "post_a"], 100.0)
        assert len(result) == 1

    def test_many_players_equal_split(self):
        players = [f"post_{i}" for i in range(10)]
        result = _shapley_contributions(players, 100.0)
        # More than 8 players -> equal split
        for v in result.values():
            assert abs(v - 10.0) < 0.01


# ─── _build_report_response ──────────────────────────────────────────────────

class TestBuildReportResponse:
    def test_empty_conversions(self):
        result = _build_report_response(
            tenant_id="t1", window_days=30, touchpoints={}, conversions=[]
        )
        assert result["status"] == "ok"
        assert result["totals"]["conversions"] == 0
        assert result["totals"]["revenue"] == 0.0

    def test_unattributed_revenue(self):
        conversions = [
            {"id": 1, "provider": "stripe", "external_order_id": "o1",
             "amount": 100.0, "touchpoint_keys": []}
        ]
        result = _build_report_response(
            tenant_id="t1", window_days=30, touchpoints={}, conversions=conversions
        )
        assert result["totals"]["unattributed_revenue"] == 100.0

    def test_attributed_revenue(self):
        touchpoints = {"tp_1": {"post_id": "post_a", "source": "linkedin", "platform": "linkedin"}}
        conversions = [
            {"id": 1, "provider": "stripe", "external_order_id": "o1",
             "amount": 200.0, "touchpoint_keys": ["tp_1"]}
        ]
        result = _build_report_response(
            tenant_id="t1", window_days=30, touchpoints=touchpoints, conversions=conversions
        )
        assert result["totals"]["attributed_revenue"] == 200.0
        assert result["totals"]["unattributed_revenue"] == 0.0
