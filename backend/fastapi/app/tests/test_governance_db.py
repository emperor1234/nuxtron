from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ..governance_db import (
    _GOVERNANCE_TABLES,
    GovernanceDB,
    UnknownGovernanceTableError,
    _validated_table,
)


def _make_mock_conn(fetchall_side_effect=None):
    cur = MagicMock()
    cur.fetchall.side_effect = fetchall_side_effect or [[], [], []]
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


def test_load_all_uses_postgres_tables() -> None:
    provider_rows = [("{\"tenant_id\": \"tenant-a\", \"id\": 1, \"name\": \"Provider A\"}",)]
    usage_rows = [("{\"tenant_id\": \"tenant-a\", \"id\": 2, \"request_path\": \"/api\"}",)]
    incident_rows = [("{\"tenant_id\": \"tenant-a\", \"id\": 3, \"title\": \"Incident A\"}",)]
    conn, _cur = _make_mock_conn([provider_rows, usage_rows, incident_rows])

    with patch("backend.fastapi.app.governance_db.psycopg.connect", return_value=conn):
        db = GovernanceDB(db_dsn="postgresql://example")
        providers, usages, incidents = db.load_all()

    assert providers[0]["name"] == "Provider A"
    assert usages[0]["request_path"] == "/api"
    assert incidents[0]["title"] == "Incident A"


def test_save_all_replaces_each_table() -> None:
    conn, cur = _make_mock_conn()

    with patch("backend.fastapi.app.governance_db.psycopg.connect", return_value=conn):
        db = GovernanceDB(db_dsn="postgresql://example")
        db.save_all(
            [{"tenant_id": "tenant-a", "id": 1, "name": "Provider A"}],
            [{"tenant_id": "tenant-a", "id": 2, "request_path": "/api"}],
            [{"tenant_id": "tenant-a", "id": 3, "title": "Incident A"}],
        )

    executed_sql = [str(call.args[0]) for call in cur.execute.call_args_list]
    assert any(sql.startswith('DELETE FROM gov_providers') for sql in executed_sql)
    assert any(sql.startswith('DELETE FROM gov_usage_events') for sql in executed_sql)
    assert any(sql.startswith('DELETE FROM gov_incidents') for sql in executed_sql)
    assert any('INSERT INTO gov_providers' in sql for sql in executed_sql)
    assert any('INSERT INTO gov_usage_events' in sql for sql in executed_sql)
    assert any('INSERT INTO gov_incidents' in sql for sql in executed_sql)


class TestValidatedTable:
    """WO-5: SQL identifier allowlist validation."""

    def test_known_table_passes_through(self) -> None:
        for known in _GOVERNANCE_TABLES:
            assert _validated_table(known) == known

    def test_unknown_table_rejected(self) -> None:
        with pytest.raises(UnknownGovernanceTableError):
            _validated_table('not_a_real_table')

    def test_injection_attempt_rejected(self) -> None:
        payloads = [
            'gov_providers; DROP TABLE users; --',
            "' OR '1'='1",
            'gov_providers UNION SELECT * FROM users',
            '',
        ]
        for payload in payloads:
            with pytest.raises(UnknownGovernanceTableError):
                _validated_table(payload)