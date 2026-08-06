"""News SEO & Google Discover — phase-h module 4."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_news_discover_signals(
    *,
    domain: str,
    recent_headlines: list[str],
    focus_topics: list[str],
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    headlines = [h.strip() for h in recent_headlines if h.strip()]
    topics = [t.strip() for t in focus_topics if t.strip()]
    notes_text = notes.strip()

    discover_readiness_score = 40
    discover_readiness_score += min(18, len(headlines) * 3)
    discover_readiness_score += min(14, len(topics) * 3)
    discover_readiness_score += 6 if site else 0
    discover_readiness_score += min(8, len(notes_text) // 25)
    discover_readiness_score = _clamp(discover_readiness_score)

    freshness_score = _clamp(discover_readiness_score - 6 + min(8, len(headlines)))
    eligibility = "high" if discover_readiness_score >= 70 else "medium" if discover_readiness_score >= 52 else "low"

    hl = headlines or ["AI Search Trends", "Discover Optimization Guide"]
    headline_improvements = [
        {
            "original": hl[0],
            "improved": f"{hl[0]}: What Publishers Should Do This Week",
            "reason": "Adds urgency and reader payoff",
        }
    ]
    if len(hl) > 1:
        headline_improvements.append(
            {
                "original": hl[1],
                "improved": f"Google Discover Playbook for {site or 'your site'}",
                "reason": "Improves clarity and CTR potential",
            }
        )

    topic_list = topics or ["news freshness", "discover optimization"]
    return {
        "discover_readiness_score": discover_readiness_score,
        "freshness_score": freshness_score,
        "top_stories_eligibility": eligibility,
        "headline_improvements": headline_improvements,
        "content_velocity": {"past_7d": max(1, len(headlines)), "recommended_per_week": max(5, len(headlines) + 2)},
        "discover_signals": {
            "image_quality": _clamp(discover_readiness_score - 8),
            "author_trust": _clamp(discover_readiness_score - 12),
            "topic_authority": _clamp(discover_readiness_score - 10),
        },
        "priority_topics": topic_list[:5],
        "quick_wins": ["Use 1200px+ lead images on news posts", "Add bylines and visible update timestamps"],
        "recommended_tools": ["google_search_console", "news_sitemap_validator", "discover_monitor"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_news_discover_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for score_key in ("discover_readiness_score", "freshness_score"):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50
    if out.get("top_stories_eligibility") not in ("low", "medium", "high"):
        out["top_stories_eligibility"] = "medium"
    for list_key in ("headline_improvements", "priority_topics", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("content_velocity"), dict):
        out["content_velocity"] = {"past_7d": 0, "recommended_per_week": 5}
    if not isinstance(out.get("discover_signals"), dict):
        out["discover_signals"] = {"image_quality": 50, "author_trust": 50, "topic_authority": 50}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_news_discover(
    *,
    domain: str,
    recent_headlines: list[str],
    focus_topics: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
    llm_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    headlines = recent_headlines[:12] if recent_headlines else ["AI Search Trends 2026"]
    topics = focus_topics[:10] if focus_topics else ["discover", "news freshness"]
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Headlines: {json.dumps(headlines)}. "
        f"Focus topics: {json.dumps(topics)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm_kwargs: dict[str, Any] = {}
    if llm_timeout_seconds is not None:
        llm_kwargs["timeout_seconds"] = llm_timeout_seconds
    llm = await ollama_json_fn(system_prompt, prompt, **llm_kwargs)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("discover_readiness_score") is not None or llm.get("headline_improvements"):
            return normalize_news_discover_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_news_discover_signals(
        domain=domain,
        recent_headlines=recent_headlines,
        focus_topics=focus_topics,
        notes=notes,
    )
    return normalize_news_discover_result(heur, analysis_mode="heuristic", ai_available=False)
