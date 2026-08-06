# pyright: reportUnusedFunction=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false

import asyncio
import hmac
import json
import os
import threading
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import httpx
import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
NOTIFICATION_NOT_FOUND = 'Notification not found.'


# ENHANCED: priority field added for severity-based routing (info/warning/error/success/critical)
PRIORITY_VALUES = {'info', 'warning', 'error', 'success', 'critical'}
DIGEST_FREQUENCY_VALUES = {'realtime', 'daily', 'weekly'}


class NotificationCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=4000)
    category: str = Field(default='general', min_length=1, max_length=40)
    # ENHANCED: priority enables severity-based display (info/warning/error/success/critical)
    priority: str = Field(default='info', min_length=1, max_length=20)


# ENHANCED: per-tenant notification preferences (Part 4 §18 Core — notification_preferences table)
class NotificationPreferencesRequest(BaseModel):
    muted_categories: list[str] = Field(default_factory=list, max_length=50)
    email_enabled: bool = True
    sms_enabled: bool = False
    slack_enabled: bool = False
    realtime_enabled: bool = True
    digest_frequency: str = Field(default='realtime', max_length=20)  # realtime | daily | weekly


# ── Extracted helpers (reduced factory complexity) ────────────────────────────

def _get_default_preferences(tenant_id: str) -> dict[str, Any]:
    """Return default notification preferences for a tenant."""
    return {
        'tenant_id': tenant_id,
        'muted_categories': [],
        'email_enabled': True,
        'sms_enabled': False,
        'slack_enabled': False,
        'realtime_enabled': True,
        'digest_frequency': 'realtime',
    }


def _sse_message(event: str, payload: dict[str, Any]) -> str:
    """Format a server-sent event message."""
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def _normalize_lower(value: object, fallback: str = '') -> str:
    """Normalize string-like values to lowercase without mutating caller data."""
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned:
            return cleaned
    return fallback


def _sanitize_muted_categories(raw_categories: list[str]) -> list[str]:
    """Deduplicate and normalize muted categories while preserving insertion order."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for category in raw_categories:
        normalized = _normalize_lower(category)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _safe_notification_id(notification: dict[str, Any]) -> int:
    """Safely coerce notification id to int for downstream receipt records."""
    try:
        return int(notification.get('id', 0) or 0)
    except (TypeError, ValueError):
        return 0


def _parse_iso_timestamp(value: object) -> float | None:
    """Parse ISO datetime values robustly, accepting trailing Z as UTC."""
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace('Z', '+00:00') if value.endswith('Z') else value
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None


def _policy_reason(enabled: bool, policy_match: bool, policy_name: str) -> str:
    """Return a normalized policy reason token for receipt metadata."""
    if not enabled:
        return f'{policy_name}-disabled-by-preference'
    if not policy_match:
        return f'{policy_name}-suppressed-by-priority-policy'
    return f'{policy_name}-eligible-by-policy'


def _batch_notifications_for_digest(
    notifications: list[dict[str, Any]],
    digest_frequency: str,
) -> dict[str, Any]:
    """
    ENHANCED: Aggregate notifications by digest frequency (realtime/daily/weekly).
    Returns a digest summary with notification counts by priority.
    """
    if digest_frequency == 'realtime':
        return {'batch_mode': 'realtime', 'notifications': notifications}
    
    # Group by priority for digest summary
    by_priority: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for notif in notifications:
        priority = _normalize_lower(notif.get('priority', 'info'), 'info')
        category = _normalize_lower(notif.get('category', 'general'), 'general')
        by_priority[priority] = by_priority.get(priority, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    
    return {
        'batch_mode': digest_frequency,
        'notifications': notifications,
        'summary': {
            'total': len(notifications),
            'by_priority': by_priority,
            'by_category': by_category,
        }
    }


def _apply_delivery_backoff(attempt: int, base_delay: int = 5) -> int:
    """
    ENHANCED: Calculate exponential backoff delay in seconds.
    For retry scheduling on failed deliveries.
    """
    return min(base_delay * (2 ** attempt), 3600)  # Cap at 1 hour


def create_notifications_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    notifications_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    notification_preferences_memory: list[dict[str, Any]] | None = None,
    notification_delivery_receipts_memory: list[dict[str, Any]] | None = None,
    db_ready_fn: Callable[[], bool] | None = None,
    db_dsn_fn: Callable[[], str] | None = None,
) -> APIRouter:
    """
    Create notification router with preferences support.
    
    Complexity kept low by extracting helper logic into module-level functions.
    """
    _preferences_memory: list[dict[str, Any]] = notification_preferences_memory if notification_preferences_memory is not None else []
    _delivery_receipts_memory: list[dict[str, Any]] = notification_delivery_receipts_memory if notification_delivery_receipts_memory is not None else []
    _db_ready_fn = db_ready_fn if db_ready_fn is not None else (lambda: False)
    _db_dsn_fn = db_dsn_fn if db_dsn_fn is not None else (lambda: '')
    router = APIRouter()
    memory_lock = threading.Lock()
    subscribers: dict[str, list[dict[str, Any]]] = {}
    unread_by_tenant_category: dict[str, dict[str, int]] = {}
    db_bootstrap = {'done': False}
    hydrated_tenants: set[str] = set()
    tenant_hydration_locks: dict[str, threading.Lock] = {}

    # ── Inline helpers (scoped to this factory instance) ─────────────────────
    
    def _get_preferences(tenant_id: str) -> dict[str, Any]:
        """Retrieve or create default preferences for a tenant."""
        with memory_lock:
            return next(
                (p.copy() for p in _preferences_memory if p.get('tenant_id') == tenant_id),
                _get_default_preferences(tenant_id),
            )

    def _db_enabled() -> bool:
        """Return whether DB persistence is configured and currently ready."""
        try:
            dsn = _db_dsn_fn().strip()
        except Exception:
            return False
        return bool(dsn) and _db_ready_fn()

    def _rebuild_unread_category_counts_locked(tenant_id: str) -> None:
        """Recompute unread category counters for a tenant from in-memory notifications."""
        counts: dict[str, int] = {}
        for item in notifications_memory:
            if item.get('tenant_id') != tenant_id or item.get('read', False):
                continue
            category = _normalize_lower(item.get('category', 'general'), 'general')
            counts[category] = counts.get(category, 0) + 1
        unread_by_tenant_category[tenant_id] = counts

    def _increment_unread_category_locked(tenant_id: str, category: str, delta: int) -> None:
        """Apply a delta to unread category counters for a tenant."""
        if delta == 0:
            return
        normalized_category = _normalize_lower(category, 'general')
        tenant_counts = unread_by_tenant_category.setdefault(tenant_id, {})
        updated = tenant_counts.get(normalized_category, 0) + delta
        if updated > 0:
            tenant_counts[normalized_category] = updated
        else:
            tenant_counts.pop(normalized_category, None)

    def _ensure_notifications_table() -> None:
        """Create notification persistence table once when DB mode is enabled."""
        if db_bootstrap['done']:
            return
        if not _db_enabled():
            return
        with psycopg.connect(_db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                create table if not exists notifications_feed (
                    id bigserial primary key,
                    tenant_id text not null,
                    title text not null,
                    message text not null,
                    category text not null,
                    priority text not null,
                    is_read boolean not null default false,
                    read_at timestamptz,
                    created_at timestamptz not null default now(),
                    source text not null default 'api'
                )
                """
            )
            cur.execute(
                """
                create index if not exists idx_notifications_feed_tenant_created
                on notifications_feed (tenant_id, created_at desc)
                """
            )
            cur.execute(
                """
                create index if not exists idx_notifications_feed_tenant_unread
                on notifications_feed (tenant_id, is_read)
                """
            )
        db_bootstrap['done'] = True

    def _hydrate_tenant_notifications(tenant_id: str) -> None:
        """Load persisted notifications into memory once per tenant to preserve unread counts after restarts."""
        with memory_lock:
            if tenant_id in hydrated_tenants:
                return
            tenant_lock = tenant_hydration_locks.setdefault(tenant_id, threading.Lock())

        with tenant_lock:
            if tenant_id in hydrated_tenants:
                return
            if not _db_enabled():
                with memory_lock:
                    hydrated_tenants.add(tenant_id)
                return

            _ensure_notifications_table()
            with psycopg.connect(_db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        id,
                        title,
                        message,
                        category,
                        priority,
                        is_read,
                        read_at,
                        created_at,
                        source
                    from notifications_feed
                    where tenant_id = %s
                    order by created_at desc
                    limit 1000
                    """,
                    (tenant_id,),
                )
                rows = cur.fetchall()

            with memory_lock:
                known_db_ids: set[int] = set()
                for item in notifications_memory:
                    if item.get('tenant_id') != tenant_id:
                        continue
                    raw_db_id = item.get('db_id')
                    if raw_db_id is None:
                        continue
                    try:
                        known_db_ids.add(int(raw_db_id))
                    except (TypeError, ValueError):
                        continue
                next_id = (max((int(item.get('id', 0) or 0) for item in notifications_memory), default=0) + 1)
                for row in rows:
                    db_id = int(row[0])
                    if db_id in known_db_ids:
                        continue
                    notifications_memory.append({
                        'id': next_id,
                        'db_id': db_id,
                        'tenant_id': tenant_id,
                        'title': str(row[1]),
                        'message': str(row[2]),
                        'category': str(row[3]),
                        'priority': str(row[4]),
                        'read': bool(row[5]),
                        'read_at': row[6].isoformat() if row[6] is not None else None,
                        'created_at': row[7].isoformat(),
                        'source': str(row[8] or 'api'),
                        # ENHANCED: persisted notifications are hydrated as DB-backed records.
                        'persistence': 'postgres',
                    })
                    next_id += 1
                _rebuild_unread_category_counts_locked(tenant_id)
                hydrated_tenants.add(tenant_id)

    def _persist_created_notification(item: dict[str, Any]) -> None:
        """Persist newly created notifications to DB when enabled."""
        if not _db_enabled():
            return
        _ensure_notifications_table()
        with psycopg.connect(_db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into notifications_feed
                (tenant_id, title, message, category, priority, is_read, read_at, created_at, source)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    str(item.get('tenant_id') or ''),
                    str(item.get('title') or ''),
                    str(item.get('message') or ''),
                    str(item.get('category') or 'general'),
                    str(item.get('priority') or 'info'),
                    bool(item.get('read', False)),
                    item.get('read_at'),
                    item.get('created_at'),
                    str(item.get('source') or 'api'),
                ),
            )
            row = cur.fetchone()
        if row:
            item['db_id'] = int(row[0])
            item['persistence'] = 'postgres'

    def _persist_read_state(item: dict[str, Any]) -> None:
        """Persist read status updates to DB for a single notification."""
        if not _db_enabled():
            return
        db_id = item.get('db_id')
        if db_id is None:
            return
        with psycopg.connect(_db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                update notifications_feed
                set is_read = %s, read_at = %s
                where id = %s and tenant_id = %s
                """,
                (
                    bool(item.get('read', False)),
                    item.get('read_at'),
                    int(db_id),
                    str(item.get('tenant_id') or ''),
                ),
            )

    def _persist_mark_all_read(tenant_id: str, read_at: str) -> None:
        """Persist mark-all-read changes to DB in a single statement."""
        if not _db_enabled():
            return
        with psycopg.connect(_db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                update notifications_feed
                set is_read = true, read_at = %s
                where tenant_id = %s and is_read = false
                """,
                (read_at, tenant_id),
            )

    def _persist_deleted_notification(item: dict[str, Any]) -> None:
        """Delete persisted notification when a record is dismissed."""
        if not _db_enabled():
            return
        db_id = item.get('db_id')
        if db_id is None:
            return
        with psycopg.connect(_db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                "delete from notifications_feed where id = %s and tenant_id = %s",
                (int(db_id), str(item.get('tenant_id') or '')),
            )

    def _snapshot_for_tenant(
        tenant_id: str,
        category: str | None = None,
        priority: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get filtered, paginated notifications for a tenant, respecting preferences."""
        _hydrate_tenant_notifications(tenant_id)
        prefs = _get_preferences(tenant_id)
        muted = set(_sanitize_muted_categories(prefs.get('muted_categories', [])))
        category_filter = _normalize_lower(category) if category is not None else None
        priority_filter = _normalize_lower(priority) if priority is not None else None
        with memory_lock:
            all_items = [
                item.copy() for item in notifications_memory
                if item.get('tenant_id') == tenant_id
                and _normalize_lower(item.get('category', 'general'), 'general') not in muted
            ]
            filtered_items = [
                item
                for item in all_items
                if (category_filter is None or _normalize_lower(item.get('category')) == category_filter)
                # ENHANCED: optional priority filter
                and (priority_filter is None or _normalize_lower(item.get('priority', 'info'), 'info') == priority_filter)
            ]
        all_items.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        filtered_items.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        unread_total = sum(1 for item in all_items if not item.get('read', False))
        unread_filtered = sum(1 for item in filtered_items if not item.get('read', False))
        total = len(filtered_items)
        # ENHANCED: pagination support
        page_items = filtered_items[offset: offset + limit]
        return {
            'status': 'ok',
            'tenant_id': tenant_id,
            'notifications': page_items,
            # Backward-compatible field retained for existing consumers.
            'unreadCount': unread_filtered,
            # ENHANCED (additive): canonical unread for all (non-muted) notifications.
            'unreadTotal': unread_total,
            'unreadCountFiltered': unread_filtered,
            'total': total,
            # ENHANCED (additive): total before category/priority filters.
            'totalAll': len(all_items),
            'limit': limit,
            'offset': offset,
        }

    def _unread_total_for_tenant(tenant_id: str) -> int:
        """Return unread count without building/sorting a full snapshot payload."""
        _hydrate_tenant_notifications(tenant_id)
        prefs = _get_preferences(tenant_id)
        muted = set(_sanitize_muted_categories(prefs.get('muted_categories', [])))
        with memory_lock:
            if tenant_id not in unread_by_tenant_category:
                _rebuild_unread_category_counts_locked(tenant_id)
            tenant_counts = unread_by_tenant_category.get(tenant_id, {})
            return sum(
                count
                for category, count in tenant_counts.items()
                if category not in muted
            )

    def _realtime_enabled_for_tenant(tenant_id: str) -> bool:
        """Check if realtime is enabled for tenant."""
        prefs = _get_preferences(tenant_id)
        return bool(prefs.get('realtime_enabled', True))

    def _append_audit(tenant_id: str, action: str, notification_id: int | None = None) -> None:
        """Record audit log entry."""
        with memory_lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'notification_id': notification_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'notifications-router',
            })

    def _append_delivery_receipt(
        tenant_id: str,
        notification_id: int,
        channel: str,
        provider: str,
        delivery_status: str,
        reason: str | None = None,
        external_id: str | None = None,
        policy_version: str = 'v1-priority-routing',
        policy_decision: str | None = None,
    ) -> dict[str, Any]:
        with memory_lock:
            receipt = {
                'id': len(_delivery_receipts_memory) + 1,
                'tenant_id': tenant_id,
                'notification_id': notification_id,
                'channel': channel,
                'provider': provider,
                'delivery_status': delivery_status,
                'reason': reason,
                'external_id': external_id,
                # ENHANCED (additive): routing policy metadata improves cross-channel auditability.
                'policy_version': policy_version,
                'policy_decision': policy_decision,
                'created_at': datetime.now(UTC).isoformat(),
            }
            _delivery_receipts_memory.append(receipt)
        return receipt

    def _fanout_slack(notification: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        notification_id = _safe_notification_id(notification)
        webhook_url = os.getenv('SLACK_WEBHOOK_URL', '').strip()
        if not webhook_url:
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'slack',
                'slack-incoming-webhook',
                'queued',
                reason='SLACK_WEBHOOK_URL not configured',
            )

        body = {
            'text': (
                f"[{str(notification.get('priority', 'info')).upper()}] "
                f"{notification.get('title', 'Notification')}\n"
                f"{notification.get('message', '')}"
            ).strip()
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook_url, json=body)
                if response.is_success:
                    return _append_delivery_receipt(
                        tenant_id,
                        notification_id,
                        'slack',
                        'slack-incoming-webhook',
                        'sent',
                    )
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'slack',
                'slack-incoming-webhook',
                'queued-after-non-success',
            )
        except httpx.HTTPError:
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'slack',
                'slack-incoming-webhook',
                'queued-after-error',
            )

    def _fanout_email(notification: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        notification_id = _safe_notification_id(notification)
        api_key = os.getenv('RESEND_API_KEY', '').strip()
        from_email = os.getenv('RESEND_FROM_EMAIL', 'onboarding@nuxtron.local').strip()
        to_email = os.getenv('NOTIFICATION_EMAIL_TO', '').strip()
        api_base_url = os.getenv('RESEND_API_BASE_URL', 'https://api.resend.com').rstrip('/')
        if not api_key or not to_email:
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'email',
                'resend',
                'queued',
                reason='RESEND_API_KEY or NOTIFICATION_EMAIL_TO not configured',
            )

        body = {
            'from': from_email,
            'to': [to_email],
            'subject': f"[{str(notification.get('priority', 'info')).upper()}] {notification.get('title', 'Notification')}",
            'text': str(notification.get('message', '') or ''),
        }
        try:
            with httpx.Client(timeout=12.0) as client:
                response = client.post(
                    f'{api_base_url}/emails',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                    json=body,
                )
                if response.is_success:
                    try:
                        data = response.json()
                    except ValueError:
                        data = {}
                    return _append_delivery_receipt(
                        tenant_id,
                        notification_id,
                        'email',
                        'resend',
                        'sent',
                        external_id=str(data.get('id') or ''),
                    )
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'email',
                'resend',
                'queued-after-non-success',
            )
        except httpx.HTTPError:
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'email',
                'resend',
                'queued-after-error',
            )

    def _fanout_webhook(notification: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        notification_id = _safe_notification_id(notification)
        webhook_url = os.getenv('NOTIFICATION_WEBHOOK_URL', '').strip()
        webhook_token = os.getenv('NOTIFICATION_WEBHOOK_TOKEN', '').strip()
        if not webhook_url:
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'webhook',
                'generic-webhook',
                'queued',
                reason='NOTIFICATION_WEBHOOK_URL not configured',
            )

        headers = {'Content-Type': 'application/json'}
        if webhook_token:
            headers['Authorization'] = f'Bearer {webhook_token}'

        payload = {
            'event': 'notification.created',
            'tenant_id': tenant_id,
            'notification': notification,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook_url, headers=headers, json=payload)
                if response.is_success:
                    return _append_delivery_receipt(
                        tenant_id,
                        notification_id,
                        'webhook',
                        'generic-webhook',
                        'sent',
                    )
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'webhook',
                'generic-webhook',
                'queued-after-non-success',
            )
        except httpx.HTTPError:
            return _append_delivery_receipt(
                tenant_id,
                notification_id,
                'webhook',
                'generic-webhook',
                'queued-after-error',
            )

    def _fanout_notification(notification: dict[str, Any], prefs: dict[str, Any]) -> list[dict[str, Any]]:
        tenant_id = str(notification.get('tenant_id') or '')
        priority = _normalize_lower(notification.get('priority', 'info'), 'info')
        notification_id = _safe_notification_id(notification)
        receipts: list[dict[str, Any]] = []

        # ENHANCED: explicit policy routing metadata keeps channel decisions inspectable.
        slack_enabled = bool(prefs.get('slack_enabled', False))
        slack_policy_match = priority in {'warning', 'error', 'critical'}
        if slack_enabled and slack_policy_match:
            receipt = _fanout_slack(notification, tenant_id)
            receipt['policy_decision'] = _policy_reason(True, True, 'slack')
            receipts.append(receipt)
        else:
            receipts.append(
                _append_delivery_receipt(
                    tenant_id,
                    notification_id,
                    'slack',
                    'slack-incoming-webhook',
                    'skipped',
                    reason='channel disabled by preference or priority policy',
                    policy_decision=_policy_reason(slack_enabled, slack_policy_match, 'slack'),
                )
            )

        email_enabled = bool(prefs.get('email_enabled', True))
        email_policy_match = priority in {'error', 'critical'}
        if email_enabled and email_policy_match:
            receipt = _fanout_email(notification, tenant_id)
            receipt['policy_decision'] = _policy_reason(True, True, 'email')
            receipts.append(receipt)
        else:
            receipts.append(
                _append_delivery_receipt(
                    tenant_id,
                    notification_id,
                    'email',
                    'resend',
                    'skipped',
                    reason='channel disabled by preference or priority policy',
                    policy_decision=_policy_reason(email_enabled, email_policy_match, 'email'),
                )
            )

        webhook_enabled = True
        webhook_policy_match = priority == 'critical'
        if webhook_policy_match:
            receipt = _fanout_webhook(notification, tenant_id)
            receipt['policy_decision'] = _policy_reason(True, True, 'webhook')
            receipts.append(receipt)
        else:
            receipts.append(
                _append_delivery_receipt(
                    tenant_id,
                    notification_id,
                    'webhook',
                    'generic-webhook',
                    'skipped',
                    reason='webhook fan-out enabled for critical notifications only',
                    policy_decision=_policy_reason(webhook_enabled, webhook_policy_match, 'webhook'),
                )
            )

        return receipts

    def _broadcast_snapshot(tenant_id: str) -> None:
        """Broadcast updated notification snapshot to connected SSE clients."""
        if not _realtime_enabled_for_tenant(tenant_id):
            return
        payload = _snapshot_for_tenant(tenant_id)
        message = _sse_message('notifications.updated', payload)
        with memory_lock:
            tenant_subscribers = list(subscribers.get(tenant_id, []))
        for subscriber in tenant_subscribers:
            try:
                subscriber['loop'].call_soon_threadsafe(subscriber['queue'].put_nowait, message)
            except RuntimeError:
                continue

    async def _stream_auth(
        request: Request,
        api_key: Annotated[str | None, Query(alias='api_key')] = None,
        tenant_id: Annotated[str | None, Query(alias='tenant_id')] = None,
        authorization: Annotated[str | None, Header(alias='Authorization')] = None,
    ) -> AuthContext:
        # Preferred path: bearer token auth (works with programmatic/EventSource wrappers
        # that can send Authorization headers).
        if isinstance(authorization, str) and authorization.strip().lower().startswith('bearer '):
            return await require_auth(request=request, x_tenant_id=tenant_id, authorization=authorization)

        # Compatibility fallback for native EventSource clients that cannot set headers.
        # Keep this route-local fallback while preserving strict auth on all other endpoints.
        if api_key and tenant_id:
            expected = os.getenv('FASTAPI_API_KEY', 'change-this-fastapi-key').strip()
            if expected and hmac.compare_digest(api_key, expected):
                return AuthContext(tenant_id=tenant_id, auth_mode='api_key')

        raise HTTPException(status_code=401, detail='Missing or invalid stream authentication.')

    @router.get('/notifications')
    def list_notifications(
        auth: AuthDep,
        category: Annotated[str | None, Query(max_length=40)] = None,
        # ENHANCED: priority filter for severity-based views
        priority: Annotated[str | None, Query(max_length=20)] = None,
        # ENHANCED: pagination to prevent unbounded responses
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        # ENHANCED: category/priority filters + pagination; muted-category awareness via preferences.
        enforce_rate_limit(f'{auth.tenant_id}:notifications:list', 1200, 60)
        return _snapshot_for_tenant(auth.tenant_id, category=category, priority=priority, limit=limit, offset=offset)

    # ENHANCED: notification preferences CRUD (Part 4 §18 Core — notification_preferences table)
    @router.get('/notifications/preferences')
    def get_preferences(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:preferences:get', 120, 60)
        prefs = _get_preferences(auth.tenant_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'preferences': prefs}

    @router.put('/notifications/preferences', responses={422: {'description': 'Invalid digest frequency.'}})
    def update_preferences(
        payload: NotificationPreferencesRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:preferences:update', 60, 60)
        digest_frequency = _normalize_lower(payload.digest_frequency, 'realtime')
        if digest_frequency not in DIGEST_FREQUENCY_VALUES:
            raise HTTPException(status_code=422, detail='Invalid digest frequency.')
        muted_categories = _sanitize_muted_categories(payload.muted_categories)
        with memory_lock:
            existing = next(
                (p for p in _preferences_memory if p.get('tenant_id') == auth.tenant_id), None
            )
            if existing:
                existing.update({
                    'muted_categories': muted_categories,
                    'email_enabled': payload.email_enabled,
                    'sms_enabled': payload.sms_enabled,
                    'slack_enabled': payload.slack_enabled,
                    'realtime_enabled': payload.realtime_enabled,
                    'digest_frequency': digest_frequency,
                    'updated_at': datetime.now(UTC).isoformat(),
                })
                prefs = existing.copy()
            else:
                prefs = {
                    'tenant_id': auth.tenant_id,
                    'muted_categories': muted_categories,
                    'email_enabled': payload.email_enabled,
                    'sms_enabled': payload.sms_enabled,
                    'slack_enabled': payload.slack_enabled,
                    'realtime_enabled': payload.realtime_enabled,
                    'digest_frequency': digest_frequency,
                    'created_at': datetime.now(UTC).isoformat(),
                    'updated_at': datetime.now(UTC).isoformat(),
                }
                _preferences_memory.append(prefs)
                prefs = prefs.copy()

        _append_audit(auth.tenant_id, 'notification_preferences_updated')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'preferences': prefs}

    @router.get('/notifications/unread-count')
    def notification_unread_count(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:unread-count', 300, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            # ENHANCED: return canonical global unread count (non-muted, no view filter).
            'unreadCount': _unread_total_for_tenant(auth.tenant_id),
        }

    @router.post('/notifications')
    def create_notification(payload: NotificationCreateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:create', 120, 60)
        _hydrate_tenant_notifications(auth.tenant_id)
        # ENHANCED: validate priority against allowed values; default to 'info'
        safe_priority = _normalize_lower(payload.priority, 'info')
        if safe_priority not in PRIORITY_VALUES:
            safe_priority = 'info'
        safe_category = _normalize_lower(payload.category, 'general')
        with memory_lock:
            item = {
                'id': len(notifications_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title,
                'message': payload.message,
                'category': safe_category,
                # ENHANCED: priority field stored with each notification
                'priority': safe_priority,
                'read': False,
                'read_at': None,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'api',
                'persistence': 'memory-fallback',
            }
            notifications_memory.append(item)
            _increment_unread_category_locked(auth.tenant_id, safe_category, 1)

            _persist_created_notification(item)

        prefs = _get_preferences(auth.tenant_id)
        receipts = _fanout_notification(item, prefs)

        _append_audit(auth.tenant_id, 'notification_created', item['id'])
        _broadcast_snapshot(auth.tenant_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'notification': item, 'deliveryReceipts': receipts}

    @router.get('/notifications/delivery-receipts')
    def list_delivery_receipts(
        auth: AuthDep,
        notification_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:delivery-receipts:list', 180, 60)
        with memory_lock:
            items = [
                receipt.copy()
                for receipt in _delivery_receipts_memory
                if receipt.get('tenant_id') == auth.tenant_id
                and (notification_id is None or receipt.get('notification_id') == notification_id)
            ]
        items.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'receipts': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    @router.get('/notifications/delivery-health')
    def delivery_health_summary(
        auth: AuthDep,
        window_seconds: Annotated[int, Query(ge=60, le=604800)] = 86400,
        channel: Annotated[str | None, Query(max_length=40)] = None,
        delivery_status: Annotated[str | None, Query(max_length=40)] = None,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:delivery-health', 180, 60)
        now = datetime.now(UTC)
        cutoff = now.timestamp() - window_seconds
        channel_filter = channel.strip().lower() if channel else None
        status_filter = delivery_status.strip().lower() if delivery_status else None

        by_channel: dict[str, int] = {}
        by_status: dict[str, int] = {}
        by_channel_status: dict[str, dict[str, int]] = {}
        by_policy_decision: dict[str, int] = {}

        with memory_lock:
            items = [
                receipt
                for receipt in _delivery_receipts_memory
                if receipt.get('tenant_id') == auth.tenant_id
            ]

        windowed_items: list[dict[str, Any]] = []
        for item in items:
            created_ts = _parse_iso_timestamp(item.get('created_at', ''))
            if created_ts is None:
                continue
            if created_ts < cutoff:
                continue
            channel_value = str(item.get('channel', 'unknown')).lower()
            status_value = str(item.get('delivery_status', 'unknown')).lower()
            if channel_filter and channel_value != channel_filter:
                continue
            if status_filter and status_value != status_filter:
                continue
            windowed_items.append(item)

            channel_name = str(item.get('channel', 'unknown'))
            status_name = str(item.get('delivery_status', 'unknown'))
            by_channel[channel_name] = by_channel.get(channel_name, 0) + 1
            by_status[status_name] = by_status.get(status_name, 0) + 1
            channel_bucket = by_channel_status.setdefault(channel_name, {})
            channel_bucket[status_name] = channel_bucket.get(status_name, 0) + 1
            # ENHANCED (additive): aggregate policy decision tokens for ops visibility.
            policy_decision_value = str(item.get('policy_decision') or 'unknown')
            by_policy_decision[policy_decision_value] = by_policy_decision.get(policy_decision_value, 0) + 1

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'windowSeconds': window_seconds,
            'filters': {
                'channel': channel_filter,
                'deliveryStatus': status_filter,
            },
            'generatedAt': now.isoformat(),
            'totalReceipts': len(windowed_items),
            'byChannel': by_channel,
            'byStatus': by_status,
            'byChannelStatus': by_channel_status,
            # ENHANCED (additive): policy decision token distribution for suppression/eligibility trends.
            'byPolicyDecision': by_policy_decision,
        }

    @router.post('/notifications/{notification_id}/read', responses={404: {'description': NOTIFICATION_NOT_FOUND}})
    def mark_notification_read(notification_id: int, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:read-one', 180, 60)
        _hydrate_tenant_notifications(auth.tenant_id)
        with memory_lock:
            item = next(
                (
                    candidate
                    for candidate in notifications_memory
                    if candidate.get('id') == notification_id and candidate.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if item is None:
                raise HTTPException(status_code=404, detail=NOTIFICATION_NOT_FOUND)
            was_unread = not item.get('read', False)
            category = str(item.get('category') or 'general')
            item['read'] = True
            item['read_at'] = datetime.now(UTC).isoformat()
            if was_unread:
                _increment_unread_category_locked(auth.tenant_id, category, -1)

        _persist_read_state(item)

        _append_audit(auth.tenant_id, 'notification_read', notification_id)
        _broadcast_snapshot(auth.tenant_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'notification': item}

    @router.post('/notifications/read-all')
    def mark_notifications_read_all(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:read-all', 60, 60)
        _hydrate_tenant_notifications(auth.tenant_id)
        marked = 0
        now_iso = datetime.now(UTC).isoformat()
        unread_deltas: dict[str, int] = {}
        with memory_lock:
            for item in notifications_memory:
                if item.get('tenant_id') != auth.tenant_id or item.get('read'):
                    continue
                category = _normalize_lower(item.get('category', 'general'), 'general')
                unread_deltas[category] = unread_deltas.get(category, 0) + 1
                item['read'] = True
                item['read_at'] = now_iso
                marked += 1

            for category, delta in unread_deltas.items():
                _increment_unread_category_locked(auth.tenant_id, category, -delta)

            _persist_mark_all_read(auth.tenant_id, now_iso)

        _append_audit(auth.tenant_id, 'notifications_read_all')
        _broadcast_snapshot(auth.tenant_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'updated': marked}

    @router.delete('/notifications/{notification_id}', responses={404: {'description': NOTIFICATION_NOT_FOUND}})
    def delete_notification(notification_id: int, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:notifications:delete', 120, 60)
        _hydrate_tenant_notifications(auth.tenant_id)
        with memory_lock:
            index = next(
                (
                    idx
                    for idx, candidate in enumerate(notifications_memory)
                    if candidate.get('id') == notification_id and candidate.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if index is None:
                raise HTTPException(status_code=404, detail=NOTIFICATION_NOT_FOUND)
            removed = notifications_memory.pop(index)
            if not removed.get('read', False):
                _increment_unread_category_locked(
                    auth.tenant_id,
                    str(removed.get('category') or 'general'),
                    -1,
                )

        _persist_deleted_notification(removed)

        _append_audit(auth.tenant_id, 'notification_deleted', notification_id)
        _broadcast_snapshot(auth.tenant_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'deleted': True, 'notification': removed}

    @router.get('/notifications/digest')
    def get_notification_digest(
        auth: AuthDep,
        frequency: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> dict[str, Any]:
        """
        ENHANCED: Get digest-formatted notification summary.
        Aggregates notifications by priority and category based on user's digest preference.
        """
        enforce_rate_limit(f'{auth.tenant_id}:notifications:digest', 120, 60)
        prefs = _get_preferences(auth.tenant_id)
        digest_freq = _normalize_lower(frequency or prefs.get('digest_frequency', 'realtime'), 'realtime')
        
        snapshot = _snapshot_for_tenant(auth.tenant_id, limit=limit)
        notifs = snapshot.get('notifications', [])
        digest_data = _batch_notifications_for_digest(notifs, digest_freq)
        
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'digest_frequency': digest_freq,
            'digest': digest_data,
            'unreadTotal': snapshot['unreadTotal'],
        }

    @router.get('/notifications/digest/batch-status')
    def get_digest_batch_status(auth: AuthDep) -> dict[str, Any]:
        """
        ENHANCED: Get digest delivery status for scheduled batch jobs.
        Returns next scheduled digest send times based on tenant preferences.
        """
        enforce_rate_limit(f'{auth.tenant_id}:notifications:batch-status', 120, 60)
        prefs = _get_preferences(auth.tenant_id)
        digest_freq = _normalize_lower(prefs.get('digest_frequency', 'realtime'), 'realtime')
        
        now = datetime.now(UTC)
        next_send = None
        if digest_freq == 'daily':
            next_send = (now.replace(hour=9, minute=0, second=0, microsecond=0) +
                        timedelta(days=1)).isoformat()
        elif digest_freq == 'weekly':
            days_ahead = 0 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_send = (now + timedelta(days=days_ahead)).replace(
                hour=9, minute=0, second=0, microsecond=0).isoformat()
        
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'digest_frequency': digest_freq,
            'batchMode': 'enabled' if digest_freq != 'realtime' else 'disabled',
            'nextScheduledSend': next_send,
            'currentTime': now.isoformat(),
        }

    @router.get('/notifications/stream')
    async def stream_notifications(
        request: Request,
        auth: Annotated[AuthContext, Depends(_stream_auth)],
    ) -> StreamingResponse:
        """
        ENHANCED: Real-time notification stream via Server-Sent Events (SSE).
        Sends updates as notifications are created, deleted, or marked read.
        Accepts auth via query params (api_key / tenant_id) for EventSource compatibility.
        """
        enforce_rate_limit(f'{auth.tenant_id}:notifications:stream-connect', 300, 60)
        queue: asyncio.Queue[str] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        subscriber = {'queue': queue, 'loop': loop}
        with memory_lock:
            subscribers.setdefault(auth.tenant_id, []).append(subscriber)

        initial_message = _sse_message('notifications.snapshot', _snapshot_for_tenant(auth.tenant_id))
        realtime_disabled_message = _sse_message(
            'notifications.realtime-disabled',
            {'status': 'ok', 'tenant_id': auth.tenant_id, 'realtime_enabled': False},
        )

        async def event_stream() -> AsyncIterator[str]:
            yield initial_message
            if not _realtime_enabled_for_tenant(auth.tenant_id):
                yield realtime_disabled_message
                return
            try:
                while True:
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=15)
                        yield message
                    except TimeoutError:
                        yield ': keep-alive\n\n'
            finally:
                with memory_lock:
                    active_subscribers = [
                        item for item in subscribers.get(auth.tenant_id, []) if item is not subscriber
                    ]
                    if active_subscribers:
                        subscribers[auth.tenant_id] = active_subscribers
                    else:
                        subscribers.pop(auth.tenant_id, None)

        return StreamingResponse(
            event_stream(),
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    return router