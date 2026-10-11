"""Workflow reliability implementation with explicit dependencies."""

from .runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any


def default_reliability_policy() -> dict[str, Any]:
    return {
        "max_retries": 3,
        "base_backoff_ms": 250,
        "circuit_failure_threshold": 5,
        "circuit_cooldown_seconds": 120,
        "slo_availability_target_pct": 99.9,
        "slo_latency_p95_target_ms": 500,
        "replay_enabled": True,
    }


def ensure_reliability_fields(connector: dict[str, Any]) -> None:
    connector.setdefault("reliability_policy", default_reliability_policy())
    connector.setdefault(
        "reliability_stats",
        {
            "total_requests": 0,
            "failed_requests": 0,
            "retries_attempted": 0,
            "replay_enqueued": 0,
            "replay_success": 0,
            "replay_failed": 0,
        },
    )
    connector.setdefault(
        "circuit_breaker", {"state": "closed", "consecutive_failures": 0, "opened_at": None, "cooldown_seconds": 120}
    )


def is_retryable_failure(failure_type: str) -> bool:
    return failure_type in {"timeout", "http_5xx", "network"}


def compute_reliability_snapshot(connector: dict[str, Any]) -> dict[str, Any]:
    ensure_reliability_fields(connector)
    stats = connector.get("reliability_stats", {})
    policy = connector.get("reliability_policy", {})
    total_requests = int(stats.get("total_requests", 0))
    failed_requests = int(stats.get("failed_requests", 0))
    availability_pct = round((total_requests - failed_requests) / total_requests * 100, 2) if total_requests else 100.0
    p95_latency_ms = 120 if connector.get("status") == "healthy" else 480
    return {
        "availability_pct_rolling": availability_pct,
        "availability_target_pct": float(policy.get("slo_availability_target_pct", 99.9)),
        "availability_breached": availability_pct < float(policy.get("slo_availability_target_pct", 99.9)),
        "latency_p95_ms": p95_latency_ms,
        "latency_target_p95_ms": int(policy.get("slo_latency_p95_target_ms", 500)),
        "latency_breached": p95_latency_ms > int(policy.get("slo_latency_p95_target_ms", 500)),
        "error_budget_pct": float(connector.get("error_budget_pct", 1.0)),
        "error_rate_pct": round(failed_requests / total_requests * 100, 2) if total_requests else 0.0,
    }


def next_retry_at(when: datetime, attempts: int, base_backoff_ms: int) -> str:
    backoff_ms = base_backoff_ms * 2 ** max(attempts - 1, 0)
    return (when + timedelta(milliseconds=backoff_ms)).isoformat()


def is_in_maintenance_window(runtime: WorkflowRuntime, tenant_id: str, connector_id: int, now: datetime) -> bool:
    current_hour = now.hour
    for window in runtime.connector_maintenance_windows:
        if window.get("tenant_id") != tenant_id or not bool(window.get("enabled", True)):
            continue
        connector_ids = window.get("connector_ids") or []
        if connector_ids and connector_id not in connector_ids:
            continue
        start_hour = int(window.get("start_hour_utc", 0))
        end_hour = int(window.get("end_hour_utc", 0))
        if start_hour == end_hour:
            return True
        if start_hour < end_hour:
            if start_hour <= current_hour < end_hour:
                return True
        elif current_hour >= start_hour or current_hour < end_hour:
            return True
    return False


def process_replay_item_locked(
    *, connector: dict[str, Any], item: dict[str, Any], force_success: bool
) -> dict[str, Any]:
    ensure_reliability_fields(connector)
    stats = connector["reliability_stats"]
    circuit = connector["circuit_breaker"]
    policy = connector["reliability_policy"]
    item["attempts"] = int(item.get("attempts", 0)) + 1
    success = bool(force_success) or connector.get("status") == "healthy"
    now = datetime.now(UTC)
    if success:
        item["status"] = "succeeded"
        item["updated_at"] = now.isoformat()
        item["next_retry_at"] = None
        stats["replay_success"] = int(stats.get("replay_success", 0)) + 1
        circuit["state"] = "closed"
        circuit["consecutive_failures"] = 0
        circuit["opened_at"] = None
        connector["status"] = "healthy"
    else:
        max_retries = int(policy.get("max_retries", 0))
        if int(item.get("attempts", 0)) > max_retries:
            item["status"] = "failed"
            item["next_retry_at"] = None
            stats["replay_failed"] = int(stats.get("replay_failed", 0)) + 1
        else:
            item["status"] = "pending"
            item["next_retry_at"] = next_retry_at(
                now, int(item.get("attempts", 0)), int(policy.get("base_backoff_ms", 250))
            )
        item["updated_at"] = now.isoformat()
        circuit["consecutive_failures"] = int(circuit.get("consecutive_failures", 0)) + 1
        if int(circuit["consecutive_failures"]) >= int(policy.get("circuit_failure_threshold", 5)):
            circuit["state"] = "open"
            circuit["opened_at"] = now.isoformat()
        connector["status"] = "degraded"
    connector["updated_at"] = now.isoformat()
    reliability = compute_reliability_snapshot(connector)
    return {"item": item, "connector": connector, "slo": reliability}
