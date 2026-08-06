"""Unit tests for AEO service (phase-k module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_aeo_service import analyze_aeo_optimize, analyze_aeo_signals


def test_heuristic_scales() -> None:
    thin = analyze_aeo_signals(
        topic="CRM",
        content="Short content.",
        target_questions=[],
        entity_targets=[],
        schema_types=["FAQPage"],
        use_openlens=False,
        use_playwright_validation=False,
        retrieval_framework="llamaindex",
    )
    rich = analyze_aeo_signals(
        topic="Enterprise CRM software",
        content=" ".join(["CRM software"] * 80),
        target_questions=["What is CRM?", "How does CRM work?", "Why use CRM?"],
        entity_targets=["Brand", "Product", "Category"],
        schema_types=["FAQPage", "HowTo"],
        use_openlens=True,
        use_playwright_validation=True,
        retrieval_framework="llamaindex",
    )
    assert rich["aeo_score"] > thin["aeo_score"]
    assert thin["aeo_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"aeo_score": 74, "snippet_opportunities": []}

    assert (
        await analyze_aeo_optimize(
            topic="CRM",
            content="Content about CRM.",
            target_questions=["What is CRM?"],
            entity_targets=["Brand"],
            schema_types=["FAQPage"],
            use_openlens=True,
            use_playwright_validation=False,
            retrieval_framework="llamaindex",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_aeo_optimize(
            topic="CRM",
            content="Content",
            target_questions=["What is CRM?"],
            entity_targets=[],
            schema_types=["FAQPage"],
            use_openlens=False,
            use_playwright_validation=False,
            retrieval_framework="llamaindex",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
