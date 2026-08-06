"""Growth Playbooks Automation — phase-c module 2."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_growth_playbooks_signals(
    *,
    objective: str,
    domain: str,
    target_channels: list[str],
    weekly_capacity_hours: int,
    notes: str,
) -> dict[str, Any]:
    obj = objective.strip()
    site = domain.strip()
    channels = [c.strip() for c in target_channels if c.strip()] or ["search", "social", "email"]
    capacity = max(1, min(200, weekly_capacity_hours))
    notes_text = notes.strip()
    obj_words = len(re.findall(r"\b\w+\b", obj))

    automation_readiness_score = 38
    automation_readiness_score += min(18, obj_words)
    automation_readiness_score += min(14, len(channels) * 3)
    automation_readiness_score += min(12, capacity // 4)
    automation_readiness_score += 6 if site else 0
    automation_readiness_score += 4 if "kpi" in notes_text.lower() or "cadence" in notes_text.lower() else 0
    automation_readiness_score = _clamp(automation_readiness_score)

    playbooks = [
        {
            "name": "Demand Capture Loop",
            "goal": f"Advance objective: {obj[:80]}",
            "owner": "growth_ops",
            "cadence": "weekly",
            "status": "ready" if capacity >= 12 else "needs_work",
            "expected_lift_pct": _clamp(8 + len(channels) * 2),
        },
        {
            "name": "Channel Reinforcement Sprint",
            "goal": f"Distribute wins across {', '.join(channels[:3])}",
            "owner": "seo_team",
            "cadence": "weekly",
            "status": "needs_work" if capacity < 16 else "ready",
            "expected_lift_pct": _clamp(6 + len(channels)),
        },
    ]

    return {
        "automation_readiness_score": automation_readiness_score,
        "playbooks": playbooks,
        "execution_timeline": [
            {"week": 1, "focus": "Instrumentation and baseline", "deliverables": ["Event map", "Source tagging QA"]},
            {"week": 2, "focus": "Playbook launch", "deliverables": ["Content refresh batch", "Distribution schedule"]},
            {"week": 3, "focus": "Optimization loop", "deliverables": ["KPI variance analysis", "Creative iterations"]},
        ],
        "measurement_framework": [
            {"metric": "assisted_revenue", "target": "+10%", "frequency": "weekly"},
            {"metric": "conversion_rate", "target": "+6%", "frequency": "weekly"},
        ],
        "blocked_dependencies": [] if site else ["Domain context missing for channel-specific playbooks"],
        "next_best_actions": [
            "Automate weekly KPI snapshots",
            "Maintain channel-specific experiment backlog",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_growth_playbooks_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["automation_readiness_score"] = _clamp(int(float(out.get("automation_readiness_score", 50))))
    except (TypeError, ValueError):
        out["automation_readiness_score"] = 50
    for list_key in ("playbooks", "execution_timeline", "measurement_framework", "blocked_dependencies", "next_best_actions"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_growth_playbooks(
    *,
    objective: str,
    domain: str,
    target_channels: list[str],
    weekly_capacity_hours: int,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    channels = target_channels[:8] if target_channels else ["search", "social", "email"]
    prompt = (
        f"Objective: {clean_text_fn(objective, 300)}. Domain: {clean_text_fn(domain, 300)}. "
        f"Target channels: {channels}. Weekly capacity hours: {weekly_capacity_hours}. "
        f"Notes: {clean_text_fn(notes, 500)}. "
        "Return automated playbook execution plan with cadence, measurement, and dependency risks."
    )
    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("automation_readiness_score") is not None or llm_result.get("playbooks"):
            return normalize_growth_playbooks_result(llm_result, analysis_mode="llm", ai_available=True)
    heuristic = analyze_growth_playbooks_signals(
        objective=objective, domain=domain, target_channels=target_channels,
        weekly_capacity_hours=weekly_capacity_hours, notes=notes,
    )
    return normalize_growth_playbooks_result(heuristic, analysis_mode="heuristic", ai_available=False)
