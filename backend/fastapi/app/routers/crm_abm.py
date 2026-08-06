# pyright: reportUnusedFunction=false
"""CRM ABM compatibility router.

This router provides the narrow ABM surface used by the release tests:
- target accounts
- committee members
- engagement events and timeline
- a lightweight ABM report
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
JsonObject = dict[str, Any]

_ABM_LOCK = threading.Lock()
_ABM_STATE: dict[str, dict[str, Any]] = {}
TARGET_ACCOUNT_NOT_FOUND = 'Target account not found.'


class TargetAccountCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    owner: str = Field(default='', max_length=180)
    tier: str = Field(default='tier_1', max_length=40)
    icp_fit_score: int = Field(default=0, ge=0, le=100)
    intent_score: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)


class CommitteeMemberCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    role: str = Field(default='stakeholder', max_length=80)
    influence_score: int = Field(default=0, ge=0, le=100)
    buying_power_score: int = Field(default=0, ge=0, le=100)
    engagement_level: str = Field(default='medium', max_length=40)


class EngagementEventCreateRequest(BaseModel):
    channel: str = Field(default='email', max_length=60)
    event_type: str = Field(default='activity', max_length=80)
    weight: int = Field(default=0, ge=0, le=100)
    actor: str = Field(default='', max_length=180)


def create_crm_abm_router(*, enforce_rate_limit: Callable[[str, int, int], None]) -> APIRouter:
    router = APIRouter(prefix='/crm', tags=['CRM ABM'])

    def _account_bucket(tenant_id: str) -> dict[str, Any]:
        with _ABM_LOCK:
            return _ABM_STATE.setdefault(tenant_id, {'next_account_id': 1, 'accounts': {}})

    def _serialize_account(account: JsonObject) -> JsonObject:
        return {
            'id': account['id'],
            'name': account['name'],
            'owner': account['owner'],
            'tier': account['tier'],
            'icp_fit_score': account['icp_fit_score'],
            'intent_score': account['intent_score'],
            'tags': list(account.get('tags', [])),
            'created_at': account['created_at'],
        }

    def _compute_score(account: JsonObject) -> float:
        committee_members = account.get('committee', [])
        engagement_events = account.get('engagement_events', [])
        base_score = (float(account.get('icp_fit_score', 0)) * 0.6) + (float(account.get('intent_score', 0)) * 0.4)
        committee_bonus = min(len(committee_members) * 4.0, 20.0)
        engagement_bonus = min(sum(float(event.get('weight', 0)) for event in engagement_events) / 10.0, 20.0)
        return round(min(base_score + committee_bonus + engagement_bonus, 100.0), 2)

    @router.post('/abm/target-accounts')
    def create_target_account(payload: TargetAccountCreateRequest, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:create', 120, 60)
        now_iso = datetime.now(UTC).isoformat()
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            account_id = int(bucket['next_account_id'])
            bucket['next_account_id'] = account_id + 1
            account: JsonObject = {
                'id': account_id,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'owner': payload.owner,
                'tier': payload.tier,
                'icp_fit_score': payload.icp_fit_score,
                'intent_score': payload.intent_score,
                'tags': list(payload.tags),
                'created_at': now_iso,
                'committee': [],
                'engagement_events': [],
            }
            bucket['accounts'][account_id] = account
        return {'target_account': _serialize_account(account)}

    @router.get('/abm/target-accounts')
    def list_target_accounts(auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:list', 240, 60)
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            accounts = [_serialize_account(account) for account in bucket['accounts'].values()]
        return {'target_accounts': accounts}

    @router.post('/abm/target-accounts/{account_id}/committee')
    def add_committee_member(account_id: int, payload: CommitteeMemberCreateRequest, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:committee', 120, 60)
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            account = bucket['accounts'].get(account_id)
            if account is None:
                raise HTTPException(status_code=404, detail=TARGET_ACCOUNT_NOT_FOUND)
            member = {
                'id': len(account['committee']) + 1,
                'name': payload.name,
                'role': payload.role,
                'influence_score': payload.influence_score,
                'buying_power_score': payload.buying_power_score,
                'engagement_level': payload.engagement_level,
                'created_at': datetime.now(UTC).isoformat(),
            }
            account['committee'].append(member)
        return {'committee_member': member}

    @router.get('/abm/target-accounts/{account_id}/committee')
    def list_committee_members(account_id: int, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:committee:list', 240, 60)
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            account = bucket['accounts'].get(account_id)
            if account is None:
                raise HTTPException(status_code=404, detail=TARGET_ACCOUNT_NOT_FOUND)
            committee_members = list(account['committee'])
        return {'committee_members': committee_members}

    @router.post('/abm/target-accounts/{account_id}/engagement-events')
    def add_engagement_event(account_id: int, payload: EngagementEventCreateRequest, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:events', 180, 60)
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            account = bucket['accounts'].get(account_id)
            if account is None:
                raise HTTPException(status_code=404, detail=TARGET_ACCOUNT_NOT_FOUND)
            event = {
                'id': len(account['engagement_events']) + 1,
                'channel': payload.channel,
                'event_type': payload.event_type,
                'weight': payload.weight,
                'actor': payload.actor,
                'created_at': datetime.now(UTC).isoformat(),
            }
            account['engagement_events'].append(event)
        return {'engagement_event': event}

    @router.get('/abm/target-accounts/{account_id}/engagement-events')
    def list_engagement_events(account_id: int, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:events:list', 240, 60)
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            account = bucket['accounts'].get(account_id)
            if account is None:
                raise HTTPException(status_code=404, detail=TARGET_ACCOUNT_NOT_FOUND)
            events = list(account['engagement_events'])
        return {'engagement_events': events}

    @router.get('/abm/target-accounts/{account_id}/engagement-timeline')
    def get_engagement_timeline(account_id: int, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:timeline', 240, 60)
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            account = bucket['accounts'].get(account_id)
            if account is None:
                raise HTTPException(status_code=404, detail=TARGET_ACCOUNT_NOT_FOUND)
            timeline = sorted(account['engagement_events'], key=lambda item: item['created_at'])
        return {'engagement_timeline': timeline}

    @router.get('/abm/target-accounts/{account_id}/score')
    def get_target_account_score(account_id: int, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:score', 240, 60)
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            account = bucket['accounts'].get(account_id)
            if account is None:
                raise HTTPException(status_code=404, detail=TARGET_ACCOUNT_NOT_FOUND)
            score = _compute_score(account)
        return {'score': {'composite_score': score}}

    @router.get('/reports/abm')
    def get_abm_report(auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:crm:abm:report', 120, 60)
        bucket = _account_bucket(auth.tenant_id)
        with _ABM_LOCK:
            accounts = list(bucket['accounts'].values())
            top_accounts = sorted(
                (
                    {
                        **_serialize_account(account),
                        'score': _compute_score(account),
                        'committee_size': len(account['committee']),
                        'engagement_events': len(account['engagement_events']),
                    }
                    for account in accounts
                ),
                key=lambda item: item['score'],
                reverse=True,
            )[:5]
        return {
            'summary': {
                'target_accounts_total': len(accounts),
                'committee_members_total': sum(len(account['committee']) for account in accounts),
                'engagement_events_total': sum(len(account['engagement_events']) for account in accounts),
            },
            'top_accounts': top_accounts,
        }

    return router
