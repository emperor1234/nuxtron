"""
Autonomous Workforce Persistence Layer

Handles Postgres-backed storage for missions, schedules, integrations,
retry queues, and audit logs. Provides async context managers for
transaction safety and atomic operations.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

MissionStatus = str
ProviderStatus = str


async def init_workforce_db(dsn: str) -> None:
    """Initialize workforce database tables."""
    async with await psycopg.AsyncConnection.connect(dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS workforce_profiles (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL UNIQUE,
                    company_name TEXT NOT NULL,
                    website TEXT NOT NULL,
                    target_markets TEXT[] DEFAULT '{}',
                    preferred_channels TEXT[] DEFAULT '{}',
                    brand_tone TEXT,
                    goals TEXT[] DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS workforce_profiles_tenant_idx
                    ON workforce_profiles (tenant_id);

                CREATE TABLE IF NOT EXISTS workforce_integrations (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'connected',
                    token_hash TEXT,
                    token_preview TEXT,
                    secret_ref TEXT,
                    account_id TEXT,
                    metadata JSONB DEFAULT '{}',
                    last_verified_at TIMESTAMPTZ,
                    last_verified_status INTEGER,
                    last_verified_response JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (tenant_id, provider)
                );

                CREATE INDEX IF NOT EXISTS workforce_integrations_tenant_idx
                    ON workforce_integrations (tenant_id);
                CREATE INDEX IF NOT EXISTS workforce_integrations_provider_status_idx
                    ON workforce_integrations (provider, status);

                CREATE TABLE IF NOT EXISTS workforce_missions (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    role TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    requires_approval BOOLEAN NOT NULL DEFAULT TRUE,
                    providers TEXT[] DEFAULT '{}',
                    input_context JSONB DEFAULT '{}',
                    approver_id TEXT,
                    approval_note TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    approved_at TIMESTAMPTZ,
                    executed_at TIMESTAMPTZ
                );

                CREATE INDEX IF NOT EXISTS workforce_missions_tenant_idx
                    ON workforce_missions (tenant_id);
                CREATE INDEX IF NOT EXISTS workforce_missions_status_idx
                    ON workforce_missions (status);
                CREATE INDEX IF NOT EXISTS workforce_missions_created_desc_idx
                    ON workforce_missions (created_at DESC);

                CREATE TABLE IF NOT EXISTS workforce_schedules (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    mission_template_id UUID,
                    title TEXT NOT NULL,
                    role TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    frequency_minutes INTEGER NOT NULL DEFAULT 60,
                    providers TEXT[] DEFAULT '{}',
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    last_run_at TIMESTAMPTZ,
                    next_run_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS workforce_schedules_tenant_idx
                    ON workforce_schedules (tenant_id);
                CREATE INDEX IF NOT EXISTS workforce_schedules_next_run_idx
                    ON workforce_schedules (next_run_at);
                CREATE INDEX IF NOT EXISTS workforce_schedules_enabled_idx
                    ON workforce_schedules (enabled);

                CREATE TABLE IF NOT EXISTS workforce_outcomes (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    mission_id UUID NOT NULL REFERENCES workforce_missions(id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    provider_results JSONB DEFAULT '{}',
                    artifact JSONB DEFAULT '{}',
                    execution_time_seconds DOUBLE PRECISION,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    source TEXT DEFAULT 'manual'
                );

                CREATE INDEX IF NOT EXISTS workforce_outcomes_tenant_idx
                    ON workforce_outcomes (tenant_id);
                CREATE INDEX IF NOT EXISTS workforce_outcomes_mission_idx
                    ON workforce_outcomes (mission_id);
                CREATE INDEX IF NOT EXISTS workforce_outcomes_created_desc_idx
                    ON workforce_outcomes (created_at DESC);

                CREATE TABLE IF NOT EXISTS workforce_action_execution (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    mission_id UUID NOT NULL REFERENCES workforce_missions(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    request_payload JSONB DEFAULT '{}',
                    response_payload JSONB DEFAULT '{}',
                    error_message TEXT,
                    execution_time_seconds DOUBLE PRECISION,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    executed_at TIMESTAMPTZ
                );

                CREATE INDEX IF NOT EXISTS workforce_action_execution_tenant_idx
                    ON workforce_action_execution (tenant_id);
                CREATE INDEX IF NOT EXISTS workforce_action_execution_mission_idx
                    ON workforce_action_execution (mission_id);
                CREATE INDEX IF NOT EXISTS workforce_action_execution_status_idx
                    ON workforce_action_execution (status);

                CREATE TABLE IF NOT EXISTS workforce_retry_queue (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    mission_id UUID NOT NULL REFERENCES workforce_missions(id) ON DELETE CASCADE,
                    action_execution_id UUID REFERENCES workforce_action_execution(id) ON DELETE SET NULL,
                    provider TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 5,
                    status TEXT NOT NULL DEFAULT 'pending',
                    next_retry_at TIMESTAMPTZ NOT NULL,
                    last_error TEXT,
                    backoff_seconds INTEGER NOT NULL DEFAULT 60,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS workforce_retry_queue_tenant_idx
                    ON workforce_retry_queue (tenant_id);
                CREATE INDEX IF NOT EXISTS workforce_retry_queue_next_retry_idx
                    ON workforce_retry_queue (next_retry_at);
                CREATE INDEX IF NOT EXISTS workforce_retry_queue_status_idx
                    ON workforce_retry_queue (status);

                CREATE TABLE IF NOT EXISTS workforce_audit_log (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT,
                    mission_id UUID REFERENCES workforce_missions(id) ON DELETE SET NULL,
                    source TEXT DEFAULT 'workforce',
                    actor_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS workforce_audit_log_tenant_idx
                    ON workforce_audit_log (tenant_id);
                CREATE INDEX IF NOT EXISTS workforce_audit_log_created_desc_idx
                    ON workforce_audit_log (created_at DESC);

                CREATE TABLE IF NOT EXISTS workforce_knowledge (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    source TEXT DEFAULT 'manual',
                    tags TEXT[] DEFAULT '{}',
                    embedding VECTOR(1536),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS workforce_knowledge_tenant_idx
                    ON workforce_knowledge (tenant_id);
                """
            )
        await conn.commit()


class WorkforceDB:
    """Transaction-safe workforce database operations."""

    def __init__(self, dsn: str):
        self.dsn = dsn

    async def create_mission(
        self,
        tenant_id: str,
        title: str,
        description: str,
        role: str,
        objective: str,
        requires_approval: bool = True,
        providers: list[str] | None = None,
        input_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create and persist a mission."""
        mission_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO workforce_missions
                    (id, tenant_id, title, description, role, objective, requires_approval, providers, input_context, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        mission_id,
                        tenant_id,
                        title,
                        description,
                        role,
                        objective,
                        requires_approval,
                        providers or [],
                        json.dumps(input_context or {}),
                        now,
                        now,
                    ),
                )
                row = await cur.fetchone()
            await conn.commit()
        return dict(row) if row else {}

    async def get_mission(self, tenant_id: str, mission_id: str) -> dict[str, Any] | None:
        """Retrieve a mission by ID."""
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM workforce_missions WHERE id = %s AND tenant_id = %s",
                    (mission_id, tenant_id),
                )
                row = await cur.fetchone()
        return dict(row) if row else None

    async def list_missions(self, tenant_id: str, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """List missions for a tenant with optional status filter."""
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if status:
                    await cur.execute(
                        """
                        SELECT * FROM workforce_missions
                        WHERE tenant_id = %s AND status = %s
                        ORDER BY created_at ASC
                        LIMIT %s
                        """,
                        (tenant_id, status, limit),
                    )
                else:
                    await cur.execute(
                        """
                        SELECT * FROM workforce_missions
                        WHERE tenant_id = %s
                        ORDER BY created_at ASC
                        LIMIT %s
                        """,
                        (tenant_id, limit),
                    )
                rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def update_mission_status(self, tenant_id: str, mission_id: str, status: str) -> bool:
        """Update mission status."""
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE workforce_missions SET status = %s, updated_at = %s WHERE id = %s AND tenant_id = %s",
                    (status, now, mission_id, tenant_id),
                )
                updated = cur.rowcount > 0
            await conn.commit()
        return updated

    async def approve_mission(self, tenant_id: str, mission_id: str, approver_id: str, note: str = "") -> bool:
        """Approve and mark mission for execution."""
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE workforce_missions
                    SET status = %s, approver_id = %s, approval_note = %s, approved_at = %s, updated_at = %s
                    WHERE id = %s AND tenant_id = %s
                    """,
                    ("approved", approver_id, note, now, now, mission_id, tenant_id),
                )
                updated = cur.rowcount > 0
            await conn.commit()
        return updated

    async def create_outcome(
        self,
        tenant_id: str,
        mission_id: str,
        status: str,
        success_count: int,
        failed_count: int,
        provider_results: list[dict[str, Any]] | None = None,
        artifact: dict[str, Any] | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Create and persist an outcome record."""
        outcome_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO workforce_outcomes
                    (id, tenant_id, mission_id, status, success_count, failed_count, provider_results, artifact, source, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        outcome_id,
                        tenant_id,
                        mission_id,
                        status,
                        success_count,
                        failed_count,
                        json.dumps(provider_results or []),
                        json.dumps(artifact or {}),
                        source,
                        now,
                    ),
                )
                row = await cur.fetchone()
            await conn.commit()
        return dict(row) if row else {}

    async def list_outcomes(self, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """List outcomes for a tenant."""
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT * FROM workforce_outcomes
                    WHERE tenant_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (tenant_id, limit),
                )
                rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def create_schedule(
        self,
        tenant_id: str,
        role: str,
        title: str,
        objective: str,
        frequency_minutes: int,
        providers: list[str],
        enabled: bool,
        mission_template_id: str | None = None,
    ) -> dict[str, Any]:
        """Create and persist a recurring schedule."""
        schedule_id = str(uuid4())
        now = datetime.now(UTC)
        now_iso = now.isoformat()
        next_run_iso = (now + timedelta(minutes=max(5, int(frequency_minutes)))).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO workforce_schedules
                    (id, tenant_id, mission_template_id, title, role, objective, frequency_minutes, providers, enabled, next_run_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        schedule_id,
                        tenant_id,
                        mission_template_id,
                        title,
                        role,
                        objective,
                        frequency_minutes,
                        providers,
                        enabled,
                        next_run_iso,
                        now_iso,
                        now_iso,
                    ),
                )
                row = await cur.fetchone()
            await conn.commit()
        return dict(row) if row else {}

    async def list_schedules(self, tenant_id: str) -> list[dict[str, Any]]:
        """List schedules for a tenant."""
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT * FROM workforce_schedules
                    WHERE tenant_id = %s
                    ORDER BY created_at ASC
                    """,
                    (tenant_id,),
                )
                rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def upsert_profile(
        self,
        tenant_id: str,
        company_name: str,
        website: str,
        target_markets: list[str],
        preferred_channels: list[str],
        brand_tone: str,
        goals: list[str],
    ) -> dict[str, Any]:
        """Insert or update tenant workforce profile."""
        now = datetime.now(UTC).isoformat()
        profile_id = str(uuid4())
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO workforce_profiles
                    (id, tenant_id, company_name, website, target_markets, preferred_channels, brand_tone, goals, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id)
                    DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        website = EXCLUDED.website,
                        target_markets = EXCLUDED.target_markets,
                        preferred_channels = EXCLUDED.preferred_channels,
                        brand_tone = EXCLUDED.brand_tone,
                        goals = EXCLUDED.goals,
                        updated_at = EXCLUDED.updated_at
                    RETURNING *
                    """,
                    (
                        profile_id,
                        tenant_id,
                        company_name,
                        website,
                        target_markets,
                        preferred_channels,
                        brand_tone,
                        goals,
                        now,
                        now,
                    ),
                )
                row = await cur.fetchone()
            await conn.commit()
        return dict(row) if row else {}

    async def get_profile(self, tenant_id: str) -> dict[str, Any] | None:
        """Get tenant workforce profile."""
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM workforce_profiles WHERE tenant_id = %s",
                    (tenant_id,),
                )
                row = await cur.fetchone()
        return dict(row) if row else None

    async def upsert_integration(
        self,
        tenant_id: str,
        provider: str,
        status: str,
        token_hash: str,
        token_preview: str | None,
        secret_ref: str | None,
        account_id: str | None,
        metadata: dict[str, Any],
        last_verified_status: int,
        last_verified_response: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert or update provider integration record."""
        now = datetime.now(UTC).isoformat()
        integration_id = str(uuid4())
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO workforce_integrations
                    (id, tenant_id, provider, status, token_hash, token_preview, secret_ref, account_id, metadata, last_verified_at, last_verified_status, last_verified_response, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, provider)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        token_hash = EXCLUDED.token_hash,
                        token_preview = EXCLUDED.token_preview,
                        secret_ref = EXCLUDED.secret_ref,
                        account_id = EXCLUDED.account_id,
                        metadata = EXCLUDED.metadata,
                        last_verified_at = EXCLUDED.last_verified_at,
                        last_verified_status = EXCLUDED.last_verified_status,
                        last_verified_response = EXCLUDED.last_verified_response,
                        updated_at = EXCLUDED.updated_at
                    RETURNING *
                    """,
                    (
                        integration_id,
                        tenant_id,
                        provider,
                        status,
                        token_hash,
                        token_preview,
                        secret_ref,
                        account_id,
                        metadata,
                        now,
                        last_verified_status,
                        last_verified_response,
                        now,
                        now,
                    ),
                )
                row = await cur.fetchone()
            await conn.commit()
        return dict(row) if row else {}

    async def list_integrations(self, tenant_id: str) -> list[dict[str, Any]]:
        """List persisted integrations for a tenant."""
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT * FROM workforce_integrations
                    WHERE tenant_id = %s
                    ORDER BY created_at ASC
                    """,
                    (tenant_id,),
                )
                rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def add_knowledge(
        self,
        tenant_id: str,
        title: str,
        body: str,
        source: str,
        tags: list[str],
    ) -> dict[str, Any]:
        """Persist a knowledge document."""
        doc_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO workforce_knowledge
                    (id, tenant_id, title, body, source, tags, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (doc_id, tenant_id, title, body, source, tags, now, now),
                )
                row = await cur.fetchone()
            await conn.commit()
        return dict(row) if row else {}

    async def list_knowledge(self, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """List persisted knowledge documents for a tenant."""
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT * FROM workforce_knowledge
                    WHERE tenant_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (tenant_id, limit),
                )
                rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def enqueue_retry(
        self,
        tenant_id: str,
        mission_id: str,
        action_execution_id: str,
        provider: str,
        max_retries: int = 5,
        backoff_seconds: int = 60,
    ) -> dict[str, Any]:
        """Enqueue a failed action for retry."""
        retry_id = str(uuid4())
        next_retry = datetime.now(UTC).isoformat()
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO workforce_retry_queue
                    (id, tenant_id, mission_id, action_execution_id, provider, max_retries, backoff_seconds, next_retry_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (retry_id, tenant_id, mission_id, action_execution_id, provider, max_retries, backoff_seconds, next_retry, now),
                )
                row = await cur.fetchone()
            await conn.commit()
        return dict(row) if row else {}

    async def get_due_retries(self, tenant_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch retry queue items due for execution."""
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if tenant_id:
                    await cur.execute(
                        """
                        SELECT * FROM workforce_retry_queue
                        WHERE status = 'pending' AND next_retry_at <= %s AND tenant_id = %s
                        ORDER BY next_retry_at ASC
                        LIMIT %s
                        """,
                        (now, tenant_id, limit),
                    )
                else:
                    await cur.execute(
                        """
                        SELECT * FROM workforce_retry_queue
                        WHERE status = 'pending' AND next_retry_at <= %s
                        ORDER BY next_retry_at ASC
                        LIMIT %s
                        """,
                        (now, limit),
                    )
                rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def update_retry_status(self, retry_id: str, status: str, retry_count: int | None = None, error_msg: str = "") -> bool:
        """Update retry queue item status."""
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor() as cur:
                if retry_count is not None:
                    await cur.execute(
                        """
                        UPDATE workforce_retry_queue
                        SET status = %s, retry_count = %s, last_error = %s, updated_at = %s
                        WHERE id = %s
                        """,
                        (status, retry_count, error_msg, now, retry_id),
                    )
                else:
                    await cur.execute(
                        "UPDATE workforce_retry_queue SET status = %s, last_error = %s, updated_at = %s WHERE id = %s",
                        (status, error_msg, now, retry_id),
                    )
                updated = cur.rowcount > 0
            await conn.commit()
        return updated

    async def audit_log(
        self, tenant_id: str, action: str, detail: str = "", mission_id: str | None = None, actor_id: str | None = None
    ) -> None:
        """Write an audit log entry."""
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO workforce_audit_log (tenant_id, action, detail, mission_id, actor_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (tenant_id, action, detail, mission_id, actor_id),
                )
            await conn.commit()

    async def get_schedule_due(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch schedules due for execution."""
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT * FROM workforce_schedules
                    WHERE enabled = TRUE AND next_run_at <= %s
                    ORDER BY next_run_at ASC
                    LIMIT %s
                    """,
                    (now, limit),
                )
                rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def update_schedule_next_run(self, schedule_id: str, next_run_at: str) -> bool:
        """Update schedule next run time."""
        now = datetime.now(UTC).isoformat()
        async with await psycopg.AsyncConnection.connect(self.dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE workforce_schedules SET next_run_at = %s, last_run_at = %s, updated_at = %s WHERE id = %s",
                    (next_run_at, now, now, schedule_id),
                )
                updated = cur.rowcount > 0
            await conn.commit()
        return updated
