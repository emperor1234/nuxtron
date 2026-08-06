"""Unit tests for Video SEO service (phase-d module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_video_seo_service import analyze_video_seo_signals, optimize_video_seo


def test_heuristic_scales() -> None:
    thin = analyze_video_seo_signals(title="Vid", description="", transcript="", platform="youtube", keywords=[])
    rich = analyze_video_seo_signals(
        title="Keyword Research Tutorial for SEO Teams",
        description="Workflow guide",
        transcript="We cover seed keywords, clustering, and reporting cadence for SEO teams.",
        platform="youtube",
        keywords=["keyword research", "seo"],
    )
    assert rich["seo_score"] > thin["seo_score"]
    assert thin["seo_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"seo_score": 75, "optimized_title": "Guide"}

    assert (
        await optimize_video_seo(
            title="Guide",
            description="",
            transcript="",
            platform="youtube",
            keywords=[],
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await optimize_video_seo(
            title="Guide",
            description="",
            transcript="",
            platform="youtube",
            keywords=[],
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
