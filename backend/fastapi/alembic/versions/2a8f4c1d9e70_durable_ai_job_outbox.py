"""add durable AI job outbox and tenant RLS

Revision ID: 2a8f4c1d9e70
Revises: 1c7b9e4a2d60
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2a8f4c1d9e70"
down_revision: str | None = "1c7b9e4a2d60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_outbox",
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("task_name", sa.String(length=180), nullable=False),
        sa.Column("queue", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant_profiles.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_outbox_tenant_id", "job_outbox", ["tenant_id"], unique=False)
    op.create_index("ix_job_outbox_tenant_status_available", "job_outbox", ["tenant_id", "status", "available_at"], unique=False)
    op.create_index("ix_job_outbox_tenant_job", "job_outbox", ["tenant_id", "job_id"], unique=False)
    op.create_index("uq_job_outbox_tenant_job", "job_outbox", ["tenant_id", "job_id"], unique=True)

    op.execute("""
        ALTER TABLE public.job_executions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.job_executions FORCE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS nuxtron_rls_job_executions ON public.job_executions;
        CREATE POLICY nuxtron_rls_job_executions ON public.job_executions
        FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::text)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::text);

        ALTER TABLE public.job_outbox ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.job_outbox FORCE ROW LEVEL SECURITY;
        CREATE POLICY nuxtron_rls_job_outbox ON public.job_outbox
        FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::text)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::text);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS nuxtron_rls_job_outbox ON public.job_outbox")
    op.execute("DROP POLICY IF EXISTS nuxtron_rls_job_executions ON public.job_executions")
    op.execute("ALTER TABLE public.job_outbox NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.job_executions NO FORCE ROW LEVEL SECURITY")
    op.drop_index("uq_job_outbox_tenant_job", table_name="job_outbox")
    op.drop_index("ix_job_outbox_tenant_job", table_name="job_outbox")
    op.drop_index("ix_job_outbox_tenant_status_available", table_name="job_outbox")
    op.drop_index("ix_job_outbox_tenant_id", table_name="job_outbox")
    op.drop_table("job_outbox")
