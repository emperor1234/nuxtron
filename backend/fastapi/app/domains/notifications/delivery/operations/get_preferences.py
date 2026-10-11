"""Notifications/Delivery use cases: get preferences."""

from __future__ import annotations
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..services.get_default_preferences import _get_default_preferences
from ..services.get_default_preferences import _normalize_lower
from ..services.get_default_preferences import _sanitize_muted_categories
from ..services.get_default_preferences import _sse_message
from datetime import UTC
from datetime import datetime
from typing import Any
import psycopg
import threading


def helper_get_preferences(runtime: ContextRuntime, tenant_id: str) -> dict[str, Any]:
    """Retrieve or create default preferences for a tenant."""
    with runtime.memory_lock:
        return next(
            (p.copy() for p in runtime._preferences_memory if p.get("tenant_id") == tenant_id),
            _get_default_preferences(tenant_id),
        )


def helper_db_enabled(runtime: ContextRuntime) -> bool:
    """Return whether DB persistence is configured and currently ready."""
    try:
        dsn = runtime._db_dsn_fn().strip()
    except Exception:
        return False
    return bool(dsn) and runtime._db_ready_fn()


def helper_rebuild_unread_category_counts_locked(runtime: ContextRuntime, tenant_id: str) -> None:
    """Recompute unread category counters for a tenant from in-memory notifications."""
    counts: dict[str, int] = {}
    for item in runtime.notifications_memory:
        if item.get("tenant_id") != tenant_id or item.get("read", False):
            continue
        category = _normalize_lower(item.get("category", "general"), "general")
        counts[category] = counts.get(category, 0) + 1
    runtime.unread_by_tenant_category[tenant_id] = counts


def helper_increment_unread_category_locked(runtime: ContextRuntime, tenant_id: str, category: str, delta: int) -> None:
    """Apply a delta to unread category counters for a tenant."""
    if delta == 0:
        return
    normalized_category = _normalize_lower(category, "general")
    tenant_counts = runtime.unread_by_tenant_category.setdefault(tenant_id, {})
    updated = tenant_counts.get(normalized_category, 0) + delta
    if updated > 0:
        tenant_counts[normalized_category] = updated
    else:
        tenant_counts.pop(normalized_category, None)


def helper_ensure_notifications_table(runtime: ContextRuntime) -> None:
    """Create notification persistence table once when DB mode is enabled."""
    if runtime.db_bootstrap["done"]:
        return
    if not helper_db_enabled(runtime):
        return
    with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
        cur.execute(
            "\n                create table if not exists notifications_feed (\n                    id bigserial primary key,\n                    tenant_id text not null,\n                    title text not null,\n                    message text not null,\n                    category text not null,\n                    priority text not null,\n                    is_read boolean not null default false,\n                    read_at timestamptz,\n                    created_at timestamptz not null default now(),\n                    source text not null default 'api'\n                )\n                "
        )
        cur.execute(
            "\n                create index if not exists idx_notifications_feed_tenant_created\n                on notifications_feed (tenant_id, created_at desc)\n                "
        )
        cur.execute(
            "\n                create index if not exists idx_notifications_feed_tenant_unread\n                on notifications_feed (tenant_id, is_read)\n                "
        )
    runtime.db_bootstrap["done"] = True


def helper_hydrate_tenant_notifications(runtime: ContextRuntime, tenant_id: str) -> None:
    """Load persisted notifications into memory once per tenant to preserve unread counts after restarts."""
    with runtime.memory_lock:
        if tenant_id in runtime.hydrated_tenants:
            return
        tenant_lock = runtime.tenant_hydration_locks.setdefault(tenant_id, threading.Lock())
    with tenant_lock:
        if tenant_id in runtime.hydrated_tenants:
            return
        if not helper_db_enabled(runtime):
            with runtime.memory_lock:
                runtime.hydrated_tenants.add(tenant_id)
            return
        helper_ensure_notifications_table(runtime)
        with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                "\n                    select\n                        id,\n                        title,\n                        message,\n                        category,\n                        priority,\n                        is_read,\n                        read_at,\n                        created_at,\n                        source\n                    from notifications_feed\n                    where tenant_id = %s\n                    order by created_at desc\n                    limit 1000\n                    ",
                (tenant_id,),
            )
            rows = cur.fetchall()
        with runtime.memory_lock:
            known_db_ids: set[int] = set()
            for item in runtime.notifications_memory:
                if item.get("tenant_id") != tenant_id:
                    continue
                raw_db_id = item.get("db_id")
                if raw_db_id is None:
                    continue
                try:
                    known_db_ids.add(int(raw_db_id))
                except (TypeError, ValueError):
                    continue
            next_id = max((int(item.get("id", 0) or 0) for item in runtime.notifications_memory), default=0) + 1
            for row in rows:
                db_id = int(row[0])
                if db_id in known_db_ids:
                    continue
                runtime.notifications_memory.append(
                    {
                        "id": next_id,
                        "db_id": db_id,
                        "tenant_id": tenant_id,
                        "title": str(row[1]),
                        "message": str(row[2]),
                        "category": str(row[3]),
                        "priority": str(row[4]),
                        "read": bool(row[5]),
                        "read_at": row[6].isoformat() if row[6] is not None else None,
                        "created_at": row[7].isoformat(),
                        "source": str(row[8] or "api"),
                        "persistence": "postgres",
                    }
                )
                next_id += 1
            helper_rebuild_unread_category_counts_locked(runtime, tenant_id)
            runtime.hydrated_tenants.add(tenant_id)


def helper_persist_created_notification(runtime: ContextRuntime, item: dict[str, Any]) -> None:
    """Persist newly created notifications to DB when enabled."""
    if not helper_db_enabled(runtime):
        return
    helper_ensure_notifications_table(runtime)
    with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
        cur.execute(
            "\n                insert into notifications_feed\n                (tenant_id, title, message, category, priority, is_read, read_at, created_at, source)\n                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)\n                returning id\n                ",
            (
                str(item.get("tenant_id") or ""),
                str(item.get("title") or ""),
                str(item.get("message") or ""),
                str(item.get("category") or "general"),
                str(item.get("priority") or "info"),
                bool(item.get("read", False)),
                item.get("read_at"),
                item.get("created_at"),
                str(item.get("source") or "api"),
            ),
        )
        row = cur.fetchone()
    if row:
        item["db_id"] = int(row[0])
        item["persistence"] = "postgres"


def helper_persist_read_state(runtime: ContextRuntime, item: dict[str, Any]) -> None:
    """Persist read status updates to DB for a single notification."""
    if not helper_db_enabled(runtime):
        return
    db_id = item.get("db_id")
    if db_id is None:
        return
    with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
        cur.execute(
            "\n                update notifications_feed\n                set is_read = %s, read_at = %s\n                where id = %s and tenant_id = %s\n                ",
            (bool(item.get("read", False)), item.get("read_at"), int(db_id), str(item.get("tenant_id") or "")),
        )


def helper_persist_mark_all_read(runtime: ContextRuntime, tenant_id: str, read_at: str) -> None:
    """Persist mark-all-read changes to DB in a single statement."""
    if not helper_db_enabled(runtime):
        return
    with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
        cur.execute(
            "\n                update notifications_feed\n                set is_read = true, read_at = %s\n                where tenant_id = %s and is_read = false\n                ",
            (read_at, tenant_id),
        )


def helper_persist_deleted_notification(runtime: ContextRuntime, item: dict[str, Any]) -> None:
    """Delete persisted notification when a record is dismissed."""
    if not helper_db_enabled(runtime):
        return
    db_id = item.get("db_id")
    if db_id is None:
        return
    with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
        cur.execute(
            "delete from notifications_feed where id = %s and tenant_id = %s",
            (int(db_id), str(item.get("tenant_id") or "")),
        )


def helper_snapshot_for_tenant(
    runtime: ContextRuntime,
    tenant_id: str,
    category: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Get filtered, paginated notifications for a tenant, respecting preferences."""
    helper_hydrate_tenant_notifications(runtime, tenant_id)
    prefs = helper_get_preferences(runtime, tenant_id)
    muted = set(_sanitize_muted_categories(prefs.get("muted_categories", [])))
    category_filter = _normalize_lower(category) if category is not None else None
    priority_filter = _normalize_lower(priority) if priority is not None else None
    with runtime.memory_lock:
        all_items = [
            item.copy()
            for item in runtime.notifications_memory
            if item.get("tenant_id") == tenant_id
            and _normalize_lower(item.get("category", "general"), "general") not in muted
        ]
        filtered_items = [
            item
            for item in all_items
            if (category_filter is None or _normalize_lower(item.get("category")) == category_filter)
            and (priority_filter is None or _normalize_lower(item.get("priority", "info"), "info") == priority_filter)
        ]
    all_items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    filtered_items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    unread_total = sum((1 for item in all_items if not item.get("read", False)))
    unread_filtered = sum((1 for item in filtered_items if not item.get("read", False)))
    total = len(filtered_items)
    page_items = filtered_items[offset : offset + limit]
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "notifications": page_items,
        "unreadCount": unread_filtered,
        "unreadTotal": unread_total,
        "unreadCountFiltered": unread_filtered,
        "total": total,
        "totalAll": len(all_items),
        "limit": limit,
        "offset": offset,
    }


def helper_unread_total_for_tenant(runtime: ContextRuntime, tenant_id: str) -> int:
    """Return unread count without building/sorting a full snapshot payload."""
    helper_hydrate_tenant_notifications(runtime, tenant_id)
    prefs = helper_get_preferences(runtime, tenant_id)
    muted = set(_sanitize_muted_categories(prefs.get("muted_categories", [])))
    with runtime.memory_lock:
        if tenant_id not in runtime.unread_by_tenant_category:
            helper_rebuild_unread_category_counts_locked(runtime, tenant_id)
        tenant_counts = runtime.unread_by_tenant_category.get(tenant_id, {})
        return sum((count for category, count in tenant_counts.items() if category not in muted))


def helper_realtime_enabled_for_tenant(runtime: ContextRuntime, tenant_id: str) -> bool:
    """Check if realtime is enabled for tenant."""
    prefs = helper_get_preferences(runtime, tenant_id)
    return bool(prefs.get("realtime_enabled", True))


def helper_append_audit(
    runtime: ContextRuntime, tenant_id: str, action: str, notification_id: int | None = None
) -> None:
    """Record audit log entry."""
    with runtime.memory_lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "notification_id": notification_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "notifications-router",
            }
        )


def helper_append_delivery_receipt(
    runtime: ContextRuntime,
    tenant_id: str,
    notification_id: int,
    channel: str,
    provider: str,
    delivery_status: str,
    reason: str | None = None,
    external_id: str | None = None,
    policy_version: str = "v1-priority-routing",
    policy_decision: str | None = None,
) -> dict[str, Any]:
    with runtime.memory_lock:
        receipt = {
            "id": len(runtime._delivery_receipts_memory) + 1,
            "tenant_id": tenant_id,
            "notification_id": notification_id,
            "channel": channel,
            "provider": provider,
            "delivery_status": delivery_status,
            "reason": reason,
            "external_id": external_id,
            "policy_version": policy_version,
            "policy_decision": policy_decision,
            "created_at": datetime.now(UTC).isoformat(),
        }
        runtime._delivery_receipts_memory.append(receipt)
    return receipt


def helper_broadcast_snapshot(runtime: ContextRuntime, tenant_id: str) -> None:
    """Broadcast updated notification snapshot to connected SSE clients."""
    if not helper_realtime_enabled_for_tenant(runtime, tenant_id):
        return
    payload = helper_snapshot_for_tenant(runtime, tenant_id)
    message = _sse_message("notifications.updated", payload)
    with runtime.memory_lock:
        tenant_subscribers = list(runtime.subscribers.get(tenant_id, []))
    for subscriber in tenant_subscribers:
        try:
            subscriber["loop"].call_soon_threadsafe(subscriber["queue"].put_nowait, message)
        except RuntimeError:
            continue


def execute_get_preferences(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:preferences:get", 120, 60)
    prefs = helper_get_preferences(runtime, auth.tenant_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "preferences": prefs}
