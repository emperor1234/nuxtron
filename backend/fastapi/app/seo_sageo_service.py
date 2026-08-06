"""
SAGEO (Search-Augmented Generative Engine Optimization) — module 5.

Builds a generative SEO plan from topic, intent, source material, and target engines.
Uses LLM when available; otherwise deterministic content-signal heuristics.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_STAT_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?%|\b\d{4}\b")
_QUESTION_RE = re.compile(r"\?")
_HEADING_RE = re.compile(r"^#{1,3}\s+|\n#{1,3}\s+", re.MULTILINE)
_LIST_RE = re.compile(r"^\s*[-*•]\s+|\n\s*[-*•]\s+|\n\s*\d+\.\s+", re.MULTILINE)
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

_DEFAULT_ENGINES = ["Google AI Overview", "ChatGPT", "Perplexity"]


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _supporting_intents(primary: str) -> list[str]:
    primary_lower = primary.lower()
    if primary_lower == "informational":
        return ["navigational", "commercial investigation"]
    if primary_lower == "commercial":
        return ["informational", "transactional"]
    if primary_lower == "transactional":
        return ["commercial", "navigational"]
    return ["informational", "commercial"]


def analyze_sageo_signals(
    *,
    topic: str,
    search_intent: str,
    source_material: str,
    target_engines: list[str],
    notes: str,
) -> dict[str, Any]:
    """Deterministic SAGEO plan from operator inputs."""
    topic_clean = topic.strip()
    intent = (search_intent or "informational").strip().lower()
    material = source_material.strip()
    engines = [e.strip() for e in target_engines if e.strip()] or _DEFAULT_ENGINES
    words = re.findall(r"\b\w+\b", material)
    word_count = len(words)
    stat_count = len(_STAT_RE.findall(material))
    question_count = len(_QUESTION_RE.findall(material))
    heading_count = len(_HEADING_RE.findall(material))
    list_count = len(_LIST_RE.findall(material))
    url_count = len(_URL_RE.findall(material))
    bracket_count = len(_BRACKET_RE.findall(material))

    score = 36
    score += min(18, word_count // 40)
    score += min(12, stat_count * 4)
    score += min(8, question_count * 3)
    score += min(8, heading_count * 3)
    score += min(6, list_count * 2)
    score += min(8, url_count * 4)
    score += min(6, len(engines) * 2)
    if notes.strip():
        score += 4
    score -= min(15, bracket_count * 5)
    if word_count < 80:
        score -= 10
    score = _clamp(score)

    confidence = round(min(0.95, 0.55 + word_count / 1200 + stat_count * 0.04), 2)

    source_priorities = [
        {
            "source_type": "first_party",
            "reason": "Canonical facts on owned pages anchor generative citations.",
            "priority": "high",
            "trust_signal": "HTTPS + consistent entity naming",
        },
        {
            "source_type": "dataset",
            "reason": "Citable metrics improve AI Overview and Perplexity inclusion.",
            "priority": "high" if stat_count >= 1 else "medium",
            "trust_signal": "dated statistics with methodology",
        },
        {
            "source_type": "expert_quote",
            "reason": "Named practitioner quotes increase E-E-A-T for answer engines.",
            "priority": "medium",
            "trust_signal": "author credentials + publication",
        },
    ]
    if url_count >= 2:
        source_priorities.append(
            {
                "source_type": "third_party_reference",
                "reason": "Outbound citations to authoritative sources strengthen retrieval grounding.",
                "priority": "high",
                "trust_signal": f"{url_count} reference URLs detected in source material",
            }
        )

    retrieval_blueprint = {
        "chunking_strategy": "semantic_paragraph" if word_count >= 200 else "fixed_window",
        "passage_size_words": 120 if word_count >= 200 else 90,
        "overlap_words": 20,
        "embedding_model": "text-embedding-3-large",
        "reranker": "cohere-rerank-v3",
        "top_k": 8 if word_count >= 300 else 5,
    }

    generative_entry_points: list[dict[str, Any]] = []
    for engine in engines[:6]:
        content_type = "definition"
        if intent == "commercial":
            content_type = "comparison"
        elif intent == "transactional" or question_count >= 2:
            content_type = "how-to"
        probability = round(min(0.92, 0.45 + score / 200 + stat_count * 0.03), 2)
        generative_entry_points.append(
            {
                "surface": engine,
                "content_type": content_type,
                "probability": probability,
            }
        )

    answer_blueprint = [
        {
            "section": "direct_answer",
            "word_count": 45,
            "format": "declarative",
            "entity_density": "high",
            "guidance": f"Answer what {topic_clean or 'the topic'} is in one paragraph.",
        },
        {
            "section": "supporting_evidence",
            "word_count": 120,
            "format": "bullet_list",
            "cite_sources": True,
            "guidance": "List 3–5 evidence bullets with outbound citations.",
        },
        {
            "section": "actionable_conclusion",
            "word_count": 60,
            "format": "numbered_steps",
            "guidance": "Close with numbered next steps aligned to search intent.",
        },
    ]

    coverage_gaps: list[dict[str, Any]] = []
    if stat_count < 2:
        coverage_gaps.append(
            {
                "topic": "Quantified evidence",
                "engine_affected": engines[:2],
                "fix": "Add at least two dated statistics with linked sources.",
            }
        )
    if question_count < 1:
        coverage_gaps.append(
            {
                "topic": "Question-led sections",
                "engine_affected": ["Google AI Overview", "ChatGPT"],
                "fix": "Add H2 questions that mirror People Also Ask phrasing.",
            }
        )
    if word_count < 150:
        coverage_gaps.append(
            {
                "topic": "Source material depth",
                "engine_affected": engines,
                "fix": "Expand source material beyond 150 words with definitions and examples.",
            }
        )

    next_actions: list[dict[str, Any]] = [
        {
            "action": f"Draft a direct-answer block for '{topic_clean or 'topic'}' under 45 words",
            "priority": "high",
            "effort": "low",
            "expected_impact": "Improves generative snippet eligibility",
        },
        {
            "action": "Implement FAQPage or HowTo schema for question-led sections",
            "priority": "high",
            "effort": "medium",
            "expected_impact": "Improves structured answer surfacing",
        },
    ]
    if stat_count < 2:
        next_actions.append(
            {
                "action": "Add two verifiable statistics with citations to source material",
                "priority": "high",
                "effort": "medium",
                "expected_impact": "Raises citation probability on Perplexity and AI Overviews",
            }
        )
    if notes.strip():
        next_actions.append(
            {
                "action": f"Operator note: {notes.strip()[:160]}",
                "priority": "medium",
                "effort": "low",
                "expected_impact": "Aligns plan with team context",
            }
        )

    augmentation_sources: list[dict[str, Any]] = []
    if url_count:
        augmentation_sources.append(
            {
                "source": "References already present in source material",
                "authority_score": _clamp(60 + url_count * 8),
                "freshness_days": 45,
                "inclusion_method": "cite",
            }
        )
    else:
        augmentation_sources.append(
            {
                "source": "Tier-1 industry publication or official documentation",
                "authority_score": 85,
                "freshness_days": 30,
                "inclusion_method": "cite",
            }
        )

    return {
        "sageo_score": score,
        "intent_map": {
            "primary_intent": intent,
            "supporting_intents": _supporting_intents(intent),
            "intent_confidence": confidence,
        },
        "source_priorities": source_priorities,
        "retrieval_blueprint": retrieval_blueprint,
        "generative_entry_points": generative_entry_points,
        "answer_blueprint": answer_blueprint,
        "augmentation_sources": augmentation_sources,
        "coverage_gaps": coverage_gaps,
        "next_actions": next_actions,
        "quick_wins": [
            "Add a TL;DR block at the top of the target page.",
            "Turn top questions into FAQ schema blocks.",
            "Cite at least two authoritative sources for core claims.",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "word_count": word_count,
            "stat_count": stat_count,
            "question_count": question_count,
            "reference_urls": url_count,
            "bracket_placeholders": bracket_count,
            "engines_targeted": len(engines),
        },
    }


def normalize_sageo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    try:
        out["sageo_score"] = _clamp(int(float(out.get("sageo_score", 50))))
    except (TypeError, ValueError):
        out["sageo_score"] = 50

    intent_map = out.get("intent_map")
    if not isinstance(intent_map, dict):
        out["intent_map"] = {"primary_intent": "informational", "supporting_intents": [], "intent_confidence": 0.7}

    for list_key in (
        "source_priorities",
        "generative_entry_points",
        "answer_blueprint",
        "augmentation_sources",
        "coverage_gaps",
        "next_actions",
        "quick_wins",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    retrieval = out.get("retrieval_blueprint")
    if not isinstance(retrieval, dict):
        out["retrieval_blueprint"] = {
            "chunking_strategy": "semantic_paragraph",
            "passage_size_words": 120,
            "overlap_words": 20,
            "embedding_model": "text-embedding-3-large",
            "reranker": "cohere-rerank-v3",
            "top_k": 8,
        }

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_sageo_plan(
    *,
    topic: str,
    search_intent: str,
    source_material: str,
    target_engines: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run SAGEO analysis."""
    engines = target_engines or _DEFAULT_ENGINES
    prompt = (
        f"Build a SAGEO strategy for topic: '{clean_text_fn(topic, 300)}'.\n"
        f"Primary search intent: {clean_text_fn(search_intent, 120)}.\n"
        f"Target generative engines: {', '.join(engines[:8])}.\n"
        f"Source material:\n{clean_text_fn(source_material, 2500)}\n\n"
        f"Notes: {clean_text_fn(notes, 500)}.\n"
        "Return intent map, source priorities, retrieval blueprint, entry points, gaps, and next actions. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("sageo_score") is not None or llm_result.get("intent_map"):
            return normalize_sageo_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_sageo_signals(
        topic=topic,
        search_intent=search_intent,
        source_material=source_material,
        target_engines=engines,
        notes=notes,
    )
    return normalize_sageo_result(heuristic, analysis_mode="heuristic", ai_available=False)
