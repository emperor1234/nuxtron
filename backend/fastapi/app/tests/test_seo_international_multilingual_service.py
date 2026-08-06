"""Unit tests for International & Multilingual SEO service (phase-d module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_international_multilingual_service import (
    analyze_international_multilingual,
    analyze_international_multilingual_signals,
)


def test_heuristic_scales() -> None:
    thin = analyze_international_multilingual_signals(
        domain="example.com", locales=[], current_hreflang_map="", notes=""
    )
    rich = analyze_international_multilingual_signals(
        domain="global.example",
        locales=["en-us", "es-es", "de-de"],
        current_hreflang_map="en-us https://global.example/en-us/\nx-default https://global.example/",
        notes="Hreflang baseline audit",
    )
    assert rich["readiness_score"] > thin["readiness_score"]
    assert thin["readiness_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"readiness_score": 70, "hreflang_coverage_pct": 68}

    assert (
        await analyze_international_multilingual(
            domain="example.com",
            locales=["en-us"],
            current_hreflang_map="",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_international_multilingual(
            domain="example.com",
            locales=[],
            current_hreflang_map="",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
