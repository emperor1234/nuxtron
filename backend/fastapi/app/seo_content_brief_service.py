"""Content Brief Generator — phase-j module 3."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_content_brief_signals(
    *,
    topic: str,
    keywords: list[str],
    word_count: int,
    audience: str,
) -> dict[str, Any]:
    subject = topic.strip()
    kws = [k.strip() for k in keywords if k.strip()] or [subject]
    target_words = max(300, min(10000, word_count))
    aud = audience.strip() or "general readers"

    brief_score = 40
    brief_score += min(16, len(kws) * 3)
    brief_score += min(10, len(subject) // 6)
    brief_score += min(8, target_words // 250)
    brief_score += 4 if aud else 0
    brief_score = _clamp(brief_score)

    return {
        "brief_score": brief_score,
        "title": f"The Complete Guide to {subject}",
        "meta_description": f"Everything you need to know about {subject} for {aud}.",
        "target_word_count": target_words,
        "primary_keyword": kws[0],
        "secondary_keywords": kws[1:6],
        "outline": [
            {
                "heading": f"H2: What Is {subject}?",
                "word_count": 300,
                "key_points": ["Definition", "Why it matters"],
                "keywords_to_include": kws[:2],
            },
            {
                "heading": f"H2: How to Get Started with {subject}",
                "word_count": 500,
                "key_points": ["Step-by-step process", "Tools needed"],
                "keywords_to_include": kws[2:4],
            },
            {
                "heading": "H2: Best Practices",
                "word_count": 400,
                "key_points": ["Do's and don'ts", "Expert tips"],
                "keywords_to_include": [],
            },
        ],
        "internal_links": ["/related-guide", "/tools"],
        "external_links": [],
        "tone": "authoritative yet accessible",
        "unique_angle": f"Actionable, data-backed guidance tailored for {aud}",
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_content_brief_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["brief_score"] = _clamp(int(float(out.get("brief_score", 50))))
    except (TypeError, ValueError):
        out["brief_score"] = 50
    for list_key in ("secondary_keywords", "outline", "internal_links", "external_links"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("target_word_count"), int):
        try:
            out["target_word_count"] = int(out.get("target_word_count", 1500))
        except (TypeError, ValueError):
            out["target_word_count"] = 1500
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def generate_content_brief(
    *,
    topic: str,
    keywords: list[str],
    word_count: int,
    audience: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Create a detailed SEO content brief for topic: '{clean_text_fn(topic, 300)}'. "
        f"Target keywords: {', '.join(keywords[:15])}. Target word count: {word_count}. "
        f"Target audience: {clean_text_fn(audience, 200)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("title") or llm.get("outline") or llm.get("brief_score") is not None:
            if llm.get("brief_score") is None:
                llm["brief_score"] = 65
            return normalize_content_brief_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_content_brief_signals(topic=topic, keywords=keywords, word_count=word_count, audience=audience)
    return normalize_content_brief_result(heur, analysis_mode="heuristic", ai_available=False)
