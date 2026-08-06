"""Unit tests for Content Brief service (phase-j module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_content_brief_service import (
    analyze_content_brief_signals,
    generate_content_brief,
)


def test_heuristic_scales() -> None:
    thin = analyze_content_brief_signals(topic="SEO", keywords=[], word_count=500, audience="")
    rich = analyze_content_brief_signals(
        topic="Enterprise content marketing strategy",
        keywords=["content marketing", "B2B SEO", "demand gen"],
        word_count=2500,
        audience="marketing directors",
    )
    assert rich["brief_score"] > thin["brief_score"]
    assert thin["brief_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"brief_score": 72, "title": "Guide", "outline": []}

    assert (
        await generate_content_brief(
            topic="CRM",
            keywords=["crm"],
            word_count=1500,
            audience="sales leaders",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await generate_content_brief(
            topic="CRM",
            keywords=["crm"],
            word_count=1500,
            audience="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
