"""Crm use cases: task to dict."""

from ....database import get_db_session
from ....models import Contact
from ....models import Task
from ....models import Ticket
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import ContactDedupeRequest
from ..schemas import TaskCreateRequest
from ..schemas import TicketCreateRequest
from .contact_to_dict import helper_contact_to_dict
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from sqlalchemy import func
from typing import Any


def helper_task_to_dict(obj: Task) -> dict[str, Any]:
    d = dict(obj.data or {})
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "title": obj.title,
        "description": d.get("description", ""),
        "contact_id": obj.related_contact_id,
        "deal_id": d.get("deal_id"),
        "due_date": obj.due_date,
        "priority": obj.priority,
        "assigned_to": obj.assigned_to,
        "type": d.get("type", "task"),
        "status": obj.status,
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }


def helper_create_db_task(tenant_id: str, payload: TaskCreateRequest) -> dict[str, Any]:
    with get_db_session() as session:
        obj = Task(
            tenant_id=tenant_id,
            title=payload.title,
            status="open",
            priority=payload.priority,
            assigned_to=payload.assigned_to,
            due_date=payload.due_date,
            related_contact_id=payload.contact_id,
            data={"description": payload.description, "deal_id": payload.deal_id, "type": payload.type},
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return helper_task_to_dict(obj)


def helper_find_duplicate_db_task(tenant_id: str, payload: TaskCreateRequest) -> dict[str, Any] | None:
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
        return helper_task_to_dict(existing)


def helper_list_db_tasks(
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
        result = [helper_task_to_dict(r) for r in rows]
        if deal_id is not None:
            result = [t for t in result if t.get("deal_id") == deal_id]
        return (result, total)


def helper_ticket_to_dict(obj: Ticket) -> dict[str, Any]:
    d = dict(obj.data or {})
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "ticket_number": obj.ticket_number,
        "subject": obj.subject,
        "description": obj.description,
        "contact_id": obj.contact_id,
        "priority": obj.priority,
        "channel": obj.channel,
        "status": obj.status,
        "assigned_to": obj.assigned_to,
        "escalated": obj.escalated,
        "resolution": obj.resolution,
        "tags": obj.tags if isinstance(obj.tags, list) else [],
        "first_response_deadline": d.get("first_response_deadline"),
        "resolution_deadline": d.get("resolution_deadline"),
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }


def helper_create_db_ticket(
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
            status="open",
            tags=payload.tags,
            data={"first_response_deadline": first_response_deadline, "resolution_deadline": resolution_deadline},
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return helper_ticket_to_dict(obj)


def helper_list_db_tickets(
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
        return ([helper_ticket_to_dict(r) for r in rows], total)


def helper_dedupe_contacts_impl(
    runtime: ContextRuntime, payload: ContactDedupeRequest, auth: AuthDep
) -> dict[str, Any]:
    with runtime.lock:
        tenant_mem_contacts = [c for c in runtime.contacts_memory if str(c.get("tenant_id", "")) == str(auth.tenant_id)]
    if tenant_mem_contacts:
        groups: dict[str, list[dict[str, Any]]] = {}
        for contact in tenant_mem_contacts:
            email = str(contact.get("email", "")).strip().lower()
            if not email:
                continue
            groups.setdefault(email, []).append(contact)
        duplicate_groups = [group for group in groups.values() if len(group) > 1]
        merge_preview: list[dict[str, Any]] = []
        merged_contacts = 0
        if not payload.dry_run:
            duplicate_ids_to_remove: set[int] = set()
        with runtime.lock:
            for group in duplicate_groups:
                group.sort(key=lambda item: int(item.get("id", 0)))
                canonical = group[0]
                duplicates = group[1:]
                duplicate_ids = [int(item.get("id", 0)) for item in duplicates]
                if payload.dry_run:
                    merge_preview.append({"canonical_id": int(canonical.get("id", 0)), "duplicate_ids": duplicate_ids})
                    continue
                canonical_tags = {str(tag) for tag in canonical.get("tags", []) if isinstance(tag, str)}
                for dup in duplicates:
                    for tag in dup.get("tags", []):
                        if isinstance(tag, str) and tag:
                            canonical_tags.add(tag)
                    if not canonical.get("phone") and dup.get("phone"):
                        canonical["phone"] = dup.get("phone")
                    if not canonical.get("company") and dup.get("company"):
                        canonical["company"] = dup.get("company")
                canonical["tags"] = sorted(canonical_tags)
                canonical["updated_at"] = datetime.now(UTC).isoformat()
                canonical_id = int(canonical.get("id", 0))
                for deal in runtime.deals_memory:
                    if deal.get("tenant_id") != auth.tenant_id:
                        continue
                    if int(deal.get("contact_id") or 0) in duplicate_ids:
                        deal["contact_id"] = canonical_id
                for activity in runtime.activities_memory:
                    if activity.get("tenant_id") != auth.tenant_id:
                        continue
                    if int(activity.get("contact_id") or 0) in duplicate_ids:
                        activity["contact_id"] = canonical_id
                duplicate_ids_to_remove.update(duplicate_ids)
                merged_contacts += len(duplicates)
            if not payload.dry_run and duplicate_ids_to_remove:
                runtime.contacts_memory[:] = [
                    c
                    for c in runtime.contacts_memory
                    if not (
                        str(c.get("tenant_id", "")) == str(auth.tenant_id)
                        and int(c.get("id", 0)) in duplicate_ids_to_remove
                    )
                ]
        helper_audit(runtime, auth.tenant_id, "crm_contacts_deduped", merged_contacts)
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "dry_run": payload.dry_run,
            "duplicate_group_count": len(duplicate_groups),
            "merged_contacts": 0 if payload.dry_run else merged_contacts,
            "merge_preview": merge_preview[:50],
        }
    with get_db_session() as session:
        tenant_contacts = [
            helper_contact_to_dict(contact)
            for contact in session.query(Contact).filter(Contact.tenant_id == auth.tenant_id).all()
        ]
        groups: dict[str, list[dict[str, Any]]] = {}
        for contact in tenant_contacts:
            email = str(contact.get("email", "")).strip().lower()
            if not email:
                continue
            groups.setdefault(email, []).append(contact)
        duplicate_groups = [group for group in groups.values() if len(group) > 1]
        merge_preview: list[dict[str, Any]] = []
        merged_contacts = 0
        for group in duplicate_groups:
            group.sort(key=lambda item: int(item.get("id", 0)))
            canonical = group[0]
            duplicates = group[1:]
            duplicate_ids = [int(item.get("id", 0)) for item in duplicates]
            if payload.dry_run:
                merge_preview.append({"canonical_id": int(canonical.get("id", 0)), "duplicate_ids": duplicate_ids})
                continue
            canonical_tags = {str(tag) for tag in canonical.get("tags", []) if isinstance(tag, str)}
            for dup in duplicates:
                for tag in dup.get("tags", []):
                    if isinstance(tag, str) and tag:
                        canonical_tags.add(tag)
                if not canonical.get("phone") and dup.get("phone"):
                    canonical["phone"] = dup.get("phone")
                if not canonical.get("company") and dup.get("company"):
                    canonical["company"] = dup.get("company")
            canonical["tags"] = sorted(canonical_tags)
            canonical["updated_at"] = datetime.now(UTC).isoformat()
            canonical_row = (
                session.query(Contact).filter_by(id=int(canonical.get("id", 0)), tenant_id=auth.tenant_id).first()
            )
            if canonical_row is not None:
                canonical_data = dict(canonical_row.data or {})
                canonical_data["tags"] = canonical["tags"]
                canonical_data["properties"] = canonical.get("properties", canonical_data.get("properties", {}))
                canonical_row.phone = str(canonical.get("phone", "") or canonical_row.phone)
                canonical_row.company = str(canonical.get("company", "") or canonical_row.company)
                canonical_row.data = canonical_data
            canonical_id = int(canonical.get("id", 0))
            with runtime.lock:
                for deal in runtime.deals_memory:
                    if deal.get("tenant_id") != auth.tenant_id:
                        continue
                    if int(deal.get("contact_id") or 0) in duplicate_ids:
                        deal["contact_id"] = canonical_id
                for activity in runtime.activities_memory:
                    if activity.get("tenant_id") != auth.tenant_id:
                        continue
                    if int(activity.get("contact_id") or 0) in duplicate_ids:
                        activity["contact_id"] = canonical_id
            if duplicate_ids:
                session.query(Contact).filter(
                    Contact.tenant_id == auth.tenant_id, Contact.id.in_(duplicate_ids)
                ).delete(synchronize_session=False)
            merged_contacts += len(duplicates)
    helper_audit(runtime, auth.tenant_id, "crm_contacts_deduped", merged_contacts)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "dry_run": payload.dry_run,
        "duplicate_group_count": len(duplicate_groups),
        "merged_contacts": 0 if payload.dry_run else merged_contacts,
        "merge_preview": merge_preview[:50],
    }


def helper_next_full_backup_utc(runtime: ContextRuntime, config: dict[str, Any], now: datetime) -> datetime:
    target_weekday = runtime.weekday_map.get(str(config.get("full_backup_weekday", "sunday")).lower(), 6)
    target_hour = int(config.get("full_backup_hour_utc", 3))
    days_ahead = (target_weekday - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(minute=0, second=0, microsecond=0, hour=target_hour)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def helper_get_backup_config(runtime: ContextRuntime, tenant_id: str) -> dict[str, Any]:
    existing = next(
        (
            row
            for row in runtime.backup_snapshots_memory
            if row.get("tenant_id") == tenant_id and row.get("type") == "config"
        ),
        None,
    )
    now_iso = datetime.now(UTC).isoformat()
    if existing is not None:
        return existing
    config = {
        "id": len(runtime.backup_snapshots_memory) + 1,
        "tenant_id": tenant_id,
        "type": "config",
        "incremental_minutes": 5,
        "full_backup_weekday": "sunday",
        "full_backup_hour_utc": 3,
        "retention_days": 30,
        "enabled": True,
        "updated_at": now_iso,
    }
    runtime.backup_snapshots_memory.append(config)
    return config


def helper_audit(runtime: ContextRuntime, tenant_id: str, action: str, resource_id: int | None = None) -> None:
    with runtime.lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "resource_id": resource_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "crm-router",
            }
        )
