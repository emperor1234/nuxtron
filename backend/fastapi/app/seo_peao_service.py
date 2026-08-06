"""
PEAO (Predictive Entity & Algorithm Optimization) — module 11.

Forecasts ranking volatility and algorithm risks from domain, keyword, and signal inputs.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_NEGATIVE_RE = re.compile(
    r"\b(drop|dropped|decline|declined|lost|penalty|deindex|error|crawl issue|anomaly|volatil)\b",
    re.IGNORECASE,
)
_POSITIVE_RE = re.compile(
    r"\b(gain|gained|improv|rise|rising|recover|ctr up|traffic up|stable)\b",
    re.IGNORECASE,
)
_UPDATE_RE = re.compile(r"\b(core update|helpful content|spam update|algorithm update|serp change)\b", re.IGNORECASE)
_COMPETITOR_RE = re.compile(r"\b(competitor|rival|outrank)\b", re.IGNORECASE)
_STAT_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?%|\bposition\s+\d+\b", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\[[^\]]+\]")


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _clamp_prob(value: float) -> float:
    return round(max(0.05, min(0.95, value)), 2)


def _volatility_risk(index: float) -> str:
    if index >= 0.62:
        return "high"
    if index >= 0.38:
        return "medium"
    return "low"


def analyze_peao_signals(
    *,
    domain: str,
    primary_keyword: str,
    recent_signals: str,
    forecast_horizon_days: int,
    notes: str,
) -> dict[str, Any]:
    """Deterministic PEAO forecast from operator-provided signals."""
    site = domain.strip()
    keyword = primary_keyword.strip()
    signals = recent_signals.strip()
    horizon = max(7, min(180, forecast_horizon_days))
    notes_text = notes.strip()

    negative_hits = len(_NEGATIVE_RE.findall(signals))
    positive_hits = len(_POSITIVE_RE.findall(signals))
    update_hits = len(_UPDATE_RE.findall(signals))
    competitor_hits = len(_COMPETITOR_RE.findall(signals))
    stat_hits = len(_STAT_RE.findall(signals))
    bracket_count = len(_BRACKET_RE.findall(signals + notes_text))
    signal_words = len(re.findall(r"\b\w+\b", signals))

    parsed = urlparse(site if "://" in site else f"https://{site}") if site else None
    https_ok = bool(parsed and parsed.scheme == "https")

    volatility_index = 0.28
    volatility_index += min(0.35, negative_hits * 0.08)
    volatility_index += min(0.2, update_hits * 0.1)
    volatility_index += min(0.12, competitor_hits * 0.06)
    volatility_index -= min(0.15, positive_hits * 0.05)
    if signal_words < 20:
        volatility_index += 0.08
    volatility_index = _clamp_prob(volatility_index)

    predictive_score = 40
    predictive_score += min(18, positive_hits * 6)
    predictive_score += min(12, stat_hits * 4)
    predictive_score += 8 if https_ok else 0
    predictive_score += min(10, signal_words // 15)
    predictive_score -= min(20, negative_hits * 6)
    predictive_score -= min(10, bracket_count * 3)
    predictive_score = _clamp(predictive_score)

    if positive_hits > negative_hits:
        direction = "up"
    elif negative_hits > positive_hits:
        direction = "down"
    else:
        direction = "stable"

    confidence = _clamp_prob(0.45 + min(0.35, stat_hits * 0.08) + (0.08 if signal_words >= 40 else 0))
    traffic_delta = 8 if direction == "up" else -6 if direction == "down" else 2
    ranking_delta = -2 if direction == "up" else 3 if direction == "down" else 0

    trend_forecast = {
        "direction": direction,
        "confidence": confidence,
        "time_horizon_days": horizon,
        "traffic_delta_pct": traffic_delta,
        "ranking_delta_positions": ranking_delta,
        "confidence_interval": {"lower": traffic_delta - 8, "upper": traffic_delta + 10},
    }

    algorithm_watchlist: list[dict[str, Any]] = []
    if update_hits or "update" in signals.lower():
        algorithm_watchlist.append(
            {
                "signal": "Google core or quality update exposure",
                "type": "core_update",
                "likelihood": "high" if update_hits >= 1 else "medium",
                "impact_severity": "high",
                "recommended_response": "Audit affected landing pages for helpful content and E-E-A-T gaps.",
                "deadline_days": min(horizon, 30),
            }
        )
    if competitor_hits:
        algorithm_watchlist.append(
            {
                "signal": "Competitive SERP pressure on primary keyword",
                "type": "entity_graph",
                "likelihood": "medium",
                "impact_severity": "medium",
                "recommended_response": f"Refresh entity coverage and comparison content for '{keyword}'.",
                "deadline_days": min(horizon, 45),
            }
        )
    if negative_hits:
        algorithm_watchlist.append(
            {
                "signal": "Recent negative ranking or crawl anomalies",
                "type": "helpful_content",
                "likelihood": "high",
                "impact_severity": "critical" if negative_hits >= 2 else "high",
                "recommended_response": "Validate indexation, internal links, and content freshness on affected URLs.",
                "deadline_days": 14,
            }
        )

    entity_momentum = [
        {
            "entity": keyword or site or "primary entity",
            "prominence_trend": "rising" if direction == "up" else "declining" if direction == "down" else "stable",
            "action": "Expand entity-rich content and internal links to supporting pages.",
        }
    ]

    forecast_drivers: list[dict[str, Any]] = []
    if positive_hits:
        forecast_drivers.append(
            {
                "driver": "Positive recent performance signals",
                "weight": _clamp_prob(0.25 + positive_hits * 0.05),
                "direction": "positive",
                "confidence": confidence,
            }
        )
    if negative_hits:
        forecast_drivers.append(
            {
                "driver": "Observed ranking or crawl instability",
                "weight": _clamp_prob(0.2 + negative_hits * 0.06),
                "direction": "negative",
                "confidence": _clamp_prob(confidence + 0.05),
            }
        )
    if stat_hits:
        forecast_drivers.append(
            {
                "driver": "Quantified signal evidence in operator notes",
                "weight": 0.32,
                "direction": "positive" if direction != "down" else "negative",
                "confidence": confidence,
            }
        )
    if not forecast_drivers:
        forecast_drivers.append(
            {
                "driver": "Limited recent signal density; baseline stability assumed",
                "weight": 0.28,
                "direction": "positive" if direction == "up" else "negative" if direction == "down" else "positive",
                "confidence": 0.52,
            }
        )

    ranking_scenarios = [
        {"scenario": "best_case", "traffic_pct": max(8, traffic_delta + 12), "probability": 0.25},
        {"scenario": "base_case", "traffic_pct": traffic_delta, "probability": 0.55},
        {"scenario": "worst_case", "traffic_pct": min(-4, traffic_delta - 14), "probability": 0.2},
    ]

    early_warning_signals: list[dict[str, Any]] = []
    if negative_hits >= 2:
        early_warning_signals.append(
            {
                "signal": "Multiple negative movement indicators in recent signals",
                "severity": "high",
                "detected_at": "heuristic_scan",
                "recommended_action": "Run URL-level diagnostics and compare against pre-drop content versions.",
            }
        )

    defensive_playbook = [
        {
            "action": "Monitor Search Console coverage and query deltas weekly",
            "trigger": "Any new crawl or indexing anomaly",
            "timeline": "immediate",
        },
        {
            "action": f"Refresh on-page entity coverage for '{keyword}'",
            "trigger": "SERP volatility index above 0.45",
            "timeline": "30d",
        },
    ]

    next_actions: list[dict[str, Any]] = [
        {
            "action": f"Document baseline rank and traffic for '{keyword}' before day {horizon // 3}",
            "priority": "high",
            "effort": "low",
            "expected_impact": "Improves forecast validation accuracy",
        },
        {
            "action": "Set alerts for core update chatter and competitor content launches",
            "priority": "medium",
            "effort": "low",
            "expected_impact": "Reduces reaction lag to algorithm shifts",
        },
    ]
    if notes_text:
        next_actions.append(
            {
                "action": f"Operator note: {notes_text[:160]}",
                "priority": "medium",
                "effort": "low",
                "expected_impact": "Aligns forecast with business context",
            }
        )

    return {
        "predictive_score": predictive_score,
        "volatility_risk": _volatility_risk(volatility_index),
        "volatility_index": volatility_index,
        "trend_forecast": trend_forecast,
        "algorithm_watchlist": algorithm_watchlist,
        "entity_momentum": entity_momentum,
        "forecast_drivers": forecast_drivers,
        "ranking_scenarios": ranking_scenarios,
        "early_warning_signals": early_warning_signals,
        "defensive_playbook": defensive_playbook,
        "next_actions": next_actions,
        "quick_wins": [
            "Log daily rank snapshots for the primary keyword.",
            "Segment recent signals into technical vs content causes.",
            "Prepare a rollback plan for pages touched in the last 30 days.",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "signal_word_count": signal_words,
            "negative_hits": negative_hits,
            "positive_hits": positive_hits,
            "stat_hits": stat_hits,
            "https": https_ok,
        },
    }


def normalize_peao_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    try:
        out["predictive_score"] = _clamp(int(float(out.get("predictive_score", 50))))
    except (TypeError, ValueError):
        out["predictive_score"] = 50

    try:
        out["volatility_index"] = _clamp_prob(float(out.get("volatility_index", 0.35)))
    except (TypeError, ValueError):
        out["volatility_index"] = 0.35

    risk = str(out.get("volatility_risk", "")).lower()
    if risk not in {"low", "medium", "high"}:
        out["volatility_risk"] = _volatility_risk(out["volatility_index"])
    else:
        out["volatility_risk"] = risk

    trend = out.get("trend_forecast")
    if not isinstance(trend, dict):
        out["trend_forecast"] = {
            "direction": "stable",
            "confidence": 0.55,
            "time_horizon_days": 30,
            "traffic_delta_pct": 0,
            "ranking_delta_positions": 0,
            "confidence_interval": {"lower": -5, "upper": 8},
        }

    for list_key in (
        "algorithm_watchlist",
        "entity_momentum",
        "forecast_drivers",
        "ranking_scenarios",
        "early_warning_signals",
        "defensive_playbook",
        "next_actions",
        "quick_wins",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_peao_forecast(
    *,
    domain: str,
    primary_keyword: str,
    recent_signals: str,
    forecast_horizon_days: int,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run PEAO analysis."""
    prompt = (
        f"Create a PEAO forecast for domain: {clean_text_fn(domain, 300)}.\n"
        f"Primary keyword: {clean_text_fn(primary_keyword, 200)}.\n"
        f"Forecast horizon: {forecast_horizon_days} days.\n"
        f"Recent signals:\n{clean_text_fn(recent_signals, 2200)}\n\n"
        f"Notes: {clean_text_fn(notes, 500)}.\n"
        "Return volatility risk, trend forecast, watchlist, and next actions. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("predictive_score") is not None or llm_result.get("trend_forecast"):
            return normalize_peao_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_peao_signals(
        domain=domain,
        primary_keyword=primary_keyword,
        recent_signals=recent_signals,
        forecast_horizon_days=forecast_horizon_days,
        notes=notes,
    )
    return normalize_peao_result(heuristic, analysis_mode="heuristic", ai_available=False)
