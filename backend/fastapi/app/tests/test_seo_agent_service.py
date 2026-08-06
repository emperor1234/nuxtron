"""Unit tests for Autonomous Agent service (phase-b module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_agent_service import (
    analyze_agent_plan,
    analyze_agent_signals,
    normalize_agent_result,
)


def test_heuristic_scales_with_goal_detail() -> None:
    thin = analyze_agent_signals(goal="Grow SEO more", domain="", plan_id="p1")
    rich = analyze_agent_signals(
        goal=(
            "Increase organic traffic and conversions in 6 months with technical SEO "
            "and content pillars for https://nuxtron.io"
        ),
        domain="https://nuxtron.io",
        plan_id="p2",
    )
    assert rich["overall_priority_score"] > thin["overall_priority_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["overall_priority_score"] < 100
    assert len(rich["phases"]) >= 4


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_agent_result(
        {"overall_priority_score": 130, "fallback": True, "phases": []},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["overall_priority_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_agent_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "plan_id": "x",
            "goal": "Traffic growth",
            "overall_priority_score": 71,
            "phases": [{"name": "Research", "tasks": [{"task": "Map keywords", "tool": "keyword_research"}]}],
        }

    result = await analyze_agent_plan(
        goal="Grow organic traffic with content and technical SEO",
        domain="example.com",
        plan_id="plan-llm",
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["overall_priority_score"] == 71


@pytest.mark.asyncio
async def test_analyze_agent_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_agent_plan(
        goal="Improve rankings for core product keywords",
        domain="",
        plan_id="plan-heur",
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["overall_priority_score"] < 100
    assert result["phases"]
