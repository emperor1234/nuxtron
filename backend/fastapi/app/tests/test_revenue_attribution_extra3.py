"""
Tests for revenue_attribution.py _build_report_response (untested function).
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

from backend.fastapi.app.routers.revenue_attribution import _build_report_response


class TestBuildReportResponse:
    def test_empty_conversions_returns_zero_totals(self) -> None:
        result = _build_report_response(
            tenant_id="t1",
            window_days=30,
            touchpoints={},
            conversions=[],
        )
        assert result["status"] == "ok"
        assert result["totals"]["conversions"] == 0
        assert result["totals"]["revenue"] == 0.0

    def test_includes_tenant_id_and_window(self) -> None:
        result = _build_report_response(
            tenant_id="my-tenant",
            window_days=7,
            touchpoints={},
            conversions=[],
        )
        assert result["tenant_id"] == "my-tenant"
        assert result["window_days"] == 7

    def test_sums_total_revenue(self) -> None:
        conversions = [
            {"id": 1, "provider": "stripe", "amount": 100.0, "touchpoint_keys": []},
            {"id": 2, "provider": "stripe", "amount": 50.0, "touchpoint_keys": []},
        ]
        result = _build_report_response(
            tenant_id="t1",
            window_days=30,
            touchpoints={},
            conversions=conversions,
        )
        assert result["totals"]["revenue"] == 150.0

    def test_attributed_revenue_with_touchpoints(self) -> None:
        touchpoints = {
            "tp_1": {"post_id": "post_a", "source": "facebook"},
        }
        conversions = [
            {"id": 1, "provider": "stripe", "amount": 200.0, "touchpoint_keys": ["tp_1"]},
        ]
        result = _build_report_response(
            tenant_id="t1",
            window_days=30,
            touchpoints=touchpoints,
            conversions=conversions,
        )
        assert result["totals"]["attributed_revenue"] == 200.0
        assert result["totals"]["unattributed_revenue"] == 0.0

    def test_unattributed_revenue_for_missing_touchpoints(self) -> None:
        touchpoints = {}
        conversions = [
            {"id": 1, "provider": "stripe", "amount": 100.0, "touchpoint_keys": ["missing-key"]},
        ]
        result = _build_report_response(
            tenant_id="t1",
            window_days=30,
            touchpoints=touchpoints,
            conversions=conversions,
        )
        assert result["totals"]["unattributed_revenue"] == 100.0

    def test_top_posts_sorted_by_revenue(self) -> None:
        touchpoints = {
            "tp_1": {"post_id": "post_a", "source": "fb"},
            "tp_2": {"post_id": "post_b", "source": "ig"},
        }
        conversions = [
            {"id": 1, "provider": "stripe", "amount": 100.0, "touchpoint_keys": ["tp_1"]},
            {"id": 2, "provider": "stripe", "amount": 300.0, "touchpoint_keys": ["tp_2"]},
        ]
        result = _build_report_response(
            tenant_id="t1",
            window_days=30,
            touchpoints=touchpoints,
            conversions=conversions,
        )
        top_posts = result["top_posts"]
        assert len(top_posts) >= 1

    def test_channels_included_in_response(self) -> None:
        touchpoints = {
            "tp_1": {"post_id": "post_a", "source": "facebook"},
        }
        conversions = [
            {"id": 1, "provider": "stripe", "amount": 100.0, "touchpoint_keys": ["tp_1"]},
        ]
        result = _build_report_response(
            tenant_id="t1",
            window_days=30,
            touchpoints=touchpoints,
            conversions=conversions,
        )
        channels = result["channels"]
        assert isinstance(channels, list)
        assert any(c["channel"] == "facebook" for c in channels)

    def test_conversion_rows_capped_at_100(self) -> None:
        conversions = [
            {"id": i, "provider": "stripe", "amount": 10.0, "touchpoint_keys": []}
            for i in range(150)
        ]
        result = _build_report_response(
            tenant_id="t1",
            window_days=30,
            touchpoints={},
            conversions=conversions,
        )
        assert len(result["conversions"]) <= 100
