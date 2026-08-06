"""Unit tests for Media SEO service (phase-g module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_media_service import analyze_media_seo_signals, audit_media_seo


def test_heuristic_scales() -> None:
    thin = analyze_media_seo_signals(url="http://x.com", check_compression=False, notes="")
    rich = analyze_media_seo_signals(
        url="https://example.com/gallery",
        check_compression=True,
        notes="Media audit with img hero and img gallery compression review notes",
    )
    assert rich["media_seo_score"] > thin["media_seo_score"]
    assert thin["media_seo_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"media_seo_score": 72, "issues": []}

    assert (
        await audit_media_seo(
            url="https://example.com",
            check_compression=True,
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await audit_media_seo(
            url="https://example.com",
            check_compression=True,
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
