"""Unit tests for production SAGEO service (module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_sageo_service import (
    analyze_sageo_plan,
    analyze_sageo_signals,
    normalize_sageo_result,
)


def test_heuristic_scales_with_source_material() -> None:
    thin = analyze_sageo_signals(
        topic="Widget SEO",
        search_intent="informational",
        source_material="",
        target_engines=["ChatGPT"],
        notes="",
    )
    rich = analyze_sageo_signals(
        topic="Widget SEO",
        search_intent="informational",
        source_material=(
            "## What is widget SEO?\n"
            "Widget SEO improves visibility by 42% in 2024.\n"
            "How does it work? See https://example.com/report\n"
            "- Use structured data\n"
        ),
        target_engines=["Google AI Overview", "ChatGPT", "Perplexity"],
        notes="Enterprise focus",
    )
    assert rich["sageo_score"] > thin["sageo_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert len(rich["generative_entry_points"]) == 3


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_sageo_result(
        {"sageo_score": 150, "fallback": True, "intent_map": {"primary_intent": "informational"}},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["sageo_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_sageo_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "sageo_score": 77,
            "intent_map": {"primary_intent": "informational", "supporting_intents": ["commercial"]},
            "source_priorities": [],
        }

    result = await analyze_sageo_plan(
        topic="Widget SEO",
        search_intent="informational",
        source_material="Draft content",
        target_engines=["ChatGPT"],
        notes="",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["sageo_score"] == 77


@pytest.mark.asyncio
async def test_analyze_sageo_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_sageo_plan(
        topic="Widget SEO",
        search_intent="informational",
        source_material="",
        target_engines=["Perplexity"],
        notes="",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "sageo_score" in result
    assert "fallback" not in result
