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


class BrandLockCheckpointRequest(BaseModel):
    action: str = Field(default='asset_sync', max_length=80)
    points: int = Field(default=10, ge=1, le=100)
    note: str = Field(default='', max_length=320)


class AutopilotCheckpointRequest(BaseModel):
    action: str = Field(default='automation_alignment', max_length=80)
    points: int = Field(default=10, ge=1, le=100)
    note: str = Field(default='', max_length=320)


class AchievementEvaluateRequest(BaseModel):
    trigger: str = Field(default='manual_refresh', max_length=80)


@dataclass
class BrandAutopilotAchievementsContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    brand_stages: list[str]
    achievement_catalog: list[dict[str, Any]]
    brand_lock_profiles_memory: list[dict[str, Any]]
    brand_lock_events_memory: list[dict[str, Any]]
    autopilot_profiles_memory: list[dict[str, Any]]
    autopilot_events_memory: list[dict[str, Any]]
    achievement_profiles_memory: list[dict[str, Any]]
    achievement_events_memory: list[dict[str, Any]]
    get_brand_profile_fn: Callable[[str], dict[str, Any]]
    brand_signals_snapshot_fn: Callable[[str], dict[str, int]]
    brand_score_fn: Callable[[dict[str, int], int], int]
    brand_stage_for_score_fn: Callable[[int], str]
    get_autopilot_profile_fn: Callable[[str], dict[str, Any]]
    autopilot_signals_snapshot_fn: Callable[[str], dict[str, int]]
    autopilot_score_fn: Callable[[dict[str, int], int], int]
    autopilot_maturity_for_score_fn: Callable[[int], str]
    evaluate_achievements_fn: Callable[[str, str], tuple[dict[str, Any], list[dict[str, Any]]]]
    tenant_display_name_fn: Callable[[str], str]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[[str, str, str, str], None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]


def register_brand_autopilot_achievement_routes(*, router: APIRouter, context: BrandAutopilotAchievementsContext) -> None:
    _register_brand_routes(router, context)
    _register_autopilot_routes(router, context)
    _register_achievement_routes(router, context)


def _register_brand_routes(router: APIRouter, ctx: BrandAutopilotAchievementsContext) -> None:
    @router.get('/engagement/personal-brand-lock-in')
    def personal_brand_lock_in(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:brand-lock:get', 240, 60)
        with ctx.lock:
            profile = ctx.get_brand_profile_fn(auth.tenant_id)
            signals = ctx.brand_signals_snapshot_fn(auth.tenant_id)
            score = ctx.brand_score_fn(signals, int(profile.get('manual_points', 0)))
            target_stage = ctx.brand_stage_for_score_fn(score)
            profile['brand_lock_score'] = score
            profile['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = profile.copy()

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'personal_brand_lock_in': {
                'profile': snapshot,
                'target_stage': target_stage,
                'stages': ctx.brand_stages,
                'signals': signals,
            },
        }

    @router.post('/engagement/personal-brand-lock-in/checkpoint')
    def personal_brand_lock_checkpoint(payload: BrandLockCheckpointRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:brand-lock:checkpoint', 120, 60)
        with ctx.lock:
            profile = ctx.get_brand_profile_fn(auth.tenant_id)
            previous_stage = str(profile.get('stage', 'starter'))

            profile['manual_points'] = int(profile.get('manual_points', 0)) + int(payload.points)
            signals = ctx.brand_signals_snapshot_fn(auth.tenant_id)
            score = ctx.brand_score_fn(signals, int(profile.get('manual_points', 0)))
            target_stage = ctx.brand_stage_for_score_fn(score)

            progressed = ctx.brand_stages.index(target_stage) > ctx.brand_stages.index(previous_stage)
            profile['stage'] = target_stage if progressed else previous_stage
            profile['brand_lock_score'] = score
            profile['last_action'] = payload.action
            profile['last_action_at'] = datetime.now(UTC).isoformat()
            profile['updated_at'] = profile['last_action_at']

            event: dict[str, Any] = {
                'id': len(ctx.brand_lock_events_memory) + 1,
                'tenant_id': auth.tenant_id,
                'action': payload.action,
                'points_added': int(payload.points),
                'note': payload.note,
                'from_stage': previous_stage,
                'to_stage': profile['stage'],
                'brand_lock_score': score,
                'signals': signals,
                'created_at': profile['last_action_at'],
            }
            ctx.brand_lock_events_memory.append(event)

            credits_awarded = 0
            if progressed:
                credits_awarded = 30
                ctx.append_credit_fn(auth.tenant_id, credits_awarded, 'personal_brand_lock_stage_advance')
                ctx.append_notification_fn(
                    auth.tenant_id,
                    'Brand Lock Stage Advanced',
                    f'You advanced from {previous_stage} to {profile["stage"]} and earned {credits_awarded} AI credits.',
                    'personal_brand_lock_in',
                )

            ctx.append_audit_fn(
                auth.tenant_id,
                'personal_brand_lock_checkpoint',
                {
                    'event_id': event['id'],
                    'from_stage': previous_stage,
                    'to_stage': profile['stage'],
                    'score': score,
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

    @router.get('/engagement/personal-brand-lock-in/timeline')
    def personal_brand_lock_timeline(auth: AuthDep, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:brand-lock:timeline', 240, 60)
        with ctx.lock:
            items = [item.copy() for item in ctx.brand_lock_events_memory if item.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'timeline': items[:limit]}


def _register_autopilot_routes(router: APIRouter, ctx: BrandAutopilotAchievementsContext) -> None:
    @router.get('/engagement/autopilot-dependency/dashboard')
    def autopilot_dependency_dashboard(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:autopilot:dashboard', 240, 60)
        with ctx.lock:
            profile = ctx.get_autopilot_profile_fn(auth.tenant_id)
            signals = ctx.autopilot_signals_snapshot_fn(auth.tenant_id)
            score = ctx.autopilot_score_fn(signals, int(profile.get('manual_points', 0)))
            maturity = ctx.autopilot_maturity_for_score_fn(score)

            profile['autopilot_score'] = score
            profile['maturity'] = maturity
            profile['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = profile.copy()

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'autopilot_dependency': {
                'profile': snapshot,
                'signals': signals,
                'recommendation': 'scale_automation' if score >= 60 else 'stabilize_automation',
            },
        }

    @router.post('/engagement/autopilot-dependency/checkpoint')
    def autopilot_dependency_checkpoint(payload: AutopilotCheckpointRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:autopilot:checkpoint', 120, 60)
        with ctx.lock:
            profile = ctx.get_autopilot_profile_fn(auth.tenant_id)
            previous_maturity = str(profile.get('maturity', 'manual_plus'))

            profile['manual_points'] = int(profile.get('manual_points', 0)) + int(payload.points)
            signals = ctx.autopilot_signals_snapshot_fn(auth.tenant_id)
            score = ctx.autopilot_score_fn(signals, int(profile.get('manual_points', 0)))
            maturity = ctx.autopilot_maturity_for_score_fn(score)

            maturity_order = {'manual_plus': 0, 'hybrid': 1, 'high_automation': 2, 'self_driving': 3}
            progressed = maturity_order[maturity] > maturity_order[previous_maturity]
            profile['maturity'] = maturity if progressed else previous_maturity
            profile['autopilot_score'] = score
            profile['last_action'] = payload.action
            profile['last_action_at'] = datetime.now(UTC).isoformat()
            profile['updated_at'] = profile['last_action_at']

            event: dict[str, Any] = {
                'id': len(ctx.autopilot_events_memory) + 1,
                'tenant_id': auth.tenant_id,
                'action': payload.action,
                'points_added': int(payload.points),
                'note': payload.note,
                'from_maturity': previous_maturity,
                'to_maturity': profile['maturity'],
                'autopilot_score': score,
                'signals': signals,
                'created_at': profile['last_action_at'],
            }
            ctx.autopilot_events_memory.append(event)

            credits_awarded = 0
            if progressed:
                credits_awarded = 35
                ctx.append_credit_fn(auth.tenant_id, credits_awarded, 'autopilot_dependency_maturity_advance')
                ctx.append_notification_fn(
                    auth.tenant_id,
                    'Autopilot Maturity Increased',
                    f'Your automation maturity advanced from {previous_maturity} to {profile["maturity"]}.',
                    'autopilot_dependency',
                )

            ctx.append_audit_fn(
                auth.tenant_id,
                'autopilot_dependency_checkpoint',
                {
                    'event_id': event['id'],
                    'from_maturity': previous_maturity,
                    'to_maturity': profile['maturity'],
                    'autopilot_score': score,
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

    @router.get('/engagement/autopilot-dependency/timeline')
    def autopilot_dependency_timeline(auth: AuthDep, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:autopilot:timeline', 240, 60)
        with ctx.lock:
            items = [item.copy() for item in ctx.autopilot_events_memory if item.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'timeline': items[:limit]}


def _register_achievement_routes(router: APIRouter, ctx: BrandAutopilotAchievementsContext) -> None:
    @router.get('/engagement/achievements')
    def achievements(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:achievements:get', 240, 60)
        with ctx.lock:
            profile, newly_unlocked = ctx.evaluate_achievements_fn(auth.tenant_id, 'auto_view')
            history = [item.copy() for item in ctx.achievement_events_memory if item.get('tenant_id') == auth.tenant_id]

        history.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'achievements': {
                'profile': profile,
                'catalog': ctx.achievement_catalog,
                'newly_unlocked': newly_unlocked,
                'history': history[:20],
            },
        }

    @router.post('/engagement/achievements/evaluate')
    def achievements_evaluate(payload: AchievementEvaluateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:achievements:evaluate', 120, 60)
        with ctx.lock:
            profile, newly_unlocked = ctx.evaluate_achievements_fn(auth.tenant_id, payload.trigger)
            ctx.append_audit_fn(
                auth.tenant_id,
                'achievement_evaluated',
                {'trigger': payload.trigger, 'newly_unlocked': [item['achievement_id'] for item in newly_unlocked]},
            )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profile': profile, 'newly_unlocked': newly_unlocked}

    @router.get('/engagement/achievements/leaderboard')
    def achievements_leaderboard(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:achievements:leaderboard', 240, 60)
        with ctx.lock:
            leaderboard_rows: list[dict[str, Any]] = [
                {
                    'tenant_id': str(item.get('tenant_id') or ''),
                    'tenant_display_name': ctx.tenant_display_name_fn(str(item.get('tenant_id', ''))),
                    'total_points': int(item.get('total_points', 0)),
                    'unlocked_count': int(item.get('unlocked_count', 0)),
                    'updated_at': str(item.get('updated_at') or ''),
                }
                for item in ctx.achievement_profiles_memory
            ]
            leaderboard: list[dict[str, Any]] = sorted(
                leaderboard_rows,
                key=lambda item: (-item['total_points'], -item['unlocked_count'], item['tenant_id']),
            )[:10]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'leaderboard': leaderboard}

    @router.get('/engagement/achievements/timeline')
    def achievements_timeline(auth: AuthDep, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:achievements:timeline', 240, 60)
        with ctx.lock:
            items = [item.copy() for item in ctx.achievement_events_memory if item.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'timeline': items[:limit]}
