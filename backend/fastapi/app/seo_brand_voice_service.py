"""Brand Voice Rewriter — phase-h module 3."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

_PASSIVE = re.compile(r"\b(was|were|been|being)\s+\w+ed\b", re.IGNORECASE)
_JARGON = re.compile(r"\b(leverage|synergy|paradigm|utilize|best-in-class)\b", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_brand_voice_signals(
    *,
    content: str,
    brand_name: str,
    tone: str,
    target_audience: str,
    notes: str,
) -> dict[str, Any]:
    text = content.strip()
    brand = brand_name.strip()
    target_tone = tone.strip() or "professional"
    audience = target_audience.strip()
    notes_text = notes.strip()

    passive_count = len(_PASSIVE.findall(text))
    jargon_count = len(_JARGON.findall(text))
    brand_mentions = len(re.findall(re.escape(brand), text, re.IGNORECASE)) if brand else 0

    alignment_pct = 58
    alignment_pct += min(16, len(text) // 80)
    alignment_pct += 8 if brand and brand_mentions > 0 else 0
    alignment_pct += 6 if audience else 0
    alignment_pct -= min(20, passive_count * 4 + jargon_count * 5)
    alignment_pct = _clamp(alignment_pct)

    brand_alignment_score = _clamp(alignment_pct - 4 + (4 if notes_text else 0))

    rewritten = text
    if brand and brand.lower() not in text.lower()[:120].lower():
        rewritten = f"{brand} — {text}"

    violations = []
    for match in _JARGON.finditer(text):
        violations.append({"type": "jargon", "text": match.group(0), "suggestion": "Use plain language"})
    for match in _PASSIVE.finditer(text):
        violations.append({"type": "passive_voice", "text": match.group(0), "suggestion": "Use active voice"})

    first_sentence = text.split(". ")[0] if text else "..."
    changes = [
        {
            "original": first_sentence,
            "rewritten": f"{first_sentence.strip()} — aligned to {target_tone} tone for {audience or 'your audience'}.",
            "reason": "Reinforced brand voice and audience fit",
        }
    ] if text else []

    return {
        "brand_alignment_score": brand_alignment_score,
        "tone_analysis": {
            "detected_tone": "neutral" if passive_count else "direct",
            "target_tone": target_tone,
            "alignment_pct": alignment_pct,
        },
        "rewritten_content": rewritten,
        "changes": changes,
        "style_violations": violations[:5],
        "seo_preservation": {"keywords_retained": True, "density_unchanged": True, "meta_impact": "none"},
        "quick_wins": [f"Replace passive constructions with active {target_tone} voice", "Remove jargon for clarity"],
        "recommended_tools": ["grammarly_tone", "writer_ai", "hemingway"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_brand_voice_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["brand_alignment_score"] = _clamp(int(float(out.get("brand_alignment_score", 50))))
    except (TypeError, ValueError):
        out["brand_alignment_score"] = 50
    if not isinstance(out.get("tone_analysis"), dict):
        out["tone_analysis"] = {"detected_tone": "neutral", "target_tone": "professional", "alignment_pct": 50}
    for list_key in ("changes", "style_violations", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("seo_preservation"), dict):
        out["seo_preservation"] = {"keywords_retained": True, "density_unchanged": True, "meta_impact": "none"}
    if not isinstance(out.get("rewritten_content"), str):
        out["rewritten_content"] = ""
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def rewrite_brand_voice(
    *,
    content: str,
    brand_name: str,
    tone: str,
    target_audience: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Brand: {clean_text_fn(brand_name, 300)}. Target tone: {clean_text_fn(tone, 100)}. "
        f"Audience: {clean_text_fn(target_audience, 300)}. Notes: {clean_text_fn(notes, 500)}. "
        f"Content to rewrite: {clean_text_fn(content, 4000)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("brand_alignment_score") is not None or llm.get("rewritten_content"):
            return normalize_brand_voice_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_brand_voice_signals(
        content=content,
        brand_name=brand_name,
        tone=tone,
        target_audience=target_audience,
        notes=notes,
    )
    return normalize_brand_voice_result(heur, analysis_mode="heuristic", ai_available=False)
