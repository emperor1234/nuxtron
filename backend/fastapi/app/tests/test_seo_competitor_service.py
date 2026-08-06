"""Unit tests for Competitor service (phase-f module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_competitor_service import analyze_competitor_intel, analyze_competitor_signals


def test_heuristic_scales() -> None:
    thin = analyze_competitor_signals(domain="example.com", competitors=[], target_keyword="", notes="")
    rich = analyze_competitor_signals(
        domain="acme.io",
        competitors=["rival1.com", "rival2.com", "rival3.com"],
        target_keyword="seo automation platform",
        notes="Quarterly competitive review",
    )
    assert rich["competitive_score"] > thin["competitive_score"]
    assert thin["competitive_score"] < 100
    assert rich["competitors"]


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"competitive_score": 71, "shared_keywords": []}

    assert (
        await analyze_competitor_intel(
            domain="example.com",
            competitors=["rival.com"],
            target_keyword="seo",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_competitor_intel(
            domain="example.com",
            competitors=[],
            target_keyword="",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
