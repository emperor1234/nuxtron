"""Unit tests for Landing Page service (phase-g module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_landing_service import analyze_landing_page_signals, generate_landing_page


def test_heuristic_scales() -> None:
    thin = analyze_landing_page_signals(
        product_name="App",
        target_keyword="seo",
        audience="general",
        schema_types=["Product"],
        notes="",
    )
    rich = analyze_landing_page_signals(
        product_name="Nuxtron SEO Suite",
        target_keyword="enterprise seo automation platform",
        audience="marketing_teams",
        schema_types=["Product", "FAQPage", "SoftwareApplication"],
        notes="Landing page brief with conversion hooks and schema markup notes",
    )
    assert rich["landing_page_score"] > thin["landing_page_score"]
    assert thin["landing_page_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"landing_page_score": 70, "hero": {}}

    assert (
        await generate_landing_page(
            product_name="Nuxtron",
            target_keyword="seo tools",
            audience="general",
            schema_types=["Product", "FAQPage"],
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await generate_landing_page(
            product_name="Nuxtron",
            target_keyword="seo tools",
            audience="general",
            schema_types=["Product"],
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
