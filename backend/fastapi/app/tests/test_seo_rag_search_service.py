"""Unit tests for RAG Search service (phase-f module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_rag_search_service import analyze_rag_search_signals, query_rag_search


def test_heuristic_scales() -> None:
    thin = analyze_rag_search_signals(query="seo", site_domain="", content_corpus="", top_k=3, notes="")
    rich = analyze_rag_search_signals(
        query="enterprise keyword research workflow",
        site_domain="docs.example.com",
        content_corpus=" ".join(["keyword clustering guide with examples"] * 30),
        top_k=5,
        notes="Docs corpus",
    )
    assert rich["confidence"] > thin["confidence"]
    assert rich["confidence"] < 0.99
    assert len(rich["search_results"]) >= len(thin["search_results"])


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"search_results": [], "answer_synthesis": "Answer"}

    assert (
        await query_rag_search(
            query="keyword research",
            site_domain="example.com",
            content_corpus="",
            top_k=3,
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    out = await query_rag_search(
        query="keyword research",
        site_domain="example.com",
        content_corpus="",
        top_k=3,
        notes="",
        ollama_json_fn=_down,
        system_prompt="s",
        clean_text_fn=lambda t, _m: t,
    )
    assert out["analysis_mode"] == "heuristic"
    assert out["confidence"] < 0.99
