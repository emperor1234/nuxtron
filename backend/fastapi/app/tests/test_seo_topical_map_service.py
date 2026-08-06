"""Unit tests for Topical Map service (phase-g module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_topical_map_service import analyze_topical_map_signals, build_topical_map


def test_heuristic_scales() -> None:
    thin = analyze_topical_map_signals(seed_topic="seo", domain="", depth=1, notes="")
    rich = analyze_topical_map_signals(
        seed_topic="enterprise AI SEO automation",
        domain="example.com",
        depth=4,
        notes="Topical map with pillar clusters silo architecture and content gap notes",
    )
    assert rich["topical_authority_score"] > thin["topical_authority_score"]
    assert thin["topical_authority_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"topical_authority_score": 68, "pillar_pages": []}

    assert (
        await build_topical_map(
            seed_topic="AI SEO",
            domain="example.com",
            depth=2,
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await build_topical_map(
            seed_topic="AI SEO",
            domain="example.com",
            depth=2,
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
