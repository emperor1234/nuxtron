"""Competitor Intelligence Engine — phase-f module 4."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _mention_likelihood(raw: Any) -> float:
    if isinstance(raw, (int, float)):
        return max(0.0, min(1.0, float(raw) if float(raw) <= 1 else float(raw) / 100.0))
    text = str(raw or "medium").lower()
    if text in {"high", "strong"}:
        return 0.72
    if text in {"low", "weak"}:
        return 0.28
    return 0.48


def analyze_competitor_signals(
    *,
    domain: str,
    competitors: list[str],
    target_keyword: str,
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    comps = [c.strip() for c in competitors if c.strip()] or ["competitor1.com", "competitor2.com"]
    keyword = target_keyword.strip() or "seo tools"
    notes_text = notes.strip()

    competitive_score = 40
    competitive_score += min(16, len(comps) * 4)
    competitive_score += min(12, len(keyword.split()) * 3)
    competitive_score += 4 if notes_text else 0
    competitive_score = _clamp(competitive_score)

    domain_vs_competitors = []
    frontend_competitors = []
    for i, comp in enumerate(comps[:5]):
        traffic = 45000 + i * 12000
        da = _clamp(38 + i * 5 + len(keyword) // 4)
        top_kw = [f"{keyword} tool", f"best {keyword}", f"{keyword} software"]
        domain_vs_competitors.append(
            {
                "competitor": comp,
                "estimated_traffic": traffic,
                "da_estimate": da,
                "top_keywords": top_kw,
                "content_gaps": [f"{keyword} case studies", f"{keyword} ROI calculator"],
            }
        )
        frontend_competitors.append(
            {
                "domain": comp,
                "traffic_estimate": traffic,
                "domain_authority": da,
                "top_keywords": top_kw,
                "content_velocity": "medium" if i % 2 else "high",
                "ai_visibility_score": _clamp(da - 6),
            }
        )

    shared_keywords = []
    for i, kw in enumerate([keyword, f"best {keyword}", f"{keyword} software"][:3]):
        your_pos = 18 + i * 6
        comp_pos = 4 + i * 2
        shared_keywords.append(
            {
                "keyword": kw,
                "your_position": your_pos,
                "competitor_position": comp_pos,
                "opportunity": f"Close {your_pos - comp_pos}-position gap with pillar content",
                "search_volume": 1200 - i * 180,
                "opportunity_score": _clamp(88 - i * 12),
            }
        )

    content_gaps = [
        {
            "topic": f"{keyword} ROI calculator",
            "competitor_coverage": "Interactive tool on top competitor",
            "your_coverage": "none",
            "priority": "high",
            "content_format": "interactive tool",
        },
        {
            "topic": f"{keyword} case studies",
            "competitor_coverage": "Multiple detailed case studies",
            "your_coverage": "partial",
            "priority": "high",
            "content_format": "case study hub",
        },
    ]

    mention = _mention_likelihood("low")
    ai_visibility = {
        "llm_mention_likelihood": "low",
        "citation_topics": [f"{keyword} definition", f"how {keyword} works"],
        "improvement_actions": ["Add citable statistics", "Structure definitional blocks for LLM extraction"],
        "mention_likelihood": mention,
    }

    return {
        "competitive_score": competitive_score,
        "domain_vs_competitors": domain_vs_competitors,
        "competitors": frontend_competitors,
        "shared_keywords": shared_keywords,
        "content_gaps": content_gaps,
        "ai_visibility": ai_visibility,
        "quick_wins": [
            f"Publish a {keyword} ROI calculator",
            "Add three detailed customer case studies",
            "Target shared keywords within 15 positions with internal links",
        ],
        "recommended_tools": ["semrush", "ahrefs", "similarweb"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_competitor_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["competitive_score"] = _clamp(int(float(out.get("competitive_score", 50))))
    except (TypeError, ValueError):
        out["competitive_score"] = 50
    for list_key in ("domain_vs_competitors", "competitors", "shared_keywords", "content_gaps", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("ai_visibility"), dict):
        out["ai_visibility"] = {"mention_likelihood": 0.4, "citation_topics": [], "improvement_actions": []}
    ai = out["ai_visibility"]
    if "mention_likelihood" not in ai:
        ai["mention_likelihood"] = _mention_likelihood(ai.get("llm_mention_likelihood"))
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


def enrich_competitor_frontend(out: dict[str, Any], *, competitors: list[str], target_keyword: str) -> dict[str, Any]:
    if not out.get("competitors") and out.get("domain_vs_competitors"):
        comps = competitors or ["competitor1.com"]
        rebuilt = []
        for i, row in enumerate(out["domain_vs_competitors"]):
            if not isinstance(row, dict):
                continue
            domain = row.get("competitor") or (comps[i] if i < len(comps) else f"competitor{i + 1}.com")
            da = _clamp(int(float(row.get("da_estimate", 45))))
            rebuilt.append(
                {
                    "domain": domain,
                    "traffic_estimate": int(row.get("estimated_traffic", 50000)),
                    "domain_authority": da,
                    "top_keywords": row.get("top_keywords") or [target_keyword or "seo"],
                    "content_velocity": "medium",
                    "ai_visibility_score": _clamp(da - 5),
                }
            )
        out["competitors"] = rebuilt
    shared = out.get("shared_keywords") or []
    normalized_shared = []
    for i, row in enumerate(shared):
        if not isinstance(row, dict):
            continue
        kw = row.get("keyword", target_keyword or "seo side")
        your_pos = row.get("your_position")
        comp_pos = row.get("competitor_position", 5)
        normalized_shared.append(
            {
                **row,
                "keyword": kw,
                "your_position": your_pos,
                "competitor_position": comp_pos,
                "search_volume": int(row.get("search_volume", 900 - i * 100)),
                "opportunity_score": _clamp(int(row.get("opportunity_score", 70 - i * 8))),
            }
        )
    out["shared_keywords"] = normalized_shared
    gaps = out.get("content_gaps") or []
    out["content_gaps"] = [
        {**g, "content_format": g.get("content_format", "article")} if isinstance(g, dict) else g for g in gaps
    ]
    ai = out.get("ai_visibility") or {}
    if isinstance(ai, dict) and "mention_likelihood" not in ai:
        ai["mention_likelihood"] = _mention_likelihood(ai.get("llm_mention_likelihood"))
        out["ai_visibility"] = ai
    return out


async def analyze_competitor_intel(
    *,
    domain: str,
    competitors: list[str],
    target_keyword: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    comps = competitors[:5] if competitors else ["competitor1.com"]
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Competitors: {comps}. "
        f"Target keyword: {clean_text_fn(target_keyword, 300)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("competitive_score") is not None or llm.get("shared_keywords"):
            out = normalize_competitor_result(llm, analysis_mode="llm", ai_available=True)
            return enrich_competitor_frontend(out, competitors=comps, target_keyword=target_keyword)
    heur = analyze_competitor_signals(
        domain=domain, competitors=competitors, target_keyword=target_keyword, notes=notes,
    )
    out = normalize_competitor_result(heur, analysis_mode="heuristic", ai_available=False)
    return enrich_competitor_frontend(out, competitors=comps, target_keyword=target_keyword)
