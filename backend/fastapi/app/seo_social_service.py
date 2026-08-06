"""Social SEO & Distribution — phase-g module 2."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_social_seo_signals(*, url: str, platforms: list[str], notes: str) -> dict[str, Any]:
    page = url.strip()
    plats = [p.strip().lower() for p in platforms if p.strip()] or ["twitter", "facebook", "linkedin"]
    notes_text = notes.strip()

    social_seo_score = 38
    social_seo_score += min(16, len(plats) * 4)
    social_seo_score += 6 if page.startswith("https") else 0
    social_seo_score += 4 if notes_text else 0
    social_seo_score = _clamp(social_seo_score)

    og_issues = ["og:title may be missing or generic"]
    if "twitter" in plats:
        og_issues.append("twitter:card meta tag should be validated")

    return {
        "social_seo_score": social_seo_score,
        "open_graph": {
            "title": "Needs review",
            "description": "Needs review",
            "image": "Missing",
            "type": "website",
            "issues": og_issues,
        },
        "twitter_card": {
            "card_type": "summary_large_image" if social_seo_score >= 55 else "missing",
            "title": "Needs review",
            "description": "Needs review",
            "image": "Missing",
            "issues": ["Validate twitter:card and image dimensions"],
        },
        "linkedin": {"article_snippet": "Snippet depends on og:description quality", "issues": ["Ensure og:description is concise"]},
        "canonical_alignment": {"canonical_url": page, "matches_og_url": page.startswith("https")},
        "distribution_opportunities": [f"Optimize share previews for {p}" for p in plats[:3]],
        "quick_wins": ["Add og:title and og:image (1200×630)", "Add twitter:card meta tag"],
        "recommended_tools": ["buffer", "hootsuite", "og-image-generator"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_social_seo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["social_seo_score"] = _clamp(int(float(out.get("social_seo_score", 50))))
    except (TypeError, ValueError):
        out["social_seo_score"] = 50
    for list_key in ("distribution_opportunities", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    for key in ("open_graph", "twitter_card", "linkedin", "canonical_alignment"):
        if not isinstance(out.get(key), dict):
            out[key] = {}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def audit_social_seo(
    *,
    url: str,
    platforms: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Audit URL: {clean_text_fn(url, 500)}. Platforms: {platforms[:6]}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("social_seo_score") is not None or llm.get("open_graph"):
            return normalize_social_seo_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_social_seo_signals(url=url, platforms=platforms, notes=notes)
    return normalize_social_seo_result(heur, analysis_mode="heuristic", ai_available=False)
