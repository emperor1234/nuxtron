"""Landing Page Builder — phase-g module 3."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "landing"


def analyze_landing_page_signals(
    *,
    product_name: str,
    target_keyword: str,
    audience: str,
    schema_types: list[str],
    notes: str,
) -> dict[str, Any]:
    product = product_name.strip()
    keyword = target_keyword.strip()
    aud = audience.strip() or "general"
    schemas = [s.strip() for s in schema_types if s.strip()] or ["Product", "FAQPage"]
    notes_text = notes.strip()

    landing_page_score = 38
    landing_page_score += min(16, len(keyword.split()) * 4)
    landing_page_score += min(12, len(product) // 4)
    landing_page_score += min(8, len(schemas) * 3)
    landing_page_score += 4 if notes_text else 0
    landing_page_score = _clamp(landing_page_score)

    slug = _slug(keyword)
    return {
        "landing_page_score": landing_page_score,
        "hero": {
            "headline": f"{product}: {keyword.title()} for {aud.replace('_', ' ')}",
            "subheadline": f"Launch-ready landing structure focused on {keyword}.",
            "cta": "Start Free Trial",
        },
        "schema_markup": [
            {"type": schemas[0], "json_ld": {"@context": "https://schema.org", "@type": schemas[0], "name": product}},
            {"type": "FAQPage", "json_ld": {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}},
        ],
        "sections": ["hero", "features", "social_proof", "faq", "cta_footer"],
        "faq_pairs": [
            {"question": f"What is {product}?", "answer": f"{product} helps teams with {keyword}."},
            {"question": f"Who is {product} for?", "answer": f"Built for {aud} teams pursuing {keyword} outcomes."},
        ],
        "ab_test_variants": [
            f"Headline A: {keyword.title()} made simple with {product}",
            f"Headline B: Stop guessing on {keyword} — use {product}",
        ],
        "seo_meta": {
            "title": f"{product} | {keyword.title()}",
            "description": f"Discover how {product} supports {aud} with {keyword}.",
            "canonical": f"/{slug}",
        },
        "conversion_signals": ["trust_badge", "testimonials", "guarantee"],
        "recommended_tools": ["next.js", "schema.org", "optimizely"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_landing_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["landing_page_score"] = _clamp(int(float(out.get("landing_page_score", 50))))
    except (TypeError, ValueError):
        out["landing_page_score"] = 50
    for list_key in ("schema_markup", "sections", "faq_pairs", "ab_test_variants", "conversion_signals", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("hero"), dict):
        out["hero"] = {"headline": "", "subheadline": "", "cta": "Get Started"}
    if not isinstance(out.get("seo_meta"), dict):
        out["seo_meta"] = {"title": "", "description": "", "canonical": "/"}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def generate_landing_page(
    *,
    product_name: str,
    target_keyword: str,
    audience: str,
    schema_types: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Product: {clean_text_fn(product_name, 200)}. Keyword: {clean_text_fn(target_keyword, 200)}. "
        f"Audience: {clean_text_fn(audience, 200)}. Schema types: {schema_types[:6]}. "
        f"Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("landing_page_score") is not None or llm.get("hero"):
            return normalize_landing_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_landing_page_signals(
        product_name=product_name,
        target_keyword=target_keyword,
        audience=audience,
        schema_types=schema_types,
        notes=notes,
    )
    return normalize_landing_result(heur, analysis_mode="heuristic", ai_available=False)
