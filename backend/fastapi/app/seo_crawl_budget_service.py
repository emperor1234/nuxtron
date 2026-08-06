"""Crawl Budget Optimizer — phase-e module 5."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

_LOW_VALUE_RE = re.compile(r"/tag/|/page/|/author/|\?|/search/|/filter", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_crawl_budget_signals(
    *,
    domain: str,
    sample_urls: list[str],
    log_snippet: str,
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    urls = [u.strip() for u in sample_urls if u.strip()] or ["/", "/blog/", "/tag/", "/page/2/"]
    log = log_snippet.strip()
    notes_text = notes.strip()
    low_value = [u for u in urls if _LOW_VALUE_RE.search(u)]
    log_low = len(_LOW_VALUE_RE.findall(log)) if log else 0

    crawl_budget_score = 40
    crawl_budget_score += min(16, len(urls) * 2)
    crawl_budget_score += 6 if log else 0
    crawl_budget_score += 4 if notes_text else 0
    crawl_budget_score -= min(16, len(low_value) * 4 + log_low)
    crawl_budget_score = _clamp(crawl_budget_score)

    waste_pct = _clamp(min(45, 12 + len(low_value) * 5 + log_low * 2))
    high = [u for u in urls if u in {"/", "/pricing", "/features"} or u == "/"]
    medium = [u for u in urls if u not in high and u not in low_value]
    if not high:
        high = urls[:2]
    if not medium:
        medium = [u for u in urls if u not in high][:2]
    low = low_value or [u for u in urls if u not in high and u not in medium]

    issues = []
    if low_value:
        issues.append(
            {
                "type": "thin_archive",
                "severity": "high" if len(low_value) >= 2 else "medium",
                "detail": "Low-value archive or parameterized paths consume crawl budget",
                "fix": "Noindex low-value archives and reduce internal prominence",
            }
        )
    if log and "404" in log:
        issues.append(
            {
                "type": "soft_404",
                "severity": "medium",
                "detail": "Log snippet references 404 responses",
                "fix": "Fix broken URLs and redirect obsolete paths",
            }
        )

    return {
        "crawl_budget_score": crawl_budget_score,
        "waste_pct": waste_pct,
        "priority_buckets": {"high": high[:5], "medium": medium[:5], "low": low[:5]},
        "issues": issues,
        "bot_efficiency": {
            "googlebot_efficiency": round(min(0.82, 0.55 + len(high) * 0.04), 2),
            "bingbot_efficiency": round(min(0.75, 0.48 + len(high) * 0.03), 2),
        },
        "exclude_recommendations": ["/tag/*", "/page/*", "*?sort=*"] if low_value else ["/search/*"],
        "quick_wins": ["Noindex low-value archives", "Consolidate duplicate parameterized URLs"],
        "recommended_tools": ["server_logs", "gsc_crawl_stats", "robots_tester"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_crawl_budget_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["crawl_budget_score"] = _clamp(int(float(out.get("crawl_budget_score", 50))))
    except (TypeError, ValueError):
        out["crawl_budget_score"] = 50
    try:
        out["waste_pct"] = _clamp(int(float(out.get("waste_pct", 20))))
    except (TypeError, ValueError):
        out["waste_pct"] = 20
    if not isinstance(out.get("priority_buckets"), dict):
        out["priority_buckets"] = {"high": [], "medium": [], "low": []}
    for list_key in ("issues", "exclude_recommendations", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("bot_efficiency"), dict):
        out["bot_efficiency"] = {"googlebot_efficiency": 0.6, "bingbot_efficiency": 0.55}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_crawl_budget(
    *,
    domain: str,
    sample_urls: list[str],
    log_snippet: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    samples = sample_urls[:12] if sample_urls else ["/"]
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Sample URLs: {samples}. "
        f"Log snippet: {clean_text_fn(log_snippet, 4000)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("crawl_budget_score") is not None or llm.get("priority_buckets"):
            return normalize_crawl_budget_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_crawl_budget_signals(
        domain=domain, sample_urls=sample_urls, log_snippet=log_snippet, notes=notes,
    )
    return normalize_crawl_budget_result(heur, analysis_mode="heuristic", ai_available=False)
