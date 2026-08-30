# NEW MODULE — Revenue & Pricing / Billing (Part 4 Section 22)
# Implements subscription tiers, credits, invoices, usage tracking per spec.
# Memory-backed, same router factory pattern.

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..database import get_db_session
from ..deps import AuthContext, require_auth
from ..models import BillingCreditLedger, BillingCreditPurchase, BillingSubscription

# Type alias for dependency injection
AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Subscription plans — exact tiers from Part 4 Section 22.1 ────────────────

PLANS: list[dict[str, Any]] = [
    {
        'id': 'starter',
        'display': 'Starter',
        'price_monthly': 0.0,
        'price_annual': 0.0,
        'currency': 'USD',
        'ai_credits': 100,
        'social_accounts': 3,
        'users': 1,
        'social_platforms': 5,
        'crm_contacts': 500,
        'email_sends_monthly': 1000,
        'seo_keywords': 100,
        'auto_ads_platforms': 0,
        'influencer_db': False,
        'ai_chatbots': 0,
        'review_platforms': 0,
        'cms_connections': 0,
        'linkinbio_pages': 1,
        'landing_pages': 0,
        'api_access': False,
        'white_label': False,
        'support': 'community',
    },
    {
        'id': 'pro',
        'display': 'Pro',
        'price_monthly': 79.0,
        'price_annual': 63.2,
        'currency': 'USD',
        'ai_credits': 5000,
        'social_accounts': 15,
        'users': 3,
        'social_platforms': 15,
        'crm_contacts': 5000,
        'email_sends_monthly': 10000,
        'seo_keywords': 2500,
        'auto_ads_platforms': 1,
        'influencer_db': 'search_only',
        'ai_chatbots': 1,
        'review_platforms': 1,
        'cms_connections': 1,
        'linkinbio_pages': 5,
        'landing_pages': 5,
        'api_access': 'basic',
        'white_label': False,
        'support': 'email',
    },
    {
        'id': 'studio',
        'display': 'Studio',
        'price_monthly': 199.0,
        'price_annual': 159.2,
        'currency': 'USD',
        'ai_credits': 25000,
        'social_accounts': 50,
        'users': 10,
        'social_platforms': 25,
        'crm_contacts': 50000,
        'email_sends_monthly': 100000,
        'seo_keywords': 10000,
        'auto_ads_platforms': 5,
        'influencer_db': 'full_12m',
        'ai_chatbots': 5,
        'review_platforms': 5,
        'cms_connections': 5,
        'linkinbio_pages': 25,
        'landing_pages': 50,
        'api_access': 'standard',
        'white_label': False,
        'support': 'priority_email_chat',
    },
    {
        'id': 'enterprise',
        'display': 'Enterprise',
        'price_monthly': 699.0,
        'price_annual': 559.2,
        'currency': 'USD',
        'ai_credits': 100000,
        'social_accounts': 200,
        'users': -1,
        'social_platforms': 25,
        'crm_contacts': -1,
        'email_sends_monthly': -1,
        'seo_keywords': 50000,
        'auto_ads_platforms': 12,
        'influencer_db': 'full_api',
        'ai_chatbots': -1,
        'review_platforms': 15,
        'cms_connections': 15,
        'linkinbio_pages': -1,
        'landing_pages': -1,
        'api_access': 'full',
        'white_label': True,
        'support': 'dedicated_csm',
    },
    {
        'id': 'agency',
        'display': 'Agency',
        'price_monthly': -1,
        'price_annual': -1,
        'currency': 'USD',
        'ai_credits': -1,
        'social_accounts': -1,
        'users': -1,
        'social_platforms': 25,
        'crm_contacts': -1,
        'email_sends_monthly': -1,
        'seo_keywords': -1,
        'auto_ads_platforms': 12,
        'influencer_db': 'full_custom',
        'ai_chatbots': -1,
        'review_platforms': -1,
        'cms_connections': -1,
        'linkinbio_pages': -1,
        'landing_pages': -1,
        'api_access': 'full_priority',
        'white_label': True,
        'support': 'dedicated_team',
    },
]


# ── Request models ────────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    plan_id: str = Field(min_length=1, max_length=40)
    billing_cycle: str = Field(default='monthly', pattern=r'^(monthly|annual)$')


class CreditsAddRequest(BaseModel):
    amount: int = Field(ge=1, le=1_000_000)
    reason: str = Field(default='purchase', max_length=80)


class CreditsQuoteRequest(BaseModel):
    amount: int = Field(ge=1, le=1_000_000)


class UpgradeRequest(BaseModel):
    new_plan_id: str = Field(min_length=1, max_length=40)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_billing_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    subscriptions_memory: list[dict[str, Any]],
    invoices_memory: list[dict[str, Any]],
    credit_ledger_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter()
    lock = threading.RLock()
    credit_unit_price_usd = 0.02

    def _credits_quote(amount: int) -> dict[str, Any]:
        subtotal = round(amount * credit_unit_price_usd, 2)
        return {
            'credits': amount,
            'unit_price_usd': credit_unit_price_usd,
            'subtotal_usd': subtotal,
            'fees_usd': 0.0,
            'total_usd': subtotal,
        }

    def _audit(tenant_id: str, action: str) -> None:
        with lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'billing-router',
            })

    def _current_subscription(tenant_id: str) -> dict[str, Any] | None:
        with get_db_session() as db:
            persisted = (
                db.query(BillingSubscription)
                .filter(
                    BillingSubscription.tenant_id == tenant_id,
                    BillingSubscription.status.in_(['active', 'trialing', 'past_due']),
                )
                .order_by(BillingSubscription.created_at.desc())
                .first()
            )
            if persisted is not None:
                plan = next((item for item in PLANS if item['id'] == persisted.plan_id), None)
                return {
                    'tenant_id': tenant_id,
                    'plan_id': persisted.plan_id,
                    'plan_display': plan['display'] if plan else persisted.plan_id,
                    'billing_cycle': persisted.billing_cycle,
                    'status': persisted.status,
                    'stripe_subscription_id': persisted.stripe_subscription_id,
                }
        with lock:
            return next(
                (s.copy() for s in subscriptions_memory
                 if s.get('tenant_id') == tenant_id and s.get('status') == 'active'),
                None,
            )

    def _credit_balance(tenant_id: str) -> int:
        with get_db_session() as db:
            persisted = (
                db.query(BillingCreditLedger)
                .filter(BillingCreditLedger.tenant_id == tenant_id)
                .all()
            )
            if persisted:
                return sum(item.amount for item in persisted)
        with lock:
            return sum(int(e.get('amount', 0)) for e in credit_ledger_memory if e.get('tenant_id') == tenant_id)

    @router.get('/billing/plans')
    def list_plans(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:billing:plans', 120, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(PLANS),
            'plans': PLANS,
            'trial_days': 14,
            'annual_discount_pct': 20,
        }

    @router.post('/billing/subscribe', responses={422: {'description': 'Unknown plan'}})
    def subscribe(  # pyright: ignore[reportUnusedFunction]
        payload: SubscribeRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:billing:subscribe', 10, 60)
        plan = next((p for p in PLANS if p['id'] == payload.plan_id), None)
        if plan is None:
            raise HTTPException(status_code=422, detail=f'Unknown plan: {payload.plan_id}')
        if payload.plan_id != 'starter':
            raise HTTPException(
                status_code=409,
                detail='Paid subscriptions must be created through Stripe Checkout.',
            )

        now = datetime.now(UTC).isoformat()
        with lock:
            # Cancel any existing active subscriptions for this tenant.
            for sub in subscriptions_memory:
                if sub.get('tenant_id') == auth.tenant_id and sub.get('status') == 'active':
                    sub['status'] = 'cancelled'
                    sub['cancelled_at'] = now

            price = plan['price_annual'] if payload.billing_cycle == 'annual' else plan['price_monthly']
            sub: dict[str, Any] = {
                'id': len(subscriptions_memory) + 1,
                'tenant_id': auth.tenant_id,
                'plan_id': payload.plan_id,
                'plan_display': plan['display'],
                'billing_cycle': payload.billing_cycle,
                'price': price,
                'currency': plan['currency'],
                'status': 'active',
                'trial_ends_at': None,
                'created_at': now,
                'updated_at': now,
            }
            subscriptions_memory.append(sub)

            # Seed credits for the plan.
            plan_credits = int(plan.get('ai_credits') or 0)
            if plan_credits > 0:
                credit_ledger_memory.append({
                    'id': len(credit_ledger_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'amount': plan_credits,
                    'reason': f'subscription_{payload.plan_id}',
                    'created_at': now,
                })

            # Create an invoice.
            invoices_memory.append({
                'id': len(invoices_memory) + 1,
                'tenant_id': auth.tenant_id,
                'subscription_id': sub['id'],
                'amount': price,
                'currency': plan['currency'],
                'status': 'paid' if price > 0 else 'free',
                'created_at': now,
            })

        _audit(auth.tenant_id, f'subscribed_to_{payload.plan_id}')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'subscription': sub, 'credits_added': plan_credits}

    @router.post('/billing/upgrade', responses={422: {'description': 'Unknown plan or no active subscription'}})
    def upgrade(  # pyright: ignore[reportUnusedFunction]
        payload: UpgradeRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:billing:upgrade', 10, 60)
        if not any(p['id'] == payload.new_plan_id for p in PLANS):
            raise HTTPException(status_code=422, detail=f'Unknown plan: {payload.new_plan_id}')
        raise HTTPException(
            status_code=409,
            detail='Subscription changes must be completed in the Stripe customer portal.',
        )

    @router.post('/billing/cancel', responses={422: {'description': 'No active subscription found'}})
    def cancel(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:billing:cancel', 5, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            sub = next(
                (s for s in subscriptions_memory
                 if s.get('tenant_id') == auth.tenant_id and s.get('status') == 'active'),
                None,
            )
            if sub is None:
                raise HTTPException(status_code=422, detail='No active subscription found.')
            if sub.get('stripe_subscription_id'):
                raise HTTPException(
                    status_code=409,
                    detail='Stripe subscriptions must be cancelled in the customer portal.',
                )
            sub['status'] = 'cancelled'
            sub['cancelled_at'] = now
            sub['updated_at'] = now
            snapshot = sub.copy()

        _audit(auth.tenant_id, 'subscription_cancelled')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'subscription': snapshot}

    @router.post('/billing/credits', responses={409: {'description': 'Direct credit mutation disabled'}})
    def add_credits(  # pyright: ignore[reportUnusedFunction]
        payload: CreditsAddRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:billing:credits', 30, 60)
        raise HTTPException(
            status_code=409,
            detail='Direct credit mutation is disabled. Use /billing/credits/checkout and /billing/credits/confirm after payment is received.',
        )

    @router.post('/billing/credits/quote')
    def quote_credits(  # pyright: ignore[reportUnusedFunction]
        payload: CreditsQuoteRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:billing:credits:quote', 60, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'quote': _credits_quote(payload.amount),
        }

    @router.post('/billing/credits/checkout')
    def legacy_checkout_credits(auth: AuthDep) -> None:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:billing:credits:checkout', 20, 60)
        raise HTTPException(
            status_code=409,
            detail='Credit purchases must be created through Stripe Checkout.',
        )

    @router.post('/billing/credits/confirm')
    def legacy_confirm_credits(auth: AuthDep) -> None:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:billing:credits:confirm', 30, 60)
        raise HTTPException(
            status_code=409,
            detail='Client-side payment confirmation is disabled. Stripe webhooks apply credits.',
        )

    @router.get('/billing/usage')
    def get_usage(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:billing:usage', 120, 60)
        balance = _credit_balance(auth.tenant_id)
        sub = _current_subscription(auth.tenant_id)
        with get_db_session() as db:
            durable_pending = (
                db.query(BillingCreditPurchase)
                .filter(
                    BillingCreditPurchase.tenant_id == auth.tenant_id,
                    BillingCreditPurchase.status.in_(['creating_checkout', 'pending_payment']),
                )
                .count()
            )
        with lock:
            memory_pending = sum(
                1
                for item in invoices_memory
                if item.get('tenant_id') == auth.tenant_id
                and item.get('invoice_type') == 'credit_topup'
                and item.get('status') == 'pending_payment'
            )
            pending_credit_topups = durable_pending or memory_pending
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'credit_balance': balance,
            'pending_credit_topups': pending_credit_topups,
            'current_plan': sub['plan_id'] if sub else 'starter',
            'plan_display': sub['plan_display'] if sub else 'Starter',
            'billing_cycle': sub['billing_cycle'] if sub else None,
        }

    @router.get('/billing/invoices')
    def list_invoices(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:billing:invoices', 120, 60)
        with get_db_session() as db:
            purchases = (
                db.query(BillingCreditPurchase)
                .filter(BillingCreditPurchase.tenant_id == auth.tenant_id)
                .all()
            )
        with lock:
            items = [i.copy() for i in invoices_memory if i.get('tenant_id') == auth.tenant_id]
        known_sessions = {str(item.get('stripe_checkout_session_id') or '') for item in items}
        for purchase in purchases:
            if purchase.stripe_checkout_session_id in known_sessions:
                continue
            items.append({
                'id': purchase.id,
                'tenant_id': purchase.tenant_id,
                'amount': purchase.amount_cents / 100,
                'currency': purchase.currency.upper(),
                'status': purchase.status,
                'created_at': purchase.created_at.isoformat(),
                'invoice_type': 'credit_topup',
                'credits_requested': purchase.credits,
                'stripe_checkout_session_id': purchase.stripe_checkout_session_id,
            })
        items.sort(key=lambda i: str(i.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'invoices': items}

    return router
