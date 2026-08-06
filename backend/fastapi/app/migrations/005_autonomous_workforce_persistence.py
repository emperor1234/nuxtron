"""Add persistent storage for autonomous workforce, missions, and workflows.

Revision ID: 005_autonomous_workforce_persistence
Revises: 004_previous_migration
Create Date: 2026-05-19 15:00:00.000000
"""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[import-not-found]

# revision identifiers, used by Alembic.
revision = '005_autonomous_workforce_persistence'
down_revision = '004'  # Update this to match the latest migration
branch_labels = None
depends_on = None


def _jsonb(*args: Any, **kwargs: Any) -> Any:
    """Typed wrapper for SQLAlchemy JSONB used in migrations.

    SQLAlchemy dialect helpers are frequently untyped in migration contexts.
    This wrapper keeps migration runtime behavior unchanged while keeping
    strict mypy checks focused on application code.
    """
    return postgresql.JSONB(*args, **kwargs)  # type: ignore[no-untyped-call]


def upgrade() -> None:
    """Create tables for persistent autonomous execution."""
    
    # Create workforce_schedules table
    op.create_table(
        'workforce_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('mission_id', sa.String(255), nullable=False),
        sa.Column('mission_name', sa.String(180), nullable=False),
        sa.Column('role', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False, server_default='pending'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('schedule_type', sa.String(40), nullable=False, server_default='recurring'),
        sa.Column('schedule_config', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('mission_config', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('next_execution_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_execution_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_execution_result', sa.String(40), nullable=True),
        sa.Column('execution_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('approval_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('pending_approval_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('data', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_workforce_schedules_tenant_next_execution', 'tenant_id', 'next_execution_at'),
        sa.Index('ix_workforce_schedules_tenant_enabled', 'tenant_id', 'enabled'),
    )
    
    # Create mission_jobs table
    op.create_table(
        'mission_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=True),
        sa.Column('mission_id', sa.String(255), nullable=False),
        sa.Column('role', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False, server_default='pending'),
        sa.Column('mission_config', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tools_to_use', _jsonb(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('result', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('approval_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('approval_status', sa.String(40), nullable=False, server_default='pending_review'),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('data', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_mission_jobs_tenant_schedule_id', 'tenant_id', 'schedule_id'),
        sa.Index('ix_mission_jobs_tenant_status', 'tenant_id', 'status'),
    )
    
    # Create workflow_executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=True),
        sa.Column('trigger_type', sa.String(100), nullable=False),
        sa.Column('trigger_entity_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(40), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('steps_executed', _jsonb(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('current_step_id', sa.String(50), nullable=True),
        sa.Column('result', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('data', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_workflow_executions_tenant_workflow_id', 'tenant_id', 'workflow_id'),
        sa.Index('ix_workflow_executions_tenant_status', 'tenant_id', 'status'),
    )
    
    # Create job_executions table
    op.create_table(
        'job_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('job_id', sa.String(255), nullable=False),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(40), nullable=False, server_default='queued'),
        sa.Column('job_params', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('data', _jsonb(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_job_executions_tenant_status', 'tenant_id', 'status'),
        sa.Index('ix_job_executions_job_id', 'job_id'),
    )


def downgrade() -> None:
    """Remove autonomous workforce persistence tables."""
    op.drop_table('job_executions')
    op.drop_table('workflow_executions')
    op.drop_table('mission_jobs')
    op.drop_table('workforce_schedules')
