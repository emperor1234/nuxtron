"""Unit tests for Rank Tracking service (phase-i module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_rank_tracking_service import analyze_rank_tracking, analyze_rank_tracking_signals


def test_heuristic_scales() -> None:
    thin = analyze_rank_tracking_signals(
        domain="example.com",
        tracked_keywords=["seo"],
        historical_lookback_days=30,
        include_competitor_tracking=False,
        competitor_domains=[],
        notes="",
    )
    rich = analyze_rank_tracking_signals(
        domain="acme.example.com",
        tracked_keywords=["enterprise seo", "seo automation", "rank tracking platform", "technical seo audit"],
        historical_lookback_days=180,
        include_competitor_tracking=True,
        competitor_domains=["comp1.com", "comp2.com"],
        notes="Rank tracking volatility review with competitor movement analysis notes",
    )
    assert rich["tracking_score"] > thin["tracking_score"]
    assert thin["tracking_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"tracking_score": 69, "ranking_history": []}

    assert (
        await analyze_rank_tracking(
            domain="example.com",
            tracked_keywords=["seo tools"],
            historical_lookback_days=90,
            include_competitor_tracking=False,
            competitor_domains=[],
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_rank_tracking(
            domain="example.com",
            tracked_keywords=["seo tools"],
            historical_lookback_days=90,
            include_competitor_tracking=False,
            competitor_domains=[],
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
