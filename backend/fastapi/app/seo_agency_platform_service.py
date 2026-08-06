"""Agency & Multi-Tenant Platform — phase-i module 2."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_agency_platform_signals(
    *,
    agency_name: str,
    workspaces: list[str],
    governance_focus: str,
    notes: str,
) -> dict[str, Any]:
    agency = agency_name.strip()
    ws = [w.strip() for w in workspaces if w.strip()] or ["default"]
    focus = governance_focus.strip()
    notes_text = notes.strip()

    platform_health_score = 44
    platform_health_score += min(14, len(ws) * 3)
    platform_health_score += min(10, len(focus) // 8)
    platform_health_score += min(8, len(notes_text) // 30)
    platform_health_score = _clamp(platform_health_score)

    workspace_health = [
        {
            "workspace": name,
            "status": "healthy" if i == 0 and platform_health_score >= 55 else "warning",
            "primary_risk": "None" if i == 0 and platform_health_score >= 60 else "Publishing SLA drift",
        }
        for i, name in enumerate(ws[:5])
    ]

    gov_base = _clamp(platform_health_score - 6)
    return {
        "platform_health_score": platform_health_score,
        "workspace_health": workspace_health,
        "governance": {
            "role_coverage_pct": gov_base,
            "policy_compliance_pct": _clamp(gov_base + 4),
            "audit_trail_score": _clamp(gov_base - 2),
        },
        "sla_risk_accounts": ws[-1:] if len(ws) > 1 and platform_health_score < 65 else [],
        "standardization_gaps": ["Inconsistent naming conventions"] if len(ws) > 2 else [],
        "automation_opportunities": ["Auto-create workspace KPI dashboards"],
        "quick_wins": ["Enforce RBAC baseline for all workspaces", "Standardize weekly reporting cadence"],
        "recommended_tools": ["workspace_templates", "rbac_audit", "tenant_dashboards"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_agency_platform_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["platform_health_score"] = _clamp(int(float(out.get("platform_health_score", 50))))
    except (TypeError, ValueError):
        out["platform_health_score"] = 50
    for list_key in (
        "workspace_health",
        "sla_risk_accounts",
        "standardization_gaps",
        "automation_opportunities",
        "quick_wins",
        "recommended_tools",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("governance"), dict):
        out["governance"] = {"role_coverage_pct": 50, "policy_compliance_pct": 50, "audit_trail_score": 50}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_agency_platform(
    *,
    agency_name: str,
    workspaces: list[str],
    governance_focus: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    ws = workspaces[:12] if workspaces else ["acme"]
    prompt = (
        f"Agency: {clean_text_fn(agency_name, 300)}. Workspaces: {json.dumps(ws)}. "
        f"Governance focus: {clean_text_fn(governance_focus, 300)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("platform_health_score") is not None or llm.get("workspace_health"):
            return normalize_agency_platform_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_agency_platform_signals(
        agency_name=agency_name,
        workspaces=workspaces,
        governance_focus=governance_focus,
        notes=notes,
    )
    return normalize_agency_platform_result(heur, analysis_mode="heuristic", ai_available=False)
