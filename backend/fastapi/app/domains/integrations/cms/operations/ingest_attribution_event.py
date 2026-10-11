"""Integrations/Cms use cases: ingest attribution event."""

from __future__ import annotations
from .....database import get_db_session
from .....models import Activity
from .....models import Contact
from .....models import Deal
from .....models import Task
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import CmsAttributionEventRequest
from .audit import helper_audit
from .audit import helper_enroll_contact_in_sequence
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import func
from typing import Any


def execute_ingest_attribution_event(
    runtime: ContextRuntime, payload: CmsAttributionEventRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:attribution:events:create", 300, 60)
    normalized_email = payload.contact_email.strip().lower()
    with runtime.lock:
        link = next(
            (
                l
                for l in runtime.cms_attribution_links_memory
                if l.get("id") == payload.attribution_link_id and l.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if link is None:
            raise HTTPException(status_code=404, detail="Attribution link not found.")
        event: dict[str, Any] = {
            "id": len(runtime.cms_attribution_events_memory) + 1,
            "tenant_id": auth.tenant_id,
            "attribution_link_id": payload.attribution_link_id,
            "campaign": link.get("campaign", ""),
            "event_type": payload.event_type,
            "visitor_id": payload.visitor_id,
            "contact_email": normalized_email,
            "value": payload.value,
            "created_at": datetime.now(UTC).isoformat(),
        }
        runtime.cms_attribution_events_memory.append(event)
    crm_bridge: dict[str, Any] = {
        "synced": False,
        "contact_created": False,
        "contact_id": None,
        "activity_id": None,
        "deal_created": False,
        "deal_id": None,
    }
    should_sync = payload.sync_to_crm and bool(normalized_email)
    if should_sync:
        with get_db_session() as session:
            contact = (
                session.query(Contact)
                .filter(Contact.tenant_id == auth.tenant_id, func.lower(Contact.email) == normalized_email)
                .first()
            )
            if contact is None:
                stage_map = {
                    "visit": "lead",
                    "lead": "lead",
                    "mql": "mql",
                    "sql": "sql",
                    "opportunity": "opportunity",
                    "customer": "customer",
                }
                contact = Contact(
                    tenant_id=auth.tenant_id,
                    email=normalized_email,
                    first_name=payload.contact_first_name,
                    last_name=payload.contact_last_name,
                    company=payload.company,
                    lifecycle_stage=stage_map.get(payload.event_type, "lead"),
                    score=0,
                    data={
                        "source": "cms_attribution",
                        "campaign": link.get("campaign", ""),
                        "utm": link.get("utm", {}),
                    },
                )
                session.add(contact)
                session.flush()
                crm_bridge["contact_created"] = True
            else:
                updated_data = dict(contact.data or {})
                updated_data["campaign"] = link.get("campaign", "")
                updated_data["utm"] = link.get("utm", {})
                contact.data = updated_data
            crm_bridge["contact_id"] = int(contact.id)
            activity = Activity(
                tenant_id=auth.tenant_id,
                type="cms_attribution",
                contact_id=int(contact.id),
                deal_id=None,
                description=f"CMS attribution event: {payload.event_type}",
                data={
                    "subject": "CMS Attribution Event",
                    "event_type": payload.event_type,
                    "campaign": link.get("campaign", ""),
                    "attribution_link_id": payload.attribution_link_id,
                    "value": payload.value,
                    "source": "cms-attribution",
                },
            )
            session.add(activity)
            session.flush()
            crm_bridge["activity_id"] = int(activity.id)
            should_create_deal = payload.create_deal or (
                payload.event_type in {"opportunity", "customer"} and (payload.value > 0 or payload.deal_value > 0)
            )
            if should_create_deal:
                deal_value = float(payload.deal_value if payload.deal_value > 0 else payload.value)
                stage = payload.deal_stage.strip().lower() or "qualified"
                if stage not in {"prospect", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"}:
                    stage = "qualified"
                deal = Deal(
                    tenant_id=auth.tenant_id,
                    title=payload.deal_title.strip() or "CMS Attributed Opportunity",
                    value=deal_value,
                    currency="USD",
                    stage=stage,
                    contact_id=int(contact.id),
                    company_id=None,
                    close_date=None,
                    data={
                        "source": "cms_attribution",
                        "campaign": link.get("campaign", ""),
                        "attribution_link_id": payload.attribution_link_id,
                        "probability": 25 if stage == "qualified" else 10,
                    },
                )
                session.add(deal)
                session.flush()
                crm_bridge["deal_created"] = True
                crm_bridge["deal_id"] = int(deal.id)
            crm_bridge["synced"] = True
    automation_executions: list[dict[str, Any]] = []
    with runtime.lock:
        rules = [
            r.copy()
            for r in runtime.cms_attribution_rules_memory
            if r.get("tenant_id") == auth.tenant_id and bool(r.get("enabled", True))
        ]
    for rule in rules:
        rule_campaign = str(rule.get("campaign") or "").strip().lower()
        event_campaign = str(link.get("campaign") or "").strip().lower()
        if rule_campaign and rule_campaign != event_campaign:
            continue
        if str(rule.get("trigger_event_type") or "") != payload.event_type:
            continue
        if float(payload.value) < float(rule.get("min_value", 0.0) or 0.0):
            continue
        execution: dict[str, Any] = {
            "id": 0,
            "tenant_id": auth.tenant_id,
            "rule_id": int(rule.get("id", 0) or 0),
            "event_id": int(event.get("id", 0) or 0),
            "campaign": link.get("campaign", ""),
            "event_type": payload.event_type,
            "actions": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
        contact_id = crm_bridge.get("contact_id")
        sequence_id_raw = rule.get("auto_enroll_sequence_id")
        if contact_id is not None and sequence_id_raw is not None:
            try:
                sequence_id = int(sequence_id_raw)
            except (TypeError, ValueError):
                sequence_id = 0
            if sequence_id > 0:
                enrolled_now, snapshot = helper_enroll_contact_in_sequence(
                    runtime, auth.tenant_id, sequence_id, int(contact_id)
                )
                execution["actions"].append(
                    {
                        "action": "sequence_enroll",
                        "sequence_id": sequence_id,
                        "contact_id": int(contact_id),
                        "success": snapshot is not None,
                        "enrolled_now": enrolled_now,
                    }
                )
        if bool(rule.get("create_deal")) and contact_id is not None and (not crm_bridge.get("deal_created")):
            stage = str(rule.get("deal_stage") or "qualified").strip().lower()
            if stage not in {"prospect", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"}:
                stage = "qualified"
            with get_db_session() as session:
                deal = Deal(
                    tenant_id=auth.tenant_id,
                    title=str(rule.get("deal_title") or "CMS Attribution Rule Opportunity"),
                    value=float(payload.value),
                    currency="USD",
                    stage=stage,
                    contact_id=int(contact_id),
                    company_id=None,
                    close_date=None,
                    data={
                        "source": "cms_attribution_rule",
                        "campaign": link.get("campaign", ""),
                        "attribution_link_id": payload.attribution_link_id,
                        "rule_id": int(rule.get("id", 0) or 0),
                        "probability": 25 if stage == "qualified" else 10,
                    },
                )
                session.add(deal)
                session.flush()
                execution["actions"].append(
                    {
                        "action": "create_deal",
                        "success": True,
                        "deal_id": int(deal.id),
                        "value": float(payload.value),
                        "stage": stage,
                    }
                )
                crm_bridge["deal_created"] = True
                crm_bridge["deal_id"] = int(deal.id)
        stage_target = str(rule.get("transition_deal_stage_to") or "").strip().lower()
        if contact_id is not None and stage_target:
            if stage_target not in {"prospect", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"}:
                stage_target = "qualified"
            probability_map = {
                "prospect": 10,
                "qualified": 25,
                "proposal": 50,
                "negotiation": 75,
                "closed_won": 100,
                "closed_lost": 0,
            }
            with get_db_session() as session:
                deal_obj: Deal | None = None
                deal_id_raw = crm_bridge.get("deal_id")
                deal_id = int(deal_id_raw) if str(deal_id_raw).strip().isdigit() else 0
                if deal_id > 0:
                    deal_obj = session.query(Deal).filter(Deal.id == deal_id, Deal.tenant_id == auth.tenant_id).first()
                if deal_obj is None:
                    deal_obj = (
                        session.query(Deal)
                        .filter(Deal.tenant_id == auth.tenant_id, Deal.contact_id == int(contact_id))
                        .order_by(Deal.id.desc())
                        .first()
                    )
                if deal_obj is not None:
                    deal_obj.stage = stage_target
                    deal_data = dict(deal_obj.data or {})
                    deal_data["probability"] = probability_map.get(stage_target, 25)
                    deal_data["last_stage_transition_source"] = "cms_attribution_rule"
                    deal_data["last_stage_transition_rule_id"] = int(rule.get("id", 0) or 0)
                    deal_data["last_stage_transition_event_id"] = int(event.get("id", 0) or 0)
                    deal_obj.data = deal_data
                    session.commit()
                    session.refresh(deal_obj)
                    crm_bridge["deal_id"] = int(deal_obj.id)
                    execution["actions"].append(
                        {
                            "action": "transition_deal_stage",
                            "success": True,
                            "deal_id": int(deal_obj.id),
                            "stage": stage_target,
                        }
                    )
                else:
                    execution["actions"].append(
                        {
                            "action": "transition_deal_stage",
                            "success": False,
                            "reason": "no_deal_found",
                            "stage": stage_target,
                        }
                    )
        if bool(rule.get("create_followup_task")) and contact_id is not None:
            task_priority = str(rule.get("task_priority") or "medium").strip().lower()
            if task_priority not in {"low", "medium", "high"}:
                task_priority = "medium"
            due_days_raw = rule.get("task_due_in_days", 2)
            try:
                due_days = int(due_days_raw)
            except (TypeError, ValueError):
                due_days = 2
            due_days = max(0, min(due_days, 60))
            due_date = (datetime.now(UTC) + timedelta(days=due_days)).date().isoformat()
            task_title = (
                str(rule.get("task_title") or "CMS Attribution Follow-up").strip() or "CMS Attribution Follow-up"
            )
            assigned_to = str(rule.get("task_assigned_to") or "").strip()
            related_deal_id = crm_bridge.get("deal_id")
            related_deal_id_value = int(related_deal_id) if str(related_deal_id).strip().isdigit() else None
            with get_db_session() as session:
                task = Task(
                    tenant_id=auth.tenant_id,
                    title=task_title,
                    status="open",
                    priority=task_priority,
                    assigned_to=assigned_to,
                    due_date=due_date,
                    related_contact_id=int(contact_id),
                    data={
                        "source": "cms_attribution_rule",
                        "campaign": link.get("campaign", ""),
                        "rule_id": int(rule.get("id", 0) or 0),
                        "event_id": int(event.get("id", 0) or 0),
                        "related_deal_id": related_deal_id_value,
                    },
                )
                session.add(task)
                session.flush()
                execution["actions"].append(
                    {
                        "action": "create_task",
                        "success": True,
                        "task_id": int(task.id),
                        "priority": task_priority,
                        "due_date": due_date,
                        "related_contact_id": int(contact_id),
                        "related_deal_id": related_deal_id_value,
                    }
                )
        with runtime.lock:
            execution["id"] = len(runtime.cms_attribution_automation_runs_memory) + 1
            runtime.cms_attribution_automation_runs_memory.append(execution)
        automation_executions.append(execution)
    helper_audit(runtime, auth.tenant_id, "cms_attribution_event_ingested", event["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "event": event,
        "crm_bridge": crm_bridge,
        "automation": {"matched_rules": len(automation_executions), "executions": automation_executions},
    }
