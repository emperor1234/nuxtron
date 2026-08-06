"""Unit tests for SEO Planner service (phase-k modules 4–5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_planner_service import (
    analyze_planner_all_modules_signals,
    analyze_planner_execute_signals,
    execute_planner,
    execute_planner_all_modules,
)


def test_heuristic_scales() -> None:
    thin = analyze_planner_execute_signals(goal="Grow SEO", domain="", primary_keyword="", market="")
    rich = analyze_planner_execute_signals(
        goal="Increase non-branded organic traffic by 35% over 90 days with content and technical fixes",
        domain="acme.example.com",
        primary_keyword="enterprise crm software",
        market="us",
    )
    assert rich["planner_score"] > thin["planner_score"]
    assert thin["planner_score"] < 100

    all_mods = analyze_planner_all_modules_signals(
        goal="Increase non-branded organic traffic by 35% over 90 days",
        domain="acme.example.com",
        primary_keyword="crm",
        market="us",
        selected_module_count=40,
    )
    assert all_mods["planner_score"] >= rich["planner_score"]


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"planner_score": 70, "priorities": ["A"], "risks": ["B"]}

    assert (
        await execute_planner(
            goal="Increase organic traffic by 35%",
            domain="example.com",
            primary_keyword="crm",
            market="us",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await execute_planner_all_modules(
            goal="Increase organic traffic across modules",
            domain="example.com",
            primary_keyword="seo",
            market="us",
            selected_module_count=20,
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
