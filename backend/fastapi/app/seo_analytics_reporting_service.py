"""Analytics, Reporting & Intelligence — phase-i module 1."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_analytics_reporting_signals(
    *,
    goal: str,
    domain: str,
    primary_keyword: str,
    market: str,
) -> dict[str, Any]:
    site = (domain or "example.com").strip()
    kw = primary_keyword.strip()
    mkt = market.strip() or "global"
    goal_text = goal.strip()

    report_score = 42
    report_score += min(16, len(goal_text) // 25)
    report_score += 6 if kw else 0
    report_score += 4 if mkt != "global" else 0
    report_score += 6 if site and site != "example.com" else 0
    report_score = _clamp(report_score)

    return {
        "report_score": report_score,
        "kpi_trends": [
            {"kpi": "organic_clicks", "trend": "up" if report_score >= 55 else "flat", "change_pct": round(report_score / 8, 1)},
            {"kpi": "impressions", "trend": "up" if report_score >= 50 else "flat", "change_pct": round(report_score / 6, 1)},
            {"kpi": "avg_position", "trend": "up" if kw else "flat", "change_pct": round(report_score / 10, 1)},
            {"kpi": "discover_clicks", "trend": "flat", "change_pct": round(report_score / 12, 1)},
        ],
        "module_highlights": [
            {"module": "technical_audit", "impact": "high" if report_score >= 60 else "medium", "note": "Crawl and index health should be tracked weekly"},
            {"module": "content_auditor", "impact": "medium", "note": "Content quality signals need dashboard visibility"},
            {"module": "realtime_monitor", "impact": "high" if kw else "medium", "note": "Volatility alerts for priority keywords"},
        ],
        "risks": ["CTR decay on high-impression queries"] if report_score < 65 else [],
        "next_actions": [
            f"Align reporting to goal: {goal_text[:80]}",
            f"Refresh top pages by impressions for {site}",
            "Run weekly KPI anomaly checks",
        ],
        "recommended_tools": ["looker_studio", "metabase", "search_console_api"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_analytics_reporting_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["report_score"] = _clamp(int(float(out.get("report_score", 50))))
    except (TypeError, ValueError):
        out["report_score"] = 50
    for list_key in ("kpi_trends", "module_highlights", "risks", "next_actions", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def generate_analytics_report(
    *,
    goal: str,
    domain: str,
    primary_keyword: str,
    market: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    site = domain or "example.com"
    prompt = (
        f"Domain: {clean_text_fn(site, 300)}. Goal: {clean_text_fn(goal, 800)}. "
        f"Primary keyword: {clean_text_fn(primary_keyword, 200)}. Market: {clean_text_fn(market, 200)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("report_score") is not None or llm.get("kpi_trends"):
            return normalize_analytics_reporting_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_analytics_reporting_signals(
        goal=goal, domain=site, primary_keyword=primary_keyword, market=market
    )
    return normalize_analytics_reporting_result(heur, analysis_mode="heuristic", ai_available=False)
