"""AI Article Writer — phase-j module 4."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_content_writer_signals(
    *,
    topic: str,
    keywords: list[str],
    word_count: int,
    tone: str,
    brief: str,
) -> dict[str, Any]:
    subject = topic.strip()
    kws = [k.strip() for k in keywords if k.strip()] or [subject]
    target_words = max(300, min(5000, word_count))
    voice = tone.strip() or "professional"
    guidance = brief.strip()

    seo_score = 42
    seo_score += min(14, len(kws) * 3)
    seo_score += min(10, len(subject) // 5)
    seo_score += min(8, target_words // 200)
    seo_score += min(8, len(guidance) // 40)
    seo_score = _clamp(seo_score)
    readability_score = _clamp(seo_score - 4)

    primary = kws[0]
    article = (
        f"# The Definitive Guide to {subject}\n\n"
        f"This {voice} overview explains {primary} with practical steps and examples.\n\n"
        f"## Why {subject} Matters\n\n"
        f"Teams adopting {primary} can improve organic visibility when content aligns with search intent.\n\n"
        f"## Next Steps\n\n"
        f"Expand this draft toward {target_words} words using your brief and internal linking plan.\n"
    )

    return {
        "seo_score": seo_score,
        "readability_score": readability_score,
        "title": f"The Definitive Guide to {subject}",
        "article": article,
        "word_count": target_words,
        "primary_keyword": primary,
        "meta_description": f"The ultimate guide to {subject}. Learn everything you need with expert tips.",
        "suggested_tags": kws[:5],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_content_writer_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for score_key in ("seo_score", "readability_score"):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50
    if not isinstance(out.get("article"), str):
        out["article"] = ""
    if not isinstance(out.get("suggested_tags"), list):
        out["suggested_tags"] = []
    try:
        out["word_count"] = int(out.get("word_count", 1200))
    except (TypeError, ValueError):
        out["word_count"] = 1200
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def write_seo_article(
    *,
    topic: str,
    keywords: list[str],
    word_count: int,
    tone: str,
    brief: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Write a {word_count}-word, {clean_text_fn(tone, 100)} SEO article about: '{clean_text_fn(topic, 300)}'. "
        f"Primary keywords: {', '.join(keywords[:10])}. Brief guidance: {clean_text_fn(brief, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("article") or llm.get("seo_score") is not None:
            return normalize_content_writer_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_content_writer_signals(
        topic=topic, keywords=keywords, word_count=word_count, tone=tone, brief=brief
    )
    return normalize_content_writer_result(heur, analysis_mode="heuristic", ai_available=False)
