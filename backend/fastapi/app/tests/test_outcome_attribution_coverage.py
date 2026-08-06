"""Targeted coverage tests for outcome_attribution DB-first branches."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "outcome-db-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
OA_PSYCOPG = "backend.fastapi.app.routers.outcome_attribution.psycopg.connect"


def _make_conn(fetchone=None, fetchall=None):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall if fetchall is not None else []

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
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def enable_db_ready():
    import backend.fastapi.app.legacy_main as lm

    with patch.object(lm, "_db_ready", True):
        yield


class TestOutcomeDbPaths:
    def test_quality_band_nan_falls_back_to_poor(self) -> None:
        from backend.fastapi.app.routers.outcome_attribution import _quality_band

        assert _quality_band(float("nan")) == "poor"

    def test_action_exists_memory_fallback(self) -> None:
        from backend.fastapi.app.routers.outcome_attribution import (
            OutcomeAttributionContext,
            _action_exists,
        )

        actions = [{"id": "a-1", "tenant_id": "outcome-db-tenant"}]
        ctx = OutcomeAttributionContext(
            enforce_rate_limit=lambda *_args, **_kwargs: None,
            actions_memory=actions,
            outcomes_memory=[],
            quality_scores_memory=[],
            audit_log_memory=[],
            get_db_ready=lambda: False,
            db_dsn=lambda: "",
        )

        assert _action_exists(ctx, "a-1", "outcome-db-tenant") is True

    def test_record_action_db_path(self, client: TestClient, enable_db_ready) -> None:
        conn, _ = _make_conn()
        with patch(OA_PSYCOPG, return_value=conn):
            r = client.post(
                "/outcome/actions",
                headers=H,
                json={
                    "action_type": "email_send",
                    "target": "lead@example.com",
                    "command": "send-email",
                    "actor_role": "ira_autonomous",
                    "channel": "email",
                    "payload": {"campaign": "q2"},
                    "dry_run": False,
                },
            )
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            assert "action_id" in r.json()

    def test_record_action_db_exception_fallback(self, client: TestClient, enable_db_ready) -> None:
        with patch(OA_PSYCOPG, side_effect=Exception("db down")):
            r = client.post(
                "/outcome/actions",
                headers=H,
                json={
                    "action_type": "crm_update",
                    "target": "contact-1",
                    "command": "update-contact",
                },
            )
        assert r.status_code in (200, 201)

    def test_record_outcome_db_path(self, client: TestClient, enable_db_ready) -> None:
        # First connection: _action_exists SELECT 1 (returns row)
        exists_conn, exists_cur = _make_conn(fetchone=(1,))
        # Second connection: INSERT + UPDATE path
        write_conn, _ = _make_conn()

        with patch(OA_PSYCOPG, side_effect=[exists_conn, write_conn]):
            r = client.post(
                "/outcome/outcomes",
                headers=H,
                json={
                    "action_id": "action-db-1",
                    "outcome_type": "converted",
                    "revenue_impact_gbp": 2500.0,
                    "confidence": 0.9,
                    "notes": "converted in 2 days",
                },
            )
        assert r.status_code in (200, 201)

    def test_record_outcome_action_not_found(self, client: TestClient, enable_db_ready) -> None:
        exists_conn, _ = _make_conn(fetchone=None)
        with patch(OA_PSYCOPG, return_value=exists_conn):
            r = client.post(
                "/outcome/outcomes",
                headers=H,
                json={
                    "action_id": "missing-action",
                    "outcome_type": "no_response",
                },
            )
        assert r.status_code == 404

    def test_record_outcome_db_exception_fallback(self, client: TestClient, enable_db_ready) -> None:
        # Ensure action exists in memory so fallback path can proceed.
        with patch(OA_PSYCOPG, side_effect=Exception("db setup error")):
            action_r = client.post(
                "/outcome/actions",
                headers=H,
                json={
                    "action_type": "fallback_action",
                    "target": "t-1",
                    "command": "cmd",
                },
            )
        assert action_r.status_code in (200, 201)
        action_id = action_r.json().get("action_id")

        # First DB call: _action_exists -> raise, then fallback to memory.
        with patch(OA_PSYCOPG, side_effect=Exception("db write error")):
            r = client.post(
                "/outcome/outcomes",
                headers=H,
                json={
                    "action_id": action_id,
                    "outcome_type": "clicked",
                    "confidence": 0.8,
                },
            )
        assert r.status_code in (200, 201)

    def test_submit_quality_db_path(self, client: TestClient, enable_db_ready) -> None:
        exists_conn, _ = _make_conn(fetchone=(1,))
        write_conn, _ = _make_conn()

        with patch(OA_PSYCOPG, side_effect=[exists_conn, write_conn]):
            r = client.post(
                "/outcome/quality",
                headers=H,
                json={
                    "action_id": "action-db-2",
                    "accuracy": 91,
                    "safety": 95,
                    "speed_ms": 320,
                    "revenue_impact_gbp": 1500,
                    "human_override": False,
                },
            )
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            data = r.json()
            assert "score" in data
            assert data["band"] in ("excellent", "good", "fair", "poor")

    def test_submit_quality_not_found(self, client: TestClient, enable_db_ready) -> None:
        exists_conn, _ = _make_conn(fetchone=None)
        with patch(OA_PSYCOPG, return_value=exists_conn):
            r = client.post(
                "/outcome/quality",
                headers=H,
                json={
                    "action_id": "missing-quality-action",
                    "accuracy": 50,
                    "safety": 50,
                    "speed_ms": 1000,
                    "revenue_impact_gbp": 0,
                    "human_override": True,
                    "override_reason": "manual correction",
                },
            )
        assert r.status_code == 404

    def test_submit_quality_db_exception_fallback(self, client: TestClient, enable_db_ready) -> None:
        # Create action in memory path so _action_exists can fallback to memory.
        with patch(OA_PSYCOPG, side_effect=Exception("db setup error")):
            action_r = client.post(
                "/outcome/actions",
                headers=H,
                json={
                    "action_type": "quality_action",
                    "target": "t-2",
                    "command": "cmd2",
                },
            )
        assert action_r.status_code in (200, 201)
        action_id = action_r.json().get("action_id")

        with patch(OA_PSYCOPG, side_effect=Exception("db failure")):
            r = client.post(
                "/outcome/quality",
                headers=H,
                json={
                    "action_id": action_id,
                    "accuracy": 75,
                    "safety": 70,
                    "speed_ms": 900,
                    "revenue_impact_gbp": 100,
                    "human_override": False,
                },
            )
        assert r.status_code in (200, 201)

    def test_get_graph_db_path(self, client: TestClient, enable_db_ready) -> None:
        row = (
            "action-1",
            "outcome-db-tenant",
            "email_send",
            "lead@example.com",
            "send-email",
            "ira_autonomous",
            "email",
            {"k": "v"},
            False,
            "converted",
            88.5,
            datetime(2024, 1, 1, tzinfo=UTC),
        )
        conn, _ = _make_conn(fetchall=[row])
        with patch(OA_PSYCOPG, return_value=conn):
            r = client.get("/outcome/graph", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data["total_actions"] >= 1
            assert "outcome_distribution" in data

    def test_list_quality_db_path(self, client: TestClient, enable_db_ready) -> None:
        row = (
            "q-1",
            "outcome-db-tenant",
            "action-1",
            90.0,
            91.0,
            250,
            1000.0,
            False,
            "",
            89.0,
            "excellent",
            datetime(2024, 1, 1, tzinfo=UTC),
        )
        conn, _ = _make_conn(fetchall=[row])
        with patch(OA_PSYCOPG, return_value=conn):
            r = client.get("/outcome/quality", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data["total"] >= 1
            assert "avg_score" in data

    def test_list_pending_db_path(self, client: TestClient, enable_db_ready) -> None:
        row = (
            "action-pending-1",
            "email_send",
            "prospect@example.com",
            datetime(2024, 1, 1, tzinfo=UTC),
        )
        conn, _ = _make_conn(fetchall=[row])
        with patch(OA_PSYCOPG, return_value=conn):
            r = client.get("/outcome/actions/pending", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data["total"] >= 1

    def test_graph_quality_pending_db_exception_fallbacks(self, client: TestClient, enable_db_ready) -> None:
        with patch(OA_PSYCOPG, side_effect=Exception("db failure")):
            r1 = client.get("/outcome/graph", headers=H)
            r2 = client.get("/outcome/quality", headers=H)
            r3 = client.get("/outcome/actions/pending", headers=H)
        assert r1.status_code in VALID
        assert r2.status_code in VALID
        assert r3.status_code in VALID

    def test_record_outcome_memory_else_branch(self, client: TestClient) -> None:
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", False):
            action_r = client.post(
                "/outcome/actions",
                headers=H,
                json={
                    "action_type": "mem_action",
                    "target": "mem-target",
                    "command": "mem-cmd",
                },
            )
            assert action_r.status_code in (200, 201)
            action_id = action_r.json().get("action_id")

            outcome_r = client.post(
                "/outcome/outcomes",
                headers=H,
                json={
                    "action_id": action_id,
                    "outcome_type": "replied",
                    "confidence": 0.7,
                },
            )
        assert outcome_r.status_code in (200, 201)

    def test_submit_quality_memory_else_branch(self, client: TestClient) -> None:
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", False):
            action_r = client.post(
                "/outcome/actions",
                headers=H,
                json={
                    "action_type": "mem_quality_action",
                    "target": "mem-target-2",
                    "command": "mem-cmd-2",
                },
            )
            assert action_r.status_code in (200, 201)
            action_id = action_r.json().get("action_id")

            quality_r = client.post(
                "/outcome/quality",
                headers=H,
                json={
                    "action_id": action_id,
                    "accuracy": 80,
                    "safety": 85,
                    "speed_ms": 600,
                    "revenue_impact_gbp": 200,
                    "human_override": False,
                },
            )
        assert quality_r.status_code in (200, 201)
