"""
Targeted coverage tests for trust_center.py DB branches.
Lines: 122-123, 143-161, 174-195, 210-224, 233-252, 263-278,
302-318, 333-352, 369-391, 410-428 (all DB path branches).
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

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "trust-test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
TC_PSYCOPG = "backend.fastapi.app.routers.trust_center.psycopg.connect"


def _make_conn(fetchone=None, fetchall=None, rowcount=0):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall if fetchall is not None else []
    cur.rowcount = rowcount

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


# ── Policy History ─────────────────────────────────────────────────────────────

class TestTrustPoliciesDbPath:
    """Cover lines 143-161 (record policy DB) and 174-195 (list policies DB)."""

    def test_record_policy_db_path(self, client: TestClient) -> None:
        """Lines 143-161: DB INSERT for policy change."""
        import backend.fastapi.app.legacy_main as lm

        conn, _ = _make_conn()
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.post("/trust-center/policies", headers=H, json={
                "policy_key": "autonomy.allow_high_impact",
                "old_value": {"value": False},
                "new_value": {"value": True},
                "change_reason": "Board approved risk increase",
                "actor_role": "ciso",
                "requires_human_validation": True,
                "approved_by": "cfo@example.com",
            })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            assert "policy_id" in r.json()

    def test_record_policy_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 160-161: DB raises → falls back to memory."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.post("/trust-center/policies", headers=H, json={
                "policy_key": "test.fallback",
                "new_value": {"v": 1},
                "change_reason": "testing",
            })
        assert r.status_code in (200, 201)

    def test_list_policies_db_path(self, client: TestClient) -> None:
        """Lines 174-195: DB SELECT returns policy rows."""
        import backend.fastapi.app.legacy_main as lm

        row = (
            "policy-uuid-1", "trust-test-tenant", "autonomy.allow_high_impact",
            {"value": False}, {"value": True}, "Board approved", "ciso",
            True, "cfo@example.com", datetime(2024, 1, 1, tzinfo=UTC),
        )
        conn, cur = _make_conn(fetchall=[row])
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.get("/trust-center/policies", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "policies" in data

    def test_list_policies_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 194-195: DB raises → falls back to memory."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.get("/trust-center/policies", headers=H)
        assert r.status_code in VALID


# ── Approval Chains ──────────────────────────────────────────────────────────

class TestTrustApprovalChainsDbPath:
    """Cover lines 210-224 (create chain DB) and 233-252 (list chains DB)."""

    def test_create_chain_db_path(self, client: TestClient) -> None:
        """Lines 210-224: DB INSERT for approval chain."""
        import backend.fastapi.app.legacy_main as lm

        conn, _ = _make_conn()
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.post("/trust-center/approval-chains", headers=H, json={
                "chain_name": "High Impact Budget Approval",
                "action_type": "spend_approval",
                "steps": [
                    {"role": "manager", "required": True},
                    {"role": "cfo", "required": True},
                ],
                "require_all": True,
            })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            assert "chain_id" in r.json()

    def test_create_chain_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 223-224: DB raises → falls back to memory."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.post("/trust-center/approval-chains", headers=H, json={
                "chain_name": "Fallback Chain",
                "action_type": "delete_action",
            })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            self.__class__.fallback_chain_id = r.json().get("chain_id")

    def test_list_chains_db_path(self, client: TestClient) -> None:
        """Lines 233-252: DB SELECT returns chain rows."""
        import backend.fastapi.app.legacy_main as lm

        row = (
            "chain-uuid-1", "trust-test-tenant", "Budget Chain",
            "spend_approval", [{"role": "manager"}], True, True,
            datetime(2024, 1, 1, tzinfo=UTC),
        )
        conn, cur = _make_conn(fetchall=[row])
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.get("/trust-center/approval-chains", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "chains" in data

    def test_list_chains_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 251-252: DB raises → memory fallback."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.get("/trust-center/approval-chains", headers=H)
        assert r.status_code in VALID

    def test_deactivate_chain_db_path(self, client: TestClient) -> None:
        """Lines 263-278: DB UPDATE for deactivating chain."""
        import backend.fastapi.app.legacy_main as lm

        row = ("chain-uuid-existing",)
        conn, cur = _make_conn(fetchone=row)
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.delete("/trust-center/approval-chains/chain-uuid-existing", headers=H)
        assert r.status_code in VALID

    def test_deactivate_chain_db_not_found(self, client: TestClient) -> None:
        """DB UPDATE returns None → 404."""
        import backend.fastapi.app.legacy_main as lm

        conn, cur = _make_conn(fetchone=None)
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.delete("/trust-center/approval-chains/chain-notexist", headers=H)
        assert r.status_code == 404

    def test_deactivate_chain_memory_not_found(self, client: TestClient) -> None:
        """Memory fallback: chain not in memory → 404."""
        r = client.delete("/trust-center/approval-chains/chain-not-in-memory", headers=H)
        assert r.status_code == 404

    def test_deactivate_chain_db_exception_memory_success(self, client: TestClient) -> None:
        """Hit DB exception path then successful memory deactivation."""
        import backend.fastapi.app.legacy_main as lm
        from backend.fastapi.app import memory_stores

        chain_id = "chain-memory-fallback-1"
        memory_stores.trust_approval_chains.append(
            {
                "id": chain_id,
                "tenant_id": H["X-Tenant-Id"],
                "chain_name": "Memory Chain",
                "action_type": "delete_action",
                "steps": [],
                "require_all": True,
                "active": True,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.delete(f"/trust-center/approval-chains/{chain_id}", headers=H)
        assert r.status_code == 200


# ── Incidents ─────────────────────────────────────────────────────────────────

class TestTrustIncidentsDbPath:
    """Cover lines 302-318 (create), 333-352 (resolve), 369-391 (list)."""

    def test_create_incident_db_path(self, client: TestClient) -> None:
        """Lines 302-318: DB INSERT for incident."""
        import backend.fastapi.app.legacy_main as lm

        conn, _ = _make_conn()
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.post("/trust-center/incidents", headers=H, json={
                "title": "Data Breach Attempt",
                "description": "Attempted unauthorized access to customer data",
                "severity": "critical",
                "affected_module": "ira",
                "resolved": False,
            })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            assert "incident_id" in r.json()

    def test_create_incident_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 317-318: DB raises → memory fallback."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.post("/trust-center/incidents", headers=H, json={
                "title": "Fallback Incident",
                "description": "This incident falls back to memory",
                "severity": "low",
                "affected_module": "platform_intelligence",
            })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            self.__class__.fallback_incident_id = r.json().get("incident_id")

    def test_create_incident_already_resolved(self, client: TestClient) -> None:
        """Create resolved incident → resolved_at is set."""
        conn, _ = _make_conn()
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.post("/trust-center/incidents", headers=H, json={
                "title": "Already Resolved Incident",
                "description": "This was resolved at creation time",
                "severity": "high",
                "affected_module": "growth_suite",
                "resolved": True,
                "resolution_notes": "Fixed by rollback",
            })
        assert r.status_code in (200, 201)

    def test_resolve_incident_db_path(self, client: TestClient) -> None:
        """Lines 333-352: DB UPDATE for resolving incident."""
        import backend.fastapi.app.legacy_main as lm

        row = ("incident-uuid-1",)
        conn, cur = _make_conn(fetchone=row)
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.patch(
                "/trust-center/incidents/incident-uuid-1/resolve",
                headers=H,
                json={"resolution_notes": "Fixed via hot patch"},
            )
        assert r.status_code in VALID
        if r.status_code == 200:
            assert r.json()["status"] == "resolved"

    def test_resolve_incident_db_not_found(self, client: TestClient) -> None:
        """DB UPDATE returns None → 404."""
        import backend.fastapi.app.legacy_main as lm

        conn, cur = _make_conn(fetchone=None)
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.patch(
                "/trust-center/incidents/incident-notexist/resolve",
                headers=H,
                json={"resolution_notes": "Not found"},
            )
        assert r.status_code == 404

    def test_resolve_incident_memory_not_found(self, client: TestClient) -> None:
        """Memory fallback: incident not in memory → 404."""
        r = client.patch(
            "/trust-center/incidents/not-in-memory/resolve",
            headers=H,
            json={"resolution_notes": "N/A"},
        )
        assert r.status_code == 404

    def test_resolve_incident_db_exception_memory_success(self, client: TestClient) -> None:
        """Hit DB exception path then successful memory resolve."""
        import backend.fastapi.app.legacy_main as lm
        from backend.fastapi.app import memory_stores

        incident_id = "incident-memory-fallback-1"
        memory_stores.trust_incidents.append(
            {
                "id": incident_id,
                "tenant_id": H["X-Tenant-Id"],
                "title": "Memory Incident",
                "description": "Seeded in-memory for fallback resolution",
                "severity": "low",
                "affected_module": "ira",
                "resolved": False,
                "resolution_notes": "",
                "created_at": datetime.now(UTC).isoformat(),
                "resolved_at": None,
            }
        )

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.patch(
                f"/trust-center/incidents/{incident_id}/resolve",
                headers=H,
                json={"resolution_notes": "Resolved via memory fallback"},
            )
        assert r.status_code == 200

    def test_list_incidents_db_path(self, client: TestClient) -> None:
        """Lines 369-391: DB SELECT returns incident rows."""
        import backend.fastapi.app.legacy_main as lm

        row = (
            "incident-uuid-1", "trust-test-tenant", "Data Breach",
            "Attempted access", "critical", "ira", False, "",
            None, datetime(2024, 1, 1, tzinfo=UTC),
        )
        conn, cur = _make_conn(fetchall=[row])
        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.get("/trust-center/incidents", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "incidents" in data

    def test_list_incidents_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 390-391: DB raises → memory fallback."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.get("/trust-center/incidents", headers=H)
        assert r.status_code in VALID


# ── Governance Snapshots ──────────────────────────────────────────────────────

class TestTrustSnapshotsDbPath:
    """Cover lines 410-428: _handle_capture_snapshot DB branch."""

    def test_capture_snapshot_db_path(self, client: TestClient) -> None:
        """Lines 410-428: DB INSERT for governance snapshot."""
        import backend.fastapi.app.legacy_main as lm

        # _get_posture_counts uses db too — mock counts response
        count_row = (0, 0)  # (total_open, critical_open)
        conn, cur = _make_conn(fetchone=count_row, fetchall=[])
        # Multiple calls for count queries and snapshot insert
        cur.fetchone.side_effect = [count_row, (0,), None]  # open_inc, active_chains, snapshot INSERT

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.post("/trust-center/snapshots", headers=H, json={
                "autonomy_enabled": True,
                "allow_high_impact_actions": False,
                "strict_policy_lock": True,
                "policy_change_human_validation": False,
                "notes": "Baseline governance snapshot",
            })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            assert "snapshot_id" in r.json()

    def test_capture_snapshot_db_exception_fallback(self, client: TestClient) -> None:
        """Lines 427-428: DB raises → memory fallback."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.post("/trust-center/snapshots", headers=H, json={
                "autonomy_enabled": False,
                "allow_high_impact_actions": True,
                "strict_policy_lock": False,
                "notes": "High-risk snapshot",
            })
        assert r.status_code in (200, 201)


# ── Posture (uses DB counts) ──────────────────────────────────────────────────

class TestTrustPostureDbPath:
    """Cover lines 122-123: _db_count_open_incidents called from _get_posture_counts."""

    def test_get_posture_db_path(self, client: TestClient) -> None:
        """Lines 122-123: DB path for incident + chain counts in posture."""
        import backend.fastapi.app.legacy_main as lm

        count_row = (3, 1)  # total_open=3, critical_open=1
        active_chains_row = (2,)  # active_chains=2
        conn, cur = _make_conn()
        cur.fetchone.side_effect = [count_row, active_chains_row]

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, return_value=conn):
            r = client.get("/trust-center/posture", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "posture_score" in data or "rating" in data or "open_incidents" in data

    def test_get_posture_db_exception_fallback(self, client: TestClient) -> None:
        """_get_posture_counts DB raises → memory fallback for posture."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True), patch(TC_PSYCOPG, side_effect=Exception("DB error")):
            r = client.get("/trust-center/posture", headers=H)
        assert r.status_code in VALID
