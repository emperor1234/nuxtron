"""Unit tests for production SXO service (module 7)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_sxo_service import analyze_sxo_experience, analyze_sxo_signals, normalize_sxo_result


def test_heuristic_scales_with_rich_content() -> None:
    thin = analyze_sxo_signals(url="http://example.com/x", content="Tiny.", keywords=["other"])
    rich = analyze_sxo_signals(
        url="https://example.com/seo-guide",
        content="## SEO guide\nLearn SEO today.\n- Improve titles\nGet started now.",
        keywords=["seo guide", "seo"],
    )
    assert rich["sxo_score"] > thin["sxo_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["sxo_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_sxo_result(
        {"sxo_score": 130, "fallback": True, "dwell_time_score": 80, "ctr_score": 70, "ux_quality_score": 75},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["sxo_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_sxo_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "sxo_score": 76,
            "dwell_time_score": 74,
            "ctr_score": 78,
            "ux_quality_score": 75,
            "improvements": [],
        }

    result = await analyze_sxo_experience(
        url="https://example.com/page",
        content="Content body",
        keywords=["seo"],
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["sxo_score"] == 76


@pytest.mark.asyncio
async def test_analyze_sxo_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_sxo_experience(
        url="https://example.com/page",
        content="",
        keywords=["seo"],
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "sxo_score" in result
    assert "fallback" not in result


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/",
        "https://example.com",
        "https://x.co/a",
    ],
)
def test_heuristic_no_keywords_slugless_url_does_not_crash(url: str) -> None:
    # Regression: empty keywords + a URL with no usable slug tokens previously
    # raised IndexError via _slug_keywords(page_url)[0]. It must degrade to a
    # safe default instead of crashing the endpoint with a 500.
    out = analyze_sxo_signals(url=url, content="", keywords=[])
    assert out["analysis_mode"] == "heuristic"
    assert isinstance(out["sxo_score"], int)
    assert out["ctr_optimization"]["optimized_title"]


@pytest.mark.asyncio
async def test_analyze_sxo_heuristic_no_keywords_root_url() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_sxo_experience(
        url="https://example.com/",
        content="",
        keywords=[],
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "sxo_score" in result
