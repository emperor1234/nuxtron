"""Notifications/Delivery service: get default preferences."""

from __future__ import annotations
from datetime import datetime
from typing import Any
import json


def _get_default_preferences(tenant_id: str) -> dict[str, Any]:
    """Return default notification preferences for a tenant."""
    return {
        "tenant_id": tenant_id,
        "muted_categories": [],
        "email_enabled": True,
        "sms_enabled": False,
        "slack_enabled": False,
        "realtime_enabled": True,
        "digest_frequency": "realtime",
    }


def _sse_message(event: str, payload: dict[str, Any]) -> str:
    """Format a server-sent event message."""
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def _normalize_lower(value: object, fallback: str = "") -> str:
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
        return int(notification.get("id", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _parse_iso_timestamp(value: object) -> float | None:
    """Parse ISO datetime values robustly, accepting trailing Z as UTC."""
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None


def _policy_reason(enabled: bool, policy_match: bool, policy_name: str) -> str:
    """Return a normalized policy reason token for receipt metadata."""
    if not enabled:
        return f"{policy_name}-disabled-by-preference"
    if not policy_match:
        return f"{policy_name}-suppressed-by-priority-policy"
    return f"{policy_name}-eligible-by-policy"


def _batch_notifications_for_digest(notifications: list[dict[str, Any]], digest_frequency: str) -> dict[str, Any]:
    """
    ENHANCED: Aggregate notifications by digest frequency (realtime/daily/weekly).
    Returns a digest summary with notification counts by priority.
    """
    if digest_frequency == "realtime":
        return {"batch_mode": "realtime", "notifications": notifications}
    by_priority: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for notif in notifications:
        priority = _normalize_lower(notif.get("priority", "info"), "info")
        category = _normalize_lower(notif.get("category", "general"), "general")
        by_priority[priority] = by_priority.get(priority, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    return {
        "batch_mode": digest_frequency,
        "notifications": notifications,
        "summary": {"total": len(notifications), "by_priority": by_priority, "by_category": by_category},
    }


def _apply_delivery_backoff(attempt: int, base_delay: int = 5) -> int:
    """
    ENHANCED: Calculate exponential backoff delay in seconds.
    For retry scheduling on failed deliveries.
    """
    return min(base_delay * 2**attempt, 3600)
