"""Unit tests for Content Creation & Blogging service (phase-j module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_content_creation_blogging_service import (
    analyze_content_creation_blogging_signals,
    plan_content_creation_blogging,
)


def test_heuristic_scales() -> None:
    thin = analyze_content_creation_blogging_signals(
        topic="Blogging",
        content_pillars=[],
        target_keywords=[],
        ai_model="llama3.2",
        word_count_target=800,
        include_multimedia_plan=False,
        publication_frequency="monthly",
        seo_brief="",
        notes="",
    )
    rich = analyze_content_creation_blogging_signals(
        topic="B2B content marketing",
        content_pillars=["strategy", "execution", "measurement"],
        target_keywords=["content marketing", "B2B SEO", "demand gen"],
        ai_model="deepseek-r1:8b",
        word_count_target=3000,
        include_multimedia_plan=True,
        publication_frequency="weekly",
        seo_brief="Focus on pillar pages and internal linking hubs.",
        notes="Quarterly editorial review with multimedia pipeline.",
    )
    assert rich["content_strategy_score"] > thin["content_strategy_score"]
    assert thin["content_strategy_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"content_strategy_score": 73, "pillar_topics": []}

    assert (
        await plan_content_creation_blogging(
            topic="CRM",
            content_pillars=["guides"],
            target_keywords=["crm"],
            ai_model="llama3.2",
            word_count_target=2000,
            include_multimedia_plan=True,
            publication_frequency="weekly",
            seo_brief="",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await plan_content_creation_blogging(
            topic="CRM",
            content_pillars=[],
            target_keywords=[],
            ai_model="llama3.2",
            word_count_target=2000,
            include_multimedia_plan=False,
            publication_frequency="weekly",
            seo_brief="",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
