"""
SXO (Search Experience Optimization) — module 7.

Scores dwell time, CTR, and UX quality from URL, content, and keyword signals.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r"^#{1,3}\s+|\n#{1,3}\s+|<h[1-3]\b", re.IGNORECASE | re.MULTILINE)
_LIST_RE = re.compile(r"^\s*[-*•]\s+|\n\s*[-*•]\s+|\n\s*\d+\.\s+", re.MULTILINE)
_CTA_RE = re.compile(r"\b(get started|sign up|learn more|buy now|contact us|try free|download)\b", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_LINK_RE = re.compile(r"https?://[^\s]+|\[[^\]]+\]\([^)]+\)", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _clamp_prob(value: float) -> float:
    return round(max(0.05, min(0.95, value)), 2)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _slug_keywords(url: str) -> list[str]:
    try:
        path = urlparse(url.strip()).path.strip("/")
    except Exception:
        return []
    if not path:
        return []
    parts = re.split(r"[/\-_]+", path)
    return [p for p in parts if len(p) >= 3 and p.lower() not in {"www", "html", "php", "asp"}]


def _bounce_risk(score: int) -> str:
    if score >= 70:
        return "low"
    if score >= 45:
        return "medium"
    return "high"


def analyze_sxo_signals(*, url: str, content: str, keywords: list[str]) -> dict[str, Any]:
    """Deterministic SXO scoring from page URL, content, and keyword alignment."""
    page_url = url.strip()
    body = content.strip()
    keyword_list = [k.strip() for k in keywords if k.strip()]
    if not body and page_url:
        body = " ".join(_slug_keywords(page_url))

    words = re.findall(r"\b\w+\b", body)
    word_count = len(words)
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    longest_para = max((_word_count(p) for p in paragraphs), default=word_count)
    heading_count = len(_HEADING_RE.findall(body))
    list_count = len(_LIST_RE.findall(body))
    cta_count = len(_CTA_RE.findall(body))
    link_count = len(_LINK_RE.findall(body))
    bracket_count = len(_BRACKET_RE.findall(body))

    parsed = urlparse(page_url) if page_url else None
    https_ok = bool(parsed and parsed.scheme == "https")
    path_depth = len([p for p in (parsed.path.split("/") if parsed else []) if p]) if parsed else 0

    keyword_hits = 0
    body_lower = body.lower()
    for kw in keyword_list:
        if kw.lower() in body_lower:
            keyword_hits += 1
    if not keyword_list and page_url:
        keyword_hits = sum(1 for slug in _slug_keywords(page_url) if slug.lower() in body_lower)

    dwell_time_score = 34
    if word_count >= 400:
        dwell_time_score += 22
    elif word_count >= 180:
        dwell_time_score += 14
    elif word_count >= 80:
        dwell_time_score += 6
    else:
        dwell_time_score -= 10
    if heading_count >= 2:
        dwell_time_score += 12
    if list_count >= 1:
        dwell_time_score += 8
    if link_count >= 2:
        dwell_time_score += 6
    dwell_time_score = _clamp(dwell_time_score)

    ctr_score = 36
    if keyword_hits >= 2:
        ctr_score += 18
    elif keyword_hits == 1:
        ctr_score += 10
    if https_ok:
        ctr_score += 8
    if parsed and len(parsed.path) <= 60:
        ctr_score += 6
    ctr_score -= min(12, bracket_count * 4)
    ctr_score = _clamp(ctr_score)

    ux_quality_score = 32
    if longest_para <= 120:
        ux_quality_score += 16
    elif longest_para <= 180:
        ux_quality_score += 8
    else:
        ux_quality_score -= 12
    if heading_count >= 1:
        ux_quality_score += 12
    if cta_count >= 1:
        ux_quality_score += 10
    if path_depth <= 4:
        ux_quality_score += 6
    ux_quality_score = _clamp(ux_quality_score)

    sxo_score = _clamp(int(round((dwell_time_score + ctr_score + ux_quality_score) / 3)))
    scroll_depth = _clamp_prob(0.25 + (word_count / 1200) + (heading_count * 0.05))
    bounce_risk = _bounce_risk(sxo_score)

    url_slug_keywords = _slug_keywords(page_url) if page_url else []
    primary_keyword = keyword_list[0] if keyword_list else (url_slug_keywords[0] if url_slug_keywords else "page topic")
    optimized_title = f"{primary_keyword.title()} — Guide, Tips, and Next Steps"[:70]

    improvements: list[dict[str, Any]] = []
    if word_count < 180:
        improvements.append(
            {
                "area": "dwell_time",
                "action": "Expand thin content with scannable sections and examples above 180 words.",
                "impact": "high",
                "effort": "medium",
                "expected_delta_pct": 14,
            }
        )
    if keyword_hits == 0 and keyword_list:
        improvements.append(
            {
                "area": "ctr",
                "action": f"Align title, H1, and intro copy with target keywords: {', '.join(keyword_list[:3])}.",
                "impact": "high",
                "effort": "low",
                "expected_delta_pct": 11,
            }
        )
    if longest_para > 150:
        improvements.append(
            {
                "area": "ux_quality",
                "action": "Break long paragraphs into shorter blocks with subheadings every 120 words.",
                "impact": "medium",
                "effort": "low",
                "expected_delta_pct": 9,
            }
        )
    if not https_ok and page_url:
        improvements.append(
            {
                "area": "ux_quality",
                "action": "Serve the page over HTTPS to improve trust and reduce early exits.",
                "impact": "high",
                "effort": "medium",
                "expected_delta_pct": 8,
            }
        )
    if cta_count == 0:
        improvements.append(
            {
                "area": "ctr",
                "action": "Add a clear above-the-fold CTA aligned to search intent.",
                "impact": "medium",
                "effort": "low",
                "expected_delta_pct": 7,
            }
        )

    return {
        "sxo_score": sxo_score,
        "dwell_time_score": dwell_time_score,
        "ctr_score": ctr_score,
        "ux_quality_score": ux_quality_score,
        "behavioral_signals": {
            "estimated_bounce_rate_pct": _clamp(100 - sxo_score + 8),
            "estimated_avg_dwell_seconds": int(35 + dwell_time_score * 0.9),
            "scroll_depth_pct": int(scroll_depth * 100),
            "rage_click_risk": round(max(0.05, 0.35 - ux_quality_score / 200), 2),
        },
        "ctr_optimization": {
            "current_title_ctr_estimate": round(0.012 + ctr_score / 5000, 3),
            "optimized_title": optimized_title,
            "power_words_added": ["guide", "proven", "fast"] if ctr_score < 70 else ["updated"],
            "meta_description_cta": f"Learn {primary_keyword} with actionable steps and clear next actions.",
            "rich_snippet_opportunities": ["faq", "breadcrumb"] if heading_count >= 2 else ["article"],
        },
        "engagement_signals": {
            "bounce_risk": bounce_risk,
            "scroll_depth_predicted": scroll_depth,
            "video_engagement_boost": word_count >= 300 and heading_count >= 2,
        },
        "above_fold_audit": {
            "cta_visible": cta_count >= 1,
            "value_prop_clear": keyword_hits >= 1 or word_count >= 80,
            "load_time_estimate_ms": 2800 if word_count > 800 else 2100,
            "hero_clarity_score": _clamp(ux_quality_score),
        },
        "improvements": improvements,
        "quick_wins": [
            "Add a keyword-aligned H1 and 160-character meta description.",
            "Insert one FAQ block for the primary query intent.",
            "Place a single primary CTA above the first scroll depth.",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "word_count": word_count,
            "keyword_hits": keyword_hits,
            "heading_count": heading_count,
            "https": https_ok,
            "path_depth": path_depth,
        },
    }


def normalize_sxo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for score_key in ("sxo_score", "dwell_time_score", "ctr_score", "ux_quality_score"):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50

    for dict_key in ("behavioral_signals", "ctr_optimization", "engagement_signals", "above_fold_audit"):
        if not isinstance(out.get(dict_key), dict):
            out[dict_key] = {}

    engagement = out.get("engagement_signals") or {}
    if "bounce_risk" not in engagement:
        engagement["bounce_risk"] = _bounce_risk(out["sxo_score"])
    if "scroll_depth_predicted" not in engagement:
        engagement["scroll_depth_predicted"] = _clamp_prob(out["sxo_score"] / 120)
    out["engagement_signals"] = engagement

    if not isinstance(out.get("improvements"), list):
        out["improvements"] = []
    if not isinstance(out.get("quick_wins"), list):
        out["quick_wins"] = []

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_sxo_experience(
    *,
    url: str,
    content: str,
    keywords: list[str],
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run SXO analysis."""
    prompt = (
        f"Analyze SXO (Search Experience Optimization) for: {clean_text_fn(url, 300)}.\n"
        f"Target keywords: {', '.join(keywords[:10])}.\n"
        f"Content:\n{clean_text_fn(content, 2000)}\n\n"
        "Score dwell time, CTR, UX quality, and engagement signals. "
        "Provide specific improvements. Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("sxo_score") is not None or llm_result.get("improvements") is not None:
            return normalize_sxo_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_sxo_signals(url=url, content=content, keywords=keywords)
    return normalize_sxo_result(heuristic, analysis_mode="heuristic", ai_available=False)
