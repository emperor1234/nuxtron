"""Unit tests for production CXAO service (phase-b module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_cxao_service import (
    analyze_cxao_experience,
    analyze_cxao_signals,
    normalize_cxao_result,
)


def test_heuristic_scales_with_rag_and_events() -> None:
    thin = analyze_cxao_signals(
        assistant_surface="chat_assistant",
        primary_intent="help",
        conversation_context="user asks",
        success_criteria=[],
        ai_model="llama3",
        rag_enabled=False,
        chat_ui_framework="nextjs",
        posthog_enabled=False,
        posthog_events=[],
    )
    rich = analyze_cxao_signals(
        assistant_surface="copilot",
        primary_intent="Guide users through pricing comparison with clear evidence and CTA",
        conversation_context=(
            "User asks pricing and ROI. Assistant gives summary, steps, and click to book a demo."
        ),
        success_criteria=["clarity", "cta follow-through"],
        ai_model="deepseek-r1",
        rag_enabled=True,
        chat_ui_framework="nextjs",
        posthog_enabled=True,
        posthog_events=["chat_started", "cta_clicked"],
    )
    assert rich["experience_optimization_score"] > thin["experience_optimization_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["experience_optimization_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_cxao_result(
        {"experience_optimization_score": 130, "fallback": True, "conversation_clarity_score": 80},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["experience_optimization_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_cxao_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "experience_optimization_score": 78,
            "conversation_clarity_score": 76,
            "answer_relevance_score": 77,
            "actionability_score": 75,
        }

    result = await analyze_cxao_experience(
        assistant_surface="chat_assistant",
        primary_intent="Onboarding",
        conversation_context="User needs setup steps.",
        success_criteria=["clarity"],
        ai_model="llama3",
        rag_enabled=True,
        chat_ui_framework="nextjs",
        posthog_enabled=False,
        posthog_events=[],
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["experience_optimization_score"] == 78


@pytest.mark.asyncio
async def test_analyze_cxao_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_cxao_experience(
        assistant_surface="chat_assistant",
        primary_intent="help",
        conversation_context="short",
        success_criteria=[],
        ai_model="llama3",
        rag_enabled=False,
        chat_ui_framework="nextjs",
        posthog_enabled=False,
        posthog_events=[],
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["experience_optimization_score"] < 100
