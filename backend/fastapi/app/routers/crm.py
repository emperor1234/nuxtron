# pyright: reportUnusedFunction=false
# NEW MODULE — CRM Engine (Part 3 Section 14.1)
# Implements HubSpot-class CRM: contacts, companies, deals, pipeline, lead scoring.
# Follows the same in-memory + optional PostgreSQL fallback pattern as all other routers.

import hashlib
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from starlette.concurrency import run_in_threadpool

from ..database import get_db_session
from ..deps import AuthContext, require_auth
from ..integrations.vendor_manager import VendorCredentials, VendorType, get_vendor_manager
from ..models import Activity, Company, Contact, Deal, Lead, Task, Ticket, WorkflowExecution, WorkflowRule

AuthDep = Annotated[AuthContext, Depends(require_auth)]
CONTACT_NOT_FOUND = 'Contact not found.'
DEAL_NOT_FOUND = 'Deal not found.'
LEAD_NOT_FOUND = 'Lead not found.'
TICKET_NOT_FOUND = 'Ticket not found.'
TASK_NOT_FOUND = 'Task not found.'
CAMPAIGN_NOT_FOUND = 'Campaign not found.'
QUOTE_NOT_FOUND = 'Quote not found.'
INVOICE_NOT_FOUND = 'CRM invoice not found.'
SEQUENCE_NOT_FOUND = 'Email sequence not found.'
WORKFLOW_NOT_FOUND = 'Workflow rule not found.'
SEGMENT_NOT_FOUND = 'Segment not found.'
PROJECT_NOT_FOUND = 'Project not found.'
ENTITY_TYPE_NOT_FOUND = 'Custom entity type not found.'
AUTOMATION_RECIPE_NOT_FOUND = 'Automation recipe not found.'


# ── Request models ────────────────────────────────────────────────────────────

class ContactCreateRequest(BaseModel):
    email: str = Field(default='', max_length=255)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(default='', max_length=120)
    company: str = Field(default='', max_length=180)
    phone: str = Field(default='', max_length=40)
    lifecycle_stage: str = Field(default='lead', max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=20)
    properties: dict[str, Any] = Field(default_factory=dict)


class ContactScoreRequest(BaseModel):
    score: int = Field(ge=0, le=100)
    reason: str = Field(default='', max_length=320)


class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    domain: str = Field(default='', max_length=180)
    industry: str = Field(default='', max_length=80)
    employee_count: int = Field(default=0, ge=0)
    annual_revenue: float = Field(default=0.0, ge=0.0)
    properties: dict[str, Any] = Field(default_factory=dict)


class DealCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    value: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default='USD', max_length=8)
    stage: str = Field(default='prospect', max_length=60)
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
    type: str = Field(default='note', max_length=40)  # note, call, email, meeting
    subject: str = Field(min_length=1, max_length=240)
    body: str = Field(default='', max_length=4000)
    contact_id: int | None = None
    deal_id: int | None = None


class ContactDedupeRequest(BaseModel):
    dry_run: bool = Field(default=True)


class CRMWebhookCreateRequest(BaseModel):
    event: str = Field(pattern=r'^(contact\.created|contact\.updated|deal\.created|deal\.updated|activity\.created|lead\.created|ticket\.created|ticket\.updated|task\.completed)$')
    target_url: str = Field(min_length=8, max_length=600)
    secret: str = Field(default='', max_length=200)


class HubSpotConnectRequest(BaseModel):
    access_token: str | None = Field(default=None, max_length=4096)
    api_key: str | None = Field(default=None, max_length=4096)
    portal_id: str | None = Field(default=None, max_length=80)
    endpoint_url: str | None = Field(default=None, max_length=300)
    verify_live: bool = Field(default=True)


class HubSpotSyncContactsRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=200)
    lifecycle_stage: str = Field(default='lead', max_length=40)
    source: str = Field(default='hubspot', max_length=80)


# ── Sales Automation / Leads ──────────────────────────────────────────────────

class LeadCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    contact_id: int | None = None
    company_id: int | None = None
    source: str = Field(default='api', max_length=60)
    estimated_value: float = Field(default=0.0, ge=0.0)
    status: str = Field(default='new', max_length=40)
    score: int = Field(default=0, ge=0, le=100)
    assigned_to: str = Field(default='', max_length=120)
    notes: str = Field(default='', max_length=2000)


class LeadUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    score: int | None = Field(default=None, ge=0, le=100)
    assigned_to: str | None = Field(default=None, max_length=120)
    estimated_value: float | None = Field(default=None, ge=0.0)
    notes: str | None = Field(default=None, max_length=2000)


# ── Task Management ───────────────────────────────────────────────────────────

class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default='', max_length=4000)
    contact_id: int | None = None
    deal_id: int | None = None
    due_date: str | None = Field(default=None, max_length=30)
    priority: str = Field(default='medium', max_length=20)
    assigned_to: str = Field(default='', max_length=120)
    type: str = Field(default='task', max_length=40)


class TaskUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    priority: str | None = Field(default=None, max_length=20)
    due_date: str | None = Field(default=None, max_length=30)
    assigned_to: str | None = Field(default=None, max_length=120)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(default='', max_length=2000)
    owner: str = Field(default='', max_length=120)
    status: str = Field(default='planning', max_length=40)
    due_date: str | None = Field(default=None, max_length=30)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=40)
    due_date: str | None = Field(default=None, max_length=30)


# ── Support Ticketing ─────────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=320)
    description: str = Field(default='', max_length=8000)
    contact_id: int | None = None
    priority: str = Field(default='medium', max_length=20)
    channel: str = Field(default='email', max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=10)


class TicketUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    priority: str | None = Field(default=None, max_length=20)
    assigned_to: str | None = Field(default=None, max_length=120)
    resolution: str | None = Field(default=None, max_length=4000)


# ── Marketing Campaigns ───────────────────────────────────────────────────────

class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    type: str = Field(default='email', max_length=40)
    subject: str = Field(default='', max_length=320)
    body: str = Field(default='', max_length=20000)
    segment_id: int | None = None
    scheduled_at: str | None = Field(default=None, max_length=30)
    ab_test: bool = Field(default=False)
    variant_b_subject: str = Field(default='', max_length=320)


# ── Contact Segments ──────────────────────────────────────────────────────────

class SegmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(default='', max_length=1000)
    filters: dict[str, Any] = Field(default_factory=dict)


# ── Notes (on contacts / deals / companies) ───────────────────────────────────

class NoteCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    contact_id: int | None = None
    deal_id: int | None = None
    company_id: int | None = None
    pinned: bool = Field(default=False)


# ── Quotes ────────────────────────────────────────────────────────────────────

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
    currency: str = Field(default='USD', max_length=8)
    valid_until: str | None = Field(default=None, max_length=30)
    notes: str = Field(default='', max_length=4000)


# ── CRM Invoices ──────────────────────────────────────────────────────────────

class CRMInvoiceCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    contact_id: int | None = None
    deal_id: int | None = None
    quote_id: int | None = None
    amount: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default='USD', max_length=8)
    due_date: str | None = Field(default=None, max_length=30)
    notes: str = Field(default='', max_length=4000)


class CRMInvoiceUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    paid_at: str | None = Field(default=None, max_length=30)


# ── Email Sequences ───────────────────────────────────────────────────────────

class SequenceStep(BaseModel):
    day_offset: int = Field(default=0, ge=0)
    subject: str = Field(min_length=1, max_length=320)
    body: str = Field(min_length=1, max_length=20000)
    type: str = Field(default='email', max_length=20)


class EmailSequenceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(default='', max_length=1000)
    steps: list[SequenceStep] = Field(default_factory=list)


# ── Workflow Rules (Sales Automation) ─────────────────────────────────────────

class WorkflowRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    trigger: str = Field(min_length=1, max_length=60)
    conditions: dict[str, Any] = Field(default_factory=dict)
    action: str = Field(min_length=1, max_length=60)
    action_params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)


class CustomEntityTypeCreateRequest(BaseModel):
    key: str = Field(pattern=r'^[a-z][a-z0-9_]{1,60}$')
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=800)
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
    full_backup_weekday: str = Field(default='sunday', pattern=r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$')
    full_backup_hour_utc: int = Field(default=3, ge=0, le=23)
    retention_days: int = Field(default=30, ge=7, le=365)
    enabled: bool = Field(default=True)


class CRMLiveSyncToggleRequest(BaseModel):
    enabled: bool = Field(default=True)
    interval_seconds: int = Field(default=30, ge=5, le=3600)


# ── SLA Rules ─────────────────────────────────────────────────────────────────

class SLARuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    applies_to: str = Field(default='ticket', max_length=40)
    priority: str = Field(default='medium', max_length=20)
    first_response_hours: int = Field(default=4, ge=0)
    resolution_hours: int = Field(default=24, ge=0)


# ── Pipeline stages (standard CRM stages per spec) ───────────────────────────

class _PipelineStage(TypedDict):
    stage: str
    display: str
    probability: int


PIPELINE_STAGES: list[_PipelineStage] = [
    {'stage': 'prospect', 'display': 'Prospect', 'probability': 10},
    {'stage': 'qualified', 'display': 'Qualified', 'probability': 25},
    {'stage': 'proposal', 'display': 'Proposal', 'probability': 50},
    {'stage': 'negotiation', 'display': 'Negotiation', 'probability': 75},
    {'stage': 'closed_won', 'display': 'Closed Won', 'probability': 100},
    {'stage': 'closed_lost', 'display': 'Closed Lost', 'probability': 0},
]


# ── Factory ───────────────────────────────────────────────────────────────────

def create_crm_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    contacts_memory: list[dict[str, Any]],
    companies_memory: list[dict[str, Any]],
    deals_memory: list[dict[str, Any]],
    activities_memory: list[dict[str, Any]],
    webhook_subscriptions_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    leads_memory: list[dict[str, Any]],
    tasks_memory: list[dict[str, Any]],
    tickets_memory: list[dict[str, Any]],
    campaigns_memory: list[dict[str, Any]],
    segments_memory: list[dict[str, Any]],
    notes_memory: list[dict[str, Any]],
    quotes_memory: list[dict[str, Any]],
    crm_invoices_memory: list[dict[str, Any]],
    email_sequences_memory: list[dict[str, Any]],
    workflow_rules_memory: list[dict[str, Any]],
    sla_rules_memory: list[dict[str, Any]],
    projects_memory: list[dict[str, Any]],
    custom_entity_types_memory: list[dict[str, Any]],
    custom_entity_records_memory: list[dict[str, Any]],
    automation_recipes_memory: list[dict[str, Any]],
    api_tokens_memory: list[dict[str, Any]],
    backup_snapshots_memory: list[dict[str, Any]],
    live_sync_state_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter()
    lock = threading.Lock()
    vendor_manager = get_vendor_manager()

    def _contact_to_dict(contact: Contact) -> dict[str, Any]:
        data = dict(contact.data or {})
        tags = data.get('tags', [])
        return {
            'id': contact.id,
            'tenant_id': contact.tenant_id,
            'email': contact.email,
            'first_name': contact.first_name,
            'last_name': contact.last_name,
            'company': contact.company,
            'phone': contact.phone,
            'lifecycle_stage': contact.lifecycle_stage,
            'lead_score': contact.score,
            'tags': tags if isinstance(tags, list) else [],
            'properties': data.get('properties', {}),
            'score_reason': data.get('score_reason', ''),
            'created_at': contact.created_at.isoformat(),
            'updated_at': contact.updated_at.isoformat(),
            'source': data.get('source', 'api'),
        }

    def _list_db_contacts(tenant_id: str) -> list[dict[str, Any]]:
        with get_db_session() as session:
            contacts = session.query(Contact).filter(Contact.tenant_id == tenant_id).all()
            return [_contact_to_dict(contact) for contact in contacts]

    def _upsert_contact_from_vendor(tenant_id: str, payload: dict[str, Any]) -> str:
        with get_db_session() as session:
            email = str(payload.get('email', '')).strip().lower()
            if not email:
                return 'skipped'
            existing = session.query(Contact).filter(Contact.tenant_id == tenant_id, Contact.email == email).first()
            if existing is None:
                created = Contact(
                    tenant_id=tenant_id,
                    email=email,
                    first_name=str(payload.get('first_name', '')).strip(),
                    last_name=str(payload.get('last_name', '')).strip(),
                    company=str(payload.get('company', '')).strip(),
                    phone=str(payload.get('phone', '')).strip(),
                    lifecycle_stage=str(payload.get('lifecycle_stage', 'lead')).strip() or 'lead',
                    score=0,
                    data={'source': str(payload.get('source', 'hubspot')), 'properties': {}},
                )
                session.add(created)
                session.flush()
                return 'created'

            changed = False
            first_name = str(payload.get('first_name', '')).strip()
            last_name = str(payload.get('last_name', '')).strip()
            company = str(payload.get('company', '')).strip()
            phone = str(payload.get('phone', '')).strip()
            lifecycle_stage = str(payload.get('lifecycle_stage', '')).strip()

            if first_name and first_name != existing.first_name:
                existing.first_name = first_name
                changed = True
            if last_name and last_name != existing.last_name:
                existing.last_name = last_name
                changed = True
            if company and company != existing.company:
                existing.company = company
                changed = True
            if phone and phone != existing.phone:
                existing.phone = phone
                changed = True
            if lifecycle_stage and lifecycle_stage != existing.lifecycle_stage:
                existing.lifecycle_stage = lifecycle_stage
                changed = True

            if changed:
                session.flush()
                return 'updated'
            return 'skipped'

    def _company_to_dict(company: Company) -> dict[str, Any]:
        data = dict(company.data or {})
        return {
            'id': company.id,
            'tenant_id': company.tenant_id,
            'name': company.name,
            'domain': company.domain,
            'industry': company.industry,
            'employee_count': company.employee_count,
            'annual_revenue': company.annual_revenue,
            'account_health': data.get('account_health', 'green'),
            'properties': data.get('properties', {}),
            'created_at': company.created_at.isoformat(),
            'updated_at': company.updated_at.isoformat(),
            'source': data.get('source', 'api'),
        }

    def _list_db_companies(tenant_id: str) -> list[dict[str, Any]]:
        with get_db_session() as session:
            companies = session.query(Company).filter(Company.tenant_id == tenant_id).all()
            return [_company_to_dict(company) for company in companies]

    def _deal_to_dict(deal: Deal) -> dict[str, Any]:
        data = dict(deal.data or {})
        return {
            'id': deal.id,
            'tenant_id': deal.tenant_id,
            'title': deal.title,
            'value': deal.value,
            'currency': deal.currency,
            'stage': deal.stage,
            'contact_id': deal.contact_id,
            'company_id': deal.company_id,
            'close_date': deal.close_date,
            'probability': int(data.get('probability', next((s['probability'] for s in PIPELINE_STAGES if s['stage'] == deal.stage), 10))),
            'properties': data.get('properties', {}),
            'created_at': deal.created_at.isoformat(),
            'updated_at': deal.updated_at.isoformat(),
            'source': data.get('source', 'api'),
        }

    def _list_db_deals(tenant_id: str) -> list[dict[str, Any]]:
        with get_db_session() as session:
            deals = session.query(Deal).filter(Deal.tenant_id == tenant_id).all()
            return [_deal_to_dict(deal) for deal in deals]

    # ── DB helpers: Workflow Rules ───────────────────────────────────────────

    def _workflow_rule_to_dict(obj: WorkflowRule) -> dict[str, Any]:
        data = dict(obj.data or {})
        actions = dict(obj.actions or {})
        conditions = dict(obj.conditions or {})
        return {
            'id': obj.id,
            'tenant_id': obj.tenant_id,
            'name': obj.name,
            'trigger': obj.trigger,
            'conditions': conditions,
            'action': str(actions.get('type', '')),
            'action_params': dict(actions.get('params') or {}),
            'enabled': obj.enabled,
            'run_count': int(data.get('run_count', 0)),
            'last_triggered_at': data.get('last_triggered_at'),
            'created_at': obj.created_at.isoformat(),
            'updated_at': obj.updated_at.isoformat(),
        }

    def _get_db_workflow_rule(rule_id: int, tenant_id: str) -> WorkflowRule | None:
        with get_db_session() as session:
            return session.query(WorkflowRule).filter(WorkflowRule.id == rule_id, WorkflowRule.tenant_id == tenant_id).first()

    def _create_db_workflow_rule(tenant_id: str, payload: WorkflowRuleCreateRequest) -> tuple[dict[str, Any], bool]:
        with get_db_session() as session:
            existing = (
                session.query(WorkflowRule)
                .filter(
                    WorkflowRule.tenant_id == tenant_id,
                    WorkflowRule.name == payload.name,
                    WorkflowRule.trigger == payload.trigger,
                )
                .first()
            )
            if existing is not None:
                existing_action = dict(existing.actions or {})
                if str(existing_action.get('type', '')).strip().lower() == payload.action.strip().lower():
                    return _workflow_rule_to_dict(existing), True

            obj = WorkflowRule(
                tenant_id=tenant_id,
                name=payload.name,
                trigger=payload.trigger,
                conditions=payload.conditions,
                actions={'type': payload.action, 'params': payload.action_params},
                enabled=payload.enabled,
                data={'run_count': 0, 'last_triggered_at': None, 'source': 'api'},
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return _workflow_rule_to_dict(obj), False

    def _list_db_workflow_rules(tenant_id: str) -> list[dict[str, Any]]:
        with get_db_session() as session:
            rows = session.query(WorkflowRule).filter(WorkflowRule.tenant_id == tenant_id).order_by(WorkflowRule.created_at.desc()).all()
            return [_workflow_rule_to_dict(row) for row in rows]

    def _trigger_db_workflow_rule(rule_id: int, tenant_id: str, triggered_at: str) -> dict[str, Any] | None:
        now_dt = datetime.fromisoformat(triggered_at)
        with get_db_session() as session:
            obj = session.query(WorkflowRule).filter(WorkflowRule.id == rule_id, WorkflowRule.tenant_id == tenant_id).first()
            if obj is None:
                return None

            data = dict(obj.data or {})
            run_count = int(data.get('run_count', 0)) + 1
            data['run_count'] = run_count
            data['last_triggered_at'] = triggered_at
            obj.data = data

            execution = WorkflowExecution(
                tenant_id=tenant_id,
                workflow_id=obj.id,
                trigger_type=obj.trigger,
                trigger_entity_id=None,
                status='completed',
                started_at=now_dt,
                completed_at=now_dt,
                steps_executed=[
                    {
                        'step': 'workflow_rule_triggered',
                        'action': dict(obj.actions or {}),
                        'completed_at': triggered_at,
                    }
                ],
                current_step_id='workflow_rule_triggered',
                result={'triggered_at': triggered_at, 'run_count': run_count},
                error_message=None,
                data={'source': 'crm_router'},
            )
            session.add(execution)
            session.commit()
            session.refresh(obj)
            return _workflow_rule_to_dict(obj)

    # ── DB helpers: Activity ──────────────────────────────────────────────────

    def _activity_to_dict(obj: Activity) -> dict[str, Any]:
        d = dict(obj.data or {})
        return {
            'id': obj.id,
            'tenant_id': obj.tenant_id,
            'type': obj.type,
            'subject': d.get('subject', obj.description),
            'body': obj.description,
            'contact_id': obj.contact_id,
            'deal_id': obj.deal_id,
            'source': d.get('source', 'api'),
            'created_at': obj.created_at.isoformat(),
            'updated_at': obj.updated_at.isoformat(),
        }

    def _create_db_activity(tenant_id: str, payload: ActivityCreateRequest) -> dict[str, Any]:
        with get_db_session() as session:
            obj = Activity(
                tenant_id=tenant_id,
                type=payload.type,
                contact_id=payload.contact_id or 0,
                deal_id=payload.deal_id,
                description=payload.body,
                data={'subject': payload.subject, 'source': 'api'},
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return _activity_to_dict(obj)

    def _list_db_activities(
        tenant_id: str,
        type_filter: str | None = None,
        contact_id: int | None = None,
        deal_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with get_db_session() as session:
            q = session.query(Activity).filter(Activity.tenant_id == tenant_id)
            if type_filter:
                q = q.filter(Activity.type == type_filter)
            if contact_id is not None:
                q = q.filter(Activity.contact_id == contact_id)
            if deal_id is not None:
                q = q.filter(Activity.deal_id == deal_id)
            total = q.count()
            rows = q.order_by(Activity.created_at.desc()).offset(offset).limit(limit).all()
            return [_activity_to_dict(r) for r in rows], total

    # ── DB helpers: Lead ──────────────────────────────────────────────────────

    def _lead_to_dict(obj: Lead) -> dict[str, Any]:
        d = dict(obj.data or {})
        return {
            'id': obj.id,
            'tenant_id': obj.tenant_id,
            'title': obj.title,
            'contact_id': obj.contact_id,
            'company_id': obj.company_id,
            'source': obj.source,
            'estimated_value': obj.estimated_value,
            'status': obj.status,
            'score': obj.score,
            'assigned_to': obj.assigned_to,
            'notes': d.get('notes', ''),
            'converted_deal_id': d.get('converted_deal_id'),
            'created_at': obj.created_at.isoformat(),
            'updated_at': obj.updated_at.isoformat(),
        }

    def _create_db_lead(tenant_id: str, payload: LeadCreateRequest) -> dict[str, Any]:
        with get_db_session() as session:
            obj = Lead(
                tenant_id=tenant_id,
                title=payload.title,
                contact_id=payload.contact_id,
                company_id=payload.company_id,
                source=payload.source,
                estimated_value=payload.estimated_value,
                status=payload.status,
                score=payload.score,
                assigned_to=payload.assigned_to,
                data={'notes': payload.notes},
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return _lead_to_dict(obj)

    def _find_duplicate_db_lead(tenant_id: str, payload: LeadCreateRequest) -> dict[str, Any] | None:
        normalized_title = payload.title.strip().lower()
        normalized_source = payload.source.strip().lower()
        normalized_status = payload.status.strip().lower()
        with get_db_session() as session:
            existing = (
                session.query(Lead)
                .filter(
                    Lead.tenant_id == tenant_id,
                    func.lower(Lead.title) == normalized_title,
                    func.lower(Lead.source) == normalized_source,
                    func.lower(Lead.status) == normalized_status,
                )
                .order_by(Lead.created_at.desc(), Lead.id.desc())
                .first()
            )
            if existing is None:
                return None
            # Treat duplicates as idempotent retries only within a short window.
            created_at = existing.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            if datetime.now(UTC) - created_at > timedelta(minutes=5):
                return None
            return _lead_to_dict(existing)

    def _list_db_leads(
        tenant_id: str,
        status: str | None = None,
        assigned_to: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with get_db_session() as session:
            query = session.query(Lead).filter(Lead.tenant_id == tenant_id)
            if status:
                query = query.filter(Lead.status == status)
            if assigned_to:
                query = query.filter(Lead.assigned_to.ilike(assigned_to))
            if q:
                query = query.filter(Lead.title.ilike(f'%{q}%'))
            total = query.count()
            rows = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
            return [_lead_to_dict(r) for r in rows], total

    def _get_db_lead(lead_id: int, tenant_id: str) -> Lead | None:
        with get_db_session() as session:
            return session.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()

    # ── DB helpers: Task ──────────────────────────────────────────────────────

    def _task_to_dict(obj: Task) -> dict[str, Any]:
        d = dict(obj.data or {})
        return {
            'id': obj.id,
            'tenant_id': obj.tenant_id,
            'title': obj.title,
            'description': d.get('description', ''),
            'contact_id': obj.related_contact_id,
            'deal_id': d.get('deal_id'),
            'due_date': obj.due_date,
            'priority': obj.priority,
            'assigned_to': obj.assigned_to,
            'type': d.get('type', 'task'),
            'status': obj.status,
            'created_at': obj.created_at.isoformat(),
            'updated_at': obj.updated_at.isoformat(),
        }

    def _create_db_task(tenant_id: str, payload: TaskCreateRequest) -> dict[str, Any]:
        with get_db_session() as session:
            obj = Task(
                tenant_id=tenant_id,
                title=payload.title,
                status='open',
                priority=payload.priority,
                assigned_to=payload.assigned_to,
                due_date=payload.due_date,
                related_contact_id=payload.contact_id,
                data={'description': payload.description, 'deal_id': payload.deal_id, 'type': payload.type},
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return _task_to_dict(obj)

    def _find_duplicate_db_task(tenant_id: str, payload: TaskCreateRequest) -> dict[str, Any] | None:
        normalized_title = payload.title.strip().lower()
        normalized_priority = payload.priority.strip().lower()
        normalized_assignee = payload.assigned_to.strip().lower()
        with get_db_session() as session:
            existing = (
                session.query(Task)
                .filter(
                    Task.tenant_id == tenant_id,
                    func.lower(Task.title) == normalized_title,
                    func.lower(Task.priority) == normalized_priority,
                    func.lower(Task.assigned_to) == normalized_assignee,
                )
                .order_by(Task.created_at.desc(), Task.id.desc())
                .first()
            )
            if existing is None:
                return None
            created_at = existing.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            if datetime.now(UTC) - created_at > timedelta(minutes=5):
                return None
            return _task_to_dict(existing)

    def _list_db_tasks(
        tenant_id: str,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        contact_id: int | None = None,
        deal_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with get_db_session() as session:
            q = session.query(Task).filter(Task.tenant_id == tenant_id)
            if status:
                q = q.filter(Task.status == status)
            if priority:
                q = q.filter(Task.priority == priority)
            if assigned_to:
                q = q.filter(Task.assigned_to.ilike(assigned_to))
            if contact_id is not None:
                q = q.filter(Task.related_contact_id == contact_id)
            total = q.count()
            rows = q.order_by(Task.due_date.asc().nullslast(), Task.created_at.asc()).offset(offset).limit(limit).all()
            result = [_task_to_dict(r) for r in rows]
            if deal_id is not None:
                result = [t for t in result if t.get('deal_id') == deal_id]
            return result, total

    # ── DB helpers: Ticket ────────────────────────────────────────────────────

    def _ticket_to_dict(obj: Ticket) -> dict[str, Any]:
        d = dict(obj.data or {})
        return {
            'id': obj.id,
            'tenant_id': obj.tenant_id,
            'ticket_number': obj.ticket_number,
            'subject': obj.subject,
            'description': obj.description,
            'contact_id': obj.contact_id,
            'priority': obj.priority,
            'channel': obj.channel,
            'status': obj.status,
            'assigned_to': obj.assigned_to,
            'escalated': obj.escalated,
            'resolution': obj.resolution,
            'tags': obj.tags if isinstance(obj.tags, list) else [],
            'first_response_deadline': d.get('first_response_deadline'),
            'resolution_deadline': d.get('resolution_deadline'),
            'created_at': obj.created_at.isoformat(),
            'updated_at': obj.updated_at.isoformat(),
        }

    def _create_db_ticket(
        tenant_id: str,
        payload: TicketCreateRequest,
        ticket_number: str,
        first_response_deadline: str | None,
        resolution_deadline: str | None,
    ) -> dict[str, Any]:
        with get_db_session() as session:
            obj = Ticket(
                tenant_id=tenant_id,
                ticket_number=ticket_number,
                subject=payload.subject,
                description=payload.description,
                contact_id=payload.contact_id,
                priority=payload.priority,
                channel=payload.channel,
                status='open',
                tags=payload.tags,
                data={'first_response_deadline': first_response_deadline, 'resolution_deadline': resolution_deadline},
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return _ticket_to_dict(obj)

    def _list_db_tickets(
        tenant_id: str,
        status: str | None = None,
        priority: str | None = None,
        channel: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with get_db_session() as session:
            q = session.query(Ticket).filter(Ticket.tenant_id == tenant_id)
            if status:
                q = q.filter(Ticket.status == status)
            if priority:
                q = q.filter(Ticket.priority == priority)
            if channel:
                q = q.filter(Ticket.channel == channel)
            total = q.count()
            rows = q.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()
            return [_ticket_to_dict(r) for r in rows], total

    def _get_db_ticket(ticket_id: int, tenant_id: str) -> Ticket | None:
        with get_db_session() as session:
            return session.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id).first()

    def _dedupe_contacts_impl(payload: ContactDedupeRequest, auth: AuthDep) -> dict[str, Any]:
        with lock:
            tenant_mem_contacts = [c for c in contacts_memory if str(c.get('tenant_id', '')) == str(auth.tenant_id)]
        if tenant_mem_contacts:
            groups: dict[str, list[dict[str, Any]]] = {}
            for contact in tenant_mem_contacts:
                email = str(contact.get('email', '')).strip().lower()
                if not email:
                    continue
                groups.setdefault(email, []).append(contact)

            duplicate_groups = [group for group in groups.values() if len(group) > 1]
            merge_preview: list[dict[str, Any]] = []
            merged_contacts = 0

            if not payload.dry_run:
                duplicate_ids_to_remove: set[int] = set()

            with lock:
                for group in duplicate_groups:
                    group.sort(key=lambda item: int(item.get('id', 0)))
                    canonical = group[0]
                    duplicates = group[1:]
                    duplicate_ids = [int(item.get('id', 0)) for item in duplicates]

                    if payload.dry_run:
                        merge_preview.append({'canonical_id': int(canonical.get('id', 0)), 'duplicate_ids': duplicate_ids})
                        continue

                    canonical_tags = {str(tag) for tag in canonical.get('tags', []) if isinstance(tag, str)}
                    for dup in duplicates:
                        for tag in dup.get('tags', []):
                            if isinstance(tag, str) and tag:
                                canonical_tags.add(tag)
                        if not canonical.get('phone') and dup.get('phone'):
                            canonical['phone'] = dup.get('phone')
                        if not canonical.get('company') and dup.get('company'):
                            canonical['company'] = dup.get('company')

                    canonical['tags'] = sorted(canonical_tags)
                    canonical['updated_at'] = datetime.now(UTC).isoformat()

                    canonical_id = int(canonical.get('id', 0))
                    for deal in deals_memory:
                        if deal.get('tenant_id') != auth.tenant_id:
                            continue
                        if int(deal.get('contact_id') or 0) in duplicate_ids:
                            deal['contact_id'] = canonical_id
                    for activity in activities_memory:
                        if activity.get('tenant_id') != auth.tenant_id:
                            continue
                        if int(activity.get('contact_id') or 0) in duplicate_ids:
                            activity['contact_id'] = canonical_id

                    duplicate_ids_to_remove.update(duplicate_ids)
                    merged_contacts += len(duplicates)

                if not payload.dry_run and duplicate_ids_to_remove:
                    contacts_memory[:] = [
                        c for c in contacts_memory
                        if not (
                            str(c.get('tenant_id', '')) == str(auth.tenant_id)
                            and int(c.get('id', 0)) in duplicate_ids_to_remove
                        )
                    ]

            _audit(auth.tenant_id, 'crm_contacts_deduped', merged_contacts)
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'dry_run': payload.dry_run,
                'duplicate_group_count': len(duplicate_groups),
                'merged_contacts': 0 if payload.dry_run else merged_contacts,
                'merge_preview': merge_preview[:50],
            }

        with get_db_session() as session:
            tenant_contacts = [
                _contact_to_dict(contact)
                for contact in session.query(Contact).filter(Contact.tenant_id == auth.tenant_id).all()
            ]
            groups: dict[str, list[dict[str, Any]]] = {}
            for contact in tenant_contacts:
                email = str(contact.get('email', '')).strip().lower()
                if not email:
                    continue
                groups.setdefault(email, []).append(contact)

            duplicate_groups = [group for group in groups.values() if len(group) > 1]
            merge_preview: list[dict[str, Any]] = []
            merged_contacts = 0
            for group in duplicate_groups:
                group.sort(key=lambda item: int(item.get('id', 0)))
                canonical = group[0]
                duplicates = group[1:]
                duplicate_ids = [int(item.get('id', 0)) for item in duplicates]

                if payload.dry_run:
                    merge_preview.append({'canonical_id': int(canonical.get('id', 0)), 'duplicate_ids': duplicate_ids})
                    continue

                canonical_tags = {str(tag) for tag in canonical.get('tags', []) if isinstance(tag, str)}
                for dup in duplicates:
                    for tag in dup.get('tags', []):
                        if isinstance(tag, str) and tag:
                            canonical_tags.add(tag)
                    if not canonical.get('phone') and dup.get('phone'):
                        canonical['phone'] = dup.get('phone')
                    if not canonical.get('company') and dup.get('company'):
                        canonical['company'] = dup.get('company')
                canonical['tags'] = sorted(canonical_tags)
                canonical['updated_at'] = datetime.now(UTC).isoformat()

                canonical_row = session.query(Contact).filter_by(
                    id=int(canonical.get('id', 0)),
                    tenant_id=auth.tenant_id,
                ).first()
                if canonical_row is not None:
                    canonical_data = dict(canonical_row.data or {})
                    canonical_data['tags'] = canonical['tags']
                    canonical_data['properties'] = canonical.get('properties', canonical_data.get('properties', {}))
                    canonical_row.phone = str(canonical.get('phone', '') or canonical_row.phone)
                    canonical_row.company = str(canonical.get('company', '') or canonical_row.company)
                    canonical_row.data = canonical_data

                canonical_id = int(canonical.get('id', 0))
                with lock:
                    for deal in deals_memory:
                        if deal.get('tenant_id') != auth.tenant_id:
                            continue
                        if int(deal.get('contact_id') or 0) in duplicate_ids:
                            deal['contact_id'] = canonical_id

                    for activity in activities_memory:
                        if activity.get('tenant_id') != auth.tenant_id:
                            continue
                        if int(activity.get('contact_id') or 0) in duplicate_ids:
                            activity['contact_id'] = canonical_id

                if duplicate_ids:
                    session.query(Contact).filter(
                        Contact.tenant_id == auth.tenant_id,
                        Contact.id.in_(duplicate_ids),
                    ).delete(synchronize_session=False)
                merged_contacts += len(duplicates)

        _audit(auth.tenant_id, 'crm_contacts_deduped', merged_contacts)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'dry_run': payload.dry_run,
            'duplicate_group_count': len(duplicate_groups),
            'merged_contacts': 0 if payload.dry_run else merged_contacts,
            'merge_preview': merge_preview[:50],
        }

    weekday_map = {
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
        'saturday': 5,
        'sunday': 6,
    }

    def _next_full_backup_utc(config: dict[str, Any], now: datetime) -> datetime:
        target_weekday = weekday_map.get(str(config.get('full_backup_weekday', 'sunday')).lower(), 6)
        target_hour = int(config.get('full_backup_hour_utc', 3))
        days_ahead = (target_weekday - now.weekday()) % 7
        candidate = (now + timedelta(days=days_ahead)).replace(minute=0, second=0, microsecond=0, hour=target_hour)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate

    def _get_backup_config(tenant_id: str) -> dict[str, Any]:
        existing = next((row for row in backup_snapshots_memory if row.get('tenant_id') == tenant_id and row.get('type') == 'config'), None)
        now_iso = datetime.now(UTC).isoformat()
        if existing is not None:
            return existing
        config = {
            'id': len(backup_snapshots_memory) + 1,
            'tenant_id': tenant_id,
            'type': 'config',
            'incremental_minutes': 5,
            'full_backup_weekday': 'sunday',
            'full_backup_hour_utc': 3,
            'retention_days': 30,
            'enabled': True,
            'updated_at': now_iso,
        }
        backup_snapshots_memory.append(config)
        return config

    def _get_live_sync_state(tenant_id: str) -> dict[str, Any]:
        existing = next((row for row in live_sync_state_memory if row.get('tenant_id') == tenant_id), None)
        now_iso = datetime.now(UTC).isoformat()
        if existing is not None:
            return existing
        state = {
            'id': len(live_sync_state_memory) + 1,
            'tenant_id': tenant_id,
            'enabled': True,
            'interval_seconds': 30,
            'last_sync_at': None,
            'last_success_at': None,
            'lag_seconds': 0,
            'events_processed_24h': 0,
            'conflict_queue': 0,
            'updated_at': now_iso,
            'provider_status': {
                'crm_core': 'healthy',
                'billing': 'healthy',
                'automation': 'healthy',
                'inbox': 'healthy',
            },
        }
        live_sync_state_memory.append(state)
        return state

    def _audit(tenant_id: str, action: str, resource_id: int | None = None) -> None:
        with lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'resource_id': resource_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'crm-router',
            })

    def _parse_iso_datetime(value: Any) -> datetime | None:
        raw = str(value or '').strip()
        if not raw:
            return None
        if len(raw) == 10:
            raw = f'{raw}T00:00:00+00:00'
        if raw.endswith('Z'):
            raw = f'{raw[:-1]}+00:00'
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _is_in_window(value: Any, window_start: datetime) -> bool:
        parsed = _parse_iso_datetime(value)
        return parsed is not None and parsed >= window_start

    def _to_window_days(days: int) -> int:
        if days <= 7:
            return 7
        if days >= 365:
            return 365
        return days

    # ── Contacts ─────────────────────────────────────────────────────────────

    @router.post('/crm/contacts')
    def create_contact(  # pyright: ignore[reportUnusedFunction]
        payload: ContactCreateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:contacts:create', 120, 60)
        with get_db_session() as session:
            existing = session.query(Contact).filter_by(
                tenant_id=auth.tenant_id,
                email=str(payload.email),
            ).first()
            if existing is not None:
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'contact': _contact_to_dict(existing),
                    'duplicate': True,
                }

            contact = Contact(
                tenant_id=auth.tenant_id,
                email=str(payload.email),
                first_name=payload.first_name,
                last_name=payload.last_name,
                company=payload.company,
                phone=payload.phone,
                lifecycle_stage=payload.lifecycle_stage,
                score=0,
                data={
                    'tags': payload.tags,
                    'properties': payload.properties,
                    'source': 'api',
                },
            )
            session.add(contact)
            session.flush()
            snapshot = _contact_to_dict(contact)

        _audit(auth.tenant_id, 'crm_contact_created', int(snapshot['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'contact': snapshot}

    @router.post('/crm/integrations/hubspot/connect')
    async def connect_hubspot(payload: HubSpotConnectRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:hubspot:connect', 60, 60)
        token = (payload.access_token or payload.api_key or '').strip()
        if not token:
            raise HTTPException(status_code=400, detail='Provide access_token or api_key.')

        endpoint_url = (payload.endpoint_url or '').strip() or None
        credentials = VendorCredentials(
            vendor_type=VendorType.CRM,
            platform='hubspot',
            api_key=token,
            access_token=token,
            endpoint_url=endpoint_url,
            additional_config={'portal_id': payload.portal_id or ''},
        )
        vendor_manager.store_credentials('hubspot_api', credentials)

        verified = False
        if payload.verify_live:
            response = await vendor_manager.make_request(
                'hubspot_api',
                'GET',
                '/crm/v3/objects/contacts',
                params={'limit': 1, 'properties': 'email,firstname,lastname'},
            )
            verified = isinstance(response, dict)

        _audit(auth.tenant_id, 'crm_hubspot_connected', payload.portal_id or 'portal_not_set')
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'integration': {
                'provider': 'hubspot',
                'connected': True,
                'verified': verified,
                'portal_id': payload.portal_id,
            },
        }

    @router.get('/crm/integrations/hubspot/status')
    def hubspot_status(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:hubspot:status', 120, 60)
        credentials = vendor_manager.get_credentials('hubspot_api')
        config = credentials.additional_config if credentials and isinstance(credentials.additional_config, dict) else {}
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'integration': {
                'provider': 'hubspot',
                'connected': credentials is not None,
                'portal_id': config.get('portal_id') if config else None,
            },
        }

    @router.post('/crm/integrations/hubspot/sync/contacts')
    async def sync_hubspot_contacts(payload: HubSpotSyncContactsRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:hubspot:sync:contacts', 30, 60)
        if not vendor_manager.has_credentials('hubspot_api'):
            raise HTTPException(status_code=400, detail='HubSpot integration is not connected.')

        response = await vendor_manager.make_request(
            'hubspot_api',
            'GET',
            '/crm/v3/objects/contacts',
            params={
                'limit': payload.limit,
                'properties': 'email,firstname,lastname,phone,company,lifecyclestage',
            },
        )

        rows = response.get('results', []) if isinstance(response, dict) else []
        created = 0
        updated = 0
        skipped = 0

        for row in rows:
            properties = row.get('properties', {}) if isinstance(row, dict) else {}
            mapped = {
                'email': properties.get('email', ''),
                'first_name': properties.get('firstname', ''),
                'last_name': properties.get('lastname', ''),
                'company': properties.get('company', ''),
                'phone': properties.get('phone', ''),
                'lifecycle_stage': properties.get('lifecyclestage', payload.lifecycle_stage),
                'source': payload.source,
            }
            result = await run_in_threadpool(_upsert_contact_from_vendor, auth.tenant_id, mapped)
            if result == 'created':
                created += 1
            elif result == 'updated':
                updated += 1
            else:
                skipped += 1

        _audit(auth.tenant_id, 'crm_hubspot_contacts_synced', f'created={created},updated={updated},skipped={skipped}')
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'provider': 'hubspot',
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'fetched': len(rows),
        }

    @router.get('/crm/contacts')  # NOSONAR
    def list_contacts(
        auth: AuthDep,
        q: Annotated[str | None, Query(max_length=160)] = None,
        lifecycle_stage: Annotated[str | None, Query(max_length=40)] = None,
        min_lead_score: Annotated[int, Query(ge=0, le=100)] = 0,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:contacts:list', 240, 60)
        query_text = (q or '').strip().lower()
        stage_filter = (lifecycle_stage or '').strip().lower()
        with get_db_session() as session:
            query = session.query(Contact).filter(Contact.tenant_id == auth.tenant_id)
            if stage_filter:
                query = query.filter(Contact.lifecycle_stage == stage_filter)
            if min_lead_score > 0:
                query = query.filter(Contact.score >= min_lead_score)
            if query_text:
                like_query = f'%{query_text}%'
                query = query.filter(
                    or_(
                        Contact.email.ilike(like_query),
                        Contact.first_name.ilike(like_query),
                        Contact.last_name.ilike(like_query),
                        Contact.company.ilike(like_query),
                    )
                )
            total = query.count()
            contacts = query.order_by(Contact.created_at.desc()).offset(offset).limit(limit).all()
            window = [_contact_to_dict(contact) for contact in contacts]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(window),
            'total': total,
            'limit': limit,
            'offset': offset,
            'contacts': window,
        }

    @router.post('/crm/contacts/dedupe')
    def dedupe_contacts(payload: ContactDedupeRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:contacts:dedupe', 30, 60)
        return _dedupe_contacts_impl(payload, auth)

    @router.get('/crm/contacts/{contact_id}', responses={404: {'description': CONTACT_NOT_FOUND}})
    def get_contact(contact_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:contacts:get', 300, 60)
        with get_db_session() as session:
            item = session.query(Contact).filter_by(id=contact_id, tenant_id=auth.tenant_id).first()
        if item is None:
            raise HTTPException(status_code=404, detail=CONTACT_NOT_FOUND)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'contact': _contact_to_dict(item)}

    @router.post('/crm/contacts/{contact_id}/score', responses={404: {'description': CONTACT_NOT_FOUND}})
    def score_contact(  # pyright: ignore[reportUnusedFunction]
        contact_id: int,
        payload: ContactScoreRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:contacts:score', 120, 60)
        with get_db_session() as session:
            item = session.query(Contact).filter_by(id=contact_id, tenant_id=auth.tenant_id).first()
            if item is None:
                raise HTTPException(status_code=404, detail=CONTACT_NOT_FOUND)
            data = dict(item.data or {})
            data['score_reason'] = payload.reason
            item.score = payload.score
            item.data = data
            session.flush()
            snapshot = _contact_to_dict(item)

        _audit(auth.tenant_id, 'crm_contact_scored', contact_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'contact': snapshot}

    # ── Companies ────────────────────────────────────────────────────────────

    @router.post('/crm/companies')
    def create_company(  # pyright: ignore[reportUnusedFunction]
        payload: CompanyCreateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:companies:create', 120, 60)
        with get_db_session() as session:
            company = Company(
                tenant_id=auth.tenant_id,
                name=payload.name,
                domain=payload.domain,
                industry=payload.industry,
                employee_count=payload.employee_count,
                annual_revenue=payload.annual_revenue,
                data={
                    'account_health': 'green',
                    'properties': payload.properties,
                    'source': 'api',
                },
            )
            session.add(company)
            session.flush()
            snapshot = _company_to_dict(company)

        _audit(auth.tenant_id, 'crm_company_created', int(snapshot['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'company': snapshot}

    @router.get('/crm/companies')  # NOSONAR
    def list_companies(
        auth: AuthDep,
        q: Annotated[str | None, Query(max_length=160)] = None,
        industry: Annotated[str | None, Query(max_length=80)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:companies:list', 240, 60)
        query_text = (q or '').strip().lower()
        industry_filter = (industry or '').strip().lower()
        with get_db_session() as session:
            query = session.query(Company).filter(Company.tenant_id == auth.tenant_id)
            if industry_filter:
                query = query.filter(Company.industry.ilike(industry_filter))
            if query_text:
                like_query = f'%{query_text}%'
                query = query.filter(or_(Company.name.ilike(like_query), Company.domain.ilike(like_query)))
            total = query.count()
            companies = query.order_by(Company.created_at.desc()).offset(offset).limit(limit).all()
            window = [_company_to_dict(company) for company in companies]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(window),
            'total': total,
            'limit': limit,
            'offset': offset,
            'companies': window,
        }

    # ── Deals ─────────────────────────────────────────────────────────────────

    @router.post('/crm/deals')
    def create_deal(  # pyright: ignore[reportUnusedFunction]
        payload: DealCreateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:deals:create', 120, 60)
        probability = next((s['probability'] for s in PIPELINE_STAGES if s['stage'] == payload.stage), 10)
        with get_db_session() as session:
            deal = Deal(
                tenant_id=auth.tenant_id,
                title=payload.title,
                value=payload.value,
                currency=payload.currency,
                stage=payload.stage,
                contact_id=payload.contact_id,
                company_id=payload.company_id,
                close_date=payload.close_date,
                data={
                    'probability': probability,
                    'properties': payload.properties,
                    'source': 'api',
                },
            )
            session.add(deal)
            session.flush()
            snapshot = _deal_to_dict(deal)

        _audit(auth.tenant_id, 'crm_deal_created', int(snapshot['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'deal': snapshot}

    @router.get('/crm/deals')  # NOSONAR
    def list_deals(
        auth: AuthDep,
        q: Annotated[str | None, Query(max_length=180)] = None,
        stage: Annotated[str | None, Query(max_length=60)] = None,
        min_value: Annotated[float, Query(ge=0.0)] = 0.0,
        max_value: Annotated[float | None, Query(ge=0.0)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:deals:list', 240, 60)
        query_text = (q or '').strip().lower()
        stage_filter = (stage or '').strip().lower()
        with get_db_session() as session:
            query = session.query(Deal).filter(Deal.tenant_id == auth.tenant_id)
            if stage_filter:
                query = query.filter(Deal.stage == stage_filter)
            query = query.filter(Deal.value >= min_value)
            if max_value is not None:
                query = query.filter(Deal.value <= max_value)
            if query_text:
                like_query = f'%{query_text}%'
                query = query.filter(Deal.title.ilike(like_query))
            total = query.count()
            deals = query.order_by(Deal.created_at.desc()).offset(offset).limit(limit).all()
            window = [_deal_to_dict(deal) for deal in deals]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(window),
            'total': total,
            'limit': limit,
            'offset': offset,
            'deals': window,
        }

    @router.patch('/crm/deals/{deal_id}', responses={404: {'description': DEAL_NOT_FOUND}})
    def update_deal(  # pyright: ignore[reportUnusedFunction]
        deal_id: int,
        payload: DealUpdateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:deals:update', 120, 60)
        with get_db_session() as session:
            item = session.query(Deal).filter_by(id=deal_id, tenant_id=auth.tenant_id).first()
            if item is None:
                raise HTTPException(status_code=404, detail=DEAL_NOT_FOUND)
            data = dict(item.data or {})
            if payload.stage is not None:
                item.stage = payload.stage
                data['probability'] = next(
                    (s['probability'] for s in PIPELINE_STAGES if s['stage'] == payload.stage),
                    int(data.get('probability', 10)),
                )
            if payload.value is not None:
                item.value = payload.value
            if payload.close_date is not None:
                item.close_date = payload.close_date
            if payload.properties:
                current_properties = data.get('properties', {})
                if not isinstance(current_properties, dict):
                    current_properties = {}
                current_properties.update(payload.properties)
                data['properties'] = current_properties
            item.data = data
            session.flush()
            snapshot = _deal_to_dict(item)

        _audit(auth.tenant_id, 'crm_deal_updated', deal_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'deal': snapshot}

    # ── Pipeline summary ─────────────────────────────────────────────────────

    @router.get('/crm/pipeline')
    def get_pipeline(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:pipeline', 180, 60)
        tenant_deals = _list_db_deals(auth.tenant_id)

        stage_buckets: dict[str, list[dict[str, Any]]] = {s['stage']: [] for s in PIPELINE_STAGES}
        for deal in tenant_deals:
            stage = str(deal.get('stage', 'prospect'))
            if stage not in stage_buckets:
                stage_buckets[stage] = []
            stage_buckets[stage].append(deal)

        pipeline: list[dict[str, Any]] = [
            {
                'stage': s['stage'],
                'display': s['display'],
                'probability': s['probability'],
                'count': len(stage_buckets.get(s['stage'], [])),
                'total_value': round(sum(float(d.get('value', 0)) for d in stage_buckets.get(s['stage'], [])), 2),
            }
            for s in PIPELINE_STAGES
        ]
        total_pipeline_value = round(sum(float(d.get('value', 0)) for d in tenant_deals if d.get('stage') not in ('closed_lost',)), 2)
        total_closed_won = round(sum(float(d.get('value', 0)) for d in tenant_deals if d.get('stage') == 'closed_won'), 2)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'pipeline': pipeline,
            'total_pipeline_value': total_pipeline_value,
            'total_closed_won': total_closed_won,
            'total_deals': len(tenant_deals),
        }

    @router.get('/crm/summary')
    def get_summary(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:summary', 240, 60)
        contacts = _list_db_contacts(auth.tenant_id)
        companies = _list_db_companies(auth.tenant_id)
        deals = _list_db_deals(auth.tenant_id)
        with lock:
            activities = [a.copy() for a in activities_memory if a.get('tenant_id') == auth.tenant_id]

        open_deals = [d for d in deals if d.get('stage') not in ('closed_won', 'closed_lost')]
        won_deals = [d for d in deals if d.get('stage') == 'closed_won']
        avg_score = round(
            (sum(int(c.get('lead_score', 0)) for c in contacts) / len(contacts)) if contacts else 0,
            2,
        )
        forecast_revenue = round(
            sum(float(d.get('value', 0)) * (float(d.get('probability', 0)) / 100.0) for d in open_deals),
            2,
        )
        stage_counts: dict[str, int] = {}
        for stage in PIPELINE_STAGES:
            key = stage['stage']
            stage_counts[key] = sum(1 for d in deals if d.get('stage') == key)

        recent_activities = sorted(
            activities,
            key=lambda a: str(a.get('created_at', '')),
            reverse=True,
        )[:10]

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'summary': {
                'contacts': len(contacts),
                'companies': len(companies),
                'deals_total': len(deals),
                'deals_open': len(open_deals),
                'deals_won': len(won_deals),
                'pipeline_value': round(sum(float(d.get('value', 0)) for d in open_deals), 2),
                'closed_won_value': round(sum(float(d.get('value', 0)) for d in won_deals), 2),
                'forecast_revenue': forecast_revenue,
                'avg_lead_score': avg_score,
                'activities': len(activities),
                'stage_counts': stage_counts,
            },
            'pipeline_stages': PIPELINE_STAGES,
            'recent_activities': recent_activities,
        }

    # ── Activities ────────────────────────────────────────────────────────────

    @router.post('/crm/activities')
    def create_activity(  # pyright: ignore[reportUnusedFunction]
        payload: ActivityCreateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:activities:create', 180, 60)
        activity = _create_db_activity(auth.tenant_id, payload)
        _audit(auth.tenant_id, 'crm_activity_created', int(activity['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'activity': activity}

    @router.get('/crm/activities')  # NOSONAR
    def list_activities(
        auth: AuthDep,
        type: Annotated[str | None, Query(max_length=40)] = None,
        contact_id: Annotated[int | None, Query(ge=1)] = None,
        deal_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:activities:list', 240, 60)
        items, total = _list_db_activities(
            auth.tenant_id,
            type_filter=(type or '').strip().lower() or None,
            contact_id=contact_id,
            deal_id=deal_id,
            limit=limit,
            offset=offset,
        )
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'total': total,
            'limit': limit,
            'offset': offset,
            'activities': items,
        }

    @router.get('/crm/export')  # NOSONAR
    def export_crm(
        auth: AuthDep,
        resource: Annotated[str, Query(pattern=r'^(contacts|companies|deals|activities)$')] = 'contacts',
        format: Annotated[str, Query(pattern=r'^(json|csv)$')] = 'json',
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:export', 20, 60)
        contact_rows = _list_db_contacts(auth.tenant_id) if resource == 'contacts' else []
        company_rows = _list_db_companies(auth.tenant_id) if resource == 'companies' else []
        deal_rows = _list_db_deals(auth.tenant_id) if resource == 'deals' else []
        with lock:
            source_map = {
                'contacts': contact_rows,
                'companies': company_rows,
                'deals': deal_rows,
                'activities': [a.copy() for a in activities_memory if a.get('tenant_id') == auth.tenant_id],
            }
        rows = source_map[resource]
        if format == 'json':
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'resource': resource, 'format': format, 'count': len(rows), 'rows': rows}

        if not rows:
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'resource': resource, 'format': format, 'count': 0, 'csv': ''}

        headers = sorted({k for row in rows for k in row if k != 'tenant_id'})
        lines = [','.join(headers)]
        for row in rows:
            values: list[str] = []
            for key in headers:
                raw = row.get(key, '')
                value = str(raw).replace('"', '""')
                values.append(f'"{value}"')
            lines.append(','.join(values))
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'resource': resource,
            'format': format,
            'count': len(rows),
            'csv': '\n'.join(lines),
        }

    @router.post('/crm/webhooks')
    def create_webhook(payload: CRMWebhookCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:webhooks:create', 40, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_webhook: dict[str, Any] | None = None
        created_webhook: dict[str, Any] | None = None
        with lock:
            existing = next(
                (
                    w for w in webhook_subscriptions_memory
                    if w.get('tenant_id') == auth.tenant_id
                    and str(w.get('event', '')).strip().lower() == payload.event.strip().lower()
                    and str(w.get('target_url', '')).strip().lower() == payload.target_url.strip().lower()
                ),
                None,
            )
            if existing is not None:
                duplicate_webhook = existing.copy()
            else:
                record: dict[str, Any] = {
                    'id': len(webhook_subscriptions_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'event': payload.event,
                    'target_url': payload.target_url,
                    'secret_masked': (payload.secret[:2] + '***') if payload.secret else '',
                    'status': 'active',
                    'created_at': now,
                    'updated_at': now,
                    'last_delivery_status': None,
                    'last_delivery_at': None,
                }
                webhook_subscriptions_memory.append(record)
                created_webhook = record

        if duplicate_webhook is not None:
            _audit(auth.tenant_id, 'crm_webhook_reused', int(duplicate_webhook.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'webhook': duplicate_webhook, 'duplicate': True, 'created': False}

        if created_webhook is None:
            raise HTTPException(status_code=500, detail='Failed to create webhook.')

        _audit(auth.tenant_id, 'crm_webhook_created', int(created_webhook['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'webhook': created_webhook, 'duplicate': False, 'created': True}

    @router.get('/crm/webhooks')
    def list_webhooks(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:webhooks:list', 120, 60)
        with lock:
            items = [w.copy() for w in webhook_subscriptions_memory if w.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda row: str(row.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'webhooks': items}

    @router.post('/crm/webhooks/{webhook_id}/test', responses={404: {'description': 'Webhook not found.'}})
    def test_webhook(webhook_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:webhooks:test', 60, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            row = next(
                (w for w in webhook_subscriptions_memory if w.get('tenant_id') == auth.tenant_id and int(w.get('id', 0)) == webhook_id),
                None,
            )
            if row is None:
                raise HTTPException(status_code=404, detail='Webhook not found.')
            row['last_delivery_status'] = 'delivered'
            row['last_delivery_at'] = now
            row['updated_at'] = now
            snapshot = row.copy()

        _audit(auth.tenant_id, 'crm_webhook_tested', webhook_id)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'webhook': snapshot,
            'delivery': {
                'status': 'delivered',
                'tested_at': now,
                'sample_payload': {'event': snapshot.get('event'), 'tenant_id': auth.tenant_id},
            },
        }

    # ── Leads (Sales Automation) ──────────────────────────────────────────────

    @router.post('/crm/leads')
    def create_lead(payload: LeadCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:leads:create', 120, 60)
        duplicate = _find_duplicate_db_lead(auth.tenant_id, payload)
        if duplicate is not None:
            _audit(auth.tenant_id, 'crm_lead_reused', int(duplicate.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'lead': duplicate, 'duplicate': True, 'created': False}

        lead = _create_db_lead(auth.tenant_id, payload)
        _audit(auth.tenant_id, 'crm_lead_created', int(lead['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'lead': lead, 'duplicate': False, 'created': True}

    @router.get('/crm/leads')
    def list_leads(
        auth: AuthDep,
        q: Annotated[str | None, Query(max_length=160)] = None,
        status: Annotated[str | None, Query(max_length=40)] = None,
        assigned_to: Annotated[str | None, Query(max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:leads:list', 240, 60)
        items, total = _list_db_leads(
            auth.tenant_id,
            status=(status or '').strip() or None,
            assigned_to=(assigned_to or '').strip() or None,
            q=(q or '').strip() or None,
            limit=limit,
            offset=offset,
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'total': total, 'limit': limit, 'offset': offset, 'leads': items}

    @router.get('/crm/leads/{lead_id}', responses={404: {'description': LEAD_NOT_FOUND}})
    def get_lead(lead_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:leads:get', 300, 60)
        obj = _get_db_lead(lead_id, auth.tenant_id)
        if obj is None:
            raise HTTPException(status_code=404, detail=LEAD_NOT_FOUND)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'lead': _lead_to_dict(obj)}

    @router.patch('/crm/leads/{lead_id}', responses={404: {'description': LEAD_NOT_FOUND}})
    def update_lead(lead_id: int, payload: LeadUpdateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:leads:update', 120, 60)
        with get_db_session() as session:
            obj = session.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == auth.tenant_id).first()
            if obj is None:
                raise HTTPException(status_code=404, detail=LEAD_NOT_FOUND)
            if payload.status is not None:
                obj.status = payload.status
            if payload.score is not None:
                obj.score = payload.score
            if payload.assigned_to is not None:
                obj.assigned_to = payload.assigned_to
            if payload.estimated_value is not None:
                obj.estimated_value = payload.estimated_value
            if payload.notes is not None:
                d = dict(obj.data or {})
                d['notes'] = payload.notes
                obj.data = d
            session.commit()
            session.refresh(obj)
            snapshot = _lead_to_dict(obj)
        _audit(auth.tenant_id, 'crm_lead_updated', lead_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'lead': snapshot}

    @router.post('/crm/leads/{lead_id}/convert', responses={404: {'description': LEAD_NOT_FOUND}})
    def convert_lead(lead_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Convert a lead into an opportunity/deal."""
        enforce_rate_limit(f'{auth.tenant_id}:crm:leads:convert', 60, 60)
        with get_db_session() as session:
            lead_obj = session.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == auth.tenant_id).first()
            if lead_obj is None:
                raise HTTPException(status_code=404, detail=LEAD_NOT_FOUND)
            deal_obj = Deal(
                tenant_id=auth.tenant_id,
                title=lead_obj.title,
                value=lead_obj.estimated_value,
                currency='USD',
                stage='qualified',
                contact_id=lead_obj.contact_id,
                company_id=lead_obj.company_id,
                data={'probability': 25, 'properties': {'converted_from_lead': lead_id}, 'source': 'lead_conversion'},
            )
            session.add(deal_obj)
            lead_obj.status = 'converted'
            d = dict(lead_obj.data or {})
            session.flush()
            d['converted_deal_id'] = deal_obj.id
            lead_obj.data = d
            session.commit()
            session.refresh(lead_obj)
            session.refresh(deal_obj)
            lead_snap = _lead_to_dict(lead_obj)
            deal_snap = _deal_to_dict(deal_obj)
        _audit(auth.tenant_id, 'crm_lead_converted', lead_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'lead': lead_snap, 'deal': deal_snap}

    # ── Tasks (Project & Task Management) ────────────────────────────────────

    @router.post('/crm/tasks')
    def create_task(payload: TaskCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tasks:create', 120, 60)
        duplicate = _find_duplicate_db_task(auth.tenant_id, payload)
        if duplicate is not None:
            _audit(auth.tenant_id, 'crm_task_reused', int(duplicate.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'task': duplicate, 'duplicate': True, 'created': False}

        task = _create_db_task(auth.tenant_id, payload)
        _audit(auth.tenant_id, 'crm_task_created', int(task['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'task': task, 'duplicate': False, 'created': True}

    @router.get('/crm/tasks')
    def list_tasks(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        priority: Annotated[str | None, Query(max_length=20)] = None,
        assigned_to: Annotated[str | None, Query(max_length=120)] = None,
        contact_id: Annotated[int | None, Query(ge=1)] = None,
        deal_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tasks:list', 240, 60)
        items, total = _list_db_tasks(
            auth.tenant_id,
            status=(status or '').strip() or None,
            priority=(priority or '').strip() or None,
            assigned_to=(assigned_to or '').strip() or None,
            contact_id=contact_id,
            deal_id=deal_id,
            limit=limit,
            offset=offset,
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'total': total, 'limit': limit, 'offset': offset, 'tasks': items}

    @router.patch('/crm/tasks/{task_id}', responses={404: {'description': TASK_NOT_FOUND}})
    def update_task(task_id: int, payload: TaskUpdateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tasks:update', 120, 60)
        with get_db_session() as session:
            obj = session.query(Task).filter(Task.id == task_id, Task.tenant_id == auth.tenant_id).first()
            if obj is None:
                raise HTTPException(status_code=404, detail=TASK_NOT_FOUND)
            if payload.status is not None:
                obj.status = payload.status
            if payload.priority is not None:
                obj.priority = payload.priority
            if payload.due_date is not None:
                obj.due_date = payload.due_date
            if payload.assigned_to is not None:
                obj.assigned_to = payload.assigned_to
            session.commit()
            session.refresh(obj)
            snapshot = _task_to_dict(obj)
        _audit(auth.tenant_id, 'crm_task_updated', task_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'task': snapshot}

    # ── Kanban board view for tasks ───────────────────────────────────────────

    @router.get('/crm/tasks/kanban')
    def tasks_kanban(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tasks:kanban', 180, 60)
        items, _ = _list_db_tasks(auth.tenant_id, limit=500)
        with lock:
            mem_items = [dict(t) for t in tasks_memory if str(t.get('tenant_id', '')) == str(auth.tenant_id)]
        existing_ids = {int(item.get('id', 0)) for item in items if int(item.get('id', 0)) > 0}
        for task in mem_items:
            task_id = int(task.get('id', 0))
            if task_id <= 0 or task_id not in existing_ids:
                items.append(task)
        columns: dict[str, list[dict[str, Any]]] = {'open': [], 'in_progress': [], 'completed': [], 'cancelled': []}
        for task in items:
            col = str(task.get('status', 'open')).lower().replace(' ', '_')
            if col not in columns:
                columns[col] = []
            columns[col].append(task)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'kanban': columns}

    # ── Support Ticketing ─────────────────────────────────────────────────────

    @router.post('/crm/tickets')
    def create_ticket(payload: TicketCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tickets:create', 120, 60)
        ticket_number = f"TKT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        sla = next((r for r in sla_rules_memory if r.get('tenant_id') == auth.tenant_id and r.get('priority') == payload.priority), None)
        first_response_deadline = None
        resolution_deadline = None
        if sla:
            fh = int(sla.get('first_response_hours', 4))
            rh = int(sla.get('resolution_hours', 24))
            first_response_deadline = (datetime.now(UTC) + timedelta(hours=fh)).isoformat()
            resolution_deadline = (datetime.now(UTC) + timedelta(hours=rh)).isoformat()
        ticket = _create_db_ticket(auth.tenant_id, payload, ticket_number, first_response_deadline, resolution_deadline)
        _audit(auth.tenant_id, 'crm_ticket_created', int(ticket['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'ticket': ticket}

    @router.get('/crm/tickets')
    def list_tickets(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        priority: Annotated[str | None, Query(max_length=20)] = None,
        channel: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tickets:list', 240, 60)
        items, total = _list_db_tickets(
            auth.tenant_id,
            status=(status or '').strip() or None,
            priority=(priority or '').strip() or None,
            channel=(channel or '').strip() or None,
            limit=limit,
            offset=offset,
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'total': total, 'limit': limit, 'offset': offset, 'tickets': items}

    @router.get('/crm/tickets/{ticket_id}', responses={404: {'description': TICKET_NOT_FOUND}})
    def get_ticket(ticket_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tickets:get', 300, 60)
        obj = _get_db_ticket(ticket_id, auth.tenant_id)
        if obj is None:
            raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'ticket': _ticket_to_dict(obj)}

    @router.patch('/crm/tickets/{ticket_id}', responses={404: {'description': TICKET_NOT_FOUND}})
    def update_ticket(ticket_id: int, payload: TicketUpdateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tickets:update', 120, 60)
        with get_db_session() as session:
            obj = session.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == auth.tenant_id).first()
            if obj is None:
                raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
            if payload.status is not None:
                obj.status = payload.status
            if payload.priority is not None:
                obj.priority = payload.priority
            if payload.assigned_to is not None:
                obj.assigned_to = payload.assigned_to
            if payload.resolution is not None:
                obj.resolution = payload.resolution
            session.commit()
            session.refresh(obj)
            snapshot = _ticket_to_dict(obj)
        _audit(auth.tenant_id, 'crm_ticket_updated', ticket_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'ticket': snapshot}

    @router.post('/crm/tickets/{ticket_id}/escalate', responses={404: {'description': TICKET_NOT_FOUND}})
    def escalate_ticket(ticket_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:tickets:escalate', 60, 60)
        with get_db_session() as session:
            obj = session.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == auth.tenant_id).first()
            if obj is None:
                raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
            obj.escalated = True
            obj.priority = 'critical'
            session.commit()
            session.refresh(obj)
            snapshot = _ticket_to_dict(obj)
        _audit(auth.tenant_id, 'crm_ticket_escalated', ticket_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'ticket': snapshot}

    # ── SLA Rules ─────────────────────────────────────────────────────────────

    @router.post('/crm/sla-rules')
    def create_sla_rule(payload: SLARuleCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:sla:create', 40, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_sla: dict[str, Any] | None = None
        created_sla: dict[str, Any] | None = None
        with lock:
            existing = next(
                (
                    r for r in sla_rules_memory
                    if r.get('tenant_id') == auth.tenant_id
                    and str(r.get('name', '')).strip().lower() == payload.name.strip().lower()
                    and str(r.get('applies_to', '')).strip().lower() == payload.applies_to.strip().lower()
                    and str(r.get('priority', '')).strip().lower() == payload.priority.strip().lower()
                ),
                None,
            )
            if existing is not None:
                duplicate_sla = existing.copy()
            else:
                rule: dict[str, Any] = {
                    'id': len(sla_rules_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'name': payload.name,
                    'applies_to': payload.applies_to,
                    'priority': payload.priority,
                    'first_response_hours': payload.first_response_hours,
                    'resolution_hours': payload.resolution_hours,
                    'created_at': now,
                }
                sla_rules_memory.append(rule)
                created_sla = rule
        if duplicate_sla is not None:
            _audit(auth.tenant_id, 'crm_sla_rule_reused', int(duplicate_sla.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sla_rule': duplicate_sla, 'duplicate': True, 'created': False}

        if created_sla is None:
            raise HTTPException(status_code=500, detail='Failed to create SLA rule.')

        _audit(auth.tenant_id, 'crm_sla_rule_created', int(created_sla['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sla_rule': created_sla, 'duplicate': False, 'created': True}

    @router.get('/crm/sla-rules')
    def list_sla_rules(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:sla:list', 120, 60)
        with lock:
            items = [r.copy() for r in sla_rules_memory if r.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'sla_rules': items}

    # ── Marketing Campaigns ───────────────────────────────────────────────────

    @router.post('/crm/campaigns')
    def create_campaign(payload: CampaignCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:campaigns:create', 60, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_campaign: dict[str, Any] | None = None
        created_campaign: dict[str, Any] | None = None
        with lock:
            existing = next(
                (
                    c for c in campaigns_memory
                    if c.get('tenant_id') == auth.tenant_id
                    and str(c.get('name', '')).strip().lower() == payload.name.strip().lower()
                    and str(c.get('type', '')).strip().lower() == payload.type.strip().lower()
                    and str(c.get('subject', '')).strip().lower() == payload.subject.strip().lower()
                ),
                None,
            )
            if existing is not None:
                duplicate_campaign = existing.copy()
            else:
                campaign: dict[str, Any] = {
                    'id': len(campaigns_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'name': payload.name,
                    'type': payload.type,
                    'subject': payload.subject,
                    'body': payload.body,
                    'segment_id': payload.segment_id,
                    'scheduled_at': payload.scheduled_at,
                    'ab_test': payload.ab_test,
                    'variant_b_subject': payload.variant_b_subject if payload.ab_test else '',
                    'status': 'draft',
                    'sent_count': 0,
                    'open_count': 0,
                    'click_count': 0,
                    'created_at': now,
                    'updated_at': now,
                }
                campaigns_memory.append(campaign)
                created_campaign = campaign
        if duplicate_campaign is not None:
            _audit(auth.tenant_id, 'crm_campaign_reused', int(duplicate_campaign.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'campaign': duplicate_campaign, 'duplicate': True, 'created': False}

        if created_campaign is None:
            raise HTTPException(status_code=500, detail='Failed to create campaign.')

        _audit(auth.tenant_id, 'crm_campaign_created', int(created_campaign['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'campaign': created_campaign, 'duplicate': False, 'created': True}

    @router.get('/crm/campaigns')
    def list_campaigns(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        type: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:campaigns:list', 180, 60)
        with lock:
            items = [c.copy() for c in campaigns_memory if c.get('tenant_id') == auth.tenant_id]
        if (status or '').strip():
            items = [c for c in items if str(c.get('status', '')) == status.strip()]  # type: ignore[union-attr]
        if (type or '').strip():
            items = [c for c in items if str(c.get('type', '')) == type.strip()]  # type: ignore[union-attr]
        items.sort(key=lambda c: str(c.get('created_at', '')), reverse=True)
        total = len(items)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items[offset:offset+limit]), 'total': total, 'campaigns': items[offset:offset+limit]}

    @router.get('/crm/campaigns/{campaign_id}', responses={404: {'description': CAMPAIGN_NOT_FOUND}})
    def get_campaign(campaign_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:campaigns:get', 300, 60)
        with lock:
            item = next((c.copy() for c in campaigns_memory if c.get('id') == campaign_id and c.get('tenant_id') == auth.tenant_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail=CAMPAIGN_NOT_FOUND)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'campaign': item}

    @router.post('/crm/campaigns/{campaign_id}/send', responses={404: {'description': CAMPAIGN_NOT_FOUND}})
    def send_campaign(campaign_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:campaigns:send', 20, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            item = next((c for c in campaigns_memory if c.get('id') == campaign_id and c.get('tenant_id') == auth.tenant_id), None)
            if item is None:
                raise HTTPException(status_code=404, detail=CAMPAIGN_NOT_FOUND)
            # Simulate send — count segment members if segment_id set
            segment = next((s for s in segments_memory if s.get('id') == item.get('segment_id') and s.get('tenant_id') == auth.tenant_id), None)
            member_count = int(segment.get('member_count', 0)) if segment else 0
            item['status'] = 'sent'
            item['sent_at'] = now
            item['sent_count'] = member_count
            item['updated_at'] = now
            snapshot = item.copy()
        _audit(auth.tenant_id, 'crm_campaign_sent', campaign_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'campaign': snapshot}

    # ── Segments ──────────────────────────────────────────────────────────────

    @router.post('/crm/segments')
    def create_segment(payload: SegmentCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:segments:create', 60, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_segment: dict[str, Any] | None = None
        created_segment: dict[str, Any] | None = None
        with lock:
            existing = next(
                (
                    s for s in segments_memory
                    if s.get('tenant_id') == auth.tenant_id
                    and str(s.get('name', '')).strip().lower() == payload.name.strip().lower()
                    and dict(s.get('filters', {})) == payload.filters
                ),
                None,
            )
            if existing is not None:
                duplicate_segment = existing.copy()
            else:
                # Compute member count based on filters
                members = _apply_segment_filters(auth.tenant_id, payload.filters, contacts_memory)
                segment: dict[str, Any] = {
                    'id': len(segments_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'name': payload.name,
                    'description': payload.description,
                    'filters': payload.filters,
                    'member_count': len(members),
                    'created_at': now,
                    'updated_at': now,
                }
                segments_memory.append(segment)
                created_segment = segment
        if duplicate_segment is not None:
            _audit(auth.tenant_id, 'crm_segment_reused', int(duplicate_segment.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'segment': duplicate_segment, 'duplicate': True, 'created': False}

        if created_segment is None:
            raise HTTPException(status_code=500, detail='Failed to create segment.')

        _audit(auth.tenant_id, 'crm_segment_created', int(created_segment['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'segment': created_segment, 'duplicate': False, 'created': True}

    @router.get('/crm/segments')
    def list_segments(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:segments:list', 180, 60)
        with lock:
            items = [s.copy() for s in segments_memory if s.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'segments': items}

    @router.get('/crm/segments/{segment_id}/members', responses={404: {'description': SEGMENT_NOT_FOUND}})
    def get_segment_members(
        segment_id: int,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:segments:members', 120, 60)
        with lock:
            segment = next((s for s in segments_memory if s.get('id') == segment_id and s.get('tenant_id') == auth.tenant_id), None)
        if segment is None:
            raise HTTPException(status_code=404, detail=SEGMENT_NOT_FOUND)
        members = _apply_segment_filters(auth.tenant_id, dict(segment.get('filters', {})), contacts_memory)
        total = len(members)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'segment_id': segment_id, 'count': len(members[offset:offset+limit]), 'total': total, 'members': members[offset:offset+limit]}

    # ── Notes ─────────────────────────────────────────────────────────────────

    @router.post('/crm/notes')
    def create_note(payload: NoteCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:notes:create', 120, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_note: dict[str, Any] | None = None
        created_note: dict[str, Any] | None = None
        with lock:
            existing = next(
                (
                    n for n in notes_memory
                    if n.get('tenant_id') == auth.tenant_id
                    and str(n.get('body', '')).strip() == payload.body.strip()
                    and n.get('contact_id') == payload.contact_id
                    and n.get('deal_id') == payload.deal_id
                    and n.get('company_id') == payload.company_id
                    and bool(n.get('pinned', False)) == payload.pinned
                ),
                None,
            )
            if existing is not None:
                duplicate_note = existing.copy()
            else:
                note: dict[str, Any] = {
                    'id': len(notes_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'body': payload.body,
                    'contact_id': payload.contact_id,
                    'deal_id': payload.deal_id,
                    'company_id': payload.company_id,
                    'pinned': payload.pinned,
                    'created_at': now,
                }
                notes_memory.append(note)
                created_note = note
        if duplicate_note is not None:
            _audit(auth.tenant_id, 'crm_note_reused', int(duplicate_note.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'note': duplicate_note, 'duplicate': True, 'created': False}

        if created_note is None:
            raise HTTPException(status_code=500, detail='Failed to create note.')

        _audit(auth.tenant_id, 'crm_note_created', int(created_note['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'note': created_note, 'duplicate': False, 'created': True}

    @router.get('/crm/notes')
    def list_notes(
        auth: AuthDep,
        contact_id: Annotated[int | None, Query(ge=1)] = None,
        deal_id: Annotated[int | None, Query(ge=1)] = None,
        company_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:notes:list', 240, 60)
        with lock:
            items = [n.copy() for n in notes_memory if n.get('tenant_id') == auth.tenant_id]
        if contact_id is not None:
            items = [n for n in items if n.get('contact_id') == contact_id]
        if deal_id is not None:
            items = [n for n in items if n.get('deal_id') == deal_id]
        if company_id is not None:
            items = [n for n in items if n.get('company_id') == company_id]
        items.sort(key=lambda n: (not bool(n.get('pinned')), str(n.get('created_at', ''))), reverse=False)
        total = len(items)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items[offset:offset+limit]), 'total': total, 'notes': items[offset:offset+limit]}

    # ── Quotes ────────────────────────────────────────────────────────────────

    @router.post('/crm/quotes')
    def create_quote(payload: QuoteCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:quotes:create', 60, 60)
        now = datetime.now(UTC).isoformat()
        subtotal = sum(
            item.quantity * item.unit_price * (1 - item.discount_pct / 100.0)
            for item in payload.line_items
        )
        duplicate_quote: dict[str, Any] | None = None
        created_quote: dict[str, Any] | None = None
        line_items = [li.model_dump() for li in payload.line_items]
        with lock:
            existing = next(
                (
                    q for q in quotes_memory
                    if q.get('tenant_id') == auth.tenant_id
                    and str(q.get('title', '')).strip().lower() == payload.title.strip().lower()
                    and q.get('contact_id') == payload.contact_id
                    and q.get('deal_id') == payload.deal_id
                    and str(q.get('currency', '')).strip().lower() == payload.currency.strip().lower()
                    and list(q.get('line_items', [])) == line_items
                    and str(q.get('status', '')).strip().lower() == 'draft'
                ),
                None,
            )
            if existing is not None:
                duplicate_quote = existing.copy()
            else:
                quote_number = f"QUO-{len(quotes_memory)+1:05d}"
                quote: dict[str, Any] = {
                    'id': len(quotes_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'quote_number': quote_number,
                    'title': payload.title,
                    'contact_id': payload.contact_id,
                    'deal_id': payload.deal_id,
                    'line_items': line_items,
                    'subtotal': round(subtotal, 2),
                    'currency': payload.currency,
                    'valid_until': payload.valid_until,
                    'notes': payload.notes,
                    'status': 'draft',
                    'created_at': now,
                    'updated_at': now,
                }
                quotes_memory.append(quote)
                created_quote = quote
        if duplicate_quote is not None:
            _audit(auth.tenant_id, 'crm_quote_reused', int(duplicate_quote.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'quote': duplicate_quote, 'duplicate': True, 'created': False}

        if created_quote is None:
            raise HTTPException(status_code=500, detail='Failed to create quote.')

        _audit(auth.tenant_id, 'crm_quote_created', int(created_quote['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'quote': created_quote, 'duplicate': False, 'created': True}

    @router.get('/crm/quotes')
    def list_quotes(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:quotes:list', 180, 60)
        with lock:
            items = [q.copy() for q in quotes_memory if q.get('tenant_id') == auth.tenant_id]
        if (status or '').strip():
            items = [q for q in items if str(q.get('status', '')) == status.strip()]  # type: ignore[union-attr]
        items.sort(key=lambda q: str(q.get('created_at', '')), reverse=True)
        total = len(items)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items[offset:offset+limit]), 'total': total, 'quotes': items[offset:offset+limit]}

    @router.post('/crm/quotes/{quote_id}/accept', responses={404: {'description': QUOTE_NOT_FOUND}})
    def accept_quote(quote_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:quotes:accept', 60, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            item = next((q for q in quotes_memory if q.get('id') == quote_id and q.get('tenant_id') == auth.tenant_id), None)
            if item is None:
                raise HTTPException(status_code=404, detail=QUOTE_NOT_FOUND)
            item['status'] = 'accepted'
            item['accepted_at'] = now
            item['updated_at'] = now
            # Auto-create invoice
            invoice: dict[str, Any] = {
                'id': len(crm_invoices_memory) + 1,
                'tenant_id': auth.tenant_id,
                'invoice_number': f"INV-{len(crm_invoices_memory)+1:05d}",
                'title': str(item.get('title', 'Invoice')),
                'contact_id': item.get('contact_id'),
                'deal_id': item.get('deal_id'),
                'quote_id': quote_id,
                'amount': float(item.get('subtotal', 0.0)),
                'currency': str(item.get('currency', 'USD')),
                'status': 'pending',
                'due_date': None,
                'created_at': now,
                'updated_at': now,
            }
            crm_invoices_memory.append(invoice)
            snapshot = item.copy()
        _audit(auth.tenant_id, 'crm_quote_accepted', quote_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'quote': snapshot, 'invoice': invoice}

    # ── Invoices ──────────────────────────────────────────────────────────────

    @router.post('/crm/invoices')
    def create_invoice(payload: CRMInvoiceCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:invoices:create', 60, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_invoice: dict[str, Any] | None = None
        created_invoice: dict[str, Any] | None = None
        with lock:
            existing = next(
                (
                    i for i in crm_invoices_memory
                    if i.get('tenant_id') == auth.tenant_id
                    and str(i.get('title', '')).strip().lower() == payload.title.strip().lower()
                    and i.get('contact_id') == payload.contact_id
                    and i.get('deal_id') == payload.deal_id
                    and i.get('quote_id') == payload.quote_id
                    and float(i.get('amount', 0.0)) == payload.amount
                    and str(i.get('currency', '')).strip().lower() == payload.currency.strip().lower()
                    and str(i.get('status', '')).strip().lower() == 'pending'
                ),
                None,
            )
            if existing is not None:
                duplicate_invoice = existing.copy()
            else:
                invoice_number = f"INV-{len(crm_invoices_memory)+1:05d}"
                inv: dict[str, Any] = {
                    'id': len(crm_invoices_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'invoice_number': invoice_number,
                    'title': payload.title,
                    'contact_id': payload.contact_id,
                    'deal_id': payload.deal_id,
                    'quote_id': payload.quote_id,
                    'amount': payload.amount,
                    'currency': payload.currency,
                    'due_date': payload.due_date,
                    'notes': payload.notes,
                    'status': 'pending',
                    'created_at': now,
                    'updated_at': now,
                }
                crm_invoices_memory.append(inv)
                created_invoice = inv
        if duplicate_invoice is not None:
            _audit(auth.tenant_id, 'crm_invoice_reused', int(duplicate_invoice.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'invoice': duplicate_invoice, 'duplicate': True, 'created': False}

        if created_invoice is None:
            raise HTTPException(status_code=500, detail='Failed to create invoice.')

        _audit(auth.tenant_id, 'crm_invoice_created', int(created_invoice['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'invoice': created_invoice, 'duplicate': False, 'created': True}

    @router.get('/crm/invoices')
    def list_invoices(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:invoices:list', 180, 60)
        with lock:
            items = [i.copy() for i in crm_invoices_memory if i.get('tenant_id') == auth.tenant_id]
        if (status or '').strip():
            items = [i for i in items if str(i.get('status', '')) == status.strip()]  # type: ignore[union-attr]
        items.sort(key=lambda i: str(i.get('created_at', '')), reverse=True)
        total = len(items)
        total_outstanding = round(sum(float(i.get('amount', 0)) for i in items if i.get('status') == 'pending'), 2)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items[offset:offset+limit]), 'total': total, 'total_outstanding': total_outstanding, 'invoices': items[offset:offset+limit]}

    @router.patch('/crm/invoices/{invoice_id}', responses={404: {'description': INVOICE_NOT_FOUND}})
    def update_invoice(invoice_id: int, payload: CRMInvoiceUpdateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:invoices:update', 60, 60)
        with lock:
            item = next((i for i in crm_invoices_memory if i.get('id') == invoice_id and i.get('tenant_id') == auth.tenant_id), None)
            if item is None:
                raise HTTPException(status_code=404, detail=INVOICE_NOT_FOUND)
            if payload.status is not None:
                item['status'] = payload.status
            if payload.paid_at is not None:
                item['paid_at'] = payload.paid_at
            item['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = item.copy()
        _audit(auth.tenant_id, 'crm_invoice_updated', invoice_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'invoice': snapshot}

    # ── Email Sequences ───────────────────────────────────────────────────────

    @router.post('/crm/email-sequences')
    def create_sequence(payload: EmailSequenceCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:sequences:create', 40, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_sequence: dict[str, Any] | None = None
        created_sequence: dict[str, Any] | None = None
        steps = [s.model_dump() for s in payload.steps]
        with lock:
            existing = next(
                (
                    s for s in email_sequences_memory
                    if s.get('tenant_id') == auth.tenant_id
                    and str(s.get('name', '')).strip().lower() == payload.name.strip().lower()
                    and list(s.get('steps', [])) == steps
                ),
                None,
            )
            if existing is not None:
                duplicate_sequence = existing.copy()
            else:
                seq: dict[str, Any] = {
                    'id': len(email_sequences_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'name': payload.name,
                    'description': payload.description,
                    'steps': steps,
                    'step_count': len(payload.steps),
                    'enrollments': 0,
                    'status': 'active',
                    'created_at': now,
                    'updated_at': now,
                }
                email_sequences_memory.append(seq)
                created_sequence = seq
        if duplicate_sequence is not None:
            _audit(auth.tenant_id, 'crm_sequence_reused', int(duplicate_sequence.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sequence': duplicate_sequence, 'duplicate': True, 'created': False}

        if created_sequence is None:
            raise HTTPException(status_code=500, detail='Failed to create email sequence.')

        _audit(auth.tenant_id, 'crm_sequence_created', int(created_sequence['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sequence': created_sequence, 'duplicate': False, 'created': True}

    @router.get('/crm/email-sequences')
    def list_sequences(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:sequences:list', 180, 60)
        with lock:
            items = [s.copy() for s in email_sequences_memory if s.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda s: str(s.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'sequences': items}

    @router.post('/crm/email-sequences/{seq_id}/enroll', responses={404: {'description': SEQUENCE_NOT_FOUND}})
    def enroll_in_sequence(seq_id: int, auth: AuthDep, contact_id: int) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:sequences:enroll', 60, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            seq = next((s for s in email_sequences_memory if s.get('id') == seq_id and s.get('tenant_id') == auth.tenant_id), None)
            if seq is None:
                raise HTTPException(status_code=404, detail=SEQUENCE_NOT_FOUND)
            seq['enrollments'] = int(seq.get('enrollments', 0)) + 1
            seq['updated_at'] = now
        _audit(auth.tenant_id, 'crm_sequence_enrolled', seq_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sequence_id': seq_id, 'contact_id': contact_id, 'enrolled_at': now}

    # ── Workflow Rules (Sales / Marketing Automation) ─────────────────────────

    @router.post('/crm/workflow-rules')
    def create_workflow_rule(payload: WorkflowRuleCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:workflows:create', 40, 60)
        try:
            workflow_rule, duplicate = _create_db_workflow_rule(auth.tenant_id, payload)
        except Exception:
            now = datetime.now(UTC).isoformat()
            duplicate_rule: dict[str, Any] | None = None
            created_rule: dict[str, Any] | None = None
            with lock:
                existing = next(
                    (
                        r for r in workflow_rules_memory
                        if r.get('tenant_id') == auth.tenant_id
                        and str(r.get('name', '')).strip().lower() == payload.name.strip().lower()
                        and str(r.get('trigger', '')).strip().lower() == payload.trigger.strip().lower()
                        and str(r.get('action', '')).strip().lower() == payload.action.strip().lower()
                    ),
                    None,
                )
                if existing is not None:
                    duplicate_rule = existing.copy()
                else:
                    rule: dict[str, Any] = {
                        'id': len(workflow_rules_memory) + 1,
                        'tenant_id': auth.tenant_id,
                        'name': payload.name,
                        'trigger': payload.trigger,
                        'conditions': payload.conditions,
                        'action': payload.action,
                        'action_params': payload.action_params,
                        'enabled': payload.enabled,
                        'run_count': 0,
                        'last_triggered_at': None,
                        'created_at': now,
                        'updated_at': now,
                    }
                    workflow_rules_memory.append(rule)
                    created_rule = rule

            if duplicate_rule is not None:
                _audit(auth.tenant_id, 'crm_workflow_rule_reused', int(duplicate_rule.get('id', 0)))
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'workflow_rule': duplicate_rule,
                    'duplicate': True,
                    'created': False,
                }

            if created_rule is None:
                raise HTTPException(status_code=500, detail='Failed to create workflow rule.')

            _audit(auth.tenant_id, 'crm_workflow_rule_created', int(created_rule['id']))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'workflow_rule': created_rule, 'duplicate': False, 'created': True}

        if duplicate:
            _audit(auth.tenant_id, 'crm_workflow_rule_reused', int(workflow_rule.get('id', 0)))
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'workflow_rule': workflow_rule,
                'duplicate': True,
                'created': False,
            }

        _audit(auth.tenant_id, 'crm_workflow_rule_created', int(workflow_rule['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'workflow_rule': workflow_rule, 'duplicate': False, 'created': True}

    @router.get('/crm/workflow-rules')
    def list_workflow_rules(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:workflows:list', 180, 60)
        try:
            items = _list_db_workflow_rules(auth.tenant_id)
        except Exception:
            with lock:
                items = [r.copy() for r in workflow_rules_memory if r.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'workflow_rules': items}

    @router.post('/crm/workflow-rules/{rule_id}/trigger', responses={404: {'description': WORKFLOW_NOT_FOUND}})
    def trigger_workflow_rule(rule_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:workflows:trigger', 60, 60)
        now = datetime.now(UTC).isoformat()
        try:
            snapshot = _trigger_db_workflow_rule(rule_id, auth.tenant_id, now)
            if snapshot is None:
                raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
        except HTTPException:
            raise
        except Exception:
            with lock:
                rule = next((r for r in workflow_rules_memory if r.get('id') == rule_id and r.get('tenant_id') == auth.tenant_id), None)
                if rule is None:
                    raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
                rule['run_count'] = int(rule.get('run_count', 0)) + 1
                rule['last_triggered_at'] = now
                rule['updated_at'] = now
                snapshot = rule.copy()
        _audit(auth.tenant_id, 'crm_workflow_triggered', rule_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'workflow_rule': snapshot, 'triggered_at': now}

    # ── Project Management ───────────────────────────────────────────────────

    @router.post('/crm/projects')
    def create_project(payload: ProjectCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:projects:create', 80, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_project: dict[str, Any] | None = None
        created_project: dict[str, Any] | None = None
        with lock:
            existing = next(
                (
                    p for p in projects_memory
                    if p.get('tenant_id') == auth.tenant_id
                    and str(p.get('name', '')).strip().lower() == payload.name.strip().lower()
                    and str(p.get('owner', '')).strip().lower() == payload.owner.strip().lower()
                ),
                None,
            )
            if existing is not None:
                duplicate_project = existing.copy()
            else:
                project: dict[str, Any] = {
                    'id': len(projects_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'name': payload.name,
                    'description': payload.description,
                    'owner': payload.owner,
                    'status': payload.status,
                    'due_date': payload.due_date,
                    'created_at': now,
                    'updated_at': now,
                }
                projects_memory.append(project)
                created_project = project
        if duplicate_project is not None:
            _audit(auth.tenant_id, 'crm_project_reused', int(duplicate_project.get('id', 0)))
            return {'status': 'ok', 'tenant_id': auth.tenant_id, 'project': duplicate_project, 'duplicate': True, 'created': False}

        if created_project is None:
            raise HTTPException(status_code=500, detail='Failed to create project.')

        _audit(auth.tenant_id, 'crm_project_created', int(created_project['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'project': created_project, 'duplicate': False, 'created': True}

    @router.get('/crm/projects')
    def list_projects(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        owner: Annotated[str | None, Query(max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:projects:list', 240, 60)
        with lock:
            items = [p.copy() for p in projects_memory if p.get('tenant_id') == auth.tenant_id]
        if (status or '').strip():
            items = [p for p in items if str(p.get('status', '')).lower() == str(status).strip().lower()]
        if (owner or '').strip():
            items = [p for p in items if str(p.get('owner', '')).lower() == str(owner).strip().lower()]
        items.sort(key=lambda p: str(p.get('created_at', '')), reverse=True)
        total = len(items)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items[offset:offset+limit]), 'total': total, 'projects': items[offset:offset+limit]}

    @router.patch('/crm/projects/{project_id}', responses={404: {'description': PROJECT_NOT_FOUND}})
    def update_project(project_id: int, payload: ProjectUpdateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:projects:update', 120, 60)
        with lock:
            item = next((p for p in projects_memory if p.get('tenant_id') == auth.tenant_id and int(p.get('id', 0)) == project_id), None)
            if item is None:
                raise HTTPException(status_code=404, detail=PROJECT_NOT_FOUND)
            if payload.name is not None:
                item['name'] = payload.name
            if payload.description is not None:
                item['description'] = payload.description
            if payload.owner is not None:
                item['owner'] = payload.owner
            if payload.status is not None:
                item['status'] = payload.status
            if payload.due_date is not None:
                item['due_date'] = payload.due_date
            item['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = item.copy()
        _audit(auth.tenant_id, 'crm_project_updated', project_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'project': snapshot}

    @router.get('/crm/projects/board')
    def projects_board(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:projects:board', 180, 60)
        with lock:
            items = [p.copy() for p in projects_memory if p.get('tenant_id') == auth.tenant_id]
        columns: dict[str, list[dict[str, Any]]] = {'planning': [], 'active': [], 'blocked': [], 'done': []}
        for item in items:
            key = str(item.get('status', 'planning')).lower().replace(' ', '_')
            if key not in columns:
                columns[key] = []
            columns[key].append(item)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'board': columns}

    # ── Custom Entities (Extensibility) ──────────────────────────────────────

    @router.post('/crm/custom-entities/types')
    def create_custom_entity_type(payload: CustomEntityTypeCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:entities:types:create', 40, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            existing = next(
                (
                    e for e in custom_entity_types_memory
                    if e.get('tenant_id') == auth.tenant_id and str(e.get('key', '')).lower() == payload.key.lower()
                ),
                None,
            )
            if existing is not None:
                return {'status': 'ok', 'tenant_id': auth.tenant_id, 'entity_type': existing, 'duplicate': True}
            entity_type: dict[str, Any] = {
                'id': len(custom_entity_types_memory) + 1,
                'tenant_id': auth.tenant_id,
                'key': payload.key,
                'name': payload.name,
                'description': payload.description,
                'fields': payload.fields,
                'created_at': now,
                'updated_at': now,
            }
            custom_entity_types_memory.append(entity_type)
        _audit(auth.tenant_id, 'crm_custom_entity_type_created', int(entity_type['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'entity_type': entity_type}

    @router.get('/crm/custom-entities/types')
    def list_custom_entity_types(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:entities:types:list', 120, 60)
        with lock:
            items = [e.copy() for e in custom_entity_types_memory if e.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda e: str(e.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'entity_types': items}

    @router.post('/crm/custom-entities/{entity_key}/records', responses={404: {'description': ENTITY_TYPE_NOT_FOUND}})
    def upsert_custom_entity_record(
        entity_key: str,
        payload: CustomEntityRecordUpsertRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:entities:records:upsert', 120, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            entity_type = next(
                (
                    e for e in custom_entity_types_memory
                    if e.get('tenant_id') == auth.tenant_id and str(e.get('key', '')) == entity_key
                ),
                None,
            )
            if entity_type is None:
                raise HTTPException(status_code=404, detail=ENTITY_TYPE_NOT_FOUND)
            record: dict[str, Any] = {
                'id': len(custom_entity_records_memory) + 1,
                'tenant_id': auth.tenant_id,
                'entity_key': entity_key,
                'values': payload.values,
                'created_at': now,
                'updated_at': now,
            }
            custom_entity_records_memory.append(record)
        _audit(auth.tenant_id, 'crm_custom_entity_record_created', int(record['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'record': record}

    @router.get('/crm/custom-entities/{entity_key}/records', responses={404: {'description': ENTITY_TYPE_NOT_FOUND}})
    def list_custom_entity_records(
        entity_key: str,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:entities:records:list', 180, 60)
        with lock:
            entity_type = next(
                (
                    e for e in custom_entity_types_memory
                    if e.get('tenant_id') == auth.tenant_id and str(e.get('key', '')) == entity_key
                ),
                None,
            )
            if entity_type is None:
                raise HTTPException(status_code=404, detail=ENTITY_TYPE_NOT_FOUND)
            items = [
                r.copy() for r in custom_entity_records_memory
                if r.get('tenant_id') == auth.tenant_id and str(r.get('entity_key', '')) == entity_key
            ]
        items.sort(key=lambda r: str(r.get('created_at', '')), reverse=True)
        total = len(items)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'entity_key': entity_key, 'count': len(items[offset:offset+limit]), 'total': total, 'records': items[offset:offset+limit]}

    # ── API + Automation Tools ───────────────────────────────────────────────

    @router.post('/crm/automation/recipes')
    def create_automation_recipe(payload: AutomationRecipeCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:automation:create', 60, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_recipe: dict[str, Any] | None = None
        created_recipe: dict[str, Any] | None = None
        with lock:
            existing = next(
                (
                    r for r in automation_recipes_memory
                    if r.get('tenant_id') == auth.tenant_id
                    and str(r.get('name', '')).strip().lower() == payload.name.strip().lower()
                    and str(r.get('trigger', '')).strip().lower() == payload.trigger.strip().lower()
                    and str(r.get('action', '')).strip().lower() == payload.action.strip().lower()
                ),
                None,
            )
            if existing is not None:
                duplicate_recipe = existing.copy()
            else:
                recipe: dict[str, Any] = {
                'id': len(automation_recipes_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'trigger': payload.trigger,
                'action': payload.action,
                'config': payload.config,
                'enabled': payload.enabled,
                'run_count': 0,
                'last_run_at': None,
                'created_at': now,
                'updated_at': now,
            }
                automation_recipes_memory.append(recipe)
                created_recipe = recipe

        if duplicate_recipe is not None:
            _audit(auth.tenant_id, 'crm_automation_recipe_reused', int(duplicate_recipe.get('id', 0)))
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'recipe': duplicate_recipe,
                'duplicate': True,
                'created': False,
            }

        if created_recipe is None:
            raise HTTPException(status_code=500, detail='Failed to create automation recipe.')

        _audit(auth.tenant_id, 'crm_automation_recipe_created', int(created_recipe['id']))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'recipe': created_recipe, 'duplicate': False, 'created': True}

    @router.get('/crm/automation/recipes')
    def list_automation_recipes(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:automation:list', 180, 60)
        with lock:
            items = [r.copy() for r in automation_recipes_memory if r.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda r: str(r.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'recipes': items}

    @router.post('/crm/automation/recipes/{recipe_id}/run', responses={404: {'description': AUTOMATION_RECIPE_NOT_FOUND}})
    def run_automation_recipe(recipe_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:automation:run', 60, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            item = next((r for r in automation_recipes_memory if r.get('tenant_id') == auth.tenant_id and int(r.get('id', 0)) == recipe_id), None)
            if item is None:
                raise HTTPException(status_code=404, detail=AUTOMATION_RECIPE_NOT_FOUND)
            item['run_count'] = int(item.get('run_count', 0)) + 1
            item['last_run_at'] = now
            item['updated_at'] = now
            snapshot = item.copy()
        _audit(auth.tenant_id, 'crm_automation_recipe_ran', recipe_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'recipe': snapshot, 'run_at': now}

    @router.post('/crm/api-tokens')
    def create_api_token(payload: APITokenCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:api-tokens:create', 30, 60)
        now = datetime.now(UTC).isoformat()
        duplicate_token: dict[str, Any] | None = None
        created_token: dict[str, Any] | None = None
        normalized_name = payload.name.strip().lower()
        normalized_scopes = sorted({scope.strip().lower() for scope in payload.scopes if scope.strip()})
        with lock:
            existing = next(
                (
                    t for t in api_tokens_memory
                    if t.get('tenant_id') == auth.tenant_id
                    and str(t.get('name', '')).strip().lower() == normalized_name
                    and sorted({str(scope).strip().lower() for scope in t.get('scopes', []) if str(scope).strip()}) == normalized_scopes
                ),
                None,
            )
            if existing is not None:
                duplicate_token = existing.copy()
            else:
                raw = f'{auth.tenant_id}:{payload.name}:{now}:{len(api_tokens_memory)+1}'
                token_preview = hashlib.sha256(raw.encode('utf-8')).hexdigest()
                token: dict[str, Any] = {
                    'id': len(api_tokens_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'name': payload.name,
                    'scopes': payload.scopes,
                    'token_prefix': token_preview[:12],
                    'created_at': now,
                    'last_used_at': None,
                    'status': 'active',
                }
                api_tokens_memory.append(token)
                created_token = token

        if duplicate_token is not None:
            _audit(auth.tenant_id, 'crm_api_token_reused', int(duplicate_token.get('id', 0)))
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'api_token': duplicate_token,
                'token_hint': str(duplicate_token.get('token_prefix', '')),
                'duplicate': True,
                'created': False,
            }

        if created_token is None:
            raise HTTPException(status_code=500, detail='Failed to create API token.')

        _audit(auth.tenant_id, 'crm_api_token_created', int(created_token['id']))
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'api_token': created_token,
            'token_hint': str(created_token.get('token_prefix', '')),
            'duplicate': False,
            'created': True,
        }

    @router.get('/crm/api-tokens')
    def list_api_tokens(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:api-tokens:list', 120, 60)
        with lock:
            items = [t.copy() for t in api_tokens_memory if t.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda t: str(t.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'api_tokens': items}

    # ── Analytics & Reporting ─────────────────────────────────────────────────

    @router.get('/crm/reports/forecast')
    def get_forecast(  # pyright: ignore[reportUnusedFunction]
        auth: AuthDep,
        days: Annotated[int, Query(ge=7, le=365)] = 30,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:reports:forecast', 120, 60)
        now = datetime.now(UTC)
        window_days = _to_window_days(days)
        window_start = now - timedelta(days=window_days)
        with lock:
            tenant_deals = [d.copy() for d in deals_memory if d.get('tenant_id') == auth.tenant_id]
            tenant_invoices = [i.copy() for i in crm_invoices_memory if i.get('tenant_id') == auth.tenant_id]

        tenant_deals = [
            d for d in tenant_deals
            if _is_in_window(d.get('created_at') or d.get('updated_at') or d.get('close_date'), window_start)
        ]
        tenant_invoices = [
            i for i in tenant_invoices
            if _is_in_window(i.get('created_at') or i.get('updated_at') or i.get('due_date'), window_start)
        ]

        open_deals = [d for d in tenant_deals if d.get('stage') not in ('closed_won', 'closed_lost')]
        won_deals = [d for d in tenant_deals if d.get('stage') == 'closed_won']

        # Weighted forecast by stage probability
        weighted_pipeline = round(sum(
            float(d.get('value', 0)) * float(d.get('probability', 0)) / 100.0
            for d in open_deals
        ), 2)
        closed_won_total = round(sum(float(d.get('value', 0)) for d in won_deals), 2)
        outstanding_invoices = round(sum(float(i.get('amount', 0)) for i in tenant_invoices if i.get('status') == 'pending'), 2)
        paid_invoices = round(sum(float(i.get('amount', 0)) for i in tenant_invoices if i.get('status') == 'paid'), 2)

        # Group by close_date month for timeline
        monthly: dict[str, float] = {}
        for d in open_deals:
            month = str(d.get('close_date', ''))[:7] or 'unknown'
            monthly.setdefault(month, 0.0)
            monthly[month] += float(d.get('value', 0)) * float(d.get('probability', 0)) / 100.0

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'window_days': window_days,
            'weighted_pipeline': weighted_pipeline,
            'closed_won_total': closed_won_total,
            'outstanding_invoices': outstanding_invoices,
            'paid_invoices': paid_invoices,
            'monthly_forecast': {k: round(v, 2) for k, v in sorted(monthly.items())},
        }

    @router.get('/crm/reports/kpis')
    def get_kpis(  # pyright: ignore[reportUnusedFunction]
        auth: AuthDep,
        days: Annotated[int, Query(ge=7, le=365)] = 30,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:reports:kpis', 120, 60)
        now = datetime.now(UTC)
        window_days = _to_window_days(days)
        window_start = now - timedelta(days=window_days)
        with lock:
            tenant_contacts = [c for c in contacts_memory if c.get('tenant_id') == auth.tenant_id]
            tenant_deals = [d for d in deals_memory if d.get('tenant_id') == auth.tenant_id]
            tenant_leads = [l for l in leads_memory if l.get('tenant_id') == auth.tenant_id]
            tenant_tickets = [t for t in tickets_memory if t.get('tenant_id') == auth.tenant_id]
            tenant_tasks = [t for t in tasks_memory if t.get('tenant_id') == auth.tenant_id]

        tenant_contacts = [c for c in tenant_contacts if _is_in_window(c.get('created_at'), window_start)]
        tenant_deals = [d for d in tenant_deals if _is_in_window(d.get('created_at') or d.get('updated_at') or d.get('close_date'), window_start)]
        tenant_leads = [l for l in tenant_leads if _is_in_window(l.get('created_at') or l.get('updated_at'), window_start)]
        tenant_tickets = [t for t in tenant_tickets if _is_in_window(t.get('created_at') or t.get('updated_at'), window_start)]
        tenant_tasks = [t for t in tenant_tasks if _is_in_window(t.get('created_at') or t.get('updated_at') or t.get('due_date'), window_start)]

        won_deals = [d for d in tenant_deals if d.get('stage') == 'closed_won']
        lost_deals = [d for d in tenant_deals if d.get('stage') == 'closed_lost']
        total_closed = len(won_deals) + len(lost_deals)
        win_rate = round(len(won_deals) / total_closed * 100, 1) if total_closed > 0 else 0.0

        converted_leads = [l for l in tenant_leads if l.get('status') == 'converted']
        lead_conversion_rate = round(len(converted_leads) / len(tenant_leads) * 100, 1) if tenant_leads else 0.0

        open_tickets = [t for t in tenant_tickets if t.get('status') == 'open']
        escalated_tickets = [t for t in tenant_tickets if t.get('escalated')]

        avg_deal_value = round(sum(float(d.get('value', 0)) for d in tenant_deals) / len(tenant_deals), 2) if tenant_deals else 0.0

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'kpis': {
                'total_contacts': len(tenant_contacts),
                'total_leads': len(tenant_leads),
                'lead_conversion_rate_pct': lead_conversion_rate,
                'total_deals': len(tenant_deals),
                'win_rate_pct': win_rate,
                'avg_deal_value': avg_deal_value,
                'closed_won_value': round(sum(float(d.get('value', 0)) for d in won_deals), 2),
                'open_tickets': len(open_tickets),
                'escalated_tickets': len(escalated_tickets),
                'open_tasks': len([t for t in tenant_tasks if t.get('status') == 'open']),
                'overdue_tasks': len([t for t in tenant_tasks if t.get('status') == 'open' and str(t.get('due_date', '')) < datetime.now(UTC).date().isoformat()]),
            },
            'window_days': window_days,
        }

    @router.get('/crm/reports/executive-analytics')
    def get_executive_analytics(  # pyright: ignore[reportUnusedFunction]
        auth: AuthDep,
        days: Annotated[int, Query(ge=7, le=365)] = 30,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:crm:reports:executive', 90, 60)
        now = datetime.now(UTC)
        window_days = _to_window_days(days)
        window_start = now - timedelta(days=window_days)

        with lock:
            tenant_contacts = [c.copy() for c in contacts_memory if c.get('tenant_id') == auth.tenant_id]
            tenant_deals = [d.copy() for d in deals_memory if d.get('tenant_id') == auth.tenant_id]
            tenant_leads = [l.copy() for l in leads_memory if l.get('tenant_id') == auth.tenant_id]
            tenant_tickets = [t.copy() for t in tickets_memory if t.get('tenant_id') == auth.tenant_id]
            tenant_tasks = [t.copy() for t in tasks_memory if t.get('tenant_id') == auth.tenant_id]

        with get_db_session() as session:
            db_contacts = [_contact_to_dict(row) for row in session.query(Contact).filter(Contact.tenant_id == auth.tenant_id).all()]
            db_deals = [_deal_to_dict(row) for row in session.query(Deal).filter(Deal.tenant_id == auth.tenant_id).all()]
            db_leads = [_lead_to_dict(row) for row in session.query(Lead).filter(Lead.tenant_id == auth.tenant_id).all()]
            db_tickets = [_ticket_to_dict(row) for row in session.query(Ticket).filter(Ticket.tenant_id == auth.tenant_id).all()]
            db_tasks = [_task_to_dict(row) for row in session.query(Task).filter(Task.tenant_id == auth.tenant_id).all()]

        def _merge_items(mem_rows: list[dict[str, Any]], db_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
            merged: dict[str, dict[str, Any]] = {}
            for row in db_rows:
                merged[f"db:{int(row.get('id', 0))}"] = row
            for row in mem_rows:
                row_id = int(row.get('id', 0))
                key = f"db:{row_id}" if row_id > 0 and f"db:{row_id}" in merged else f"mem:{row_id}:{len(merged)}"
                merged[key] = row
            return list(merged.values())

        tenant_contacts = _merge_items(tenant_contacts, db_contacts)
        tenant_deals = _merge_items(tenant_deals, db_deals)
        tenant_leads = _merge_items(tenant_leads, db_leads)
        tenant_tickets = _merge_items(tenant_tickets, db_tickets)
        tenant_tasks = _merge_items(tenant_tasks, db_tasks)

        tenant_contacts = [c for c in tenant_contacts if _is_in_window(c.get('created_at'), window_start)]
        tenant_deals = [d for d in tenant_deals if _is_in_window(d.get('created_at') or d.get('updated_at') or d.get('close_date'), window_start)]
        tenant_leads = [l for l in tenant_leads if _is_in_window(l.get('created_at') or l.get('updated_at'), window_start)]
        tenant_tickets = [t for t in tenant_tickets if _is_in_window(t.get('created_at') or t.get('updated_at'), window_start)]
        tenant_tasks = [t for t in tenant_tasks if _is_in_window(t.get('created_at') or t.get('updated_at') or t.get('due_date'), window_start)]

        stage_counts: dict[str, int] = {stage['stage']: 0 for stage in PIPELINE_STAGES}
        for deal in tenant_deals:
            stage = str(deal.get('stage', 'prospect'))
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        funnel = [
            {
                'stage': stage['stage'],
                'display': stage['display'],
                'count': stage_counts.get(stage['stage'], 0),
            }
            for stage in PIPELINE_STAGES
        ]

        revenue_trend: dict[str, float] = {}
        for deal in tenant_deals:
            if str(deal.get('stage', '')) != 'closed_won':
                continue
            close_date = str(deal.get('close_date') or deal.get('updated_at') or deal.get('created_at') or '')
            month = close_date[:7] if len(close_date) >= 7 else now.strftime('%Y-%m')
            revenue_trend.setdefault(month, 0.0)
            revenue_trend[month] += float(deal.get('value', 0.0))

        sorted_months = sorted(revenue_trend.keys())[-6:]
        monthly_closed_won = [{'month': month, 'value': round(revenue_trend[month], 2)} for month in sorted_months]

        lead_source_breakdown: dict[str, int] = {}
        for lead in tenant_leads:
            source = str(lead.get('source', 'unknown')).strip().lower() or 'unknown'
            lead_source_breakdown[source] = lead_source_breakdown.get(source, 0) + 1

        overdue_tasks = len([
            task for task in tenant_tasks
            if str(task.get('status', '')) == 'open' and str(task.get('due_date', '')) < now.date().isoformat()
        ])
        escalated_tickets = len([ticket for ticket in tenant_tickets if bool(ticket.get('escalated'))])

        anomalies: list[dict[str, Any]] = []
        if overdue_tasks > 0:
            anomalies.append({'type': 'task_overdue', 'severity': 'medium', 'detail': f'{overdue_tasks} overdue open tasks'})
        if tenant_tickets and (escalated_tickets / len(tenant_tickets)) >= 0.2:
            anomalies.append({'type': 'support_risk', 'severity': 'high', 'detail': 'Escalation ratio is above 20%'})
        open_stage_total = sum(
            count for stage, count in stage_counts.items()
            if stage not in ('closed_won', 'closed_lost')
        )
        negotiation_share = (stage_counts.get('negotiation', 0) / open_stage_total) if open_stage_total else 0.0
        if negotiation_share >= 0.6:
            anomalies.append({'type': 'pipeline_congestion', 'severity': 'medium', 'detail': 'Open pipeline is concentrated in negotiation stage'})

        total_contacts = len(tenant_contacts)
        converted_leads = len([lead for lead in tenant_leads if str(lead.get('status', '')) == 'converted'])
        conversion_rate = round((converted_leads / len(tenant_leads)) * 100, 1) if tenant_leads else 0.0

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generated_at': now.isoformat(),
            'window_days': window_days,
            'overview': {
                'total_contacts': total_contacts,
                'total_deals': len(tenant_deals),
                'total_leads': len(tenant_leads),
                'lead_conversion_rate_pct': conversion_rate,
                'escalated_ticket_ratio_pct': round((escalated_tickets / len(tenant_tickets)) * 100, 1) if tenant_tickets else 0.0,
                'overdue_tasks': overdue_tasks,
            },
            'charts': {
                'pipeline_funnel': funnel,
                'monthly_closed_won': monthly_closed_won,
                'lead_source_breakdown': lead_source_breakdown,
            },
            'anomalies': anomalies,
        }

    @router.get('/crm/ops/backup')
    def get_backup_ops(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:ops:backup:get', 120, 60)
        now = datetime.now(UTC)
        with lock:
            config = _get_backup_config(auth.tenant_id).copy()
            snapshots = [
                row.copy() for row in backup_snapshots_memory
                if row.get('tenant_id') == auth.tenant_id and row.get('type') == 'snapshot'
            ]
        snapshots.sort(key=lambda row: str(row.get('started_at', '')), reverse=True)
        latest_incremental = next((row for row in snapshots if row.get('mode') == 'incremental'), None)
        latest_full = next((row for row in snapshots if row.get('mode') == 'full'), None)

        next_incremental_at = now + timedelta(minutes=int(config.get('incremental_minutes', 5)))
        next_full_at = _next_full_backup_utc(config, now)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'config': config,
            'latest_incremental': latest_incremental,
            'latest_full': latest_full,
            'snapshot_count': len(snapshots),
            'next_runs': {
                'incremental_at': next_incremental_at.isoformat(),
                'full_at': next_full_at.isoformat(),
            },
            'schedule_health': 'healthy' if bool(config.get('enabled', True)) else 'paused',
        }

    @router.post('/crm/ops/backup/config')
    def update_backup_config(payload: CRMBackupConfigRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:ops:backup:config', 60, 60)
        now_iso = datetime.now(UTC).isoformat()
        with lock:
            config = _get_backup_config(auth.tenant_id)
            config['incremental_minutes'] = payload.incremental_minutes
            config['full_backup_weekday'] = payload.full_backup_weekday
            config['full_backup_hour_utc'] = payload.full_backup_hour_utc
            config['retention_days'] = payload.retention_days
            config['enabled'] = payload.enabled
            config['updated_at'] = now_iso
            snapshot = config.copy()

        _audit(auth.tenant_id, 'crm_backup_config_updated', int(snapshot.get('id', 0)))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'config': snapshot}

    @router.post('/crm/ops/backup/run')
    def run_backup(
        auth: AuthDep,
        mode: Annotated[str, Query(pattern=r'^(incremental|full)$')] = 'incremental',
        source: Annotated[str, Query(max_length=80)] = 'manual',
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:ops:backup:run', 30, 60)
        now = datetime.now(UTC)

        with lock:
            _get_backup_config(auth.tenant_id)
            tenant_contacts = [c for c in contacts_memory if c.get('tenant_id') == auth.tenant_id]
            tenant_companies = [c for c in companies_memory if c.get('tenant_id') == auth.tenant_id]
            tenant_deals = [d for d in deals_memory if d.get('tenant_id') == auth.tenant_id]
            tenant_tickets = [t for t in tickets_memory if t.get('tenant_id') == auth.tenant_id]

            counts = {
                'contacts': len(tenant_contacts),
                'companies': len(tenant_companies),
                'deals': len(tenant_deals),
                'tickets': len(tenant_tickets),
            }
            digest_seed = f"{auth.tenant_id}:{mode}:{counts['contacts']}:{counts['companies']}:{counts['deals']}:{counts['tickets']}:{now.isoformat()}"
            snapshot = {
                'id': len(backup_snapshots_memory) + 1,
                'tenant_id': auth.tenant_id,
                'type': 'snapshot',
                'mode': mode,
                'source': source,
                'started_at': now.isoformat(),
                'completed_at': now.isoformat(),
                'status': 'completed',
                'checksum': hashlib.sha256(digest_seed.encode('utf-8')).hexdigest()[:24],
                'entity_counts': counts,
            }
            backup_snapshots_memory.append(snapshot)

        snapshot_id = snapshot.get('id')
        _audit(auth.tenant_id, 'crm_backup_run', snapshot_id if isinstance(snapshot_id, int) else None)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'backup': snapshot}

    @router.get('/crm/ops/live-sync')
    def get_live_sync_status(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:ops:sync:get', 120, 60)
        with lock:
            state = _get_live_sync_state(auth.tenant_id).copy()
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sync': state}

    @router.post('/crm/ops/live-sync/toggle')
    def toggle_live_sync(payload: CRMLiveSyncToggleRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:ops:sync:toggle', 60, 60)
        now_iso = datetime.now(UTC).isoformat()
        with lock:
            state = _get_live_sync_state(auth.tenant_id)
            state['enabled'] = payload.enabled
            state['interval_seconds'] = payload.interval_seconds
            state['updated_at'] = now_iso
            snapshot = state.copy()
        _audit(auth.tenant_id, 'crm_live_sync_toggled', int(snapshot.get('id', 0)))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sync': snapshot}

    @router.post('/crm/ops/live-sync/run')
    def run_live_sync(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:crm:ops:sync:run', 60, 60)
        now_iso = datetime.now(UTC).isoformat()
        with lock:
            state = _get_live_sync_state(auth.tenant_id)
            state['last_sync_at'] = now_iso
            state['last_success_at'] = now_iso
            state['lag_seconds'] = 0
            state['events_processed_24h'] = int(state.get('events_processed_24h', 0)) + 125
            state['conflict_queue'] = 0
            state['updated_at'] = now_iso
            snapshot = state.copy()
        _audit(auth.tenant_id, 'crm_live_sync_ran', int(snapshot.get('id', 0)))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sync': snapshot}

    return router


# ── Segment filter helper (module-level) ─────────────────────────────────────

def _apply_segment_filters(tenant_id: str, filters: dict[str, Any], contacts_memory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply segment filters to contacts and return matching copies."""
    if contacts_memory:
        items = [dict(c) for c in contacts_memory if str(c.get('tenant_id', '')) == str(tenant_id)]
    else:
        with get_db_session() as session:
            items = []
            contacts = session.query(Contact).filter(Contact.tenant_id == tenant_id).all()
            for contact in contacts:
                data = dict(contact.data or {})
                tags = data.get('tags', [])
                items.append({
                    'id': contact.id,
                    'tenant_id': contact.tenant_id,
                    'email': contact.email,
                    'first_name': contact.first_name,
                    'last_name': contact.last_name,
                    'company': contact.company,
                    'phone': contact.phone,
                    'lifecycle_stage': contact.lifecycle_stage,
                    'lead_score': contact.score,
                    'tags': tags if isinstance(tags, list) else [],
                    'properties': data.get('properties', {}),
                    'created_at': contact.created_at.isoformat(),
                    'updated_at': contact.updated_at.isoformat(),
                    'source': data.get('source', 'api'),
                })
    if not filters:
        return items
    if 'lifecycle_stage' in filters:
        items = [c for c in items if str(c.get('lifecycle_stage', '')) == str(filters['lifecycle_stage'])]
    if 'min_lead_score' in filters:
        items = [c for c in items if int(c.get('lead_score', 0)) >= int(filters['min_lead_score'])]
    if 'tag' in filters:
        tag = str(filters['tag'])
        items = [c for c in items if tag in [str(t) for t in c.get('tags', [])]]
    if 'company' in filters:
        cq = str(filters['company']).lower()
        items = [c for c in items if cq in str(c.get('company', '')).lower()]
    return items
