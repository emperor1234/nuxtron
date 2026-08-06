"""
CXAO (Conversational Experience Answer Optimization) — phase-b module 1.

Scores assistant conversation quality from intent, context, and instrumentation signals.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_VAGUE_RE = re.compile(r"\b(maybe|might|unclear|not sure|i think|possibly)\b", re.IGNORECASE)
_ACTION_RE = re.compile(
    r"\b(click|sign up|next step|cta|book a demo|get started|schedule|try|download)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(r"\?")
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_STRUCTURE_RE = re.compile(r"\b(summary|step|because|therefore|first|second|finally)\b", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_cxao_signals(
    *,
    assistant_surface: str,
    primary_intent: str,
    conversation_context: str,
    success_criteria: list[str],
    ai_model: str,
    rag_enabled: bool,
    chat_ui_framework: str,
    posthog_enabled: bool,
    posthog_events: list[str],
) -> dict[str, Any]:
    """Deterministic CXAO scoring from conversational and stack signals."""
    surface = assistant_surface.strip() or "chat_assistant"
    intent = primary_intent.strip()
    context = conversation_context.strip()
    criteria = [c.strip() for c in success_criteria if c.strip()]
    events = [e.strip() for e in posthog_events if e.strip()]
    model = ai_model.strip()

    context_words = len(re.findall(r"\b\w+\b", context))
    intent_words = len(re.findall(r"\b\w+\b", intent))
    vague_hits = len(_VAGUE_RE.findall(context + " " + intent))
    action_hits = len(_ACTION_RE.findall(context + " " + intent))
    question_count = len(_QUESTION_RE.findall(context))
    bracket_count = len(_BRACKET_RE.findall(context))
    structure_hits = len(_STRUCTURE_RE.findall(context))

    intent_context_overlap = 0
    intent_tokens = {t.lower() for t in re.findall(r"\b\w{4,}\b", intent)}
    context_tokens = {t.lower() for t in re.findall(r"\b\w{4,}\b", context)}
    if intent_tokens:
        intent_context_overlap = len(intent_tokens & context_tokens)

    conversation_clarity_score = 36
    conversation_clarity_score += min(18, intent_words * 2)
    conversation_clarity_score += min(16, structure_hits * 4)
    conversation_clarity_score += min(10, question_count * 3)
    conversation_clarity_score -= min(16, vague_hits * 5)
    conversation_clarity_score -= min(12, bracket_count * 4)
    conversation_clarity_score = _clamp(conversation_clarity_score)

    answer_relevance_score = 34
    answer_relevance_score += min(22, intent_context_overlap * 4)
    answer_relevance_score += min(14, context_words // 25)
    if "user" in context.lower() and "assistant" in context.lower():
        answer_relevance_score += 8
    answer_relevance_score -= min(10, vague_hits * 3)
    answer_relevance_score = _clamp(answer_relevance_score)

    actionability_score = 32
    actionability_score += min(18, action_hits * 5)
    actionability_score += min(12, len(criteria) * 4)
    actionability_score += 8 if any("cta" in c.lower() or "completion" in c.lower() for c in criteria) else 0
    actionability_score += 6 if posthog_enabled and any("cta" in e.lower() for e in events) else 0
    actionability_score -= min(8, bracket_count * 3)
    actionability_score = _clamp(actionability_score)

    experience_optimization_score = _clamp(
        int(round((conversation_clarity_score + answer_relevance_score + actionability_score) / 3))
    )
    if rag_enabled:
        experience_optimization_score = _clamp(experience_optimization_score + 4)
    if posthog_enabled and len(events) >= 2:
        experience_optimization_score = _clamp(experience_optimization_score + 4)

    friction_points: list[dict[str, Any]] = []
    if vague_hits >= 2:
        friction_points.append(
            {
                "issue": "Responses may sound uncertain or non-committal",
                "impact": "medium",
                "fix": "Replace hedging language with evidence-backed statements and explicit assumptions",
            }
        )
    if action_hits < 1:
        friction_points.append(
            {
                "issue": "No clear next action in the conversation scenario",
                "impact": "high",
                "fix": "End each answer with one prioritized CTA aligned to primary intent",
            }
        )
    if not rag_enabled:
        friction_points.append(
            {
                "issue": "RAG retrieval disabled for grounded answers",
                "impact": "medium",
                "fix": "Enable retrieval over product docs and FAQs before generation",
            }
        )
    if posthog_enabled and len(events) < 2:
        friction_points.append(
            {
                "issue": "Insufficient PostHog instrumentation for funnel diagnosis",
                "impact": "low",
                "fix": "Track chat_started, chat_completed, and cta_clicked at minimum",
            }
        )

    optimization_playbook = [
        "Use intent-first scaffolding: direct summary → rationale → numbered actions → CTA.",
        f"Tune prompts for surface `{surface}` with explicit success criteria from operator inputs.",
    ]
    if rag_enabled:
        optimization_playbook.append("Ground answers with retrieved snippets and cite source titles inline.")
    else:
        optimization_playbook.append("Enable RAG over canonical docs to reduce hallucinated product claims.")
    if posthog_enabled:
        optimization_playbook.append("Correlate friction points with PostHog drop-off between chat_started and cta_clicked.")
    if criteria:
        optimization_playbook.append(f"Measure weekly progress on: {', '.join(criteria[:3])}.")

    response_template = {
        "opening": f"Here is the fastest path to: {intent[:120]}",
        "structure": ["summary", "evidence", "step-by-step actions", "assumptions", "next checkpoint"],
        "cta": "Would you like this tailored to your segment and deployment constraints?",
    }

    return {
        "experience_optimization_score": experience_optimization_score,
        "conversation_clarity_score": conversation_clarity_score,
        "answer_relevance_score": answer_relevance_score,
        "actionability_score": actionability_score,
        "friction_points": friction_points[:6],
        "optimization_playbook": optimization_playbook[:8],
        "response_template": response_template,
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "context_word_count": context_words,
            "success_criteria_count": len(criteria),
            "posthog_event_count": len(events),
            "rag_enabled": rag_enabled,
            "ai_model": model or "unspecified",
            "chat_ui_framework": chat_ui_framework.strip() or "nextjs",
        },
    }


def normalize_cxao_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for score_key in (
        "experience_optimization_score",
        "conversation_clarity_score",
        "answer_relevance_score",
        "actionability_score",
    ):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50

    if not isinstance(out.get("friction_points"), list):
        out["friction_points"] = []
    if not isinstance(out.get("optimization_playbook"), list):
        out["optimization_playbook"] = []
    if not isinstance(out.get("response_template"), dict):
        out["response_template"] = {
            "opening": "Here is the quickest path to your goal:",
            "structure": ["summary", "evidence", "actions"],
            "cta": "Want a version tailored to your audience?",
        }

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_cxao_experience(
    *,
    assistant_surface: str,
    primary_intent: str,
    conversation_context: str,
    success_criteria: list[str],
    ai_model: str,
    rag_enabled: bool,
    chat_ui_framework: str,
    posthog_enabled: bool,
    posthog_events: list[str],
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run CXAO analysis."""
    success = success_criteria[:8] if success_criteria else [
        "higher answer clarity",
        "faster task completion",
        "increased CTA follow-through",
    ]
    prompt = (
        f"Assistant surface: {clean_text_fn(assistant_surface, 120)}. "
        f"Primary intent: {clean_text_fn(primary_intent, 300)}. "
        f"Conversation context: {clean_text_fn(conversation_context, 3000)}. "
        f"Success criteria: {success}. "
        f"AI model: {clean_text_fn(ai_model, 100)}. RAG enabled: {rag_enabled}. "
        f"Chat UI framework: {clean_text_fn(chat_ui_framework, 100)}. "
        f"PostHog enabled: {posthog_enabled}. Events: {posthog_events[:12]}. "
        "Return experience optimization scores, key friction points, and a practical playbook. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("experience_optimization_score") is not None or llm_result.get("friction_points"):
            return normalize_cxao_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_cxao_signals(
        assistant_surface=assistant_surface,
        primary_intent=primary_intent,
        conversation_context=conversation_context,
        success_criteria=success_criteria,
        ai_model=ai_model,
        rag_enabled=rag_enabled,
        chat_ui_framework=chat_ui_framework,
        posthog_enabled=posthog_enabled,
        posthog_events=posthog_events,
    )
    return normalize_cxao_result(heuristic, analysis_mode="heuristic", ai_available=False)
