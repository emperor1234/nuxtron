"""Unit tests for Link Building service (phase-d module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_linkbuilding_service import analyze_linkbuilding, analyze_linkbuilding_signals


def test_heuristic_scales() -> None:
    thin = analyze_linkbuilding_signals(
        domain="x.com", competitors=[], niche="", target_keywords=[], opportunity_types=[]
    )
    rich = analyze_linkbuilding_signals(
        domain="https://acme.io",
        competitors=["a.com", "b.com"],
        niche="SaaS",
        target_keywords=["seo", "content"],
        opportunity_types=["guest_post", "resource_page"],
    )
    assert rich["linkbuilding_score"] > thin["linkbuilding_score"]
    assert thin["linkbuilding_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"linkbuilding_score": 70, "domain_authority_estimate": 55, "backlink_gaps": []}

    assert (
        await analyze_linkbuilding(
            domain="example.com",
            competitors=[],
            niche="",
            target_keywords=[],
            opportunity_types=[],
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_linkbuilding(
            domain="example.com",
            competitors=[],
            niche="",
            target_keywords=[],
            opportunity_types=[],
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
