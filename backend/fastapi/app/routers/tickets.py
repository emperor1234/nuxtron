# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedFunction=false
"""
Help Desk / Ticketing System (HubSpot Service Hub §6.1)
NEW: Support ticket pipeline with SLA management, omnichannel intake,
auto-routing, priority escalation, CSAT tracking per ticket.
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

TICKET_NOT_FOUND = 'Ticket not found.'
COMMENT_NOT_FOUND = 'Ticket comment not found.'
PRIORITY_LEVELS = {'low', 'normal', 'high', 'urgent'}
TICKET_STATUSES = {'open', 'in_progress', 'waiting_on_customer', 'resolved', 'closed'}
CHANNELS = {'email', 'chat', 'social', 'phone', 'form', 'api'}


class TicketCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    description: str = Field(default='', max_length=10000)
    priority: str = Field(default='normal', max_length=10)
    channel: str = Field(default='api', max_length=20)
    customer_email: str = Field(min_length=1, max_length=200)
    customer_name: str = Field(default='', max_length=200)
    contact_id: str = Field(default='', max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=10)
    attachments: list[str] = Field(default_factory=list, max_length=5)


class TicketUpdateRequest(BaseModel):
    subject: str = Field(default='', max_length=300)
    status: str = Field(default='', max_length=30)
    priority: str = Field(default='', max_length=10)
    assigned_to: str = Field(default='', max_length=100)
    tags: list[str] | None = None
    resolution_notes: str = Field(default='', max_length=5000)


class TicketCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    is_internal: bool = False
    attachments: list[str] = Field(default_factory=list, max_length=5)


class SLAConfigRequest(BaseModel):
    priority: str = Field(max_length=10)
    first_response_hours: int = Field(ge=0, le=168)
    resolution_hours: int = Field(ge=0, le=720)


def create_tickets_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    tickets_memory: list[dict[str, Any]],
    ticket_comments_memory: list[dict[str, Any]],
    sla_configs_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """NEW: Help desk ticketing router — HubSpot Service Hub §6.1."""
    router = APIRouter()
    _lock = threading.Lock()

    # Default SLA hours per priority
    DEFAULT_SLA: dict[str, dict[str, int]] = {
        'low':    {'first_response_hours': 24, 'resolution_hours': 120},
        'normal': {'first_response_hours': 8,  'resolution_hours': 48},
        'high':   {'first_response_hours': 4,  'resolution_hours': 24},
        'urgent': {'first_response_hours': 1,  'resolution_hours': 8},
    }

    def _get_sla(tenant_id: str, priority: str) -> dict[str, int]:
        cfg = next((s for s in sla_configs_memory
                    if s.get('tenant_id') == tenant_id and s.get('priority') == priority), None)
        if cfg:
            return {'first_response_hours': int(cfg['first_response_hours']),
                    'resolution_hours': int(cfg['resolution_hours'])}
        return DEFAULT_SLA.get(priority, DEFAULT_SLA['normal'])

    def _append_audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'tickets-router',
            })

    def _sla_due_timestamp(created_at: datetime, hours: int) -> str:
        return (created_at + timedelta(hours=hours)).isoformat()

    @router.post('/tickets', summary='Create support ticket')
    def create_ticket(payload: TicketCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create a support ticket from any channel."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:create', 120, 60)
        priority = payload.priority.strip().lower()
        if priority not in PRIORITY_LEVELS:
            priority = 'normal'
        channel = payload.channel.strip().lower()
        if channel not in CHANNELS:
            channel = 'api'
        sla = _get_sla(auth.tenant_id, priority)
        created_at = datetime.now(UTC)
        with _lock:
            ticket = {
                'id': len(tickets_memory) + 1,
                'tenant_id': auth.tenant_id,
                'ticket_number': f'TKT-{len(tickets_memory) + 1:05d}',
                'subject': payload.subject,
                'description': payload.description,
                'priority': priority,
                'channel': channel,
                'status': 'open',
                'customer_email': payload.customer_email,
                'customer_name': payload.customer_name,
                'contact_id': payload.contact_id,
                'tags': payload.tags,
                'attachments': payload.attachments,
                'assigned_to': None,
                'first_response_due': _sla_due_timestamp(created_at, sla['first_response_hours']),
                'resolution_due': _sla_due_timestamp(created_at, sla['resolution_hours']),
                'first_response_at': None,
                'resolved_at': None,
                'resolution_notes': '',
                'sla_first_response_hours': sla['first_response_hours'],
                'sla_resolution_hours': sla['resolution_hours'],
                'comment_count': 0,
                'csat_score': None,
                'created_at': created_at.isoformat(),
                'updated_at': created_at.isoformat(),
            }
            tickets_memory.append(ticket)
        _append_audit(auth.tenant_id, 'ticket_created', ticket['id'])
        return {'status': 'ok', 'ticket': ticket}

    @router.get('/tickets', summary='List tickets')
    def list_tickets(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=30)] = None,
        priority: Annotated[str | None, Query(max_length=10)] = None,
        assigned_to: Annotated[str | None, Query(max_length=100)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List tickets with optional filters."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:list', 120, 60)
        with _lock:
            items = [t.copy() for t in tickets_memory if t.get('tenant_id') == auth.tenant_id]
        if status:
            items = [t for t in items if t.get('status') == status]
        if priority:
            items = [t for t in items if t.get('priority') == priority]
        if assigned_to:
            items = [t for t in items if t.get('assigned_to') == assigned_to]
        items.sort(key=lambda x: str(x.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tickets': items[offset:offset + limit], 'total': len(items)}

    @router.get('/tickets/{ticket_id}', responses={404: {'description': TICKET_NOT_FOUND}})
    def get_ticket(ticket_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a single ticket with all details."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:get', 120, 60)
        with _lock:
            ticket = next((t.copy() for t in tickets_memory
                           if t.get('id') == ticket_id and t.get('tenant_id') == auth.tenant_id), None)
            comments = [c.copy() for c in ticket_comments_memory if c.get('ticket_id') == ticket_id]
        if ticket is None:
            raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
        ticket['comments'] = comments
        return {'status': 'ok', 'ticket': ticket}

    @router.patch('/tickets/{ticket_id}', responses={404: {'description': TICKET_NOT_FOUND}})
    def update_ticket(ticket_id: int, payload: TicketUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Update ticket fields (status, priority, assignment, resolution)."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:update', 120, 60)
        with _lock:
            ticket = next((t for t in tickets_memory
                           if t.get('id') == ticket_id and t.get('tenant_id') == auth.tenant_id), None)
            if ticket is None:
                raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
            now = datetime.now(UTC).isoformat()
            if payload.subject:
                ticket['subject'] = payload.subject
            if payload.status and payload.status in TICKET_STATUSES:
                ticket['status'] = payload.status
                if payload.status in {'resolved', 'closed'} and not ticket.get('resolved_at'):
                    ticket['resolved_at'] = now
            if payload.priority and payload.priority in PRIORITY_LEVELS:
                ticket['priority'] = payload.priority
                ticket['sla_first_response_hours'] = _get_sla(auth.tenant_id, payload.priority)['first_response_hours']
                ticket['sla_resolution_hours'] = _get_sla(auth.tenant_id, payload.priority)['resolution_hours']
                created_at_value = datetime.fromisoformat(str(ticket.get('created_at')).replace('Z', '+00:00'))
                if ticket.get('first_response_at') is None:
                    ticket['first_response_due'] = _sla_due_timestamp(created_at_value, ticket['sla_first_response_hours'])
                if ticket.get('resolved_at') is None:
                    ticket['resolution_due'] = _sla_due_timestamp(created_at_value, ticket['sla_resolution_hours'])
            if payload.assigned_to:
                if not ticket.get('first_response_at'):
                    ticket['first_response_at'] = now
                ticket['assigned_to'] = payload.assigned_to
            if payload.tags is not None:
                ticket['tags'] = payload.tags
            if payload.resolution_notes:
                ticket['resolution_notes'] = payload.resolution_notes
            ticket['updated_at'] = now
        _append_audit(auth.tenant_id, 'ticket_updated', ticket_id)
        return {'status': 'ok', 'ticket': ticket.copy()}

    @router.post('/tickets/{ticket_id}/comments', responses={404: {'description': TICKET_NOT_FOUND}})
    def add_comment(ticket_id: int, payload: TicketCommentRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Add a comment/note to a ticket (public or internal)."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:comment', 120, 60)
        with _lock:
            ticket = next((t for t in tickets_memory
                           if t.get('id') == ticket_id and t.get('tenant_id') == auth.tenant_id), None)
            if ticket is None:
                raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
            comment = {
                'id': len(ticket_comments_memory) + 1,
                'tenant_id': auth.tenant_id,
                'ticket_id': ticket_id,
                'body': payload.body,
                'is_internal': payload.is_internal,
                'attachments': payload.attachments,
                'author_id': f'tenant:{auth.tenant_id}',
                'created_at': datetime.now(UTC).isoformat(),
            }
            ticket_comments_memory.append(comment)
            ticket['comment_count'] = ticket.get('comment_count', 0) + 1
            # First public response marks first_response_at
            if not payload.is_internal and not ticket.get('first_response_at'):
                ticket['first_response_at'] = comment['created_at']
        _append_audit(auth.tenant_id, 'ticket_comment_added', ticket_id)
        return {'status': 'ok', 'comment': comment}

    @router.get('/tickets/{ticket_id}/comments', responses={404: {'description': TICKET_NOT_FOUND}})
    def list_comments(ticket_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: List all comments on a ticket."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:list-comments', 120, 60)
        with _lock:
            ticket = next((t for t in tickets_memory
                           if t.get('id') == ticket_id and t.get('tenant_id') == auth.tenant_id), None)
            if ticket is None:
                raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
            comments = [c.copy() for c in ticket_comments_memory if c.get('ticket_id') == ticket_id]
        return {'status': 'ok', 'comments': comments, 'total': len(comments)}

    @router.post('/tickets/{ticket_id}/csat', responses={404: {'description': TICKET_NOT_FOUND}})
    def submit_csat(
        ticket_id: int,
        auth: AuthDep,
        score: Annotated[int, Query(ge=1, le=5)] = 5,
    ) -> dict[str, Any]:
        """NEW: Submit CSAT score for a resolved ticket."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:csat', 60, 60)
        with _lock:
            ticket = next((t for t in tickets_memory
                           if t.get('id') == ticket_id and t.get('tenant_id') == auth.tenant_id), None)
            if ticket is None:
                raise HTTPException(status_code=404, detail=TICKET_NOT_FOUND)
            ticket['csat_score'] = score
            ticket['csat_submitted_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'ticket_csat_submitted', ticket_id)
        return {'status': 'ok', 'ticket_id': ticket_id, 'csat_score': score}

    @router.put('/tickets/sla-config', summary='Configure SLA rules', responses={422: {'description': 'Invalid priority'}})
    def configure_sla(payload: SLAConfigRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Set SLA response/resolution time targets per priority."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:sla-config', 30, 60)
        priority = payload.priority.strip().lower()
        if priority not in PRIORITY_LEVELS:
            raise HTTPException(status_code=422, detail=f'Invalid priority. Must be one of: {sorted(PRIORITY_LEVELS)}')
        with _lock:
            existing = next((s for s in sla_configs_memory
                             if s.get('tenant_id') == auth.tenant_id and s.get('priority') == priority), None)
            if existing:
                existing['first_response_hours'] = payload.first_response_hours
                existing['resolution_hours'] = payload.resolution_hours
                existing['updated_at'] = datetime.now(UTC).isoformat()
                cfg = existing.copy()
            else:
                cfg = {
                    'id': len(sla_configs_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'priority': priority,
                    'first_response_hours': payload.first_response_hours,
                    'resolution_hours': payload.resolution_hours,
                    'created_at': datetime.now(UTC).isoformat(),
                }
                sla_configs_memory.append(cfg)
        return {'status': 'ok', 'sla_config': cfg}

    @router.get('/tickets/analytics/summary', summary='Ticket analytics')
    def ticket_analytics(auth: AuthDep) -> dict[str, Any]:
        """NEW: Ticket analytics — open count, CSAT avg, resolution time, by priority."""
        enforce_rate_limit(f'{auth.tenant_id}:tickets:analytics', 60, 60)
        with _lock:
            all_tickets = [t for t in tickets_memory if t.get('tenant_id') == auth.tenant_id]
        open_count = sum(1 for t in all_tickets if t.get('status') == 'open')
        in_progress = sum(1 for t in all_tickets if t.get('status') == 'in_progress')
        resolved = sum(1 for t in all_tickets if t.get('status') in {'resolved', 'closed'})
        csat_scores = [int(t['csat_score']) for t in all_tickets if t.get('csat_score') is not None]
        csat_avg = round(sum(csat_scores) / len(csat_scores), 2) if csat_scores else None
        priority_breakdown: dict[str, int] = {}
        for t in all_tickets:
            p = str(t.get('priority', 'normal'))
            priority_breakdown[p] = priority_breakdown.get(p, 0) + 1
        return {
            'status': 'ok',
            'total_tickets': len(all_tickets),
            'open': open_count,
            'in_progress': in_progress,
            'resolved': resolved,
            'csat_average': csat_avg,
            'csat_responses': len(csat_scores),
            'priority_breakdown': priority_breakdown,
        }

    return router
