"""
Entity SEO — module 10.

Extracts named entities and knowledge-graph opportunities from content signals.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b")
_ORG_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&\s]{2,48}(?:Inc|LLC|Ltd|Corp|Corporation|Company|University|Institute|Foundation)\.?)\b"
)
_IS_A_RE = re.compile(r"\b([A-Z][A-Za-z0-9\s]{2,40})\s+is\s+(?:a|an)\s+([A-Za-z0-9\s]{2,40})", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_STOPWORDS = {
    "The",
    "This",
    "That",
    "These",
    "Those",
    "However",
    "Therefore",
    "Additionally",
    "Furthermore",
    "What",
    "When",
    "Where",
    "Why",
    "How",
}


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _clamp_salience(value: float) -> float:
    return round(max(0.05, min(0.98, value)), 2)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _guess_entity_type(name: str, *, topic: str) -> str:
    lower = name.lower()
    if any(token in lower for token in ("inc", "llc", "corp", "company", "university", "institute")):
        return "Organization"
    if name.lower() == topic.lower() or lower in topic.lower():
        return "Concept"
    if len(name.split()) == 1 and name[0].isupper():
        return "Person"
    return "Concept"


def _extract_entity_candidates(content: str, topic: str) -> list[str]:
    candidates: list[str] = []
    if topic.strip():
        candidates.append(topic.strip())
    candidates.extend(match.group(1).strip() for match in _ORG_RE.finditer(content))
    candidates.extend(match.group(1).strip() for match in _PROPER_NOUN_RE.finditer(content))

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        name = re.sub(r"\s+", " ", raw).strip(" ,.;:")
        if len(name) < 3 or name in _STOPWORDS:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
    return cleaned[:12]


def _entity_context(content: str, name: str) -> str:
    pattern = re.compile(re.escape(name), re.IGNORECASE)
    match = pattern.search(content)
    if not match:
        return "Mentioned in content."
    start = max(0, match.start() - 40)
    end = min(len(content), match.end() + 40)
    snippet = content[start:end].strip()
    return re.sub(r"\s+", " ", snippet)[:120]


def analyze_entity_signals(*, content: str, topic: str) -> dict[str, Any]:
    """Deterministic entity extraction and coverage scoring."""
    body = content.strip()
    topic_clean = topic.strip()
    word_count = _word_count(body)
    bracket_count = len(_BRACKET_RE.findall(body))
    url_count = len(_URL_RE.findall(body))

    candidates = _extract_entity_candidates(body, topic_clean)
    if not candidates and topic_clean:
        candidates = [topic_clean]

    counts = Counter()
    body_lower = body.lower()
    for name in candidates:
        counts[name] = len(re.findall(re.escape(name), body, re.IGNORECASE))

    entities_found: list[dict[str, Any]] = []
    for name in candidates:
        mentions = counts[name]
        salience = _clamp_salience(0.25 + min(0.55, mentions * 0.12) + (0.15 if name.lower() == topic_clean.lower() else 0))
        entity_type = _guess_entity_type(name, topic=topic_clean)
        wiki_eligible = salience >= 0.55 and entity_type in {"Person", "Organization", "Concept"}
        entities_found.append(
            {
                "name": name,
                "entity": name,
                "type": entity_type,
                "salience": salience,
                "prominence": salience,
                "wiki_eligible": wiki_eligible,
                "context": _entity_context(body, name),
                "co_occurrence_opportunities": [],
            }
        )

    if topic_clean:
        topic_present = any(e["name"].lower() == topic_clean.lower() for e in entities_found)
        if not topic_present:
            entities_found.insert(
                0,
                {
                    "name": topic_clean,
                    "entity": topic_clean,
                    "type": "Concept",
                    "salience": 0.35,
                    "prominence": 0.35,
                    "wiki_eligible": False,
                    "context": "Topic entity under-represented in content.",
                    "co_occurrence_opportunities": ["Add explicit definition paragraph for the main topic."],
                },
            )

    for entity in entities_found:
        peers = [other["name"] for other in entities_found if other["name"] != entity["name"]][:3]
        entity["co_occurrence_opportunities"] = [
            f"Mention '{peer}' alongside '{entity['name']}' in a supporting paragraph." for peer in peers[:2]
        ]

    entity_count = len(entities_found)
    topic_hits = body_lower.count(topic_clean.lower()) if topic_clean else 0
    entity_coverage_score = 30
    entity_coverage_score += min(24, entity_count * 4)
    entity_coverage_score += min(16, topic_hits * 4)
    if word_count >= 200:
        entity_coverage_score += 10
    entity_coverage_score -= min(12, bracket_count * 4)
    entity_coverage_score = _clamp(entity_coverage_score)

    authority_score = 32
    authority_score += min(24, url_count * 8)
    authority_score += min(16, sum(1 for e in entities_found if e["wiki_eligible"]) * 4)
    authority_score = _clamp(authority_score)

    entity_seo_score = _clamp(int(round((entity_coverage_score * 0.55) + (authority_score * 0.45))))

    knowledge_graph_entries = [
        {
            "entity": entity["name"],
            "kg_id": None,
            "description": entity["context"][:160],
            "types": [entity["type"]],
            "prominence": entity["prominence"],
        }
        for entity in entities_found
        if entity.get("wiki_eligible")
    ]

    entity_relations: list[dict[str, Any]] = []
    for match in _IS_A_RE.finditer(body):
        subject = match.group(1).strip()
        obj = match.group(2).strip().rstrip(".")
        if len(subject) >= 2 and len(obj) >= 2:
            entity_relations.append(
                {
                    "subject": subject,
                    "relation": "is_a",
                    "object": obj,
                    "confidence": 0.72,
                }
            )

    missing_entities: list[str] = []
    if topic_clean and topic_hits < 2:
        missing_entities.append(topic_clean)
    if entity_count < 3 and topic_clean:
        missing_entities.append(f"{topic_clean} related subtopic")

    co_occurrence_clusters: list[dict[str, Any]] = []
    if len(entities_found) >= 2:
        co_occurrence_clusters.append(
            {
                "cluster": topic_clean or "Primary entity cluster",
                "entities": [e["name"] for e in entities_found[:5]],
            }
        )

    knowledge_graph_opportunities = [
        "Add Organization or Person schema for named entities with stable identifiers.",
        "Cross-link entity mentions to authoritative definition pages.",
    ]
    if not knowledge_graph_entries:
        knowledge_graph_opportunities.append("Introduce at least one wiki-eligible entity with clear type and description.")

    semantic_improvements = [
        "Increase co-occurrence density between the main topic and supporting entities.",
        "Add explicit entity definitions in the opening section.",
    ]
    if url_count < 2:
        semantic_improvements.append("Cite external authority pages that reinforce entity relationships.")

    schema_recommendations = ["Organization", "Article"]
    if any(e["type"] == "Person" for e in entities_found):
        schema_recommendations.append("Person")
    if topic_clean:
        schema_recommendations.append("DefinedTerm")

    optimization_plan = [
        f"Define '{topic_clean or 'the primary topic'}' in the first paragraph with schema markup.",
        "Add an entity glossary block linking related concepts.",
        "Use consistent entity naming across headings and body copy.",
    ]

    return {
        "entity_seo_score": entity_seo_score,
        "entity_coverage_score": entity_coverage_score,
        "entity_coverage_pct": entity_coverage_score,
        "authority_score": authority_score,
        "entities_found": entities_found,
        "knowledge_graph_opportunities": knowledge_graph_opportunities,
        "knowledge_graph_entries": knowledge_graph_entries,
        "semantic_improvements": semantic_improvements,
        "entity_relations": entity_relations,
        "missing_entities": missing_entities,
        "co_occurrence_clusters": co_occurrence_clusters,
        "schema_recommendations": schema_recommendations,
        "optimization_plan": optimization_plan,
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "word_count": word_count,
            "entity_count": entity_count,
            "reference_urls": url_count,
            "topic_hits": topic_hits,
        },
    }


def normalize_entity_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for score_key in ("entity_seo_score", "entity_coverage_score", "authority_score"):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50

    out["entity_coverage_pct"] = out.get("entity_coverage_pct", out.get("entity_coverage_score", 50))
    try:
        out["entity_coverage_pct"] = _clamp(int(float(out["entity_coverage_pct"])))
    except (TypeError, ValueError):
        out["entity_coverage_pct"] = out.get("entity_coverage_score", 50)

    entities = out.get("entities_found")
    if not isinstance(entities, list):
        entities = []
    normalized_entities: list[dict[str, Any]] = []
    for item in entities:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("entity") or "").strip()
        if not name:
            continue
        salience_raw = item.get("salience", item.get("prominence", 0.5))
        try:
            salience = _clamp_salience(float(salience_raw))
        except (TypeError, ValueError):
            salience = 0.5
        normalized_entities.append(
            {
                **item,
                "name": name,
                "entity": name,
                "type": item.get("type") or "Concept",
                "salience": salience,
                "prominence": salience,
                "context": item.get("context") or "Mentioned in content.",
                "co_occurrence_opportunities": item.get("co_occurrence_opportunities")
                if isinstance(item.get("co_occurrence_opportunities"), list)
                else [],
            }
        )
    out["entities_found"] = normalized_entities

    for list_key in (
        "knowledge_graph_opportunities",
        "knowledge_graph_entries",
        "semantic_improvements",
        "entity_relations",
        "missing_entities",
        "co_occurrence_clusters",
        "schema_recommendations",
        "optimization_plan",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    if not out.get("entity_seo_score"):
        out["entity_seo_score"] = _clamp(
            int(round((out["entity_coverage_score"] + out["authority_score"]) / 2))
        )

    if not out.get("optimization_plan") and out.get("semantic_improvements"):
        out["optimization_plan"] = list(out["semantic_improvements"])

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_entity_seo(
    *,
    content: str,
    topic: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run Entity SEO analysis."""
    prompt = (
        f"Analyze Entity SEO for topic: {clean_text_fn(topic, 300)}.\n"
        f"Content:\n{clean_text_fn(content, 3000)}\n\n"
        "Extract named entities, salience, wiki eligibility, and knowledge graph opportunities. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("entities_found") or llm_result.get("entity_coverage_score") is not None:
            return normalize_entity_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_entity_signals(content=content, topic=topic)
    return normalize_entity_result(heuristic, analysis_mode="heuristic", ai_available=False)
