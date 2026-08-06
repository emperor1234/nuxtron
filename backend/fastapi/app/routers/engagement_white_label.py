import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
PaginationLimit = Annotated[int, Query(ge=1, le=100)]


class WhiteLabelBrandKitRequest(BaseModel):
    brand_name: str = Field(min_length=2, max_length=80)
    primary_color: str = Field(default='#0A7BFF', max_length=20)
    accent_color: str = Field(default='#22C55E', max_length=20)
    logo_url: str = Field(default='', max_length=300)
    support_email: str = Field(default='', max_length=160)


class WhiteLabelDomainRequest(BaseModel):
    custom_domain: str = Field(min_length=3, max_length=160)
    ssl_enabled: bool = True


class WhiteLabelCheckpointRequest(BaseModel):
    action: str = Field(default='manual_checkpoint', max_length=80)
    points: int = Field(default=12, ge=1, le=100)
    note: str = Field(default='', max_length=320)


@dataclass
class WhiteLabelContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    white_label_stages: list[str]
    white_label_events_memory: list[dict[str, Any]]
    get_profile_fn: Callable[[str], dict[str, Any]]
    signals_snapshot_fn: Callable[[str, dict[str, Any]], dict[str, int]]
    score_fn: Callable[[dict[str, int], int], int]
    stage_for_score_fn: Callable[[int], str]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[[str, str, str, str], None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]


def register_white_label_routes(*, router: APIRouter, context: WhiteLabelContext) -> None:
    @router.get('/white-label/profile')
    def white_label_profile(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:white-label:profile:get', 240, 60)
        with context.lock:
            profile = context.get_profile_fn(auth.tenant_id)
            signals = context.signals_snapshot_fn(auth.tenant_id, profile)
            score = context.score_fn(signals, int(profile.get('manual_points', 0)))
            stage = context.stage_for_score_fn(score)
            profile['white_label_score'] = score
            profile['stage'] = stage
            profile['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = profile.copy()
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'white_label': {'profile': snapshot, 'stages': context.white_label_stages, 'signals': signals},
        }

    @router.post('/white-label/brand-kit')
    def white_label_brand_kit(payload: WhiteLabelBrandKitRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:white-label:brand-kit', 120, 60)
        with context.lock:
            profile = context.get_profile_fn(auth.tenant_id)
            profile['brand_name'] = payload.brand_name
            profile['primary_color'] = payload.primary_color
            profile['accent_color'] = payload.accent_color
            profile['logo_url'] = payload.logo_url
            profile['support_email'] = payload.support_email
            profile['last_action'] = 'brand_kit_updated'
            profile['last_action_at'] = datetime.now(UTC).isoformat()
            profile['updated_at'] = profile['last_action_at']
            context.append_audit_fn(auth.tenant_id, 'white_label_brand_kit_updated', {'brand_name': payload.brand_name})
            snapshot = profile.copy()
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profile': snapshot}

    @router.post('/white-label/domain')
    def white_label_domain(payload: WhiteLabelDomainRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:white-label:domain', 120, 60)
        with context.lock:
            profile = context.get_profile_fn(auth.tenant_id)
            profile['custom_domain'] = payload.custom_domain.strip().lower()
            profile['ssl_enabled'] = bool(payload.ssl_enabled)
            profile['last_action'] = 'domain_configured'
            profile['last_action_at'] = datetime.now(UTC).isoformat()
            profile['updated_at'] = profile['last_action_at']
            context.append_audit_fn(auth.tenant_id, 'white_label_domain_configured', {'custom_domain': profile['custom_domain']})
            snapshot = profile.copy()
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profile': snapshot}

    @router.post('/white-label/checkpoint')
    def white_label_checkpoint(payload: WhiteLabelCheckpointRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:white-label:checkpoint', 120, 60)
        with context.lock:
            profile = context.get_profile_fn(auth.tenant_id)
            previous_stage = str(profile.get('stage', 'foundation'))
            profile['manual_points'] = int(profile.get('manual_points', 0)) + int(payload.points)

            signals = context.signals_snapshot_fn(auth.tenant_id, profile)
            score = context.score_fn(signals, int(profile.get('manual_points', 0)))
            stage = context.stage_for_score_fn(score)
            progressed = context.white_label_stages.index(stage) > context.white_label_stages.index(previous_stage)

            profile['stage'] = stage if progressed else previous_stage
            profile['white_label_score'] = score
            profile['last_action'] = payload.action
            profile['last_action_at'] = datetime.now(UTC).isoformat()
            profile['updated_at'] = profile['last_action_at']

            event: dict[str, Any] = {
                'id': len(context.white_label_events_memory) + 1,
                'tenant_id': auth.tenant_id,
                'action': payload.action,
                'points_added': int(payload.points),
                'note': payload.note,
                'from_stage': previous_stage,
                'to_stage': profile['stage'],
                'white_label_score': score,
                'signals': signals,
                'created_at': profile['last_action_at'],
            }
            context.white_label_events_memory.append(event)

            credits_awarded = 0
            if progressed:
                credits_awarded = 45
                context.append_credit_fn(auth.tenant_id, credits_awarded, 'white_label_stage_advance')
                context.append_notification_fn(
                    auth.tenant_id,
                    'White Label Stage Advanced',
                    f'You advanced from {previous_stage} to {profile["stage"]} in your white-label rollout.',
                    'white_label',
                )

            context.append_audit_fn(
                auth.tenant_id,
                'white_label_checkpoint',
                {
                    'event_id': event['id'],
                    'from_stage': previous_stage,
                    'to_stage': profile['stage'],
                    'white_label_score': score,
                    'progressed': progressed,
                },
            )
            snapshot = profile.copy()

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'progressed': progressed,
            'credits_awarded': credits_awarded,
            'profile': snapshot,
            'event': event,
        }

    @router.get('/white-label/timeline')
    def white_label_timeline(auth: AuthDep, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:white-label:timeline', 240, 60)
        with context.lock:
            items = [item.copy() for item in context.white_label_events_memory if item.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'timeline': items[:limit]}
