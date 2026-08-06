"""Link Building — phase-d module 1."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

_OPP_TYPES = {"guest_post", "resource_page", "broken_link", "skyscraper", "unlinked_mention", "podcast", "interview"}


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_linkbuilding_signals(
    *,
    domain: str,
    competitors: list[str],
    niche: str,
    target_keywords: list[str],
    opportunity_types: list[str],
) -> dict[str, Any]:
    site = domain.strip()
    comps = [c.strip() for c in competitors if c.strip()]
    kw = [k.strip() for k in target_keywords if k.strip()]
    opps = [o.strip().lower() for o in opportunity_types if o.strip()] or ["guest_post", "resource_page", "broken_link"]
    niche_text = niche.strip() or (kw[0] if kw else "industry")

    parsed = urlparse(site if "://" in site else f"https://{site}") if site else None
    https_ok = bool(parsed and parsed.scheme == "https")

    linkbuilding_score = 38
    linkbuilding_score += min(14, len(comps) * 4)
    linkbuilding_score += min(12, len(kw) * 3)
    linkbuilding_score += min(10, len(opps) * 2)
    linkbuilding_score += 8 if https_ok else 0
    linkbuilding_score = _clamp(linkbuilding_score)

    domain_authority_estimate = _clamp(28 + len(comps) * 4 + len(kw) * 2)
    link_velocity_target = min(12, 3 + len(opps))

    backlink_gaps = [
        {"topic": niche_text, "opportunity": "Resource page links from niche publications", "difficulty": "medium"},
        {"topic": f"{niche_text} comparisons", "opportunity": "Guest posts on comparison blogs", "difficulty": "low"},
    ]

    outreach_targets = [
        {"type": opp if opp in _OPP_TYPES else "resource_page", "site_type": "industry_blog", "approach": f"Pitch {opp.replace('_', ' ')} with data asset"}
        for opp in opps[:4]
    ]

    prospects = []
    for idx, opp in enumerate(opps[:6]):
        dr = _clamp(35 + idx * 5 + len(kw))
        prospects.append(
            {
                "domain": f"prospect-{idx + 1}.example",
                "url": f"https://prospect-{idx + 1}.example/{niche_text.replace(' ', '-')}",
                "opportunity_type": opp if opp in _OPP_TYPES else "resource_page",
                "domain_rating": dr,
                "monthly_traffic": 1200 + idx * 400,
                "relevance_score": _clamp(55 + len(kw) * 4),
                "contact_hint": "editor@prospect.example",
                "status": "new",
            }
        )

    quick_wins = ["Claim unlinked brand mentions", "Fix broken outbound references on top pages"]
    if "broken_link" in opps:
        quick_wins.append("Run broken-link reclamation on competitor resource pages")

    top_types: dict[str, int] = {}
    for p in prospects:
        top_types[p["opportunity_type"]] = top_types.get(p["opportunity_type"], 0) + 1

    return {
        "linkbuilding_score": linkbuilding_score,
        "domain_authority_estimate": domain_authority_estimate,
        "backlink_gaps": backlink_gaps,
        "outreach_targets": outreach_targets,
        "quick_wins": quick_wins,
        "link_velocity_target": link_velocity_target,
        "total_prospects": len(prospects),
        "prospects": prospects,
        "top_opportunity_types": [{"type": k, "count": v} for k, v in top_types.items()],
        "average_domain_rating": round(sum(p["domain_rating"] for p in prospects) / max(1, len(prospects)), 1),
        "estimated_link_velocity": link_velocity_target,
        "strategy_notes": quick_wins + [f"Prioritize {niche_text} anchors aligned to: {', '.join(kw[:3])}" if kw else "Define target keyword anchors"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_linkbuilding_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for key in ("linkbuilding_score", "domain_authority_estimate"):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50
    for list_key in ("backlink_gaps", "outreach_targets", "quick_wins", "prospects", "strategy_notes"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_linkbuilding(
    *,
    domain: str,
    competitors: list[str],
    niche: str,
    target_keywords: list[str],
    opportunity_types: list[str],
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Analyze link building for domain: {clean_text_fn(domain, 200)}. "
        f"Niche: {clean_text_fn(niche or (target_keywords[0] if target_keywords else ''), 200)}. "
        f"Competitors: {competitors[:5]}. Keywords: {target_keywords[:10]}. "
        f"Opportunity types: {opportunity_types[:8]}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("domain_authority_estimate") is not None or llm.get("backlink_gaps"):
            return normalize_linkbuilding_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_linkbuilding_signals(
        domain=domain, competitors=competitors, niche=niche,
        target_keywords=target_keywords, opportunity_types=opportunity_types,
    )
    return normalize_linkbuilding_result(heur, analysis_mode="heuristic", ai_available=False)
