"""Unit tests for Content Auditor service (phase-e module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_content_auditor_service import analyze_content_auditor, analyze_content_auditor_signals


def test_heuristic_scales() -> None:
    thin = analyze_content_auditor_signals(content="Short.", source_url="", topic="", target_model="", notes="")
    rich = analyze_content_auditor_signals(
        content=(
            "According to https://example.com/report the market grew 12% in 2024 with documented methodology. "
            "Teams should review primary research before publishing benchmarks."
        ),
        source_url="https://example.com/article",
        topic="SEO benchmarks",
        target_model="gpt-4o",
        notes="Editorial review",
    )
    assert rich["quality_score"] > thin["quality_score"]
    assert thin["quality_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"quality_score": 72, "fact_checks": []}

    assert (
        await analyze_content_auditor(
            content="Article body with claims.",
            source_url="",
            topic="",
            target_model="",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_content_auditor(
            content="Article body.",
            source_url="",
            topic="",
            target_model="",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
