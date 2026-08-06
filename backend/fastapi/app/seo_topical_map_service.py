"""Topical Map & Silo Builder — phase-g module 5."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "topic"


def analyze_topical_map_signals(
    *,
    seed_topic: str,
    domain: str,
    depth: int,
    notes: str,
) -> dict[str, Any]:
    topic = seed_topic.strip()
    site = domain.strip()
    silo_depth = max(1, min(4, depth))
    notes_text = notes.strip()
    slug = _slug(topic)

    topical_authority_score = 36
    topical_authority_score += min(18, len(topic.split()) * 4)
    topical_authority_score += min(12, silo_depth * 4)
    topical_authority_score += 6 if site else 0
    topical_authority_score += 4 if notes_text else 0
    topical_authority_score = _clamp(topical_authority_score)

    pillar_title = f"Ultimate Guide to {topic}"
    pillar2 = f"{topic} Best Practices"
    cluster_pages = [
        {
            "pillar": pillar_title,
            "title": f"How to Get Started with {topic}",
            "slug": f"how-to-{slug}",
            "target_keyword": f"how to {topic.lower()}",
            "internal_links": [f"/{slug}"],
        },
        {
            "pillar": pillar_title,
            "title": f"{topic} vs Alternatives",
            "slug": f"{slug}-vs-alternatives",
            "target_keyword": f"{topic.lower()} alternatives",
            "internal_links": [f"/{slug}"],
        },
    ]

    return {
        "topical_authority_score": topical_authority_score,
        "pillar_pages": [
            {"title": pillar_title, "slug": slug, "target_keyword": topic, "word_count_target": 3200},
            {"title": pillar2, "slug": f"{slug}-best-practices", "target_keyword": f"{topic} best practices", "word_count_target": 2400},
        ],
        "cluster_pages": cluster_pages,
        "silo_structure": {
            "depth": silo_depth,
            "hubs": [
                {"hub": pillar_title, "spokes": [f"how-to-{slug}", f"{slug}-vs-alternatives"]},
                {"hub": pillar2, "spokes": [f"{slug}-checklist"]},
            ],
        },
        "content_gaps": [f"{topic} case studies", f"{topic} statistics", f"{topic} tools comparison"],
        "quick_wins": ["Publish pillar page first", "Wire hub-spoke internal links on launch"],
        "recommended_publishing_order": [pillar_title, pillar2, cluster_pages[0]["title"]],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_topical_map_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["topical_authority_score"] = _clamp(int(float(out.get("topical_authority_score", 50))))
    except (TypeError, ValueError):
        out["topical_authority_score"] = 50
    for list_key in ("pillar_pages", "cluster_pages", "content_gaps", "quick_wins", "recommended_publishing_order"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("silo_structure"), dict):
        out["silo_structure"] = {"depth": 2, "hubs": []}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def build_topical_map(
    *,
    seed_topic: str,
    domain: str,
    depth: int,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Seed topic: {clean_text_fn(seed_topic, 300)}. Domain: {clean_text_fn(domain, 300)}. "
        f"Silo depth: {depth}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("topical_authority_score") is not None or llm.get("pillar_pages"):
            return normalize_topical_map_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_topical_map_signals(seed_topic=seed_topic, domain=domain, depth=depth, notes=notes)
    return normalize_topical_map_result(heur, analysis_mode="heuristic", ai_available=False)
