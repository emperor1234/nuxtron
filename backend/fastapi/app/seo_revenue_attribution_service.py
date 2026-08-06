"""Revenue Attribution Intelligence — phase-c module 1."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

_CHANNEL_WEIGHTS = {
    "organic_search": 1.0,
    "ai_referrals": 0.92,
    "email": 0.78,
    "social": 0.72,
    "paid_search": 0.85,
    "direct": 0.65,
}


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_revenue_attribution_signals(
    *,
    domain: str,
    channels: list[str],
    conversion_events: list[str],
    revenue_window_days: int,
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    ch = [c.strip() for c in channels if c.strip()] or ["organic_search", "ai_referrals", "email", "social"]
    events = [e.strip() for e in conversion_events if e.strip()] or ["demo_request", "trial_signup", "checkout"]
    window = max(1, min(365, revenue_window_days))
    notes_text = notes.strip()

    parsed = urlparse(site if "://" in site else f"https://{site}") if site else None
    https_ok = bool(parsed and parsed.scheme == "https")

    attribution_confidence_score = 36
    attribution_confidence_score += min(16, len(ch) * 3)
    attribution_confidence_score += min(14, len(events) * 3)
    attribution_confidence_score += min(10, window // 10)
    attribution_confidence_score += 8 if https_ok else 0
    attribution_confidence_score += 6 if "utm" in notes_text.lower() or "attribution" in notes_text.lower() else 0
    attribution_confidence_score = _clamp(attribution_confidence_score)

    revenue_influenced_pct = _clamp(min(72, 24 + len(ch) * 6 + len(events) * 4))

    channel_attribution: list[dict[str, Any]] = []
    for idx, channel in enumerate(ch[:6]):
        weight = _CHANNEL_WEIGHTS.get(channel.lower().replace(" ", "_"), 0.7 - idx * 0.05)
        base = int(48000 * weight)
        channel_attribution.append(
            {
                "channel": channel,
                "pipeline_value": base + window * 120,
                "won_revenue": int(base * 0.32),
                "assisted_revenue": int(base * 0.18),
                "confidence": "high" if idx == 0 and len(events) >= 2 else "medium" if idx < 3 else "low",
            }
        )

    funnel_leakage = [
        {
            "stage": "session_to_lead",
            "drop_off_pct": _clamp(38 - len(events) * 2),
            "primary_cause": "Weak offer-message alignment on informational entry pages",
            "fix": "Add intent-specific CTA variants with channel-aware landing paths",
        },
        {
            "stage": "lead_to_opportunity",
            "drop_off_pct": _clamp(26 - len(ch)),
            "primary_cause": "Missing nurture paths for AI referral and social cohorts",
            "fix": "Create segment-specific nurture workflows tied to conversion events",
        },
    ]

    return {
        "attribution_confidence_score": attribution_confidence_score,
        "revenue_influenced_pct": revenue_influenced_pct,
        "channel_attribution": channel_attribution,
        "funnel_leakage": funnel_leakage,
        "priority_actions": [
            "Unify first-touch and assisted-touch events in one attribution model",
            f"Tag top conversion paths for: {', '.join(events[:3])}",
            "Run weekly QA on missing UTM/source fields across channels",
        ],
        "measurement_plan": [
            "Weekly channel influence review",
            f"Monthly cohort recalibration over {window}-day window",
            "Quarterly attribution model audit",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_revenue_attribution_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for key in ("attribution_confidence_score", "revenue_influenced_pct"):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50
    for list_key in ("channel_attribution", "funnel_leakage", "priority_actions", "measurement_plan"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_revenue_attribution(
    *,
    domain: str,
    channels: list[str],
    conversion_events: list[str],
    revenue_window_days: int,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    ch = channels[:8] if channels else ["organic_search", "ai_referrals", "email", "social"]
    events = conversion_events[:8] if conversion_events else ["demo_request", "trial_signup", "checkout"]
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Channels: {ch}. "
        f"Conversion events: {events}. Revenue window: {revenue_window_days} days. "
        f"Notes: {clean_text_fn(notes, 500)}. "
        "Generate attribution intelligence with channel influence, leakage points, and a measurable action plan."
    )
    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("attribution_confidence_score") is not None or llm_result.get("channel_attribution"):
            return normalize_revenue_attribution_result(llm_result, analysis_mode="llm", ai_available=True)
    heuristic = analyze_revenue_attribution_signals(
        domain=domain, channels=channels, conversion_events=conversion_events,
        revenue_window_days=revenue_window_days, notes=notes,
    )
    return normalize_revenue_attribution_result(heuristic, analysis_mode="heuristic", ai_available=False)
