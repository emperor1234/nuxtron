"""Unit tests for Trust & Risk Governance service (phase-c module 3)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_trust_risk_governance_service import (
    analyze_trust_risk_governance,
    analyze_trust_risk_governance_signals,
)


def test_heuristic_scales() -> None:
    thin = analyze_trust_risk_governance_signals(
        domain="example.com", policy_scope="seo", controls=[], incidents_last_90d=5, notes=""
    )
    rich = analyze_trust_risk_governance_signals(
        domain="nuxtron.io", policy_scope="seo-and-ai",
        controls=["content_policy", "prompt_review", "rbac", "audit_log"], incidents_last_90d=0, notes="Quarterly drill",
    )
    assert rich["governance_score"] > thin["governance_score"]
    assert rich["governance_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"governance_score": 74, "risk_register": []}

    assert (await analyze_trust_risk_governance(
        domain="example.com", policy_scope="seo-and-ai", controls=["rbac"], incidents_last_90d=0, notes="",
        ollama_json_fn=_llm, system_prompt="s", clean_text_fn=lambda t, _m: t,
    ))["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (await analyze_trust_risk_governance(
        domain="example.com", policy_scope="seo", controls=[], incidents_last_90d=1, notes="",
        ollama_json_fn=_down, system_prompt="s", clean_text_fn=lambda t, _m: t,
    ))["analysis_mode"] == "heuristic"
