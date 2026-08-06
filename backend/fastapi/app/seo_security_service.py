"""Security & SEO Health Monitor — phase-g module 4."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_security_seo_signals(*, url: str, check_cloaking: bool, notes: str) -> dict[str, Any]:
    page = url.strip()
    notes_text = notes.strip()
    https_ok = page.startswith("https")

    security_seo_score = 42
    security_seo_score += 12 if https_ok else 0
    security_seo_score += 4 if check_cloaking else 0
    security_seo_score += min(8, len(notes_text) // 25)
    security_seo_score = _clamp(security_seo_score)

    issues = []
    if not https_ok:
        issues.append(
            {
                "severity": "high",
                "category": "security",
                "description": "Site URL is not HTTPS",
                "fix": "Enforce HTTPS redirects and HSTS",
            }
        )
    issues.append(
        {
            "severity": "medium",
            "category": "security",
            "description": "Content-Security-Policy header should be validated",
            "fix": "Define CSP to reduce XSS risk",
        }
    )

    return {
        "security_seo_score": security_seo_score,
        "https": {"enabled": https_ok, "hsts": https_ok, "mixed_content_issues": 0 if https_ok else 2},
        "security_headers": {
            "csp_present": False,
            "x_frame_options": "Missing" if security_seo_score < 60 else "SAMEORIGIN",
            "x_content_type": "nosniff",
        },
        "cloaking_signals": {"user_agent_cloaking": False, "ip_cloaking": False, "js_cloaking": False},
        "spam_signals": {"hidden_text": False, "keyword_stuffing": False, "doorway_pages": False},
        "redirect_health": {"chains_detected": 0 if https_ok else 1, "chain_details": [] if https_ok else ["http → https redirect chain"]},
        "issues": issues,
        "quick_wins": ["Enable HSTS", "Add CSP header", "Audit mixed-content assets"],
        "recommended_tools": ["securityheaders.com", "sucuri", "semrush_site_audit"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_security_seo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["security_seo_score"] = _clamp(int(float(out.get("security_seo_score", 50))))
    except (TypeError, ValueError):
        out["security_seo_score"] = 50
    for list_key in ("issues", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    for key in ("https", "security_headers", "cloaking_signals", "spam_signals", "redirect_health"):
        if not isinstance(out.get(key), dict):
            out[key] = {}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def audit_security_seo(
    *,
    url: str,
    check_cloaking: bool,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Audit URL: {clean_text_fn(url, 500)}. Check cloaking: {check_cloaking}. "
        f"Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("security_seo_score") is not None or llm.get("issues"):
            return normalize_security_seo_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_security_seo_signals(url=url, check_cloaking=check_cloaking, notes=notes)
    return normalize_security_seo_result(heur, analysis_mode="heuristic", ai_available=False)
