"""
SQLAlchemy ORM models for Nuxtron platform.

Defines all persistent entities: Contacts, Deals, Workflows, Invoices, etc.
Models use JSONB for flexibility while maintaining schema structure.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

# Keep both import paths bound to the same module object to prevent duplicate
# declarative registrations across mixed test import styles.
sys.modules.setdefault('app.models', sys.modules[__name__])
sys.modules.setdefault('backend.fastapi.app.models', sys.modules[__name__])

JsonObject = dict[str, Any]
JsonField = JSON().with_variant(JSONB, 'postgresql')


class Tenant(Base):
    """Canonical tenant registry — maps to the pre-existing ``tenant_profiles``
    table that ``routers/tenants.py`` has managed via raw SQL since before any
    ORM model existed for it (there was previously no tracked schema/migration
    for this table at all; it was created out-of-band). This model exists so
    every other tenant-scoped table can carry a real foreign key to it instead
    of an unconstrained string, without introducing a second, competing
    "tenant" table.

    Column shape mirrors exactly what ``routers/tenants.py``'s raw
    INSERT/SELECT statements already read and write — this is a formalization
    of the existing table, not a new design.

    Rows are auto-provisioned just-in-time by the ``before_flush`` session
    event in ``database.py`` the first time a tenant_id is written via any
    ORM session, so the FK below never blocks normal usage — no tenant needs
    to call ``POST /tenants`` before using any other tenant-scoped feature.
    """

    __tablename__ = 'tenant_profiles'

    tenant_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name_cipher: Mapped[str | None] = mapped_column(Text, default=None)
    display_name_preview: Mapped[str] = mapped_column(String(64), default='')
    plan: Mapped[str] = mapped_column(String(40), default='starter')
    status: Mapped[str] = mapped_column(String(40), default='active')
    settings_json: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class BaseTenantModel(Base):
    """Base class for all tenant-scoped models."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(255), ForeignKey('tenant_profiles.tenant_id', ondelete='CASCADE'), nullable=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class Contact(BaseTenantModel):
    """CRM Contact model."""

    __tablename__ = 'contacts'
    __table_args__ = (Index('ix_contacts_tenant_email', 'tenant_id', 'email'),)

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), default='')
    company: Mapped[str] = mapped_column(String(180), default='')
    phone: Mapped[str] = mapped_column(String(40), default='')
    lifecycle_stage: Mapped[str] = mapped_column(String(40), default='lead')
    score: Mapped[int] = mapped_column(default=0)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class Deal(BaseTenantModel):
    """CRM Deal/Pipeline model."""

    __tablename__ = 'deals'
    __table_args__ = (Index('ix_deals_tenant_stage', 'tenant_id', 'stage'),)

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    value: Mapped[float] = mapped_column(default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default='USD')
    stage: Mapped[str] = mapped_column(String(60), default='prospect')
    contact_id: Mapped[int | None] = mapped_column(default=None)
    company_id: Mapped[int | None] = mapped_column(default=None)
    close_date: Mapped[str | None] = mapped_column(String(30), default=None)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class Company(BaseTenantModel):
    """CRM Company model."""

    __tablename__ = 'companies'

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    domain: Mapped[str] = mapped_column(String(180), default='')
    industry: Mapped[str] = mapped_column(String(80), default='')
    employee_count: Mapped[int] = mapped_column(default=0)
    annual_revenue: Mapped[float] = mapped_column(default=0.0)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class Activity(BaseTenantModel):
    """CRM Activity (note, call, email, meeting) model."""

    __tablename__ = 'activities'
    __table_args__ = (Index('ix_activities_tenant_type', 'tenant_id', 'type'),)

    type: Mapped[str] = mapped_column(String(40), default='note')  # note, call, email, meeting
    contact_id: Mapped[int] = mapped_column(nullable=False, index=True)
    deal_id: Mapped[int | None] = mapped_column(default=None)
    description: Mapped[str] = mapped_column(Text, default='')
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class Task(BaseTenantModel):
    """CRM Task/Action Item model."""

    __tablename__ = 'tasks'
    __table_args__ = (Index('ix_tasks_tenant_status', 'tenant_id', 'status'),)

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default='open')  # open, completed, cancelled
    priority: Mapped[str] = mapped_column(String(20), default='medium')  # low, medium, high
    assigned_to: Mapped[str] = mapped_column(String(255), default='')
    due_date: Mapped[str | None] = mapped_column(String(30), default=None)
    related_contact_id: Mapped[int | None] = mapped_column(default=None)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class Lead(BaseTenantModel):
    """CRM Lead / Sales Opportunity model."""

    __tablename__ = 'leads'
    __table_args__ = (Index('ix_leads_tenant_status', 'tenant_id', 'status'),)

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    contact_id: Mapped[int | None] = mapped_column(default=None)
    company_id: Mapped[int | None] = mapped_column(default=None)
    source: Mapped[str] = mapped_column(String(60), default='api')
    estimated_value: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[str] = mapped_column(String(40), default='new')
    score: Mapped[int] = mapped_column(default=0)
    assigned_to: Mapped[str] = mapped_column(String(120), default='')
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)  # stores notes, converted_deal_id, etc.


class Ticket(BaseTenantModel):
    """CRM Support Ticket model."""

    __tablename__ = 'tickets'
    __table_args__ = (Index('ix_tickets_tenant_status', 'tenant_id', 'status'),)

    ticket_number: Mapped[str] = mapped_column(String(60), nullable=False)
    subject: Mapped[str] = mapped_column(String(320), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    contact_id: Mapped[int | None] = mapped_column(default=None)
    priority: Mapped[str] = mapped_column(String(20), default='medium')
    channel: Mapped[str] = mapped_column(String(40), default='email')
    status: Mapped[str] = mapped_column(String(40), default='open')
    assigned_to: Mapped[str | None] = mapped_column(String(255), default=None)
    escalated: Mapped[bool] = mapped_column(default=False)
    resolution: Mapped[str | None] = mapped_column(Text, default=None)
    tags: Mapped[list[str]] = mapped_column(JsonField, default=list)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)  # stores SLA deadlines


class WorkflowRule(BaseTenantModel):
    """Workflow automation rule model."""

    __tablename__ = 'workflow_rules'
    __table_args__ = (Index('ix_workflow_rules_tenant_enabled', 'tenant_id', 'enabled'),)

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    trigger: Mapped[str] = mapped_column(String(100), nullable=False)  # contact_created, deal_updated, etc.
    conditions: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    actions: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class ScheduledPost(BaseTenantModel):
    """Social media scheduled post model."""

    __tablename__ = 'scheduled_posts'
    __table_args__ = (Index('ix_scheduled_posts_tenant_platform', 'tenant_id', 'platform'),)

    platform: Mapped[str] = mapped_column(String(40), nullable=False)  # twitter, linkedin, tiktok, etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    status: Mapped[str] = mapped_column(String(40), default='pending')  # pending, published, failed
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class InboxMessage(BaseTenantModel):
    """Smart inbox social message model."""

    __tablename__ = 'inbox_messages'
    __table_args__ = (Index('ix_inbox_messages_tenant_status', 'tenant_id', 'status'),)

    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    platform_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default='unread')  # unread, read, replied, internal_note
    assigned_to: Mapped[str | None] = mapped_column(String(255), default=None)
    tags: Mapped[list[str]] = mapped_column(JsonField, default=list)
    thread: Mapped[list[JsonObject]] = mapped_column(JsonField, default=list)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class Invoice(BaseTenantModel):
    """CRM Invoice model."""

    __tablename__ = 'invoices'

    invoice_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    contact_id: Mapped[int | None] = mapped_column(default=None)
    amount: Mapped[float] = mapped_column(default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default='USD')
    status: Mapped[str] = mapped_column(String(40), default='draft')  # draft, sent, viewed, paid
    due_date: Mapped[str | None] = mapped_column(String(30), default=None)
    items: Mapped[list[JsonObject]] = mapped_column(JsonField, default=list)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class AuditLog(BaseTenantModel):
    """Audit trail for compliance and tracking."""

    __tablename__ = 'audit_logs'
    __table_args__ = (Index('ix_audit_logs_tenant_action', 'tenant_id', 'action'),)

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(default=None)
    user_id: Mapped[str] = mapped_column(String(255), default='')
    changes: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class WorkforceSchedule(BaseTenantModel):
    """Persistent schedule for 24/7 autonomous workforce execution."""

    __tablename__ = 'workforce_schedules'
    __table_args__ = (
        Index('ix_workforce_schedules_tenant_next_execution', 'tenant_id', 'next_execution_at'),
        Index('ix_workforce_schedules_tenant_enabled', 'tenant_id', 'enabled'),
    )

    mission_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Unique mission identifier
    mission_name: Mapped[str] = mapped_column(String(180), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)  # social_media, seo, ads, etc.
    status: Mapped[str] = mapped_column(String(40), default='pending')  # pending, running, completed, failed, paused
    enabled: Mapped[bool] = mapped_column(default=True)
    
    # Schedule config
    schedule_type: Mapped[str] = mapped_column(String(40), default='recurring')  # once, recurring, daily, weekly
    schedule_config: Mapped[JsonObject] = mapped_column(JsonField, default=dict)  # cron, interval, etc.
    
    # Mission definition
    mission_config: Mapped[JsonObject] = mapped_column(JsonField, default=dict)  # mission parameters, tools, goals
    
    # Execution tracking
    next_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_execution_result: Mapped[str | None] = mapped_column(String(40), default=None)  # success, failed, error
    
    # Result tracking
    execution_count: Mapped[int] = mapped_column(default=0)
    failure_count: Mapped[int] = mapped_column(default=0)
    last_error_message: Mapped[str | None] = mapped_column(Text, default=None)
    
    # Approval workflow
    approval_required: Mapped[bool] = mapped_column(default=True)
    pending_approval_count: Mapped[int] = mapped_column(default=0)
    
    # Extended data
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class MissionJob(BaseTenantModel):
    """Individual autonomous workforce mission job."""

    __tablename__ = 'mission_jobs'
    __table_args__ = (
        Index('ix_mission_jobs_tenant_schedule_id', 'tenant_id', 'schedule_id'),
        Index('ix_mission_jobs_tenant_status', 'tenant_id', 'status'),
    )

    schedule_id: Mapped[int | None] = mapped_column(default=None)  # Reference to WorkforceSchedule
    mission_id: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default='pending')  # pending, running, completed, failed, rejected
    
    # Job definition
    mission_config: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    tools_to_use: Mapped[list[str]] = mapped_column(JsonField, default=list)
    
    # Execution details
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    duration_seconds: Mapped[float | None] = mapped_column(default=None)
    
    # Results
    result: Mapped[JsonObject] = mapped_column(JsonField, default=dict)  # Generated content, metrics, etc.
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    
    # Approval workflow
    approval_required: Mapped[bool] = mapped_column(default=True)
    approval_status: Mapped[str] = mapped_column(String(40), default='pending_review')  # pending_review, approved, rejected
    approved_by: Mapped[str | None] = mapped_column(String(255), default=None)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    approval_notes: Mapped[str | None] = mapped_column(Text, default=None)
    
    # Extended data
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class WorkflowExecution(BaseTenantModel):
    """Workflow rule execution history and results."""

    __tablename__ = 'workflow_executions'
    __table_args__ = (
        Index('ix_workflow_executions_tenant_workflow_id', 'tenant_id', 'workflow_id'),
        Index('ix_workflow_executions_tenant_status', 'tenant_id', 'status'),
    )

    workflow_id: Mapped[int | None] = mapped_column(default=None)  # Reference to WorkflowRule
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_entity_id: Mapped[int | None] = mapped_column(default=None)
    
    status: Mapped[str] = mapped_column(String(40), default='running')  # running, completed, failed, paused
    
    # Execution details
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    
    # Steps executed
    steps_executed: Mapped[list[JsonObject]] = mapped_column(JsonField, default=list)  # Track each step result
    current_step_id: Mapped[str | None] = mapped_column(String(50), default=None)
    
    # Results and errors
    result: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    
    # Extended data
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class JobExecution(BaseTenantModel):
    """Celery/Background job execution tracking for observability."""

    __tablename__ = 'job_executions'
    __table_args__ = (
        Index('ix_job_executions_tenant_status', 'tenant_id', 'status'),
        Index('ix_job_executions_job_id', 'job_id'),
    )

    job_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Celery task ID or similar
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)  # mission_execution, workflow_step, etc.
    status: Mapped[str] = mapped_column(String(40), default='queued')  # queued, running, completed, failed, retry
    
    # Job parameters
    job_params: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    
    # Execution details
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    duration_seconds: Mapped[float | None] = mapped_column(default=None)
    
    # Retry tracking
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    
    # Results
    result: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    error_traceback: Mapped[str | None] = mapped_column(Text, default=None)
    
    # Extended data
    data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


# Register all models with Base for create_all() to work
__all__ = [
    'Tenant',
    'BaseTenantModel',
    'Contact',
    'Deal',
    'Company',
    'Activity',
    'Task',
    'Lead',
    'Ticket',
    'WorkflowRule',
    'ScheduledPost',
    'InboxMessage',
    'Invoice',
    'AuditLog',
    'WorkforceSchedule',
    'MissionJob',
    'WorkflowExecution',
    'JobExecution',
]
