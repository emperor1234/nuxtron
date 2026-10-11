"""Social/Inbox use cases: list messages."""

from __future__ import annotations
from ..constants import LOCK_NOT_HELD, REPLY_NOT_FOUND
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..runtime import ContextRuntime
from ..schemas import InternalNoteRequest
from ..schemas import LockRequest
from .audit import helper_build_alerts
from .audit import helper_delivery_readiness_for
from .audit import helper_get_message
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_list_messages(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=40)] = None,
    network: Annotated[str | None, Query(max_length=40)] = None,
    message_type: Annotated[str | None, Query(max_length=40)] = None,
    sentiment: Annotated[str | None, Query(max_length=20)] = None,
    assigned_to: Annotated[str | None, Query(max_length=160)] = None,
    unread_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """ADDED: List inbox messages with rich filtering (§3.1.3 Inbox Views)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:list", 240, 60)
    status_f = status.strip().lower() if status else None
    network_f = network.strip().lower() if network else None
    type_f = message_type.strip().lower() if message_type else None
    sentiment_f = sentiment.strip().lower() if sentiment else None
    assigned_f = assigned_to.strip() if assigned_to else None
    with runtime._lock:
        items = [
            m.copy()
            for m in runtime.messages_memory
            if m.get("tenant_id") == auth.tenant_id
            and (status_f is None or m.get("status") == status_f)
            and (network_f is None or m.get("network") == network_f)
            and (type_f is None or m.get("message_type") == type_f)
            and (sentiment_f is None or m.get("sentiment") == sentiment_f)
            and (assigned_f is None or m.get("assigned_to") == assigned_f)
            and (not unread_only or not m.get("read", False))
        ]
    items.sort(key=lambda m: int(m.get("priority_score", 0)), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "messages": items[offset : offset + limit],
        "limit": limit,
        "offset": offset,
    }


def execute_get_message(runtime: ContextRuntime, message_id: int, auth: AuthDep) -> dict[str, Any]:
    """ADDED: Get a single message with thread, notes, lock status, and suggested replies."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:get", 300, 60)
    message = helper_get_message(runtime, auth.tenant_id, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
    with runtime._lock:
        for m in runtime.messages_memory:
            if m.get("tenant_id") == auth.tenant_id and m.get("id") == message_id and (not m.get("read")):
                m["read"] = True
                m["read_at"] = datetime.now(UTC).isoformat()
                message = m.copy()
                break
    thread: list[dict[str, Any]] = []
    if message.get("parent_message_id"):
        with runtime._lock:
            thread = [
                m.copy()
                for m in runtime.messages_memory
                if m.get("tenant_id") == auth.tenant_id
                and m.get("parent_message_id") == message.get("parent_message_id")
                and (m.get("id") != message_id)
            ]
    with runtime._lock:
        notes = [
            n.copy()
            for n in runtime.notes_memory
            if n.get("tenant_id") == auth.tenant_id and n.get("message_id") == message_id
        ]
    with runtime._lock:
        lock_info = next(
            (
                lk.copy()
                for lk in runtime.locks_memory
                if lk.get("tenant_id") == auth.tenant_id and lk.get("message_id") == message_id
            ),
            None,
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "message": message,
        "thread": thread,
        "notes": notes,
        "notes_count": len(notes),
        "lock": lock_info,
        "is_locked": lock_info is not None,
    }


def execute_add_note(
    runtime: ContextRuntime, message_id: int, payload: InternalNoteRequest, auth: AuthDep
) -> dict[str, Any]:
    """ADDED: Add an internal note to a message — never visible to customers (§3.1.3)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:notes:add", 180, 60)
    if helper_get_message(runtime, auth.tenant_id, message_id) is None:
        raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
    with runtime._lock:
        note: dict[str, Any] = {
            "id": len(runtime.notes_memory) + 1,
            "tenant_id": auth.tenant_id,
            "message_id": message_id,
            "author": payload.author.strip(),
            "note": payload.note,
            "created_at": datetime.now(UTC).isoformat(),
        }
        runtime.notes_memory.append(note)
    return {"status": "ok", "tenant_id": auth.tenant_id, "note": note.copy()}


def execute_list_notes(runtime: ContextRuntime, message_id: int, auth: AuthDep) -> dict[str, Any]:
    """ADDED: List internal notes for a message."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:notes:list", 240, 60)
    if helper_get_message(runtime, auth.tenant_id, message_id) is None:
        raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
    with runtime._lock:
        items = [
            n.copy()
            for n in runtime.notes_memory
            if n.get("tenant_id") == auth.tenant_id and n.get("message_id") == message_id
        ]
    items.sort(key=lambda n: str(n.get("created_at", "")))
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "notes": items}


def execute_acquire_lock(
    runtime: ContextRuntime, message_id: int, payload: LockRequest, auth: AuthDep
) -> dict[str, Any]:
    """
    ADDED: Acquire a collision-prevention lock before composing a reply (§3.1.3).
    Returns 409 if another team member already holds the lock.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:lock", 300, 60)
    if helper_get_message(runtime, auth.tenant_id, message_id) is None:
        raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
    with runtime._lock:
        existing_lock = next(
            (
                lk
                for lk in runtime.locks_memory
                if lk.get("tenant_id") == auth.tenant_id and lk.get("message_id") == message_id
            ),
            None,
        )
        lock_record: dict[str, Any]
        if existing_lock and existing_lock.get("locked_by") != payload.locked_by:
            raise HTTPException(
                status_code=409,
                detail=f"Message already locked by {existing_lock.get('locked_by')}. Collision detected.",
            )
        if existing_lock:
            existing_lock["locked_at"] = datetime.now(UTC).isoformat()
            lock_record = existing_lock.copy()
        else:
            lock_record = {
                "id": len(runtime.locks_memory) + 1,
                "tenant_id": auth.tenant_id,
                "message_id": message_id,
                "locked_by": payload.locked_by.strip(),
                "locked_at": datetime.now(UTC).isoformat(),
            }
            runtime.locks_memory.append(lock_record)
    return {"status": "ok", "tenant_id": auth.tenant_id, "lock": lock_record, "collision_detected": False}


def execute_release_lock(
    runtime: ContextRuntime,
    message_id: int,
    locked_by: Annotated[str, Query(min_length=1, max_length=160)],
    auth: AuthDep,
) -> dict[str, Any]:
    """ADDED: Release the collision-prevention lock after composing/sending a reply."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:unlock", 300, 60)
    with runtime._lock:
        index = next(
            (
                i
                for i, lk in enumerate(runtime.locks_memory)
                if lk.get("tenant_id") == auth.tenant_id
                and lk.get("message_id") == message_id
                and (lk.get("locked_by") == locked_by)
            ),
            None,
        )
        if index is None:
            raise HTTPException(status_code=404, detail=LOCK_NOT_HELD)
        runtime.locks_memory.pop(index)
    return {"status": "ok", "tenant_id": auth.tenant_id, "message_id": message_id, "released": True}


def execute_inbox_stats(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """ADDED: Inbox summary — total, unread, by status, by type, by sentiment, avg response time."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:stats", 120, 60)
    with runtime._lock:
        messages = [m for m in runtime.messages_memory if m.get("tenant_id") == auth.tenant_id]
    total = len(messages)
    unread = sum((1 for m in messages if not m.get("read", False)))
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_sentiment: dict[str, int] = {}
    by_network: dict[str, int] = {}
    replied = sum((1 for m in messages if m.get("replied", False)))
    for m in messages:
        s = str(m.get("status", "pending"))
        by_status[s] = by_status.get(s, 0) + 1
        t = str(m.get("message_type", "conversation"))
        by_type[t] = by_type.get(t, 0) + 1
        sent = str(m.get("sentiment", "neutral"))
        by_sentiment[sent] = by_sentiment.get(sent, 0) + 1
        net = str(m.get("network", "unknown"))
        by_network[net] = by_network.get(net, 0) + 1
    avg_priority = round(sum((int(m.get("priority_score", 0)) for m in messages)) / total, 1) if total else 0.0
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "generatedAt": datetime.now(UTC).isoformat(),
        "total": total,
        "unread": unread,
        "replied": replied,
        "replyRate": round(replied / total, 4) if total else 0.0,
        "avgPriorityScore": avg_priority,
        "byStatus": by_status,
        "byMessageType": by_type,
        "bySentiment": by_sentiment,
        "byNetwork": by_network,
    }


def execute_mention_alerts(
    runtime: ContextRuntime,
    auth: AuthDep,
    severity: Annotated[str | None, Query(max_length=20)] = None,
    unresolved_only: Annotated[bool, Query()] = True,
) -> dict[str, Any]:
    """Return mention-driven alerts and other urgent inbound messages for triage."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:mentions:alerts", 180, 60)
    alerts = helper_build_alerts(runtime, auth.tenant_id)
    severity_filter = severity.strip().lower() if severity else None
    if severity_filter:
        alerts = [item for item in alerts if str(item.get("severity")) == severity_filter]
    if unresolved_only:
        with runtime._lock:
            unresolved_ids = {
                int(m.get("id"))
                for m in runtime.messages_memory
                if m.get("tenant_id") == auth.tenant_id and str(m.get("status")) != "complete"
            }
        alerts = [item for item in alerts if int(item.get("message_id") or 0) in unresolved_ids]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(alerts), "alerts": alerts}


def execute_pending_approvals(
    runtime: ContextRuntime,
    auth: AuthDep,
    network: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """List approval-pending inbox responses for reviewers."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:approvals:pending", 240, 60)
    network_filter = network.strip().lower() if network else None
    with runtime._lock:
        items = [
            {
                "message_id": int(m.get("id") or 0),
                "network": m.get("network"),
                "author_handle": m.get("author_handle"),
                "message_type": m.get("message_type"),
                "priority_score": int(m.get("priority_score") or 0),
                "status": m.get("status"),
                "response_preview": m.get("last_response_preview"),
                "response_source": m.get("last_response_source"),
                "response_staged_by": m.get("last_response_by"),
                "response_staged_at": m.get("last_response_at"),
                "created_at": m.get("created_at"),
            }
            for m in runtime.messages_memory
            if m.get("tenant_id") == auth.tenant_id
            and str(m.get("status")) == "requires_approval"
            and str(m.get("last_response_preview", "")).strip()
            and (network_filter is None or str(m.get("network", "")).lower() == network_filter)
        ]
    for item in items:
        readiness = helper_delivery_readiness_for(str(item.get("network") or ""))
        item.update(readiness)
    items.sort(key=lambda item: str(item.get("response_staged_at", "")), reverse=True)
    total = len(items)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": total,
        "items": items[offset : offset + limit],
        "limit": limit,
        "offset": offset,
    }


def execute_list_delivery_failures(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """List failed outbound inbox deliveries queued for retry operations."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:list", 180, 60)
    status_filter = status.strip().lower() if status else None
    with runtime._lock:
        items = [
            item.copy()
            for item in runtime.delivery_failures_memory
            if item.get("tenant_id") == auth.tenant_id
            and (status_filter is None or str(item.get("status", "")).lower() == status_filter)
        ]
    items.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "items": items[offset : offset + limit],
        "limit": limit,
        "offset": offset,
    }


def execute_list_delivery_failure_replay_runs(
    runtime: ContextRuntime,
    auth: AuthDep,
    network: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """List replay-pending operation runs for DLQ queue-audit visibility."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:replay-runs", 120, 60)
    network_filter = network.strip().lower() if network else None
    with runtime._lock:
        items = [
            item.copy()
            for item in runtime.delivery_replay_runs_memory
            if item.get("tenant_id") == auth.tenant_id
            and (network_filter is None or str(item.get("network_filter") or "").strip().lower() == network_filter)
        ]
    items.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "items": items[offset : offset + limit],
        "limit": limit,
        "offset": offset,
        "network_filter": network_filter,
    }


def execute_delete_saved_reply(runtime: ContextRuntime, reply_id: int, auth: AuthDep) -> dict[str, Any]:
    """ADDED: Delete a saved reply from the library."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:saved-replies:delete", 60, 60)
    with runtime._lock:
        index = next(
            (
                i
                for i, r in enumerate(runtime.saved_replies_memory)
                if r.get("tenant_id") == auth.tenant_id and r.get("id") == reply_id
            ),
            None,
        )
        if index is None:
            raise HTTPException(status_code=404, detail=REPLY_NOT_FOUND)
        runtime.saved_replies_memory.pop(index)
    return {"status": "ok", "tenant_id": auth.tenant_id, "reply_id": reply_id, "deleted": True}
