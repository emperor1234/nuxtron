"""Knowledge Graph Management — phase-e module 3."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_knowledge_graph_signals(
    *,
    domain: str,
    seed_entities: list[str],
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    seeds = [s.strip() for s in seed_entities if s.strip()] or ["brand", "core product", "industry concept"]
    notes_text = notes.strip()

    graph_health_score = 36
    graph_health_score += min(24, len(seeds) * 4)
    graph_health_score += 6 if notes_text else 0
    graph_health_score += 4 if site else 0
    graph_health_score = _clamp(graph_health_score)

    entities = [
        {"name": name, "type": ["brand", "product", "concept", "person", "org"][i % 5], "confidence": round(0.72 + (i * 0.04), 2)}
        for i, name in enumerate(seeds[:8])
    ]
    relationships = []
    for i in range(min(3, len(seeds) - 1)):
        relationships.append(
            {
                "from": seeds[i],
                "to": seeds[i + 1],
                "type": "related" if i else "parent",
                "confidence": round(0.7 + i * 0.05, 2),
            }
        )

    orphan_count = max(0, len(seeds) - 2)
    coverage_pct = _clamp(min(78, 28 + len(seeds) * 8))

    return {
        "graph_health_score": graph_health_score,
        "entities": entities,
        "relationships": relationships,
        "coverage": {"entity_pages_pct": coverage_pct, "orphan_entities": orphan_count, "duplicate_entities": 1 if len(seeds) > 4 else 0},
        "gaps": ["Missing comparison entities", "Weak cross-entity relationship depth"],
        "next_entities_to_build": [f"{seeds[0]} competitor", f"{seeds[-1]} use case", "category benchmark"][:3],
        "quick_wins": ["Add entity schema blocks to top landing pages", "Merge duplicate alias entities"],
        "recommended_tools": ["neo4j", "wikidata", "schema_org"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_knowledge_graph_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["graph_health_score"] = _clamp(int(float(out.get("graph_health_score", 50))))
    except (TypeError, ValueError):
        out["graph_health_score"] = 50
    for list_key in ("entities", "relationships", "gaps", "next_entities_to_build", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("coverage"), dict):
        out["coverage"] = {"entity_pages_pct": 50, "orphan_entities": 0, "duplicate_entities": 0}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_knowledge_graph(
    *,
    domain: str,
    seed_entities: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    seeds = seed_entities[:10] if seed_entities else ["brand"]
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Seed entities: {seeds}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("graph_health_score") is not None or llm.get("entities"):
            return normalize_knowledge_graph_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_knowledge_graph_signals(domain=domain, seed_entities=seed_entities, notes=notes)
    return normalize_knowledge_graph_result(heur, analysis_mode="heuristic", ai_available=False)
