"""Unit tests for Integrations Automation service (phase-i module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_integrations_automation_service import (
    analyze_integrations_automation,
    analyze_integrations_automation_signals,
)


def test_heuristic_scales() -> None:
    thin = analyze_integrations_automation_signals(
        domain="example.com", integrations=["search_console"], automation_goals=["alerting"], notes=""
    )
    rich = analyze_integrations_automation_signals(
        domain="ops.example.com",
        integrations=["search_console", "analytics", "slack", "webhooks", "crm"],
        automation_goals=["alerting", "reporting", "content_sync", "incident_routing"],
        notes="Integration health review with automation backlog and connector SLA notes",
    )
    assert rich["integration_coverage_score"] > thin["integration_coverage_score"]
    assert thin["integration_coverage_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"integration_coverage_score": 66, "automation_backlog": []}

    assert (
        await analyze_integrations_automation(
            domain="example.com",
            integrations=["search_console", "slack"],
            automation_goals=["alerting"],
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_integrations_automation(
            domain="example.com",
            integrations=["search_console"],
            automation_goals=["alerting"],
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
