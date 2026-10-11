"""add durable security audit events

Revision ID: 7e2f4c9a1b66
Revises: 6c3e8f1a2b77
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7e2f4c9a1b66"
down_revision: str | None = "6c3e8f1a2b77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("principal_id", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("auth_mode", sa.String(length=40), nullable=False),
        sa.Column("method", sa.String(length=12), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("ip_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant_profiles.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_audit_events_tenant_created", "security_audit_events", ["tenant_id", "created_at"])
    op.create_index("ix_security_audit_events_request_id", "security_audit_events", ["request_id"])
    op.execute("ALTER TABLE public.security_audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.security_audit_events FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY nuxtron_rls_security_audit_events
        ON public.security_audit_events
        FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), ''))
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), ''))
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS nuxtron_rls_security_audit_events ON public.security_audit_events")
    op.execute("ALTER TABLE public.security_audit_events NO FORCE ROW LEVEL SECURITY")
    op.drop_index("ix_security_audit_events_request_id", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_tenant_created", table_name="security_audit_events")
    op.drop_table("security_audit_events")
