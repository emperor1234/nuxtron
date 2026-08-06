"""Unit tests for production PEAO service (module 11)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_peao_service import analyze_peao_forecast, analyze_peao_signals, normalize_peao_result


def test_heuristic_scales_with_positive_signals() -> None:
    thin = analyze_peao_signals(
        domain="example.com",
        primary_keyword="crm software",
        recent_signals="",
        forecast_horizon_days=30,
        notes="",
    )
    rich = analyze_peao_signals(
        domain="https://example.com",
        primary_keyword="crm software",
        recent_signals="Traffic gained 20%. Position 3 stable. Improved CTR this month.",
        forecast_horizon_days=30,
        notes="",
    )
    assert rich["predictive_score"] > thin["predictive_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["predictive_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_peao_result(
        {"predictive_score": 140, "fallback": True, "volatility_risk": "low"},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["predictive_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_peao_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "predictive_score": 74,
            "volatility_risk": "medium",
            "trend_forecast": {"direction": "up", "confidence": 0.71},
        }

    result = await analyze_peao_forecast(
        domain="example.com",
        primary_keyword="crm software",
        recent_signals="Stable",
        forecast_horizon_days=30,
        notes="",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["predictive_score"] == 74


@pytest.mark.asyncio
async def test_analyze_peao_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_peao_forecast(
        domain="example.com",
        primary_keyword="crm software",
        recent_signals="Rankings dropped after crawl issue",
        forecast_horizon_days=30,
        notes="",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "predictive_score" in result
    assert "fallback" not in result
