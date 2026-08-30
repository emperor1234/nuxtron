"""Database initialization and table creation utilities."""

import logging
import os
import threading
from datetime import UTC, datetime

import psycopg

from .database import _get_database_url

logger = logging.getLogger(__name__)

# Module-level state
_db_ready = False
_db_init_attempted = False
_db_init_lock = threading.Lock()


def db_dsn() -> str:
    """Get the database connection string for psycopg.
    
    Prefers DATABASE_URL (> POSTGRES_* vars) precedence the SQLAlchemy engine
    already uses in database.py.
    """
    if url := _get_database_url():
        separator = '&' if '?' in url else '?'
        return f'{url}{separator}connect_timeout=2'

    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'nuxtron')
    user = os.getenv('POSTGRES_USER', 'nuxtron')
    password = os.getenv('POSTGRES_PASSWORD', '')
    return f"host={host} port={port} dbname={db_name} user={user} password={password} connect_timeout=2"


def apply_startup_db_timeouts(conn: psycopg.Connection) -> None:
    """Apply timeout settings for startup DDL operations.
    
    Startup DDL should fail fast under lock contention so memory fallback remains usable.
    """
    conn.execute("SET lock_timeout = '2000ms'")
    conn.execute("SET statement_timeout = '5000ms'")


def is_db_ready() -> bool:
    """Check if the database is ready."""
    return _db_ready


# Export the variable directly for backward compatibility
__all__ = [
    'db_dsn',
    'init_db_tables',
    'is_db_ready',
    'set_db_ready',
    'set_db_init_attempted',
    'get_db_init_lock',
    'apply_startup_db_timeouts',
]


def init_social_table() -> None:
    """Initialize the social_scheduled_posts table."""
    global _db_ready
    try:
        with psycopg.connect(db_dsn()) as conn:
            apply_startup_db_timeouts(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS social_scheduled_posts (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        text_cipher TEXT NOT NULL,
                        text_preview TEXT NOT NULL,
                        publish_at TIMESTAMPTZ NOT NULL,
                        media_urls TEXT[] NOT NULL DEFAULT '{}',
                        status TEXT NOT NULL DEFAULT 'scheduled',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute("ALTER TABLE social_scheduled_posts ADD COLUMN IF NOT EXISTS text_cipher TEXT")
                cur.execute("ALTER TABLE social_scheduled_posts ADD COLUMN IF NOT EXISTS text_preview TEXT")
                cur.execute(
                    """
                    UPDATE social_scheduled_posts
                    SET text_cipher = COALESCE(text_cipher, text_preview, ''),
                        text_preview = COALESCE(text_preview, '[encrypted]')
                    WHERE text_cipher IS NULL OR text_preview IS NULL
                    """
                )
            conn.commit()
        _db_ready = True
    except Exception:
        logger.exception('Failed to initialize social table')
        _db_ready = False


def init_email_tables() -> None:
    """Initialize email-related tables."""
    if not _db_ready:
        return

    with psycopg.connect(db_dsn()) as conn:
        apply_startup_db_timeouts(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS email_contacts (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    email_cipher TEXT NOT NULL,
                    email_preview TEXT NOT NULL,
                    name_cipher TEXT,
                    name_preview TEXT,
                    tags TEXT[] NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS email_campaigns (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_cipher TEXT NOT NULL,
                    subject_preview TEXT NOT NULL,
                    body_cipher TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    provider TEXT NOT NULL DEFAULT 'listmonk',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS security_alert_emails (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'smtp-queue',
                    to_email TEXT NOT NULL,
                    from_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TIMESTAMPTZ,
                    locked_at TIMESTAMPTZ,
                    delivery_detail TEXT,
                    requeued_by TEXT,
                    requeued_source_ip TEXT,
                    requeued_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("ALTER TABLE security_alert_emails ADD COLUMN IF NOT EXISTS requeued_by TEXT")
            cur.execute("ALTER TABLE security_alert_emails ADD COLUMN IF NOT EXISTS requeued_source_ip TEXT")
            cur.execute("ALTER TABLE security_alert_emails ADD COLUMN IF NOT EXISTS requeued_at TIMESTAMPTZ")
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_security_alert_emails_dispatch
                ON security_alert_emails (tenant_id, status, next_attempt_at, id)
                """
            )
        conn.commit()


def init_tenant_tables() -> None:
    """Initialize tenant profile tables."""
    if not _db_ready:
        return

    with psycopg.connect(db_dsn()) as conn:
        apply_startup_db_timeouts(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tenant_profiles (
                    tenant_id TEXT PRIMARY KEY,
                    display_name_cipher TEXT,
                    display_name_preview TEXT,
                    plan TEXT NOT NULL DEFAULT 'starter',
                    status TEXT NOT NULL DEFAULT 'active',
                    settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()


def init_users_table() -> None:
    """Initialize the users table."""
    if not _db_ready:
        return

    with psycopg.connect(db_dsn()) as conn:
        apply_startup_db_timeouts(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    email_hash TEXT NOT NULL,
                    email_cipher TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    name_cipher TEXT,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    reset_token TEXT,
                    reset_token_expires TIMESTAMPTZ,
                    roles TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(tenant_id, email_hash)
                )
                """
            )
            # Comma-separated JWT roles claim (e.g. 'admin', 'user,billing') —
            # persisted so a returning user keeps their assigned role instead
            # of every login re-issuing a token with the default 'user'.
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS roles TEXT NOT NULL DEFAULT 'user'")
        conn.commit()


def init_flywheel_tables() -> None:
    """Initialize flywheel module tables (outcome attribution, trust center, playbooks, benchmarks)."""
    if not _db_ready:
        return

    with psycopg.connect(db_dsn()) as conn:
        apply_startup_db_timeouts(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS outcome_actions (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
                    impact_level TEXT NOT NULL DEFAULT 'medium',
                    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
                    approved_by TEXT,
                    executed BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS outcome_outcomes (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    action_id UUID REFERENCES outcome_actions(id) ON DELETE SET NULL,
                    outcome_type TEXT NOT NULL,
                    value_delta DOUBLE PRECISION,
                    currency TEXT DEFAULT 'GBP',
                    attributed_revenue DOUBLE PRECISION DEFAULT 0,
                    confidence DOUBLE PRECISION DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS outcome_quality_scores (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    action_id UUID REFERENCES outcome_actions(id) ON DELETE SET NULL,
                    score DOUBLE PRECISION NOT NULL DEFAULT 0,
                    reasoning TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS trust_policy_history (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    policy_key TEXT NOT NULL,
                    old_value JSONB,
                    new_value JSONB NOT NULL DEFAULT '{}',
                    change_reason TEXT NOT NULL,
                    actor_role TEXT NOT NULL DEFAULT 'admin',
                    requires_human_validation BOOLEAN NOT NULL DEFAULT FALSE,
                    approved_by TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS trust_approval_chains (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    chain_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    steps JSONB NOT NULL DEFAULT '[]',
                    require_all BOOLEAN NOT NULL DEFAULT TRUE,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS trust_incidents (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'medium',
                    affected_module TEXT NOT NULL DEFAULT 'ira',
                    resolved BOOLEAN NOT NULL DEFAULT FALSE,
                    resolution_notes TEXT,
                    resolved_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS trust_governance_snapshots (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    autonomy_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    allow_high_impact_actions BOOLEAN NOT NULL DEFAULT FALSE,
                    strict_policy_lock BOOLEAN NOT NULL DEFAULT TRUE,
                    policy_change_human_validation BOOLEAN NOT NULL DEFAULT FALSE,
                    active_approval_chains INTEGER NOT NULL DEFAULT 0,
                    open_incidents INTEGER NOT NULL DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS playbooks (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    vertical TEXT NOT NULL DEFAULT 'all',
                    description TEXT NOT NULL,
                    steps JSONB NOT NULL DEFAULT '[]',
                    integrations JSONB NOT NULL DEFAULT '[]',
                    roi_target JSONB NOT NULL DEFAULT '{}',
                    time_to_value_days INTEGER NOT NULL DEFAULT 1,
                    built_in BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS playbook_runs (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    playbook_id TEXT NOT NULL,
                    playbook_name TEXT,
                    config JSONB NOT NULL DEFAULT '{}',
                    dry_run BOOLEAN NOT NULL DEFAULT TRUE,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    steps_total INTEGER NOT NULL DEFAULT 0,
                    steps_completed INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    baseline_value DOUBLE PRECISION,
                    uplift_pct DOUBLE PRECISION,
                    period_label TEXT NOT NULL,
                    segment TEXT NOT NULL DEFAULT 'all',
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS segment_benchmarks (
                    id UUID PRIMARY KEY,
                    segment TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    p50 DOUBLE PRECISION NOT NULL,
                    p75 DOUBLE PRECISION NOT NULL,
                    p90 DOUBLE PRECISION NOT NULL,
                    period_label TEXT NOT NULL,
                    sample_size INTEGER NOT NULL,
                    published_by_tenant TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        conn.commit()


def init_db_tables() -> None:
    """Initialize all database tables at startup.
    
    This is the main entry point for database initialization.
    Uses CREATE TABLE IF NOT EXISTS for idempotent initialization.
    """
    global _db_ready, _db_init_attempted

    if os.getenv('NUXTRON_SKIP_STARTUP_DB_INIT', '').strip().lower() in {'1', 'true', 'yes'}:
        _db_ready = False
        _db_init_attempted = True
        return

    if _db_ready or _db_init_attempted:
        return

    with _db_init_lock:
        if _db_ready or _db_init_attempted:
            return

        try:
            init_social_table()
            init_email_tables()
            init_tenant_tables()
            init_users_table()
            init_flywheel_tables()
            _db_init_attempted = True
        except Exception:
            logger.exception('Database table initialization failed')
            _db_init_attempted = True
            _db_ready = False


def set_db_ready(ready: bool) -> None:
    """Set the database ready state (for testing)."""
    global _db_ready
    _db_ready = ready


def set_db_init_attempted(attempted: bool) -> None:
    """Set the database init attempted state (for testing)."""
    global _db_init_attempted
    _db_init_attempted = attempted


def get_db_init_lock() -> threading.Lock:
    """Get the database init lock (for testing)."""
    return _db_init_lock


def claim_security_alert_email() -> dict[str, object] | None:
    """Atomically claim the next pending platform security-alert email.

    This persistence concern belongs with the database adapter rather than an
    HTTP entry point. ``FOR UPDATE SKIP LOCKED`` allows multiple workers to
    dispatch safely without delivering the same alert twice.
    """
    try:
        with psycopg.connect(db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH candidate AS (
                        SELECT id FROM security_alert_emails
                        WHERE tenant_id = %s AND status IN ('queued', 'retry')
                          AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                        ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1
                    )
                    UPDATE security_alert_emails AS queued
                    SET status = 'sending', locked_at = NOW(),
                        attempts = queued.attempts + 1, updated_at = NOW()
                    FROM candidate
                    WHERE queued.id = candidate.id
                    RETURNING queued.id, queued.tenant_id, queued.provider,
                        queued.to_email, queued.from_email, queued.subject,
                        queued.body, queued.status, queued.attempts,
                        queued.next_attempt_at, queued.delivery_detail,
                        queued.created_at, queued.updated_at
                    """,
                    ('platform-security',),
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:
            return None
        next_attempt = row[9]
        return {
            'id': int(row[0]), 'tenant_id': str(row[1] or ''),
            'provider': str(row[2] or ''), 'to': str(row[3] or ''),
            'from': str(row[4] or ''), 'subject': str(row[5] or ''),
            'body': str(row[6] or ''), 'status': str(row[7] or ''),
            'attempts': int(row[8] or 0),
            'next_attempt_at': int(next_attempt.timestamp()) if isinstance(next_attempt, datetime) else 0,
            'delivery_detail': str(row[10] or ''),
            'created_at': row[11].isoformat() if isinstance(row[11], datetime) else '',
            'updated_at': row[12].isoformat() if isinstance(row[12], datetime) else '',
            '__queue_source': 'db',
        }
    except Exception:
        logger.exception('Could not claim security alert email')
        return None
