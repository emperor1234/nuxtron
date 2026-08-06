"""Unit tests for Local SEO service (phase-d module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_local_seo_service import analyze_local_seo_signals, optimize_local_seo


def test_heuristic_scales() -> None:
    thin = analyze_local_seo_signals(
        business_name="Acme", category="", location="", website="", description=""
    )
    rich = analyze_local_seo_signals(
        business_name="Sunrise Dental",
        category="Dental",
        location="Austin, TX",
        website="https://sunrise.example",
        description="Full-service dental clinic with cosmetic and emergency care for families.",
    )
    assert rich["local_seo_score"] > thin["local_seo_score"]
    assert thin["local_seo_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"local_seo_score": 68, "gmb_optimization": {"score": 65}}

    assert (
        await optimize_local_seo(
            business_name="Acme",
            category="",
            location="",
            website="",
            description="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await optimize_local_seo(
            business_name="Acme",
            category="",
            location="",
            website="",
            description="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
