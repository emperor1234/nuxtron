import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

ALREADY_CLAIMED = 'This tenant has already claimed a referral reward.'


class ReferralClaimRequest(BaseModel):
    referral_code: str = Field(min_length=4, max_length=40)
    referred_email: str = Field(default='', max_length=320)


@dataclass
class ReferralsContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    referrals_memory: list[dict[str, Any]]
    referral_claims_memory: list[dict[str, Any]]
    refferq_jobs_memory: list[dict[str, Any]]
    referral_rewards: dict[str, int]
    get_referral_profile_fn: Callable[[str], dict[str, Any]]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[..., None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]
    referral_not_found: str
    self_referral_not_allowed: str


def register_referrals_routes(*, router: APIRouter, context: ReferralsContext) -> None:
    _register_referral_read_routes(router, context)
    _register_referral_write_routes(router, context)


def _register_referral_read_routes(router: APIRouter, ctx: ReferralsContext) -> None:
    @router.get('/engagement/referrals')
    def get_referrals(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:referrals:get', 120, 60)
        with ctx.lock:
            profile = ctx.get_referral_profile_fn(auth.tenant_id).copy()
            claims = [
                item.copy()
                for item in ctx.referral_claims_memory
                if item.get('referrer_tenant_id') == auth.tenant_id
                or item.get('referred_tenant_id') == auth.tenant_id
            ]
        claims.sort(key=lambda item: str(item.get('claimed_at', '')), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'referral_rewards': ctx.referral_rewards,
            'profile': profile,
            'claims': claims,
        }

    @router.post('/engagement/referrals/generate-code')
    def generate_referral_code(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:referrals:generate', 30, 60)
        with ctx.lock:
            profile = ctx.get_referral_profile_fn(auth.tenant_id)
            profile['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = profile.copy()
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profile': snapshot, 'referral_rewards': ctx.referral_rewards}

    @router.get('/engagement/referrals/leaderboard')
    def referral_leaderboard(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:referrals:leaderboard', 120, 60)
        with ctx.lock:
            _raw: list[dict[str, Any]] = [
                {
                    'tenant_id': str(item.get('tenant_id') or ''),
                    'successful_referrals': int(item.get('successful_referrals', 0)),
                    'total_credits_earned': int(item.get('total_credits_earned', 0)),
                    'last_referral_at': str(item.get('last_referral_at') or ''),
                }
                for item in ctx.referrals_memory
            ]
            leaderboard: list[dict[str, Any]] = sorted(
                _raw,
                key=lambda d: (
                    -d['successful_referrals'],
                    -d['total_credits_earned'],
                    d['tenant_id'],
                ),
            )[:10]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'leaderboard': leaderboard}


def _register_referral_write_routes(router: APIRouter, ctx: ReferralsContext) -> None:
    @router.post(
        '/engagement/referrals/claim',
        responses={
            404: {'description': 'Referral code not found.'},
            409: {'description': 'This tenant has already claimed a referral reward.'},
            422: {'description': 'Self-referral is not allowed.'},
        },
    )
    def claim_referral(payload: ReferralClaimRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:referrals:claim', 30, 60)
        with ctx.lock:
            referrer_profile = next(
                (
                    item for item in ctx.referrals_memory
                    if str(item.get('referral_code', '')).upper() == payload.referral_code.strip().upper()
                ),
                None,
            )
            if referrer_profile is None:
                raise HTTPException(status_code=404, detail=ctx.referral_not_found)

            referrer_tenant_id = str(referrer_profile.get('tenant_id'))
            if referrer_tenant_id == auth.tenant_id:
                raise HTTPException(status_code=422, detail=ctx.self_referral_not_allowed)

            existing_claim = next(
                (item for item in ctx.referral_claims_memory if item.get('referred_tenant_id') == auth.tenant_id),
                None,
            )
            if existing_claim is not None:
                raise HTTPException(status_code=409, detail=ALREADY_CLAIMED)

            now_iso = datetime.now(UTC).isoformat()
            claim: dict[str, Any] = {
                'id': len(ctx.referral_claims_memory) + 1,
                'referral_code': str(referrer_profile.get('referral_code')),
                'referrer_tenant_id': referrer_tenant_id,
                'referred_tenant_id': auth.tenant_id,
                'referred_email': payload.referred_email,
                'referrer_credits': ctx.referral_rewards['referrer_credits'],
                'referred_credits': ctx.referral_rewards['referred_credits'],
                'claimed_at': now_iso,
                'bridge_status': 'queued',
            }
            ctx.referral_claims_memory.append(claim)

            referrer_profile['successful_referrals'] = int(referrer_profile.get('successful_referrals', 0)) + 1
            referrer_profile['total_credits_earned'] = (
                int(referrer_profile.get('total_credits_earned', 0))
                + int(ctx.referral_rewards['referrer_credits'])
            )
            referrer_profile['last_referral_at'] = now_iso
            referrer_profile['updated_at'] = now_iso

            ctx.append_credit_fn(referrer_tenant_id, ctx.referral_rewards['referrer_credits'], 'referral_referrer_reward')
            ctx.append_credit_fn(auth.tenant_id, ctx.referral_rewards['referred_credits'], 'referral_referred_reward')
            ctx.append_notification_fn(
                referrer_tenant_id,
                'Referral Reward Unlocked',
                f'You earned {ctx.referral_rewards["referrer_credits"]} AI credits from a successful referral.',
            )
            ctx.append_notification_fn(
                auth.tenant_id,
                'Welcome Referral Reward',
                f'You earned {ctx.referral_rewards["referred_credits"]} AI credits for joining via referral.',
            )

            ctx.refferq_jobs_memory.append({
                'id': len(ctx.refferq_jobs_memory) + 1,
                'tenant_id': referrer_tenant_id,
                'status': 'queued',
                'reason': 'Platform-native referral mirrored to bridge queue',
                'referral': {
                    'referral_code': claim['referral_code'],
                    'referrer_tenant_id': referrer_tenant_id,
                    'referred_tenant_id': auth.tenant_id,
                },
                'created_at': now_iso,
            })

            ctx.append_audit_fn(referrer_tenant_id, 'referral_reward_referrer', {'claim_id': claim['id']})
            ctx.append_audit_fn(auth.tenant_id, 'referral_reward_referred', {'claim_id': claim['id']})

        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'claim': claim, 'referral_rewards': ctx.referral_rewards}
