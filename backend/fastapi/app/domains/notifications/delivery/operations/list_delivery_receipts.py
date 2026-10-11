"""Notifications/Delivery use cases: list delivery receipts."""

from __future__ import annotations
from .....deps import AuthContext
from ..constants import AuthDep
from ..constants import NOTIFICATION_NOT_FOUND
from ..runtime import ContextRuntime
from ..services.get_default_preferences import _batch_notifications_for_digest
from ..services.get_default_preferences import _normalize_lower
from ..services.get_default_preferences import _parse_iso_timestamp
from ..services.get_default_preferences import _sse_message
from .fanout_slack import helper_stream_auth
from .get_preferences import helper_append_audit
from .get_preferences import helper_broadcast_snapshot
from .get_preferences import helper_get_preferences
from .get_preferences import helper_hydrate_tenant_notifications
from .get_preferences import helper_increment_unread_category_locked
from .get_preferences import helper_persist_deleted_notification
from .get_preferences import helper_persist_mark_all_read
from .get_preferences import helper_persist_read_state
from .get_preferences import helper_realtime_enabled_for_tenant
from .get_preferences import helper_snapshot_for_tenant
from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from typing import Annotated
from typing import Any
import asyncio


def execute_list_delivery_receipts(
    runtime: ContextRuntime,
    auth: AuthDep,
    notification_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:delivery-receipts:list", 180, 60)
    with runtime.memory_lock:
        items = [
            receipt.copy()
            for receipt in runtime._delivery_receipts_memory
            if receipt.get("tenant_id") == auth.tenant_id
            and (notification_id is None or receipt.get("notification_id") == notification_id)
        ]
    items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "receipts": items[offset : offset + limit],
        "limit": limit,
        "offset": offset,
    }


def execute_delivery_health_summary(
    runtime: ContextRuntime,
    auth: AuthDep,
    window_seconds: Annotated[int, Query(ge=60, le=604800)] = 86400,
    channel: Annotated[str | None, Query(max_length=40)] = None,
    delivery_status: Annotated[str | None, Query(max_length=40)] = None,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:delivery-health", 180, 60)
    now = datetime.now(UTC)
    cutoff = now.timestamp() - window_seconds
    channel_filter = channel.strip().lower() if channel else None
    status_filter = delivery_status.strip().lower() if delivery_status else None
    by_channel: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_channel_status: dict[str, dict[str, int]] = {}
    by_policy_decision: dict[str, int] = {}
    with runtime.memory_lock:
        items = [receipt for receipt in runtime._delivery_receipts_memory if receipt.get("tenant_id") == auth.tenant_id]
    windowed_items: list[dict[str, Any]] = []
    for item in items:
        created_ts = _parse_iso_timestamp(item.get("created_at", ""))
        if created_ts is None:
            continue
        if created_ts < cutoff:
            continue
        channel_value = str(item.get("channel", "unknown")).lower()
        status_value = str(item.get("delivery_status", "unknown")).lower()
        if channel_filter and channel_value != channel_filter:
            continue
        if status_filter and status_value != status_filter:
            continue
        windowed_items.append(item)
        channel_name = str(item.get("channel", "unknown"))
        status_name = str(item.get("delivery_status", "unknown"))
        by_channel[channel_name] = by_channel.get(channel_name, 0) + 1
        by_status[status_name] = by_status.get(status_name, 0) + 1
        channel_bucket = by_channel_status.setdefault(channel_name, {})
        channel_bucket[status_name] = channel_bucket.get(status_name, 0) + 1
        policy_decision_value = str(item.get("policy_decision") or "unknown")
        by_policy_decision[policy_decision_value] = by_policy_decision.get(policy_decision_value, 0) + 1
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "windowSeconds": window_seconds,
        "filters": {"channel": channel_filter, "deliveryStatus": status_filter},
        "generatedAt": now.isoformat(),
        "totalReceipts": len(windowed_items),
        "byChannel": by_channel,
        "byStatus": by_status,
        "byChannelStatus": by_channel_status,
        "byPolicyDecision": by_policy_decision,
    }


def execute_mark_notification_read(runtime: ContextRuntime, notification_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:read-one", 180, 60)
    helper_hydrate_tenant_notifications(runtime, auth.tenant_id)
    with runtime.memory_lock:
        item = next(
            (
                candidate
                for candidate in runtime.notifications_memory
                if candidate.get("id") == notification_id and candidate.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail=NOTIFICATION_NOT_FOUND)
        was_unread = not item.get("read", False)
        category = str(item.get("category") or "general")
        item["read"] = True
        item["read_at"] = datetime.now(UTC).isoformat()
        if was_unread:
            helper_increment_unread_category_locked(runtime, auth.tenant_id, category, -1)
    helper_persist_read_state(runtime, item)
    helper_append_audit(runtime, auth.tenant_id, "notification_read", notification_id)
    helper_broadcast_snapshot(runtime, auth.tenant_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "notification": item}


def execute_mark_notifications_read_all(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:read-all", 60, 60)
    helper_hydrate_tenant_notifications(runtime, auth.tenant_id)
    marked = 0
    now_iso = datetime.now(UTC).isoformat()
    unread_deltas: dict[str, int] = {}
    with runtime.memory_lock:
        for item in runtime.notifications_memory:
            if item.get("tenant_id") != auth.tenant_id or item.get("read"):
                continue
            category = _normalize_lower(item.get("category", "general"), "general")
            unread_deltas[category] = unread_deltas.get(category, 0) + 1
            item["read"] = True
            item["read_at"] = now_iso
            marked += 1
        for category, delta in unread_deltas.items():
            helper_increment_unread_category_locked(runtime, auth.tenant_id, category, -delta)
        helper_persist_mark_all_read(runtime, auth.tenant_id, now_iso)
    helper_append_audit(runtime, auth.tenant_id, "notifications_read_all")
    helper_broadcast_snapshot(runtime, auth.tenant_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "updated": marked}


def execute_delete_notification(runtime: ContextRuntime, notification_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:delete", 120, 60)
    helper_hydrate_tenant_notifications(runtime, auth.tenant_id)
    with runtime.memory_lock:
        index = next(
            (
                idx
                for idx, candidate in enumerate(runtime.notifications_memory)
                if candidate.get("id") == notification_id and candidate.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if index is None:
            raise HTTPException(status_code=404, detail=NOTIFICATION_NOT_FOUND)
        removed = runtime.notifications_memory.pop(index)
        if not removed.get("read", False):
            helper_increment_unread_category_locked(
                runtime, auth.tenant_id, str(removed.get("category") or "general"), -1
            )
    helper_persist_deleted_notification(runtime, removed)
    helper_append_audit(runtime, auth.tenant_id, "notification_deleted", notification_id)
    helper_broadcast_snapshot(runtime, auth.tenant_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted": True, "notification": removed}


def execute_get_notification_digest(
    runtime: ContextRuntime,
    auth: AuthDep,
    frequency: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    """
    ENHANCED: Get digest-formatted notification summary.
    Aggregates notifications by priority and category based on user's digest preference.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:digest", 120, 60)
    prefs = helper_get_preferences(runtime, auth.tenant_id)
    digest_freq = _normalize_lower(frequency or prefs.get("digest_frequency", "realtime"), "realtime")
    snapshot = helper_snapshot_for_tenant(runtime, auth.tenant_id, limit=limit)
    notifs = snapshot.get("notifications", [])
    digest_data = _batch_notifications_for_digest(notifs, digest_freq)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "digest_frequency": digest_freq,
        "digest": digest_data,
        "unreadTotal": snapshot["unreadTotal"],
    }


def execute_get_digest_batch_status(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    ENHANCED: Get digest delivery status for scheduled batch jobs.
    Returns next scheduled digest send times based on tenant preferences.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:batch-status", 120, 60)
    prefs = helper_get_preferences(runtime, auth.tenant_id)
    digest_freq = _normalize_lower(prefs.get("digest_frequency", "realtime"), "realtime")
    now = datetime.now(UTC)
    next_send = None
    if digest_freq == "daily":
        next_send = (now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()
    elif digest_freq == "weekly":
        days_ahead = 0 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_send = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "digest_frequency": digest_freq,
        "batchMode": "enabled" if digest_freq != "realtime" else "disabled",
        "nextScheduledSend": next_send,
        "currentTime": now.isoformat(),
    }


async def execute_stream_notifications(
    runtime: ContextRuntime, request: Request, auth: Annotated[AuthContext, Depends(helper_stream_auth)]
) -> StreamingResponse:
    """
    ENHANCED: Real-time notification stream via Server-Sent Events (SSE).
    Sends updates as notifications are created, deleted, or marked read.
    Accepts auth via query params (api_key / tenant_id) for EventSource compatibility.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:stream-connect", 300, 60)
    queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    subscriber = {"queue": queue, "loop": loop}
    with runtime.memory_lock:
        runtime.subscribers.setdefault(auth.tenant_id, []).append(subscriber)
    initial_message = _sse_message("notifications.snapshot", helper_snapshot_for_tenant(runtime, auth.tenant_id))
    realtime_disabled_message = _sse_message(
        "notifications.realtime-disabled", {"status": "ok", "tenant_id": auth.tenant_id, "realtime_enabled": False}
    )

    async def event_stream() -> AsyncIterator[str]:
        yield initial_message
        if not helper_realtime_enabled_for_tenant(runtime, auth.tenant_id):
            yield realtime_disabled_message
            return
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield message
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            with runtime.memory_lock:
                active_subscribers = [
                    item for item in runtime.subscribers.get(auth.tenant_id, []) if item is not subscriber
                ]
                if active_subscribers:
                    runtime.subscribers[auth.tenant_id] = active_subscribers
                else:
                    runtime.subscribers.pop(auth.tenant_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
