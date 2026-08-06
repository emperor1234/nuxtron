"""Unit tests for production VSO service (module 6)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_vso_service import analyze_vso_optimize, analyze_vso_signals, normalize_vso_result


def test_heuristic_scales_with_conversational_content() -> None:
    thin = analyze_vso_signals(topic="coffee shops", content="Coffee.", local_area="")
    rich = analyze_vso_signals(
        topic="coffee shops",
        content="What is the best coffee near me? You can find great local cafes by checking reviews.",
        local_area="London",
    )
    assert rich["vso_score"] > thin["vso_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["vso_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_vso_result(
        {"vso_score": 120, "fallback": True, "voice_query_coverage": 80, "conversational_score": 70},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["vso_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_vso_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "vso_score": 72,
            "voice_query_coverage": 68,
            "conversational_score": 66,
            "voice_keywords": [],
        }

    result = await analyze_vso_optimize(
        topic="coffee shops",
        content="Coffee shops serve espresso.",
        local_area="London",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["vso_score"] == 72


@pytest.mark.asyncio
async def test_analyze_vso_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_vso_optimize(
        topic="coffee shops",
        content="What is the best coffee shop near me?",
        local_area="",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "vso_score" in result
    assert "fallback" not in result
