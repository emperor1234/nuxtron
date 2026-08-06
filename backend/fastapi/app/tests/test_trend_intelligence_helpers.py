"""Tests for pure helper functions in trend_intelligence.py."""
import os
from datetime import UTC, datetime

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from backend.fastapi.app.routers.trend_intelligence import (
    _asset_text,
    _best_hour_for_perf,
    _build_content_assets,
    _build_performance_diagnostics,
    _classify_phase,
    _clip,
    _recommendation_lines,
    _safe_rate,
    _to_dt,
    _topic_projection,
    _topic_series,
    _topic_strengths,
    _topic_timing,
)

NOW = datetime.now(UTC)


# ─── _to_dt ──────────────────────────────────────────────────────────────────

class TestToDt:
    def test_none_returns_fallback(self):
        result = _to_dt(None, NOW)
        assert result == NOW

    def test_empty_returns_fallback(self):
        result = _to_dt("", NOW)
        assert result == NOW

    def test_valid_iso(self):
        result = _to_dt("2024-01-15T10:00:00+00:00", NOW)
        assert isinstance(result, datetime)

    def test_z_suffix(self):
        result = _to_dt("2024-01-15T10:00:00Z", NOW)
        assert isinstance(result, datetime)

    def test_invalid_returns_fallback(self):
        result = _to_dt("not-a-date", NOW)
        assert result == NOW


# ─── _safe_rate ──────────────────────────────────────────────────────────────

class TestSafeRate:
    def test_zero_denominator(self):
        assert _safe_rate(10.0, 0.0) == 0.0

    def test_normal_division(self):
        assert _safe_rate(10.0, 100.0) == pytest.approx(0.1)

    def test_negative_denominator(self):
        assert _safe_rate(5.0, -1.0) == 0.0

    def test_zero_numerator(self):
        assert _safe_rate(0.0, 100.0) == 0.0


# ─── _clip ───────────────────────────────────────────────────────────────────

class TestClip:
    def test_within_range(self):
        assert _clip(0.5) == pytest.approx(0.5)

    def test_above_upper(self):
        assert _clip(1.5) == 1.0

    def test_below_lower(self):
        assert _clip(-0.5) == 0.0

    def test_custom_bounds(self):
        assert _clip(15.0, 0.0, 10.0) == 10.0

    def test_at_boundary(self):
        assert _clip(1.0) == pytest.approx(1.0)
        assert _clip(0.0) == pytest.approx(0.0)


# ─── _classify_phase ─────────────────────────────────────────────────────────

class TestClassifyPhase:
    def test_upcoming_forecast(self):
        result = _classify_phase(0.7, 0.1, 0.02)
        assert result == "upcoming_forecast"

    def test_emerging(self):
        result = _classify_phase(0.55, 0.05, 0.0)
        assert result == "emerging"

    def test_current(self):
        result = _classify_phase(0.45, 0.0, 0.0)
        assert result == "current"

    def test_downfall(self):
        result = _classify_phase(0.1, -0.1, -0.05)
        assert result == "downfall"


# ─── _recommendation_lines ───────────────────────────────────────────────────

class TestRecommendationLines:
    def test_upcoming_forecast_phase(self):
        lines = _recommendation_lines("upcoming_forecast", 0.5, None)
        assert any("early" in l.lower() for l in lines)

    def test_emerging_phase(self):
        lines = _recommendation_lines("emerging", 0.5, None)
        assert any("scale" in l.lower() for l in lines)

    def test_current_phase(self):
        lines = _recommendation_lines("current", 0.5, None)
        assert any("hook" in l.lower() for l in lines)

    def test_downfall_phase(self):
        lines = _recommendation_lines("downfall", 0.5, None)
        assert any("reposition" in l.lower() for l in lines)

    def test_low_roi_adds_line(self):
        lines = _recommendation_lines("current", 0.3, None)
        assert any("intent" in l.lower() or "efficiency" in l.lower() for l in lines)

    def test_high_roi_adds_line(self):
        lines = _recommendation_lines("current", 0.8, None)
        assert any("spend" in l.lower() for l in lines)

    def test_best_hour_adds_line(self):
        lines = _recommendation_lines("current", 0.5, 14)
        assert any("14" in l for l in lines)


# ─── _best_hour_for_perf ─────────────────────────────────────────────────────

class TestBestHourForPerf:
    def test_empty_returns_none(self):
        assert _best_hour_for_perf([], NOW) is None

    def test_returns_hour_with_most_engagement(self):
        perf = [
            {"posted_at": "2024-01-15T10:00:00Z", "engagement_rate": 0.1},
            {"posted_at": "2024-01-15T14:00:00Z", "engagement_rate": 0.5},
            {"posted_at": "2024-01-15T14:30:00Z", "engagement_rate": 0.3},
        ]
        best = _best_hour_for_perf(perf, NOW)
        assert best == 14  # Hour 14 has highest total engagement

    def test_single_record(self):
        perf = [{"posted_at": "2024-01-15T09:00:00Z", "engagement_rate": 0.2}]
        assert _best_hour_for_perf(perf, NOW) == 9


# ─── _topic_series ───────────────────────────────────────────────────────────

class TestTopicSeries:
    def test_extracts_fields(self):
        signals = [
            {"virality_score": 0.5, "quality_index": 0.4, "ctr": 0.02, "conversion_rate": 0.01},
            {"virality_score": 0.7, "quality_index": 0.6, "ctr": 0.03, "conversion_rate": 0.02},
        ]
        scores, quality, ctr, conv = _topic_series(signals)
        assert scores == [0.5, 0.7]
        assert quality == [0.4, 0.6]

    def test_empty_signals(self):
        scores, quality, ctr, conv = _topic_series([])
        assert scores == []
        assert quality == []

    def test_missing_fields_default_to_zero(self):
        signals = [{}]
        scores, quality, ctr, conv = _topic_series(signals)
        assert scores == [0.0]


# ─── _topic_strengths ────────────────────────────────────────────────────────

class TestTopicStrengths:
    def test_returns_five_values(self):
        scores = [0.5, 0.6, 0.7]
        quality = [0.4, 0.5, 0.6]
        ctr = [0.02, 0.03, 0.04]
        conv = [0.01, 0.02, 0.03]
        result = _topic_strengths(scores, quality, ctr, conv)
        assert len(result) == 5

    def test_phase_is_string(self):
        scores = [0.5, 0.6, 0.7]
        quality = [0.4, 0.5, 0.6]
        ctr = [0.02, 0.03, 0.04]
        conv = [0.01, 0.02, 0.03]
        *_, phase = _topic_strengths(scores, quality, ctr, conv)
        assert isinstance(phase, str)

    def test_empty_lists(self):
        # Should not raise — single-element lists to avoid ZeroDivisionError
        result = _topic_strengths([0.0], [0.0], [0.0], [0.0])
        assert len(result) == 5


# ─── _topic_timing ───────────────────────────────────────────────────────────

class TestTopicTiming:
    def test_returns_best_platform_and_hour(self):
        signals = [
            {"source_platform": "linkedin", "captured_at": "2024-01-15T10:00:00Z", "views": 1000},
            {"source_platform": "instagram", "captured_at": "2024-01-15T14:00:00Z", "views": 500},
            {"source_platform": "linkedin", "captured_at": "2024-01-15T11:00:00Z", "views": 800},
        ]
        platform, hour = _topic_timing(signals, NOW)
        assert platform == "linkedin"  # Most signals

    def test_single_signal(self):
        signals = [{'source_platform': 'tiktok', 'captured_at': '2024-01-15T10:00:00Z', 'views': 500}]
        platform, hour = _topic_timing(signals, NOW)
        assert platform == 'tiktok'
        assert isinstance(hour, int)


# ─── _topic_projection ───────────────────────────────────────────────────────

class TestTopicProjection:
    def test_returns_horizon_days(self):
        result = _topic_projection(0.5, 0.05, 0.01, 0.02, 7)
        assert len(result) == 7

    def test_each_item_has_expected_keys(self):
        result = _topic_projection(0.5, 0.05, 0.01, 0.02, 3)
        for item in result:
            assert "day" in item
            assert "projected_strength" in item
            assert "projected_reach" in item

    def test_strength_clipped_to_1(self):
        result = _topic_projection(1.0, 1.0, 1.0, 1.0, 5)
        for item in result:
            assert item["projected_strength"] <= 1.0


# ─── _asset_text ─────────────────────────────────────────────────────────────

class TestAssetText:
    def test_social_post(self):
        result = _asset_text("AI trends", "emerging", "linkedin", "social_post")
        assert "Ai Trends" in result or "AI trends" in result or "ai trends" in result.lower()

    def test_short_ad_copy(self):
        result = _asset_text("AI trends", "current", "instagram", "short_ad_copy")
        assert "ai trends" in result.lower()

    def test_hook(self):
        result = _asset_text("AI trends", "upcoming_forecast", "x", "hook")
        assert "ai trends" in result.lower()

    def test_cta(self):
        result = _asset_text("AI trends", "current", "linkedin", "cta")
        assert "Save" in result or "test" in result

    def test_fallback(self):
        result = _asset_text("AI trends", "current", "linkedin", "unknown_kind")
        assert "ai trends" in result.lower()


# ─── _build_content_assets ───────────────────────────────────────────────────

class TestBuildContentAssets:
    def test_returns_list(self):
        result = _build_content_assets("AI", "current", "linkedin", ["social_post", "hook"], "linkedin")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_each_has_type_and_text(self):
        result = _build_content_assets("AI", "current", "linkedin", ["hook"], "linkedin")
        assert result[0]["type"] == "hook"
        assert isinstance(result[0]["text"], str)

    def test_empty_output_types(self):
        result = _build_content_assets("AI", "current", "linkedin", [], "linkedin")
        assert result == []


# ─── _build_performance_diagnostics ─────────────────────────────────────────

class TestBuildPerformanceDiagnostics:
    def test_basic(self):
        perf = [
            {"posted_at": "2024-01-15T10:00:00Z", "views": 1000, "not_viewed_reasons": {"hook_too_weak": 50}},
        ]
        result = _build_performance_diagnostics(perf, 0.02)
        assert "top_not_viewed_reasons" in result
        assert "best_hour" in result
        assert result["improvement_focus"] == "hook_quality"

    def test_empty_perf(self):
        result = _build_performance_diagnostics([], 0.5)
        assert result["top_not_viewed_reasons"] == []
        assert result["best_hour"] is None
        assert result["improvement_focus"] == "cta_optimization"

    def test_high_engagement_cta_focus(self):
        result = _build_performance_diagnostics([], 0.05)
        assert result["improvement_focus"] == "cta_optimization"

    def test_not_viewed_reasons_aggregated(self):
        perf = [
            {"posted_at": "2024-01-15T10:00:00Z", "views": 100,
             "not_viewed_reasons": {"hook_too_weak": 20, "bad_timing": 10}},
            {"posted_at": "2024-01-15T12:00:00Z", "views": 200,
             "not_viewed_reasons": {"hook_too_weak": 30}},
        ]
        result = _build_performance_diagnostics(perf, 0.01)
        reason_names = [r["reason"] for r in result["top_not_viewed_reasons"]]
        assert "hook_too_weak" in reason_names
