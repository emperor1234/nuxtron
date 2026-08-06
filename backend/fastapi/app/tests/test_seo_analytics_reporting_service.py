"""Unit tests for Analytics Reporting service (phase-i module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_analytics_reporting_service import (
    analyze_analytics_reporting_signals,
    generate_analytics_report,
)


def test_heuristic_scales() -> None:
    thin = analyze_analytics_reporting_signals(
        goal="Grow traffic", domain="example.com", primary_keyword="", market=""
    )
    rich = analyze_analytics_reporting_signals(
        goal="Increase organic revenue by improving CTR on commercial landing pages across priority clusters",
        domain="acme.example.com",
        primary_keyword="enterprise seo platform",
        market="us",
    )
    assert rich["report_score"] > thin["report_score"]
    assert thin["report_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"report_score": 70, "kpi_trends": []}

    assert (
        await generate_analytics_report(
            goal="Increase organic traffic across core product pages",
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
        await generate_analytics_report(
            goal="Increase organic traffic across core product pages",
            domain="example.com",
            primary_keyword="crm",
            market="us",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
