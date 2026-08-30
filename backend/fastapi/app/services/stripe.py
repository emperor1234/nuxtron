"""Stripe Payments Service

Extracted from legacy_main.py: Stripe checkout creation, webhook processing, event listing.
"""

from __future__ import annotations

import os
from typing import Annotated
from urllib.parse import urlparse

import stripe
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from ..deps import AuthContext, require_auth
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit

JsonObject = dict[str, object]
AuthDep = Annotated[AuthContext, Depends(require_auth)]

# ── Memory Store References (set by legacy_main.py) ──────────
_stripe_events_memory = []
_rate_buckets = {}
_rate_lock = None
_verify_stripe_signature = None


def set_memory_stores(
    stripe_events_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
    verify_stripe_signature=None,
) -> None:
    """Inject memory store references and helpers from legacy_main.py."""
    global _stripe_events_memory, _rate_buckets, _rate_lock, _enforce_rate_limit, _verify_stripe_signature
    if stripe_events_memory is not None:
        _stripe_events_memory = stripe_events_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit
    if verify_stripe_signature is not None:
        _verify_stripe_signature = verify_stripe_signature


# ── Stripe Operations ─────────────────────────────────────────


def stripe_create_checkout(payload: StripeCreateCheckoutRequest, auth: AuthDep) -> JsonObject:
    """Create an allowlisted one-time Checkout session.

    Product billing and credit purchases use ``/billing/stripe/*`` instead.
    This compatibility endpoint cannot accept arbitrary Stripe Prices or
    off-site redirect URLs.
    """
    _enforce_rate_limit(f'{auth.tenant_id}:stripe:checkout', limit=60, window_seconds=60)

    secret_key = os.getenv('STRIPE_SECRET_KEY', '').strip()
    if not secret_key:
        raise HTTPException(status_code=503, detail='Stripe is not configured.')

    allowed_prices = {
        item.strip()
        for item in os.getenv('STRIPE_ALLOWED_ONE_TIME_PRICE_IDS', '').split(',')
        if item.strip()
    }
    if payload.price_id not in allowed_prices:
        raise HTTPException(status_code=422, detail='Stripe Price is not allowlisted.')

    site_url = os.getenv('SITE_URL', '').strip()
    site_origin = urlparse(site_url)
    for return_url in (str(payload.success_url), str(payload.cancel_url)):
        parsed = urlparse(return_url)
        if (parsed.scheme, parsed.netloc) != (site_origin.scheme, site_origin.netloc):
            raise HTTPException(status_code=422, detail='Checkout return URL is not allowed.')

    metadata = {
        str(key): str(value)
        for key, value in payload.metadata.items()
        if key not in {'tenant_id', 'user_id', 'customer_id'}
    }
    metadata['tenant_id'] = auth.tenant_id
    params: dict[str, object] = {
        'mode': 'payment',
        'success_url': str(payload.success_url),
        'cancel_url': str(payload.cancel_url),
        'line_items': [{'price': payload.price_id, 'quantity': payload.quantity}],
        'metadata': metadata,
    }
    if payload.customer_email:
        params['customer_email'] = payload.customer_email
    try:
        client = stripe.StripeClient(
            secret_key,
            stripe_version='2026-07-29.dahlia',
            max_network_retries=2,
        )
        session = client.v1.checkout.sessions.create(params)
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail='Stripe could not create Checkout.') from exc
    return {
        'status': 'ok',
        'result': {
            'tenant_id': auth.tenant_id,
            'action': 'create-checkout',
            'delivery_status': 'created',
            'session_id': session.id,
            'checkout_url': session.url,
        },
    }


def stripe_process_webhook(payload: StripeWebhookProcessRequest, auth: AuthDep) -> JsonObject:
    """Reject the legacy JSON webhook simulator.

    Real events must arrive as raw signed requests at
    ``/billing/stripe/webhook``; authenticated clients cannot self-report
    payment events.
    """
    _enforce_rate_limit(f'{auth.tenant_id}:stripe:webhook', limit=300, window_seconds=60)
    _ = payload
    raise HTTPException(
        status_code=410,
        detail='Use the signed /billing/stripe/webhook endpoint.',
    )


def list_stripe_events(auth: AuthDep) -> JsonObject:
    """List Stripe events for a tenant."""
    items: list[JsonObject] = [e for e in _stripe_events_memory if e.get('tenant_id') == auth.tenant_id]
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'events': items}


# ── Request Models ────────────────────────────────────────────


class StripeCreateCheckoutRequest(BaseModel):
    price_id: str = Field(min_length=1, max_length=120)
    success_url: HttpUrl
    cancel_url: HttpUrl
    customer_email: str | None = Field(default=None, max_length=320)
    quantity: int = Field(default=1, ge=1, le=100)
    metadata: dict[str, object] = Field(default_factory=dict)


class StripeWebhookProcessRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    event_id: str = Field(min_length=1, max_length=120)
    data: dict[str, object] = Field(default_factory=dict)
    signature: str | None = Field(default=None, max_length=512)
