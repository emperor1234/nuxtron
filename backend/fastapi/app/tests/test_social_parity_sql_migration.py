from __future__ import annotations

import sqlite3
from pathlib import Path


def test_social_parity_sql_migration_creates_required_tables(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[4]
    migration_path = repo_root / "services" / "fastapi" / "sql" / "20260523_social_parity_state_schema.sql"

    assert migration_path.exists(), "Expected social parity migration file to exist"
    sql_text = migration_path.read_text(encoding="utf-8")

    db_path = tmp_path / "migration_check.sqlite"
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(sql_text)

        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('social_parity_state', 'social_parity_state_versions')"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "social_parity_state" in tables
        assert "social_parity_state_versions" in tables

        index_cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_social_parity_state_versions_tenant_created_at'"
        )
        assert index_cursor.fetchone() is not None
    finally:
        connection.close()
