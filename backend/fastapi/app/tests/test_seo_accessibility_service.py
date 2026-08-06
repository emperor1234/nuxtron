"""Unit tests for Accessibility service (phase-f module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_accessibility_service import analyze_accessibility_signals, audit_accessibility


def test_heuristic_scales() -> None:
    thin = analyze_accessibility_signals(url="http://x.com", standard="WCAG2.1A", notes="")
    rich = analyze_accessibility_signals(
        url="https://example.com/pricing",
        standard="WCAG2.1AA",
        notes="Accessibility audit with keyboard nav and contrast review notes",
    )
    assert rich["accessibility_score"] > thin["accessibility_score"]
    assert thin["accessibility_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"accessibility_score": 68, "issues": []}

    assert (
        await audit_accessibility(
            url="https://example.com",
            standard="WCAG2.1AA",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await audit_accessibility(
            url="https://example.com",
            standard="WCAG2.1AA",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
