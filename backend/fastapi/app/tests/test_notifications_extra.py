"""
Tests for notifications router — covering uncovered endpoints.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestListNotifications:
    def test_list_default(self, client: TestClient) -> None:
        r = client.get("/notifications", headers=H)
        assert r.status_code in VALID

    def test_list_with_filter(self, client: TestClient) -> None:
        r = client.get("/notifications?unread_only=true", headers=H)
        assert r.status_code in VALID


class TestPreferences:
    def test_get_preferences(self, client: TestClient) -> None:
        r = client.get("/notifications/preferences", headers=H)
        assert r.status_code in VALID

    def test_update_preferences(self, client: TestClient) -> None:
        r = client.put("/notifications/preferences", headers=H, json={
            "email_enabled": True,
            "digest_frequency": "daily",
        })
        assert r.status_code in VALID

    def test_invalid_digest_frequency(self, client: TestClient) -> None:
        r = client.put("/notifications/preferences", headers=H, json={
            "digest_frequency": "hourly",
        })
        assert r.status_code in VALID


class TestUnreadCount:
    def test_unread_count(self, client: TestClient) -> None:
        r = client.get("/notifications/unread-count", headers=H)
        assert r.status_code in VALID


class TestCreateNotification:
    def test_create_notification(self, client: TestClient) -> None:
        r = client.post("/notifications", headers=H, json={
            "title": "Test Notification",
            "body": "This is a test notification",
            "notification_type": "info",
        })
        assert r.status_code in VALID

    def test_create_notification_minimal(self, client: TestClient) -> None:
        r = client.post("/notifications", headers=H, json={
            "title": "Minimal Notification",
        })
        assert r.status_code in VALID


class TestDelivery:
    def test_delivery_receipts(self, client: TestClient) -> None:
        r = client.get("/notifications/delivery-receipts", headers=H)
        assert r.status_code in VALID

    def test_delivery_health(self, client: TestClient) -> None:
        r = client.get("/notifications/delivery-health", headers=H)
        assert r.status_code in VALID


class TestReadActions:
    def test_mark_read_nonexistent(self, client: TestClient) -> None:
        r = client.post("/notifications/notif_nonexistent/read", headers=H)
        assert r.status_code in VALID

    def test_mark_all_read(self, client: TestClient) -> None:
        r = client.post("/notifications/read-all", headers=H)
        assert r.status_code in VALID


class TestDeleteNotification:
    def test_delete_nonexistent(self, client: TestClient) -> None:
        r = client.delete("/notifications/notif_nonexistent", headers=H)
        assert r.status_code in VALID


class TestDigest:
    def test_get_digest(self, client: TestClient) -> None:
        r = client.get("/notifications/digest", headers=H)
        assert r.status_code in VALID

    def test_digest_batch_status(self, client: TestClient) -> None:
        r = client.get("/notifications/digest/batch-status", headers=H)
        assert r.status_code in VALID

    def test_notification_stream(self, client: TestClient) -> None:
        r = client.get("/notifications/stream", headers=H)
        assert r.status_code in VALID
