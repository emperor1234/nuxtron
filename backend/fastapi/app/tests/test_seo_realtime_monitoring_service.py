"""Unit tests for Real-Time Monitoring service (phase-e module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_realtime_monitoring_service import (
    analyze_realtime_monitoring,
    analyze_realtime_monitoring_signals,
)


def test_heuristic_scales() -> None:
    thin = analyze_realtime_monitoring_signals(domain="x.com", tracked_queries=[], lookback_hours=24, notes="")
    rich = analyze_realtime_monitoring_signals(
        domain="monitor.example",
        tracked_queries=["brand", "product", "pricing", "reviews"],
        lookback_hours=72,
        notes="Volatility baseline",
    )
    assert rich["volatility_score"] > thin["volatility_score"]
    assert thin["volatility_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"volatility_score": 70, "query_snapshots": []}

    assert (
        await analyze_realtime_monitoring(
            domain="example.com",
            tracked_queries=["q"],
            lookback_hours=24,
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_realtime_monitoring(
            domain="example.com",
            tracked_queries=[],
            lookback_hours=24,
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
