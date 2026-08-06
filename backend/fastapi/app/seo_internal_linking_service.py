"""AI Internal Linking Engine — phase-e module 4."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

_LINK_TYPES = ("hub", "spoke", "bridge", "support")


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _path_title(url: str) -> str:
    path = urlparse(url if "://" in url else f"https://{url}").path.strip("/")
    if not path:
        return "Homepage"
    slug = path.split("/")[-1]
    return re.sub(r"[-_]+", " ", slug).title() or path


def analyze_internal_linking_signals(
    *,
    page_url: str,
    page_content: str,
    target_urls: list[str],
    notes: str,
) -> dict[str, Any]:
    page = page_url.strip()
    content = page_content.strip()
    targets = [t.strip() for t in target_urls if t.strip()] or ["/pricing", "/features", "/blog/best-practices"]
    notes_text = notes.strip()
    words = len(re.findall(r"\b\w+\b", content))

    linking_score = 38
    linking_score += min(16, len(targets) * 3)
    linking_score += min(14, words // 30)
    linking_score += 4 if notes_text else 0
    linking_score = _clamp(linking_score)

    suggestions = []
    opportunities = []
    for i, target in enumerate(targets[:6]):
        rel = round(max(0.55, 0.86 - i * 0.07), 2)
        anchor = "related guide" if i == 0 else "learn more"
        suggestions.append(
            {
                "from_url": page,
                "to_url": target,
                "anchor_text": anchor,
                "reason": "Topical overlap and conversion support",
                "relevance_score": rel,
                "placement_hint": "First third of content after primary definition",
            }
        )
        opportunities.append(
            {
                "from_url": page,
                "to_url": target,
                "anchor_text": anchor,
                "relevance_score": rel,
                "link_type": _LINK_TYPES[i % len(_LINK_TYPES)],
            }
        )

    hub_spoke = {"hub": page, "spokes": targets[:3]}
    hub_spoke_clusters = [
        {
            "hub_url": page,
            "hub_title": _path_title(page),
            "spoke_urls": targets[:3],
            "coverage_pct": _clamp(min(85, 35 + len(targets) * 8)),
        }
    ]

    orphan_strings = ["/blog/old-post-1", "/resources/checklist-2023"]
    orphan_pages = [
        {"url": u, "title": _path_title(u), "traffic_potential": "medium" if i else "high"}
        for i, u in enumerate(orphan_strings)
    ]

    return {
        "linking_score": linking_score,
        "suggestions": suggestions,
        "opportunities": opportunities,
        "total_opportunities": len(opportunities),
        "hub_spoke": hub_spoke,
        "hub_spoke_clusters": hub_spoke_clusters,
        "orphan_pages": orphan_pages,
        "anchor_distribution": {"branded": 28, "partial_match": 49, "exact_match": 23},
        "crawl_depth_issues": ["Some spoke pages sit 4+ clicks from homepage"] if len(targets) > 4 else [],
        "recommendations": [
            "Add 2 contextual links in the top 30% of content",
            "Replace generic anchors with intent-rich phrases",
        ],
        "quick_wins": ["Add contextual links above the fold", "Link orphan pages from hub templates"],
        "recommended_tools": ["screaming_frog", "sitebulb", "internal_linking_map"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_internal_linking_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["linking_score"] = _clamp(int(float(out.get("linking_score", 50))))
    except (TypeError, ValueError):
        out["linking_score"] = 50
    for list_key in ("suggestions", "opportunities", "quick_wins", "recommended_tools", "crawl_depth_issues", "recommendations"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("hub_spoke"), dict):
        out["hub_spoke"] = {"hub": "", "spokes": []}
    if not isinstance(out.get("hub_spoke_clusters"), list):
        out["hub_spoke_clusters"] = []
    if not isinstance(out.get("orphan_pages"), list):
        out["orphan_pages"] = []
    if not isinstance(out.get("anchor_distribution"), dict):
        out["anchor_distribution"] = {"branded": 30, "partial_match": 45, "exact_match": 25}
    if not out.get("total_opportunities") and out.get("opportunities"):
        out["total_opportunities"] = len(out["opportunities"])
    elif not out.get("total_opportunities") and out.get("suggestions"):
        out["total_opportunities"] = len(out["suggestions"])
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


def enrich_internal_linking_frontend(out: dict[str, Any], *, page_url: str) -> dict[str, Any]:
    if not out.get("opportunities") and out.get("suggestions"):
        opps = []
        for i, s in enumerate(out["suggestions"]):
            if not isinstance(s, dict):
                continue
            rel = s.get("relevance_score", 0.7)
            if isinstance(rel, (int, float)) and rel <= 1:
                rel_score = float(rel)
            else:
                rel_score = float(rel) / 100.0 if rel else 0.7
            opps.append(
                {
                    "from_url": s.get("from_url", page_url),
                    "to_url": s.get("to_url", ""),
                    "anchor_text": s.get("anchor_text", "learn more"),
                    "relevance_score": rel_score,
                    "link_type": _LINK_TYPES[i % len(_LINK_TYPES)],
                }
            )
        out["opportunities"] = opps
        out["total_opportunities"] = len(opps)
    if not out.get("hub_spoke_clusters") and out.get("hub_spoke"):
        hs = out["hub_spoke"]
        if isinstance(hs, dict):
            hub = hs.get("hub", page_url)
            spokes = hs.get("spokes", [])
            out["hub_spoke_clusters"] = [
                {"hub_url": hub, "hub_title": _path_title(str(hub)), "spoke_urls": spokes, "coverage_pct": 55}
            ]
    orphans = out.get("orphan_pages") or []
    if orphans and isinstance(orphans[0], str):
        out["orphan_pages"] = [
            {"url": u, "title": _path_title(u), "traffic_potential": "medium"} for u in orphans
        ]
    return out


async def suggest_internal_linking(
    *,
    page_url: str,
    page_content: str,
    target_urls: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    targets = target_urls[:10] if target_urls else ["/pricing"]
    prompt = (
        f"Page URL: {clean_text_fn(page_url, 500)}. Target URLs: {targets}. "
        f"Notes: {clean_text_fn(notes, 500)}. Content: {clean_text_fn(page_content, 4000)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("linking_score") is not None or llm.get("suggestions"):
            out = normalize_internal_linking_result(llm, analysis_mode="llm", ai_available=True)
            return enrich_internal_linking_frontend(out, page_url=page_url)
    heur = analyze_internal_linking_signals(
        page_url=page_url, page_content=page_content, target_urls=target_urls, notes=notes,
    )
    out = normalize_internal_linking_result(heur, analysis_mode="heuristic", ai_available=False)
    return enrich_internal_linking_frontend(out, page_url=page_url)
