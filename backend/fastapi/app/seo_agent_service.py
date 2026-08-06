"""
Autonomous SEO Agent Engine — phase-b module 2.

Builds multi-phase SEO execution plans from goal and domain signals.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_TRAFFIC_RE = re.compile(r"\b(traffic|sessions|visitors|clicks|impressions)\b", re.IGNORECASE)
_CONVERSION_RE = re.compile(r"\b(conversion|revenue|leads|signup|sales|mql)\b", re.IGNORECASE)
_RANK_RE = re.compile(r"\b(rank|position|serp|keyword|organic)\b", re.IGNORECASE)
_TECH_RE = re.compile(r"\b(technical|core web vitals|schema|crawl|index)\b", re.IGNORECASE)
_CONTENT_RE = re.compile(r"\b(content|blog|article|pillar|copy)\b", re.IGNORECASE)
_LOCAL_RE = re.compile(r"\b(local|maps|gmb|near me)\b", re.IGNORECASE)
_TIMEFRAME_RE = re.compile(r"\b(\d+)\s*(month|week|quarter|year)s?\b", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_VAGUE_RE = re.compile(r"\b(improve|better|more|grow)\b", re.IGNORECASE)

_DEFAULT_KPIS = ["organic_sessions", "avg_position", "conversions"]


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _hours_to_timeframe(total_hours: int) -> str:
    if total_hours <= 12:
        return "2-3 weeks"
    if total_hours <= 24:
        return "4-6 weeks"
    if total_hours <= 40:
        return "8-10 weeks"
    return "12-16 weeks"


def _normalize_task(raw: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(raw, str):
        return {"task": raw.strip(), "tool": "seo_workflow", "priority": "medium", "hours": 2}
    hours = raw.get("hours")
    if hours is None:
        hours = raw.get("estimated_hours", 2)
    try:
        hours_val = max(1, int(float(hours)))
    except (TypeError, ValueError):
        hours_val = 2
    return {
        "task": str(raw.get("task") or "SEO task").strip(),
        "tool": str(raw.get("tool") or "seo_workflow").strip(),
        "priority": str(raw.get("priority") or "medium").strip(),
        "hours": hours_val,
    }


def _normalize_phase(raw: dict[str, Any], index: int) -> dict[str, Any]:
    name = str(raw.get("name") or raw.get("phase") or f"Phase {index + 1}").strip()
    if name.isdigit():
        name = str(raw.get("name") or f"Phase {name}").strip()
    tasks_raw = raw.get("tasks") if isinstance(raw.get("tasks"), list) else []
    tasks = [_normalize_task(t) for t in tasks_raw[:8]]
    kpis = raw.get("kpis") if isinstance(raw.get("kpis"), list) else []
    return {
        "phase": name,
        "description": str(raw.get("description") or "").strip(),
        "tasks": tasks,
        "kpis": [str(k).strip() for k in kpis[:6] if str(k).strip()],
        "expected_outcome": str(raw.get("expected_outcome") or "").strip(),
    }


def analyze_agent_signals(*, goal: str, domain: str, plan_id: str) -> dict[str, Any]:
    """Deterministic agent plan from goal and domain signals."""
    goal_text = goal.strip()
    site = domain.strip()
    goal_lower = goal_text.lower()

    goal_words = len(re.findall(r"\b\w+\b", goal_text))
    traffic = bool(_TRAFFIC_RE.search(goal_lower))
    conversion = bool(_CONVERSION_RE.search(goal_lower))
    rank_focus = bool(_RANK_RE.search(goal_lower))
    tech_focus = bool(_TECH_RE.search(goal_lower))
    content_focus = bool(_CONTENT_RE.search(goal_lower))
    local_focus = bool(_LOCAL_RE.search(goal_lower))
    timeframe_match = _TIMEFRAME_RE.search(goal_lower)
    bracket_count = len(_BRACKET_RE.findall(goal_text))
    vague_count = len(_VAGUE_RE.findall(goal_lower))

    parsed = urlparse(site if "://" in site else f"https://{site}") if site else None
    https_ok = bool(parsed and parsed.scheme == "https")

    overall_priority_score = 38
    overall_priority_score += min(16, goal_words)
    overall_priority_score += 8 if traffic else 0
    overall_priority_score += 8 if conversion else 0
    overall_priority_score += 6 if rank_focus else 0
    overall_priority_score += 6 if site else 0
    overall_priority_score += 6 if https_ok else 0
    overall_priority_score += 4 if timeframe_match else 0
    overall_priority_score -= min(12, vague_count * 3)
    overall_priority_score -= min(10, bracket_count * 4)
    overall_priority_score = _clamp(overall_priority_score)

    domain_label = site or "target property"
    phases: list[dict[str, Any]] = [
        {
            "phase": "Research",
            "description": f"Validate demand and opportunity for: {goal_text[:120]}",
            "tasks": [
                {
                    "task": "Cluster priority keywords aligned to the stated goal",
                    "tool": "keyword_research",
                    "priority": "high",
                    "hours": 3,
                },
                {
                    "task": "Audit top competitor SERP coverage and content gaps",
                    "tool": "competitor_analysis",
                    "priority": "high",
                    "hours": 2,
                },
            ],
            "expected_outcome": "Prioritized keyword and competitor gap map",
            "kpis": ["keyword_coverage", "share_of_voice"],
        },
        {
            "phase": "Implementation",
            "description": f"Fix technical blockers on {domain_label}",
            "tasks": [
                {
                    "task": "Run technical SEO audit (crawl, indexation, CWV)",
                    "tool": "technical_audit",
                    "priority": "high" if tech_focus else "medium",
                    "hours": 3,
                },
                {
                    "task": "Deploy structured data for key templates",
                    "tool": "schema_generator",
                    "priority": "medium",
                    "hours": 2,
                },
            ],
            "expected_outcome": "Critical technical issues remediated",
            "kpis": ["indexed_pages", "cwv_pass_rate"],
        },
        {
            "phase": "Content",
            "description": "Publish and optimize pages tied to goal outcomes",
            "tasks": [
                {
                    "task": "Create pillar page and supporting cluster briefs",
                    "tool": "content_brief",
                    "priority": "high" if content_focus or rank_focus else "medium",
                    "hours": 5,
                },
                {
                    "task": "Refresh underperforming URLs with updated intent coverage",
                    "tool": "ai_writer",
                    "priority": "medium",
                    "hours": 4,
                },
            ],
            "expected_outcome": "Goal-aligned content shipped and interlinked",
            "kpis": ["content_velocity", "engagement_rate"],
        },
        {
            "phase": "Monitor",
            "description": "Track execution impact and iterate weekly",
            "tasks": [
                {
                    "task": "Configure rank and conversion tracking dashboards",
                    "tool": "rank_tracker",
                    "priority": "medium",
                    "hours": 2,
                },
                {
                    "task": "Run weekly agent review loop with KPI deltas",
                    "tool": "seo_workflow",
                    "priority": "medium",
                    "hours": 1,
                },
            ],
            "expected_outcome": "Closed-loop reporting against goal KPIs",
            "kpis": _DEFAULT_KPIS,
        },
    ]

    if local_focus:
        phases[1]["tasks"].append(
            {
                "task": "Optimize local landing pages and citation consistency",
                "tool": "local_seo",
                "priority": "high",
                "hours": 3,
            }
        )

    estimated_total_hours = sum(task["hours"] for phase in phases for task in phase["tasks"])
    expected_outcomes = [p["expected_outcome"] for p in phases if p.get("expected_outcome")]
    priorities: list[str] = []
    if traffic:
        priorities.append("Organic traffic growth")
    if conversion:
        priorities.append("Conversion efficiency")
    if rank_focus:
        priorities.append("Keyword visibility")
    if tech_focus:
        priorities.append("Technical health")
    if not priorities:
        priorities = ["Content quality", "Technical health", "Authority building"]

    risks: list[str] = []
    if not site:
        risks.append("No domain provided — plan assumes property access for technical tasks")
    if vague_count >= 2:
        risks.append("Goal language is broad; tighten KPI targets before execution")
    if not timeframe_match:
        risks.append("No explicit timeline in goal — default cadence assumes 8-10 weeks")

    return {
        "plan_id": plan_id,
        "goal": goal_text,
        "overall_priority_score": overall_priority_score,
        "agent_score": overall_priority_score,
        "phases": phases,
        "estimated_total_hours": estimated_total_hours,
        "estimated_timeframe": _hours_to_timeframe(estimated_total_hours),
        "expected_outcomes": expected_outcomes,
        "success_metrics": expected_outcomes[:6],
        "kpis": _DEFAULT_KPIS,
        "priorities": priorities[:5],
        "risks": risks[:4],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "goal_word_count": goal_words,
            "has_domain": bool(site),
            "traffic_goal": traffic,
            "conversion_goal": conversion,
            "local_goal": local_focus,
        },
    }


def normalize_agent_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    score_raw = out.get("overall_priority_score", out.get("agent_score", 50))
    try:
        score = _clamp(int(float(score_raw)))
    except (TypeError, ValueError):
        score = 50
    out["overall_priority_score"] = score
    out["agent_score"] = score

    phases_raw = out.get("phases") if isinstance(out.get("phases"), list) else []
    out["phases"] = [_normalize_phase(p, i) for i, p in enumerate(phases_raw) if isinstance(p, dict)]

    if not isinstance(out.get("kpis"), list):
        out["kpis"] = list(_DEFAULT_KPIS)
    if not isinstance(out.get("priorities"), list):
        out["priorities"] = []
    if not isinstance(out.get("risks"), list):
        out["risks"] = []
    if not isinstance(out.get("expected_outcomes"), list):
        outcomes = out.get("success_metrics")
        out["expected_outcomes"] = outcomes if isinstance(outcomes, list) else []
    if not isinstance(out.get("success_metrics"), list):
        out["success_metrics"] = out["expected_outcomes"]

    try:
        total_hours = int(float(out.get("estimated_total_hours", 0)))
    except (TypeError, ValueError):
        total_hours = sum(
            task.get("hours", 0)
            for phase in out["phases"]
            for task in phase.get("tasks", [])
            if isinstance(task, dict)
        )
    out["estimated_total_hours"] = total_hours
    if not out.get("estimated_timeframe"):
        out["estimated_timeframe"] = _hours_to_timeframe(total_hours or 20)

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_agent_plan(
    *,
    goal: str,
    domain: str,
    plan_id: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run autonomous agent planning."""
    prompt = (
        f"Create a comprehensive autonomous SEO action plan.\n"
        f"Goal: {clean_text_fn(goal, 800)}.\n"
        f"Domain: {clean_text_fn(domain, 300)}.\n"
        f"Plan ID: {plan_id}.\n\n"
        "Break the goal into 3-4 phases (Research, Implementation, Content, Monitoring). "
        "For each phase list specific tasks with the SEO tool to use, priority level, and estimated hours. "
        "Include expected outcomes and KPIs. Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("phases") or llm_result.get("plan_id"):
            if not llm_result.get("goal"):
                llm_result["goal"] = goal.strip()
            return normalize_agent_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_agent_signals(goal=goal, domain=domain, plan_id=plan_id)
    return normalize_agent_result(heuristic, analysis_mode="heuristic", ai_available=False)
