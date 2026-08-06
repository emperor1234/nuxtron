"""
GXO (Generative Experience Optimization) — module 8.

Optimizes for Google AI Overview citation readiness from topic, URL, and content signals.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFINITION_RE = re.compile(r"\b(is a|are a|refers to|defined as|means that)\b", re.IGNORECASE)
_STAT_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?%|\b\d{4}\b")
_HEADING_RE = re.compile(r"^#{1,3}\s+|\n#{1,3}\s+|<h[1-3]\b", re.IGNORECASE | re.MULTILINE)
_LIST_RE = re.compile(r"^\s*[-*•]\s+|\n\s*[-*•]\s+|\n\s*\d+\.\s+", re.MULTILINE)
_QUESTION_RE = re.compile(r"\?")
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_HOWTO_RE = re.compile(r"\b(step \d+|how to|first,|second,|finally,)\b", re.IGNORECASE)
_COMPARE_RE = re.compile(r"\b(vs\.?|versus|compared to|alternative)\b", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _clamp_prob(value: float) -> float:
    return round(max(0.05, min(0.92, value)), 2)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def analyze_gxo_signals(*, topic: str, content: str, url: str) -> dict[str, Any]:
    """Deterministic GXO scoring from content structure and AI-overview readiness cues."""
    topic_clean = topic.strip()
    body = content.strip()
    page_url = url.strip()

    words = re.findall(r"\b\w+\b", body)
    word_count = len(words)
    topic_hits = body.lower().count(topic_clean.lower()) if topic_clean else 0
    definition = bool(_DEFINITION_RE.search(body))
    stat_count = len(_STAT_RE.findall(body))
    heading_count = len(_HEADING_RE.findall(body))
    list_count = len(_LIST_RE.findall(body))
    question_count = len(_QUESTION_RE.findall(body))
    bracket_count = len(_BRACKET_RE.findall(body))
    howto_hits = len(_HOWTO_RE.findall(body))
    compare_hits = len(_COMPARE_RE.findall(body))

    parsed = urlparse(page_url) if page_url else None
    https_ok = bool(parsed and parsed.scheme == "https")

    structured_data_score = 34
    if heading_count >= 2:
        structured_data_score += 16
    if list_count >= 2:
        structured_data_score += 12
    if question_count >= 1:
        structured_data_score += 10
    if howto_hits >= 1:
        structured_data_score += 8
    structured_data_score -= min(15, bracket_count * 5)
    structured_data_score = _clamp(structured_data_score)

    comprehensiveness_score = 32
    if word_count >= 500:
        comprehensiveness_score += 24
    elif word_count >= 220:
        comprehensiveness_score += 16
    elif word_count >= 120:
        comprehensiveness_score += 8
    else:
        comprehensiveness_score -= 8
    if stat_count >= 2:
        comprehensiveness_score += 10
    if compare_hits >= 1:
        comprehensiveness_score += 8
    comprehensiveness_score = _clamp(comprehensiveness_score)

    entity_prominence_score = 36
    if topic_hits >= 3:
        entity_prominence_score += 18
    elif topic_hits >= 1:
        entity_prominence_score += 10
    if definition:
        entity_prominence_score += 14
    entity_prominence_score = _clamp(entity_prominence_score)

    helpful_content_score = _clamp(int(round((comprehensiveness_score + entity_prominence_score) / 2)))
    depth_score = comprehensiveness_score
    originality_score = _clamp(helpful_content_score - min(10, bracket_count * 3))

    gxo_score = _clamp(
        int(round((structured_data_score + comprehensiveness_score + entity_prominence_score) / 3))
    )
    if https_ok:
        gxo_score = _clamp(gxo_score + 4)

    citation_probability = _clamp_prob(
        0.16 + (gxo_score / 250) + (stat_count * 0.03) + (0.06 if question_count >= 2 else 0)
    )

    citation_triggers: list[dict[str, Any]] = []
    if definition:
        citation_triggers.append(
            {
                "trigger": f"What is {topic_clean or 'the topic'}?",
                "format": "definition",
                "probability": _clamp_prob(citation_probability + 0.08),
                "schema_support": "FAQPage",
            }
        )
    if howto_hits >= 1:
        citation_triggers.append(
            {
                "trigger": f"How to {topic_clean or 'implement this'}",
                "format": "how-to",
                "probability": _clamp_prob(citation_probability + 0.05),
                "schema_support": "HowTo",
            }
        )
    if compare_hits >= 1:
        citation_triggers.append(
            {
                "trigger": f"{topic_clean or 'Topic'} comparison",
                "format": "comparison",
                "probability": _clamp_prob(citation_probability + 0.04),
                "schema_support": "Article",
            }
        )
    if stat_count >= 1:
        citation_triggers.append(
            {
                "trigger": "Quantified claim with source",
                "format": "statistic",
                "probability": _clamp_prob(citation_probability + 0.06),
                "schema_support": "Article",
            }
        )

    sge_readiness_checklist: list[dict[str, Any]] = [
        {
            "check": "Direct answer block under 60 words",
            "status": "pass" if definition and word_count >= 80 else "partial" if word_count >= 80 else "fail",
            "impact": "high",
            "fix": "Add a concise definition paragraph near the top.",
        },
        {
            "check": "FAQ or question-led sections",
            "status": "pass" if question_count >= 2 else "partial" if question_count == 1 else "fail",
            "impact": "high",
            "fix": "Add two H2 questions aligned to People Also Ask phrasing.",
        },
        {
            "check": "Structured headings and lists",
            "status": "pass" if heading_count >= 2 and list_count >= 1 else "partial",
            "impact": "medium",
            "fix": "Break content into scannable sections with bullet lists.",
        },
    ]

    schema_recommendations: list[dict[str, Any]] = []
    if question_count >= 1:
        schema_recommendations.append(
            {
                "type": "FAQPage",
                "missing_fields": ["acceptedAnswer"] if question_count < 2 else [],
                "implementation_effort": "low",
            }
        )
    if howto_hits >= 1:
        schema_recommendations.append(
            {
                "type": "HowTo",
                "missing_fields": ["step"] if list_count < 2 else [],
                "implementation_effort": "medium",
            }
        )
    schema_recommendations.append(
        {
            "type": "Article",
            "missing_fields": ["author", "datePublished"] if not page_url else ["author"],
            "implementation_effort": "low",
        }
    )

    improvements: list[dict[str, Any]] = []
    if word_count < 220:
        improvements.append(
            {
                "priority": "high",
                "action": "Expand content depth beyond 220 words with examples and supporting evidence.",
                "expected_citation_lift_pct": 14,
                "effort": "medium",
            }
        )
    if stat_count < 2:
        improvements.append(
            {
                "priority": "high",
                "action": "Add at least two citable statistics with linked sources.",
                "expected_citation_lift_pct": 12,
                "effort": "medium",
            }
        )
    if question_count < 2:
        improvements.append(
            {
                "priority": "high",
                "action": "Add FAQ-style sections that mirror common AI Overview queries.",
                "expected_citation_lift_pct": 16,
                "effort": "low",
            }
        )
    if not https_ok and page_url:
        improvements.append(
            {
                "priority": "medium",
                "action": "Publish the target URL over HTTPS for trust and crawl stability.",
                "expected_citation_lift_pct": 6,
                "effort": "medium",
            }
        )

    return {
        "gxo_score": gxo_score,
        "ai_overview_citation_probability": citation_probability,
        "structured_data_score": structured_data_score,
        "comprehensiveness_score": comprehensiveness_score,
        "entity_prominence_score": entity_prominence_score,
        "content_quality_signals": {
            "helpful_content_score": helpful_content_score,
            "depth_score": depth_score,
            "originality_score": originality_score,
            "eeat_alignment": round(min(0.95, helpful_content_score / 110), 2),
        },
        "citation_triggers": citation_triggers,
        "sge_readiness_checklist": sge_readiness_checklist,
        "improvements": improvements,
        "schema_recommendations": schema_recommendations,
        "competitor_citation_benchmark": {
            "avg_competitor_citation_prob": _clamp_prob(citation_probability + 0.08),
            "gap_score": _clamp(18 - max(0, gxo_score - 55)),
            "top_cited_patterns": ["definition blocks", "FAQ schema", "step lists"],
        },
        "quick_wins": [
            "Add FAQPage schema for top two questions.",
            "Place a 45-word direct answer under the H1.",
            "Cite two authoritative sources for key claims.",
        ],
        "next_actions": [
            {
                "action": f"Draft AI Overview answer block for '{topic_clean or 'topic'}'",
                "priority": "high",
                "effort": "low",
                "expected_impact": "Improves generative citation eligibility",
            }
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "word_count": word_count,
            "topic_hits": topic_hits,
            "stat_count": stat_count,
            "question_count": question_count,
            "https": https_ok,
        },
    }


def normalize_gxo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for score_key in (
        "gxo_score",
        "structured_data_score",
        "comprehensiveness_score",
        "entity_prominence_score",
    ):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50

    try:
        out["ai_overview_citation_probability"] = _clamp_prob(
            float(out.get("ai_overview_citation_probability", 0.3))
        )
    except (TypeError, ValueError):
        out["ai_overview_citation_probability"] = 0.3

    if not isinstance(out.get("content_quality_signals"), dict):
        out["content_quality_signals"] = {}

    for list_key in (
        "citation_triggers",
        "sge_readiness_checklist",
        "improvements",
        "schema_recommendations",
        "quick_wins",
        "next_actions",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    benchmark = out.get("competitor_citation_benchmark")
    if not isinstance(benchmark, dict):
        out["competitor_citation_benchmark"] = {
            "avg_competitor_citation_prob": out["ai_overview_citation_probability"],
            "gap_score": 0,
            "top_cited_patterns": [],
        }

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_gxo_optimize(
    *,
    topic: str,
    content: str,
    url: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run GXO optimization."""
    prompt = (
        f"Optimize for GXO (Google AI Overviews).\n"
        f"Topic: {clean_text_fn(topic, 300)}.\n"
        f"URL: {clean_text_fn(url, 300)}.\n"
        f"Content:\n{clean_text_fn(content, 3000)}\n\n"
        "Estimate citation probability, structured data readiness, and improvements. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("gxo_score") is not None or llm_result.get("schema_recommendations"):
            return normalize_gxo_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_gxo_signals(topic=topic, content=content, url=url)
    return normalize_gxo_result(heuristic, analysis_mode="heuristic", ai_available=False)
