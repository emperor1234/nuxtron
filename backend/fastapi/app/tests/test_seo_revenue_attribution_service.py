"""Unit tests for Revenue Attribution service (phase-c module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_revenue_attribution_service import (
    analyze_revenue_attribution,
    analyze_revenue_attribution_signals,
)


def test_heuristic_scales_with_channels() -> None:
    thin = analyze_revenue_attribution_signals(
        domain="example.com", channels=[], conversion_events=[], revenue_window_days=7, notes=""
    )
    rich = analyze_revenue_attribution_signals(
        domain="https://nuxtron.io",
        channels=["organic_search", "ai_referrals", "email", "social"],
        conversion_events=["demo_request", "trial_signup", "checkout"],
        revenue_window_days=60,
        notes="UTM attribution QA weekly",
    )
    assert rich["attribution_confidence_score"] > thin["attribution_confidence_score"]
    assert rich["attribution_confidence_score"] < 100
    assert rich["revenue_influenced_pct"] < 100


@pytest.mark.asyncio
async def test_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"attribution_confidence_score": 71, "channel_attribution": []}

    out = await analyze_revenue_attribution(
        domain="example.com", channels=["organic_search"], conversion_events=["checkout"],
        revenue_window_days=30, notes="", ollama_json_fn=_llm, system_prompt="s", clean_text_fn=lambda t, _m: t,
    )
    assert out["analysis_mode"] == "llm"


@pytest.mark.asyncio
async def test_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    out = await analyze_revenue_attribution(
        domain="example.com", channels=[], conversion_events=[], revenue_window_days=30, notes="",
        ollama_json_fn=_down, system_prompt="s", clean_text_fn=lambda t, _m: t,
    )
    assert out["analysis_mode"] == "heuristic"
