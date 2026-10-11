"""Social/Inbox use cases: replay delivery failures bulk."""

from __future__ import annotations
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import DeliveryFailureBulkReplayRequest
from .audit import helper_attempt_outbound_delivery
from .audit import helper_audit
from .audit import helper_build_delivery_idempotency_key
from datetime import UTC
from datetime import datetime
from fastapi import Query
from typing import Annotated
from typing import Any


async def execute_replay_delivery_failures_bulk(
    runtime: ContextRuntime, payload: DeliveryFailureBulkReplayRequest, auth: AuthDep
) -> dict[str, Any]:
    """Replay multiple pending delivery failures and return per-item outcomes."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:replay-bulk", 60, 60)
    deduped_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in payload.failure_ids:
        if raw_id in seen:
            continue
        seen.add(raw_id)
        deduped_ids.append(raw_id)
    operator = payload.operator.strip()
    note = payload.note.strip() if payload.note else None
    items: list[dict[str, Any]] = []
    for failure_id in deduped_ids:
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
                items.append({"failure_id": failure_id, "replayed": False, "status": "not_found"})
                continue
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
                items.append({"failure_id": failure_id, "replayed": False, "status": "message_not_found"})
                continue
            if str(message.get("response_delivery_status")) == "sent":
                now_iso = datetime.now(UTC).isoformat()
                failure["status"] = "resolved"
                failure["resolution"] = "already_delivered"
                failure["resolved_at"] = now_iso
                failure["resolved_by"] = operator
                failure["replay_note"] = note
                items.append({"failure_id": failure_id, "replayed": False, "status": "already_delivered"})
                continue
            current_status = str(failure.get("status") or "pending_retry").lower()
            if current_status not in {"pending_retry", "replaying"}:
                items.append({"failure_id": failure_id, "replayed": False, "status": current_status})
                continue
            replay_started_at = datetime.now(UTC).isoformat()
            failure["status"] = "replaying"
            failure["replay_started_at"] = replay_started_at
            failure["replayed_by"] = operator
            failure["replay_note"] = note
            request_payload = dict(failure.get("payload") or {})
            response_text = str(message.get("last_response_preview") or request_payload.get("reply_text") or "")
            idempotency_key = str(
                request_payload.get("idempotency_key")
                or message.get("response_delivery_idempotency_key")
                or helper_build_delivery_idempotency_key(auth.tenant_id, int(message.get("id") or 0), response_text)
            )
            request_payload["idempotency_key"] = idempotency_key
            vendor_id = str(failure.get("vendor_id") or "")
            endpoint = str(failure.get("endpoint") or "")
            message_id = int(message.get("id") or 0)
        vendor_response, delivery_errors, attempts_made = await helper_attempt_outbound_delivery(
            vendor_id=vendor_id, endpoint=endpoint, request_payload=request_payload, idempotency_key=idempotency_key
        )
        now_iso = datetime.now(UTC).isoformat()
        if vendor_response is None:
            with runtime._lock:
                failure_ref = next(
                    (
                        item
                        for item in runtime.delivery_failures_memory
                        if item.get("tenant_id") == auth.tenant_id and int(item.get("id") or 0) == failure_id
                    ),
                    None,
                )
                if failure_ref is not None:
                    failure_ref["status"] = "pending_retry"
                    failure_ref["errors"] = [*list(failure_ref.get("errors") or []), *delivery_errors]
                    failure_ref["retry_count"] = int(failure_ref.get("retry_count") or 0) + 1
                    failure_ref["last_attempted_at"] = now_iso
                    failure_ref["replayed_by"] = operator
                    failure_ref["replay_note"] = note
                message_ref = next(
                    (
                        item
                        for item in runtime.messages_memory
                        if item.get("tenant_id") == auth.tenant_id and int(item.get("id") or 0) == message_id
                    ),
                    None,
                )
                if message_ref is not None:
                    message_ref["response_delivery_status"] = "failed"
                    message_ref["response_delivery_attempts"] = (
                        int(message_ref.get("response_delivery_attempts") or 0) + attempts_made
                    )
                    message_ref["response_delivery_failure_id"] = failure_id
                    message_ref["response_delivery_last_error"] = (
                        delivery_errors[-1] if delivery_errors else "delivery failed"
                    )
                    message_ref["response_delivery_idempotency_key"] = idempotency_key
                    message_ref["updated_at"] = now_iso
            items.append(
                {
                    "failure_id": failure_id,
                    "replayed": False,
                    "status": "delivery_failed",
                    "attempts_made": attempts_made,
                    "last_error": delivery_errors[-1] if delivery_errors else "delivery failed",
                }
            )
            continue
        with runtime._lock:
            failure_ref = next(
                (
                    item
                    for item in runtime.delivery_failures_memory
                    if item.get("tenant_id") == auth.tenant_id and int(item.get("id") or 0) == failure_id
                ),
                None,
            )
            if failure_ref is not None:
                failure_ref["status"] = "resolved"
                failure_ref["resolution"] = "replayed"
                failure_ref["resolved_at"] = now_iso
                failure_ref["resolved_by"] = operator
                failure_ref["replay_note"] = note
                failure_ref["retry_count"] = int(failure_ref.get("retry_count") or 0) + 1
                failure_ref["last_attempted_at"] = now_iso
                failure_ref["payload"] = request_payload
            message_ref = next(
                (
                    item
                    for item in runtime.messages_memory
                    if item.get("tenant_id") == auth.tenant_id and int(item.get("id") or 0) == message_id
                ),
                None,
            )
            if message_ref is not None:
                message_ref["status"] = "complete"
                message_ref["replied"] = True
                message_ref["replied_at"] = now_iso
                message_ref["response_delivered_at"] = now_iso
                message_ref["response_delivery_vendor"] = vendor_id
                message_ref["response_delivery_status"] = "sent"
                message_ref["response_delivery_attempts"] = (
                    int(message_ref.get("response_delivery_attempts") or 0) + attempts_made
                )
                message_ref["response_delivery_result"] = vendor_response
                message_ref["response_delivery_failure_id"] = None
                message_ref["response_delivery_last_error"] = None
                message_ref["response_delivery_idempotency_key"] = idempotency_key
                message_ref["updated_at"] = now_iso
        helper_audit(runtime, auth.tenant_id, "inbox_auto_response_delivery_replayed_bulk", message_id)
        items.append(
            {
                "failure_id": failure_id,
                "replayed": True,
                "status": "replayed",
                "attempts_made": attempts_made,
                "idempotency_key": idempotency_key,
            }
        )
    replayed_count = sum((1 for item in items if item.get("replayed") is True))
    not_found_count = sum((1 for item in items if item.get("status") == "not_found"))
    failed_count = sum((1 for item in items if item.get("status") == "delivery_failed"))
    skipped_count = len(items) - replayed_count - failed_count
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "replayed_count": replayed_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "not_found_count": not_found_count,
        "items": items,
    }


def execute_inbox_ops_runbooks(
    runtime: ContextRuntime, auth: AuthDep, code: Annotated[str | None, Query(max_length=120)] = None
) -> dict[str, Any]:
    """Return alert runbooks for Smart Inbox operations and replay governance."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:ops:runbooks", 120, 60)
    runbooks = [
        {
            "code": "pending_backlog_ratio_high",
            "title": "Pending Delivery Backlog High",
            "severity": "warning",
            "steps": [
                "Open /inbox/delivery-failures?status=pending_retry and segment by network.",
                "Check /inbox/delivery-failures/replay-runs/performance for operator bottlenecks.",
                "Run replay-pending with a controlled limit and verify resolved movement.",
            ],
        },
        {
            "code": "oldest_pending_age_high",
            "title": "Oldest Pending Failure Age High",
            "severity": "warning",
            "steps": [
                "Identify the oldest failure from /inbox/delivery-failures list.",
                "Attempt targeted replay for the failure id.",
                "If replay fails repeatedly, resolve to manual_followup and notify owner.",
            ],
        },
        {
            "code": "replay_success_rate_low",
            "title": "Replay Success Rate Low",
            "severity": "critical",
            "steps": [
                "Inspect last errors in replay-pending and replay-bulk response items.",
                "Verify vendor credentials and endpoint readiness for affected network.",
                "Throttle replay batches while escalating provider incident.",
            ],
        },
        {
            "code": "replay_runs_no_selection_spike",
            "title": "Replay No-Selection Spike",
            "severity": "warning",
            "steps": [
                "Confirm queue input path still creates pending_retry failures.",
                "Validate network filter and replay limit parameters used by operators.",
                "Review approval pipeline to ensure failures are entering DLQ when delivery fails.",
            ],
        },
        {
            "code": "operator_success_rate_low",
            "title": "Operator Replay Success Rate Low",
            "severity": "warning",
            "steps": [
                "Open replay-runs/performance with operator filter.",
                "Check recent replay items for not_found and delivery_failed statuses.",
                "Pair operator with runbook owner until success rate recovers.",
            ],
        },
        {
            "code": "operator_no_selection_only_runs",
            "title": "Operator Producing Empty Replay Runs",
            "severity": "warning",
            "steps": [
                "Confirm operator uses correct network filter and tenant context.",
                "Review pending queue count before replay execution.",
                "Adjust playbook to avoid no-op replays during zero-backlog windows.",
            ],
        },
        {
            "code": "operator_latency_spike",
            "title": "Operator Replay Latency Spike",
            "severity": "warning",
            "steps": [
                "Inspect provider latency and timeout trends for the operator runs.",
                "Reduce replay batch size and retry with smaller windows.",
                "Escalate provider if p95 latency remains elevated.",
            ],
        },
    ]
    code_filter = code.strip().lower() if code else None
    if code_filter is not None:
        runbooks = [item for item in runbooks if str(item.get("code")) == code_filter]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(runbooks),
        "items": runbooks,
        "code_filter": code_filter,
    }


def execute_list_saved_replies(
    runtime: ContextRuntime,
    auth: AuthDep,
    search: Annotated[str | None, Query(max_length=120)] = None,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    network: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """ADDED: List saved replies with search and filter (§13.2)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:saved-replies:list", 240, 60)
    search_lc = search.strip().lower() if search else None
    tag_f = tag.strip().lower() if tag else None
    network_f = network.strip().lower() if network else None
    with runtime._lock:
        items = [
            r.copy()
            for r in runtime.saved_replies_memory
            if r.get("tenant_id") == auth.tenant_id
            and (
                search_lc is None
                or search_lc in str(r.get("title", "")).lower()
                or search_lc in str(r.get("body", "")).lower()
            )
            and (tag_f is None or tag_f in [str(t) for t in r.get("tags", [])])
            and (network_f is None or not r.get("networks") or network_f in [str(n) for n in r.get("networks", [])])
        ]
    items.sort(key=lambda r: int(r.get("use_count", 0)), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "replies": items[offset : offset + limit],
        "limit": limit,
        "offset": offset,
    }
