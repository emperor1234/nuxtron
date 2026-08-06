"""Unit tests for Keyword Research service (phase-j module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_keyword_research_service import (
    analyze_keyword_research_signals,
    research_keywords,
)


def test_heuristic_scales() -> None:
    thin = analyze_keyword_research_signals(seed_keyword="seo", domain="", country="US", count=5)
    rich = analyze_keyword_research_signals(
        seed_keyword="enterprise crm software",
        domain="acme.example.com",
        country="GB",
        count=40,
    )
    assert rich["keyword_research_score"] > thin["keyword_research_score"]
    assert thin["keyword_research_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"keyword_research_score": 68, "keywords": [{"keyword": "crm"}]}

    assert (
        await research_keywords(
            seed_keyword="crm",
            domain="example.com",
            country="US",
            count=10,
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await research_keywords(
            seed_keyword="crm",
            domain="example.com",
            country="US",
            count=10,
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
