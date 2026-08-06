import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]


class StudiosServiceRequest(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    category: str = Field(default='video', max_length=80)
    price_usd: float = Field(default=0.0, ge=0.0, le=1000000.0)
    turnaround_days: int = Field(default=7, ge=1, le=365)


class StudiosBriefRequest(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    category: str = Field(default='video', max_length=80)
    budget_usd: float = Field(default=0.0, ge=0.0, le=1000000.0)
    due_date: str = Field(min_length=10, max_length=40)
    scope: str = Field(default='', max_length=1000)


class StudiosProposalRequest(BaseModel):
    brief_id: int
    service_id: int
    bid_usd: float = Field(gt=0.0, le=1000000.0)
    message: str = Field(default='', max_length=1000)


class StudiosEscrowRequest(BaseModel):
    proposal_id: int
    milestone_name: str = Field(min_length=3, max_length=160)
    amount_usd: float = Field(gt=0.0, le=1000000.0)


class StudiosEscrowReleaseRequest(BaseModel):
    escrow_id: int
    approved: bool = True
    note: str = Field(default='', max_length=320)


@dataclass
class StudiosContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    studios_services_memory: list[dict[str, Any]]
    studios_briefs_memory: list[dict[str, Any]]
    studios_proposals_memory: list[dict[str, Any]]
    studios_escrows_memory: list[dict[str, Any]]
    studios_bid_status_fn: Callable[[int, int], str]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[[str, str, str, str], None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]
    brief_not_found: str
    service_not_found: str
    proposal_not_found: str
    escrow_not_found: str
    escrow_not_funded: str


def register_studios_routes(*, router: APIRouter, context: StudiosContext) -> None:
    _register_studios_listing_routes(router, context)
    _register_studios_transaction_routes(router, context)


def _register_studios_listing_routes(router: APIRouter, ctx: StudiosContext) -> None:
    @router.post('/money-printers/nuxtron-studios/services')
    def nuxtron_studios_create_service(payload: StudiosServiceRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-studios:services:create', 120, 60)
        with ctx.lock:
            now_iso = datetime.now(UTC).isoformat()
            service: dict[str, Any] = {
                'id': len(ctx.studios_services_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title,
                'category': payload.category.strip().lower(),
                'price_usd': round(float(payload.price_usd), 2),
                'turnaround_days': int(payload.turnaround_days),
                'status': 'active',
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.studios_services_memory.append(service)
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_studios_service_created', {'service_id': service['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'service': service}

    @router.post('/money-printers/nuxtron-studios/briefs')
    def nuxtron_studios_create_brief(payload: StudiosBriefRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-studios:briefs:create', 120, 60)
        with ctx.lock:
            now_iso = datetime.now(UTC).isoformat()
            brief: dict[str, Any] = {
                'id': len(ctx.studios_briefs_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title,
                'category': payload.category.strip().lower(),
                'budget_usd': round(float(payload.budget_usd), 2),
                'due_date': payload.due_date,
                'scope': payload.scope,
                'status': 'open',
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.studios_briefs_memory.append(brief)
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_studios_brief_created', {'brief_id': brief['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'brief': brief}

    @router.post('/money-printers/nuxtron-studios/proposals', responses={404: {'description': 'Studios brief or service not found.'}})
    def nuxtron_studios_create_proposal(payload: StudiosProposalRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-studios:proposals:create', 120, 60)
        with ctx.lock:
            brief = next(
                (item for item in ctx.studios_briefs_memory
                 if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.brief_id)),
                None,
            )
            if brief is None:
                raise HTTPException(status_code=404, detail=ctx.brief_not_found)
            service = next(
                (item for item in ctx.studios_services_memory
                 if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.service_id)),
                None,
            )
            if service is None:
                raise HTTPException(status_code=404, detail=ctx.service_not_found)
            now_iso = datetime.now(UTC).isoformat()
            proposal: dict[str, Any] = {
                'id': len(ctx.studios_proposals_memory) + 1,
                'tenant_id': auth.tenant_id,
                'brief_id': int(brief['id']),
                'service_id': int(service['id']),
                'bid_usd': round(float(payload.bid_usd), 2),
                'message': payload.message,
                'status': 'submitted',
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.studios_proposals_memory.append(proposal)
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_studios_proposal_created',
                {'proposal_id': proposal['id'], 'brief_id': int(brief['id'])})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'proposal': proposal}


def _register_studios_transaction_routes(router: APIRouter, ctx: StudiosContext) -> None:
    @router.post('/money-printers/nuxtron-studios/escrows', responses={404: {'description': 'Studios proposal not found.'}})
    def nuxtron_studios_create_escrow(payload: StudiosEscrowRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-studios:escrows:create', 90, 60)
        with ctx.lock:
            proposal = next(
                (item for item in ctx.studios_proposals_memory
                 if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.proposal_id)),
                None,
            )
            if proposal is None:
                raise HTTPException(status_code=404, detail=ctx.proposal_not_found)
            now_iso = datetime.now(UTC).isoformat()
            escrow: dict[str, Any] = {
                'id': len(ctx.studios_escrows_memory) + 1,
                'tenant_id': auth.tenant_id,
                'proposal_id': int(proposal['id']),
                'milestone_name': payload.milestone_name,
                'amount_usd': round(float(payload.amount_usd), 2),
                'status': 'funded',
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.studios_escrows_memory.append(escrow)
            proposal['status'] = 'accepted'
            proposal['updated_at'] = now_iso
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_studios_escrow_funded', {'escrow_id': escrow['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'escrow': escrow}

    @router.post(
        '/money-printers/nuxtron-studios/escrows/release',
        responses={
            404: {'description': 'Studios escrow not found.'},
            409: {'description': 'Escrow can only be released from funded state.'},
        },
    )
    def nuxtron_studios_release_escrow(payload: StudiosEscrowReleaseRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-studios:escrows:release', 90, 60)
        with ctx.lock:
            escrow = next(
                (item for item in ctx.studios_escrows_memory
                 if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.escrow_id)),
                None,
            )
            if escrow is None:
                raise HTTPException(status_code=404, detail=ctx.escrow_not_found)
            if str(escrow.get('status', '')).lower() != 'funded':
                raise HTTPException(status_code=409, detail=ctx.escrow_not_funded)
            escrow['status'] = 'released' if payload.approved else 'disputed'
            escrow['updated_at'] = datetime.now(UTC).isoformat()
            event: dict[str, Any] = {
                'escrow_id': int(escrow['id']),
                'approved': bool(payload.approved),
                'note': payload.note,
                'status': escrow['status'],
                'created_at': escrow['updated_at'],
            }
            credits_awarded = 0
            if payload.approved:
                credits_awarded = max(10, int(float(escrow.get('amount_usd', 0.0)) * 0.03))
                ctx.append_credit_fn(auth.tenant_id, credits_awarded, 'nuxtron_studios_escrow_release')
                ctx.append_notification_fn(
                    auth.tenant_id, 'Nuxtron Studios Escrow Released',
                    f'Escrow #{escrow["id"]} released for ${float(escrow.get("amount_usd", 0.0)):.2f}.',
                    'nuxtron_studios',
                )
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_studios_escrow_release', event)
        return {
            'status': 'ok', 'tenant_id': auth.tenant_id,
            'escrow': escrow, 'event': event, 'credits_awarded': credits_awarded,
        }

    @router.get('/money-printers/nuxtron-studios/overview')
    def nuxtron_studios_overview(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-studios:overview', 240, 60)
        with ctx.lock:
            services = [item.copy() for item in ctx.studios_services_memory if item.get('tenant_id') == auth.tenant_id]
            briefs = [item.copy() for item in ctx.studios_briefs_memory if item.get('tenant_id') == auth.tenant_id]
            proposals = [item.copy() for item in ctx.studios_proposals_memory if item.get('tenant_id') == auth.tenant_id]
            escrows = [item.copy() for item in ctx.studios_escrows_memory if item.get('tenant_id') == auth.tenant_id]
        accepted = sum(1 for item in proposals if str(item.get('status', '')).lower() == 'accepted')
        funded = sum(1 for item in escrows if str(item.get('status', '')).lower() == 'funded')
        released = sum(1 for item in escrows if str(item.get('status', '')).lower() == 'released')
        throughput_usd = round(
            sum(
                float(item.get('amount_usd', 0.0))
                for item in escrows
                if str(item.get('status', '')).lower() in ('funded', 'released')
            ),
            2,
        )
        return {
            'status': 'ok', 'tenant_id': auth.tenant_id,
            'studios': {
                'services': len(services), 'briefs': len(briefs), 'proposals': len(proposals),
                'accepted_proposals': accepted, 'funded_escrows': funded, 'released_escrows': released,
                'throughput_usd': throughput_usd,
                'market_stage': ctx.studios_bid_status_fn(len(proposals), accepted),
            },
        }
