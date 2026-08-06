# pyright: reportUnusedFunction=false

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]


class TalentCreatorRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    niche: str = Field(default='general', max_length=100)
    platform: str = Field(default='youtube', max_length=40)
    followers: int = Field(default=0, ge=0, le=1000000000)
    rate_card_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    bio: str = Field(default='', max_length=800)


class TalentDealRequest(BaseModel):
    creator_id: int
    brand_name: str = Field(min_length=2, max_length=160)
    deliverables: list[str] | str = Field(default_factory=list)
    budget_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    currency: str = Field(default='USD', max_length=8)
    note: str = Field(default='', max_length=500)


class TalentDealAcceptRequest(BaseModel):
    deal_id: int
    accepted: bool = Field(default=True)
    counter_rate_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    note: str = Field(default='', max_length=500)


class TalentRateCardRequest(BaseModel):
    creator_id: int
    post_rate_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    story_rate_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    reel_rate_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    package_rate_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    currency: str = Field(default='USD', max_length=8)


@dataclass
class TalentAgencyContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    talent_creators_memory: list[dict[str, Any]]
    talent_deals_memory: list[dict[str, Any]]
    talent_rate_cards_memory: list[dict[str, Any]]
    creator_not_found: str
    deal_not_found: str


def _normalize_deliverables(value: list[str] | str) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in value.replace(',', '+').split('+') if part.strip()]


def _talent_deal_stage(budget: float, accepted: bool) -> str:
    if not accepted:
        return 'proposed'
    if budget >= 5000:
        return 'enterprise_deal'
    if budget >= 1000:
        return 'mid_market_deal'
    return 'micro_deal'


def register_talent_agency_routes(*, router: APIRouter, context: TalentAgencyContext) -> None:
    talent_creator_counter: list[int] = [0]
    talent_deal_counter: list[int] = [0]
    talent_rate_card_counter: list[int] = [0]

    _register_talent_creator_routes(
        router=router,
        context=context,
        talent_creator_counter=talent_creator_counter,
        talent_rate_card_counter=talent_rate_card_counter,
    )
    _register_talent_deal_routes(
        router=router,
        context=context,
        talent_deal_counter=talent_deal_counter,
    )


def _register_talent_creator_routes(
    *,
    router: APIRouter,
    context: TalentAgencyContext,
    talent_creator_counter: list[int],
    talent_rate_card_counter: list[int],
) -> None:
    @router.get('/talent-agency/roster')
    def talent_roster(auth: AuthDep) -> dict[str, Any]:
        context.enforce_rate_limit(f'{auth.tenant_id}:talent:roster', 240, 60)
        with context.lock:
            creators = [c.copy() for c in context.talent_creators_memory if c.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(creators), 'creators': creators}

    @router.post('/talent-agency/creators')
    def talent_create_creator(
        payload: TalentCreatorRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        context.enforce_rate_limit(f'{auth.tenant_id}:talent:creators', 120, 60)
        with context.lock:
            talent_creator_counter[0] += 1
            creator: dict[str, Any] = {
                'id': talent_creator_counter[0],
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'niche': payload.niche,
                'platform': payload.platform,
                'followers': payload.followers,
                'rate_card_usd': round(payload.rate_card_usd, 2),
                'bio': payload.bio,
                'status': 'active',
                'created_at': datetime.now(UTC).isoformat(),
            }
            context.talent_creators_memory.append(creator)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'creator': creator.copy()}

    @router.post('/talent-agency/rate-cards', responses={404: {'description': 'Creator not found.'}})
    def talent_set_rate_card(
        payload: TalentRateCardRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        context.enforce_rate_limit(f'{auth.tenant_id}:talent:rate-cards', 120, 60)
        with context.lock:
            creator = next(
                (
                    c
                    for c in context.talent_creators_memory
                    if c.get('id') == payload.creator_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if creator is None:
                raise HTTPException(status_code=404, detail=context.creator_not_found)
            talent_rate_card_counter[0] += 1
            rate_card: dict[str, Any] = {
                'id': talent_rate_card_counter[0],
                'tenant_id': auth.tenant_id,
                'creator_id': payload.creator_id,
                'post_rate_usd': round(payload.post_rate_usd, 2),
                'story_rate_usd': round(payload.story_rate_usd, 2),
                'reel_rate_usd': round(payload.reel_rate_usd, 2),
                'package_rate_usd': round(payload.package_rate_usd, 2),
                'currency': payload.currency.upper(),
                'created_at': datetime.now(UTC).isoformat(),
            }
            context.talent_rate_cards_memory.append(rate_card)
            creator['rate_card_usd'] = max(payload.post_rate_usd, payload.reel_rate_usd, payload.package_rate_usd)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'rate_card': rate_card.copy()}


def _register_talent_deal_routes(
    *,
    router: APIRouter,
    context: TalentAgencyContext,
    talent_deal_counter: list[int],
) -> None:
    _register_talent_deal_crud_routes(router=router, context=context, talent_deal_counter=talent_deal_counter)
    _register_talent_overview_route(router=router, context=context)


def _register_talent_deal_crud_routes(
    *,
    router: APIRouter,
    context: TalentAgencyContext,
    talent_deal_counter: list[int],
) -> None:
    @router.post('/talent-agency/deals', responses={404: {'description': 'Creator not found.'}})
    def talent_propose_deal(
        payload: TalentDealRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        context.enforce_rate_limit(f'{auth.tenant_id}:talent:deals', 120, 60)
        with context.lock:
            creator = next(
                (
                    c
                    for c in context.talent_creators_memory
                    if c.get('id') == payload.creator_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if creator is None:
                raise HTTPException(status_code=404, detail=context.creator_not_found)
            talent_deal_counter[0] += 1
            deal: dict[str, Any] = {
                'id': talent_deal_counter[0],
                'tenant_id': auth.tenant_id,
                'creator_id': payload.creator_id,
                'creator_name': creator.get('name', ''),
                'brand_name': payload.brand_name,
                'deliverables': _normalize_deliverables(payload.deliverables),
                'budget_usd': round(payload.budget_usd, 2),
                'currency': payload.currency.upper(),
                'note': payload.note,
                'accepted': False,
                'status': 'proposed',
                'created_at': datetime.now(UTC).isoformat(),
            }
            context.talent_deals_memory.append(deal)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'deal': deal.copy()}

    @router.post('/talent-agency/deals/accept', responses={404: {'description': 'Deal not found.'}})
    def talent_accept_deal(
        payload: TalentDealAcceptRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        context.enforce_rate_limit(f'{auth.tenant_id}:talent:deals:accept', 120, 60)
        with context.lock:
            deal = next(
                (
                    d
                    for d in context.talent_deals_memory
                    if d.get('id') == payload.deal_id and d.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if deal is None:
                raise HTTPException(status_code=404, detail=context.deal_not_found)
            deal['accepted'] = bool(payload.accepted)
            if payload.counter_rate_usd > 0:
                deal['budget_usd'] = round(payload.counter_rate_usd, 2)
            deal['note'] = payload.note or deal.get('note', '')
            deal['status'] = _talent_deal_stage(float(deal['budget_usd']), bool(payload.accepted))
            deal['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = deal.copy()
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'deal': snapshot}

    @router.get('/talent-agency/deals')
    def talent_list_deals(auth: AuthDep) -> dict[str, Any]:
        context.enforce_rate_limit(f'{auth.tenant_id}:talent:deals:list', 240, 60)
        with context.lock:
            deals = [d.copy() for d in context.talent_deals_memory if d.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(deals), 'deals': deals}


def _register_talent_overview_route(*, router: APIRouter, context: TalentAgencyContext) -> None:
    @router.get('/talent-agency/overview')
    def talent_overview(auth: AuthDep) -> dict[str, Any]:
        context.enforce_rate_limit(f'{auth.tenant_id}:talent:overview', 240, 60)
        with context.lock:
            creators = [c.copy() for c in context.talent_creators_memory if c.get('tenant_id') == auth.tenant_id]
            deals = [d.copy() for d in context.talent_deals_memory if d.get('tenant_id') == auth.tenant_id]
            rate_cards = [r.copy() for r in context.talent_rate_cards_memory if r.get('tenant_id') == auth.tenant_id]
        accepted_deals = [d for d in deals if d.get('accepted')]
        total_deal_value = round(sum(float(d.get('budget_usd', 0)) for d in accepted_deals), 2)
        avg_rate = round(sum(float(c.get('rate_card_usd', 0)) for c in creators) / len(creators) if creators else 0.0, 2)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'talent_agency': {
                'creators_on_roster': len(creators),
                'rate_cards_on_file': len(rate_cards),
                'total_deals': len(deals),
                'accepted_deals': len(accepted_deals),
                'total_deal_value_usd': total_deal_value,
                'avg_creator_rate_usd': avg_rate,
                'marketplace_stage': 'active' if len(accepted_deals) > 0 else 'seeding',
            },
        }
