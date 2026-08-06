"""Unit tests for News Discover service (phase-h module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_news_discover_service import analyze_news_discover, analyze_news_discover_signals


def test_heuristic_scales() -> None:
    thin = analyze_news_discover_signals(domain="example.com", recent_headlines=[], focus_topics=[], notes="")
    rich = analyze_news_discover_signals(
        domain="news.example.com",
        recent_headlines=["AI Search Trends", "Discover Playbook", "Top Stories Signals", "Publisher Freshness"],
        focus_topics=["ai seo", "discover", "news freshness", "top stories"],
        notes="Discover readiness audit with headline velocity and topic authority notes",
    )
    assert rich["discover_readiness_score"] > thin["discover_readiness_score"]
    assert thin["discover_readiness_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"discover_readiness_score": 66, "headline_improvements": []}

    assert (
        await analyze_news_discover(
            domain="example.com",
            recent_headlines=["Headline A"],
            focus_topics=["discover"],
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_news_discover(
            domain="example.com",
            recent_headlines=["Headline A"],
            focus_topics=["discover"],
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
