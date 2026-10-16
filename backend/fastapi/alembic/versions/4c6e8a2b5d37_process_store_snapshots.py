"""add the table that keeps process-local store snapshots across restarts

Revision ID: 4c6e8a2b5d37
Revises: 3b5d7f9a1c24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4c6e8a2b5d37"
down_revision: str | None = "3b5d7f9a1c24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "process_store_snapshots"


def upgrade() -> None:
    # The application also creates this table on first start when it has the
    # privilege; the migration keeps locked-down production roles working.
    if TABLE in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        TABLE,
        sa.Column("store_name", sa.String(length=160), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("store_name"),
    )


def downgrade() -> None:
    op.drop_table(TABLE)
