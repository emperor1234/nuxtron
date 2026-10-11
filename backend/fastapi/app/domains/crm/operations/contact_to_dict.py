"""Crm use cases: contact to dict."""

from ....database import get_db_session
from ....models import Activity
from ....models import Company
from ....models import Contact
from ....models import Deal
from ....models import Lead
from ....models import Ticket
from ....models import WorkflowExecution
from ....models import WorkflowRule
from ..constants import PIPELINE_STAGES
from ..schemas import ActivityCreateRequest
from ..schemas import LeadCreateRequest
from ..schemas import WorkflowRuleCreateRequest
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from sqlalchemy import func
from typing import Any


def helper_contact_to_dict(contact: Contact) -> dict[str, Any]:
    data = dict(contact.data or {})
    tags = data.get("tags", [])
    return {
        "id": contact.id,
        "tenant_id": contact.tenant_id,
        "email": contact.email,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "company": contact.company,
        "phone": contact.phone,
        "lifecycle_stage": contact.lifecycle_stage,
        "lead_score": contact.score,
        "tags": tags if isinstance(tags, list) else [],
        "properties": data.get("properties", {}),
        "score_reason": data.get("score_reason", ""),
        "created_at": contact.created_at.isoformat(),
        "updated_at": contact.updated_at.isoformat(),
        "source": data.get("source", "api"),
    }


def helper_list_db_contacts(tenant_id: str) -> list[dict[str, Any]]:
    with get_db_session() as session:
        contacts = session.query(Contact).filter(Contact.tenant_id == tenant_id).all()
        return [helper_contact_to_dict(contact) for contact in contacts]


def helper_upsert_contact_from_vendor(tenant_id: str, payload: dict[str, Any]) -> str:
    with get_db_session() as session:
        email = str(payload.get("email", "")).strip().lower()
        if not email:
            return "skipped"
        existing = session.query(Contact).filter(Contact.tenant_id == tenant_id, Contact.email == email).first()
        if existing is None:
            created = Contact(
                tenant_id=tenant_id,
                email=email,
                first_name=str(payload.get("first_name", "")).strip(),
                last_name=str(payload.get("last_name", "")).strip(),
                company=str(payload.get("company", "")).strip(),
                phone=str(payload.get("phone", "")).strip(),
                lifecycle_stage=str(payload.get("lifecycle_stage", "lead")).strip() or "lead",
                score=0,
                data={"source": str(payload.get("source", "hubspot")), "properties": {}},
            )
            session.add(created)
            session.flush()
            return "created"
        changed = False
        first_name = str(payload.get("first_name", "")).strip()
        last_name = str(payload.get("last_name", "")).strip()
        company = str(payload.get("company", "")).strip()
        phone = str(payload.get("phone", "")).strip()
        lifecycle_stage = str(payload.get("lifecycle_stage", "")).strip()
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
            return "updated"
        return "skipped"


def helper_company_to_dict(company: Company) -> dict[str, Any]:
    data = dict(company.data or {})
    return {
        "id": company.id,
        "tenant_id": company.tenant_id,
        "name": company.name,
        "domain": company.domain,
        "industry": company.industry,
        "employee_count": company.employee_count,
        "annual_revenue": company.annual_revenue,
        "account_health": data.get("account_health", "green"),
        "properties": data.get("properties", {}),
        "created_at": company.created_at.isoformat(),
        "updated_at": company.updated_at.isoformat(),
        "source": data.get("source", "api"),
    }


def helper_list_db_companies(tenant_id: str) -> list[dict[str, Any]]:
    with get_db_session() as session:
        companies = session.query(Company).filter(Company.tenant_id == tenant_id).all()
        return [helper_company_to_dict(company) for company in companies]


def helper_deal_to_dict(deal: Deal) -> dict[str, Any]:
    data = dict(deal.data or {})
    return {
        "id": deal.id,
        "tenant_id": deal.tenant_id,
        "title": deal.title,
        "value": deal.value,
        "currency": deal.currency,
        "stage": deal.stage,
        "contact_id": deal.contact_id,
        "company_id": deal.company_id,
        "close_date": deal.close_date,
        "probability": int(
            data.get("probability", next((s["probability"] for s in PIPELINE_STAGES if s["stage"] == deal.stage), 10))
        ),
        "properties": data.get("properties", {}),
        "created_at": deal.created_at.isoformat(),
        "updated_at": deal.updated_at.isoformat(),
        "source": data.get("source", "api"),
    }


def helper_list_db_deals(tenant_id: str) -> list[dict[str, Any]]:
    with get_db_session() as session:
        deals = session.query(Deal).filter(Deal.tenant_id == tenant_id).all()
        return [helper_deal_to_dict(deal) for deal in deals]


def helper_workflow_rule_to_dict(obj: WorkflowRule) -> dict[str, Any]:
    data = dict(obj.data or {})
    actions = dict(obj.actions or {})
    conditions = dict(obj.conditions or {})
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "name": obj.name,
        "trigger": obj.trigger,
        "conditions": conditions,
        "action": str(actions.get("type", "")),
        "action_params": dict(actions.get("params") or {}),
        "enabled": obj.enabled,
        "run_count": int(data.get("run_count", 0)),
        "last_triggered_at": data.get("last_triggered_at"),
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }


def helper_get_db_workflow_rule(rule_id: int, tenant_id: str) -> WorkflowRule | None:
    with get_db_session() as session:
        return (
            session.query(WorkflowRule).filter(WorkflowRule.id == rule_id, WorkflowRule.tenant_id == tenant_id).first()
        )


def helper_create_db_workflow_rule(tenant_id: str, payload: WorkflowRuleCreateRequest) -> tuple[dict[str, Any], bool]:
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
            if str(existing_action.get("type", "")).strip().lower() == payload.action.strip().lower():
                return (helper_workflow_rule_to_dict(existing), True)
        obj = WorkflowRule(
            tenant_id=tenant_id,
            name=payload.name,
            trigger=payload.trigger,
            conditions=payload.conditions,
            actions={"type": payload.action, "params": payload.action_params},
            enabled=payload.enabled,
            data={"run_count": 0, "last_triggered_at": None, "source": "api"},
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return (helper_workflow_rule_to_dict(obj), False)


def helper_list_db_workflow_rules(tenant_id: str) -> list[dict[str, Any]]:
    with get_db_session() as session:
        rows = (
            session.query(WorkflowRule)
            .filter(WorkflowRule.tenant_id == tenant_id)
            .order_by(WorkflowRule.created_at.desc())
            .all()
        )
        return [helper_workflow_rule_to_dict(row) for row in rows]


def helper_trigger_db_workflow_rule(rule_id: int, tenant_id: str, triggered_at: str) -> dict[str, Any] | None:
    now_dt = datetime.fromisoformat(triggered_at)
    with get_db_session() as session:
        obj = (
            session.query(WorkflowRule).filter(WorkflowRule.id == rule_id, WorkflowRule.tenant_id == tenant_id).first()
        )
        if obj is None:
            return None
        data = dict(obj.data or {})
        run_count = int(data.get("run_count", 0)) + 1
        data["run_count"] = run_count
        data["last_triggered_at"] = triggered_at
        obj.data = data
        execution = WorkflowExecution(
            tenant_id=tenant_id,
            workflow_id=obj.id,
            trigger_type=obj.trigger,
            trigger_entity_id=None,
            status="completed",
            started_at=now_dt,
            completed_at=now_dt,
            steps_executed=[
                {"step": "workflow_rule_triggered", "action": dict(obj.actions or {}), "completed_at": triggered_at}
            ],
            current_step_id="workflow_rule_triggered",
            result={"triggered_at": triggered_at, "run_count": run_count},
            error_message=None,
            data={"source": "crm_router"},
        )
        session.add(execution)
        session.commit()
        session.refresh(obj)
        return helper_workflow_rule_to_dict(obj)


def helper_activity_to_dict(obj: Activity) -> dict[str, Any]:
    d = dict(obj.data or {})
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "type": obj.type,
        "subject": d.get("subject", obj.description),
        "body": obj.description,
        "contact_id": obj.contact_id,
        "deal_id": obj.deal_id,
        "source": d.get("source", "api"),
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }


def helper_create_db_activity(tenant_id: str, payload: ActivityCreateRequest) -> dict[str, Any]:
    with get_db_session() as session:
        obj = Activity(
            tenant_id=tenant_id,
            type=payload.type,
            contact_id=payload.contact_id or 0,
            deal_id=payload.deal_id,
            description=payload.body,
            data={"subject": payload.subject, "source": "api"},
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return helper_activity_to_dict(obj)


def helper_list_db_activities(
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
        return ([helper_activity_to_dict(r) for r in rows], total)


def helper_lead_to_dict(obj: Lead) -> dict[str, Any]:
    d = dict(obj.data or {})
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "title": obj.title,
        "contact_id": obj.contact_id,
        "company_id": obj.company_id,
        "source": obj.source,
        "estimated_value": obj.estimated_value,
        "status": obj.status,
        "score": obj.score,
        "assigned_to": obj.assigned_to,
        "notes": d.get("notes", ""),
        "converted_deal_id": d.get("converted_deal_id"),
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }


def helper_create_db_lead(tenant_id: str, payload: LeadCreateRequest) -> dict[str, Any]:
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
            data={"notes": payload.notes},
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return helper_lead_to_dict(obj)


def helper_find_duplicate_db_lead(tenant_id: str, payload: LeadCreateRequest) -> dict[str, Any] | None:
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
        created_at = existing.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - created_at > timedelta(minutes=5):
            return None
        return helper_lead_to_dict(existing)


def helper_list_db_leads(
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
            query = query.filter(Lead.title.ilike(f"%{q}%"))
        total = query.count()
        rows = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
        return ([helper_lead_to_dict(r) for r in rows], total)


def helper_get_db_lead(lead_id: int, tenant_id: str) -> Lead | None:
    with get_db_session() as session:
        return session.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()


def helper_get_db_ticket(ticket_id: int, tenant_id: str) -> Ticket | None:
    with get_db_session() as session:
        return session.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id).first()
