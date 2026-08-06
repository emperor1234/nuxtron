"""Advanced Rank Tracking — phase-i module 5."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_rank_tracking_signals(
    *,
    domain: str,
    tracked_keywords: list[str],
    historical_lookback_days: int,
    include_competitor_tracking: bool,
    competitor_domains: list[str],
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    keywords = [k.strip() for k in tracked_keywords if k.strip()] or ["primary keyword"]
    lookback = max(7, min(365, historical_lookback_days))
    competitors = [c.strip() for c in competitor_domains if c.strip()]
    notes_text = notes.strip()

    tracking_score = 44
    tracking_score += min(18, len(keywords) * 3)
    tracking_score += min(8, lookback // 30)
    tracking_score += 6 if include_competitor_tracking and competitors else 0
    tracking_score += min(6, len(notes_text) // 35)
    tracking_score = _clamp(tracking_score)

    ranking_history = [
        {
            "keyword": kw,
            "current_position": max(3, 18 - tracking_score // 5 - i),
            "trend": "up" if tracking_score >= 55 else "flat",
            "position_change": 2 if tracking_score >= 55 else 0,
            "30d_trend": "gradual improvement" if tracking_score >= 55 else "stable",
        }
        for i, kw in enumerate(keywords[:5])
    ]

    volatility_index = round(max(0.08, 0.45 - tracking_score / 200), 2)
    return {
        "tracking_score": tracking_score,
        "volatile_keywords": keywords[:2] if volatility_index >= 0.35 else [],
        "ranking_history": ranking_history,
        "volatility_index": volatility_index,
        "key_movements": [
            {
                "keyword": keywords[0],
                "movement": f"Movement detected over {lookback}d window for {site or 'domain'}",
                "likely_cause": "Content freshness and internal linking updates",
            }
        ],
        "competitor_movements": [
            {"competitor": c, "keyword": keywords[0], "change": -1}
            for c in competitors[:3]
        ] if include_competitor_tracking else [],
        "trend_forecast": {
            "direction": "up" if tracking_score >= 58 else "stable",
            "confidence": round(min(0.88, tracking_score / 100), 2),
            "forecast_horizon_days": min(lookback, 30),
            "key_drivers": ["Content freshness", "Technical health"],
        },
        "alert_triggers": ["Position drop >5 for priority keyword"] if volatility_index >= 0.3 else [],
        "next_actions": ["Maintain publish cadence", "Expand tracked keyword set"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_rank_tracking_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["tracking_score"] = _clamp(int(float(out.get("tracking_score", 50))))
    except (TypeError, ValueError):
        out["tracking_score"] = 50
    try:
        out["volatility_index"] = float(out.get("volatility_index", 0.2))
    except (TypeError, ValueError):
        out["volatility_index"] = 0.2
    for list_key in ("volatile_keywords", "ranking_history", "key_movements", "competitor_movements", "alert_triggers", "next_actions"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("trend_forecast"), dict):
        out["trend_forecast"] = {"direction": "stable", "confidence": 0.5, "forecast_horizon_days": 30, "key_drivers": []}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_rank_tracking(
    *,
    domain: str,
    tracked_keywords: list[str],
    historical_lookback_days: int,
    include_competitor_tracking: bool,
    competitor_domains: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
    llm_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    keywords_str = ", ".join(tracked_keywords[:15]) if tracked_keywords else "primary keywords"
    competitors_str = ", ".join(competitor_domains[:5]) if competitor_domains else ""
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Keywords: {clean_text_fn(keywords_str, 300)}. "
        f"Lookback: {historical_lookback_days} days. Competitor tracking: {include_competitor_tracking}. "
        f"Competitors: {clean_text_fn(competitors_str, 300)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm_kwargs: dict[str, Any] = {}
    if llm_timeout_seconds is not None:
        llm_kwargs["timeout_seconds"] = llm_timeout_seconds
    llm = await ollama_json_fn(system_prompt, prompt, **llm_kwargs)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("tracking_score") is not None or llm.get("ranking_history"):
            return normalize_rank_tracking_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_rank_tracking_signals(
        domain=domain,
        tracked_keywords=tracked_keywords,
        historical_lookback_days=historical_lookback_days,
        include_competitor_tracking=include_competitor_tracking,
        competitor_domains=competitor_domains,
        notes=notes,
    )
    return normalize_rank_tracking_result(heur, analysis_mode="heuristic", ai_available=False)
