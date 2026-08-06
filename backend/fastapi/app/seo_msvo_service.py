"""
MSVO (Multi-Surface Visibility Optimization) — module 12.

Scores omni-channel visibility across search, AI, and owned distribution surfaces.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_SURFACES = ["google", "chatgpt", "perplexity", "linkedin"]
_SURFACE_ALIASES = {
    "google": "google_search",
    "google search": "google_search",
    "google_search": "google_search",
    "google ai overview": "google_ai_overview",
    "google_ai_overview": "google_ai_overview",
    "chatgpt": "chatgpt",
    "gpt": "chatgpt",
    "claude": "claude",
    "perplexity": "perplexity",
    "linkedin": "linkedin",
    "youtube": "youtube",
    "x": "x_twitter",
    "twitter": "x_twitter",
    "x_twitter": "x_twitter",
    "email": "email",
    "reddit": "reddit",
    "blog": "blog",
}


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _clamp_rate(value: float) -> float:
    return round(max(0.01, min(0.25, value)), 3)


def _normalize_surface(raw: str) -> str:
    key = raw.strip().lower()
    return _SURFACE_ALIASES.get(key, key.replace(" ", "_"))


def _surface_content_format(surface: str) -> str:
    if surface in {"youtube"}:
        return "video"
    if surface in {"x_twitter", "reddit"}:
        return "thread"
    if surface in {"chatgpt", "claude", "perplexity", "google_ai_overview"}:
        return "snippet"
    if surface == "email":
        return "newsletter"
    return "article"


def analyze_msvo_signals(
    *,
    brand: str,
    topic: str,
    target_surfaces: list[str],
    owned_channels: list[str],
    notes: str,
) -> dict[str, Any]:
    """Deterministic MSVO plan from brand, topic, and channel inputs."""
    brand_clean = brand.strip()
    topic_clean = topic.strip()
    surfaces = [_normalize_surface(s) for s in target_surfaces if s.strip()] or _DEFAULT_SURFACES.copy()
    owned = [_normalize_surface(c) for c in owned_channels if c.strip()]
    notes_text = notes.strip()
    notes_lower = notes_text.lower()

    owned_set = set(owned)
    overlap = [s for s in surfaces if s in owned_set or s.replace("_search", "") in owned_set]

    visibility_score = 34
    visibility_score += min(24, len(surfaces) * 4)
    visibility_score += min(16, len(overlap) * 5)
    visibility_score += min(10, len(notes_text) // 40)
    if brand_clean.lower() in notes_lower:
        visibility_score += 4
    visibility_score = _clamp(visibility_score)

    message_consistency_score = 38
    if brand_clean and topic_clean:
        message_consistency_score += 16
    if len(owned) >= 2:
        message_consistency_score += 14
    if "consistent" in notes_lower or "message" in notes_lower:
        message_consistency_score += 10
    message_consistency_score = _clamp(message_consistency_score)
    message_alignment_score = _clamp(int(round((message_consistency_score + visibility_score) / 2)))

    surface_coverage: list[dict[str, Any]] = []
    for surface in surfaces[:10]:
        has_owned = surface in owned_set or surface.split("_")[0] in owned_set
        presence = 42
        if has_owned:
            presence += 24
        if surface in {"google_search", "google"}:
            presence += 8
        if surface in {"chatgpt", "perplexity", "claude"} and ("ai" in notes_lower or "llm" in notes_lower):
            presence += 10
        presence = _clamp(presence)
        surface_coverage.append(
            {
                "surface": surface,
                "presence_score": presence,
                "audience_reach": 5000 + presence * 120,
                "engagement_rate": _clamp_rate(0.012 + presence / 5000),
                "content_format": _surface_content_format(surface),
                "priority_action": (
                    f"Maintain {brand_clean or 'brand'} messaging on {surface.replace('_', ' ')}"
                    if has_owned
                    else f"Launch first { _surface_content_format(surface)} asset for {surface.replace('_', ' ')}"
                ),
                "effort": "low" if has_owned else "medium",
                "impact": "high" if surface in {"google_search", "chatgpt", "perplexity"} else "medium",
            }
        )

    owned_channel_gaps: list[dict[str, Any]] = []
    for surface in surfaces:
        if surface not in owned_set and surface.split("_")[0] not in owned_set:
            owned_channel_gaps.append(
                {
                    "channel": surface,
                    "gap_type": "no_presence",
                    "fix": f"Create a { _surface_content_format(surface)} activation plan for {surface.replace('_', ' ')}.",
                }
            )
    for channel in owned:
        if channel not in surfaces and channel not in {g["channel"] for g in owned_channel_gaps}:
            owned_channel_gaps.append(
                {
                    "channel": channel,
                    "gap_type": "inconsistent_message",
                    "fix": f"Align {channel} content calendar with target surfaces for '{topic_clean or 'topic'}'.",
                }
            )

    cross_surface_amplification: list[dict[str, Any]] = []
    if "google_search" in surfaces and "linkedin" in surfaces:
        cross_surface_amplification.append(
            {
                "from_surface": "google_search",
                "to_surface": "linkedin",
                "amplification_mechanic": "Repurpose top-performing SEO article into LinkedIn thought-leadership posts",
                "expected_reach_lift_pct": 18,
            }
        )
    if "chatgpt" in surfaces and "blog" in owned_set:
        cross_surface_amplification.append(
            {
                "from_surface": "blog",
                "to_surface": "chatgpt",
                "amplification_mechanic": "Structure blog facts as citable snippets for AI assistants",
                "expected_reach_lift_pct": 14,
            }
        )

    audience_journey_map = [
        {
            "stage": "awareness",
            "primary_surface": surfaces[0] if surfaces else "google_search",
            "content_type": "article",
            "cta": f"Learn how {brand_clean or 'the brand'} approaches {topic_clean or 'the topic'}",
        },
        {
            "stage": "consideration",
            "primary_surface": surfaces[1] if len(surfaces) > 1 else "linkedin",
            "content_type": "comparison",
            "cta": "Download checklist or case study",
        },
        {
            "stage": "conversion",
            "primary_surface": "email" if "email" in surfaces or "email" in owned_set else surfaces[-1],
            "content_type": "demo_or_trial",
            "cta": "Book demo or start trial",
        },
    ]

    distribution_sequence = [
        {
            "step": index + 1,
            "surface": item["surface"],
            "content": f"{brand_clean or 'Brand'} {topic_clean or 'topic'} launch asset",
            "timing": f"week {index + 1}",
            "kpi": "presence_score",
        }
        for index, item in enumerate(surface_coverage[:4])
    ]

    next_actions: list[dict[str, Any]] = [
        {
            "action": f"Publish a canonical {topic_clean or 'topic'} message matrix for all target surfaces",
            "priority": "high",
            "effort": "medium",
            "expected_impact": "Improves cross-surface consistency",
        },
        {
            "action": "Schedule weekly visibility checks on top three surfaces",
            "priority": "medium",
            "effort": "low",
            "expected_impact": "Detects channel drift early",
        },
    ]
    if owned_channel_gaps:
        next_actions.insert(
            0,
            {
                "action": f"Close gap on {owned_channel_gaps[0]['channel']} with one launch asset",
                "priority": "high",
                "effort": "medium",
                "expected_impact": "Expands reachable audience",
            },
        )

    return {
        "visibility_score": visibility_score,
        "surface_coverage": surface_coverage,
        "message_consistency_score": message_consistency_score,
        "message_alignment_score": message_alignment_score,
        "owned_channel_gaps": owned_channel_gaps,
        "cross_surface_amplification": cross_surface_amplification,
        "audience_journey_map": audience_journey_map,
        "distribution_sequence": distribution_sequence,
        "next_actions": next_actions,
        "quick_wins": [
            "Repurpose one SEO article into LinkedIn and email snippets.",
            "Add brand + topic boilerplate for AI assistant citations.",
            "Audit message consistency across owned channels.",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "target_surface_count": len(surfaces),
            "owned_channel_count": len(owned),
            "surface_owned_overlap": len(overlap),
        },
    }


def normalize_msvo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for score_key in ("visibility_score", "message_consistency_score", "message_alignment_score"):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50

    if not isinstance(out.get("surface_coverage"), list):
        out["surface_coverage"] = []

    for list_key in (
        "owned_channel_gaps",
        "cross_surface_amplification",
        "audience_journey_map",
        "distribution_sequence",
        "next_actions",
        "quick_wins",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_msvo_visibility(
    *,
    brand: str,
    topic: str,
    target_surfaces: list[str],
    owned_channels: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run MSVO analysis."""
    prompt = (
        f"Build an MSVO plan for brand: {clean_text_fn(brand, 200)}.\n"
        f"Topic: {clean_text_fn(topic, 300)}.\n"
        f"Target surfaces: {', '.join(target_surfaces[:10])}.\n"
        f"Owned channels: {', '.join(owned_channels[:10])}.\n"
        f"Notes: {clean_text_fn(notes, 500)}.\n"
        "Return surface coverage, channel gaps, and distribution sequence. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("visibility_score") is not None or llm_result.get("surface_coverage"):
            return normalize_msvo_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_msvo_signals(
        brand=brand,
        topic=topic,
        target_surfaces=target_surfaces,
        owned_channels=owned_channels,
        notes=notes,
    )
    return normalize_msvo_result(heuristic, analysis_mode="heuristic", ai_available=False)
