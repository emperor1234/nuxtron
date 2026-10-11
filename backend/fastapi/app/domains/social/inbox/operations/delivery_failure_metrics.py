"""Social/Inbox use cases: delivery failure metrics."""

from __future__ import annotations
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import DeliveryFailureBulkReplayRequest
from ..schemas import DeliveryFailureReplayPendingRequest
from .audit import helper_env_float
from .audit import helper_env_int
from .audit import helper_record_replay_run
from .replay_delivery_failures_bulk import execute_replay_delivery_failures_bulk
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any
import time


def execute_delivery_failure_metrics(
    runtime: ContextRuntime, auth: AuthDep, network: Annotated[str | None, Query(max_length=40)] = None
) -> dict[str, Any]:
    """Return operational metrics for Smart Inbox delivery failures and replay actions."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:metrics", 120, 60)
    network_filter = network.strip().lower() if network else None
    with runtime._lock:
        failures = [
            item.copy()
            for item in runtime.delivery_failures_memory
            if item.get("tenant_id") == auth.tenant_id
            and (network_filter is None or str(item.get("network", "")).strip().lower() == network_filter)
        ]
        tenant_audit_events = [
            entry.copy()
            for entry in runtime.audit_log_memory
            if entry.get("tenant_id") == auth.tenant_id
            and str(entry.get("source")) == "smart-inbox-router"
            and str(entry.get("action", "")).startswith("inbox_auto_response_delivery_")
        ]
        replay_runs = [
            item.copy()
            for item in runtime.delivery_replay_runs_memory
            if item.get("tenant_id") == auth.tenant_id
            and (network_filter is None or str(item.get("network_filter") or "").strip().lower() == network_filter)
        ]
    by_status: dict[str, int] = {}
    by_network: dict[str, int] = {}
    by_resolution: dict[str, int] = {}
    replay_runs_by_operator: dict[str, int] = {}
    retry_attempt_sum = 0
    oldest_pending_age_seconds = 0
    replay_runs_last_24h = 0
    replay_runs_selected_total = 0
    replay_runs_replayed_total = 0
    replay_runs_failed_total = 0
    replay_runs_with_no_selection = 0
    now = datetime.now(UTC)
    for item in failures:
        status_name = str(item.get("status") or "unknown").lower()
        by_status[status_name] = by_status.get(status_name, 0) + 1
        network_name = str(item.get("network") or "unknown").lower()
        by_network[network_name] = by_network.get(network_name, 0) + 1
        resolution_name = str(item.get("resolution") or "").strip().lower()
        if resolution_name:
            by_resolution[resolution_name] = by_resolution.get(resolution_name, 0) + 1
        retry_attempt_sum += int(item.get("retry_count") or 0)
        if status_name == "pending_retry":
            created_at = str(item.get("created_at") or "").strip()
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    age_seconds = int((now - created_dt).total_seconds())
                    if age_seconds > oldest_pending_age_seconds:
                        oldest_pending_age_seconds = max(0, age_seconds)
                except ValueError:
                    continue
    for run in replay_runs:
        operator_name = str(run.get("operator") or "unknown").strip().lower() or "unknown"
        replay_runs_by_operator[operator_name] = replay_runs_by_operator.get(operator_name, 0) + 1
        selected_count = int(run.get("selected_count") or 0)
        replayed_count = int(run.get("replayed_count") or 0)
        failed_count = int(run.get("failed_count") or 0)
        replay_runs_selected_total += selected_count
        replay_runs_replayed_total += replayed_count
        replay_runs_failed_total += failed_count
        if selected_count == 0:
            replay_runs_with_no_selection += 1
        created_at_raw = str(run.get("created_at") or "").strip()
        if created_at_raw:
            try:
                created_at_dt = datetime.fromisoformat(created_at_raw)
                if created_at_dt >= now - timedelta(hours=24):
                    replay_runs_last_24h += 1
            except ValueError:
                continue
    tenant_audit_events.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    recent_operations = [
        {"action": event.get("action"), "ref_id": event.get("ref_id"), "created_at": event.get("created_at")}
        for event in tenant_audit_events[:20]
    ]
    total_failures = len(failures)
    pending_count = by_status.get("pending_retry", 0)
    resolved_count = by_status.get("resolved", 0)
    pending_ratio = round(pending_count / total_failures, 4) if total_failures else 0.0
    replay_success_rate = (
        round(replay_runs_replayed_total / replay_runs_selected_total, 4) if replay_runs_selected_total else 0.0
    )
    replay_no_selection_ratio = round(replay_runs_with_no_selection / len(replay_runs), 4) if replay_runs else 0.0
    pending_ratio_high_threshold = helper_env_float("INBOX_ALERT_PENDING_RATIO_HIGH", 0.35, minimum=0.0, maximum=1.0)
    pending_min_count_threshold = helper_env_int("INBOX_ALERT_PENDING_MIN_COUNT", 3, minimum=0)
    oldest_pending_age_threshold_seconds = helper_env_int("INBOX_ALERT_OLDEST_PENDING_AGE_SECONDS", 60 * 60, minimum=0)
    replay_success_rate_low_threshold = helper_env_float(
        "INBOX_ALERT_REPLAY_SUCCESS_RATE_LOW", 0.7, minimum=0.0, maximum=1.0
    )
    replay_min_selected_threshold = helper_env_int("INBOX_ALERT_REPLAY_MIN_SELECTED", 3, minimum=0)
    no_selection_ratio_high_threshold = helper_env_float(
        "INBOX_ALERT_NO_SELECTION_RATIO_HIGH", 0.8, minimum=0.0, maximum=1.0
    )
    no_selection_min_runs_threshold = helper_env_int("INBOX_ALERT_NO_SELECTION_MIN_RUNS", 5, minimum=0)
    alert_flags: list[dict[str, Any]] = []
    if pending_ratio >= pending_ratio_high_threshold and pending_count >= pending_min_count_threshold:
        alert_flags.append(
            {
                "code": "pending_backlog_ratio_high",
                "severity": "warning",
                "value": pending_ratio,
                "context": {
                    "pending_count": pending_count,
                    "total_failures": total_failures,
                    "ratio_threshold": pending_ratio_high_threshold,
                    "min_count_threshold": pending_min_count_threshold,
                },
            }
        )
    if oldest_pending_age_seconds >= oldest_pending_age_threshold_seconds:
        alert_flags.append(
            {
                "code": "oldest_pending_age_high",
                "severity": "warning",
                "value": oldest_pending_age_seconds,
                "context": {"threshold_seconds": oldest_pending_age_threshold_seconds},
            }
        )
    if (
        replay_runs_selected_total >= replay_min_selected_threshold
        and replay_success_rate <= replay_success_rate_low_threshold
    ):
        alert_flags.append(
            {
                "code": "replay_success_rate_low",
                "severity": "critical",
                "value": replay_success_rate,
                "context": {
                    "selected_total": replay_runs_selected_total,
                    "replayed_total": replay_runs_replayed_total,
                    "success_rate_threshold": replay_success_rate_low_threshold,
                    "min_selected_threshold": replay_min_selected_threshold,
                },
            }
        )
    if (
        len(replay_runs) >= no_selection_min_runs_threshold
        and replay_no_selection_ratio >= no_selection_ratio_high_threshold
    ):
        alert_flags.append(
            {
                "code": "replay_runs_no_selection_spike",
                "severity": "warning",
                "value": replay_no_selection_ratio,
                "context": {
                    "total_runs": len(replay_runs),
                    "runs_with_no_selection": replay_runs_with_no_selection,
                    "ratio_threshold": no_selection_ratio_high_threshold,
                    "min_runs_threshold": no_selection_min_runs_threshold,
                },
            }
        )
    replay_runs.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    recent_replay_runs = [
        {
            "id": run.get("id"),
            "operator": run.get("operator"),
            "selected_count": run.get("selected_count"),
            "replayed_count": run.get("replayed_count"),
            "failed_count": run.get("failed_count"),
            "network_filter": run.get("network_filter"),
            "created_at": run.get("created_at"),
        }
        for run in replay_runs[:10]
    ]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "generatedAt": now.isoformat(),
        "network_filter": network_filter,
        "total_failures": total_failures,
        "pending_count": pending_count,
        "resolved_count": resolved_count,
        "pending_ratio": pending_ratio,
        "avg_retry_attempts": round(retry_attempt_sum / total_failures, 2) if total_failures else 0.0,
        "oldest_pending_age_seconds": oldest_pending_age_seconds,
        "by_status": by_status,
        "by_network": by_network,
        "by_resolution": by_resolution,
        "recent_operations": recent_operations,
        "alerts": alert_flags,
        "alert_thresholds": {
            "pending_ratio_high": pending_ratio_high_threshold,
            "pending_min_count": pending_min_count_threshold,
            "oldest_pending_age_seconds": oldest_pending_age_threshold_seconds,
            "replay_success_rate_low": replay_success_rate_low_threshold,
            "replay_min_selected": replay_min_selected_threshold,
            "no_selection_ratio_high": no_selection_ratio_high_threshold,
            "no_selection_min_runs": no_selection_min_runs_threshold,
        },
        "replay_run_metrics": {
            "total_runs": len(replay_runs),
            "runs_last_24h": replay_runs_last_24h,
            "runs_with_no_selection": replay_runs_with_no_selection,
            "selected_total": replay_runs_selected_total,
            "replayed_total": replay_runs_replayed_total,
            "failed_total": replay_runs_failed_total,
            "replayed_success_rate": replay_success_rate,
            "no_selection_ratio": replay_no_selection_ratio,
            "by_operator": replay_runs_by_operator,
            "recent_runs": recent_replay_runs,
        },
    }


async def execute_replay_pending_delivery_failures(
    runtime: ContextRuntime, payload: DeliveryFailureReplayPendingRequest, auth: AuthDep
) -> dict[str, Any]:
    """Replay the next pending failure items with limit and optional network filter."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:replay-pending", 60, 60)
    run_started = time.perf_counter()
    network_filter = payload.network.strip().lower() if payload.network else None
    with runtime._lock:
        pending = [
            item
            for item in runtime.delivery_failures_memory
            if item.get("tenant_id") == auth.tenant_id
            and str(item.get("status", "")).lower() == "pending_retry"
            and (network_filter is None or str(item.get("network", "")).strip().lower() == network_filter)
        ]
    pending.sort(key=lambda item: int(item.get("id") or 0))
    selected_ids = [int(item.get("id") or 0) for item in pending[: payload.limit] if int(item.get("id") or 0) > 0]
    if not selected_ids:
        empty_result = {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "requested_limit": payload.limit,
            "selected_count": 0,
            "selected_failure_ids": [],
            "count": 0,
            "replayed_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "not_found_count": 0,
            "items": [],
        }
        run_record = helper_record_replay_run(
            runtime,
            tenant_id=auth.tenant_id,
            operator=payload.operator.strip(),
            note=payload.note.strip() if payload.note else None,
            requested_limit=payload.limit,
            selected_failure_ids=[],
            network_filter=network_filter,
            replay_result=empty_result,
            duration_ms=max(0, int((time.perf_counter() - run_started) * 1000)),
        )
        empty_result["run"] = run_record
        return empty_result
    replay_result = await execute_replay_delivery_failures_bulk(
        runtime,
        DeliveryFailureBulkReplayRequest(failure_ids=selected_ids, operator=payload.operator, note=payload.note),
        auth,
    )
    replay_result["requested_limit"] = payload.limit
    replay_result["selected_count"] = len(selected_ids)
    replay_result["selected_failure_ids"] = selected_ids
    replay_result["network_filter"] = network_filter
    run_record = helper_record_replay_run(
        runtime,
        tenant_id=auth.tenant_id,
        operator=payload.operator.strip(),
        note=payload.note.strip() if payload.note else None,
        requested_limit=payload.limit,
        selected_failure_ids=selected_ids,
        network_filter=network_filter,
        replay_result=replay_result,
        duration_ms=max(0, int((time.perf_counter() - run_started) * 1000)),
    )
    replay_result["run"] = run_record
    return replay_result


def execute_inbox_ops_config(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Return effective Smart Inbox operations configuration used by replay and anomaly analytics."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:ops-config", 120, 60)
    replay_config = {
        "delivery_max_retries": helper_env_int("INBOX_DELIVERY_MAX_RETRIES", 3, minimum=1),
        "delivery_backoff_seconds": helper_env_float("INBOX_DELIVERY_BACKOFF_SECONDS", 0.5, minimum=0.0),
        "delivery_max_backoff_seconds": helper_env_float("INBOX_DELIVERY_MAX_BACKOFF_SECONDS", 8.0, minimum=0.0),
        "replay_pending_limit_default": 25,
        "replay_pending_limit_max": 200,
    }
    metrics_alert_thresholds = {
        "pending_ratio_high": helper_env_float("INBOX_ALERT_PENDING_RATIO_HIGH", 0.35, minimum=0.0, maximum=1.0),
        "pending_min_count": helper_env_int("INBOX_ALERT_PENDING_MIN_COUNT", 3, minimum=0),
        "oldest_pending_age_seconds": helper_env_int("INBOX_ALERT_OLDEST_PENDING_AGE_SECONDS", 60 * 60, minimum=0),
        "replay_success_rate_low": helper_env_float(
            "INBOX_ALERT_REPLAY_SUCCESS_RATE_LOW", 0.7, minimum=0.0, maximum=1.0
        ),
        "replay_min_selected": helper_env_int("INBOX_ALERT_REPLAY_MIN_SELECTED", 3, minimum=0),
        "no_selection_ratio_high": helper_env_float(
            "INBOX_ALERT_NO_SELECTION_RATIO_HIGH", 0.8, minimum=0.0, maximum=1.0
        ),
        "no_selection_min_runs": helper_env_int("INBOX_ALERT_NO_SELECTION_MIN_RUNS", 5, minimum=0),
    }
    performance_alert_thresholds = {
        "operator_success_rate_low": helper_env_float(
            "INBOX_ALERT_OPERATOR_SUCCESS_RATE_LOW", 0.7, minimum=0.0, maximum=1.0
        ),
        "operator_min_selected": helper_env_int("INBOX_ALERT_OPERATOR_MIN_SELECTED", 3, minimum=0),
        "operator_no_selection_min_runs": helper_env_int("INBOX_ALERT_OPERATOR_NO_SELECTION_MIN_RUNS", 5, minimum=0),
        "operator_latency_spike_multiplier": helper_env_float(
            "INBOX_ALERT_OPERATOR_LATENCY_SPIKE_MULTIPLIER", 2.0, minimum=1.0
        ),
        "operator_latency_min_runs": helper_env_int("INBOX_ALERT_OPERATOR_LATENCY_MIN_RUNS", 3, minimum=0),
        "overall_success_rate_low": helper_env_float(
            "INBOX_ALERT_OVERALL_SUCCESS_RATE_LOW", 0.7, minimum=0.0, maximum=1.0
        ),
        "overall_min_selected": helper_env_int("INBOX_ALERT_OVERALL_MIN_SELECTED", 3, minimum=0),
    }
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "generatedAt": datetime.now(UTC).isoformat(),
        "replay": replay_config,
        "metrics_alert_thresholds": metrics_alert_thresholds,
        "performance_alert_thresholds": performance_alert_thresholds,
    }
