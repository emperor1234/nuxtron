"""SEO Execution Planner — phase-k modules 4–5."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _default_workflow() -> list[dict[str, str]]:
    return [
        {"phase": "Research", "module": "keyword_research", "action": "Build intent clusters and quick-win terms", "path": "/seo/keywords"},
        {"phase": "Content Blueprint", "module": "content_brief", "action": "Generate SERP-informed brief and article outline", "path": "/seo/content-brief"},
        {"phase": "Content Production", "module": "writer", "action": "Draft E-E-A-T aligned article and metadata", "path": "/seo/writer"},
        {"phase": "Technical and Structured Data", "module": "technical_and_schema", "action": "Apply technical fixes and JSON-LD schema", "path": "/seo/technical"},
        {"phase": "Authority and Distribution", "module": "linkbuilding", "action": "Execute backlink outreach and internal links", "path": "/seo/linkbuilding"},
        {"phase": "AI Search Coverage", "module": "geo_aeo_llmo", "action": "Optimize for AI overviews and answer engines", "path": "/seo/geo"},
    ]


def analyze_planner_execute_signals(
    *,
    goal: str,
    domain: str,
    primary_keyword: str,
    market: str,
) -> dict[str, Any]:
    g = goal.strip()
    site = domain.strip()
    kw = primary_keyword.strip()
    mkt = market.strip() or "global"

    planner_score = 42
    planner_score += min(18, len(g) // 25)
    planner_score += 6 if site else 0
    planner_score += min(12, len(kw.split()) * 3)
    planner_score += 4 if mkt else 0
    planner_score = _clamp(planner_score)

    return {
        "planner_score": planner_score,
        "priorities": [
            f"Validate keyword clusters around '{kw or 'core topic'}' for {site or 'target domain'}",
            "Ship one pillar brief and publish an MVP article this sprint",
            "Close technical/schema gaps before scaling content velocity",
        ],
        "risks": [
            "Thin topical coverage if brief and technical work run in parallel without owners",
            "SERP volatility in competitive markets without weekly rank monitoring",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def analyze_planner_all_modules_signals(
    *,
    goal: str,
    domain: str,
    primary_keyword: str,
    market: str,
    selected_module_count: int,
) -> dict[str, Any]:
    base = analyze_planner_execute_signals(goal=goal, domain=domain, primary_keyword=primary_keyword, market=market)
    score = _clamp(base["planner_score"] + min(12, selected_module_count // 4))
    base["planner_score"] = score
    base["mission"] = f"Autonomous SEO execution across {selected_module_count} modules for {domain or 'target property'}"
    base["escalation_rules"] = [
        "Escalate when two or more modules report critical regressions in the same week",
        "Require human approval before publishing schema or migration changes at scale",
    ]
    return base


def normalize_planner_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["planner_score"] = _clamp(int(float(out.get("planner_score", 55))))
    except (TypeError, ValueError):
        out["planner_score"] = 55
    for list_key in ("priorities", "risks", "next_actions", "escalation_rules"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("mission"), str):
        out["mission"] = out.get("mission") or ""
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def execute_planner(
    *,
    goal: str,
    domain: str,
    primary_keyword: str,
    market: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Create concise SEO priorities for goal '{clean_text_fn(goal, 500)}'. "
        f"Domain: {domain}. Primary keyword: {primary_keyword}. Market: {market}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("priorities") or llm.get("risks"):
            llm.setdefault("planner_score", 68)
            return normalize_planner_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_planner_execute_signals(goal=goal, domain=domain, primary_keyword=primary_keyword, market=market)
    return normalize_planner_result(heur, analysis_mode="heuristic", ai_available=False)


async def execute_planner_all_modules(
    *,
    goal: str,
    domain: str,
    primary_keyword: str,
    market: str,
    selected_module_count: int,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Create a concise autonomous SEO command strategy for goal '{clean_text_fn(goal, 500)}'. "
        f"Domain: {domain}. Primary keyword: {primary_keyword}. Market: {market}. "
        f"Module count: {selected_module_count}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("priorities") or llm.get("mission") or llm.get("risks"):
            llm.setdefault("planner_score", 70)
            return normalize_planner_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_planner_all_modules_signals(
        goal=goal,
        domain=domain,
        primary_keyword=primary_keyword,
        market=market,
        selected_module_count=selected_module_count,
    )
    return normalize_planner_result(heur, analysis_mode="heuristic", ai_available=False)


def default_planner_workflow() -> list[dict[str, str]]:
    return _default_workflow()
