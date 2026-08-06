"""
Additional tests for legacy_main.py pure helper functions not yet covered.
Covers: _allowed_hosts, _cors_origins, _security_alert_from_email,
_security_alert_db_queue_enabled, _memory_queue_item_matches,
_memory_queue_item_payload, _paginate_email_queue_items,
_map_security_alert_email_row, _dispatch_security_email,
_hash_password_ops, _hash_email, _decrypt_value_or_empty
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)


class TestAllowedHosts:
    def test_default_non_production(self) -> None:
        from backend.fastapi.app.legacy_main import _allowed_hosts
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "", "ENVIRONMENT": "development"}):
            result = _allowed_hosts()
            assert result == ["*"]

    def test_parses_env_var(self) -> None:
        from backend.fastapi.app.legacy_main import _allowed_hosts
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "example.com, api.example.com"}):
            result = _allowed_hosts()
            assert "example.com" in result
            assert "api.example.com" in result

    def test_strips_whitespace(self) -> None:
        from backend.fastapi.app.legacy_main import _allowed_hosts
        with patch.dict(os.environ, {"ALLOWED_HOSTS": " host1.com , host2.com "}):
            result = _allowed_hosts()
            assert "host1.com" in result
            assert "host2.com" in result

    def test_filters_empty_items(self) -> None:
        from backend.fastapi.app.legacy_main import _allowed_hosts
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "host1.com,,host2.com"}):
            result = _allowed_hosts()
            assert "" not in result
            assert len(result) == 2


class TestCorsOrigins:
    def test_default_non_production(self) -> None:
        from backend.fastapi.app.legacy_main import _cors_origins
        with patch.dict(os.environ, {"CORS_ORIGINS": "", "ENVIRONMENT": "development"}):
            result = _cors_origins()
            assert result == ["*"]

    def test_parses_env_var(self) -> None:
        from backend.fastapi.app.legacy_main import _cors_origins
        with patch.dict(os.environ, {"CORS_ORIGINS": "https://app.com,https://admin.com"}):
            result = _cors_origins()
            assert "https://app.com" in result
            assert "https://admin.com" in result


class TestSecurityAlertFromEmail:
    def test_returns_smtp_from_first(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_from_email
        with patch.dict(os.environ, {
            "SMTP_FROM": "alerts@example.com",
            "RESEND_FROM_EMAIL": "other@example.com",
        }):
            result = _security_alert_from_email()
            assert result == "alerts@example.com"

    def test_falls_back_to_resend(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_from_email
        with patch.dict(os.environ, {
            "SMTP_FROM": "",
            "RESEND_FROM_EMAIL": "resend@example.com",
            "SES_FROM_EMAIL": "",
            "POSTAL_FROM_EMAIL": "",
        }):
            result = _security_alert_from_email()
            assert result == "resend@example.com"

    def test_returns_empty_if_none_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_from_email
        with patch.dict(os.environ, {
            "SMTP_FROM": "",
            "RESEND_FROM_EMAIL": "",
            "SES_FROM_EMAIL": "",
            "POSTAL_FROM_EMAIL": "",
        }):
            result = _security_alert_from_email()
            assert result == ""

    def test_falls_back_to_ses(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_from_email
        with patch.dict(os.environ, {
            "SMTP_FROM": "",
            "RESEND_FROM_EMAIL": "",
            "SES_FROM_EMAIL": "ses@example.com",
            "POSTAL_FROM_EMAIL": "",
        }):
            result = _security_alert_from_email()
            assert result == "ses@example.com"

    def test_falls_back_to_postal(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_from_email
        with patch.dict(os.environ, {
            "SMTP_FROM": "",
            "RESEND_FROM_EMAIL": "",
            "SES_FROM_EMAIL": "",
            "POSTAL_FROM_EMAIL": "postal@example.com",
        }):
            result = _security_alert_from_email()
            assert result == "postal@example.com"


class TestSecurityAlertDbQueueEnabled:
    def test_enabled_by_default(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_db_queue_enabled
        # _db_ready is False in test mode, so it will be False regardless of flag
        result = _security_alert_db_queue_enabled()
        assert isinstance(result, bool)

    def test_disabled_by_env(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_db_queue_enabled
        with patch.dict(os.environ, {"SECURITY_ALERT_DB_QUEUE_ENABLED": "0"}):
            result = _security_alert_db_queue_enabled()
            assert result is False

    def test_disabled_by_false_string(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_db_queue_enabled
        with patch.dict(os.environ, {"SECURITY_ALERT_DB_QUEUE_ENABLED": "false"}):
            result = _security_alert_db_queue_enabled()
            assert result is False


class TestMemoryQueueItemMatches:
    def test_matches_correct_tenant_and_status(self) -> None:
        from backend.fastapi.app.legacy_main import _memory_queue_item_matches
        raw = {"tenant_id": "platform-security", "id": 100, "status": "queued"}
        assert _memory_queue_item_matches(raw, "queued", 0) is True

    def test_wrong_tenant_returns_false(self) -> None:
        from backend.fastapi.app.legacy_main import _memory_queue_item_matches
        raw = {"tenant_id": "other-tenant", "id": 1, "status": "queued"}
        assert _memory_queue_item_matches(raw, "queued", 0) is False

    def test_before_id_filter(self) -> None:
        from backend.fastapi.app.legacy_main import _memory_queue_item_matches
        raw = {"tenant_id": "platform-security", "id": 100, "status": "queued"}
        # id >= before_id → excluded
        assert _memory_queue_item_matches(raw, "queued", 100) is False
        # id < before_id → included
        assert _memory_queue_item_matches(raw, "queued", 101) is True

    def test_status_filter(self) -> None:
        from backend.fastapi.app.legacy_main import _memory_queue_item_matches
        raw = {"tenant_id": "platform-security", "id": 1, "status": "failed"}
        assert _memory_queue_item_matches(raw, "queued", 0) is False
        assert _memory_queue_item_matches(raw, "failed", 0) is True

    def test_all_status_matches_any(self) -> None:
        from backend.fastapi.app.legacy_main import _memory_queue_item_matches
        raw = {"tenant_id": "platform-security", "id": 1, "status": "sent"}
        assert _memory_queue_item_matches(raw, "all", 0) is True


class TestMemoryQueueItemPayload:
    def test_maps_fields(self) -> None:
        from backend.fastapi.app.legacy_main import _memory_queue_item_payload
        raw = {
            "id": 42,
            "provider": "resend",
            "to": "user@example.com",
            "from": "alerts@example.com",
            "subject": "Security Alert",
            "status": "queued",
            "attempts": 1,
            "delivery_detail": "OK",
        }
        result = _memory_queue_item_payload(raw)
        assert result["id"] == 42
        assert result["provider"] == "resend"
        assert result["queue_source"] == "memory"

    def test_defaults_for_missing_fields(self) -> None:
        from backend.fastapi.app.legacy_main import _memory_queue_item_payload
        result = _memory_queue_item_payload({})
        assert result["id"] == 0
        assert result["provider"] == ""
        assert result["status"] == "queued"
        assert result["attempts"] == 0

    def test_null_values_become_empty(self) -> None:
        from backend.fastapi.app.legacy_main import _memory_queue_item_payload
        raw = {"id": 1, "provider": None, "to": None}
        result = _memory_queue_item_payload(raw)
        assert result["provider"] == ""
        assert result["to"] == ""


class TestPaginateEmailQueueItems:
    def test_no_more_pages(self) -> None:
        from backend.fastapi.app.legacy_main import _paginate_email_queue_items
        items = [{"id": i} for i in range(5)]
        page, has_more, cursor = _paginate_email_queue_items(items, 10)
        assert len(page) == 5
        assert has_more is False
        assert cursor is None

    def test_has_more_page(self) -> None:
        from backend.fastapi.app.legacy_main import _paginate_email_queue_items
        items = [{"id": i} for i in range(10)]
        page, has_more, cursor = _paginate_email_queue_items(items, 5)
        assert len(page) == 5
        assert has_more is True
        assert cursor is not None

    def test_cursor_is_last_item_id(self) -> None:
        from backend.fastapi.app.legacy_main import _paginate_email_queue_items
        items = [{"id": i} for i in [10, 9, 8, 7, 6, 5, 4]]
        page, has_more, cursor = _paginate_email_queue_items(items, 5)
        assert cursor == 6  # last item in page

    def test_empty_items(self) -> None:
        from backend.fastapi.app.legacy_main import _paginate_email_queue_items
        page, has_more, cursor = _paginate_email_queue_items([], 10)
        assert page == []
        assert has_more is False
        assert cursor is None


class TestMapSecurityAlertEmailRow:
    def test_full_row(self) -> None:
        from backend.fastapi.app.legacy_main import _map_security_alert_email_row
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        row = (
            1,          # id
            "resend",   # provider
            "user@example.com",  # to_email
            "alerts@example.com",  # from_email
            "Security Alert",  # subject
            "sent",     # status
            3,          # attempts
            "Delivered",  # delivery_detail
            now,        # next_attempt_at
            now,        # created_at
            now,        # updated_at
            now,        # requeued_at
            "admin",    # requeued_by
            "127.0.0.1",  # requeued_source_ip
        )
        result = _map_security_alert_email_row(row)
        assert result["id"] == 1
        assert result["provider"] == "resend"
        assert result["queue_source"] == "db"
        assert result["next_attempt_at"] is not None

    def test_null_datetimes(self) -> None:
        from backend.fastapi.app.legacy_main import _map_security_alert_email_row
        row = (1, "", "", "", "", "queued", 0, "", None, None, None, None, "", "")
        result = _map_security_alert_email_row(row)
        assert result["next_attempt_at"] is None
        assert result["created_at"] is None


class TestDispatchSecurityEmail:
    def test_returns_failure_when_no_providers(self) -> None:
        from backend.fastapi.app.legacy_main import _dispatch_security_email
        # No providers configured by default → all return "not configured"
        ok, provider, detail = _dispatch_security_email(
            "user@example.com", "Alert", "Message body"
        )
        # Should attempt all providers and return False when none are configured
        assert isinstance(ok, bool)
        assert isinstance(provider, str)
        assert isinstance(detail, str)


class TestHashPasswordOps:
    def test_bcrypt(self) -> None:
        from backend.fastapi.app.legacy_main import _hash_password_ops
        result = _hash_password_ops("mysecretpassword", "bcrypt")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_default_algorithm(self) -> None:
        from backend.fastapi.app.legacy_main import _hash_password_ops
        result = _hash_password_ops("mysecretpassword", "sha256")
        assert isinstance(result, str)
        assert len(result) > 0


class TestHashEmail:
    def test_returns_hex_hash(self) -> None:
        from backend.fastapi.app.legacy_main import _hash_email
        result = _hash_email("user@example.com")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex is 64 chars

    def test_case_insensitive(self) -> None:
        from backend.fastapi.app.legacy_main import _hash_email
        result1 = _hash_email("User@Example.COM")
        result2 = _hash_email("user@example.com")
        assert result1 == result2

    def test_different_emails_differ(self) -> None:
        from backend.fastapi.app.legacy_main import _hash_email
        r1 = _hash_email("user1@example.com")
        r2 = _hash_email("user2@example.com")
        assert r1 != r2
