"""Backlink Intelligence Engine — phase-i module 4."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_backlink_intelligence_signals(
    *,
    domain: str,
    competitor_domains: list[str],
    link_analysis_depth: str,
    include_topical_clusters: bool,
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    competitors = [c.strip() for c in competitor_domains if c.strip()]
    depth = link_analysis_depth.strip() or "standard"
    notes_text = notes.strip()

    backlink_intelligence_score = 42
    backlink_intelligence_score += min(14, len(competitors) * 4)
    backlink_intelligence_score += 6 if depth == "deep" else 3 if depth == "standard" else 0
    backlink_intelligence_score += 4 if include_topical_clusters else 0
    backlink_intelligence_score += min(8, len(notes_text) // 30)
    backlink_intelligence_score = _clamp(backlink_intelligence_score)

    da = _clamp(backlink_intelligence_score - 8)
    clusters = []
    if include_topical_clusters:
        clusters = [
            {"topic": "Core topic authority", "link_count": 80 + backlink_intelligence_score, "anchor_diversity": 0.72},
            {"topic": "Brand mentions", "link_count": 40 + len(competitors) * 10, "anchor_diversity": 0.85},
        ]

    comp_rows = [
        {
            "competitor": c,
            "backlinks": 1200 + i * 400,
            "gap_opportunity": "Resource page and skyscraper opportunities",
            "acquisition_tactics": ["broken link building", "guest post"],
        }
        for i, c in enumerate(competitors[:3] or ["competitor.example"])
    ]

    return {
        "backlink_intelligence_score": backlink_intelligence_score,
        "domain_authority_estimate": da,
        "link_graph": {
            "total_estimated_backlinks": 800 + backlink_intelligence_score * 40,
            "referring_domains": 120 + len(competitors) * 25,
            "authority_distribution": "Mixed tier profile with room to diversify anchors",
            "topical_clusters": clusters,
        },
        "competitor_analysis": comp_rows,
        "authority_distribution": {
            "tier_1_domains_pct": _clamp(da // 3),
            "tier_2_domains_pct": _clamp(da // 2),
            "long_tail_pct": _clamp(100 - (da // 3) - (da // 2)),
        },
        "acquisition_opportunities": [
            {"type": "resource_page", "difficulty": "low", "potential_links": 8 + len(competitors)},
            {"type": "skyscraper", "difficulty": "medium", "potential_links": 10},
        ],
        "next_actions": ["Launch competitor gap campaign", "Reclaim unlinked brand mentions"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_backlink_intelligence_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["backlink_intelligence_score"] = _clamp(int(float(out.get("backlink_intelligence_score", 50))))
    except (TypeError, ValueError):
        out["backlink_intelligence_score"] = 50
    try:
        out["domain_authority_estimate"] = _clamp(int(float(out.get("domain_authority_estimate", 45))))
    except (TypeError, ValueError):
        out["domain_authority_estimate"] = 45
    for list_key in ("competitor_analysis", "acquisition_opportunities", "next_actions"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("link_graph"), dict):
        out["link_graph"] = {"total_estimated_backlinks": 0, "referring_domains": 0, "authority_distribution": "", "topical_clusters": []}
    if not isinstance(out.get("authority_distribution"), dict):
        out["authority_distribution"] = {"tier_1_domains_pct": 20, "tier_2_domains_pct": 40, "long_tail_pct": 40}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_backlink_intelligence(
    *,
    domain: str,
    competitor_domains: list[str],
    link_analysis_depth: str,
    include_topical_clusters: bool,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
    llm_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Competitors: {', '.join(competitor_domains[:8])}. "
        f"Depth: {link_analysis_depth}. Topical clusters: {include_topical_clusters}. "
        f"Notes: {clean_text_fn(notes, 500)}."
    )
    llm_kwargs: dict[str, Any] = {}
    if llm_timeout_seconds is not None:
        llm_kwargs["timeout_seconds"] = llm_timeout_seconds
    llm = await ollama_json_fn(system_prompt, prompt, **llm_kwargs)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("backlink_intelligence_score") is not None or llm.get("link_graph"):
            return normalize_backlink_intelligence_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_backlink_intelligence_signals(
        domain=domain,
        competitor_domains=competitor_domains,
        link_analysis_depth=link_analysis_depth,
        include_topical_clusters=include_topical_clusters,
        notes=notes,
    )
    return normalize_backlink_intelligence_result(heur, analysis_mode="heuristic", ai_available=False)
