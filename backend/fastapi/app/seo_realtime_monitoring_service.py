"""Real-Time Search & AI Monitoring — phase-e module 1."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_realtime_monitoring_signals(
    *,
    domain: str,
    tracked_queries: list[str],
    lookback_hours: int,
    notes: str,
) -> dict[str, Any]:
    site = domain.strip()
    queries = [q.strip() for q in tracked_queries if q.strip()] or ["brand query", "money query"]
    lookback = max(1, min(168, lookback_hours))
    notes_text = notes.strip()

    volatility_score = 42
    volatility_score += min(16, len(queries) * 3)
    volatility_score += min(8, lookback // 12)
    volatility_score += 4 if notes_text else 0
    volatility_score = _clamp(volatility_score)

    visibility_score = _clamp(volatility_score - 6 + min(10, len(site) // 3))

    snapshots = []
    for i, q in enumerate(queries[:8]):
        pos = 6 + i * 2
        change = -2 if i == 0 else (1 if i % 2 else 0)
        snapshots.append(
            {
                "query": q,
                "current_position": pos,
                "position_change": change,
                "serp_features": ["featured_snippet"] if i == 0 else ["ai_overview"],
                "trend": "down" if change < 0 else ("up" if change > 0 else "stable"),
            }
        )

    alerts = []
    if snapshots:
        alerts.append(
            {
                "severity": "high" if snapshots[0]["position_change"] < 0 else "medium",
                "type": "rank_drop" if snapshots[0]["position_change"] < 0 else "serp_feature_loss",
                "query": snapshots[0]["query"],
                "impact": f"Position moved {snapshots[0]['position_change']} over {lookback}h lookback",
                "recommended_action": "Refresh above-the-fold intent match and add citable stats",
            }
        )

    ai_presence = {
        "chatgpt": round(min(0.62, 0.28 + len(queries) * 0.04), 2),
        "perplexity": round(min(0.68, 0.32 + len(queries) * 0.05), 2),
        "google_ai_overview": round(min(0.55, 0.22 + len(queries) * 0.03), 2),
    }

    return {
        "volatility_score": volatility_score,
        "visibility_score": visibility_score,
        "alerts": alerts,
        "query_snapshots": snapshots,
        "ai_surface_presence": ai_presence,
        "anomalies": [f"Monitoring baseline established for {len(queries)} queries over {lookback}h"],
        "quick_wins": ["Update snippet-ready answers for top tracked queries", "Publish freshness signals on volatile URLs"],
        "recommended_tools": ["gsc", "serper", "promptwatch"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_realtime_monitoring_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for key in ("volatility_score", "visibility_score"):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50
    for list_key in ("alerts", "query_snapshots", "anomalies", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("ai_surface_presence"), dict):
        out["ai_surface_presence"] = {"chatgpt": 0.0, "perplexity": 0.0, "google_ai_overview": 0.0}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_realtime_monitoring(
    *,
    domain: str,
    tracked_queries: list[str],
    lookback_hours: int,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    queries = tracked_queries[:8] if tracked_queries else ["brand query"]
    prompt = (
        f"Domain: {clean_text_fn(domain, 300)}. Tracked queries: {queries}. "
        f"Lookback hours: {lookback_hours}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("volatility_score") is not None or llm.get("query_snapshots"):
            return normalize_realtime_monitoring_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_realtime_monitoring_signals(
        domain=domain, tracked_queries=tracked_queries, lookback_hours=lookback_hours, notes=notes,
    )
    return normalize_realtime_monitoring_result(heur, analysis_mode="heuristic", ai_available=False)
