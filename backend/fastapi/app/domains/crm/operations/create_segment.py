"""Crm use cases: create segment."""

from ..constants import AuthDep
from ..constants import INVOICE_NOT_FOUND
from ..constants import QUOTE_NOT_FOUND
from ..constants import SEQUENCE_NOT_FOUND
from ..runtime import ContextRuntime
from ..schemas import CRMInvoiceCreateRequest
from ..schemas import CRMInvoiceUpdateRequest
from ..schemas import EmailSequenceCreateRequest
from ..schemas import NoteCreateRequest
from ..schemas import QuoteCreateRequest
from ..schemas import SegmentCreateRequest
from ..services.apply_segment_filters import _apply_segment_filters
from .get_live_sync_state import helper_get_live_sync_state
from .task_to_dict import helper_audit
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_create_segment(runtime: ContextRuntime, payload: SegmentCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:segments:create", 60, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_segment: dict[str, Any] | None = None
    created_segment: dict[str, Any] | None = None
    with runtime.lock:
        existing = next(
            (
                s
                for s in runtime.segments_memory
                if s.get("tenant_id") == auth.tenant_id
                and str(s.get("name", "")).strip().lower() == payload.name.strip().lower()
                and (dict(s.get("filters", {})) == payload.filters)
            ),
            None,
        )
        if existing is not None:
            duplicate_segment = existing.copy()
        else:
            members = _apply_segment_filters(auth.tenant_id, payload.filters, runtime.contacts_memory)
            segment: dict[str, Any] = {
                "id": len(runtime.segments_memory) + 1,
                "tenant_id": auth.tenant_id,
                "name": payload.name,
                "description": payload.description,
                "filters": payload.filters,
                "member_count": len(members),
                "created_at": now,
                "updated_at": now,
            }
            runtime.segments_memory.append(segment)
            created_segment = segment
    if duplicate_segment is not None:
        helper_audit(runtime, auth.tenant_id, "crm_segment_reused", int(duplicate_segment.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "segment": duplicate_segment,
            "duplicate": True,
            "created": False,
        }
    if created_segment is None:
        raise HTTPException(status_code=500, detail="Failed to create segment.")
    helper_audit(runtime, auth.tenant_id, "crm_segment_created", int(created_segment["id"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "segment": created_segment,
        "duplicate": False,
        "created": True,
    }


def execute_create_note(runtime: ContextRuntime, payload: NoteCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:notes:create", 120, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_note: dict[str, Any] | None = None
    created_note: dict[str, Any] | None = None
    with runtime.lock:
        existing = next(
            (
                n
                for n in runtime.notes_memory
                if n.get("tenant_id") == auth.tenant_id
                and str(n.get("body", "")).strip() == payload.body.strip()
                and (n.get("contact_id") == payload.contact_id)
                and (n.get("deal_id") == payload.deal_id)
                and (n.get("company_id") == payload.company_id)
                and (bool(n.get("pinned", False)) == payload.pinned)
            ),
            None,
        )
        if existing is not None:
            duplicate_note = existing.copy()
        else:
            note: dict[str, Any] = {
                "id": len(runtime.notes_memory) + 1,
                "tenant_id": auth.tenant_id,
                "body": payload.body,
                "contact_id": payload.contact_id,
                "deal_id": payload.deal_id,
                "company_id": payload.company_id,
                "pinned": payload.pinned,
                "created_at": now,
            }
            runtime.notes_memory.append(note)
            created_note = note
    if duplicate_note is not None:
        helper_audit(runtime, auth.tenant_id, "crm_note_reused", int(duplicate_note.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "note": duplicate_note,
            "duplicate": True,
            "created": False,
        }
    if created_note is None:
        raise HTTPException(status_code=500, detail="Failed to create note.")
    helper_audit(runtime, auth.tenant_id, "crm_note_created", int(created_note["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "note": created_note, "duplicate": False, "created": True}


def execute_list_notes(
    runtime: ContextRuntime,
    auth: AuthDep,
    contact_id: Annotated[int | None, Query(ge=1)] = None,
    deal_id: Annotated[int | None, Query(ge=1)] = None,
    company_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:notes:list", 240, 60)
    with runtime.lock:
        items = [n.copy() for n in runtime.notes_memory if n.get("tenant_id") == auth.tenant_id]
    if contact_id is not None:
        items = [n for n in items if n.get("contact_id") == contact_id]
    if deal_id is not None:
        items = [n for n in items if n.get("deal_id") == deal_id]
    if company_id is not None:
        items = [n for n in items if n.get("company_id") == company_id]
    items.sort(key=lambda n: (not bool(n.get("pinned")), str(n.get("created_at", ""))), reverse=False)
    total = len(items)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[offset : offset + limit]),
        "total": total,
        "notes": items[offset : offset + limit],
    }


def execute_create_quote(runtime: ContextRuntime, payload: QuoteCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:quotes:create", 60, 60)
    now = datetime.now(UTC).isoformat()
    subtotal = sum((item.quantity * item.unit_price * (1 - item.discount_pct / 100.0) for item in payload.line_items))
    duplicate_quote: dict[str, Any] | None = None
    created_quote: dict[str, Any] | None = None
    line_items = [li.model_dump() for li in payload.line_items]
    with runtime.lock:
        existing = next(
            (
                q
                for q in runtime.quotes_memory
                if q.get("tenant_id") == auth.tenant_id
                and str(q.get("title", "")).strip().lower() == payload.title.strip().lower()
                and (q.get("contact_id") == payload.contact_id)
                and (q.get("deal_id") == payload.deal_id)
                and (str(q.get("currency", "")).strip().lower() == payload.currency.strip().lower())
                and (list(q.get("line_items", [])) == line_items)
                and (str(q.get("status", "")).strip().lower() == "draft")
            ),
            None,
        )
        if existing is not None:
            duplicate_quote = existing.copy()
        else:
            quote_number = f"QUO-{len(runtime.quotes_memory) + 1:05d}"
            quote: dict[str, Any] = {
                "id": len(runtime.quotes_memory) + 1,
                "tenant_id": auth.tenant_id,
                "quote_number": quote_number,
                "title": payload.title,
                "contact_id": payload.contact_id,
                "deal_id": payload.deal_id,
                "line_items": line_items,
                "subtotal": round(subtotal, 2),
                "currency": payload.currency,
                "valid_until": payload.valid_until,
                "notes": payload.notes,
                "status": "draft",
                "created_at": now,
                "updated_at": now,
            }
            runtime.quotes_memory.append(quote)
            created_quote = quote
    if duplicate_quote is not None:
        helper_audit(runtime, auth.tenant_id, "crm_quote_reused", int(duplicate_quote.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "quote": duplicate_quote,
            "duplicate": True,
            "created": False,
        }
    if created_quote is None:
        raise HTTPException(status_code=500, detail="Failed to create quote.")
    helper_audit(runtime, auth.tenant_id, "crm_quote_created", int(created_quote["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "quote": created_quote, "duplicate": False, "created": True}


def execute_list_quotes(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:quotes:list", 180, 60)
    with runtime.lock:
        items = [q.copy() for q in runtime.quotes_memory if q.get("tenant_id") == auth.tenant_id]
    if (status or "").strip():
        items = [q for q in items if str(q.get("status", "")) == status.strip()]
    items.sort(key=lambda q: str(q.get("created_at", "")), reverse=True)
    total = len(items)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[offset : offset + limit]),
        "total": total,
        "quotes": items[offset : offset + limit],
    }


def execute_accept_quote(runtime: ContextRuntime, quote_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:quotes:accept", 60, 60)
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        item = next(
            (q for q in runtime.quotes_memory if q.get("id") == quote_id and q.get("tenant_id") == auth.tenant_id), None
        )
        if item is None:
            raise HTTPException(status_code=404, detail=QUOTE_NOT_FOUND)
        item["status"] = "accepted"
        item["accepted_at"] = now
        item["updated_at"] = now
        invoice: dict[str, Any] = {
            "id": len(runtime.crm_invoices_memory) + 1,
            "tenant_id": auth.tenant_id,
            "invoice_number": f"INV-{len(runtime.crm_invoices_memory) + 1:05d}",
            "title": str(item.get("title", "Invoice")),
            "contact_id": item.get("contact_id"),
            "deal_id": item.get("deal_id"),
            "quote_id": quote_id,
            "amount": float(item.get("subtotal", 0.0)),
            "currency": str(item.get("currency", "USD")),
            "status": "pending",
            "due_date": None,
            "created_at": now,
            "updated_at": now,
        }
        runtime.crm_invoices_memory.append(invoice)
        snapshot = item.copy()
    helper_audit(runtime, auth.tenant_id, "crm_quote_accepted", quote_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "quote": snapshot, "invoice": invoice}


def execute_create_invoice(runtime: ContextRuntime, payload: CRMInvoiceCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:invoices:create", 60, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_invoice: dict[str, Any] | None = None
    created_invoice: dict[str, Any] | None = None
    with runtime.lock:
        existing = next(
            (
                i
                for i in runtime.crm_invoices_memory
                if i.get("tenant_id") == auth.tenant_id
                and str(i.get("title", "")).strip().lower() == payload.title.strip().lower()
                and (i.get("contact_id") == payload.contact_id)
                and (i.get("deal_id") == payload.deal_id)
                and (i.get("quote_id") == payload.quote_id)
                and (float(i.get("amount", 0.0)) == payload.amount)
                and (str(i.get("currency", "")).strip().lower() == payload.currency.strip().lower())
                and (str(i.get("status", "")).strip().lower() == "pending")
            ),
            None,
        )
        if existing is not None:
            duplicate_invoice = existing.copy()
        else:
            invoice_number = f"INV-{len(runtime.crm_invoices_memory) + 1:05d}"
            inv: dict[str, Any] = {
                "id": len(runtime.crm_invoices_memory) + 1,
                "tenant_id": auth.tenant_id,
                "invoice_number": invoice_number,
                "title": payload.title,
                "contact_id": payload.contact_id,
                "deal_id": payload.deal_id,
                "quote_id": payload.quote_id,
                "amount": payload.amount,
                "currency": payload.currency,
                "due_date": payload.due_date,
                "notes": payload.notes,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }
            runtime.crm_invoices_memory.append(inv)
            created_invoice = inv
    if duplicate_invoice is not None:
        helper_audit(runtime, auth.tenant_id, "crm_invoice_reused", int(duplicate_invoice.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "invoice": duplicate_invoice,
            "duplicate": True,
            "created": False,
        }
    if created_invoice is None:
        raise HTTPException(status_code=500, detail="Failed to create invoice.")
    helper_audit(runtime, auth.tenant_id, "crm_invoice_created", int(created_invoice["id"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "invoice": created_invoice,
        "duplicate": False,
        "created": True,
    }


def execute_list_invoices(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:invoices:list", 180, 60)
    with runtime.lock:
        items = [i.copy() for i in runtime.crm_invoices_memory if i.get("tenant_id") == auth.tenant_id]
    if (status or "").strip():
        items = [i for i in items if str(i.get("status", "")) == status.strip()]
    items.sort(key=lambda i: str(i.get("created_at", "")), reverse=True)
    total = len(items)
    total_outstanding = round(sum((float(i.get("amount", 0)) for i in items if i.get("status") == "pending")), 2)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[offset : offset + limit]),
        "total": total,
        "total_outstanding": total_outstanding,
        "invoices": items[offset : offset + limit],
    }


def execute_update_invoice(
    runtime: ContextRuntime, invoice_id: int, payload: CRMInvoiceUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:invoices:update", 60, 60)
    with runtime.lock:
        item = next(
            (
                i
                for i in runtime.crm_invoices_memory
                if i.get("id") == invoice_id and i.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail=INVOICE_NOT_FOUND)
        if payload.status is not None:
            item["status"] = payload.status
        if payload.paid_at is not None:
            item["paid_at"] = payload.paid_at
        item["updated_at"] = datetime.now(UTC).isoformat()
        snapshot = item.copy()
    helper_audit(runtime, auth.tenant_id, "crm_invoice_updated", invoice_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "invoice": snapshot}


def execute_create_sequence(
    runtime: ContextRuntime, payload: EmailSequenceCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:sequences:create", 40, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_sequence: dict[str, Any] | None = None
    created_sequence: dict[str, Any] | None = None
    steps = [s.model_dump() for s in payload.steps]
    with runtime.lock:
        existing = next(
            (
                s
                for s in runtime.email_sequences_memory
                if s.get("tenant_id") == auth.tenant_id
                and str(s.get("name", "")).strip().lower() == payload.name.strip().lower()
                and (list(s.get("steps", [])) == steps)
            ),
            None,
        )
        if existing is not None:
            duplicate_sequence = existing.copy()
        else:
            seq: dict[str, Any] = {
                "id": len(runtime.email_sequences_memory) + 1,
                "tenant_id": auth.tenant_id,
                "name": payload.name,
                "description": payload.description,
                "steps": steps,
                "step_count": len(payload.steps),
                "enrollments": 0,
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
            runtime.email_sequences_memory.append(seq)
            created_sequence = seq
    if duplicate_sequence is not None:
        helper_audit(runtime, auth.tenant_id, "crm_sequence_reused", int(duplicate_sequence.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "sequence": duplicate_sequence,
            "duplicate": True,
            "created": False,
        }
    if created_sequence is None:
        raise HTTPException(status_code=500, detail="Failed to create email sequence.")
    helper_audit(runtime, auth.tenant_id, "crm_sequence_created", int(created_sequence["id"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "sequence": created_sequence,
        "duplicate": False,
        "created": True,
    }


def execute_enroll_in_sequence(runtime: ContextRuntime, seq_id: int, auth: AuthDep, contact_id: int) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:sequences:enroll", 60, 60)
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        seq = next(
            (
                s
                for s in runtime.email_sequences_memory
                if s.get("id") == seq_id and s.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if seq is None:
            raise HTTPException(status_code=404, detail=SEQUENCE_NOT_FOUND)
        seq["enrollments"] = int(seq.get("enrollments", 0)) + 1
        seq["updated_at"] = now
    helper_audit(runtime, auth.tenant_id, "crm_sequence_enrolled", seq_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "sequence_id": seq_id,
        "contact_id": contact_id,
        "enrolled_at": now,
    }


def execute_get_live_sync_status(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:ops:sync:get", 120, 60)
    with runtime.lock:
        state = helper_get_live_sync_state(runtime, auth.tenant_id).copy()
    return {"status": "ok", "tenant_id": auth.tenant_id, "sync": state}
