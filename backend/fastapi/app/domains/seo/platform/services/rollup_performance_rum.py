"""Seo/Platform service: rollup performance rum."""

from .get_shared_job_store import _normalize_perf_metric_name
from .get_shared_job_store import _perf_float
from .get_shared_job_store import _perf_int
from .get_shared_job_store import _perf_percentile
from .get_shared_job_store import _performance_score_from_field
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any


def _rollup_performance_rum(analyses: list[dict[str, Any]], url: str, lookback_days: int = 28) -> dict[str, Any] | None:
    cutoff = datetime.now(UTC) - timedelta(days=max(1, lookback_days))
    normalized_url = str(url or "").rstrip("/")
    metrics: dict[str, list[float]] = {"lcp": [], "inp": [], "cls": [], "ttfb": [], "fcp": []}
    sessions: set[str] = set()
    device_counts: dict[str, int] = {}
    network_counts: dict[str, int] = {}
    geo_lcp: dict[tuple[str, str, str], list[float]] = {}
    daily_lcp: dict[str, list[float]] = {}
    for row in analyses:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if str(payload.get("url", "")).rstrip("/") != normalized_url:
            continue
        created_raw = str(row.get("created_at", ""))
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if created < cutoff:
            continue
        metric_name = _normalize_perf_metric_name(str(payload.get("metric_name", "")))
        if not metric_name:
            continue
        metric_value = _perf_float(payload.get("value"), -1.0)
        if metric_value < 0:
            continue
        metrics.setdefault(metric_name, []).append(metric_value)
        session_id = str(payload.get("session_id", "") or "")
        if session_id:
            sessions.add(session_id)
        device_type = str(payload.get("device_type", "") or "unknown").strip().lower()
        device_counts[device_type] = device_counts.get(device_type, 0) + 1
        network_type = str(payload.get("effective_connection_type", "") or "unknown").strip().lower()
        network_counts[network_type] = network_counts.get(network_type, 0) + 1
        if metric_name == "lcp":
            geo_key = (
                str(payload.get("country", "") or "unknown"),
                str(payload.get("region", "") or "unknown"),
                str(payload.get("isp", "") or "unknown"),
            )
            geo_lcp.setdefault(geo_key, []).append(metric_value)
            daily_key = created.strftime("%Y-%m-%d")
            daily_lcp.setdefault(daily_key, []).append(metric_value)
    sample_size = len(sessions) or max(
        len(metrics.get("lcp", [])), len(metrics.get("inp", [])), len(metrics.get("cls", []))
    )
    if sample_size <= 0:
        return None
    field = {
        "lcp_p75_ms": _perf_int(_perf_percentile(metrics.get("lcp", []), 0.75), 0),
        "inp_p75_ms": _perf_int(_perf_percentile(metrics.get("inp", []), 0.75), 0),
        "cls_p75": round(_perf_percentile(metrics.get("cls", []), 0.75), 4),
        "sample_size": sample_size,
        "period": f"{max(1, lookback_days)}d",
        "source": "web_vitals_rum",
    }
    core = {
        "lcp_ms": field["lcp_p75_ms"],
        "inp_ms": field["inp_p75_ms"],
        "cls": field["cls_p75"],
        "ttfb_ms": _perf_int(_perf_percentile(metrics.get("ttfb", []), 0.75), 0),
    }

    def _normalize_distribution(counts: dict[str, int]) -> dict[str, float]:
        total = sum(counts.values())
        if total <= 0:
            return {}
        return {key: round(value / total, 4) for key, value in counts.items() if key}

    geo_breakdown = []
    for (country, region, isp), values in sorted(geo_lcp.items(), key=lambda item: len(item[1]), reverse=True)[:8]:
        geo_breakdown.append(
            {
                "country": country,
                "region": region,
                "isp": isp,
                "lcp_p75_ms": _perf_int(_perf_percentile(values, 0.75), 0),
                "sample_size": len(values),
            }
        )
    history_runs = []
    for day_key in sorted(daily_lcp.keys())[-14:]:
        day_values = daily_lcp.get(day_key, [])
        day_lcp = _perf_int(_perf_percentile(day_values, 0.75), 0)
        history_runs.append(
            {
                "ts": f"{day_key}T00:00:00+00:00",
                "performance_score": _performance_score_from_field(
                    {"lcp_p75_ms": day_lcp, "inp_p75_ms": field["inp_p75_ms"], "cls_p75": field["cls_p75"]}
                ),
                "lcp_ms": day_lcp,
                "cls": field["cls_p75"],
                "device": "field-rum",
            }
        )
    regression_detected = False
    if len(history_runs) >= 2:
        regression_detected = _perf_int(history_runs[-1].get("lcp_ms"), 0) > _perf_int(history_runs[0].get("lcp_ms"), 0)
    return {
        "performance_score": _performance_score_from_field(field),
        "core_web_vitals": core,
        "field_web_vitals": field,
        "rum_summary": {
            "sessions": sample_size,
            "rage_click_rate": 0.0,
            "friction_score": max(0, min(100, 100 - _perf_int(field.get("inp_p75_ms"), 0) // 4)),
            "device_mix": _normalize_distribution(device_counts),
            "network_mix": _normalize_distribution(network_counts),
            "geo_isp_breakdown": geo_breakdown,
        },
        "history": {
            "trend": "degrading" if regression_detected else "improving",
            "regression_detected": regression_detected,
            "runs": history_runs,
        },
        "recommended_stack": ["web_vitals_rum", "lighthouse_cli", "pagespeed_insights_api", "chrome_ux_report_api"],
        "vendor_stack": [{"vendor": "web-vitals RUM", "usage": "First-party browser telemetry"}],
        "free_provider_status": {"web_vitals_rum": True},
        "data_provenance": {"source": "web_vitals_rum", "at": datetime.now(UTC).isoformat()},
    }
