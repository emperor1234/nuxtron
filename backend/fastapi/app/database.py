
"""
SQLAlchemy ORM database layer for Nuxtron platform.

Provides connection pooling, session management, and model base for all routers.
Supports both in-memory (dev) and PostgreSQL (prod) backends.

Usage:
    from .database import get_db_session, init_db
    
    # Initialize on app startup
    init_db()
    
    # In routes
    with get_db_session() as session:
        contacts = session.query(Contact).filter_by(tenant_id=auth.tenant_id).all()
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Ensure both import styles share one module instance and one engine/session factory.
sys.modules['app.database'] = sys.modules[__name__]
sys.modules['backend.fastapi.app.database'] = sys.modules[__name__]

Base = declarative_base()

# ─────────────────────────────────────────────────────────────────────────────
# Database Configuration
# ─────────────────────────────────────────────────────────────────────────────


def _get_database_url() -> str | None:
    """Resolve the PostgreSQL database URL from environment variables.

    Priority: explicit ``DATABASE_URL`` > individual ``POSTGRES_*`` vars.
    """
    if explicit := os.getenv('DATABASE_URL', '').strip():
        return explicit

    # Build from individual POSTGRES_* vars
    host = os.getenv('POSTGRES_HOST', '').strip()
    port = os.getenv('POSTGRES_PORT', '').strip()
    db_name = os.getenv('POSTGRES_DB', '').strip()
    user = os.getenv('POSTGRES_USER', '').strip()
    password = os.getenv('POSTGRES_PASSWORD', '').strip()

    if not (host and db_name and user):
        return None

    port = port or '5432'
    if password:
        return f'postgresql://{user}:{password}@{host}:{port}/{db_name}'
    return f'postgresql://{user}@{host}:{port}/{db_name}'


def _as_sqlalchemy_url(db_url: str) -> str:
    """Force the psycopg3 dialect for SQLAlchemy engines.

    requirements.txt installs psycopg[binary] (psycopg3), not psycopg2, but
    SQLAlchemy's default dialect for a bare "postgresql://" URL is psycopg2
    — without this, create_engine() (here and in alembic/env.py) tries to
    import a driver that was never installed. Not applied inside
    _get_database_url() itself: legacy_main.py's raw psycopg.connect() calls
    that function directly and needs the plain, undecorated URI.
    """
    if db_url.startswith('postgresql://'):
        return 'postgresql+psycopg://' + db_url[len('postgresql://') :]
    return db_url


def _is_production_environment() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _get_engine() -> Engine:
    """Create SQLAlchemy engine with connection pooling."""
    db_url = _get_database_url()

    if not db_url:
        # In production a missing database URL is a fatal misconfiguration: the
        # previous behaviour silently fell back to an in-memory, per-process
        # SQLite database, which means total data loss on every restart and
        # divergent state across workers. Fail loud instead.
        if _is_production_environment():
            logger.critical(
                'No database URL configured (DATABASE_URL / POSTGRES_HOST). '
                'Refusing to start in production with an in-memory database.'
            )
            raise RuntimeError(
                'Database URL is not configured. Set DATABASE_URL or '
                'POSTGRES_* environment variables in production.'
            )
        logger.warning('DATABASE_URL not configured; using in-memory SQLite for development')
        return create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False,
        )

    db_url = _as_sqlalchemy_url(db_url)

    # Production: PostgreSQL with connection pooling.
    engine_kwargs: dict[str, Any] = {
        'pool_pre_ping': True,   # Test connections before use
        'pool_recycle': 3600,    # Recycle connections after 1 hour
        'echo': False,
    }
    # SQLite (file or memory) cannot use the QueuePool defaults.
    if db_url.startswith('sqlite'):
        engine_kwargs['connect_args'] = {'check_same_thread': False}
        engine_kwargs['poolclass'] = StaticPool
    else:
        engine_kwargs['pool_size'] = int(os.getenv('DB_POOL_SIZE', '10'))
        engine_kwargs['max_overflow'] = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    return create_engine(db_url, **engine_kwargs)


# Global engine and session factory (lazy-initialized)
_engine: Engine | None = None
_session_factory: sessionmaker | None = None
_init_lock = threading.Lock()


def _get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _engine, _session_factory
    
    if _session_factory is not None:
        return _session_factory
    
    with _init_lock:
        if _session_factory is not None:
            return _session_factory
        
        _engine = _get_engine()
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
        # Ensure in-memory SQLite has schema available for test sessions.
        if _engine.url.get_backend_name() == 'sqlite':
            Base.metadata.create_all(_engine)
        return _session_factory


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def init_db() -> None:
    """Initialize database schema. Call on app startup.

    SQLite (dev/test): unchanged — ``create_all`` is cheap, harmless, and
    what the test suite depends on for a zero-setup in-memory DB per run.

    PostgreSQL (real deployments): ``create_all`` is NOT run here anymore.
    It only ever adds missing tables/columns additively and silently — it
    cannot alter or drop anything, so relying on it as "the" schema-creation
    path means schema changes have no history, no rollback, and no guarantee
    that what's running matches what any given code revision expects. Alembic
    (``alembic/``, wired to this same ``Base.metadata`` — see
    ``alembic upgrade head``) is now that path. This function instead
    verifies migrations have actually been run (an ``alembic_version`` table
    exists) and fails loud if not, rather than silently leaving the database
    partially or fully unmigrated.
    """
    factory = _get_session_factory()
    engine = factory.kw['bind']

    if engine.url.get_backend_name() == 'sqlite':
        logger.info('SQLite backend: creating tables via create_all (dev/test only).')
        Base.metadata.create_all(engine)
        logger.info('Database initialization complete')
        return

    from sqlalchemy import inspect as sa_inspect

    if not sa_inspect(engine).has_table('alembic_version'):
        message = (
            'PostgreSQL is configured but no Alembic migration history was found '
            "(no 'alembic_version' table). Run `alembic upgrade head` before "
            'starting the app — schema is no longer auto-created against Postgres.'
        )
        if _is_production_environment():
            logger.critical(message)
            raise RuntimeError(message)
        logger.warning(message)
        return

    logger.info('Database schema is Alembic-managed; skipping create_all.')


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.
    
    Usage:
        with get_db_session() as session:
            contacts = session.query(Contact).all()
    """
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session_sync() -> Session:
    """Get a database session (non-context manager version).
    
    Must be closed manually or used with context manager.
    
    Usage:
        session = get_db_session_sync()
        try:
            contacts = session.query(Contact).all()
        finally:
            session.close()
    """
    factory = _get_session_factory()
    return factory()


def close_db() -> None:
    """Close database connections. Call on app shutdown."""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None


def SessionLocal() -> Session:  # noqa: N802
    """Alias for get_db_session_sync, used in test fixtures."""
    factory = _get_session_factory()
    engine = factory.kw['bind']
    if engine.url.get_backend_name() == 'sqlite':
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    return get_db_session_sync()


# ─────────────────────────────────────────────────────────────────────────────
# SQLAlchemy Event Hooks
# ─────────────────────────────────────────────────────────────────────────────


@event.listens_for(Engine, "connect")
def receive_connect(dbapi_conn: Any, connection_record: Any) -> None:
    """Enable foreign keys for SQLite (ignored by PostgreSQL).

    Previously checked ``dbapi_conn.__class__.__name__ == 'pysqlite3.dbapi2.Connection'``,
    which never matched — the stdlib ``sqlite3`` driver SQLAlchemy actually
    uses here reports its class as plain ``Connection`` in module ``sqlite3``,
    not ``pysqlite3.dbapi2``. FK enforcement was silently a no-op for SQLite
    as a result (every FK constraint was accepted but never checked). Checking
    the module name instead of the qualified class name matches correctly.
    """
    if dbapi_conn.__class__.__module__ == 'sqlite3':
        cursor = dbapi_conn.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()


@event.listens_for(Session, 'before_flush')
def _auto_provision_tenants(session: Session, flush_context: Any, instances: Any) -> None:
    """Just-in-time tenant provisioning so the new ``tenant_id`` FK constraints
    (see models.py's ``Tenant``/``BaseTenantModel``) never block normal usage.

    Every tenant-scoped table now has ``tenant_id`` as a real foreign key to
    ``tenant_profiles.tenant_id``. But tenant_id itself has always just been
    "whatever string a valid JWT/API key carries" (deps.py) — no tenant ever
    has to explicitly register before using the product, and requiring that
    would be a real product behavior change, not a schema-hygiene one. This
    event inserts a minimal ``Tenant`` row for any tenant_id it sees being
    written for the first time, in the SAME flush/transaction as the write
    that needed it, so the FK is always satisfied without any caller —
    including the ~90 existing routers — having to change.

    Deliberately does NOT touch ``routers/tenants.py``'s raw-SQL
    ``tenant_profiles`` writes (``POST /tenants`` still work as before,
    upserting richer profile data than this auto-created stub) — this only
    fills in the minimum row needed to satisfy the FK when some OTHER
    tenant-scoped write happens first.
    """
    from .models import BaseTenantModel, Tenant  # local import: avoid import-order cycle at module load

    candidate_tenant_ids: set[str] = set()
    for obj in session.new:
        if isinstance(obj, BaseTenantModel) and not isinstance(obj, Tenant):
            tenant_id = getattr(obj, 'tenant_id', None)
            if isinstance(tenant_id, str) and tenant_id:
                candidate_tenant_ids.add(tenant_id)

    if not candidate_tenant_ids:
        return

    # Exclude tenant_ids already present in this same flush's new Tenant rows
    # (e.g. a real POST /tenants-style creation happening in the same session).
    already_creating = {
        obj.tenant_id for obj in session.new
        if isinstance(obj, Tenant) and isinstance(getattr(obj, 'tenant_id', None), str)
    }
    candidate_tenant_ids -= already_creating

    if not candidate_tenant_ids:
        return

    existing = {
        row[0] for row in session.query(Tenant.tenant_id).filter(Tenant.tenant_id.in_(candidate_tenant_ids)).all()
    }
    to_create = candidate_tenant_ids - existing
    if not to_create:
        return

    # Deliberately session.execute(insert(...)) rather than session.add(Tenant(...)):
    # the unit-of-work's insert ordering is derived from mapper-level
    # relationship()s, which BaseTenantModel subclasses don't declare to
    # Tenant (they only have the bare column-level FK). Without that,
    # SQLAlchemy has no reason to order the Tenant insert before e.g. the
    # Lead insert that needed it, and the FK constraint fails. A Core insert
    # executes immediately against the current transaction, before flush's
    # mapper-persistence phase runs, so ordering is guaranteed.
    from sqlalchemy import insert
    now = datetime.now(UTC)
    session.execute(
        insert(Tenant.__table__),
        [
            {
                'tenant_id': tenant_id,
                'display_name_cipher': None,
                'display_name_preview': '',
                'plan': 'starter',
                'status': 'active',
                'settings_json': {},
                'created_at': now,
                'updated_at': now,
            }
            for tenant_id in to_create
        ],
    )
