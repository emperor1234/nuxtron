"""Unit tests for production MSVO service (module 12)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_msvo_service import analyze_msvo_signals, analyze_msvo_visibility, normalize_msvo_result


def test_heuristic_scales_with_owned_channels() -> None:
    thin = analyze_msvo_signals(
        brand="Acme",
        topic="CRM",
        target_surfaces=["google"],
        owned_channels=[],
        notes="",
    )
    rich = analyze_msvo_signals(
        brand="Nuxtron",
        topic="AI SEO",
        target_surfaces=["google", "chatgpt", "linkedin", "email"],
        owned_channels=["blog", "linkedin", "email"],
        notes="Consistent Nuxtron messaging across channels.",
    )
    assert rich["visibility_score"] > thin["visibility_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["visibility_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_msvo_result(
        {"visibility_score": 130, "fallback": True, "message_alignment_score": 80},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["visibility_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_msvo_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "visibility_score": 77,
            "surface_coverage": [{"surface": "google_search", "presence_score": 74}],
            "message_alignment_score": 76,
        }

    result = await analyze_msvo_visibility(
        brand="Nuxtron",
        topic="AI SEO",
        target_surfaces=["google"],
        owned_channels=["blog"],
        notes="",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["visibility_score"] == 77


@pytest.mark.asyncio
async def test_analyze_msvo_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_msvo_visibility(
        brand="Nuxtron",
        topic="AI SEO",
        target_surfaces=["google", "chatgpt"],
        owned_channels=[],
        notes="",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "visibility_score" in result
    assert "fallback" not in result
