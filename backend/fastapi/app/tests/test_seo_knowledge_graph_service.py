"""Unit tests for Knowledge Graph service (phase-e module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_knowledge_graph_service import analyze_knowledge_graph, analyze_knowledge_graph_signals


def test_heuristic_scales() -> None:
    thin = analyze_knowledge_graph_signals(domain="example.com", seed_entities=[], notes="")
    rich = analyze_knowledge_graph_signals(
        domain="global.example",
        seed_entities=["Brand", "Product", "Category", "Persona", "Use case"],
        notes="Entity audit complete",
    )
    assert rich["graph_health_score"] > thin["graph_health_score"]
    assert thin["graph_health_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"graph_health_score": 68, "entities": []}

    assert (
        await analyze_knowledge_graph(
            domain="example.com",
            seed_entities=["Brand"],
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_knowledge_graph(
            domain="example.com",
            seed_entities=[],
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
