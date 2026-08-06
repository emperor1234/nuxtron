"""
Tests for notifications.py pure helper functions not covered by test_notifications_extra.py.
Covers: _get_default_preferences, _normalize_lower, _sanitize_muted_categories,
        _safe_notification_id, _parse_iso_timestamp, _policy_reason,
        _batch_notifications_for_digest, _apply_delivery_backoff.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

from backend.fastapi.app.routers.notifications import (
    _apply_delivery_backoff,
    _batch_notifications_for_digest,
    _get_default_preferences,
    _normalize_lower,
    _parse_iso_timestamp,
    _policy_reason,
    _safe_notification_id,
    _sanitize_muted_categories,
)


class TestGetDefaultPreferences:
    def test_returns_dict_with_tenant_id(self) -> None:
        result = _get_default_preferences("tenant-abc")
        assert result["tenant_id"] == "tenant-abc"

    def test_default_email_enabled(self) -> None:
        assert _get_default_preferences("t")["email_enabled"] is True

    def test_default_sms_disabled(self) -> None:
        assert _get_default_preferences("t")["sms_enabled"] is False

    def test_default_realtime_enabled(self) -> None:
        assert _get_default_preferences("t")["realtime_enabled"] is True

    def test_default_digest_frequency(self) -> None:
        assert _get_default_preferences("t")["digest_frequency"] == "realtime"


class TestNormalizeLower:
    def test_lowercases_string(self) -> None:
        assert _normalize_lower("Hello World") == "hello world"

    def test_strips_whitespace(self) -> None:
        assert _normalize_lower("  Test  ") == "test"

    def test_returns_fallback_for_non_string(self) -> None:
        assert _normalize_lower(123) == ""

    def test_returns_fallback_for_empty_string(self) -> None:
        assert _normalize_lower("") == ""
        assert _normalize_lower("   ") == ""

    def test_custom_fallback(self) -> None:
        assert _normalize_lower("", fallback="default") == "default"
        assert _normalize_lower(None, fallback="none") == "none"


class TestSanitizeMutedCategories:
    def test_deduplicates(self) -> None:
        result = _sanitize_muted_categories(["A", "a", "B"])
        assert result.count("a") == 1
        assert "b" in result

    def test_normalizes_to_lowercase(self) -> None:
        result = _sanitize_muted_categories(["Marketing", "SALES"])
        assert "marketing" in result
        assert "sales" in result

    def test_removes_empty_strings(self) -> None:
        result = _sanitize_muted_categories(["", "  ", "news"])
        assert "" not in result
        assert "news" in result

    def test_preserves_insertion_order(self) -> None:
        result = _sanitize_muted_categories(["cat1", "cat2", "cat3"])
        assert result == ["cat1", "cat2", "cat3"]

    def test_empty_input_returns_empty(self) -> None:
        assert _sanitize_muted_categories([]) == []


class TestSafeNotificationId:
    def test_returns_int_id(self) -> None:
        assert _safe_notification_id({"id": 42}) == 42

    def test_handles_string_id(self) -> None:
        assert _safe_notification_id({"id": "5"}) == 5

    def test_returns_zero_for_missing_id(self) -> None:
        assert _safe_notification_id({}) == 0

    def test_returns_zero_for_none_id(self) -> None:
        assert _safe_notification_id({"id": None}) == 0

    def test_returns_zero_for_invalid_id(self) -> None:
        assert _safe_notification_id({"id": "abc"}) == 0


class TestParseIsoTimestamp:
    def test_parses_iso_string(self) -> None:
        result = _parse_iso_timestamp("2024-01-15T12:00:00+00:00")
        assert result is not None
        assert isinstance(result, float)

    def test_handles_z_suffix(self) -> None:
        result = _parse_iso_timestamp("2024-01-15T12:00:00Z")
        assert result is not None

    def test_returns_none_for_empty_string(self) -> None:
        assert _parse_iso_timestamp("") is None

    def test_returns_none_for_non_string(self) -> None:
        assert _parse_iso_timestamp(None) is None
        assert _parse_iso_timestamp(123) is None

    def test_returns_none_for_invalid_format(self) -> None:
        assert _parse_iso_timestamp("not-a-date") is None


class TestPolicyReason:
    def test_disabled_preference(self) -> None:
        result = _policy_reason(False, True, "email")
        assert result == "email-disabled-by-preference"

    def test_suppressed_by_policy(self) -> None:
        result = _policy_reason(True, False, "slack")
        assert result == "slack-suppressed-by-priority-policy"

    def test_eligible_by_policy(self) -> None:
        result = _policy_reason(True, True, "webhook")
        assert result == "webhook-eligible-by-policy"


class TestBatchNotificationsForDigest:
    def test_realtime_returns_all_notifications(self) -> None:
        notifs = [{"id": 1}, {"id": 2}]
        result = _batch_notifications_for_digest(notifs, "realtime")
        assert result["batch_mode"] == "realtime"
        assert result["notifications"] == notifs

    def test_daily_batch_includes_summary(self) -> None:
        notifs = [
            {"id": 1, "priority": "high", "category": "billing"},
            {"id": 2, "priority": "info", "category": "billing"},
        ]
        result = _batch_notifications_for_digest(notifs, "daily")
        assert result["batch_mode"] == "daily"
        assert result["summary"]["total"] == 2
        assert "by_priority" in result["summary"]

    def test_weekly_batch_groups_by_category(self) -> None:
        notifs = [
            {"id": 1, "priority": "high", "category": "marketing"},
            {"id": 2, "priority": "high", "category": "sales"},
        ]
        result = _batch_notifications_for_digest(notifs, "weekly")
        assert result["summary"]["by_category"]["marketing"] == 1
        assert result["summary"]["by_category"]["sales"] == 1

    def test_empty_notifications(self) -> None:
        result = _batch_notifications_for_digest([], "daily")
        assert result["summary"]["total"] == 0


class TestApplyDeliveryBackoff:
    def test_attempt_0_returns_base_delay(self) -> None:
        assert _apply_delivery_backoff(0) == 5

    def test_attempt_1_doubles_delay(self) -> None:
        assert _apply_delivery_backoff(1) == 10

    def test_attempt_2_quadruples_delay(self) -> None:
        assert _apply_delivery_backoff(2) == 20

    def test_caps_at_3600(self) -> None:
        assert _apply_delivery_backoff(20) == 3600

    def test_custom_base_delay(self) -> None:
        assert _apply_delivery_backoff(0, base_delay=10) == 10
        assert _apply_delivery_backoff(1, base_delay=10) == 20
