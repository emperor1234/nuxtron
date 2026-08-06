"""Unit tests for Performance Auto-Fix (phase-k module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_performance_service import (
    analyze_performance_auto_fix_signals,
    apply_performance_auto_fix,
)


def test_heuristic_scales() -> None:
    none = analyze_performance_auto_fix_signals(url="https://example.com", candidates=[])
    rich = analyze_performance_auto_fix_signals(
        url="https://example.com",
        candidates=[
            {"title": "Inline CSS", "estimated_gain_ms": 180},
            {"title": "Defer analytics", "estimated_gain_ms": 120},
        ],
    )
    assert rich["new_performance_score"] >= none["new_performance_score"]
    assert none["new_performance_score"] < 100
    assert len(rich["fixes_applied"]) == 2


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"new_performance_score": 68, "fixes_applied": [{"title": "Fix", "status": "applied"}]}

    assert (
        await apply_performance_auto_fix(
            url="https://example.com",
            candidates=[{"title": "Inline CSS", "estimated_gain_ms": 100}],
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    out = await apply_performance_auto_fix(
        url="https://example.com",
        candidates=[{"title": "Inline CSS", "estimated_gain_ms": 100}],
        ollama_json_fn=_down,
        system_prompt="s",
        clean_text_fn=lambda t, _m: t,
    )
    assert out["analysis_mode"] == "heuristic"
    assert out["new_performance_score"] < 100
