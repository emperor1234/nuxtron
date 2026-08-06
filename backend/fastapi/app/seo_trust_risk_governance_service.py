"""Trust & Risk Governance — phase-c module 3."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

_BASE_CONTROLS = {"content_policy", "prompt_review", "rbac", "audit_log"}


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_trust_risk_governance_signals(
    *,
    domain: str,
    policy_scope: str,
    controls: list[str],
    incidents_last_90d: int,
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    scope = policy_scope.strip() or "seo-and-ai"
    ctrl = [c.strip() for c in controls if c.strip()] or list(_BASE_CONTROLS)
    incidents = max(0, min(1000, incidents_last_90d))
    notes_text = notes.strip()
    ctrl_set = {c.lower().replace(" ", "_") for c in ctrl}
    coverage = len(ctrl_set & _BASE_CONTROLS) / len(_BASE_CONTROLS)

    governance_score = 40
    governance_score += min(20, int(coverage * 20))
    governance_score += min(14, len(ctrl) * 2)
    governance_score += 6 if "ai" in scope.lower() else 0
    governance_score += 4 if notes_text else 0
    governance_score -= min(24, incidents * 3)
    governance_score = _clamp(governance_score)

    policy_compliance_pct = _clamp(governance_score + 4)
    control_coverage_pct = _clamp(int(round(coverage * 70 + len(ctrl) * 2)))

    risk_register = [
        {
            "risk": "Unreviewed AI-generated content publication",
            "severity": "high" if "content_policy" not in ctrl_set else "medium",
            "owner": "content_ops",
            "mitigation": "Require staged approval before publish",
        },
        {
            "risk": "Source attribution omissions in AI-assisted outputs",
            "severity": "medium",
            "owner": "seo_lead",
            "mitigation": "Enforce citation checks in QA workflow",
        },
    ]
    if incidents >= 2:
        risk_register.append(
            {
                "risk": f"Repeat incidents ({incidents} in 90d) indicate control drift",
                "severity": "high",
                "owner": "security_ops",
                "mitigation": "Run root-cause review and tighten change controls",
            }
        )

    control_gaps = []
    if "prompt_review" not in ctrl_set:
        control_gaps.append({"control": "Prompt policy registry", "gap": "No versioned prompt approvals", "priority": "high"})
    if "audit_log" not in ctrl_set:
        control_gaps.append({"control": "Audit log coverage", "gap": "Incomplete operator action logging", "priority": "high"})

    return {
        "governance_score": governance_score,
        "policy_compliance_pct": policy_compliance_pct,
        "control_coverage_pct": control_coverage_pct,
        "risk_register": risk_register[:5],
        "control_gaps": control_gaps[:5],
        "audit_actions": [
            "Implement monthly control attestations",
            "Track policy exceptions with owners and due dates",
        ],
        "incident_prevention_plan": [
            "Add pre-publish policy linting",
            f"Scope governance checks for {scope} on {site or 'tenant workspace'}",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_trust_risk_governance_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for key in ("governance_score", "policy_compliance_pct", "control_coverage_pct"):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50
    for list_key in ("risk_register", "control_gaps", "audit_actions", "incident_prevention_plan"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_trust_risk_governance(
    *,
    domain: str,
    policy_scope: str,
    controls: list[str],
    incidents_last_90d: int,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    ctrl = controls[:12] if controls else list(_BASE_CONTROLS)
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Policy scope: {clean_text_fn(policy_scope, 200)}. "
        f"Controls: {ctrl}. Incidents in last 90d: {incidents_last_90d}. "
        f"Notes: {clean_text_fn(notes, 500)}. "
        "Return governance scorecard with risk register, control gaps, and prevention plan."
    )
    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("governance_score") is not None or llm_result.get("risk_register"):
            return normalize_trust_risk_governance_result(llm_result, analysis_mode="llm", ai_available=True)
    heuristic = analyze_trust_risk_governance_signals(
        domain=domain, policy_scope=policy_scope, controls=controls,
        incidents_last_90d=incidents_last_90d, notes=notes,
    )
    return normalize_trust_risk_governance_result(heuristic, analysis_mode="heuristic", ai_available=False)
