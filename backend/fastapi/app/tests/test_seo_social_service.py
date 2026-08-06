"""Unit tests for Social SEO service (phase-g module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_social_service import analyze_social_seo_signals, audit_social_seo


def test_heuristic_scales() -> None:
    thin = analyze_social_seo_signals(url="http://x.com", platforms=["twitter"], notes="")
    rich = analyze_social_seo_signals(
        url="https://example.com/blog",
        platforms=["twitter", "facebook", "linkedin", "pinterest"],
        notes="Social distribution audit with OG and Twitter card review notes",
    )
    assert rich["social_seo_score"] > thin["social_seo_score"]
    assert thin["social_seo_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"social_seo_score": 65, "open_graph": {}}

    assert (
        await audit_social_seo(
            url="https://example.com",
            platforms=["twitter", "facebook"],
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await audit_social_seo(
            url="https://example.com",
            platforms=["twitter"],
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
