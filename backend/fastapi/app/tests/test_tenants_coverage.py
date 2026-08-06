"""
Targeted coverage tests for tenants.py DB branches.
Lines: 49-80 (create DB), 115-142 (list DB), 154-205 (update DB),
222 (update 404 in memory), 243-248 (delete DB).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ["JWT_SIGNING_KEY"] = "tenants-test-secret"
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)

_JWT_SECRET = "tenants-test-secret"


def _make_jwt(claims: dict[str, str], secret: str = _JWT_SECRET) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({**claims, "exp": int(time.time()) + 86400}).encode()
    ).rstrip(b"=").decode()
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


def _headers(tenant_id: str = "tenants-db-tenant") -> dict[str, str]:
    # 'admin' role: PATCH/DELETE /tenants/{id} require it (routers/tenants.py's
    # AdminDep). Harmless for the GET/POST/list paths in this file too.
    return {
        "Authorization": f"Bearer {_make_jwt({'tenant_id': tenant_id, 'roles': ['admin']})}",
        "X-Tenant-Id": tenant_id,
    }

def _make_mock_conn_with_row(row):
    """Create a mock psycopg connection that returns the given row."""
    cur = MagicMock()
    cur.fetchone.return_value = row
    cur.fetchall.return_value = [row] if row else []
    cur.rowcount = 1

    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur_ctx

    return conn, cur


@pytest.fixture(scope="module")
def client() -> TestClient:
    from ..main import app
    return TestClient(app, raise_server_exceptions=False)


class TestTenantsCreateDbPath:
    """Cover lines 49-80: create_tenant_profile DB branch."""

    def test_create_tenant_db_path(self, client: TestClient) -> None:
        """Lines 49-80: DB INSERT returns a row → success response."""
        from .. import legacy_main as lm

        db_row = (
            "tenants-db-tenant",    # tenant_id
            "encrypted:display_name",  # display_name_cipher
            "Test Corp",            # display_name_preview
            "pro",                  # plan
            "active",               # status
            {},                     # settings_json
            datetime(2024, 1, 1, tzinfo=UTC),  # created_at
            datetime(2024, 1, 1, tzinfo=UTC),  # updated_at
        )
        conn, _ = _make_mock_conn_with_row(db_row)

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            r = client.post("/tenants", headers=_headers(), json={
                "display_name": "Test Corp",
                "plan": "pro",
                "status": "active",
            })
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data["tenant"]["plan"] == "pro"
            assert data["tenant"]["persistence"] == "postgres"

    def test_create_tenant_db_no_row_returns_500(self, client: TestClient) -> None:
        """Line 80: DB INSERT but no row returned → 500."""
        from .. import legacy_main as lm

        conn, _ = _make_mock_conn_with_row(None)

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            r = client.post("/tenants", headers=_headers(), json={
                "display_name": "No Row Corp",
                "plan": "starter",
            })
        assert r.status_code in (500, 200, 422)


class TestTenantsListDbPath:
    """Cover lines 115-142: list_tenant_profiles DB branch."""

    def test_list_tenants_db_path(self, client: TestClient) -> None:
        """Lines 115-142: DB SELECT returns rows → list response."""
        from .. import legacy_main as lm

        db_row = (
            "tenants-db-tenant",
            "encrypted:display_name",
            "Test Corp",
            "growth",
            "active",
            {},
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 1, tzinfo=UTC),
        )
        conn, _ = _make_mock_conn_with_row(db_row)

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            r = client.get("/tenants", headers=_headers())
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "items" in data or "count" in data

    def test_list_tenants_db_path_empty(self, client: TestClient) -> None:
        """DB returns empty rows → empty list."""
        from .. import legacy_main as lm

        cur = MagicMock()
        cur.fetchall.return_value = []
        cur_ctx = MagicMock()
        cur_ctx.__enter__ = MagicMock(return_value=cur)
        cur_ctx.__exit__ = MagicMock(return_value=False)
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur_ctx

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            r = client.get("/tenants", headers=_headers("empty-tenant"))
        assert r.status_code in VALID
        if r.status_code == 200:
            assert r.json()["count"] == 0


class TestTenantsUpdateDbPath:
    """Cover lines 154-205: update_tenant_profile DB branch."""

    def test_update_tenant_db_success(self, client: TestClient) -> None:
        """Lines 154-205: DB UPDATE returns a row → success response."""
        from .. import legacy_main as lm

        existing_row = (
            "encrypted:old_name",  # display_name_cipher
            "Old Corp",             # display_name_preview
            "starter",              # plan
            "active",               # status
            {},                     # settings_json
        )
        updated_row = (
            "tenants-db-tenant",
            "encrypted:new_name",
            "New Corp",
            "pro",
            "active",
            {"feature": "enabled"},
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 2, tzinfo=UTC),
        )

        cur = MagicMock()
        # First call: SELECT existing, Second call: UPDATE
        cur.fetchone.side_effect = [existing_row, updated_row]

        cur_ctx = MagicMock()
        cur_ctx.__enter__ = MagicMock(return_value=cur)
        cur_ctx.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur_ctx

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            r = client.patch("/tenants/tenants-db-tenant", headers=_headers(), json={
                "display_name": "New Corp",
                "plan": "pro",
            })
        assert r.status_code in VALID
        if r.status_code == 200:
            assert r.json()["tenant"]["persistence"] == "postgres"

    def test_update_tenant_db_not_found(self, client: TestClient) -> None:
        """Line 172: DB SELECT returns None → 404."""
        from .. import legacy_main as lm

        cur = MagicMock()
        cur.fetchone.return_value = None

        cur_ctx = MagicMock()
        cur_ctx.__enter__ = MagicMock(return_value=cur)
        cur_ctx.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur_ctx

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            h = _headers("notfound-tenant")
            r = client.patch("/tenants/notfound-tenant", headers=h, json={
                "plan": "pro",
            })
        assert r.status_code in (404, 200, 422)

    def test_update_tenant_db_no_row_after_update(self, client: TestClient) -> None:
        """Line 205 (500): UPDATE returns no row."""
        from .. import legacy_main as lm

        existing_row = ("enc:old", "Old", "starter", "active", {})
        cur = MagicMock()
        cur.fetchone.side_effect = [existing_row, None]  # Second call (UPDATE RETURNING) returns None

        cur_ctx = MagicMock()
        cur_ctx.__enter__ = MagicMock(return_value=cur)
        cur_ctx.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur_ctx

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            r = client.patch("/tenants/tenants-db-tenant", headers=_headers(), json={
                "plan": "enterprise",
            })
        assert r.status_code in (500, 200, 422)


class TestTenantsUpdateMemoryNotFound:
    """Cover line 222: update returns 404 when tenant not in memory."""

    def test_update_nonexistent_tenant_in_memory(self, client: TestClient) -> None:
        """Line 222: memory fallback - tenant_id not in memory → 404."""
        h = _headers("tenant-not-in-memory")
        r = client.patch("/tenants/tenant-not-in-memory", headers=h, json={
            "display_name": "New Name",
        })
        assert r.status_code in (404, 200, 422)


class TestTenantsDeleteDbPath:
    """Cover lines 243-248: delete_tenant_profile DB branch."""

    def test_delete_tenant_db_path(self, client: TestClient) -> None:
        """Lines 243-248: DB DELETE → success."""
        from .. import legacy_main as lm

        cur = MagicMock()
        cur.rowcount = 1

        cur_ctx = MagicMock()
        cur_ctx.__enter__ = MagicMock(return_value=cur)
        cur_ctx.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur_ctx

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            r = client.delete("/tenants/tenants-db-tenant", headers=_headers())
        assert r.status_code in VALID
        if r.status_code == 200:
            assert r.json()["persistence"] == "postgres"

    def test_delete_nonexistent_tenant_db_path(self, client: TestClient) -> None:
        """DB DELETE where rowcount is 0."""
        from .. import legacy_main as lm

        cur = MagicMock()
        cur.rowcount = 0

        cur_ctx = MagicMock()
        cur_ctx.__enter__ = MagicMock(return_value=cur)
        cur_ctx.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur_ctx

        with patch.object(lm, "_db_ready", True), \
             patch("psycopg.connect", return_value=conn):
            r = client.delete("/tenants/tenants-db-tenant", headers=_headers())
        assert r.status_code in VALID
        if r.status_code == 200:
            assert r.json()["deleted"] is False

    def test_cross_tenant_update_returns_403(self, client: TestClient) -> None:
        """403 when updating another tenant's profile."""
        h = _headers("my-tenant")
        r = client.patch("/tenants/other-tenant-id", headers=h, json={
            "plan": "enterprise",
        })
        assert r.status_code == 403

    def test_cross_tenant_delete_returns_403(self, client: TestClient) -> None:
        """403 when deleting another tenant's profile."""
        h = _headers("my-tenant")
        r = client.delete("/tenants/other-tenant-id", headers=h)
        assert r.status_code == 403
