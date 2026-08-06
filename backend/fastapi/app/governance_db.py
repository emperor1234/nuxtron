"""
PostgreSQL-backed persistence for API governance stores.

Governance data (providers, usage events, incidents) must survive app restarts.
All sensitive fields (provider tokens) are already AES-256-GCM encrypted by the
time they reach this module — we store the encrypted ciphertext only.

Usage:
    from .governance_db import GovernanceDB
    db = GovernanceDB()
    providers, usages, incidents = db.load_all()
    db.save_all(providers, usages, incidents)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import psycopg

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

_GOVERNANCE_TABLES = (
    'gov_providers',
    'gov_usage_events',
    'gov_incidents',
)


class UnknownGovernanceTableError(ValueError):
    """Raised when code attempts to interpolate a table name that is not on the
    reviewed allowlist. This is a security control, not a convenience check — do
    not broaden ``_GOVERNANCE_TABLES`` casually; each entry should be a table
    this module is actually responsible for managing."""


def _validated_table(name: str) -> str:
    """Return ``name`` only if it is on the static allowlist of governance
    tables. Refuses anything else (including obvious injection payloads) so
    that f-string identifier interpolation here can never execute attacker-
    controlled SQL, even if a future change accidentally routes user input
    through this path."""
    if name not in _GOVERNANCE_TABLES:
        raise UnknownGovernanceTableError(
            f"'{name}' is not in _GOVERNANCE_TABLES; refusing to interpolate "
            'it into SQL. If this is a legitimate new governance table, add '
            'it to _GOVERNANCE_TABLES explicitly — do not bypass this check.'
        )
    return name


def _db_dsn_from_env() -> str:
    """Build a libpq keyword/value DSN from the standard connection env vars.

    Priority: ``DATABASE_URL`` (full URL) → individual ``POSTGRES_*`` vars.
    """
    direct = os.getenv('DATABASE_URL', '').strip()
    if direct:
        return direct

    host = os.getenv('POSTGRES_HOST', 'localhost').strip()
    port = os.getenv('POSTGRES_PORT', '5432').strip()
    db_name = os.getenv('POSTGRES_DB', 'nuxtron').strip()
    user = os.getenv('POSTGRES_USER', 'nuxtron').strip()
    password = os.getenv('POSTGRES_PASSWORD', '').strip()
    parts = [
        f'host={host}',
        f'port={port}',
        f'dbname={db_name}',
        f'user={user}',
        'connect_timeout=5',
    ]
    if password:
        parts.insert(4, f'password={password}')
    return ' '.join(parts)


class GovernanceDB:
    """Thread-safe PostgreSQL persistence layer for governance stores.

    The database DSN is resolved from ``DATABASE_URL`` first, then the
    standard ``POSTGRES_*`` environment variables used elsewhere in the repo.
    """

    def __init__(
        self,
        db_dsn: str | None = None,
        db_dsn_fn: Callable[[], str] | None = None,
    ) -> None:
        self._db_dsn = db_dsn
        self._db_dsn_fn = db_dsn_fn or _db_dsn_from_env
        self._backend: str = 'postgres'
        self._sqlite_path = Path(os.getenv('GOVERNANCE_DB_FALLBACK_PATH', './data/governance_fallback.db')).expanduser()
        self._lock = threading.Lock()
        self._init_schema()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_all(self) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject]]:
        """Return (providers, usage_events, incidents) loaded from PostgreSQL."""
        if self._backend == 'sqlite':
            return self._load_all_sqlite()
        with self._lock, self._connect() as conn:
            providers = self._load_table(conn, 'gov_providers')
            usages = self._load_table(conn, 'gov_usage_events')
            incidents = self._load_table(conn, 'gov_incidents')
        return providers, usages, incidents

    def save_all(
        self,
        providers: list[JsonObject],
        usage_events: list[JsonObject],
        incidents: list[JsonObject],
    ) -> None:
        """Atomically replace all three store tables with current in-memory state."""
        if self._backend == 'sqlite':
            self._save_all_sqlite(providers, usage_events, incidents)
            return
        with self._lock, self._connect() as conn:
            self._replace_table(conn, 'gov_providers', providers)
            self._replace_table(conn, 'gov_usage_events', usage_events)
            self._replace_table(conn, 'gov_incidents', incidents)

    def save_providers(self, providers: list[JsonObject]) -> None:
        if self._backend == 'sqlite':
            self._save_table_sqlite('gov_providers', providers)
            return
        with self._lock, self._connect() as conn:
            self._replace_table(conn, 'gov_providers', providers)

    def save_usage_events(self, usage_events: list[JsonObject]) -> None:
        if self._backend == 'sqlite':
            self._save_table_sqlite('gov_usage_events', usage_events)
            return
        with self._lock, self._connect() as conn:
            self._replace_table(conn, 'gov_usage_events', usage_events)

    def save_incidents(self, incidents: list[JsonObject]) -> None:
        if self._backend == 'sqlite':
            self._save_table_sqlite('gov_incidents', incidents)
            return
        with self._lock, self._connect() as conn:
            self._replace_table(conn, 'gov_incidents', incidents)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _dsn(self) -> str:
        if self._db_dsn:
            return self._db_dsn
        dsn = self._db_dsn_fn().strip()
        if not dsn:
            raise RuntimeError('GovernanceDB: PostgreSQL DSN is not configured')
        return dsn

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn())

    def _connect_sqlite(self) -> sqlite3.Connection:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        try:
            with self._lock, self._connect() as conn, conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS gov_providers (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        data JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS gov_usage_events (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        data JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS gov_incidents (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        data JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                for table in _GOVERNANCE_TABLES:
                    cur.execute(f'CREATE INDEX IF NOT EXISTS {_validated_table(table)}_tenant_idx ON {_validated_table(table)} (tenant_id)')
        except Exception:
            self._backend = 'sqlite'
            self._init_schema_sqlite()

    def _init_schema_sqlite(self) -> None:
        try:
            with self._lock, self._connect_sqlite() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gov_providers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        data TEXT NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gov_usage_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        data TEXT NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gov_incidents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        data TEXT NOT NULL
                    )
                    """
                )
                for table in _GOVERNANCE_TABLES:
                    cur.execute(f'CREATE INDEX IF NOT EXISTS {_validated_table(table)}_tenant_idx ON {_validated_table(table)} (tenant_id)')
                conn.commit()
            logger.warning('GovernanceDB: PostgreSQL unavailable; using SQLite fallback at %s', self._sqlite_path)
        except Exception:
            logger.exception('GovernanceDB: fallback schema init failed — governance data will not persist')

    def _load_table(self, conn: psycopg.Connection[Any], table: str) -> list[JsonObject]:
        rows: list[JsonObject] = []
        try:
            with conn.cursor() as cur:
                # Table names are constrained by _GOVERNANCE_TABLES.
                cur.execute(f'SELECT data FROM {_validated_table(table)} ORDER BY id')  # noqa: S608  # nosec B608
                for (data_value,) in cur.fetchall():
                    try:
                        if isinstance(data_value, str):
                            obj = json.loads(data_value)
                        else:
                            obj = data_value
                        if isinstance(obj, dict):
                            rows.append(obj)
                    except json.JSONDecodeError:
                        logger.warning('GovernanceDB: skipped corrupt row in %s', table)
        except Exception:
            logger.exception('GovernanceDB: failed to load table %s', table)
        return rows

    def _replace_table(
        self, conn: psycopg.Connection[Any], table: str, rows: list[JsonObject]
    ) -> None:
        """Delete-and-reinsert for simplicity (tables are small, transactions are atomic)."""
        try:
            with conn.cursor() as cur:
                # Table names are constrained by _GOVERNANCE_TABLES.
                cur.execute(f'DELETE FROM {_validated_table(table)}')  # noqa: S608  # nosec B608
                for row in rows:
                    tenant_id = str(row.get('tenant_id', '') or '').strip()
                    cur.execute(
                        f'INSERT INTO {table} (tenant_id, data) VALUES (%s, %s::jsonb)',  # noqa: S608  # nosec B608
                        (tenant_id, json.dumps(row, default=str)),
                    )
        except Exception:
            logger.exception('GovernanceDB: failed to persist table %s', table)

    def _load_table_sqlite(self, table: str) -> list[JsonObject]:
        rows: list[JsonObject] = []
        try:
            with self._connect_sqlite() as conn:
                cur = conn.cursor()
                # Table names are constrained by _GOVERNANCE_TABLES.
                cur.execute(f'SELECT data FROM {_validated_table(table)} ORDER BY id')  # noqa: S608  # nosec B608
                for row in cur.fetchall():
                    try:
                        value = row['data']
                        obj = json.loads(value) if isinstance(value, str) else value
                        if isinstance(obj, dict):
                            rows.append(obj)
                    except json.JSONDecodeError:
                        logger.warning('GovernanceDB: skipped corrupt SQLite row in %s', table)
        except Exception:
            logger.exception('GovernanceDB: failed to load SQLite table %s', table)
        return rows

    def _save_table_sqlite(self, table: str, rows: list[JsonObject]) -> None:
        try:
            with self._connect_sqlite() as conn:
                cur = conn.cursor()
                # Table names are constrained by _GOVERNANCE_TABLES.
                cur.execute(f'DELETE FROM {_validated_table(table)}')  # noqa: S608  # nosec B608
                for row in rows:
                    tenant_id = str(row.get('tenant_id', '') or '').strip()
                    cur.execute(
                        f'INSERT INTO {table} (tenant_id, data) VALUES (?, ?)',  # noqa: S608  # nosec B608
                        (tenant_id, json.dumps(row, default=str)),
                    )
                conn.commit()
        except Exception:
            logger.exception('GovernanceDB: failed to persist SQLite table %s', table)

    def _load_all_sqlite(self) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject]]:
        return (
            self._load_table_sqlite('gov_providers'),
            self._load_table_sqlite('gov_usage_events'),
            self._load_table_sqlite('gov_incidents'),
        )

    def _save_all_sqlite(
        self,
        providers: list[JsonObject],
        usage_events: list[JsonObject],
        incidents: list[JsonObject],
    ) -> None:
        self._save_table_sqlite('gov_providers', providers)
        self._save_table_sqlite('gov_usage_events', usage_events)
        self._save_table_sqlite('gov_incidents', incidents)
