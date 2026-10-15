"""Unit tests for review-only SEO workflow draft helpers."""

from __future__ import annotations

import asyncio

import pytest
from backend.fastapi.app.seo_planner_service import (
    analyze_planner_execute_signals,
    default_planner_workflow,
    execute_planner,
)

pytestmark = pytest.mark.no_legacy


def test_template_suggestions_have_no_synthetic_score_or_site_claims() -> None:
    result = analyze_planner_execute_signals(
        goal="Grow SEO",
        domain="",
        primary_keyword="",
        market="",
    )

    assert result["analysis_mode"] == "heuristic"
    assert result["ai_available"] is False
    assert "planner_score" not in result
    assert all("current ranking" in risk or "without an owner" in risk for risk in result["risks"])


def test_default_sequence_uses_only_current_customer_routes_and_is_review_only() -> None:
    workflow = default_planner_workflow()

    assert [step["phase"] for step in workflow] == [
        "Confirm scope",
        "Validate search evidence",
        "Prepare content",
        "Review results",
    ]
    assert {step["path"] for step in workflow} <= {"", "/seo/keywords", "/content-generation", "/seo/history"}
    assert all("execute" not in step["action"].lower() for step in workflow)


def test_llm_and_fallback_results_are_drafts_without_score_fields() -> None:
    async def exercise() -> None:
        async def _llm(_system: str, _user: str, **_kwargs: object) -> dict[str, object]:
            return {"planner_score": 99, "priorities": ["Review evidence"], "risks": ["Validate scope"]}

        llm_result = await execute_planner(
            goal="Increase organic traffic by 35%",
            domain="example.com",
            primary_keyword="crm",
            market="us",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda text, _max_length: text,
        )
        assert llm_result["analysis_mode"] == "llm"
        assert llm_result["ai_available"] is True
        assert llm_result["priorities"] == ["Review evidence"]
        assert "planner_score" not in llm_result

        async def _down(_system: str, _user: str, **_kwargs: object) -> dict[str, object]:
            return {"fallback": True}

        fallback_result = await execute_planner(
            goal="Increase organic traffic across the workspace",
            domain="example.com",
            primary_keyword="seo",
            market="us",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda text, _max_length: text,
        )
        assert fallback_result["analysis_mode"] == "heuristic"
        assert fallback_result["ai_available"] is False
        assert fallback_result["priorities"]
        assert "planner_score" not in fallback_result

    asyncio.run(exercise())
