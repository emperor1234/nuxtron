# NEW MODULE — Revenue & Pricing / Billing (Part 4 Section 22)
# Implements subscription tiers, credits, invoices, usage tracking per spec.
# Memory-backed, same router factory pattern.

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

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
    payment_method_id: str = Field(default='', max_length=120)


class CreditsAddRequest(BaseModel):
    amount: int = Field(ge=1, le=1_000_000)
    reason: str = Field(default='purchase', max_length=80)


class CreditsQuoteRequest(BaseModel):
    amount: int = Field(ge=1, le=1_000_000)


class CreditsCheckoutRequest(BaseModel):
    amount: int = Field(ge=1, le=1_000_000)
    payment_provider: str = Field(default='manual', max_length=40)
    payment_method_id: str = Field(min_length=1, max_length=120)


class CreditsConfirmRequest(BaseModel):
    invoice_id: int = Field(ge=1)
    payment_reference: str = Field(min_length=1, max_length=120)
    provider_transaction_id: str = Field(min_length=1, max_length=160)
    amount_usd: float = Field(gt=0)


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
        with lock:
            return next(
                (s.copy() for s in subscriptions_memory
                 if s.get('tenant_id') == tenant_id and s.get('status') == 'active'),
                None,
            )

    def _credit_balance(tenant_id: str) -> int:
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
        plan = next((p for p in PLANS if p['id'] == payload.new_plan_id), None)
        if plan is None:
            raise HTTPException(status_code=422, detail=f'Unknown plan: {payload.new_plan_id}')

        now = datetime.now(UTC).isoformat()
        with lock:
            current = next(
                (s for s in subscriptions_memory
                 if s.get('tenant_id') == auth.tenant_id and s.get('status') == 'active'),
                None,
            )
            if current:
                current['plan_id'] = payload.new_plan_id
                current['plan_display'] = plan['display']
                current['price'] = plan['price_monthly']
                current['updated_at'] = now
                snapshot = current.copy()
            else:
                raise HTTPException(status_code=422, detail='No active subscription to upgrade.')

        _audit(auth.tenant_id, f'upgraded_to_{payload.new_plan_id}')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'subscription': snapshot}

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
    def checkout_credits(  # pyright: ignore[reportUnusedFunction]
        payload: CreditsCheckoutRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:billing:credits:checkout', 20, 60)
        now = datetime.now(UTC).isoformat()
        quote = _credits_quote(payload.amount)
        with lock:
            invoice_id = len(invoices_memory) + 1
            payment_reference = f'credit_topup_{auth.tenant_id}_{invoice_id}'
            invoice = {
                'id': invoice_id,
                'tenant_id': auth.tenant_id,
                'subscription_id': None,
                'amount': quote['total_usd'],
                'currency': 'USD',
                'status': 'pending_payment',
                'created_at': now,
                'invoice_type': 'credit_topup',
                'credits_requested': payload.amount,
                'payment_provider': payload.payment_provider,
                'payment_method_id': payload.payment_method_id,
                'payment_reference': payment_reference,
                'credits_applied': False,
            }
            invoices_memory.append(invoice)

        _audit(auth.tenant_id, 'credit_checkout_created')
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'invoice': invoice,
            'quote': quote,
        }

    @router.post('/billing/credits/confirm', responses={422: {'description': 'Invoice mismatch or invalid payment confirmation'}})
    def confirm_credits(  # pyright: ignore[reportUnusedFunction]
        payload: CreditsConfirmRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:billing:credits:confirm', 30, 60)
        now = datetime.now(UTC).isoformat()
        with lock:
            invoice = next(
                (
                    item for item in invoices_memory
                    if item.get('id') == payload.invoice_id and item.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if invoice is None or invoice.get('invoice_type') != 'credit_topup':
                raise HTTPException(status_code=422, detail='Unknown credit top-up invoice.')
            if invoice.get('payment_reference') != payload.payment_reference:
                raise HTTPException(status_code=422, detail='Payment reference mismatch.')
            if invoice.get('credits_applied'):
                balance = _credit_balance(auth.tenant_id)
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'credits_added': 0,
                    'new_balance': balance,
                    'invoice': invoice,
                }
            expected_total = float(invoice.get('amount') or 0)
            received_total = round(float(payload.amount_usd), 2)
            if received_total != expected_total:
                raise HTTPException(status_code=422, detail='Confirmed payment amount does not match invoice total.')

            credits_requested = int(invoice.get('credits_requested') or 0)
            ledger_entry: dict[str, Any] = {
                'id': len(credit_ledger_memory) + 1,
                'tenant_id': auth.tenant_id,
                'amount': credits_requested,
                'reason': 'confirmed_credit_topup',
                'created_at': now,
                'invoice_id': invoice['id'],
                'payment_reference': payload.payment_reference,
                'provider_transaction_id': payload.provider_transaction_id,
            }
            credit_ledger_memory.append(ledger_entry)
            invoice['status'] = 'paid'
            invoice['paid_at'] = now
            invoice['provider_transaction_id'] = payload.provider_transaction_id
            invoice['credits_applied'] = True
            balance = _credit_balance(auth.tenant_id)

        _audit(auth.tenant_id, 'credits_confirmed_after_payment')
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'credits_added': credits_requested,
            'new_balance': balance,
            'invoice': invoice,
        }

    @router.get('/billing/usage')
    def get_usage(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:billing:usage', 120, 60)
        balance = _credit_balance(auth.tenant_id)
        sub = _current_subscription(auth.tenant_id)
        with lock:
            pending_credit_topups = sum(
                1
                for item in invoices_memory
                if item.get('tenant_id') == auth.tenant_id
                and item.get('invoice_type') == 'credit_topup'
                and item.get('status') == 'pending_payment'
            )
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
        with lock:
            items = [i.copy() for i in invoices_memory if i.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda i: str(i.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'invoices': items}

    return router
