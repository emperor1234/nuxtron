"""Unit tests for production Entity SEO service (module 10)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_entity_service import analyze_entity_seo, analyze_entity_signals, normalize_entity_result


def test_heuristic_extracts_named_entities() -> None:
    thin = analyze_entity_signals(content="Short text.", topic="")
    rich = analyze_entity_signals(
        content="Entity SEO helps Acme Corp and Jane Doe. Acme Corp is a software company.",
        topic="Entity SEO",
    )
    assert rich["entity_seo_score"] >= thin["entity_seo_score"]
    assert len(rich["entities_found"]) >= 1
    assert rich["analysis_mode"] == "heuristic"
    assert rich["entity_coverage_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_entity_result(
        {"entity_coverage_score": 120, "fallback": True, "entities_found": []},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["entity_coverage_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_entity_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "entity_coverage_score": 73,
            "entities_found": [{"name": "Entity SEO", "type": "Concept", "salience": 0.77}],
        }

    result = await analyze_entity_seo(
        content="Entity SEO content",
        topic="Entity SEO",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["entities_found"][0]["entity"] == "Entity SEO"


@pytest.mark.asyncio
async def test_analyze_entity_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_entity_seo(
        content="Acme Corp provides Entity SEO tooling.",
        topic="Entity SEO",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert "entities_found" in result
    assert "fallback" not in result
