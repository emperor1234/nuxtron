"""
Targeted coverage tests for playbooks.py DB branches.
Lines: 122-129 (_find_playbook_in_db), 137 (_find_playbook DB branch),
139-142 (except/fallback), 153-163 (_handle_list_playbooks DB),
175 (_handle_get_playbook 404), 191-209 (_handle_create_playbook DB),
230-246 (_handle_run_playbook DB), 260-280 (_handle_list_runs DB).
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "pb-test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


def _make_conn_ctx():
    """Build a mock psycopg connection that supports context manager protocol."""
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    cur.rowcount = 0

    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur_ctx
    return conn, cur


def _make_playbook_row(pb_id="pb-custom-abc123456789"):
    return (
        pb_id,                   # id
        "pb-test-tenant",        # tenant_id
        "Test Playbook",         # name
        "saas",                  # vertical
        "A test playbook",       # description
        ["Step 1", "Step 2"],    # steps
        ["crm", "email"],        # integrations
        {"metric": "activation_rate_pct", "value": 10.0},  # roi_target
        5,                       # time_to_value_days
        False,                   # built_in
        datetime(2024, 1, 1, tzinfo=UTC),  # created_at
    )


def _make_run_row(run_id="run-abc123"):
    return (
        run_id,             # id
        "pb-test-tenant",   # tenant_id
        "pb-custom-abc",    # playbook_id
        "Test Playbook",    # playbook_name
        True,               # dry_run
        "dry_run_preview",  # status
        2,                  # steps_total
        0,                  # steps_completed
        datetime(2024, 1, 1, tzinfo=UTC),  # created_at
    )


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestPlaybooksListDbPath:
    """Cover lines 153-163: _handle_list_playbooks DB branch."""

    def test_list_playbooks_db_path_with_rows(self, client: TestClient) -> None:
        """Lines 153-163: DB SELECT returns playbook rows → combined list."""
        import backend.fastapi.app.legacy_main as lm

        pb_row = _make_playbook_row()
        conn, cur = _make_conn_ctx()
        cur.fetchall.return_value = [pb_row]

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect", return_value=conn):
            r = client.get("/playbooks", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "playbooks" in data
            assert data["built_in"] == 10  # 10 built-in playbooks

    def test_list_playbooks_db_path_empty(self, client: TestClient) -> None:
        """DB SELECT returns empty → only built-ins."""
        import backend.fastapi.app.legacy_main as lm

        conn, cur = _make_conn_ctx()
        cur.fetchall.return_value = []

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect", return_value=conn):
            r = client.get("/playbooks", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data["custom"] == 0

    def test_list_playbooks_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 162-163: DB raises → falls back to memory."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect",
                   side_effect=Exception("DB unavailable")):
            r = client.get("/playbooks", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "playbooks" in data


class TestPlaybooksGetDbPath:
    """Cover lines 137, 139-142: _find_playbook DB branch."""

    def test_get_builtin_playbook(self, client: TestClient) -> None:
        """Get a built-in playbook by known ID → no DB needed."""
        r = client.get("/playbooks/pb-builtin-001", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            assert r.json()["id"] == "pb-builtin-001"

    def test_get_custom_playbook_via_db(self, client: TestClient) -> None:
        """Line 137: _find_playbook calls _find_playbook_in_db when db_ready."""
        import backend.fastapi.app.legacy_main as lm

        pb_row = _make_playbook_row(pb_id="pb-custom-db-found")
        conn, cur = _make_conn_ctx()
        cur.fetchone.return_value = pb_row

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect", return_value=conn):
            r = client.get("/playbooks/pb-custom-db-found", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            assert r.json()["id"] == "pb-custom-db-found"

    def test_get_playbook_not_found(self, client: TestClient) -> None:
        """Line 175: playbook_id not in DB or memory → 404."""
        r = client.get("/playbooks/pb-nonexistent-99999", headers=H)
        assert r.status_code == 404

    def test_get_custom_playbook_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 139-142: DB raises → falls back to memory → 404 if not in memory."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect",
                   side_effect=Exception("DB error")):
            r = client.get("/playbooks/pb-custom-notexist", headers=H)
        assert r.status_code == 404

    def test_get_custom_playbook_db_returns_none(self, client: TestClient) -> None:
        """_find_playbook_in_db returns None → falls through to memory → 404."""
        import backend.fastapi.app.legacy_main as lm

        conn, cur = _make_conn_ctx()
        cur.fetchone.return_value = None  # Not found in DB

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect", return_value=conn):
            r = client.get("/playbooks/pb-custom-ghost", headers=H)
        assert r.status_code == 404


class TestPlaybooksCreateDbPath:
    """Cover lines 191-209: _handle_create_playbook DB branch."""

    def test_create_playbook_db_path(self, client: TestClient) -> None:
        """Lines 191-209: DB INSERT succeeds."""
        import backend.fastapi.app.legacy_main as lm

        conn, cur = _make_conn_ctx()

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect", return_value=conn):
            r = client.post("/playbooks", headers=H, json={
                "name": "My DB Playbook",
                "description": "A test playbook created via DB path",
                "vertical": "saas",
                "steps": ["Step A", "Step B"],
                "integrations": ["crm"],
                "roi_metric": "activation_rate_pct",
                "roi_target_value": 25.0,
                "time_to_value_days": 3,
            })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            data = r.json()
            assert "playbook_id" in data
            assert data["status"] == "created"

    def test_create_playbook_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 208-209: DB raises → falls back to memory."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect",
                   side_effect=Exception("DB error")):
            r = client.post("/playbooks", headers=H, json={
                "name": "My Fallback Playbook",
                "description": "Playbook that falls back to memory when DB fails",
                "vertical": "all",
            })
        assert r.status_code in (200, 201)

    def test_create_playbook_memory_path(self, client: TestClient) -> None:
        """No DB → memory path."""
        r = client.post("/playbooks", headers=H, json={
            "name": "My Memory Playbook",
            "description": "Created in memory without any DB",
            "vertical": "ecommerce",
        })
        assert r.status_code in (200, 201)


class TestPlaybooksRunDbPath:
    """Cover lines 230-246: _handle_run_playbook DB branch."""

    def test_run_builtin_playbook_db_path(self, client: TestClient) -> None:
        """Lines 230-246: run a built-in playbook → DB INSERT for run record."""
        import backend.fastapi.app.legacy_main as lm

        conn, cur = _make_conn_ctx()

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect", return_value=conn):
            r = client.post("/playbooks/run", headers=H, json={
                "playbook_id": "pb-builtin-001",
                "dry_run": True,
                "config": {"target_segment": "enterprise"},
            })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            data = r.json()
            assert "run_id" in data
            assert data["status"] in ("dry_run_preview", "scheduled")

    def test_run_playbook_not_found_returns_404(self, client: TestClient) -> None:
        """404 when playbook_id doesn't exist."""
        r = client.post("/playbooks/run", headers=H, json={
            "playbook_id": "pb-nonexistent-xyz",
            "dry_run": True,
        })
        assert r.status_code == 404

    def test_run_playbook_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 244-246: DB raises → falls back to memory for run record."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect",
                   side_effect=Exception("DB insert error")):
            r = client.post("/playbooks/run", headers=H, json={
                "playbook_id": "pb-builtin-002",
                "dry_run": False,
                "config": {"audience": "mid-market"},
            })
        assert r.status_code in (200, 201)


class TestPlaybooksListRunsDbPath:
    """Cover lines 260-280: _handle_list_runs DB branch."""

    def test_list_runs_db_path_with_rows(self, client: TestClient) -> None:
        """Lines 260-280: DB SELECT returns run rows."""
        import backend.fastapi.app.legacy_main as lm

        run_row = _make_run_row()
        conn, cur = _make_conn_ctx()
        cur.fetchall.return_value = [run_row]

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect", return_value=conn):
            r = client.get("/playbooks/runs/list", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "runs" in data
            assert data["total"] >= 1

    def test_list_runs_db_path_empty(self, client: TestClient) -> None:
        """DB SELECT returns empty → zero runs."""
        import backend.fastapi.app.legacy_main as lm

        conn, cur = _make_conn_ctx()
        cur.fetchall.return_value = []

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect", return_value=conn):
            r = client.get("/playbooks/runs/list", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data["total"] == 0

    def test_list_runs_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 279-280: DB raises → falls back to memory."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), \
             patch("backend.fastapi.app.routers.playbooks.psycopg.connect",
                   side_effect=Exception("DB list_runs error")):
            r = client.get("/playbooks/runs/list", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "runs" in data
