"""Associate meeting consent records with their meeting.

Revision ID: 1c7b9e4a2d60
Revises: 8b41d69ce205
"""

from alembic import op
import sqlalchemy as sa

revision = "1c7b9e4a2d60"
down_revision = "8b41d69ce205"
branch_labels = None
depends_on = None


def _consent_table(*, include_meeting: bool) -> sa.Table:
    """Describe the pre-migration table for SQLite batch and offline migrations."""
    metadata = sa.MetaData()
    columns = [
        sa.Column("participant_email", sa.String(255), nullable=False),
        sa.Column("recording_consent", sa.Boolean(), nullable=False),
        sa.Column("transcript_consent", sa.Boolean(), nullable=False),
        sa.Column("ai_processing_consent", sa.Boolean(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
    ]
    if include_meeting:
        columns.append(sa.Column("meeting_id", sa.Integer(), nullable=True))
    columns.extend(
        [
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        ]
    )
    table = sa.Table(
        "meeting_consent_logs",
        metadata,
        *columns,
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant_profiles.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    sa.Index("ix_meeting_consent_logs_tenant_id", table.c.tenant_id)
    if include_meeting:
        table.append_constraint(
            sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], name="fk_meeting_consent_logs_meeting_id", ondelete="CASCADE")
        )
        sa.Index(
            "ix_meeting_consent_logs_tenant_meeting",
            table.c.tenant_id,
            table.c.meeting_id,
            table.c.participant_email,
        )
    return table


def upgrade() -> None:
    """Add a nullable meeting association while preserving existing audit history."""
    with op.batch_alter_table(
        "meeting_consent_logs", copy_from=_consent_table(include_meeting=False)
    ) as batch_op:
        batch_op.add_column(sa.Column("meeting_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_meeting_consent_logs_meeting_id",
            "meetings",
            ["meeting_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_meeting_consent_logs_tenant_meeting",
            ["tenant_id", "meeting_id", "participant_email"],
            unique=False,
        )


def downgrade() -> None:
    """Remove only the new association; preserve existing consent records."""
    with op.batch_alter_table(
        "meeting_consent_logs", copy_from=_consent_table(include_meeting=True)
    ) as batch_op:
        batch_op.drop_index("ix_meeting_consent_logs_tenant_meeting")
        batch_op.drop_constraint("fk_meeting_consent_logs_meeting_id", type_="foreignkey")
        batch_op.drop_column("meeting_id")
