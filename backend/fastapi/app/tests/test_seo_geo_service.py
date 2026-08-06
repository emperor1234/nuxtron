"""Unit tests for production GEO service (module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_geo_service import (
    analyze_content_signals,
    analyze_geo_optimize,
    normalize_geo_result,
)


def test_heuristic_penalizes_bracket_placeholders() -> None:
    result = analyze_content_signals(
        topic="GEO marketing",
        content="GEO marketing is a [concise 1-2 sentence definition]. No stats here.",
        serp_context="",
        site_content_context="",
        target_engines=["ChatGPT"],
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["content_signals"]["bracket_placeholders"] >= 1
    assert result["geo_score"] < 75
    for passage in result["optimized_passages"]:
        assert "[" not in passage


def test_heuristic_rewards_stats_and_definition() -> None:
    thin = analyze_content_signals(
        topic="generative engine optimization",
        content="Short note.",
        serp_context="",
        site_content_context="",
        target_engines=["Perplexity"],
    )
    rich = analyze_content_signals(
        topic="generative engine optimization",
        content=(
            "Generative engine optimization is a practice for improving citation in AI answers. "
            "In 2024, 62% of teams reported higher visibility. "
            "## How does GEO work?\n"
            "It combines structure, entities, and citations."
        ),
        serp_context="People also ask: what is GEO?",
        site_content_context="Pillar: /geo-guide",
        target_engines=["Perplexity", "ChatGPT"],
    )
    assert rich["geo_score"] > thin["geo_score"]
    assert rich["factual_density_score"] > thin["factual_density_score"]


def test_normalize_strips_bracket_passages() -> None:
    out = normalize_geo_result(
        {
            "geo_score": 80,
            "citability_score": 70,
            "factual_density_score": 70,
            "question_coverage_score": 70,
            "entity_clarity_score": 70,
            "optimized_passages": [
                "Good passage without placeholders.",
                "Bad [placeholder] line.",
            ],
            "engine_scores": {"ChatGPT": 77},
        },
        analysis_mode="llm",
        ai_available=True,
    )
    assert all("[" not in p for p in out["optimized_passages"])


@pytest.mark.asyncio
async def test_analyze_geo_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "geo_score": 81,
            "citability_score": 80,
            "factual_density_score": 79,
            "question_coverage_score": 78,
            "entity_clarity_score": 77,
            "engine_scores": {"ChatGPT": 81},
            "citation_triggers": [],
            "improvements": [],
            "optimized_passages": ["Final copy without placeholders."],
            "quick_wins": [],
        }

    result = await analyze_geo_optimize(
        topic="GEO",
        content="GEO is a strategy for AI visibility with 40% lift in 2025.",
        target_engines=["ChatGPT"],
        ai_model="test",
        rag_enabled=True,
        serp_context="",
        site_content_context="",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["geo_score"] == 81


@pytest.mark.asyncio
async def test_analyze_geo_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True, "error": "down"}

    result = await analyze_geo_optimize(
        topic="GEO",
        content="Brief.",
        target_engines=["Gemini"],
        ai_model="test",
        rag_enabled=False,
        serp_context="",
        site_content_context="",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["ai_available"] is False
