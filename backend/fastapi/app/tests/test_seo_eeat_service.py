"""Unit tests for production E-E-A-T service (module 9)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_eeat_service import analyze_eeat_score, analyze_eeat_signals, normalize_eeat_result


def test_heuristic_scales_with_author_and_citations() -> None:
    thin = analyze_eeat_signals(content="Short article.", author_bio="", domain="", niche="")
    rich = analyze_eeat_signals(
        content=(
            "In my experience testing tools, results improved. "
            "See https://example.org/study. Reviewed by editorial team."
        ),
        author_bio="Sam Lee, CPA with 10 years experience.",
        domain="https://example.com",
        niche="finance",
    )
    assert rich["eeat_score"] > thin["eeat_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["eeat_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_eeat_result(
        {"eeat_score": 130, "fallback": True, "experience_score": 80, "trust_score": 75},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["eeat_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_eeat_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "eeat_score": 76,
            "experience_score": 74,
            "expertise_score": 78,
            "authority_score": 72,
            "trust_score": 80,
        }

    result = await analyze_eeat_score(
        content="Content body",
        author_bio="Bio",
        domain="example.com",
        niche="saas",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["eeat_score"] == 76


@pytest.mark.asyncio
async def test_analyze_eeat_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_eeat_score(
        content="Article text",
        author_bio="",
        domain="",
        niche="",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "eeat_score" in result
    assert "fallback" not in result
