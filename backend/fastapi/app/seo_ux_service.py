"""UX & Conversion Optimizer — phase-f module 2."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_ux_conversion_signals(
    *,
    url: str,
    page_type: str,
    traffic_source: str,
    notes: str,
) -> dict[str, Any]:
    page = url.strip()
    ptype = page_type.strip() or "landing"
    source = traffic_source.strip() or "organic"
    notes_text = notes.strip()

    ux_score = 38
    ux_score += 10 if ptype in {"landing", "pricing", "product"} else 6
    ux_score += 8 if source == "organic" else 4
    ux_score += min(10, len(notes_text) // 20)
    ux_score = _clamp(ux_score)

    conversion_score = _clamp(ux_score - 5 + (6 if ptype in {"landing", "pricing"} else 0))

    friction_points = [
        {
            "location": "hero section",
            "type": "cta_clarity",
            "impact": "high" if ptype == "landing" else "medium",
            "fix": "Use action-specific CTA copy aligned to search intent",
        }
    ]
    if ptype == "pricing":
        friction_points.append(
            {
                "location": "pricing table",
                "type": "trust_signal",
                "impact": "medium",
                "fix": "Add customer logos and guarantee badge near plans",
            }
        )

    return {
        "ux_score": ux_score,
        "conversion_score": conversion_score,
        "above_fold": {"cta_visible": True, "load_time_estimate": 3.1, "hero_clarity_score": _clamp(ux_score - 8)},
        "friction_points": friction_points,
        "trust_signals": {
            "present": ["SSL certificate"] if page.startswith("https") else [],
            "missing": ["money-back guarantee badge", "customer logos", "security certifications"],
        },
        "heatmap_insights": [
            "Navigation receives more clicks than primary CTA on mobile",
            "Users scroll past pricing without pausing on comparison rows",
        ],
        "ab_test_ideas": [
            {
                "element": "hero_cta",
                "variant_a": "Learn More",
                "variant_b": "Start Free Trial",
                "hypothesis": "Specific trial CTA improves qualified conversions from organic traffic",
            }
        ],
        "quick_wins": ["Clarify hero CTA", "Add trust badges above the fold", "Reduce mobile LCP on hero media"],
        "recommended_tools": ["hotjar", "microsoft_clarity", "google_optimize"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_ux_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for key in ("ux_score", "conversion_score"):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50
    for list_key in ("friction_points", "heatmap_insights", "ab_test_ideas", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("trust_signals"), dict):
        out["trust_signals"] = {"present": [], "missing": []}
    if not isinstance(out.get("above_fold"), dict):
        out["above_fold"] = {"cta_visible": True, "load_time_estimate": 3.0, "hero_clarity_score": out["ux_score"]}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def audit_ux_conversion(
    *,
    url: str,
    page_type: str,
    traffic_source: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"URL: {clean_text_fn(url, 500)}. Page type: {clean_text_fn(page_type, 100)}. "
        f"Traffic source: {clean_text_fn(traffic_source, 100)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("ux_score") is not None or llm.get("friction_points"):
            return normalize_ux_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_ux_conversion_signals(url=url, page_type=page_type, traffic_source=traffic_source, notes=notes)
    return normalize_ux_result(heur, analysis_mode="heuristic", ai_available=False)
