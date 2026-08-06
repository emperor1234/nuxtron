"""
eCommerce SEO Suite — phase-b module 5 (phase-b capstone).

Optimizes product titles, descriptions, bullets, and Product schema from catalog inputs.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_GENERIC_RE = re.compile(r"\b(best price|high quality|premium quality|trusted by)\b", re.IGNORECASE)
_FEATURE_RE = re.compile(r"\b(wireless|bluetooth|waterproof|organic|vegan|portable|rechargeable)\b", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def analyze_ecommerce_signals(
    *,
    product_name: str,
    category: str,
    description: str,
    keywords: list[str],
) -> dict[str, Any]:
    """Deterministic eCommerce SEO optimization from product catalog signals."""
    name = product_name.strip()
    cat = category.strip()
    desc = description.strip()
    kw_list = [k.strip() for k in keywords if k.strip()]
    primary_kw = kw_list[0] if kw_list else (cat.split("/")[-1].strip() if cat else "product")

    name_words = len(re.findall(r"\b\w+\b", name))
    desc_words = len(re.findall(r"\b\w+\b", desc))
    kw_in_name = sum(1 for k in kw_list if k.lower() in name.lower())
    feature_hits = len(_FEATURE_RE.findall(name + " " + desc))
    bracket_count = len(_BRACKET_RE.findall(name + desc))
    generic_hits = len(_GENERIC_RE.findall(desc))

    seo_score = 38
    seo_score += min(16, name_words * 2)
    seo_score += min(14, desc_words // 12)
    seo_score += min(12, len(kw_list) * 3)
    seo_score += min(8, kw_in_name * 4)
    seo_score += min(8, feature_hits * 2)
    seo_score += 6 if cat else 0
    seo_score -= min(12, bracket_count * 4)
    seo_score -= min(8, generic_hits * 3)
    seo_score = _clamp(seo_score)

    title_base = name
    if primary_kw.lower() not in name.lower():
        title_base = f"{name} — {primary_kw.title()}"
    optimized_title = _truncate(f"{title_base} | {cat or 'Shop Now'}", 60)

    desc_seed = desc or f"Shop {name} with fast shipping and reliable support."
    optimized_description = _truncate(
        f"{desc_seed} Ideal for shoppers searching for {primary_kw}. "
        f"Compare specs, read reviews, and buy with confidence.",
        160,
    )

    bullet_points = [
        f"{name} engineered for {primary_kw} use cases",
        f"Category: {cat}" if cat else "Clear product specifications and compatibility details",
        "Fast shipping with transparent return policy",
    ]
    if feature_hits:
        bullet_points.append("Highlights differentiated product features buyers compare first")
    if kw_list:
        bullet_points.append(f"Optimized for queries like: {', '.join(kw_list[:3])}")
    bullet_points = bullet_points[:5]

    category_keywords = kw_list[:8] if kw_list else ([cat] if cat else [primary_kw])
    review_schema_eligible = desc_words >= 40 and len(kw_list) >= 1 and bool(name)

    product_schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": _truncate(desc or optimized_description, 240),
        "category": cat or None,
    }
    if kw_list:
        product_schema["keywords"] = ", ".join(kw_list[:10])

    recommendations: list[str] = []
    if len(optimized_title) > 60:
        recommendations.append("Shorten title to under 60 characters for SERP display")
    if desc_words < 80:
        recommendations.append("Expand unique product description to at least 80 words for rich results")
    if not kw_list:
        recommendations.append("Add 3–5 buyer-intent keywords tied to category and variant attributes")
    if not review_schema_eligible:
        recommendations.append("Add verified review volume before enabling aggregateRating schema")
    recommendations.append("Include Offer schema with price, availability, and shipping details")
    if generic_hits:
        recommendations.append("Replace generic marketing phrases with spec-led, query-matching copy")

    return {
        "seo_score": seo_score,
        "ecommerce_score": seo_score,
        "optimized_title": optimized_title,
        "optimized_description": optimized_description,
        "bullet_points": bullet_points,
        "product_schema": product_schema,
        "category_keywords": category_keywords,
        "review_schema_eligible": review_schema_eligible,
        "recommendations": recommendations[:6],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "description_word_count": desc_words,
            "keyword_count": len(kw_list),
            "keywords_in_title": kw_in_name,
            "feature_signal_hits": feature_hits,
        },
    }


def normalize_ecommerce_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    score_raw = out.get("seo_score", out.get("ecommerce_score", 50))
    try:
        score = _clamp(int(float(score_raw)))
    except (TypeError, ValueError):
        score = 50
    out["seo_score"] = score
    out["ecommerce_score"] = score

    if not isinstance(out.get("bullet_points"), list):
        out["bullet_points"] = []
    if not isinstance(out.get("category_keywords"), list):
        out["category_keywords"] = []
    if not isinstance(out.get("recommendations"), list):
        out["recommendations"] = []
    if not isinstance(out.get("product_schema"), dict):
        out["product_schema"] = {"@type": "Product", "name": out.get("optimized_title", "Product")}

    if out.get("review_schema_eligible") is None:
        out["review_schema_eligible"] = False

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def optimize_ecommerce_seo(
    *,
    product_name: str,
    category: str,
    description: str,
    keywords: list[str],
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run eCommerce SEO optimization."""
    prompt = (
        f"Optimize eCommerce SEO for product: '{clean_text_fn(product_name, 300)}'.\n"
        f"Category: {clean_text_fn(category, 200)}.\n"
        f"Keywords: {', '.join(keywords[:10])}.\n"
        f"Description: {clean_text_fn(description, 1500)}.\n\n"
        "Create an SEO-optimized title, meta description, 5 bullet points, "
        "category-level keywords, Product schema, and review schema eligibility. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("seo_score") is not None or llm_result.get("optimized_title"):
            return normalize_ecommerce_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_ecommerce_signals(
        product_name=product_name,
        category=category,
        description=description,
        keywords=keywords,
    )
    return normalize_ecommerce_result(heuristic, analysis_mode="heuristic", ai_available=False)
