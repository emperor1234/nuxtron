"""Review & Reputation Engine — phase-h module 2."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

_POSITIVE = re.compile(r"\b(great|love|excellent|amazing|recommend|happy|best|fantastic)\b", re.IGNORECASE)
_NEGATIVE = re.compile(r"\b(bad|terrible|slow|late|broken|awful|disappointed|refund|poor)\b", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_review_reputation_signals(
    *,
    brand: str,
    reviews_text: str,
    platforms: list[str],
    notes: str,
) -> dict[str, Any]:
    name = brand.strip()
    text = reviews_text.strip()
    plats = [p.strip().lower() for p in platforms if p.strip()] or ["google", "trustpilot"]
    notes_text = notes.strip()

    positive_hits = len(_POSITIVE.findall(text))
    negative_hits = len(_NEGATIVE.findall(text))
    total_signals = max(1, positive_hits + negative_hits)
    positive_pct = _clamp(int(round(positive_hits / total_signals * 100)))
    negative_pct = _clamp(int(round(negative_hits / total_signals * 100)))
    neutral_pct = _clamp(100 - positive_pct - negative_pct)

    reputation_score = 44
    reputation_score += min(16, positive_hits * 3)
    reputation_score += min(10, len(plats) * 3)
    reputation_score += min(8, len(text) // 120)
    reputation_score -= min(18, negative_hits * 4)
    reputation_score = _clamp(reputation_score)

    overall = "positive" if positive_pct >= negative_pct else "negative" if negative_pct > positive_pct else "mixed"
    review_count = max(3, len(re.findall(r"[.!?]", text)) or len(text.split("\n")))

    themes = []
    if negative_hits:
        themes.append(
            {
                "theme": "Service Issues",
                "sentiment": "negative",
                "frequency": negative_hits,
                "example_quote": "Support response time needs improvement",
            }
        )
    if positive_hits:
        themes.append(
            {
                "theme": "Product Quality",
                "sentiment": "positive",
                "frequency": positive_hits,
                "example_quote": f"Customers mention strong value from {name or 'the brand'}",
            }
        )
    if not themes:
        themes.append(
            {
                "theme": "General Sentiment",
                "sentiment": "neutral",
                "frequency": 1,
                "example_quote": "Add review text for deeper theme extraction",
            }
        )

    return {
        "reputation_score": reputation_score,
        "sentiment": {
            "overall": overall,
            "positive_pct": positive_pct,
            "neutral_pct": neutral_pct,
            "negative_pct": negative_pct,
        },
        "themes": themes,
        "review_summary": {
            "total_reviews": review_count,
            "avg_rating": round(min(4.8, 3.2 + reputation_score / 40), 1),
            "platform_breakdown": {p: max(1, review_count // len(plats)) for p in plats},
        },
        "response_templates": [
            {
                "scenario": "negative_service",
                "template": f"Hi, we're sorry {name or 'we'} missed the mark. Please share your order details so we can resolve this quickly.",
            },
            {
                "scenario": "positive_generic",
                "template": f"Thank you for sharing your experience with {name or 'our team'} — we really appreciate your feedback.",
            },
        ],
        "reputation_risks": ["Unaddressed negative themes may suppress local pack CTR"] if negative_hits else [],
        "quick_wins": ["Respond to negative reviews within 24 hours", "Surface recurring themes to operations"],
        "recommended_tools": ["yext", "reputation_com", "reviewtrackers"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_review_reputation_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["reputation_score"] = _clamp(int(float(out.get("reputation_score", 50))))
    except (TypeError, ValueError):
        out["reputation_score"] = 50
    if not isinstance(out.get("sentiment"), dict):
        out["sentiment"] = {"overall": "mixed", "positive_pct": 50, "neutral_pct": 30, "negative_pct": 20}
    for list_key in ("themes", "response_templates", "reputation_risks", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("review_summary"), dict):
        out["review_summary"] = {"total_reviews": 0, "avg_rating": 4.0, "platform_breakdown": {}}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_review_reputation(
    *,
    brand: str,
    reviews_text: str,
    platforms: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Brand: {clean_text_fn(brand, 300)}. Platforms: {', '.join(platforms)}. "
        f"Reviews text: {clean_text_fn(reviews_text, 4000)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("reputation_score") is not None or llm.get("themes"):
            return normalize_review_reputation_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_review_reputation_signals(
        brand=brand, reviews_text=reviews_text, platforms=platforms, notes=notes
    )
    return normalize_review_reputation_result(heur, analysis_mode="heuristic", ai_available=False)
