"""Unit tests for UX service (phase-f module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_ux_service import analyze_ux_conversion_signals, audit_ux_conversion


def test_heuristic_scales() -> None:
    thin = analyze_ux_conversion_signals(url="http://x.com", page_type="blog", traffic_source="direct", notes="")
    rich = analyze_ux_conversion_signals(
        url="https://example.com/pricing",
        page_type="pricing",
        traffic_source="organic",
        notes="High-intent organic landing page with trust layer gaps",
    )
    assert rich["ux_score"] > thin["ux_score"]
    assert thin["ux_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"ux_score": 68, "friction_points": []}

    assert (
        await audit_ux_conversion(
            url="https://example.com",
            page_type="landing",
            traffic_source="organic",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await audit_ux_conversion(
            url="https://example.com",
            page_type="landing",
            traffic_source="organic",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
