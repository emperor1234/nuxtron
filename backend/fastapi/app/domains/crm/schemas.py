"""Crm request contracts."""

from pydantic import BaseModel
from pydantic import Field
from typing import Any
from typing import TypedDict


class ContactCreateRequest(BaseModel):
    email: str = Field(default="", max_length=255)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(default="", max_length=120)
    company: str = Field(default="", max_length=180)
    phone: str = Field(default="", max_length=40)
    lifecycle_stage: str = Field(default="lead", max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=20)
    properties: dict[str, Any] = Field(default_factory=dict)


class ContactScoreRequest(BaseModel):
    score: int = Field(ge=0, le=100)
    reason: str = Field(default="", max_length=320)


class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    domain: str = Field(default="", max_length=180)
    industry: str = Field(default="", max_length=80)
    employee_count: int = Field(default=0, ge=0)
    annual_revenue: float = Field(default=0.0, ge=0.0)
    properties: dict[str, Any] = Field(default_factory=dict)


class DealCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    value: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default="USD", max_length=8)
    stage: str = Field(default="prospect", max_length=60)
    contact_id: int | None = None
    company_id: int | None = None
    close_date: str | None = Field(default=None, max_length=30)
    properties: dict[str, Any] = Field(default_factory=dict)


class DealUpdateRequest(BaseModel):
    stage: str | None = Field(default=None, max_length=60)
    value: float | None = Field(default=None, ge=0.0)
    close_date: str | None = Field(default=None, max_length=30)
    properties: dict[str, Any] = Field(default_factory=dict)


class ActivityCreateRequest(BaseModel):
    type: str = Field(default="note", max_length=40)
    subject: str = Field(min_length=1, max_length=240)
    body: str = Field(default="", max_length=4000)
    contact_id: int | None = None
    deal_id: int | None = None


class ContactDedupeRequest(BaseModel):
    dry_run: bool = Field(default=True)


class CRMWebhookCreateRequest(BaseModel):
    event: str = Field(
        pattern="^(contact\\.created|contact\\.updated|deal\\.created|deal\\.updated|activity\\.created|lead\\.created|ticket\\.created|ticket\\.updated|task\\.completed)$"
    )
    target_url: str = Field(min_length=8, max_length=600)
    secret: str = Field(default="", max_length=200)


class HubSpotConnectRequest(BaseModel):
    access_token: str | None = Field(default=None, max_length=4096)
    api_key: str | None = Field(default=None, max_length=4096)
    portal_id: str | None = Field(default=None, max_length=80)
    endpoint_url: str | None = Field(default=None, max_length=300)
    verify_live: bool = Field(default=True)


class HubSpotSyncContactsRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=200)
    lifecycle_stage: str = Field(default="lead", max_length=40)
    source: str = Field(default="hubspot", max_length=80)


class LeadCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    contact_id: int | None = None
    company_id: int | None = None
    source: str = Field(default="api", max_length=60)
    estimated_value: float = Field(default=0.0, ge=0.0)
    status: str = Field(default="new", max_length=40)
    score: int = Field(default=0, ge=0, le=100)
    assigned_to: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=2000)


class LeadUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    score: int | None = Field(default=None, ge=0, le=100)
    assigned_to: str | None = Field(default=None, max_length=120)
    estimated_value: float | None = Field(default=None, ge=0.0)
    notes: str | None = Field(default=None, max_length=2000)


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=4000)
    contact_id: int | None = None
    deal_id: int | None = None
    due_date: str | None = Field(default=None, max_length=30)
    priority: str = Field(default="medium", max_length=20)
    assigned_to: str = Field(default="", max_length=120)
    type: str = Field(default="task", max_length=40)


class TaskUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    priority: str | None = Field(default=None, max_length=20)
    due_date: str | None = Field(default=None, max_length=30)
    assigned_to: str | None = Field(default=None, max_length=120)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=2000)
    owner: str = Field(default="", max_length=120)
    status: str = Field(default="planning", max_length=40)
    due_date: str | None = Field(default=None, max_length=30)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=40)
    due_date: str | None = Field(default=None, max_length=30)


class TicketCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=320)
    description: str = Field(default="", max_length=8000)
    contact_id: int | None = None
    priority: str = Field(default="medium", max_length=20)
    channel: str = Field(default="email", max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=10)


class TicketUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    priority: str | None = Field(default=None, max_length=20)
    assigned_to: str | None = Field(default=None, max_length=120)
    resolution: str | None = Field(default=None, max_length=4000)


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    type: str = Field(default="email", max_length=40)
    subject: str = Field(default="", max_length=320)
    body: str = Field(default="", max_length=20000)
    segment_id: int | None = None
    scheduled_at: str | None = Field(default=None, max_length=30)
    ab_test: bool = Field(default=False)
    variant_b_subject: str = Field(default="", max_length=320)


class SegmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=1000)
    filters: dict[str, Any] = Field(default_factory=dict)


class NoteCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    contact_id: int | None = None
    deal_id: int | None = None
    company_id: int | None = None
    pinned: bool = Field(default=False)


class QuoteLineItem(BaseModel):
    description: str = Field(min_length=1, max_length=240)
    quantity: float = Field(default=1.0, ge=0.0)
    unit_price: float = Field(default=0.0, ge=0.0)
    discount_pct: float = Field(default=0.0, ge=0.0, le=100.0)


class QuoteCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    contact_id: int | None = None
    deal_id: int | None = None
    line_items: list[QuoteLineItem] = Field(default_factory=list)
    currency: str = Field(default="USD", max_length=8)
    valid_until: str | None = Field(default=None, max_length=30)
    notes: str = Field(default="", max_length=4000)


class CRMInvoiceCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    contact_id: int | None = None
    deal_id: int | None = None
    quote_id: int | None = None
    amount: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default="USD", max_length=8)
    due_date: str | None = Field(default=None, max_length=30)
    notes: str = Field(default="", max_length=4000)


class CRMInvoiceUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    paid_at: str | None = Field(default=None, max_length=30)


class SequenceStep(BaseModel):
    day_offset: int = Field(default=0, ge=0)
    subject: str = Field(min_length=1, max_length=320)
    body: str = Field(min_length=1, max_length=20000)
    type: str = Field(default="email", max_length=20)


class EmailSequenceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=1000)
    steps: list[SequenceStep] = Field(default_factory=list)


class WorkflowRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    trigger: str = Field(min_length=1, max_length=60)
    conditions: dict[str, Any] = Field(default_factory=dict)
    action: str = Field(min_length=1, max_length=60)
    action_params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)


class CustomEntityTypeCreateRequest(BaseModel):
    key: str = Field(pattern="^[a-z][a-z0-9_]{1,60}$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=800)
    fields: list[dict[str, Any]] = Field(default_factory=list)


class CustomEntityRecordUpsertRequest(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class AutomationRecipeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    trigger: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=1, max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)


class APITokenCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=list, max_length=20)


class CRMBackupConfigRequest(BaseModel):
    incremental_minutes: int = Field(default=5, ge=5, le=1440)
    full_backup_weekday: str = Field(
        default="sunday", pattern="^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$"
    )
    full_backup_hour_utc: int = Field(default=3, ge=0, le=23)
    retention_days: int = Field(default=30, ge=7, le=365)
    enabled: bool = Field(default=True)


class CRMLiveSyncToggleRequest(BaseModel):
    enabled: bool = Field(default=True)
    interval_seconds: int = Field(default=30, ge=5, le=3600)


class SLARuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    applies_to: str = Field(default="ticket", max_length=40)
    priority: str = Field(default="medium", max_length=20)
    first_response_hours: int = Field(default=4, ge=0)
    resolution_hours: int = Field(default=24, ge=0)


class _PipelineStage(TypedDict):
    stage: str
    display: str
    probability: int
