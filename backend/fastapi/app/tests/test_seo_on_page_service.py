"""Unit tests for On-Page Optimizer service (phase-j module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_on_page_service import analyze_on_page, analyze_on_page_signals


def test_heuristic_scales() -> None:
    thin = analyze_on_page_signals(url="http://example.com", content="", focus_keyword="seo")
    rich = analyze_on_page_signals(
        url="https://example.com/guide",
        content=" ".join(["crm software"] * 120),
        focus_keyword="crm software",
    )
    assert rich["seo_score"] > thin["seo_score"]
    assert thin["seo_score"] < 100
    assert rich.get("signals")


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"overall_score": 71, "recommendations": []}

    out = await analyze_on_page(
        url="https://example.com",
        content="content",
        focus_keyword="crm",
        ollama_json_fn=_llm,
        system_prompt="s",
        clean_text_fn=lambda t, _m: t,
    )
    assert out["analysis_mode"] == "llm"
    assert out["seo_score"] == 71

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_on_page(
            url="https://example.com",
            content="content",
            focus_keyword="crm",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
