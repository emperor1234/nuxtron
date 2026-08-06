import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
PaginationLimit = Annotated[int, Query(ge=1, le=100)]
OptionalQueryStr = Annotated[str | None, Query()]


class CompanionCheckInRequest(BaseModel):
    mood: str = Field(default='focused', max_length=40)
    energy: int = Field(default=3, ge=1, le=5)
    today_goal: str = Field(default='', max_length=320)


class CompanionMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class FomoRuleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    trigger_type: str = Field(default='limited_slot', max_length=40)
    threshold: int = Field(default=1, ge=1, le=100000)
    window_minutes: int = Field(default=60, ge=1, le=1440)


class FomoTriggerRequest(BaseModel):
    rule_id: int
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=5, max_length=4000)
    priority: str = Field(default='high', max_length=20)


class SocialProofEventRequest(BaseModel):
    headline: str = Field(min_length=3, max_length=180)
    metric_label: str = Field(default='wins', max_length=60)
    metric_value: float = Field(default=1.0, ge=0.0, le=1000000000.0)
    proof_type: str = Field(default='revenue', max_length=40)
    actor_name: str = Field(default='', max_length=80)
    boost_points: int = Field(default=10, ge=1, le=1000)


@dataclass
class CompanionSocialContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    companion_profiles_memory: list[dict[str, Any]]
    companion_messages_memory: list[dict[str, Any]]
    fomo_rules_memory: list[dict[str, Any]]
    fomo_events_memory: list[dict[str, Any]]
    social_proof_events_memory: list[dict[str, Any]]
    fomo_rule_not_found: str
    fomo_rule_inactive: str
    today_fn: Callable[[], date]
    parse_date_fn: Callable[[str | None], date | None]
    get_companion_profile_fn: Callable[[str], dict[str, Any]]
    companion_reply_fn: Callable[[dict[str, Any], str], str]
    get_default_fomo_rules_fn: Callable[[str], list[dict[str, Any]]]
    tenant_display_name_fn: Callable[[str], str]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[[str, str, str, str], None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]


def register_companion_social_routes(*, router: APIRouter, context: CompanionSocialContext) -> None:
    _register_ai_best_friend_routes(router, context)
    _register_fomo_routes(router, context)
    _register_social_proof_routes(router, context)


def _register_ai_best_friend_routes(router: APIRouter, ctx: CompanionSocialContext) -> None:
    @router.get('/engagement/ai-best-friend')
    def ai_best_friend(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:ai-best-friend:get', 240, 60)
        today_iso = ctx.today_fn().isoformat()
        with ctx.lock:
            profile = ctx.get_companion_profile_fn(auth.tenant_id).copy()
            history = [
                item.copy()
                for item in ctx.companion_messages_memory
                if item.get('tenant_id') == auth.tenant_id
            ]

        history.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        checked_in_today = str(profile.get('last_check_in_date', '')) == today_iso
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'companion': {
                'profile': profile,
                'checked_in_today': checked_in_today,
                'daily_prompt': 'What is the one outcome that would make today a win?',
                'recent_messages': history[:5],
            },
        }

    @router.post('/engagement/ai-best-friend/check-in')
    def ai_best_friend_check_in(payload: CompanionCheckInRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:ai-best-friend:check-in', 60, 60)
        today = ctx.today_fn()
        today_iso = today.isoformat()
        with ctx.lock:
            profile = ctx.get_companion_profile_fn(auth.tenant_id)
            last_check_in = ctx.parse_date_fn(profile.get('last_check_in_date'))
            already_checked_in = profile.get('last_check_in_date') == today_iso

            if not already_checked_in:
                if last_check_in is not None and (today - last_check_in).days == 1:
                    profile['consecutive_days'] = int(profile.get('consecutive_days', 0)) + 1
                else:
                    profile['consecutive_days'] = 1
                profile['total_check_ins'] = int(profile.get('total_check_ins', 0)) + 1
                profile['bond_score'] = min(100, int(profile.get('bond_score', 0)) + 3)
                profile['last_check_in_date'] = today_iso

            profile['last_goal'] = payload.today_goal
            profile['last_mood'] = payload.mood
            profile['updated_at'] = datetime.now(UTC).isoformat()

            credits_awarded = 0
            if not already_checked_in:
                credits_awarded = 15
                ctx.append_credit_fn(auth.tenant_id, credits_awarded, 'ai_best_friend_daily_check_in')
                ctx.append_notification_fn(
                    auth.tenant_id,
                    'Companion Check-in Complete',
                    f'You earned {credits_awarded} AI credits for your daily companion check-in.',
                    'engagement',
                )

            ctx.append_audit_fn(auth.tenant_id, 'ai_best_friend_check_in', {
                'already_checked_in': already_checked_in,
                'mood': payload.mood,
                'energy': payload.energy,
                'today_goal': payload.today_goal,
                'credits_awarded': credits_awarded,
            })
            snapshot = profile.copy()

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'already_checked_in': already_checked_in,
            'credits_awarded': credits_awarded,
            'profile': snapshot,
        }

    @router.post('/engagement/ai-best-friend/message')
    def ai_best_friend_message(payload: CompanionMessageRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:ai-best-friend:message', 180, 60)
        with ctx.lock:
            profile = ctx.get_companion_profile_fn(auth.tenant_id)
            reply = ctx.companion_reply_fn(profile, payload.message)
            event: dict[str, Any] = {
                'id': len(ctx.companion_messages_memory) + 1,
                'tenant_id': auth.tenant_id,
                'message': payload.message,
                'reply': reply,
                'created_at': datetime.now(UTC).isoformat(),
            }
            ctx.companion_messages_memory.append(event)

            profile['last_message_at'] = event['created_at']
            profile['bond_score'] = min(100, int(profile.get('bond_score', 0)) + 1)
            profile['updated_at'] = event['created_at']

            ctx.append_audit_fn(auth.tenant_id, 'ai_best_friend_message', {'message_id': event['id']})
            snapshot = profile.copy()

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'reply': reply,
            'profile': snapshot,
            'message_event': event,
        }

    @router.get('/engagement/ai-best-friend/history')
    def ai_best_friend_history(auth: AuthDep, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:ai-best-friend:history', 240, 60)
        with ctx.lock:
            history = [
                item.copy()
                for item in ctx.companion_messages_memory
                if item.get('tenant_id') == auth.tenant_id
            ]
        history.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(history), 'history': history[:limit]}


def _register_fomo_routes(router: APIRouter, ctx: CompanionSocialContext) -> None:
    @router.get('/engagement/fomo/rules')
    def fomo_rules(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:fomo:rules:get', 180, 60)
        with ctx.lock:
            rules = [item.copy() for item in ctx.get_default_fomo_rules_fn(auth.tenant_id)]
        rules.sort(key=lambda item: int(item.get('id', 0)))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(rules), 'rules': rules}

    @router.post('/engagement/fomo/rules')
    def create_fomo_rule(payload: FomoRuleRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:fomo:rules:create', 60, 60)
        with ctx.lock:
            ctx.get_default_fomo_rules_fn(auth.tenant_id)
            now_iso = datetime.now(UTC).isoformat()
            rule: dict[str, Any] = {
                'id': len(ctx.fomo_rules_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'trigger_type': payload.trigger_type,
                'threshold': payload.threshold,
                'window_minutes': payload.window_minutes,
                'active': True,
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.fomo_rules_memory.append(rule)
            ctx.append_audit_fn(auth.tenant_id, 'fomo_rule_created', {'rule_id': rule['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'rule': rule}

    @router.post('/engagement/fomo/trigger', responses={404: {'description': 'FOMO rule not found.'}, 422: {'description': 'FOMO rule is inactive.'}})
    def trigger_fomo(payload: FomoTriggerRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:fomo:trigger', 120, 60)
        with ctx.lock:
            ctx.get_default_fomo_rules_fn(auth.tenant_id)
            rule = next(
                (
                    item for item in ctx.fomo_rules_memory
                    if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.rule_id)
                ),
                None,
            )
            if rule is None:
                raise HTTPException(status_code=404, detail=ctx.fomo_rule_not_found)
            if not bool(rule.get('active', True)):
                raise HTTPException(status_code=422, detail=ctx.fomo_rule_inactive)

            event: dict[str, Any] = {
                'id': len(ctx.fomo_events_memory) + 1,
                'tenant_id': auth.tenant_id,
                'rule_id': int(rule['id']),
                'title': payload.title,
                'message': payload.message,
                'priority': payload.priority,
                'trigger_type': rule.get('trigger_type'),
                'threshold': int(rule.get('threshold', 1)),
                'window_minutes': int(rule.get('window_minutes', 60)),
                'created_at': datetime.now(UTC).isoformat(),
            }
            ctx.fomo_events_memory.append(event)

            ctx.append_notification_fn(auth.tenant_id, payload.title, payload.message, 'fomo')
            ctx.append_audit_fn(auth.tenant_id, 'fomo_trigger_fired', {'event_id': event['id'], 'rule_id': event['rule_id']})

        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'event': event}

    @router.get('/engagement/fomo/feed')
    def fomo_feed(auth: AuthDep, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:fomo:feed', 240, 60)
        with ctx.lock:
            events = [item.copy() for item in ctx.fomo_events_memory if item.get('tenant_id') == auth.tenant_id]
        events.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(events), 'events': events[:limit]}


def _register_social_proof_routes(router: APIRouter, ctx: CompanionSocialContext) -> None:
    @router.post('/engagement/social-proof/events')
    def create_social_proof_event(payload: SocialProofEventRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:social-proof:create', 120, 60)
        with ctx.lock:
            event: dict[str, Any] = {
                'id': len(ctx.social_proof_events_memory) + 1,
                'tenant_id': auth.tenant_id,
                'tenant_display_name': ctx.tenant_display_name_fn(auth.tenant_id),
                'actor_name': payload.actor_name.strip() or ctx.tenant_display_name_fn(auth.tenant_id),
                'headline': payload.headline,
                'metric_label': payload.metric_label,
                'metric_value': round(float(payload.metric_value), 2),
                'proof_type': payload.proof_type,
                'boost_points': int(payload.boost_points),
                'created_at': datetime.now(UTC).isoformat(),
            }
            ctx.social_proof_events_memory.append(event)

            ctx.append_notification_fn(
                auth.tenant_id,
                'Success Broadcast Added',
                f"Your social proof event '{payload.headline}' is now visible in the success feed.",
                'social_proof',
            )
            ctx.append_audit_fn(auth.tenant_id, 'social_proof_event_created', {'event_id': event['id']})

        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'event': event}

    @router.get('/engagement/social-proof/feed')
    def social_proof_feed(auth: AuthDep, limit: PaginationLimit = 25, proof_type: OptionalQueryStr = None) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:social-proof:feed', 240, 60)
        with ctx.lock:
            events = [item.copy() for item in ctx.social_proof_events_memory]

        if proof_type:
            filter_value = proof_type.strip().lower()
            events = [item for item in events if str(item.get('proof_type', '')).lower() == filter_value]

        events.sort(
            key=lambda item: (str(item.get('created_at', '')), int(item.get('boost_points', 0))),
            reverse=True,
        )
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(events),
            'events': events[:limit],
        }

    @router.get('/engagement/social-proof/leaderboard')
    def social_proof_leaderboard(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:social-proof:leaderboard', 240, 60)
        with ctx.lock:
            points_by_tenant: dict[str, int] = {}
            wins_by_tenant: dict[str, int] = {}
            last_win_at_by_tenant: dict[str, str] = {}
            for event in ctx.social_proof_events_memory:
                tenant_id = str(event.get('tenant_id', ''))
                if not tenant_id:
                    continue
                points_by_tenant[tenant_id] = points_by_tenant.get(tenant_id, 0) + int(event.get('boost_points', 0))
                wins_by_tenant[tenant_id] = wins_by_tenant.get(tenant_id, 0) + 1
                occurred_at = str(event.get('created_at', ''))
                if occurred_at > last_win_at_by_tenant.get(tenant_id, ''):
                    last_win_at_by_tenant[tenant_id] = occurred_at

            leaderboard_rows: list[dict[str, Any]] = [
                {
                    'tenant_id': tenant_id,
                    'tenant_display_name': ctx.tenant_display_name_fn(tenant_id),
                    'boost_points': points_by_tenant.get(tenant_id, 0),
                    'success_events': wins_by_tenant.get(tenant_id, 0),
                    'last_success_at': last_win_at_by_tenant.get(tenant_id),
                }
                for tenant_id in points_by_tenant
            ]
            leaderboard: list[dict[str, Any]] = sorted(
                leaderboard_rows,
                key=lambda item: (-item['boost_points'], -item['success_events'], item['tenant_id']),
            )[:10]

        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'leaderboard': leaderboard}
