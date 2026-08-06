"""Integrations & Automation Layer — phase-i module 3."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_integrations_automation_signals(
    *,
    domain: str,
    integrations: list[str],
    automation_goals: list[str],
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    connected = [i.strip() for i in integrations if i.strip()] or ["search_console", "analytics"]
    goals = [g.strip() for g in automation_goals if g.strip()] or ["alerting"]
    notes_text = notes.strip()

    integration_coverage_score = 40
    integration_coverage_score += min(18, len(connected) * 3)
    integration_coverage_score += min(12, len(goals) * 3)
    integration_coverage_score += min(8, len(notes_text) // 25)
    integration_coverage_score = _clamp(integration_coverage_score)

    return {
        "integration_coverage_score": integration_coverage_score,
        "connected": connected[:5],
        "missing": ["crm_sync", "incident_webhook"] if integration_coverage_score < 70 else [],
        "automation_backlog": [
            {"workflow": "Daily KPI digest", "impact": "high", "complexity": "low", "owner": "ops"},
            {"workflow": "SERP anomaly to Slack", "impact": "high", "complexity": "medium", "owner": "seo"},
        ],
        "connector_health": [
            {"connector": name, "status": "ok" if i < 2 else "degraded", "latency_ms": 110 + (i * 35)}
            for i, name in enumerate(connected[:4])
        ],
        "event_flow_risks": ["No retry policy on webhook handlers"] if integration_coverage_score < 60 else [],
        "quick_wins": ["Add retry/backoff for webhook failures", "Automate weekly integration health report"],
        "recommended_tools": ["webhooks", "task_queues", "integration_tests"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_integrations_automation_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["integration_coverage_score"] = _clamp(int(float(out.get("integration_coverage_score", 50))))
    except (TypeError, ValueError):
        out["integration_coverage_score"] = 50
    for list_key in ("connected", "missing", "automation_backlog", "connector_health", "event_flow_risks", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_integrations_automation(
    *,
    domain: str,
    integrations: list[str],
    automation_goals: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    ints = integrations[:15] if integrations else ["search_console", "analytics"]
    goals = automation_goals[:10] if automation_goals else ["alerting"]
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Integrations: {json.dumps(ints)}. "
        f"Automation goals: {json.dumps(goals)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("integration_coverage_score") is not None or llm.get("automation_backlog"):
            return normalize_integrations_automation_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_integrations_automation_signals(
        domain=domain,
        integrations=integrations,
        automation_goals=automation_goals,
        notes=notes,
    )
    return normalize_integrations_automation_result(heur, analysis_mode="heuristic", ai_available=False)
