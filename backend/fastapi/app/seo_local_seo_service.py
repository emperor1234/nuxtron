"""Local SEO Suite — phase-d module 2."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_local_seo_signals(
    *,
    business_name: str,
    category: str,
    location: str,
    website: str,
    description: str,
) -> dict[str, Any]:
    name = business_name.strip()
    cat = category.strip() or "local business"
    loc = location.strip() or "your city"
    site = website.strip()
    desc = description.strip()
    desc_words = len(re.findall(r"\b\w+\b", desc))

    local_seo_score = 36
    local_seo_score += min(16, desc_words // 8)
    local_seo_score += 10 if loc else 0
    local_seo_score += 8 if site.startswith("http") else 0
    local_seo_score += 8 if cat else 0
    local_seo_score = _clamp(local_seo_score)

    gmb_score = _clamp(local_seo_score - 4)
    missing = []
    if desc_words < 40:
        missing.append("business_description")
    if not site:
        missing.append("website_url")

    return {
        "local_seo_score": local_seo_score,
        "gmb_optimization": {
            "score": gmb_score,
            "missing_fields": missing,
            "recommendations": ["Add weekly photo updates", "Respond to reviews within 24 hours"],
        },
        "local_keywords": [
            {"keyword": f"{cat} {loc}", "monthly_searches": 900 + len(loc) * 10, "local_intent": True},
            {"keyword": f"best {cat} near me", "monthly_searches": 650, "local_intent": True},
        ],
        "citation_opportunities": ["Google Business Profile", "Yelp", "Bing Places", "Apple Maps"],
        "review_strategy": ["Send post-visit review requests", "Display review badges on site"],
        "local_schema": {
            "@type": "LocalBusiness",
            "name": name,
            "address": {"@type": "PostalAddress", "addressLocality": loc},
            "url": site or None,
        },
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_local_seo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["local_seo_score"] = _clamp(int(float(out.get("local_seo_score", 50))))
    except (TypeError, ValueError):
        out["local_seo_score"] = 50
    if not isinstance(out.get("gmb_optimization"), dict):
        out["gmb_optimization"] = {"score": out["local_seo_score"], "missing_fields": [], "recommendations": []}
    for list_key in ("local_keywords", "citation_opportunities", "review_strategy"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def optimize_local_seo(
    *,
    business_name: str,
    category: str,
    location: str,
    website: str,
    description: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Optimize local SEO for: {clean_text_fn(business_name, 200)}. "
        f"Category: {clean_text_fn(category, 120)}. Location: {clean_text_fn(location, 120)}. "
        f"Website: {clean_text_fn(website, 300)}. Description: {clean_text_fn(description, 1000)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("local_seo_score") is not None or llm.get("local_keywords"):
            return normalize_local_seo_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_local_seo_signals(
        business_name=business_name, category=category, location=location, website=website, description=description,
    )
    return normalize_local_seo_result(heur, analysis_mode="heuristic", ai_available=False)
