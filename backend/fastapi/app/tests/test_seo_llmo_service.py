"""Unit tests for production LLMO service (module 4)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_llmo_service import analyze_llmo_brand, analyze_llmo_signals, normalize_llmo_result


def test_heuristic_scales_with_claims() -> None:
    thin = analyze_llmo_signals(
        brand="Acme",
        domain="",
        key_claims=[],
        competitors=[],
        page={"fetch_ok": False},
    )
    rich = analyze_llmo_signals(
        brand="Acme",
        domain="acme.com",
        key_claims=[
            "Founded in 2019 with 40% YoY growth",
            "Serves 2,000 customers in Europe",
            "Offers transparent pricing",
            "ISO 27001 certified",
        ],
        competitors=["Globex"],
        page={"fetch_ok": True, "meta_description": "Acme software", "has_canonical": True},
    )
    assert rich["brand_ai_score"] > thin["brand_ai_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert "gpt4o" in rich["model_representations"]


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_llmo_result(
        {"brand_ai_score": 120, "fallback": True, "accuracy_risk": "low", "consistency_score": 80},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["brand_ai_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_llmo_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "brand_ai_score": 73,
            "accuracy_risk": "medium",
            "consistency_score": 71,
            "model_representations": {"gpt4o": "Stable"},
        }

    with patch(
        "backend.fastapi.app.seo_llmo_service.fetch_page_signals",
        new=AsyncMock(return_value={"fetch_ok": True, "url": "https://acme.com"}),
    ):
        result = await analyze_llmo_brand(
            brand="Acme",
            domain="acme.com",
            key_claims=["Claim one"],
            competitors=[],
            ollama_json_fn=_llm,
            system_prompt="sys",
            clean_text_fn=lambda t, _m: t,
        )
    assert result["analysis_mode"] == "llm"
    assert result["brand_ai_score"] == 73


@pytest.mark.asyncio
async def test_analyze_llmo_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    with patch(
        "backend.fastapi.app.seo_llmo_service.fetch_page_signals",
        new=AsyncMock(return_value={"fetch_ok": False}),
    ):
        result = await analyze_llmo_brand(
            brand="Acme",
            domain="acme.com",
            key_claims=[],
            competitors=[],
            ollama_json_fn=_down,
            system_prompt="sys",
            clean_text_fn=lambda t, _m: t,
        )
    assert result["analysis_mode"] == "heuristic"
    assert result["accuracy_risk"] in ("low", "medium", "high")
