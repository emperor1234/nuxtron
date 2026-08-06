"""Unit tests for Agency Platform service (phase-i module 2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_agency_platform_service import analyze_agency_platform, analyze_agency_platform_signals


def test_heuristic_scales() -> None:
    thin = analyze_agency_platform_signals(
        agency_name="Agency", workspaces=["one"], governance_focus="", notes=""
    )
    rich = analyze_agency_platform_signals(
        agency_name="Northstar SEO Agency",
        workspaces=["acme", "northstar", "velocity", "orbit"],
        governance_focus="rbac reporting standards and SLA governance",
        notes="Multi-tenant workspace health audit with governance focus notes",
    )
    assert rich["platform_health_score"] > thin["platform_health_score"]
    assert thin["platform_health_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"platform_health_score": 68, "workspace_health": []}

    assert (
        await analyze_agency_platform(
            agency_name="Northstar",
            workspaces=["acme"],
            governance_focus="rbac",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_agency_platform(
            agency_name="Northstar",
            workspaces=["acme"],
            governance_focus="rbac",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
