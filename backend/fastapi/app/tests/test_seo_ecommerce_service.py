"""Unit tests for eCommerce SEO service (phase-b module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_ecommerce_service import (
    analyze_ecommerce_signals,
    normalize_ecommerce_result,
    optimize_ecommerce_seo,
)


def test_heuristic_scales_with_description_and_keywords() -> None:
    thin = analyze_ecommerce_signals(
        product_name="Widget",
        category="",
        description="",
        keywords=[],
    )
    rich = analyze_ecommerce_signals(
        product_name="Wireless Noise-Cancelling Headphones",
        category="Electronics / Audio",
        description=(
            "Premium wireless headphones with adaptive noise cancellation and 40-hour battery "
            "for commuters who need focus and comfort on long trips."
        ),
        keywords=["wireless headphones", "noise cancelling", "bluetooth"],
    )
    assert rich["seo_score"] > thin["seo_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["seo_score"] < 100
    assert rich["bullet_points"]


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_ecommerce_result(
        {"seo_score": 130, "fallback": True, "bullet_points": []},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["seo_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_optimize_ecommerce_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"seo_score": 77, "optimized_title": "Product Title", "bullet_points": ["A"]}

    result = await optimize_ecommerce_seo(
        product_name="Headphones",
        category="Audio",
        description="Wireless ANC",
        keywords=["headphones"],
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["seo_score"] == 77


@pytest.mark.asyncio
async def test_optimize_ecommerce_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await optimize_ecommerce_seo(
        product_name="Mug",
        category="Kitchen",
        description="Ceramic mug",
        keywords=["coffee mug"],
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["seo_score"] < 100
