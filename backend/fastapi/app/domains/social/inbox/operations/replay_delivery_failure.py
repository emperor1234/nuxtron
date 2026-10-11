"""Social/Inbox use cases: replay delivery failure."""

from __future__ import annotations
from ..constants import REPLY_NOT_FOUND
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..runtime import ContextRuntime
from ..schemas import ResponseReplayRequest
from ..schemas import SavedReplyRequest
from ..schemas import SavedReplyUpdateRequest
from .audit import helper_attempt_outbound_delivery
from .audit import helper_audit
from .audit import helper_build_delivery_idempotency_key
from .audit import helper_env_float
from .audit import helper_env_int
from .audit import helper_percentile
from .audit import helper_update_delivery_failure
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


async def execute_replay_delivery_failure(
    runtime: ContextRuntime, failure_id: int, payload: ResponseReplayRequest, auth: AuthDep
) -> dict[str, Any]:
    """Replay a failed outbound inbox delivery while guarding against duplicate sends."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:replay", 120, 60)
    with runtime._lock:
        failure = next(
            (
                item
                for item in runtime.delivery_failures_memory
                if item.get("tenant_id") == auth.tenant_id and int(item.get("id") or 0) == failure_id
            ),
            None,
        )
        if failure is None:
            raise HTTPException(status_code=404, detail="Delivery failure not found")
        message = next(
            (
                item
                for item in runtime.messages_memory
                if item.get("tenant_id") == auth.tenant_id
                and int(item.get("id") or 0) == int(failure.get("message_id") or 0)
            ),
            None,
        )
        if message is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
        if str(message.get("response_delivery_status")) == "sent":
            failure["status"] = "resolved"
            failure["resolution"] = "already_delivered"
            failure["resolved_at"] = datetime.now(UTC).isoformat()
            failure["resolved_by"] = payload.operator.strip()
            failure["replay_note"] = payload.note.strip() if payload.note else None
            return {
                "status": "ok",
                "tenant_id": auth.tenant_id,
                "replayed": False,
                "reason": "already_delivered",
                "failure": failure.copy(),
                "message": message.copy(),
            }
        current_status = str(failure.get("status") or "pending_retry").lower()
        if current_status not in {"pending_retry", "replaying"}:
            return {
                "status": "ok",
                "tenant_id": auth.tenant_id,
                "replayed": False,
                "reason": current_status,
                "failure": failure,
                "message": message.copy(),
            }
        replay_started_at = datetime.now(UTC).isoformat()
        failure["status"] = "replaying"
        failure["replay_started_at"] = replay_started_at
        failure["replayed_by"] = payload.operator.strip()
        failure["replay_note"] = payload.note.strip() if payload.note else None
        request_payload = dict(failure.get("payload") or {})
        response_text = str(message.get("last_response_preview") or request_payload.get("reply_text") or "")
        idempotency_key = str(
            request_payload.get("idempotency_key")
            or message.get("response_delivery_idempotency_key")
            or helper_build_delivery_idempotency_key(auth.tenant_id, int(message.get("id") or 0), response_text)
        )
        request_payload["idempotency_key"] = idempotency_key
    vendor_response, delivery_errors, attempts_made = await helper_attempt_outbound_delivery(
        vendor_id=str(failure.get("vendor_id") or ""),
        endpoint=str(failure.get("endpoint") or ""),
        request_payload=request_payload,
        idempotency_key=idempotency_key,
    )
    now_iso = datetime.now(UTC).isoformat()
    if vendor_response is None:
        combined_errors = [*list(failure.get("errors") or []), *delivery_errors]
        updated_failure = helper_update_delivery_failure(
            runtime,
            auth.tenant_id,
            failure_id,
            status="pending_retry",
            errors=combined_errors,
            retry_count=int(failure.get("retry_count") or 0) + 1,
            last_attempted_at=now_iso,
            replayed_by=payload.operator.strip(),
            replay_note=payload.note.strip() if payload.note else None,
        )
        with runtime._lock:
            message = next(
                (
                    m
                    for m in runtime.messages_memory
                    if m.get("tenant_id") == auth.tenant_id and m.get("id") == failure.get("message_id")
                ),
                None,
            )
            if message is not None:
                message["response_delivery_status"] = "failed"
                message["response_delivery_attempts"] = (
                    int(message.get("response_delivery_attempts") or 0) + attempts_made
                )
                message["response_delivery_failure_id"] = failure_id
                message["response_delivery_last_error"] = delivery_errors[-1] if delivery_errors else "delivery failed"
                message["response_delivery_idempotency_key"] = idempotency_key
                message["updated_at"] = now_iso
                updated_message = message.copy()
            else:
                updated_message = None
        raise HTTPException(
            status_code=502, detail=f"Replay delivery failed after retries; failure_id={failure_id}"
        ) from None
    updated_failure = helper_update_delivery_failure(
        runtime,
        auth.tenant_id,
        failure_id,
        status="resolved",
        resolution="replayed",
        resolved_at=now_iso,
        resolved_by=payload.operator.strip(),
        replay_note=payload.note.strip() if payload.note else None,
        retry_count=int(failure.get("retry_count") or 0) + 1,
        last_attempted_at=now_iso,
        payload=request_payload,
    )
    with runtime._lock:
        message = next(
            (
                m
                for m in runtime.messages_memory
                if m.get("tenant_id") == auth.tenant_id and m.get("id") == failure.get("message_id")
            ),
            None,
        )
        if message is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
        message["status"] = "complete"
        message["replied"] = True
        message["replied_at"] = now_iso
        message["response_delivered_at"] = now_iso
        message["response_delivery_vendor"] = failure.get("vendor_id")
        message["response_delivery_status"] = "sent"
        message["response_delivery_attempts"] = int(message.get("response_delivery_attempts") or 0) + attempts_made
        message["response_delivery_result"] = vendor_response
        message["response_delivery_failure_id"] = None
        message["response_delivery_last_error"] = None
        message["response_delivery_idempotency_key"] = idempotency_key
        message["updated_at"] = now_iso
        updated_message = message.copy()
    helper_audit(runtime, auth.tenant_id, "inbox_auto_response_delivery_replayed", int(failure.get("message_id") or 0))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "replayed": True,
        "failure": updated_failure or failure,
        "message": updated_message,
        "response": {"delivered": True, "idempotency_key": idempotency_key, "result": vendor_response},
    }


def execute_delivery_failure_replay_run_performance(
    runtime: ContextRuntime,
    auth: AuthDep,
    network: Annotated[str | None, Query(max_length=40)] = None,
    operator: Annotated[str | None, Query(max_length=120)] = None,
    window_hours: Annotated[int, Query(ge=1, le=24 * 30)] = 24,
) -> dict[str, Any]:
    """Return per-operator replay-run performance analytics over a bounded time window."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:replay-runs:performance", 120, 60)
    network_filter = network.strip().lower() if network else None
    operator_filter = operator.strip().lower() if operator else None
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=window_hours)
    with runtime._lock:
        runs = [
            item.copy()
            for item in runtime.delivery_replay_runs_memory
            if item.get("tenant_id") == auth.tenant_id
            and (network_filter is None or str(item.get("network_filter") or "").strip().lower() == network_filter)
        ]
    filtered_runs: list[dict[str, Any]] = []
    for run in runs:
        created_at_raw = str(run.get("created_at") or "").strip()
        if not created_at_raw:
            continue
        try:
            created_at_dt = datetime.fromisoformat(created_at_raw)
        except ValueError:
            continue
        if created_at_dt < window_start:
            continue
        run_operator = str(run.get("operator") or "unknown").strip().lower() or "unknown"
        if operator_filter is not None and run_operator != operator_filter:
            continue
        filtered_runs.append(run)
    by_operator: dict[str, dict[str, Any]] = {}
    for run in filtered_runs:
        run_operator = str(run.get("operator") or "unknown").strip().lower() or "unknown"
        selected_count = int(run.get("selected_count") or 0)
        replayed_count = int(run.get("replayed_count") or 0)
        failed_count = int(run.get("failed_count") or 0)
        duration_ms = max(0, int(run.get("duration_ms") or 0))
        stats = by_operator.setdefault(
            run_operator,
            {
                "operator": run_operator,
                "runs": 0,
                "selected_total": 0,
                "replayed_total": 0,
                "failed_total": 0,
                "durations_ms": [],
            },
        )
        stats["runs"] = int(stats["runs"]) + 1
        stats["selected_total"] = int(stats["selected_total"]) + selected_count
        stats["replayed_total"] = int(stats["replayed_total"]) + replayed_count
        stats["failed_total"] = int(stats["failed_total"]) + failed_count
        stats["durations_ms"].append(duration_ms)
    operator_rows: list[dict[str, Any]] = []
    operator_success_rate_low_threshold = helper_env_float(
        "INBOX_ALERT_OPERATOR_SUCCESS_RATE_LOW", 0.7, minimum=0.0, maximum=1.0
    )
    operator_min_selected_threshold = helper_env_int("INBOX_ALERT_OPERATOR_MIN_SELECTED", 3, minimum=0)
    operator_no_selection_min_runs_threshold = helper_env_int(
        "INBOX_ALERT_OPERATOR_NO_SELECTION_MIN_RUNS", 5, minimum=0
    )
    operator_latency_spike_multiplier = helper_env_float(
        "INBOX_ALERT_OPERATOR_LATENCY_SPIKE_MULTIPLIER", 2.0, minimum=1.0
    )
    operator_latency_min_runs_threshold = helper_env_int("INBOX_ALERT_OPERATOR_LATENCY_MIN_RUNS", 3, minimum=0)
    for stats in by_operator.values():
        durations: list[int] = list(stats["durations_ms"])
        selected_total = int(stats["selected_total"])
        replayed_total = int(stats["replayed_total"])
        failed_total = int(stats["failed_total"])
        success_rate = round(replayed_total / selected_total, 4) if selected_total else 0.0
        avg_duration_ms = round(sum(durations) / len(durations), 2) if durations else 0.0
        row = {
            "operator": stats["operator"],
            "runs": int(stats["runs"]),
            "selected_total": selected_total,
            "replayed_total": replayed_total,
            "failed_total": failed_total,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration_ms,
            "p50_duration_ms": round(helper_percentile(durations, 0.5), 2) if durations else 0.0,
            "p95_duration_ms": round(helper_percentile(durations, 0.95), 2) if durations else 0.0,
            "alerts": [],
        }
        if selected_total >= operator_min_selected_threshold and success_rate <= operator_success_rate_low_threshold:
            row["alerts"].append("operator_success_rate_low")
        if int(row["runs"]) >= operator_no_selection_min_runs_threshold and selected_total == 0:
            row["alerts"].append("operator_no_selection_only_runs")
        operator_rows.append(row)
    operator_rows.sort(
        key=lambda item: (int(item.get("runs") or 0), int(item.get("replayed_total") or 0)), reverse=True
    )
    total_selected = sum((int(item["selected_total"]) for item in operator_rows))
    total_replayed = sum((int(item["replayed_total"]) for item in operator_rows))
    total_failed = sum((int(item["failed_total"]) for item in operator_rows))
    overall_success_rate = round(total_replayed / total_selected, 4) if total_selected else 0.0
    global_p50_duration_ms = (
        round(helper_percentile([int(run.get("duration_ms") or 0) for run in filtered_runs], 0.5), 2)
        if filtered_runs
        else 0.0
    )
    overall_success_rate_low_threshold = helper_env_float(
        "INBOX_ALERT_OVERALL_SUCCESS_RATE_LOW", 0.7, minimum=0.0, maximum=1.0
    )
    overall_min_selected_threshold = helper_env_int("INBOX_ALERT_OVERALL_MIN_SELECTED", 3, minimum=0)
    for row in operator_rows:
        if (
            int(row["runs"]) >= operator_latency_min_runs_threshold
            and global_p50_duration_ms > 0
            and (float(row["avg_duration_ms"]) >= global_p50_duration_ms * operator_latency_spike_multiplier)
        ):
            row["alerts"].append("operator_latency_spike")
    anomaly_summary = {
        "operators_with_alerts": sum((1 for row in operator_rows if row["alerts"])),
        "total_alerts": sum((len(list(row["alerts"])) for row in operator_rows)),
        "global_p50_duration_ms": global_p50_duration_ms,
        "overall_success_rate_low": overall_success_rate <= overall_success_rate_low_threshold
        and total_selected >= overall_min_selected_threshold,
    }
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "generatedAt": now.isoformat(),
        "window_hours": window_hours,
        "window_start": window_start.isoformat(),
        "network_filter": network_filter,
        "operator_filter": operator_filter,
        "total_runs": len(filtered_runs),
        "total_selected": total_selected,
        "total_replayed": total_replayed,
        "total_failed": total_failed,
        "overall_success_rate": overall_success_rate,
        "anomaly_summary": anomaly_summary,
        "anomaly_thresholds": {
            "operator_success_rate_low": operator_success_rate_low_threshold,
            "operator_min_selected": operator_min_selected_threshold,
            "operator_no_selection_min_runs": operator_no_selection_min_runs_threshold,
            "operator_latency_spike_multiplier": operator_latency_spike_multiplier,
            "operator_latency_min_runs": operator_latency_min_runs_threshold,
            "overall_success_rate_low": overall_success_rate_low_threshold,
            "overall_min_selected": overall_min_selected_threshold,
        },
        "operators": operator_rows,
    }


def execute_create_saved_reply(runtime: ContextRuntime, payload: SavedReplyRequest, auth: AuthDep) -> dict[str, Any]:
    """ADDED: Create a pre-approved reply template in the saved replies library (§13.2)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:saved-replies:create", 120, 60)
    with runtime._lock:
        reply: dict[str, Any] = {
            "id": len(runtime.saved_replies_memory) + 1,
            "tenant_id": auth.tenant_id,
            "title": payload.title.strip(),
            "body": payload.body,
            "tags": [t.strip().lower() for t in payload.tags if t.strip()],
            "networks": [n.strip().lower() for n in payload.networks if n.strip()],
            "use_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.saved_replies_memory.append(reply)
    helper_audit(runtime, auth.tenant_id, "saved_reply_created", reply["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "reply": reply.copy()}


def execute_update_saved_reply(
    runtime: ContextRuntime, reply_id: int, payload: SavedReplyUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    """ADDED: Update a saved reply."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:saved-replies:update", 120, 60)
    with runtime._lock:
        reply = next(
            (
                r
                for r in runtime.saved_replies_memory
                if r.get("tenant_id") == auth.tenant_id and r.get("id") == reply_id
            ),
            None,
        )
        if reply is None:
            raise HTTPException(status_code=404, detail=REPLY_NOT_FOUND)
        if payload.title is not None:
            reply["title"] = payload.title.strip()
        if payload.body is not None:
            reply["body"] = payload.body
        if payload.tags is not None:
            reply["tags"] = [t.strip().lower() for t in payload.tags if t.strip()]
        if payload.networks is not None:
            reply["networks"] = [n.strip().lower() for n in payload.networks if n.strip()]
        reply["updated_at"] = datetime.now(UTC).isoformat()
        updated = reply.copy()
    return {"status": "ok", "tenant_id": auth.tenant_id, "reply": updated}
