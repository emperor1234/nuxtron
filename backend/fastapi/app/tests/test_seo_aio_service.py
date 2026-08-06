"""Unit tests for production AIO service (module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_aio_service import (
    analyze_aio_content_signals,
    analyze_aio_score,
    normalize_aio_result,
)


def test_heuristic_rejects_bracket_templates() -> None:
    result = analyze_aio_content_signals(
        topic="AIO scoring",
        content="AIO scoring is a [concise definition in 1 sentence]. Key facts: [bullet 1].",
    )
    assert result["content_signals"]["bracket_placeholders"] >= 2
    assert all("[" not in p for p in result["optimized_paragraphs"])
    for item in result["improvements"]:
        assert "[" not in str(item.get("before", ""))
        assert "[" not in str(item.get("after", ""))


def test_heuristic_rewards_structure() -> None:
    thin = analyze_aio_content_signals(topic="AIO", content="One long unstructured block without headings.")
    rich = analyze_aio_content_signals(
        topic="AIO",
        content=(
            "AIO is a method for improving machine-readable content.\n\n"
            "## Why AIO matters\n"
            "- Clear headings\n"
            "- Short paragraphs\n"
            "- Definition in the intro"
        ),
    )
    assert rich["structure_score"] > thin["structure_score"]
    assert rich["aio_score"] > thin["aio_score"]


@pytest.mark.asyncio
async def test_analyze_aio_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "aio_score": 77,
            "machine_readability": 76,
            "entity_clarity": 75,
            "structure_score": 74,
            "extractability_score": 73,
            "semantic_density_score": 75,
            "improvements": [],
            "optimized_paragraphs": ["Clean copy."],
        }

    result = await analyze_aio_score(
        topic="AIO",
        content="Structured AIO content with clear sections.",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["aio_score"] == 77


@pytest.mark.asyncio
async def test_analyze_aio_heuristic_fallback() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_aio_score(
        topic="AIO",
        content="Short.",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["ai_available"] is False


def test_normalize_strips_bracket_improvements() -> None:
    out = normalize_aio_result(
        {
            "aio_score": 70,
            "machine_readability": 70,
            "entity_clarity": 70,
            "structure_score": 70,
            "extractability_score": 70,
            "semantic_density_score": 70,
            "improvements": [
                {
                    "area": "extractability",
                    "action": "Fix",
                    "before": "N/A",
                    "after": "Key facts: [bullet 1], [bullet 2]",
                }
            ],
            "optimized_paragraphs": ["ok", "bad [x]"],
        },
        analysis_mode="llm",
        ai_available=True,
    )
    assert len(out["optimized_paragraphs"]) == 1
    if out["improvements"]:
        assert "after" not in out["improvements"][0] or "[" not in str(out["improvements"][0].get("after", ""))
