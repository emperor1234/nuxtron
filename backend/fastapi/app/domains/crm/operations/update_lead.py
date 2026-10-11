"""Crm use cases: update lead."""

from ....database import get_db_session
from ....models import Deal
from ....models import Lead
from ....models import Task
from ....models import Ticket
from ..constants import AuthDep
from ..constants import CAMPAIGN_NOT_FOUND
from ..constants import LEAD_NOT_FOUND
from ..constants import SEGMENT_NOT_FOUND
from ..constants import TASK_NOT_FOUND
from ..constants import TICKET_NOT_FOUND
from ..runtime import ContextRuntime
from ..schemas import CampaignCreateRequest
from ..schemas import LeadUpdateRequest
from ..schemas import SLARuleCreateRequest
from ..schemas import TaskUpdateRequest
from ..schemas import TicketCreateRequest
from ..schemas import TicketUpdateRequest
from ..services.apply_segment_filters import _apply_segment_filters
from .contact_to_dict import helper_deal_to_dict
from .contact_to_dict import helper_get_db_ticket
from .contact_to_dict import helper_lead_to_dict
from .task_to_dict import helper_audit
from .task_to_dict import helper_create_db_ticket
from .task_to_dict import helper_list_db_tasks
from .task_to_dict import helper_list_db_tickets
from .task_to_dict import helper_task_to_dict
from .task_to_dict import helper_ticket_to_dict
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_update_lead(
    runtime: ContextRuntime, lead_id: int, payload: LeadUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:leads:update", 120, 60)
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
            d["notes"] = payload.notes
            obj.data = d
        session.commit()
        session.refresh(obj)
        snapshot = helper_lead_to_dict(obj)
    helper_audit(runtime, auth.tenant_id, "crm_lead_updated", lead_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "lead": snapshot}


def execute_convert_lead(runtime: ContextRuntime, lead_id: int, auth: AuthDep) -> dict[str, Any]:
    """Convert a lead into an opportunity/deal."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:leads:convert", 60, 60)
    with get_db_session() as session:
        lead_obj = session.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == auth.tenant_id).first()
        if lead_obj is None:
            raise HTTPException(status_code=404, detail=LEAD_NOT_FOUND)
        deal_obj = Deal(
            tenant_id=auth.tenant_id,
            title=lead_obj.title,
            value=lead_obj.estimated_value,
            currency="USD",
            stage="qualified",
            contact_id=lead_obj.contact_id,
            company_id=lead_obj.company_id,
            data={"probability": 25, "properties": {"converted_from_lead": lead_id}, "source": "lead_conversion"},
        )
        session.add(deal_obj)
        lead_obj.status = "converted"
        d = dict(lead_obj.data or {})
        session.flush()
        d["converted_deal_id"] = deal_obj.id
        lead_obj.data = d
        session.commit()
        session.refresh(lead_obj)
        session.refresh(deal_obj)
        lead_snap = helper_lead_to_dict(lead_obj)
        deal_snap = helper_deal_to_dict(deal_obj)
    helper_audit(runtime, auth.tenant_id, "crm_lead_converted", lead_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "lead": lead_snap, "deal": deal_snap}


def execute_list_tasks(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=40)] = None,
    priority: Annotated[str | None, Query(max_length=20)] = None,
    assigned_to: Annotated[str | None, Query(max_length=120)] = None,
    contact_id: Annotated[int | None, Query(ge=1)] = None,
    deal_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tasks:list", 240, 60)
    items, total = helper_list_db_tasks(
        auth.tenant_id,
        status=(status or "").strip() or None,
        priority=(priority or "").strip() or None,
        assigned_to=(assigned_to or "").strip() or None,
        contact_id=contact_id,
        deal_id=deal_id,
        limit=limit,
        offset=offset,
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "total": total,
        "limit": limit,
        "offset": offset,
        "tasks": items,
    }


def execute_update_task(
    runtime: ContextRuntime, task_id: int, payload: TaskUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tasks:update", 120, 60)
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
        snapshot = helper_task_to_dict(obj)
    helper_audit(runtime, auth.tenant_id, "crm_task_updated", task_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "task": snapshot}


def execute_tasks_kanban(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tasks:kanban", 180, 60)
    items, _ = helper_list_db_tasks(auth.tenant_id, limit=500)
    with runtime.lock:
        mem_items = [dict(t) for t in runtime.tasks_memory if str(t.get("tenant_id", "")) == str(auth.tenant_id)]
    existing_ids = {int(item.get("id", 0)) for item in items if int(item.get("id", 0)) > 0}
    for task in mem_items:
        task_id = int(task.get("id", 0))
        if task_id <= 0 or task_id not in existing_ids:
            items.append(task)
    columns: dict[str, list[dict[str, Any]]] = {"open": [], "in_progress": [], "completed": [], "cancelled": []}
    for task in items:
        col = str(task.get("status", "open")).lower().replace(" ", "_")
        if col not in columns:
            columns[col] = []
        columns[col].append(task)
    return {"status": "ok", "tenant_id": auth.tenant_id, "kanban": columns}


def execute_create_ticket(runtime: ContextRuntime, payload: TicketCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tickets:create", 120, 60)
    ticket_number = f"TKT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    sla = next(
        (
            r
            for r in runtime.sla_rules_memory
            if r.get("tenant_id") == auth.tenant_id and r.get("priority") == payload.priority
        ),
        None,
    )
    first_response_deadline = None
    resolution_deadline = None
    if sla:
        fh = int(sla.get("first_response_hours", 4))
        rh = int(sla.get("resolution_hours", 24))
        first_response_deadline = (datetime.now(UTC) + timedelta(hours=fh)).isoformat()
        resolution_deadline = (datetime.now(UTC) + timedelta(hours=rh)).isoformat()
    ticket = helper_create_db_ticket(
        auth.tenant_id, payload, ticket_number, first_response_deadline, resolution_deadline
    )
    helper_audit(runtime, auth.tenant_id, "crm_ticket_created", int(ticket["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "ticket": ticket}


def execute_list_tickets(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=40)] = None,
    priority: Annotated[str | None, Query(max_length=20)] = None,
    channel: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tickets:list", 240, 60)
    items, total = helper_list_db_tickets(
        auth.tenant_id,
        status=(status or "").strip() or None,
        priority=(priority or "").strip() or None,
        channel=(channel or "").strip() or None,
        limit=limit,
        offset=offset,
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "total": total,
        "limit": limit,
        "offset": offset,
        "tickets": items,
    }


def execute_get_ticket(runtime: ContextRuntime, ticket_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tickets:get", 300, 60)
    obj = helper_get_db_ticket(ticket_id, auth.tenant_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
    return {"status": "ok", "tenant_id": auth.tenant_id, "ticket": helper_ticket_to_dict(obj)}


def execute_update_ticket(
    runtime: ContextRuntime, ticket_id: int, payload: TicketUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tickets:update", 120, 60)
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
        snapshot = helper_ticket_to_dict(obj)
    helper_audit(runtime, auth.tenant_id, "crm_ticket_updated", ticket_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "ticket": snapshot}


def execute_escalate_ticket(runtime: ContextRuntime, ticket_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tickets:escalate", 60, 60)
    with get_db_session() as session:
        obj = session.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == auth.tenant_id).first()
        if obj is None:
            raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
        obj.escalated = True
        obj.priority = "critical"
        session.commit()
        session.refresh(obj)
        snapshot = helper_ticket_to_dict(obj)
    helper_audit(runtime, auth.tenant_id, "crm_ticket_escalated", ticket_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "ticket": snapshot}


def execute_create_sla_rule(runtime: ContextRuntime, payload: SLARuleCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:sla:create", 40, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_sla: dict[str, Any] | None = None
    created_sla: dict[str, Any] | None = None
    with runtime.lock:
        existing = next(
            (
                r
                for r in runtime.sla_rules_memory
                if r.get("tenant_id") == auth.tenant_id
                and str(r.get("name", "")).strip().lower() == payload.name.strip().lower()
                and (str(r.get("applies_to", "")).strip().lower() == payload.applies_to.strip().lower())
                and (str(r.get("priority", "")).strip().lower() == payload.priority.strip().lower())
            ),
            None,
        )
        if existing is not None:
            duplicate_sla = existing.copy()
        else:
            rule: dict[str, Any] = {
                "id": len(runtime.sla_rules_memory) + 1,
                "tenant_id": auth.tenant_id,
                "name": payload.name,
                "applies_to": payload.applies_to,
                "priority": payload.priority,
                "first_response_hours": payload.first_response_hours,
                "resolution_hours": payload.resolution_hours,
                "created_at": now,
            }
            runtime.sla_rules_memory.append(rule)
            created_sla = rule
    if duplicate_sla is not None:
        helper_audit(runtime, auth.tenant_id, "crm_sla_rule_reused", int(duplicate_sla.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "sla_rule": duplicate_sla,
            "duplicate": True,
            "created": False,
        }
    if created_sla is None:
        raise HTTPException(status_code=500, detail="Failed to create SLA rule.")
    helper_audit(runtime, auth.tenant_id, "crm_sla_rule_created", int(created_sla["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "sla_rule": created_sla, "duplicate": False, "created": True}


def execute_list_sla_rules(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:sla:list", 120, 60)
    with runtime.lock:
        items = [r.copy() for r in runtime.sla_rules_memory if r.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "sla_rules": items}


def execute_create_campaign(runtime: ContextRuntime, payload: CampaignCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:campaigns:create", 60, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_campaign: dict[str, Any] | None = None
    created_campaign: dict[str, Any] | None = None
    with runtime.lock:
        existing = next(
            (
                c
                for c in runtime.campaigns_memory
                if c.get("tenant_id") == auth.tenant_id
                and str(c.get("name", "")).strip().lower() == payload.name.strip().lower()
                and (str(c.get("type", "")).strip().lower() == payload.type.strip().lower())
                and (str(c.get("subject", "")).strip().lower() == payload.subject.strip().lower())
            ),
            None,
        )
        if existing is not None:
            duplicate_campaign = existing.copy()
        else:
            campaign: dict[str, Any] = {
                "id": len(runtime.campaigns_memory) + 1,
                "tenant_id": auth.tenant_id,
                "name": payload.name,
                "type": payload.type,
                "subject": payload.subject,
                "body": payload.body,
                "segment_id": payload.segment_id,
                "scheduled_at": payload.scheduled_at,
                "ab_test": payload.ab_test,
                "variant_b_subject": payload.variant_b_subject if payload.ab_test else "",
                "status": "draft",
                "sent_count": 0,
                "open_count": 0,
                "click_count": 0,
                "created_at": now,
                "updated_at": now,
            }
            runtime.campaigns_memory.append(campaign)
            created_campaign = campaign
    if duplicate_campaign is not None:
        helper_audit(runtime, auth.tenant_id, "crm_campaign_reused", int(duplicate_campaign.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "campaign": duplicate_campaign,
            "duplicate": True,
            "created": False,
        }
    if created_campaign is None:
        raise HTTPException(status_code=500, detail="Failed to create campaign.")
    helper_audit(runtime, auth.tenant_id, "crm_campaign_created", int(created_campaign["id"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "campaign": created_campaign,
        "duplicate": False,
        "created": True,
    }


def execute_list_campaigns(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=40)] = None,
    type: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:campaigns:list", 180, 60)
    with runtime.lock:
        items = [c.copy() for c in runtime.campaigns_memory if c.get("tenant_id") == auth.tenant_id]
    if (status or "").strip():
        items = [c for c in items if str(c.get("status", "")) == status.strip()]
    if (type or "").strip():
        items = [c for c in items if str(c.get("type", "")) == type.strip()]
    items.sort(key=lambda c: str(c.get("created_at", "")), reverse=True)
    total = len(items)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[offset : offset + limit]),
        "total": total,
        "campaigns": items[offset : offset + limit],
    }


def execute_get_campaign(runtime: ContextRuntime, campaign_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:campaigns:get", 300, 60)
    with runtime.lock:
        item = next(
            (
                c.copy()
                for c in runtime.campaigns_memory
                if c.get("id") == campaign_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
    if item is None:
        raise HTTPException(status_code=404, detail=CAMPAIGN_NOT_FOUND)
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": item}


def execute_send_campaign(runtime: ContextRuntime, campaign_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:campaigns:send", 20, 60)
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        item = next(
            (
                c
                for c in runtime.campaigns_memory
                if c.get("id") == campaign_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail=CAMPAIGN_NOT_FOUND)
        segment = next(
            (
                s
                for s in runtime.segments_memory
                if s.get("id") == item.get("segment_id") and s.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        member_count = int(segment.get("member_count", 0)) if segment else 0
        item["status"] = "sent"
        item["sent_at"] = now
        item["sent_count"] = member_count
        item["updated_at"] = now
        snapshot = item.copy()
    helper_audit(runtime, auth.tenant_id, "crm_campaign_sent", campaign_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": snapshot}


def execute_list_segments(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:segments:list", 180, 60)
    with runtime.lock:
        items = [s.copy() for s in runtime.segments_memory if s.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "segments": items}


def execute_get_segment_members(
    runtime: ContextRuntime,
    segment_id: int,
    auth: AuthDep,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:segments:members", 120, 60)
    with runtime.lock:
        segment = next(
            (s for s in runtime.segments_memory if s.get("id") == segment_id and s.get("tenant_id") == auth.tenant_id),
            None,
        )
    if segment is None:
        raise HTTPException(status_code=404, detail=SEGMENT_NOT_FOUND)
    members = _apply_segment_filters(auth.tenant_id, dict(segment.get("filters", {})), runtime.contacts_memory)
    total = len(members)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "segment_id": segment_id,
        "count": len(members[offset : offset + limit]),
        "total": total,
        "members": members[offset : offset + limit],
    }


def execute_list_sequences(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:sequences:list", 180, 60)
    with runtime.lock:
        items = [s.copy() for s in runtime.email_sequences_memory if s.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda s: str(s.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "sequences": items}
