"""Unit tests for Schema service (phase-f module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_schema_service import analyze_schema_signals, generate_schema_markup


def test_heuristic_scales() -> None:
    thin = analyze_schema_signals(schema_type="Article", content="Short.", url="")
    rich = analyze_schema_signals(
        schema_type="Product",
        content=" ".join(["Detailed product description with features and benefits."] * 20),
        url="https://example.com/product",
    )
    assert rich["schema_score"] > thin["schema_score"]
    assert thin["schema_score"] < 100
    assert rich["json_ld"]


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"schema_score": 70, "schema_json": {"@type": "Article", "name": "Guide"}}

    assert (
        await generate_schema_markup(
            schema_type="Article",
            content="Article body",
            url="https://example.com",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await generate_schema_markup(
            schema_type="Article",
            content="Article body",
            url="https://example.com",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
