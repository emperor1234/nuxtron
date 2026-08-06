# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedFunction=false
"""
Sales Documents, Templates & Quotes (HubSpot Sales Hub §5.6)
NEW: Document library, quote builder, proposal tracker, e-signature.
Track opens, time-on-page, deal-linked quotes, approval workflow.
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

DOCUMENT_NOT_FOUND = 'Document not found.'
QUOTE_NOT_FOUND = 'Quote not found.'
DOC_TYPES = {'proposal', 'case_study', 'one_pager', 'deck', 'brochure', 'contract', 'template', 'other'}
QUOTE_STATUSES = {'draft', 'sent', 'viewed', 'accepted', 'declined', 'expired'}


class LineItemModel(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=1000)
    quantity: float = Field(default=1.0, gt=0)
    unit_price: float = Field(default=0.0, ge=0)
    discount_pct: float = Field(default=0.0, ge=0, le=100)
    tax_pct: float = Field(default=0.0, ge=0, le=100)


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    doc_type: str = Field(default='other', max_length=20)
    description: str = Field(default='', max_length=2000)
    content_url: str = Field(default='', max_length=500)
    content_body: str = Field(default='', max_length=100000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    is_template: bool = False


class DocumentShareRequest(BaseModel):
    recipient_email: str = Field(min_length=1, max_length=200)
    recipient_name: str = Field(default='', max_length=200)
    contact_id: str = Field(default='', max_length=100)
    deal_id: str = Field(default='', max_length=100)
    message: str = Field(default='', max_length=2000)
    expires_in_days: int = Field(default=30, ge=1, le=365)


class QuoteCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    deal_id: str = Field(default='', max_length=100)
    contact_id: str = Field(default='', max_length=100)
    company_name: str = Field(default='', max_length=200)
    recipient_email: str = Field(min_length=1, max_length=200)
    recipient_name: str = Field(default='', max_length=200)
    line_items: list[LineItemModel] = Field(default_factory=list, max_length=100)
    currency: str = Field(default='USD', max_length=3)
    valid_days: int = Field(default=30, ge=1, le=365)
    notes: str = Field(default='', max_length=5000)
    require_signature: bool = False
    payment_terms: str = Field(default='', max_length=200)


def create_documents_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    documents_memory: list[dict[str, Any]],
    document_views_memory: list[dict[str, Any]],
    quotes_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """NEW: Sales documents & quotes router — HubSpot Sales Hub §5.6."""
    router = APIRouter()
    _lock = threading.Lock()

    def _append_audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'documents-router',
            })

    def _calc_quote_totals(line_items: list[dict[str, Any]]) -> dict[str, float]:
        subtotal = 0.0
        discount_total = 0.0
        tax_total = 0.0
        for item in line_items:
            qty = float(item.get('quantity', 1))
            price = float(item.get('unit_price', 0))
            disc = float(item.get('discount_pct', 0)) / 100
            tax = float(item.get('tax_pct', 0)) / 100
            line = qty * price
            disc_amt = line * disc
            taxable = line - disc_amt
            tax_amt = taxable * tax
            subtotal += line
            discount_total += disc_amt
            tax_total += tax_amt
        total = subtotal - discount_total + tax_total
        return {
            'subtotal': round(subtotal, 2),
            'discount_total': round(discount_total, 2),
            'tax_total': round(tax_total, 2),
            'total': round(total, 2),
        }

    # ── Documents ─────────────────────────────────────────────────────────────

    @router.post('/documents', summary='Upload/create document')
    def create_document(payload: DocumentCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Add a document or template to the library."""
        enforce_rate_limit(f'{auth.tenant_id}:docs:create', 60, 60)
        doc_type = payload.doc_type.strip().lower()
        if doc_type not in DOC_TYPES:
            doc_type = 'other'
        with _lock:
            doc = {
                'id': len(documents_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title,
                'doc_type': doc_type,
                'description': payload.description,
                'content_url': payload.content_url,
                'content_body': payload.content_body,
                'tags': payload.tags,
                'is_template': payload.is_template,
                'view_count': 0,
                'share_count': 0,
                'avg_time_on_page_seconds': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            documents_memory.append(doc)
        _append_audit(auth.tenant_id, 'document_created', doc['id'])
        return {'status': 'ok', 'document': doc}

    @router.get('/documents', summary='List documents')
    def list_documents(
        auth: AuthDep,
        doc_type: Annotated[str | None, Query(max_length=20)] = None,
        is_template: Annotated[bool | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List documents in the library."""
        enforce_rate_limit(f'{auth.tenant_id}:docs:list', 120, 60)
        with _lock:
            items = [d.copy() for d in documents_memory if d.get('tenant_id') == auth.tenant_id]
        if doc_type:
            items = [d for d in items if d.get('doc_type') == doc_type]
        if is_template is not None:
            items = [d for d in items if bool(d.get('is_template')) == is_template]
        items.sort(key=lambda x: int(x.get('view_count', 0)), reverse=True)
        return {'status': 'ok', 'documents': items[offset:offset + limit], 'total': len(items)}

    @router.get('/documents/{document_id}', responses={404: {'description': DOCUMENT_NOT_FOUND}})
    def get_document(document_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a document and its engagement stats."""
        enforce_rate_limit(f'{auth.tenant_id}:docs:get', 120, 60)
        with _lock:
            doc = next((d.copy() for d in documents_memory
                        if d.get('id') == document_id and d.get('tenant_id') == auth.tenant_id), None)
            if doc is None:
                raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)
            views = [v.copy() for v in document_views_memory if v.get('document_id') == document_id]
        doc['recent_views'] = views[-20:]
        return {'status': 'ok', 'document': doc}

    @router.post('/documents/{document_id}/share', responses={404: {'description': DOCUMENT_NOT_FOUND}})
    def share_document(document_id: int, payload: DocumentShareRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Share a document link with a contact — tracking enabled."""
        enforce_rate_limit(f'{auth.tenant_id}:docs:share', 60, 60)
        shared_at = datetime.now(UTC)
        with _lock:
            doc = next((d for d in documents_memory
                        if d.get('id') == document_id and d.get('tenant_id') == auth.tenant_id), None)
            if doc is None:
                raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)
            doc['share_count'] = doc.get('share_count', 0) + 1
            share = {
                'id': len(document_views_memory) + 1,
                'tenant_id': auth.tenant_id,
                'document_id': document_id,
                'recipient_email': payload.recipient_email,
                'recipient_name': payload.recipient_name,
                'contact_id': payload.contact_id,
                'deal_id': payload.deal_id,
                'message': payload.message,
                'share_token': f'share-{document_id}-{len(document_views_memory) + 1}',
                'view_count': 0,
                'total_time_seconds': 0,
                'first_viewed_at': None,
                'last_viewed_at': None,
                'expires_at': (shared_at + timedelta(days=payload.expires_in_days)).isoformat(),
                'shared_at': shared_at.isoformat(),
            }
            document_views_memory.append(share)
        _append_audit(auth.tenant_id, 'document_shared', document_id)
        return {'status': 'ok', 'share': share, 'tracking_url': f'https://docs.app/view/{share["share_token"]}'}

    @router.delete('/documents/{document_id}', responses={404: {'description': DOCUMENT_NOT_FOUND}})
    def delete_document(document_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Delete a document from the library."""
        enforce_rate_limit(f'{auth.tenant_id}:docs:delete', 30, 60)
        with _lock:
            idx = next((i for i, d in enumerate(documents_memory)
                        if d.get('id') == document_id and d.get('tenant_id') == auth.tenant_id), None)
            if idx is None:
                raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)
            removed = documents_memory.pop(idx)
        _append_audit(auth.tenant_id, 'document_deleted', document_id)
        return {'status': 'ok', 'deleted': True, 'document': removed}

    # ── Quotes ────────────────────────────────────────────────────────────────

    @router.post('/quotes', summary='Create sales quote')
    def create_quote(payload: QuoteCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create a sales quote with line items and pricing."""
        enforce_rate_limit(f'{auth.tenant_id}:quotes:create', 60, 60)
        line_items = [item.model_dump() for item in payload.line_items]
        totals = _calc_quote_totals(line_items)
        with _lock:
            quote = {
                'id': len(quotes_memory) + 1,
                'tenant_id': auth.tenant_id,
                'quote_number': f'Q-{len(quotes_memory) + 1:05d}',
                'title': payload.title,
                'deal_id': payload.deal_id,
                'contact_id': payload.contact_id,
                'company_name': payload.company_name,
                'recipient_email': payload.recipient_email,
                'recipient_name': payload.recipient_name,
                'line_items': line_items,
                'currency': payload.currency.upper(),
                'subtotal': totals['subtotal'],
                'discount_total': totals['discount_total'],
                'tax_total': totals['tax_total'],
                'total': totals['total'],
                'notes': payload.notes,
                'require_signature': payload.require_signature,
                'payment_terms': payload.payment_terms,
                'status': 'draft',
                'view_count': 0,
                'valid_days': payload.valid_days,
                'signed_at': None,
                'signature_name': None,
                'sent_at': None,
                'viewed_at': None,
                'accepted_at': None,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            quotes_memory.append(quote)
        _append_audit(auth.tenant_id, 'quote_created', quote['id'])
        return {'status': 'ok', 'quote': quote}

    @router.get('/quotes', summary='List quotes')
    def list_quotes(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=20)] = None,
        deal_id: Annotated[str | None, Query(max_length=100)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List all quotes."""
        enforce_rate_limit(f'{auth.tenant_id}:quotes:list', 120, 60)
        with _lock:
            items = [q.copy() for q in quotes_memory if q.get('tenant_id') == auth.tenant_id]
        if status:
            items = [q for q in items if q.get('status') == status]
        if deal_id:
            items = [q for q in items if q.get('deal_id') == deal_id]
        items.sort(key=lambda x: str(x.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'quotes': items[offset:offset + limit], 'total': len(items)}

    @router.get('/quotes/{quote_id}', responses={404: {'description': QUOTE_NOT_FOUND}})
    def get_quote(quote_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a single quote."""
        enforce_rate_limit(f'{auth.tenant_id}:quotes:get', 120, 60)
        with _lock:
            quote = next((q.copy() for q in quotes_memory
                          if q.get('id') == quote_id and q.get('tenant_id') == auth.tenant_id), None)
        if quote is None:
            raise HTTPException(status_code=404, detail=QUOTE_NOT_FOUND)
        return {'status': 'ok', 'quote': quote}

    @router.post('/quotes/{quote_id}/send', responses={404: {'description': QUOTE_NOT_FOUND}})
    def send_quote(quote_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Mark quote as sent."""
        enforce_rate_limit(f'{auth.tenant_id}:quotes:send', 60, 60)
        with _lock:
            quote = next((q for q in quotes_memory
                          if q.get('id') == quote_id and q.get('tenant_id') == auth.tenant_id), None)
            if quote is None:
                raise HTTPException(status_code=404, detail=QUOTE_NOT_FOUND)
            quote['status'] = 'sent'
            quote['sent_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'quote_sent', quote_id)
        return {'status': 'ok', 'quote': quote.copy()}

    @router.post('/quotes/{quote_id}/sign', responses={404: {'description': QUOTE_NOT_FOUND}})
    def sign_quote(
        quote_id: int,
        auth: AuthDep,
        signature_name: Annotated[str, Query(min_length=1, max_length=200)],
    ) -> dict[str, Any]:
        """NEW: Record e-signature acceptance of a quote."""
        enforce_rate_limit(f'{auth.tenant_id}:quotes:sign', 30, 60)
        with _lock:
            quote = next((q for q in quotes_memory
                          if q.get('id') == quote_id and q.get('tenant_id') == auth.tenant_id), None)
            if quote is None:
                raise HTTPException(status_code=404, detail=QUOTE_NOT_FOUND)
            quote['status'] = 'accepted'
            quote['signed_at'] = datetime.now(UTC).isoformat()
            quote['signature_name'] = signature_name
            quote['accepted_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'quote_signed', quote_id)
        return {'status': 'ok', 'quote': quote.copy()}

    return router
