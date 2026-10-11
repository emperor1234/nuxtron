"""add external organization identity mapping

Revision ID: 4a1c7e9b2d10
Revises: 9d2f6f1a3b40
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4a1c7e9b2d10"
down_revision: str | None = "9d2f6f1a3b40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_identity_mappings",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("external_organization_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant_profiles.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_organization_id"),
        sa.UniqueConstraint("tenant_id"),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="ck_org_identity_status"),
    )
    op.create_index(
        "ix_org_identity_mappings_tenant_id",
        "organization_identity_mappings",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_org_identity_mappings_tenant_id", table_name="organization_identity_mappings")
    op.drop_table("organization_identity_mappings")
