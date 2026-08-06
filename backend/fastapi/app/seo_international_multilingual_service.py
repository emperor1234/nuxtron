"""International & Multilingual SEO — phase-d module 4."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_international_multilingual_signals(
    *,
    domain: str,
    locales: list[str],
    current_hreflang_map: str,
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    locs = [l.strip() for l in locales if l.strip()] or ["en-us", "en-gb", "es-es", "de-de"]
    hreflang = current_hreflang_map.strip()
    notes_text = notes.strip()
    hreflang_lines = len([ln for ln in hreflang.splitlines() if ln.strip()])

    readiness_score = 36
    readiness_score += min(18, len(locs) * 3)
    readiness_score += min(14, hreflang_lines * 2)
    readiness_score += 6 if "x-default" in hreflang.lower() else 0
    readiness_score += 4 if notes_text else 0
    readiness_score = _clamp(readiness_score)

    hreflang_coverage_pct = _clamp(min(85, 30 + len(locs) * 8 + hreflang_lines * 2))
    canonical_consistency_pct = _clamp(readiness_score - 5)

    return {
        "readiness_score": readiness_score,
        "hreflang_coverage_pct": hreflang_coverage_pct,
        "canonical_consistency_pct": canonical_consistency_pct,
        "locale_targets": [
            {"locale": locale, "status": "active" if i < 2 else "needs_work", "focus_keyword": f"{site} {locale}"}
            for i, locale in enumerate(locs[:8])
        ],
        "regional_gaps": [
            {"locale": locs[2] if len(locs) > 2 else "es-es", "gap": "Missing localized informational cluster", "severity": "high"},
        ],
        "priority_actions": [
            "Validate reciprocal hreflang and canonical tags across locales",
            "Build locale landing clusters for high-intent regional terms",
            "Monitor Search Console coverage per locale weekly",
        ],
        "recommended_tools": ["search_console", "screaming_frog", "hreflang_checker"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_international_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for key in ("readiness_score", "hreflang_coverage_pct", "canonical_consistency_pct"):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50
    for list_key in ("locale_targets", "regional_gaps", "priority_actions", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_international_multilingual(
    *,
    domain: str,
    locales: list[str],
    current_hreflang_map: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    locs = locales[:10] if locales else ["en-us", "en-gb", "es-es"]
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Locales: {locs}. "
        f"Hreflang map: {clean_text_fn(current_hreflang_map, 3000)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("readiness_score") is not None or llm.get("locale_targets"):
            return normalize_international_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_international_multilingual_signals(domain=domain, locales=locales, current_hreflang_map=current_hreflang_map, notes=notes)
    return normalize_international_result(heur, analysis_mode="heuristic", ai_available=False)
