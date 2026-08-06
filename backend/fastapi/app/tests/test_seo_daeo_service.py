"""Unit tests for production DAEO service (module 13)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_daeo_service import (
    analyze_daeo_readiness,
    analyze_daeo_signals,
    normalize_daeo_result,
)


def test_heuristic_scales_with_canonical_facts() -> None:
    thin = analyze_daeo_signals(
        domain="example.com",
        protocol_targets=["self_hosted_search"],
        canonical_facts=[],
        federation_notes="",
        notes="",
    )
    rich = analyze_daeo_signals(
        domain="https://nuxtron.io",
        protocol_targets=["self_hosted_search", "federated_index", "knowledge_api"],
        canonical_facts=[
            "Nuxtron is an AI SEO platform.",
            "Facts are published as JSON-LD.",
            "Federation API is read-only.",
        ],
        federation_notes="well-known facts endpoint and federated index API documented.",
        notes="Syndicate fact pack hash to partners.",
    )
    assert rich["decentralization_score"] > thin["decentralization_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["decentralization_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_daeo_result(
        {"decentralization_score": 130, "fallback": True, "federation_readiness_score": 80},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["decentralization_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_daeo_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "decentralization_score": 72,
            "federation_readiness_score": 74,
            "protocol_opportunities": [{"protocol": "knowledge_api"}],
        }

    result = await analyze_daeo_readiness(
        domain="nuxtron.io",
        protocol_targets=["knowledge_api"],
        canonical_facts=["Brand fact"],
        federation_notes="API",
        notes="",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["decentralization_score"] == 72


@pytest.mark.asyncio
async def test_analyze_daeo_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_daeo_readiness(
        domain="example.com",
        protocol_targets=["federated_index"],
        canonical_facts=[],
        federation_notes="",
        notes="",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["decentralization_score"] < 100
