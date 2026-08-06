"""Unit tests for Performance service (phase-h module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_performance_service import analyze_performance_signals, audit_performance


def test_heuristic_scales() -> None:
    thin = analyze_performance_signals(
        url="http://example.com",
        target_device="mobile",
        target_region="lhr1",
        connection="3g",
        browser="chrome",
        notes="slow blocking render issues",
    )
    rich = analyze_performance_signals(
        url="https://example.com/pricing",
        target_device="desktop",
        target_region="iad1",
        connection="wifi",
        browser="chrome",
        notes="Performance audit with stable vitals and optimized critical path notes",
    )
    assert rich["performance_score"] > thin["performance_score"]
    assert thin["performance_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"performance_score": 74, "core_web_vitals": {"lcp_ms": 2200}}

    assert (
        await audit_performance(
            url="https://example.com",
            target_device="mobile",
            target_region="lhr1",
            connection="4g",
            browser="chrome",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await audit_performance(
            url="https://example.com",
            target_device="mobile",
            target_region="lhr1",
            connection="4g",
            browser="chrome",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
