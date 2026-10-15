"""add durable content approval tables with tenant RLS

Revision ID: 3b5d7f9a1c24
Revises: 2a8f4c1d9e70
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3b5d7f9a1c24"
down_revision: str | None = "2a8f4c1d9e70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
_TABLES = ("content_approval_configs", "content_approval_requests", "content_approval_comments")


def _tenant_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "content_approval_configs",
        sa.Column("levels", _JSON, nullable=False),
        sa.Column("require_all_levels", sa.Boolean(), nullable=False),
        sa.Column("expiry_hours", sa.Integer(), nullable=False),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant_profiles.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_approval_configs_tenant_id", "content_approval_configs", ["tenant_id"])
    op.create_index("uq_content_approval_configs_tenant", "content_approval_configs", ["tenant_id"], unique=True)

    op.create_table(
        "content_approval_requests",
        sa.Column("scheduled_post_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("content_preview", sa.Text(), nullable=False),
        sa.Column("campaign_tag", sa.String(length=80), nullable=True),
        sa.Column("requested_by", sa.String(length=120), nullable=False),
        sa.Column("requested_by_subject", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approval_levels", _JSON, nullable=False),
        sa.Column("approvals_received", _JSON, nullable=False),
        sa.Column("require_all_levels", sa.Boolean(), nullable=False),
        sa.Column("due_at", sa.String(length=40), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("rejected_by", sa.String(length=80), nullable=True),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant_profiles.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_approval_requests_tenant_id", "content_approval_requests", ["tenant_id"])
    op.create_index(
        "ix_content_approval_requests_tenant_status", "content_approval_requests", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_content_approval_requests_tenant_post", "content_approval_requests", ["tenant_id", "scheduled_post_id"]
    )
    # At most one open request per post, enforced by the database rather than a
    # check-then-insert race in application code.
    op.create_index(
        "uq_content_approval_requests_pending_post",
        "content_approval_requests",
        ["tenant_id", "scheduled_post_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "content_approval_comments",
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_role", sa.String(length=80), nullable=False),
        sa.Column("reviewer_subject", sa.String(length=255), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant_profiles.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["content_approval_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_approval_comments_tenant_id", "content_approval_comments", ["tenant_id"])
    op.create_index(
        "ix_content_approval_comments_tenant_request", "content_approval_comments", ["tenant_id", "request_id"]
    )

    for table in _TABLES:
        op.execute(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY nuxtron_rls_{table} ON public.{table}
            FOR ALL
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::text)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::text);
        """)


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS nuxtron_rls_{table} ON public.{table}")
    op.drop_index("ix_content_approval_comments_tenant_request", table_name="content_approval_comments")
    op.drop_index("ix_content_approval_comments_tenant_id", table_name="content_approval_comments")
    op.drop_table("content_approval_comments")
    op.drop_index("uq_content_approval_requests_pending_post", table_name="content_approval_requests")
    op.drop_index("ix_content_approval_requests_tenant_post", table_name="content_approval_requests")
    op.drop_index("ix_content_approval_requests_tenant_status", table_name="content_approval_requests")
    op.drop_index("ix_content_approval_requests_tenant_id", table_name="content_approval_requests")
    op.drop_table("content_approval_requests")
    op.drop_index("uq_content_approval_configs_tenant", table_name="content_approval_configs")
    op.drop_index("ix_content_approval_configs_tenant_id", table_name="content_approval_configs")
    op.drop_table("content_approval_configs")
