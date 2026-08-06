"""Keyword Research Engine — phase-j module 1."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_keyword_research_signals(
    *,
    seed_keyword: str,
    domain: str,
    country: str,
    count: int,
) -> dict[str, Any]:
    seed = seed_keyword.strip()
    site = domain.strip()
    region = country.strip() or "US"
    target_count = max(1, min(100, count))

    keyword_research_score = 42
    keyword_research_score += min(16, len(seed.split()) * 4)
    keyword_research_score += 6 if site else 0
    keyword_research_score += 4 if region != "US" else 0
    keyword_research_score += min(10, target_count // 2)
    keyword_research_score = _clamp(keyword_research_score)

    keywords = [
        {
            "keyword": seed,
            "monthly_searches": 1200 + keyword_research_score * 40,
            "difficulty": _clamp(55 - keyword_research_score // 3),
            "opportunity_score": _clamp(keyword_research_score + 4),
            "intent": "informational",
            "serp_features": ["featured_snippet", "paa"],
        },
        {
            "keyword": f"best {seed}",
            "monthly_searches": 800 + keyword_research_score * 25,
            "difficulty": _clamp(60 - keyword_research_score // 4),
            "opportunity_score": _clamp(keyword_research_score),
            "intent": "commercial",
            "serp_features": ["ads", "reviews"],
        },
        {
            "keyword": f"how to {seed}",
            "monthly_searches": 600 + keyword_research_score * 20,
            "difficulty": _clamp(48 - keyword_research_score // 5),
            "opportunity_score": _clamp(keyword_research_score + 2),
            "intent": "informational",
            "serp_features": ["featured_snippet"],
        },
    ]

    return {
        "keyword_research_score": keyword_research_score,
        "keywords": keywords[: max(3, min(len(keywords), target_count // 5 + 2))],
        "semantic_clusters": [
            {"cluster": "Informational", "keywords": [seed, f"how to {seed}"], "opportunity": "high"},
            {"cluster": "Commercial", "keywords": [f"best {seed}"], "opportunity": "medium"},
        ],
        "quick_wins": [f"Target long-tail variant of '{seed}' with FAQ structure"],
        "featured_snippet_opportunities": [f"how to {seed}", f"what is {seed}"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_keyword_research_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["keyword_research_score"] = _clamp(int(float(out.get("keyword_research_score", 50))))
    except (TypeError, ValueError):
        out["keyword_research_score"] = 50
    for list_key in ("keywords", "semantic_clusters", "quick_wins", "featured_snippet_opportunities"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def research_keywords(
    *,
    seed_keyword: str,
    domain: str,
    country: str,
    count: int,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    kw = clean_text_fn(seed_keyword, 200)
    prompt = (
        f"Research {count} keywords for the seed: '{kw}'. "
        f"Domain: '{clean_text_fn(domain, 200)}'. Country: {country}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("keyword_research_score") is not None or llm.get("keywords"):
            return normalize_keyword_research_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_keyword_research_signals(
        seed_keyword=seed_keyword, domain=domain, country=country, count=count
    )
    return normalize_keyword_research_result(heur, analysis_mode="heuristic", ai_available=False)
