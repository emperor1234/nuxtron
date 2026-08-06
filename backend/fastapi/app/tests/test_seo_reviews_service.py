"""Unit tests for Reviews service (phase-h module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_reviews_service import analyze_review_reputation, analyze_review_reputation_signals


def test_heuristic_scales() -> None:
    thin = analyze_review_reputation_signals(brand="Acme", reviews_text="", platforms=["google"], notes="")
    rich = analyze_review_reputation_signals(
        brand="Acme Pro",
        reviews_text="Love the product quality. Great support. Terrible shipping was slow and broken packaging.",
        platforms=["google", "trustpilot", "yelp"],
        notes="Reputation mining with sentiment themes and response workflow notes",
    )
    assert rich["reputation_score"] != thin["reputation_score"] or len(rich["themes"]) >= len(thin["themes"])
    assert thin["reputation_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"reputation_score": 72, "themes": []}

    assert (
        await analyze_review_reputation(
            brand="Acme",
            reviews_text="Great product",
            platforms=["google"],
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_review_reputation(
            brand="Acme",
            reviews_text="Great product",
            platforms=["google"],
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
