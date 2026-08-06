"""Unit tests for production GXO service (module 8)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_gxo_service import analyze_gxo_optimize, analyze_gxo_signals, normalize_gxo_result


def test_heuristic_scales_with_rich_content() -> None:
    thin = analyze_gxo_signals(topic="CRM", content="CRM tool.", url="")
    rich = analyze_gxo_signals(
        topic="CRM software",
        content=(
            "What is CRM software? CRM is a system for managing customer relationships.\n"
            "- Track leads\n"
            "Growth reached 38% in 2024."
        ),
        url="https://example.com/crm",
    )
    assert rich["gxo_score"] > thin["gxo_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["gxo_score"] < 100
    assert rich["ai_overview_citation_probability"] < 1.0


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_gxo_result(
        {"gxo_score": 140, "fallback": True, "structured_data_score": 80, "comprehensiveness_score": 75},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["gxo_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_gxo_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "gxo_score": 73,
            "ai_overview_citation_probability": 0.41,
            "structured_data_score": 70,
            "schema_recommendations": [],
        }

    result = await analyze_gxo_optimize(
        topic="CRM software",
        content="Content body",
        url="https://example.com/crm",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["gxo_score"] == 73


@pytest.mark.asyncio
async def test_analyze_gxo_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_gxo_optimize(
        topic="CRM software",
        content="What is CRM?",
        url="",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "gxo_score" in result
    assert "fallback" not in result
