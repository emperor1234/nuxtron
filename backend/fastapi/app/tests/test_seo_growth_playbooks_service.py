"""Unit tests for Growth Playbooks service (phase-c module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_growth_playbooks_service import analyze_growth_playbooks, analyze_growth_playbooks_signals


def test_heuristic_scales() -> None:
    thin = analyze_growth_playbooks_signals(objective="Grow", domain="", target_channels=[], weekly_capacity_hours=5, notes="")
    rich = analyze_growth_playbooks_signals(
        objective="Increase qualified pipeline from organic and AI-assisted demand across search and email",
        domain="nuxtron.io", target_channels=["search", "social", "email"], weekly_capacity_hours=30, notes="Weekly KPI cadence",
    )
    assert rich["automation_readiness_score"] > thin["automation_readiness_score"]
    assert rich["automation_readiness_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"automation_readiness_score": 73, "playbooks": []}

    llm = await analyze_growth_playbooks(
        objective="Grow pipeline", domain="", target_channels=["search"], weekly_capacity_hours=20, notes="",
        ollama_json_fn=_llm, system_prompt="s", clean_text_fn=lambda t, _m: t,
    )
    assert llm["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    heur = await analyze_growth_playbooks(
        objective="Grow pipeline", domain="", target_channels=[], weekly_capacity_hours=10, notes="",
        ollama_json_fn=_down, system_prompt="s", clean_text_fn=lambda t, _m: t,
    )
    assert heur["analysis_mode"] == "heuristic"
