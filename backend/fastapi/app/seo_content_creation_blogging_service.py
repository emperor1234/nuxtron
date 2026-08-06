"""Content Creation & Blogging Suite — phase-j module 5."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_content_creation_blogging_signals(
    *,
    topic: str,
    content_pillars: list[str],
    target_keywords: list[str],
    ai_model: str,
    word_count_target: int,
    include_multimedia_plan: bool,
    publication_frequency: str,
    seo_brief: str,
    notes: str,
) -> dict[str, Any]:
    subject = topic.strip()
    pillars = [p.strip() for p in content_pillars if p.strip()] or [f"{subject} fundamentals"]
    keywords = [k.strip() for k in target_keywords if k.strip()]
    model = ai_model.strip() or "llama3.2"
    words = max(500, min(8000, word_count_target))
    freq = publication_frequency.strip() or "weekly"
    brief_text = seo_brief.strip()
    notes_text = notes.strip()

    content_strategy_score = 40
    content_strategy_score += min(14, len(pillars) * 3)
    content_strategy_score += min(14, len(keywords) * 3)
    content_strategy_score += 6 if include_multimedia_plan else 0
    content_strategy_score += min(8, len(brief_text) // 50)
    content_strategy_score += 4 if notes_text else 0
    content_strategy_score = _clamp(content_strategy_score)

    slug = subject.lower().replace(" ", "-")
    return {
        "content_strategy_score": content_strategy_score,
        "pillar_topics": [
            {
                "pillar": f"Ultimate Guide to {subject}",
                "content_angle": "Comprehensive how-to with expert interviews",
                "internal_link_hub": f"/{slug}",
            },
            {
                "pillar": f"{subject} Best Practices",
                "content_angle": "Data-backed checklist with examples",
                "internal_link_hub": f"/{slug}-best-practices",
            },
        ],
        "content_calendar": [
            {
                "week": w + 1,
                "topics": [f"{subject} topic {w + 1}"],
                "publishing_dates": [f"2026-06-{str(2 + w * 7).zfill(2)}"],
                "content_types": ["long_form"],
            }
            for w in range(min(4, 2 + len(keywords)))
        ],
        "seo_brief": [
            {
                "title": f"The Complete Guide to {subject}",
                "meta_description": f"Everything about {subject} — expert guide with actionable steps.",
                "target_keywords": keywords[:5] or [subject],
                "outline": [f"H2: What Is {subject}?", "H2: Best Practices", "H2: FAQ"],
            }
        ],
        "multimedia_plan": {
            "hero_image_brief": f"High-impact visual showing {subject} in action",
            "video_outline": [f"Introduction to {subject}", "Step-by-step walkthrough"],
            "interactive_elements": ["quiz"] if include_multimedia_plan else [],
            "infographic_topics": [f"{subject} process flow"] if include_multimedia_plan else [],
        },
        "promotion_strategy": ["organic_search", "social", "email"],
        "measurement_framework": {
            "kpis": ["organic_sessions", "avg_time_on_page", "conversions"],
            "tracking_plan": f"Weekly GSC report + {freq} content performance review using {model}",
        },
        "next_actions": ["Publish pillar content first", "Build editorial calendar", "Launch multimedia pipeline"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_content_creation_blogging_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["content_strategy_score"] = _clamp(int(float(out.get("content_strategy_score", 50))))
    except (TypeError, ValueError):
        out["content_strategy_score"] = 50
    for list_key in ("pillar_topics", "content_calendar", "seo_brief", "promotion_strategy", "next_actions"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("multimedia_plan"), dict):
        out["multimedia_plan"] = {}
    if not isinstance(out.get("measurement_framework"), dict):
        out["measurement_framework"] = {"kpis": [], "tracking_plan": ""}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def plan_content_creation_blogging(
    *,
    topic: str,
    content_pillars: list[str],
    target_keywords: list[str],
    ai_model: str,
    word_count_target: int,
    include_multimedia_plan: bool,
    publication_frequency: str,
    seo_brief: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
    llm_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    prompt = (
        f"Topic: '{clean_text_fn(topic, 300)}'. Pillars: {', '.join(content_pillars[:10])}. "
        f"Keywords: {', '.join(target_keywords[:15])}. Model: {ai_model}. "
        f"Word count target: {word_count_target}. Multimedia: {include_multimedia_plan}. "
        f"Frequency: {publication_frequency}. SEO brief: {clean_text_fn(seo_brief, 2000)}. "
        f"Notes: {clean_text_fn(notes, 500)}."
    )
    llm_kwargs: dict[str, Any] = {}
    if llm_timeout_seconds is not None:
        llm_kwargs["timeout_seconds"] = llm_timeout_seconds
    llm = await ollama_json_fn(system_prompt, prompt, **llm_kwargs)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("content_strategy_score") is not None or llm.get("pillar_topics"):
            return normalize_content_creation_blogging_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_content_creation_blogging_signals(
        topic=topic,
        content_pillars=content_pillars,
        target_keywords=target_keywords,
        ai_model=ai_model,
        word_count_target=word_count_target,
        include_multimedia_plan=include_multimedia_plan,
        publication_frequency=publication_frequency,
        seo_brief=seo_brief,
        notes=notes,
    )
    return normalize_content_creation_blogging_result(heur, analysis_mode="heuristic", ai_available=False)
