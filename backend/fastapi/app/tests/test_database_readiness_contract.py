from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from backend.fastapi.app import database


def test_engine_requires_explicit_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    with pytest.raises(RuntimeError, match="ENVIRONMENT must be explicitly set"):
        database._get_engine()


def test_postgres_readiness_requires_all_current_alembic_heads() -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
            connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('stale-revision')"))

        with pytest.raises(RuntimeError, match="do not match the application heads"):
            database._assert_current_alembic_revision(engine)

        current_head = next(iter(database._expected_alembic_heads()))
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM alembic_version"))
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": current_head},
            )

        database._assert_current_alembic_revision(engine)
    finally:
        engine.dispose()


def test_postgres_readiness_rejects_missing_migration_table() -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        with pytest.raises(RuntimeError, match="No Alembic migration history"):
            database._assert_current_alembic_revision(engine)
    finally:
        engine.dispose()
