"""Unit tests for Programmatic SEO service (phase-b module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_programmatic_service import (
    analyze_programmatic_signals,
    generate_programmatic_seo,
    normalize_programmatic_result,
    parse_programmatic_inputs,
)


def test_parse_frontend_variable_matrix() -> None:
    parsed = parse_programmatic_inputs(
        template_topic="",
        variable_sets=[],
        page_count=10,
        url_template="/[location]-[service]",
        title_template="Best [service] in [location]",
        meta_description_template="Find [service] in [location].",
        variables={"location": ["Austin"], "service": ["plumbers", "roofers"]},
    )
    assert len(parsed["variable_sets"]) == 2
    assert parsed["template_topic"]


def test_heuristic_scales_with_matrix() -> None:
    thin = analyze_programmatic_signals(
        template_topic="pages",
        variable_sets=[{"x": "1"}],
        page_count=1,
    )
    rich = analyze_programmatic_signals(
        template_topic="local services",
        variable_sets=[],
        page_count=6,
        url_template="/[location]-[service]",
        title_template="Best [service] in [location] | Brand",
        meta_description_template="Trusted [service] providers in [location] with reviews and pricing details.",
        variables={"location": ["NYC", "LA"], "service": ["plumbers"]},
    )
    assert rich["template_quality_score"] > thin["template_quality_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["template_quality_score"] < 100
    assert rich["pages"]


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_programmatic_result(
        {"template_quality_score": 130, "fallback": True, "page_templates": []},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["template_quality_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_generate_programmatic_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"template_quality_score": 73, "page_templates": [{"title": "T"}]}

    result = await generate_programmatic_seo(
        template_topic="widgets",
        variable_sets=[{"region": "US"}],
        page_count=2,
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["template_quality_score"] == 73


@pytest.mark.asyncio
async def test_generate_programmatic_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await generate_programmatic_seo(
        template_topic="guides",
        variable_sets=[{"topic": "alpha"}],
        page_count=1,
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["template_quality_score"] < 100
