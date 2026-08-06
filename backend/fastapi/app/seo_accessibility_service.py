"""Accessibility Optimizer — phase-f module 5."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_accessibility_signals(*, url: str, standard: str, notes: str) -> dict[str, Any]:
    page = url.strip()
    std = standard.strip() or "WCAG2.1AA"
    notes_text = notes.strip()
    https_ok = page.startswith("https")

    accessibility_score = 42
    accessibility_score += 8 if https_ok else 0
    accessibility_score += min(10, len(notes_text) // 15)
    accessibility_score += 6 if "AA" in std else 4
    accessibility_score = _clamp(accessibility_score)

    issues = [
        {
            "level": "AA",
            "criterion": "1.1.1",
            "description": "Some images may be missing descriptive alt text",
            "element": "img",
            "fix": "Add meaningful alt attributes to informative images",
            "impact": "serious",
        }
    ]
    if not https_ok:
        issues.append(
            {
                "level": "A",
                "criterion": "best_practice",
                "description": "Page URL is not HTTPS",
                "element": "document",
                "fix": "Serve content over HTTPS",
                "impact": "moderate",
            }
        )

    readability_words = len(re.findall(r"\b\w+\b", notes_text))
    grade = _clamp(8 + readability_words // 30)

    return {
        "accessibility_score": accessibility_score,
        "standard": std,
        "issues": issues,
        "readability": {
            "flesch_kincaid_grade": grade,
            "flesch_reading_ease": _clamp(70 - grade * 2),
            "avg_sentence_words": 18,
            "passive_voice_pct": 12,
        },
        "assistive_tech": {
            "screen_reader_score": _clamp(accessibility_score - 6),
            "keyboard_nav_score": _clamp(accessibility_score - 2),
            "focus_visible": accessibility_score >= 55,
        },
        "quick_wins": ["Add alt text to hero images", "Ensure form inputs have labels", "Fix low-contrast footer links"],
        "recommended_tools": ["axe-core", "lighthouse", "pa11y"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_accessibility_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["accessibility_score"] = _clamp(int(float(out.get("accessibility_score", 50))))
    except (TypeError, ValueError):
        out["accessibility_score"] = 50
    for list_key in ("issues", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("readability"), dict):
        out["readability"] = {"flesch_kincaid_grade": 9, "flesch_reading_ease": 58}
    if not isinstance(out.get("assistive_tech"), dict):
        out["assistive_tech"] = {"screen_reader_score": 50, "keyboard_nav_score": 50, "focus_visible": False}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def audit_accessibility(
    *,
    url: str,
    standard: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Audit URL: {clean_text_fn(url, 500)}. Standard: {clean_text_fn(standard, 30)}. "
        f"Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("accessibility_score") is not None or llm.get("issues"):
            return normalize_accessibility_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_accessibility_signals(url=url, standard=standard, notes=notes)
    return normalize_accessibility_result(heur, analysis_mode="heuristic", ai_available=False)
