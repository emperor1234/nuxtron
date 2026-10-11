"""Crm HTTP composition and legacy import exports."""

from ...integrations.vendor_manager import get_vendor_manager
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    create_contact,
    create_company,
    list_activities,
    update_lead,
    get_ticket,
    send_campaign,
    accept_quote,
    list_workflow_rules,
    upsert_custom_entity_record,
    get_kpis,
)
from .services.apply_segment_filters import _apply_segment_filters as _apply_segment_filters
from .schemas import LeadUpdateRequest as LeadUpdateRequest
from .schemas import HubSpotConnectRequest as HubSpotConnectRequest
from .schemas import WorkflowRuleCreateRequest as WorkflowRuleCreateRequest
from .schemas import ContactDedupeRequest as ContactDedupeRequest
from .schemas import SegmentCreateRequest as SegmentCreateRequest
from .schemas import CRMInvoiceCreateRequest as CRMInvoiceCreateRequest
from .schemas import TaskCreateRequest as TaskCreateRequest
from .schemas import CRMWebhookCreateRequest as CRMWebhookCreateRequest
from .schemas import ContactCreateRequest as ContactCreateRequest
from .schemas import DealCreateRequest as DealCreateRequest
from .schemas import DealUpdateRequest as DealUpdateRequest
from .schemas import ActivityCreateRequest as ActivityCreateRequest
from .schemas import HubSpotSyncContactsRequest as HubSpotSyncContactsRequest
from .schemas import TicketUpdateRequest as TicketUpdateRequest
from .schemas import QuoteLineItem as QuoteLineItem
from .schemas import QuoteCreateRequest as QuoteCreateRequest
from .schemas import APITokenCreateRequest as APITokenCreateRequest
from .schemas import CustomEntityTypeCreateRequest as CustomEntityTypeCreateRequest
from .schemas import _PipelineStage as _PipelineStage
from .schemas import TicketCreateRequest as TicketCreateRequest
from .schemas import AutomationRecipeCreateRequest as AutomationRecipeCreateRequest
from .schemas import SLARuleCreateRequest as SLARuleCreateRequest
from .schemas import CRMInvoiceUpdateRequest as CRMInvoiceUpdateRequest
from .schemas import EmailSequenceCreateRequest as EmailSequenceCreateRequest
from .schemas import CampaignCreateRequest as CampaignCreateRequest
from .schemas import CRMBackupConfigRequest as CRMBackupConfigRequest
from .schemas import NoteCreateRequest as NoteCreateRequest
from .schemas import ProjectCreateRequest as ProjectCreateRequest
from .schemas import ContactScoreRequest as ContactScoreRequest
from .schemas import CompanyCreateRequest as CompanyCreateRequest
from .schemas import SequenceStep as SequenceStep
from .schemas import ProjectUpdateRequest as ProjectUpdateRequest
from .schemas import CustomEntityRecordUpsertRequest as CustomEntityRecordUpsertRequest
from .schemas import LeadCreateRequest as LeadCreateRequest
from .schemas import TaskUpdateRequest as TaskUpdateRequest
from .schemas import CRMLiveSyncToggleRequest as CRMLiveSyncToggleRequest
from .constants import WORKFLOW_NOT_FOUND as WORKFLOW_NOT_FOUND
from .constants import CAMPAIGN_NOT_FOUND as CAMPAIGN_NOT_FOUND
from .constants import ENTITY_TYPE_NOT_FOUND as ENTITY_TYPE_NOT_FOUND
from .constants import AUTOMATION_RECIPE_NOT_FOUND as AUTOMATION_RECIPE_NOT_FOUND
from .constants import INVOICE_NOT_FOUND as INVOICE_NOT_FOUND
from .constants import AuthDep as AuthDep
from .constants import SEQUENCE_NOT_FOUND as SEQUENCE_NOT_FOUND
from .constants import TASK_NOT_FOUND as TASK_NOT_FOUND
from .constants import SEGMENT_NOT_FOUND as SEGMENT_NOT_FOUND
from .constants import DEAL_NOT_FOUND as DEAL_NOT_FOUND
from .constants import TICKET_NOT_FOUND as TICKET_NOT_FOUND
from .constants import PROJECT_NOT_FOUND as PROJECT_NOT_FOUND
from .constants import LEAD_NOT_FOUND as LEAD_NOT_FOUND
from .constants import CONTACT_NOT_FOUND as CONTACT_NOT_FOUND
from .constants import QUOTE_NOT_FOUND as QUOTE_NOT_FOUND
from .constants import PIPELINE_STAGES as PIPELINE_STAGES
from ...database import get_db_session
from ...deps import AuthContext
from ...deps import require_auth
from ...integrations.vendor_manager import VendorCredentials
from ...integrations.vendor_manager import VendorType
from ...models import Activity
from ...models import Company
from ...models import Contact
from ...models import Deal
from ...models import Lead
from ...models import Task
from ...models import Ticket
from ...models import WorkflowExecution
from ...models import WorkflowRule


def create_crm_router(
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
    weekday_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    runtime = ContextRuntime(
        activities_memory=activities_memory,
        api_tokens_memory=api_tokens_memory,
        audit_log_memory=audit_log_memory,
        automation_recipes_memory=automation_recipes_memory,
        backup_snapshots_memory=backup_snapshots_memory,
        campaigns_memory=campaigns_memory,
        companies_memory=companies_memory,
        contacts_memory=contacts_memory,
        crm_invoices_memory=crm_invoices_memory,
        custom_entity_records_memory=custom_entity_records_memory,
        custom_entity_types_memory=custom_entity_types_memory,
        deals_memory=deals_memory,
        email_sequences_memory=email_sequences_memory,
        enforce_rate_limit=enforce_rate_limit,
        leads_memory=leads_memory,
        live_sync_state_memory=live_sync_state_memory,
        lock=lock,
        notes_memory=notes_memory,
        projects_memory=projects_memory,
        quotes_memory=quotes_memory,
        segments_memory=segments_memory,
        sla_rules_memory=sla_rules_memory,
        tasks_memory=tasks_memory,
        tickets_memory=tickets_memory,
        vendor_manager=vendor_manager,
        webhook_subscriptions_memory=webhook_subscriptions_memory,
        weekday_map=weekday_map,
        workflow_rules_memory=workflow_rules_memory,
    )
    create_contact.register(router, runtime)
    create_company.register(router, runtime)
    list_activities.register(router, runtime)
    update_lead.register(router, runtime)
    get_ticket.register(router, runtime)
    send_campaign.register(router, runtime)
    accept_quote.register(router, runtime)
    list_workflow_rules.register(router, runtime)
    upsert_custom_entity_record.register(router, runtime)
    get_kpis.register(router, runtime)
    return router
