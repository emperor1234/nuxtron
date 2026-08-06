"""Technical SEO Audit — phase-k module 1."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _flatten_issues(raw: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if isinstance(raw.get("issues"), list):
        for item in raw["issues"]:
            if isinstance(item, dict):
                sev = str(item.get("severity", item.get("level", "info"))).lower()
                if sev in {"high", "medium"}:
                    sev = "warning"
                elif sev not in {"critical", "warning", "info"}:
                    sev = "info"
                issues.append(
                    {
                        "type": str(item.get("type", item.get("category", "issue"))),
                        "severity": sev,
                        "detail": str(item.get("detail", item.get("description", ""))),
                        "fix": str(item.get("fix", item.get("suggestion", ""))),
                    }
                )
        return issues
    bucket_map = {"critical": "critical", "high": "warning", "medium": "warning", "low": "info"}
    issues_obj = raw.get("issues")
    for bucket, severity in bucket_map.items():
        if isinstance(issues_obj, dict):
            bucket_items = issues_obj.get(bucket, [])
        else:
            bucket_items = raw.get(bucket, [])
        if not isinstance(bucket_items, list):
            continue
        for item in bucket_items:
            if isinstance(item, dict):
                issues.append(
                    {
                        "type": str(item.get("type", bucket)),
                        "severity": severity,
                        "detail": str(item.get("description", item.get("detail", ""))),
                        "fix": str(item.get("fix", "")),
                    }
                )
    return issues


def analyze_technical_audit_signals(
    *,
    url: str,
    issues_raw: list[dict[str, Any]],
    sitemap_url: str = "",
    crawl_depth: int = 3,
    check_mobile_friendly: bool = True,
    check_core_web_vitals: bool = True,
) -> dict[str, Any]:
    page = url.strip()
    sitemap = sitemap_url.strip()
    depth = max(1, min(10, int(crawl_depth)))
    https_ok = page.startswith("https")
    known = [i for i in issues_raw if isinstance(i, dict)]
    critical_count = sum(1 for i in known if str(i.get("severity", "")).lower() in {"critical", "high"})

    overall_score = 48
    overall_score += 10 if https_ok else 0
    overall_score += 4 if sitemap else 0
    overall_score += min(4, depth)
    overall_score -= min(18, critical_count * 4)
    overall_score -= min(10, max(0, len(known) - 2) * 2)
    overall_score = _clamp(overall_score)

    crawlability = _clamp(overall_score + (6 if https_ok else -4))
    indexability = _clamp(overall_score + 2)
    performance = _clamp(overall_score - 4)

    issues = [
        {
            "type": "HTTPS enforcement",
            "severity": "critical" if not https_ok else "info",
            "detail": "Site should be served over HTTPS with valid certificates",
            "fix": "Enable HTTPS redirects and HSTS",
        },
        {
            "type": "Canonical coverage",
            "severity": "warning",
            "detail": "Validate canonical tags on paginated and parameterized URLs",
            "fix": "Add self-referencing canonical tags to indexable templates",
        },
    ]
    for raw_issue in known[:5]:
        sev = str(raw_issue.get("severity", "warning")).lower()
        if sev == "high":
            sev = "warning"
        if sev not in {"critical", "warning", "info"}:
            sev = "warning"
        issues.append(
            {
                "type": str(raw_issue.get("type", "known_issue")),
                "severity": sev,
                "detail": str(raw_issue.get("detail", raw_issue.get("description", "Reported crawl issue"))),
                "fix": str(raw_issue.get("fix", "Review in Search Console and patch template")),
            }
        )

    return {
        "technical_score": overall_score,
        "overall_score": overall_score,
        "crawlability_score": crawlability,
        "indexability_score": indexability,
        "performance_score": performance,
        "core_web_vitals_score": performance,
        "structured_data_score": _clamp(overall_score - 6),
        "issues": issues,
        "core_web_vitals": (
            {
                "lcp": max(1.8, 4.2 - overall_score / 35),
                "cls": round(max(0.05, 0.18 - overall_score / 800), 2),
                "inp": max(120, 280 - overall_score * 2),
                "ttfb": max(280, 720 - overall_score * 4),
                "lcp_rating": "good" if overall_score >= 70 else "needs-improvement",
                "cls_rating": "good" if overall_score >= 65 else "needs-improvement",
            }
            if check_core_web_vitals
            else {}
        ),
        "mobile_friendly": (overall_score >= 55) if check_mobile_friendly else True,
        "https_secure": https_ok,
        "sitemap_found": bool(sitemap) or overall_score >= 50,
        "robots_txt_found": True,
        "structured_data_types": ["WebPage"],
        "page_speed_ms": max(900, 3200 - overall_score * 22),
        "recommendations": [
            "Fix critical crawl/index signals before content expansion",
            "Improve CWV on templates with highest organic traffic",
        ],
        "quick_wins": ["Enable HSTS", "Compress images to WebP", "Add canonical tags to paginated URLs"],
        "recommended_tools": ["search_console", "lighthouse", "screaming_frog"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_technical_audit_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    score = out.get("overall_score", out.get("technical_score", 50))
    try:
        overall = _clamp(int(float(score)))
    except (TypeError, ValueError):
        overall = 50
    out["overall_score"] = overall
    out["technical_score"] = overall
    cats = out.get("categories", {}) if isinstance(out.get("categories"), dict) else {}
    for key, cat_key, default in (
        ("crawlability_score", "crawlability", overall),
        ("indexability_score", "indexability", overall),
        ("performance_score", "core_web_vitals", overall - 4),
        ("core_web_vitals_score", "core_web_vitals", overall - 4),
        ("structured_data_score", "structured_data", overall - 6),
    ):
        if out.get(key) is None:
            cat = cats.get(cat_key, {})
            if isinstance(cat, dict) and cat.get("score") is not None:
                try:
                    out[key] = _clamp(int(float(cat["score"])))
                except (TypeError, ValueError):
                    out[key] = _clamp(int(default))
            else:
                out[key] = _clamp(int(default))
    flat = _flatten_issues(out)
    if flat:
        out["issues"] = flat
    elif not isinstance(out.get("issues"), list):
        out["issues"] = []
    if not isinstance(out.get("recommendations"), list):
        recs = out.get("recommendations")
        out["recommendations"] = recs if isinstance(recs, list) else []
    if not isinstance(out.get("quick_wins"), list):
        out["quick_wins"] = []
    cwv = out.get("core_web_vitals")
    if isinstance(cwv, dict) and "lcp_ms" in cwv and "lcp" not in cwv:
        try:
            out["core_web_vitals"] = {
                **cwv,
                "lcp": round(float(cwv.get("lcp_ms", 2500)) / 1000, 2),
                "inp": float(cwv.get("inp_ms", 200)),
                "cls": float(cwv.get("cls", 0.1)),
            }
        except (TypeError, ValueError):
            pass
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_technical_audit(
    *,
    url: str,
    issues_raw: list[dict[str, Any]],
    sitemap_url: str = "",
    crawl_depth: int = 3,
    check_mobile_friendly: bool = True,
    check_core_web_vitals: bool = True,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Perform a full technical SEO audit for: {clean_text_fn(url, 500)}. "
        f"Sitemap: {clean_text_fn(sitemap_url, 500) or 'not provided'}. "
        f"Crawl depth: {crawl_depth}. "
        f"Check mobile friendly: {check_mobile_friendly}. "
        f"Check core web vitals: {check_core_web_vitals}. "
        f"Known issues: {issues_raw[:10]}. "
        "Categorize all issues by severity. Score each category 0-100. List quick wins."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("overall_score") is not None or llm.get("categories") or llm.get("critical"):
            if llm.get("overall_score") is None and llm.get("technical_score") is not None:
                llm["overall_score"] = llm["technical_score"]
            return normalize_technical_audit_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_technical_audit_signals(
        url=url,
        issues_raw=issues_raw,
        sitemap_url=sitemap_url,
        crawl_depth=crawl_depth,
        check_mobile_friendly=check_mobile_friendly,
        check_core_web_vitals=check_core_web_vitals,
    )
    return normalize_technical_audit_result(heur, analysis_mode="heuristic", ai_available=False)
