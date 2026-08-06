"""Unit tests for Multi-Channel Activation service (phase-c module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_multi_channel_activation_service import (
    analyze_multi_channel_activation,
    analyze_multi_channel_activation_signals,
)


def test_heuristic_scales() -> None:
    thin = analyze_multi_channel_activation_signals(
        campaign_name="Q1", primary_offer="", channels=[], audience_segments=[], notes=""
    )
    rich = analyze_multi_channel_activation_signals(
        campaign_name="Q3 Demand Expansion Campaign",
        primary_offer="SEO + AI Growth Blueprint",
        channels=["search", "social", "email", "community"],
        audience_segments=["new_visitors", "returning_users", "product_eval"],
        notes="Unified message framework",
    )
    assert rich["activation_readiness_score"] > thin["activation_readiness_score"]
    assert rich["message_consistency_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"activation_readiness_score": 72, "channel_plan": []}

    assert (await analyze_multi_channel_activation(
        campaign_name="Launch", primary_offer="Offer", channels=["search"], audience_segments=["new"], notes="",
        ollama_json_fn=_llm, system_prompt="s", clean_text_fn=lambda t, _m: t,
    ))["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (await analyze_multi_channel_activation(
        campaign_name="Launch", primary_offer="", channels=[], audience_segments=[], notes="",
        ollama_json_fn=_down, system_prompt="s", clean_text_fn=lambda t, _m: t,
    ))["analysis_mode"] == "heuristic"
