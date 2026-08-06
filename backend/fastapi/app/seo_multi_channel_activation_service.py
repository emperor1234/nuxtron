"""Multi-Channel Activation Loop — phase-c module 4."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_multi_channel_activation_signals(
    *,
    campaign_name: str,
    primary_offer: str,
    channels: list[str],
    audience_segments: list[str],
    notes: str,
) -> dict[str, Any]:
    campaign = campaign_name.strip()
    offer = primary_offer.strip() or "core_offer"
    ch = [c.strip() for c in channels if c.strip()] or ["search", "social", "email", "community"]
    segments = [s.strip() for s in audience_segments if s.strip()] or ["new_visitors", "returning_users"]
    notes_text = notes.strip()
    campaign_words = len(re.findall(r"\b\w+\b", campaign))

    activation_readiness_score = 38
    activation_readiness_score += min(16, campaign_words * 2)
    activation_readiness_score += min(16, len(ch) * 3)
    activation_readiness_score += min(12, len(segments) * 3)
    activation_readiness_score += 8 if offer and offer != "core_offer" else 0
    activation_readiness_score += 4 if "message" in notes_text.lower() else 0
    activation_readiness_score = _clamp(activation_readiness_score)

    message_consistency_score = _clamp(activation_readiness_score - 6 + (4 if offer else 0))

    channel_plan = []
    windows = ["week_1", "week_1", "week_2", "week_3"]
    for idx, channel in enumerate(ch[:6]):
        channel_plan.append(
            {
                "channel": channel,
                "objective": f"Activate {offer} on {channel}",
                "primary_asset": "intent landing pages" if channel == "search" else f"{channel} creative pack",
                "launch_window": windows[idx % len(windows)],
                "kpi": "qualified_sessions" if channel == "search" else "assisted_clicks",
            }
        )

    audience_mapping = [
        {"segment": seg, "channel": ch[idx % len(ch)], "offer": offer}
        for idx, seg in enumerate(segments[:6])
    ]

    return {
        "activation_readiness_score": activation_readiness_score,
        "message_consistency_score": message_consistency_score,
        "channel_plan": channel_plan,
        "audience_mapping": audience_mapping,
        "activation_loop": ["plan", "launch", "measure", "optimize"],
        "distribution_risks": [
            "Creative-message mismatch between search and social",
            "Lifecycle lag on reactivation cohorts",
        ],
        "priority_actions": [
            "Standardize channel briefs with one source-of-truth messaging",
            "Publish weekly loop scorecard and iteration backlog",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_multi_channel_activation_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for key in ("activation_readiness_score", "message_consistency_score"):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50
    for list_key in ("channel_plan", "audience_mapping", "activation_loop", "distribution_risks", "priority_actions"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_multi_channel_activation(
    *,
    campaign_name: str,
    primary_offer: str,
    channels: list[str],
    audience_segments: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    ch = channels[:8] if channels else ["search", "social", "email", "community"]
    segments = audience_segments[:8] if audience_segments else ["new_visitors", "returning_users"]
    prompt = (
        f"Campaign name: {clean_text_fn(campaign_name, 300)}. Primary offer: {clean_text_fn(primary_offer, 300)}. "
        f"Channels: {ch}. Audience segments: {segments}. Notes: {clean_text_fn(notes, 500)}. "
        "Return activation plan with channel sequencing, loop metrics, and distribution risk controls."
    )
    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("activation_readiness_score") is not None or llm_result.get("channel_plan"):
            return normalize_multi_channel_activation_result(llm_result, analysis_mode="llm", ai_available=True)
    heuristic = analyze_multi_channel_activation_signals(
        campaign_name=campaign_name, primary_offer=primary_offer, channels=channels,
        audience_segments=audience_segments, notes=notes,
    )
    return normalize_multi_channel_activation_result(heuristic, analysis_mode="heuristic", ai_available=False)
