"""Image & Media SEO Engine — phase-g module 1."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_media_seo_signals(*, url: str, check_compression: bool, notes: str) -> dict[str, Any]:
    page = url.strip()
    notes_text = notes.strip()
    https_ok = page.startswith("https")

    media_seo_score = 40
    media_seo_score += 10 if https_ok else 0
    media_seo_score += 6 if check_compression else 0
    media_seo_score += min(10, len(notes_text) // 20)
    media_seo_score = _clamp(media_seo_score)

    issues = [
        {
            "type": "missing_alt",
            "element": "img.hero",
            "description": "Hero image may be missing descriptive alt text",
            "fix": "Add keyword-aware alt text",
            "impact": "high",
        }
    ]
    if check_compression:
        issues.append(
            {
                "type": "oversized",
                "element": "img.content",
                "description": "Some images may exceed recommended size budgets",
                "fix": "Compress to WebP/AVIF under 200 KB where possible",
                "impact": "medium",
            }
        )

    return {
        "media_seo_score": media_seo_score,
        "total_images_estimated": 12 + len(re.findall(r"\bimg\b", notes_text.lower())),
        "issues": issues,
        "compression": {"average_size_kb": 280, "optimizable_pct": 38 if check_compression else 22, "recommended_format": "webp"},
        "schema_coverage": {"image_objects_with_schema_pct": _clamp(media_seo_score - 15)},
        "video_seo": {"has_video_sitemap": False, "transcript_coverage_pct": 0},
        "quick_wins": ["Add alt text to hero and gallery images", "Enable lazy loading below the fold"],
        "recommended_tools": ["sharp", "squoosh", "cloudinary"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_media_seo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["media_seo_score"] = _clamp(int(float(out.get("media_seo_score", 50))))
    except (TypeError, ValueError):
        out["media_seo_score"] = 50
    for list_key in ("issues", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("compression"), dict):
        out["compression"] = {"average_size_kb": 250, "optimizable_pct": 30, "recommended_format": "webp"}
    if not isinstance(out.get("schema_coverage"), dict):
        out["schema_coverage"] = {"image_objects_with_schema_pct": 40}
    if not isinstance(out.get("video_seo"), dict):
        out["video_seo"] = {"has_video_sitemap": False, "transcript_coverage_pct": 0}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def audit_media_seo(
    *,
    url: str,
    check_compression: bool,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Audit URL: {clean_text_fn(url, 500)}. Check compression: {check_compression}. "
        f"Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("media_seo_score") is not None or llm.get("issues"):
            return normalize_media_seo_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_media_seo_signals(url=url, check_compression=check_compression, notes=notes)
    return normalize_media_seo_result(heur, analysis_mode="heuristic", ai_available=False)
