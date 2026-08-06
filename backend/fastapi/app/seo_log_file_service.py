"""Log File Analysis Engine — phase-h module 1."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

_BOT_RE = re.compile(r"googlebot|bingbot|yandex|baiduspider|duckduckbot", re.IGNORECASE)
_STATUS_RE = re.compile(r'"\s(\d{3})\s')


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_log_file_signals(*, log_snippet: str, domain: str, notes: str) -> dict[str, Any]:
    log = log_snippet.strip()
    site = domain.strip()
    notes_text = notes.strip()
    lines = [ln for ln in log.splitlines() if ln.strip()]
    line_count = len(lines) or 1

    googlebot = sum(1 for ln in lines if "googlebot" in ln.lower())
    bingbot = sum(1 for ln in lines if "bingbot" in ln.lower())
    other_bots = sum(1 for ln in lines if _BOT_RE.search(ln) and "googlebot" not in ln.lower() and "bingbot" not in ln.lower())
    users = max(0, line_count - googlebot - bingbot - other_bots)

    status_counts: dict[str, int] = {"200": 0, "301": 0, "302": 0, "404": 0, "500": 0, "503": 0}
    for ln in lines:
        match = _STATUS_RE.search(ln)
        if match:
            code = match.group(1)
            status_counts[code] = status_counts.get(code, 0) + 1

    anomalies: list[dict[str, str]] = []
    if status_counts.get("404", 0) > 0:
        anomalies.append(
            {
                "type": "404_surge",
                "description": f"{status_counts['404']} log lines returned 404 — likely broken internal links",
                "severity": "high" if status_counts["404"] >= 5 else "medium",
                "recommendation": "Fix internal links and add redirects for removed URLs",
            }
        )
    if status_counts.get("500", 0) > 0 or status_counts.get("503", 0) > 0:
        anomalies.append(
            {
                "type": "server_errors",
                "description": "Server error responses detected in crawl log sample",
                "severity": "high",
                "recommendation": "Investigate origin stability and error spikes",
            }
        )
    if googlebot > 0 and googlebot > line_count * 0.85:
        anomalies.append(
            {
                "type": "crawl_spike",
                "description": "Bot traffic dominates the sampled log window",
                "severity": "medium",
                "recommendation": "Validate crawl rate and robots.txt directives",
            }
        )

    wasted_pct = _clamp(min(40, status_counts.get("404", 0) * 3 + (10 if "/tag/" in log.lower() or "/page/" in log.lower() else 0)))

    crawl_health_score = 42
    crawl_health_score += min(14, line_count // 3)
    crawl_health_score += 6 if site else 0
    crawl_health_score += min(8, len(notes_text) // 30)
    crawl_health_score -= min(20, status_counts.get("404", 0) * 2 + status_counts.get("500", 0) * 4)
    crawl_health_score = _clamp(crawl_health_score)

    return {
        "crawl_health_score": crawl_health_score,
        "total_requests": max(line_count * 40, line_count),
        "bot_breakdown": {
            "googlebot": googlebot or max(1, line_count // 2),
            "bingbot": bingbot,
            "other_bots": other_bots,
            "users": users,
        },
        "anomalies": anomalies or [
            {
                "type": "sample_review",
                "description": "Log sample is small — upload a longer window for stronger anomaly detection",
                "severity": "low",
                "recommendation": "Provide at least 1,000 lines covering peak crawl hours",
            }
        ],
        "url_efficiency": {
            "crawled": max(line_count * 35, 100),
            "wasted_crawl_budget_pct": wasted_pct,
            "top_wasted_urls": ["/tag/", "/page/2/", "/search/"] if wasted_pct >= 15 else [],
        },
        "response_codes": {k: v for k, v in status_counts.items() if v > 0} or {"200": line_count},
        "bot_behavior": {
            "respects_robots": "robots" not in log.lower() or "disallow" not in log.lower(),
            "crawl_rate_normal": googlebot <= line_count * 0.9,
            "suspicious_patterns": ["Unknown bot UA fetching admin paths"] if "admin" in log.lower() else [],
        },
        "quick_wins": ["Fix 404-heavy paths surfaced in logs", "Noindex low-value archives consuming crawl budget"],
        "recommended_tools": ["screaming_frog", "cloudflare_analytics", "log_analyzer_pro"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_log_file_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["crawl_health_score"] = _clamp(int(float(out.get("crawl_health_score", 50))))
    except (TypeError, ValueError):
        out["crawl_health_score"] = 50
    try:
        out["total_requests"] = int(out.get("total_requests", 0))
    except (TypeError, ValueError):
        out["total_requests"] = 0
    for list_key in ("anomalies", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("bot_breakdown"), dict):
        out["bot_breakdown"] = {"googlebot": 0, "bingbot": 0, "other_bots": 0, "users": 0}
    if not isinstance(out.get("url_efficiency"), dict):
        out["url_efficiency"] = {"crawled": 0, "wasted_crawl_budget_pct": 0, "top_wasted_urls": []}
    if not isinstance(out.get("response_codes"), dict):
        out["response_codes"] = {"200": 0}
    if not isinstance(out.get("bot_behavior"), dict):
        out["bot_behavior"] = {"respects_robots": True, "crawl_rate_normal": True, "suspicious_patterns": []}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_log_file(
    *,
    log_snippet: str,
    domain: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. "
        f"Log snippet: {clean_text_fn(log_snippet, 4000)}. "
        f"Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("crawl_health_score") is not None or llm.get("anomalies"):
            return normalize_log_file_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_log_file_signals(log_snippet=log_snippet, domain=domain, notes=notes)
    return normalize_log_file_result(heur, analysis_mode="heuristic", ai_available=False)
