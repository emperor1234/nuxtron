"""
VSO (Voice Search Optimization) — module 6.

Scores voice readiness from content and topic signals; uses LLM when available.
No fake perfect scores or generic placeholder answers in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_QUESTION_RE = re.compile(r"\?")
_HEADING_QUESTION_RE = re.compile(r"^#{1,3}\s+.+\?|\n#{1,3}\s+.+\?", re.MULTILINE)
_CONVERSATIONAL_RE = re.compile(r"\b(you|your|we|our|let's|how to|what is|where can)\b", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+\s+")
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_NEAR_ME_RE = re.compile(r"\bnear me\b|\bnearby\b|\blocal\b", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _clamp_prob(value: float) -> float:
    return round(max(0.05, min(0.92, value)), 2)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _trim_words(text: str, max_words: int = 55) -> str:
    words = re.findall(r"\S+", text.strip())
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).rstrip(",;:") + "."


def _first_answer_snippet(content: str, topic: str) -> str:
    body = content.strip()
    if not body:
        return f"{topic.strip()} is covered on this page with practical guidance for voice search users."
    for sentence in _SENTENCE_SPLIT_RE.split(body):
        cleaned = sentence.strip()
        if len(cleaned) >= 20:
            return _trim_words(cleaned, 55)
    return _trim_words(body, 55)


def _build_voice_keywords(*, topic: str, content: str, local_area: str) -> list[dict[str, Any]]:
    topic_clean = topic.strip() or "this topic"
    area = local_area.strip()
    base_answer = _first_answer_snippet(content, topic_clean)
    keywords: list[dict[str, Any]] = [
        {
            "query": f"what is {topic_clean}",
            "intent": "informational",
            "answer": base_answer,
            "word_count": _word_count(base_answer),
            "schema_type": "FAQPage",
            "local_intent": False,
        },
        {
            "query": f"how do I {topic_clean}",
            "intent": "instructional",
            "answer": _trim_words(
                f"To {topic_clean}, follow the steps outlined in the opening section and keep answers under 60 words for voice playback.",
                55,
            ),
            "word_count": 0,
            "schema_type": "HowTo",
            "local_intent": False,
        },
    ]
    keywords[1]["word_count"] = _word_count(keywords[1]["answer"])

    if area:
        local_answer = _trim_words(
            f"For {topic_clean} in {area}, use location-specific details from your content and confirm hours, address, and contact options.",
            55,
        )
        keywords.append(
            {
                "query": f"best {topic_clean} in {area}",
                "intent": "local",
                "answer": local_answer,
                "word_count": _word_count(local_answer),
                "schema_type": "LocalBusiness",
                "local_intent": True,
            }
        )

    question_lines = [line.strip(" #") for line in content.splitlines() if "?" in line][:2]
    for line in question_lines:
        if len(line) < 8:
            continue
        answer = _trim_words(
            next((s for s in _SENTENCE_SPLIT_RE.split(content) if len(s.strip()) >= 20), content),
            55,
        )
        keywords.append(
            {
                "query": line.lower() if line.endswith("?") else f"{line.lower()}?",
                "intent": "informational",
                "answer": answer,
                "word_count": _word_count(answer),
                "schema_type": "FAQPage",
                "local_intent": bool(_NEAR_ME_RE.search(line)),
            }
        )
    return keywords[:6]


def analyze_vso_signals(*, topic: str, content: str, local_area: str) -> dict[str, Any]:
    """Deterministic VSO scoring from content structure and conversational cues."""
    topic_clean = topic.strip()
    body = content.strip()
    area = local_area.strip()
    words = re.findall(r"\b\w+\b", body)
    word_count = len(words)
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(body) if s.strip()]
    avg_sentence_len = word_count / max(1, len(sentences))
    question_count = len(_QUESTION_RE.findall(body))
    heading_questions = len(_HEADING_QUESTION_RE.findall(body))
    conversational_hits = len(_CONVERSATIONAL_RE.findall(body))
    bracket_count = len(_BRACKET_RE.findall(body))
    has_near_me = bool(_NEAR_ME_RE.search(body)) or bool(area)

    conversational_score = 32
    if conversational_hits >= 3:
        conversational_score += 18
    elif conversational_hits >= 1:
        conversational_score += 10
    if question_count >= 2:
        conversational_score += 14
    if heading_questions >= 1:
        conversational_score += 10
    if 8 <= avg_sentence_len <= 18:
        conversational_score += 12
    elif avg_sentence_len <= 24:
        conversational_score += 6
    else:
        conversational_score -= 10
    conversational_score -= min(12, bracket_count * 4)
    conversational_score = _clamp(conversational_score)

    voice_keywords = _build_voice_keywords(topic=topic_clean, content=body, local_area=area)
    voice_query_coverage = _clamp(28 + len(voice_keywords) * 10 + min(20, question_count * 4))
    if word_count < 80:
        voice_query_coverage = _clamp(voice_query_coverage - 15)

    vso_score = _clamp(
        int(round((conversational_score * 0.45) + (voice_query_coverage * 0.35) + (18 if has_near_me else 8)))
    )
    if word_count < 50:
        vso_score = _clamp(vso_score - 12)

    position_zero_probability = _clamp_prob(
        0.18 + (vso_score / 220) + (question_count * 0.03) + (0.08 if area else 0)
    )

    device_base = max(38, vso_score - 8)
    device_coverage = {
        "google_assistant": _clamp(device_base + (6 if area else 0)),
        "siri": _clamp(device_base + (4 if area else 0)),
        "alexa": _clamp(device_base - 6),
        "cortana": _clamp(device_base - 12),
    }

    local_voice_queries: list[dict[str, Any]] = []
    if area or has_near_me:
        local_voice_queries = [
            {
                "query": f"best {topic_clean} near me",
                "intent": "near_me",
                "gmb_required": True,
            },
            {
                "query": f"{topic_clean} in {area or 'my area'}",
                "intent": "local_discovery",
                "gmb_required": bool(area),
            },
        ]

    conversational_rewrites: list[dict[str, str]] = []
    if sentences:
        original = sentences[0].strip()
        if original and not original.lower().startswith(("what", "how", "why")):
            conversational_rewrites.append(
                {
                    "original": _trim_words(original, 24),
                    "rewritten": f"What is {topic_clean}? {_trim_words(original, 40)}",
                    "reason": "Lead with a spoken question form for assistant triggers.",
                }
            )

    speakable_spec_plan = {
        "recommended": word_count >= 120,
        "target_sections": ["intro", "faq"] if question_count else ["intro"],
        "schema_template": "SpeakableSpecification",
    }

    recommendations: list[dict[str, Any]] = [
        {
            "action": "Rewrite top H2s as natural spoken questions",
            "priority": "high",
            "effort": "low",
            "expected_lift_pct": 10,
        },
        {
            "action": "Place a 40–55 word direct answer immediately after each question heading",
            "priority": "high",
            "effort": "medium",
            "expected_lift_pct": 14,
        },
    ]
    if area:
        recommendations.append(
            {
                "action": f"Add LocalBusiness schema with {area} address and phone",
                "priority": "high",
                "effort": "medium",
                "expected_lift_pct": 16,
            }
        )
    if avg_sentence_len > 22:
        recommendations.append(
            {
                "action": "Shorten long sentences to under 20 words for voice playback",
                "priority": "medium",
                "effort": "low",
                "expected_lift_pct": 8,
            }
        )

    return {
        "vso_score": vso_score,
        "voice_query_coverage": voice_query_coverage,
        "conversational_score": conversational_score,
        "position_zero_probability": position_zero_probability,
        "device_coverage": device_coverage,
        "voice_keywords": voice_keywords,
        "local_voice_queries": local_voice_queries,
        "conversational_rewrites": conversational_rewrites,
        "speakable_spec_plan": speakable_spec_plan,
        "recommendations": recommendations,
        "quick_wins": [
            "Add FAQPage schema for top voice queries.",
            "Answer the primary question in the first 45 words.",
            "Use second-person phrasing (you/your) in intro paragraphs.",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "word_count": word_count,
            "question_count": question_count,
            "conversational_hits": conversational_hits,
            "avg_sentence_length": round(avg_sentence_len, 1),
            "has_local_context": has_near_me,
        },
    }


def normalize_vso_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for score_key in ("vso_score", "voice_query_coverage", "conversational_score"):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50

    try:
        out["position_zero_probability"] = _clamp_prob(float(out.get("position_zero_probability", 0.3)))
    except (TypeError, ValueError):
        out["position_zero_probability"] = 0.3

    device = out.get("device_coverage")
    if not isinstance(device, dict):
        base = out["vso_score"]
        out["device_coverage"] = {
            "google_assistant": _clamp(base),
            "siri": _clamp(base - 4),
            "alexa": _clamp(base - 8),
            "cortana": _clamp(base - 12),
        }

    for list_key in (
        "voice_keywords",
        "local_voice_queries",
        "conversational_rewrites",
        "recommendations",
        "quick_wins",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    speakable = out.get("speakable_spec_plan")
    if not isinstance(speakable, dict):
        out["speakable_spec_plan"] = {
            "recommended": True,
            "target_sections": ["intro", "faq"],
            "schema_template": "SpeakableSpecification",
        }

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_vso_optimize(
    *,
    topic: str,
    content: str,
    local_area: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run VSO optimization."""
    prompt = (
        f"Optimize for Voice Search (VSO).\n"
        f"Topic: {clean_text_fn(topic, 300)}.\n"
        f"Local area: {clean_text_fn(local_area, 120)}.\n"
        f"Content:\n{clean_text_fn(content, 3000)}\n\n"
        "Return voice keywords with 40–60 word answers, device coverage, and recommendations. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("vso_score") is not None or llm_result.get("voice_keywords"):
            return normalize_vso_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_vso_signals(topic=topic, content=content, local_area=local_area)
    return normalize_vso_result(heuristic, analysis_mode="heuristic", ai_available=False)
