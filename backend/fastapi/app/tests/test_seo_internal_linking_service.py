"""Unit tests for Internal Linking service (phase-e module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_internal_linking_service import analyze_internal_linking_signals, suggest_internal_linking


def test_heuristic_scales() -> None:
    thin = analyze_internal_linking_signals(page_url="https://example.com/a", page_content="", target_urls=[], notes="")
    rich = analyze_internal_linking_signals(
        page_url="https://example.com/guide",
        page_content=" ".join(["context"] * 80),
        target_urls=["/pricing", "/features", "/blog/seo", "/docs"],
        notes="Hub page",
    )
    assert rich["linking_score"] > thin["linking_score"]
    assert thin["linking_score"] < 100
    assert rich["opportunities"]


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"linking_score": 71, "suggestions": [{"from_url": "https://x.com", "to_url": "/p"}]}

    assert (
        await suggest_internal_linking(
            page_url="https://example.com/guide",
            page_content="",
            target_urls=["/pricing"],
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await suggest_internal_linking(
            page_url="https://example.com/guide",
            page_content="",
            target_urls=[],
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
