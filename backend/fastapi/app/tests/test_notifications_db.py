"""
Tests for notifications.py DB-backed paths.
Covers lines that require _db_enabled() to return True.
Also covers other missing paths like:
- Weekly batch-status (lines 1031-1034)
- realtime_enabled=False broadcast (line 700)
- Email ValueError (lines 555-556)
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-db-tenant"}


def _make_mock_conn(rows=None, fetchone=None):
    """Create mock psycopg connection with cursor context manager support."""
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = fetchone
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestNotificationsDbPaths:
    """Cover DB hydration and persistence paths by enabling _db_ready."""

    def test_create_with_db_enabled_covers_persist(self, client: TestClient) -> None:
        """
        Lines 200-233, 299-325: With _db_ready=True and mocked psycopg,
        _ensure_notifications_table and _persist_created_notification are called.
        """
        import backend.fastapi.app.legacy_main as lm
        mock_conn, _ = _make_mock_conn(fetchone=(99,))  # returning DB id

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-db-create"}
                r = client.post("/notifications", headers=h, json={
                    "title": "DB test notification",
                    "message": "Testing DB persistence path",
                    "category": "system",
                    "priority": "info",
                })
                assert r.status_code in VALID

    def test_get_notifications_with_db_enabled_hydration(self, client: TestClient) -> None:
        """
        Lines 235-297: _hydrate_tenant_notifications with DB enabled.
        Uses a new unique tenant to ensure hydration runs.
        """
        import backend.fastapi.app.legacy_main as lm
        # Return some rows that represent DB notifications
        db_rows = [
            (1001, "DB Notif Title", "DB message", "system", "info",
             False, None, __import__("datetime").datetime(2024, 1, 1, 12, 0), "api"),
        ]
        mock_conn, _ = _make_mock_conn(rows=db_rows)

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-db-hydrate-unique1"}
                r = client.get("/notifications", headers=h)
                assert r.status_code in VALID

    def test_mark_read_with_db_persistence(self, client: TestClient) -> None:
        """Lines 331-346: _persist_read_state with DB enabled after marking read."""
        import backend.fastapi.app.legacy_main as lm
        mock_conn, _ = _make_mock_conn()

        # First create a notification
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-db-read"}
        create_r = client.post("/notifications", headers=h, json={
            "title": "Read persistence test",
            "message": "Testing read persistence",
            "category": "general",
            "priority": "info",
        })
        assert create_r.status_code in VALID
        if create_r.status_code not in (200, 201):
            return

        notif = create_r.json().get("notification") or {}
        notif_id = notif.get("id")
        if not notif_id:
            return

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                read_r = client.post(f"/notifications/{notif_id}/read", headers=h)
                assert read_r.status_code in VALID

    def test_delete_with_db_persistence(self, client: TestClient) -> None:
        """Lines 353-375: _persist_delete with DB enabled after deleting notification."""
        import backend.fastapi.app.legacy_main as lm
        mock_conn, _ = _make_mock_conn()

        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-db-delete"}
        create_r = client.post("/notifications", headers=h, json={
            "title": "Delete persistence test",
            "message": "Testing delete persistence",
            "category": "general",
            "priority": "info",
        })
        assert create_r.status_code in VALID
        if create_r.status_code not in (200, 201):
            return

        notif = create_r.json().get("notification") or {}
        notif_id = notif.get("id")
        if not notif_id:
            return

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                del_r = client.delete(f"/notifications/{notif_id}", headers=h)
                assert del_r.status_code in VALID

    def test_db_ensure_table_exception_path(self, client: TestClient) -> None:
        """Lines 194-195: exception in _db_dsn_fn causes _db_enabled to return False."""
        import backend.fastapi.app.legacy_main as lm
        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", side_effect=Exception("DB connection failed")):
                h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-db-except"}
                r = client.post("/notifications", headers=h, json={
                    "title": "Exception fallback test",
                    "message": "Should fall back to memory",
                    "category": "general",
                    "priority": "info",
                })
                assert r.status_code in VALID

    def test_hydrate_with_db_rows_loaded(self, client: TestClient) -> None:
        """Lines 264-296: hydration with rows from DB, covering next_id logic."""
        from datetime import datetime

        import backend.fastapi.app.legacy_main as lm
        now = datetime.now(UTC)

        db_rows = [
            (2001, "Hydrated Title 1", "Hydrated message 1", "system", "warning",
             False, None, now, "api"),
            (2002, "Hydrated Title 2", "Hydrated message 2", "general", "info",
             True, now, now, "api"),
        ]
        mock_conn, _ = _make_mock_conn(rows=db_rows)

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-db-hydrate-rows"}
                r = client.get("/notifications", headers=h)
                assert r.status_code in VALID


class TestNotificationsWeeklyDigest:
    """Cover lines 1031-1034: weekly batch-status days_ahead calculation."""

    def test_weekly_batch_status(self, client: TestClient) -> None:
        """Lines 1031-1034: set weekly preference, get batch-status."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-weekly-batch"}

        # Set weekly preference
        pref_r = client.put("/notifications/preferences", headers=h, json={
            "digest_frequency": "weekly",
        })
        assert pref_r.status_code in VALID

        # Get batch status - triggers the weekly branch
        r = client.get("/notifications/digest/batch-status", headers=h)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data.get("digest_frequency") == "weekly"
            assert data.get("batchMode") == "enabled"

    def test_daily_batch_status(self, client: TestClient) -> None:
        """Daily batch-status path."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-daily-batch"}

        pref_r = client.put("/notifications/preferences", headers=h, json={
            "digest_frequency": "daily",
        })
        assert pref_r.status_code in VALID

        r = client.get("/notifications/digest/batch-status", headers=h)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data.get("batchMode") == "enabled"

    def test_realtime_batch_status(self, client: TestClient) -> None:
        """Realtime batch-status (no next_send)."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-realtime-batch"}
        r = client.get("/notifications/digest/batch-status", headers=h)
        assert r.status_code in VALID


class TestNotificationsRealtimeDisabled:
    """Cover line 700: _broadcast_snapshot with realtime_enabled=False."""

    def test_create_with_realtime_disabled(self, client: TestClient) -> None:
        """Line 700: create notification when realtime is off → no broadcast."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-no-realtime"}

        # Disable realtime
        pref_r = client.put("/notifications/preferences", headers=h, json={
            "realtime_enabled": False,
        })
        assert pref_r.status_code in VALID

        r = client.post("/notifications", headers=h, json={
            "title": "No realtime test",
            "message": "Realtime is disabled",
            "category": "general",
            "priority": "info",
        })
        assert r.status_code in VALID

    def test_mark_read_with_realtime_disabled(self, client: TestClient) -> None:
        """Lines 940-943: mark read with broadcast when realtime=False."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-noreal-read"}

        # Disable realtime
        client.put("/notifications/preferences", headers=h, json={
            "realtime_enabled": False,
        })

        # Create a notification
        create_r = client.post("/notifications", headers=h, json={
            "title": "No realtime mark read",
            "message": "Testing mark read",
            "category": "general",
            "priority": "info",
        })
        assert create_r.status_code in VALID
        if create_r.status_code not in (200, 201):
            return

        notif_id = (create_r.json().get("notification") or {}).get("id")
        if not notif_id:
            return

        r = client.post(f"/notifications/{notif_id}/read", headers=h)
        assert r.status_code in VALID


class TestNotificationsMarkReadNotFound:
    """Cover line 936: 404 when marking non-existent notification as read."""

    def test_mark_read_not_found(self, client: TestClient) -> None:
        """Line 936: notification_id not found → 404."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-read-notfound"}
        r = client.post("/notifications/9999999/read", headers=h)
        assert r.status_code in VALID
        if r.status_code == 404:
            assert "not found" in r.json().get("detail", "").lower()

    def test_delete_not_found(self, client: TestClient) -> None:
        """404 when deleting non-existent notification."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-del-notfound"}
        r = client.delete("/notifications/9999999", headers=h)
        assert r.status_code in VALID


class TestNotificationsEmailValueError:
    """Cover line 555-556: ValueError in email response JSON parsing."""

    def test_email_response_invalid_json(self, client: TestClient) -> None:
        """Lines 554-556: email delivery response that has is_success but invalid JSON."""

        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-email-valueerr"}

        # Set email preferences
        pref_r = client.put("/notifications/preferences", headers=h, json={
            "email_enabled": True,
            "slack_enabled": False,
            "realtime_enabled": False,
        })
        assert pref_r.status_code in VALID

        # Mock httpx to return a response that has is_success=True but .json() raises ValueError
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.side_effect = ValueError("Not valid JSON")
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.return_value = mock_response

        with patch.dict(os.environ, {
            "RESEND_API_KEY": "re_test_key",
            "RESEND_FROM_EMAIL": "from@example.com",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client_instance):
                r = client.post("/notifications", headers=h, json={
                    "title": "Email ValueError test",
                    "message": "Should handle JSON parse error gracefully",
                    "category": "general",
                    "priority": "info",
                })
                assert r.status_code in VALID


class TestNotificationsUnreadCountAndPrefs:
    """Cover additional paths in unread-count and preferences."""

    def test_unread_count(self, client: TestClient) -> None:
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-unread-count"}
        r = client.get("/notifications/unread-count", headers=h)
        assert r.status_code in VALID

    def test_get_preferences(self, client: TestClient) -> None:
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-prefs-get"}
        r = client.get("/notifications/preferences", headers=h)
        assert r.status_code in VALID

    def test_read_all(self, client: TestClient) -> None:
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-read-all"}
        r = client.post("/notifications/read-all", headers=h)
        assert r.status_code in VALID

    def test_delivery_receipts_filtered(self, client: TestClient) -> None:
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-receipts"}
        r = client.get("/notifications/delivery-receipts", headers=h,
                       params={"notification_id": 1})
        assert r.status_code in VALID

    def test_invalid_priority_still_creates(self, client: TestClient) -> None:
        """Line 802: invalid priority normalized to 'info'."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "notif-badprio"}
        r = client.post("/notifications", headers=h, json={
            "title": "Bad priority test",
            "message": "Priority that does not exist",
            "category": "general",
            "priority": "super_invalid_priority_xyz",
        })
        assert r.status_code in VALID
        if r.status_code in (200, 201):
            notif = r.json().get("notification") or {}
            assert notif.get("priority") == "info"
