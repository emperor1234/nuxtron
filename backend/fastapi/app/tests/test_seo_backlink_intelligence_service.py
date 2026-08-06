"""Unit tests for Backlink Intelligence service (phase-i module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_backlink_intelligence_service import (
    analyze_backlink_intelligence,
    analyze_backlink_intelligence_signals,
)


def test_heuristic_scales() -> None:
    thin = analyze_backlink_intelligence_signals(
        domain="example.com",
        competitor_domains=[],
        link_analysis_depth="basic",
        include_topical_clusters=False,
        notes="",
    )
    rich = analyze_backlink_intelligence_signals(
        domain="acme.example.com",
        competitor_domains=["comp1.com", "comp2.com", "comp3.com"],
        link_analysis_depth="deep",
        include_topical_clusters=True,
        notes="Backlink graph review with competitor gap analysis and topical cluster mapping notes",
    )
    assert rich["backlink_intelligence_score"] > thin["backlink_intelligence_score"]
    assert thin["backlink_intelligence_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"backlink_intelligence_score": 71, "link_graph": {}}

    assert (
        await analyze_backlink_intelligence(
            domain="example.com",
            competitor_domains=["comp.com"],
            link_analysis_depth="standard",
            include_topical_clusters=True,
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_backlink_intelligence(
            domain="example.com",
            competitor_domains=["comp.com"],
            link_analysis_depth="standard",
            include_topical_clusters=True,
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
