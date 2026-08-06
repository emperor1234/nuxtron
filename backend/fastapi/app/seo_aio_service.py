"""
AIO (AI Content Optimization) — production implementation (module 3).

Scores machine-readability and extractability from content signals; uses LLM when
available. No bracket-placeholder templates in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_BRACKET_PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]")
_DEFINITION_RE = re.compile(
    r"\b(is a|are a|refers to|defined as|means that)\b",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^#{1,3}\s+|\n#{1,3}\s+|<h[1-3]\b", re.IGNORECASE | re.MULTILINE)
_LIST_RE = re.compile(r"^\s*[-*•]\s+|\n\s*[-*•]\s+|\n\s*\d+\.\s+", re.MULTILINE)
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+\s+")


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_aio_content_signals(*, topic: str, content: str) -> dict[str, Any]:
    """Deterministic AIO scoring from measurable content structure."""
    body = content.strip()
    topic_clean = topic.strip()
    words = re.findall(r"\b\w+\b", body)
    word_count = len(words)
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(body) if s.strip()]
    avg_sentence_len = (word_count / max(1, len(sentences))) if sentences else word_count
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    longest_para_words = max((len(re.findall(r"\b\w+\b", p)) for p in paragraphs), default=word_count)

    bracket_count = len(_BRACKET_PLACEHOLDER_RE.findall(body))
    has_definition = bool(_DEFINITION_RE.search(body))
    heading_count = len(_HEADING_RE.findall(body))
    list_count = len(_LIST_RE.findall(body))
    topic_hits = body.lower().count(topic_clean.lower()) if topic_clean else 0

    structure = 34
    if heading_count >= 2:
        structure += 18
    if list_count >= 2:
        structure += 12
    if longest_para_words <= 120:
        structure += 10
    elif longest_para_words > 200:
        structure -= 12
    structure = _clamp(structure)

    machine_readability = 36
    if 12 <= avg_sentence_len <= 22:
        machine_readability += 16
    elif avg_sentence_len <= 28:
        machine_readability += 8
    else:
        machine_readability -= 8
    if word_count >= 150:
        machine_readability += 10
    machine_readability -= min(18, bracket_count * 6)
    machine_readability = _clamp(machine_readability)

    entity_clarity = 38
    if topic_hits >= 2:
        entity_clarity += 18
    elif topic_hits == 1:
        entity_clarity += 10
    if has_definition:
        entity_clarity += 14
    entity_clarity = _clamp(entity_clarity)

    extractability = 35
    if list_count >= 1:
        extractability += 12
    if heading_count >= 1:
        extractability += 10
    if has_definition:
        extractability += 12
    if bracket_count > 0:
        extractability -= 10
    extractability = _clamp(extractability)

    semantic_density = _clamp(int((machine_readability + entity_clarity) / 2))
    aio_score = _clamp(int((structure + machine_readability + entity_clarity + extractability) / 4))

    improvements: list[dict[str, Any]] = []
    if structure < 75:
        improvements.append(
            {
                "area": "structure",
                "current_score": structure,
                "target_score": min(90, structure + 15),
                "action": "Split long paragraphs into sections under 120 words with descriptive headings.",
                "before": f"Longest paragraph is ~{longest_para_words} words.",
                "after": "Use H2 sections with one idea per block and bullet lists for steps.",
                "effort": "low",
                "impact": "high",
            }
        )
    if extractability < 78:
        improvements.append(
            {
                "area": "extractability",
                "current_score": extractability,
                "target_score": min(92, extractability + 14),
                "action": "Add a Key Takeaways bullet list immediately after the introduction.",
                "before": "No scannable summary block detected.",
                "after": "Key takeaways: three one-line facts an LLM can quote verbatim.",
                "effort": "low",
                "impact": "high",
            }
        )
    if entity_clarity < 80 and topic_clean:
        improvements.append(
            {
                "area": "entity_clarity",
                "current_score": entity_clarity,
                "target_score": min(92, entity_clarity + 12),
                "action": f"Define {topic_clean} on first mention and repeat once in a summary.",
                "before": "Topic salience is weak in the draft.",
                "after": f"{topic_clean} is defined in the opening sentence with type context.",
                "effort": "medium",
                "impact": "medium",
            }
        )

    definition_line = (
        f"{topic_clean} is a focused subject in this page; state what it is, who it helps, "
        f"and the primary outcome in the first two sentences."
        if topic_clean
        else "Open with what the page covers, who it is for, and the primary outcome in two sentences."
    )
    optimized_paragraphs = [definition_line]
    if word_count >= 60:
        optimized_paragraphs.append(
            "Key takeaways: (1) core definition, (2) primary benefit with a number, "
            "(3) one actionable next step — keep each takeaway under 20 words."
        )

    schema_ops = ["DefinedTerm", "FAQPage"]
    if list_count >= 2:
        schema_ops.append("HowTo")

    return {
        "aio_score": aio_score,
        "machine_readability": machine_readability,
        "entity_clarity": entity_clarity,
        "structure_score": structure,
        "extractability_score": extractability,
        "semantic_density_score": semantic_density,
        "improvements": improvements,
        "ai_readability_breakdown": {
            "gpt4_compatibility": _clamp(aio_score + 2),
            "claude_compatibility": _clamp(aio_score - 1),
            "perplexity_compatibility": _clamp(aio_score + 3),
            "llama_compatibility": _clamp(aio_score - 2),
        },
        "optimized_paragraphs": optimized_paragraphs,
        "schema_opportunities": schema_ops,
        "quick_wins": [
            "Add a Key Takeaways block at the top of the page.",
            "Keep paragraphs under 120 words with one idea each.",
            "Add JSON-LD DefinedTerm or FAQPage where appropriate.",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "word_count": word_count,
            "avg_sentence_length": round(avg_sentence_len, 1),
            "longest_paragraph_words": longest_para_words,
            "heading_count": heading_count,
            "list_count": list_count,
            "bracket_placeholders": bracket_count,
            "topic_mentions": topic_hits,
        },
    }


def _strip_bracket_text(value: str) -> str | None:
    if not isinstance(value, str) or _BRACKET_PLACEHOLDER_RE.search(value):
        return None
    return value


def normalize_aio_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for key in (
        "aio_score",
        "machine_readability",
        "entity_clarity",
        "structure_score",
        "extractability_score",
        "semantic_density_score",
    ):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50

    breakdown = out.get("ai_readability_breakdown")
    if isinstance(breakdown, dict):
        cleaned: dict[str, int] = {}
        for k, v in breakdown.items():
            try:
                cleaned[str(k)] = _clamp(int(float(v)))
            except (TypeError, ValueError):
                cleaned[str(k)] = int(out["aio_score"])
        out["ai_readability_breakdown"] = cleaned
    else:
        base = int(out["aio_score"])
        out["ai_readability_breakdown"] = {
            "gpt4_compatibility": _clamp(base + 2),
            "claude_compatibility": _clamp(base - 1),
            "perplexity_compatibility": _clamp(base + 3),
            "llama_compatibility": _clamp(base - 2),
        }

    improvements = out.get("improvements")
    if isinstance(improvements, list):
        cleaned_improvements: list[dict[str, Any]] = []
        for item in improvements:
            if not isinstance(item, dict):
                continue
            before = _strip_bracket_text(str(item.get("before", "")))
            after = _strip_bracket_text(str(item.get("after", "")))
            if before is None and after is None and _BRACKET_PLACEHOLDER_RE.search(str(item.get("action", ""))):
                continue
            row = dict(item)
            if before is not None:
                row["before"] = before
            elif "before" in row and _BRACKET_PLACEHOLDER_RE.search(str(row["before"])):
                row.pop("before", None)
            if after is not None:
                row["after"] = after
            elif "after" in row and _BRACKET_PLACEHOLDER_RE.search(str(row["after"])):
                row.pop("after", None)
            cleaned_improvements.append(row)
        out["improvements"] = cleaned_improvements

    passages = out.get("optimized_paragraphs")
    if isinstance(passages, list):
        out["optimized_paragraphs"] = [
            p for p in passages if isinstance(p, str) and not _BRACKET_PLACEHOLDER_RE.search(p)
        ]

    if not isinstance(out.get("schema_opportunities"), list):
        out["schema_opportunities"] = ["DefinedTerm", "FAQPage"]
    if not isinstance(out.get("quick_wins"), list):
        out["quick_wins"] = []

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_aio_score(
    *,
    topic: str,
    content: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Score content for AIO; LLM first, heuristic fallback."""
    prompt = (
        f"Score this content for AIO (AI Content Optimization).\n"
        f"Topic: {clean_text_fn(topic, 300)}.\n"
        f"Content:\n{clean_text_fn(content, 3000)}\n\n"
        "Score: machine_readability, entity_clarity, structure, extractability (all 0-100). "
        "Provide specific improvement actions with before/after examples. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("aio_score") is not None or llm_result.get("machine_readability") is not None:
            return normalize_aio_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_aio_content_signals(topic=topic, content=content)
    return normalize_aio_result(heuristic, analysis_mode="heuristic", ai_available=False)
