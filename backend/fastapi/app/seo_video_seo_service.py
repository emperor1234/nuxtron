"""Video SEO Module — phase-d module 3."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_video_seo_signals(
    *,
    title: str,
    description: str,
    transcript: str,
    platform: str,
    keywords: list[str],
) -> dict[str, Any]:
    vid_title = title.strip()
    desc = description.strip()
    trans = transcript.strip()
    plat = platform.strip() or "youtube"
    kw = [k.strip() for k in keywords if k.strip()]
    title_words = len(re.findall(r"\b\w+\b", vid_title))
    trans_words = len(re.findall(r"\b\w+\b", trans))

    seo_score = 38
    seo_score += min(18, title_words * 2)
    seo_score += min(14, trans_words // 20)
    seo_score += min(12, len(kw) * 3)
    seo_score += 6 if desc else 0
    seo_score = _clamp(seo_score)

    optimized_title = vid_title[:60] if len(vid_title) <= 60 else vid_title[:57] + "..."
    if kw and kw[0].lower() not in optimized_title.lower():
        optimized_title = f"{optimized_title} | {kw[0].title()}"[:60]

    return {
        "seo_score": seo_score,
        "video_seo_score": seo_score,
        "optimized_title": optimized_title,
        "optimized_description": desc or f"In this {plat} video we cover {vid_title}. Subscribe for more expert content.",
        "tags": kw[:15] if kw else [w for w in re.findall(r"\b\w{4,}\b", vid_title.lower())[:8]],
        "chapters": [
            {"time": "0:00", "title": "Introduction"},
            {"time": "1:30", "title": "Main topic"},
            {"time": "5:00", "title": "Key takeaways"},
        ],
        "thumbnail_tips": ["Use high contrast", "Include keyword text overlay", "Show faces for CTR"],
        "card_suggestions": ["Link related video at midpoint", "End screen subscribe CTA"],
        "schema": {"@type": "VideoObject", "name": vid_title, "description": desc[:240] or vid_title},
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_video_seo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    score_raw = out.get("seo_score", out.get("video_seo_score", 50))
    try:
        score = _clamp(int(float(score_raw)))
    except (TypeError, ValueError):
        score = 50
    out["seo_score"] = score
    out["video_seo_score"] = score
    for list_key in ("tags", "chapters", "thumbnail_tips", "card_suggestions"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def optimize_video_seo(
    *,
    title: str,
    description: str,
    transcript: str,
    platform: str,
    keywords: list[str],
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Optimize video SEO for {clean_text_fn(platform, 50)}. Title: {clean_text_fn(title, 200)}. "
        f"Keywords: {', '.join(keywords[:10])}. Transcript: {clean_text_fn(transcript, 2000)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("seo_score") is not None or llm.get("optimized_title"):
            return normalize_video_seo_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_video_seo_signals(title=title, description=description, transcript=transcript, platform=platform, keywords=keywords)
    return normalize_video_seo_result(heur, analysis_mode="heuristic", ai_available=False)
