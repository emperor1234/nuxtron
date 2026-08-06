"""Unit tests for AI Article Writer service (phase-j module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_content_writer_service import (
    analyze_content_writer_signals,
    write_seo_article,
)


def test_heuristic_scales() -> None:
    thin = analyze_content_writer_signals(topic="SEO", keywords=[], word_count=400, tone="", brief="")
    rich = analyze_content_writer_signals(
        topic="Enterprise SaaS SEO playbook",
        keywords=["saas seo", "b2b seo", "organic growth"],
        word_count=2500,
        tone="authoritative",
        brief="Include case studies and actionable framework sections.",
    )
    assert rich["seo_score"] > thin["seo_score"]
    assert thin["seo_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"seo_score": 74, "article": "# Title\n\nBody"}

    assert (
        await write_seo_article(
            topic="CRM",
            keywords=["crm"],
            word_count=1200,
            tone="professional",
            brief="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await write_seo_article(
            topic="CRM",
            keywords=["crm"],
            word_count=1200,
            tone="professional",
            brief="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
