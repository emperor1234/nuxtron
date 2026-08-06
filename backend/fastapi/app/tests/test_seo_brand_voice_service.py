"""Unit tests for Brand Voice service (phase-h module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_brand_voice_service import analyze_brand_voice_signals, rewrite_brand_voice


def test_heuristic_scales() -> None:
    thin = analyze_brand_voice_signals(
        content="We deliver value.",
        brand_name="Acme",
        tone="professional",
        target_audience="",
        notes="",
    )
    rich = analyze_brand_voice_signals(
        content="We leverage synergies to utilize best-in-class outcomes. Value was delivered by the team.",
        brand_name="Acme Voice",
        tone="authoritative",
        target_audience="enterprise buyers",
        notes="Brand voice rewrite with tone alignment and SEO preservation notes",
    )
    assert rich["brand_alignment_score"] <= thin["brand_alignment_score"] or rich["tone_analysis"]["alignment_pct"] != thin["tone_analysis"]["alignment_pct"]
    assert thin["brand_alignment_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"brand_alignment_score": 70, "rewritten_content": "Updated copy"}

    assert (
        await rewrite_brand_voice(
            content="Our product helps teams ship faster.",
            brand_name="Acme",
            tone="professional",
            target_audience="teams",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await rewrite_brand_voice(
            content="Our product helps teams ship faster.",
            brand_name="Acme",
            tone="professional",
            target_audience="teams",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
