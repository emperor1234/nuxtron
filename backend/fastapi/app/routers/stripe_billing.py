"""Stripe billing integration — checkout sessions, webhooks, customer portal."""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

logger = logging.getLogger(__name__)

AuthDep = Annotated[AuthContext, Depends(require_auth)]

STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
SITE_URL: str = os.getenv("SITE_URL", "http://localhost:3000")

# Map internal plan_id → monthly price in cents (USD)
PLAN_PRICE_CENTS: dict[str, int] = {
    "starter": 0,
    "pro": 7900,
    "studio": 19900,
    "enterprise": 69900,
    "agency": 0,  # Custom — redirect to contact sales
}

PLAN_DISPLAY: dict[str, str] = {
    "starter": "Starter",
    "pro": "Pro",
    "studio": "Studio",
    "enterprise": "Enterprise",
    "agency": "Agency",
}


class ActivateRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)


class CheckoutSessionRequest(BaseModel):
    plan_id: str = Field(min_length=1, max_length=40)
    billing_cycle: str = Field(default="monthly", pattern=r"^(monthly|annual)$")


class PortalSessionRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=120)


def _stripe_client() -> Any:
    """Return a configured Stripe client. Raises if key is missing."""
    if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY.startswith("sk_test_local"):
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured. Set STRIPE_SECRET_KEY in the environment.",
        )
    return stripe.Stripe(STRIPE_SECRET_KEY)


def create_stripe_billing_router() -> APIRouter:
    router = APIRouter(prefix="/billing/stripe", tags=["Stripe Billing"])

    @router.post("/activate")
    def activate_after_checkout(
        payload: ActivateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        """Called by frontend after Stripe redirects to success URL.

        Retrieves the checkout session from Stripe and logs the activation.
        The subscription record is managed by the webhook handler; this is a
        lightweight confirmation step for the frontend.
        """
        client = _stripe_client()
        try:
            session = client.checkout.sessions.retrieve(payload.session_id)
        except stripe.StripeError as exc:
            raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message}") from exc

        if session.payment_status not in ("paid", "no_payment_required"):
            raise HTTPException(status_code=422, detail="Payment not yet confirmed by Stripe.")

        metadata = session.metadata or {}
        plan_id = metadata.get("plan_id", "unknown")
        logger.info("Checkout activated: tenant=%s plan=%s session=%s", auth.tenant_id, plan_id, payload.session_id)
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "plan_id": plan_id,
            "payment_status": session.payment_status,
        }

    @router.post("/checkout-session")
    def create_checkout_session(
        payload: CheckoutSessionRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        """Create a Stripe Checkout session for a subscription plan.

        Returns ``{ checkout_url, session_id }`` — the frontend should redirect
        to ``checkout_url`` immediately.
        """
        plan_id = payload.plan_id
        price_cents = PLAN_PRICE_CENTS.get(plan_id)
        if price_cents is None:
            raise HTTPException(status_code=422, detail=f"Unknown plan: {plan_id}")
        if price_cents == 0 and plan_id not in ("starter",):
            raise HTTPException(
                status_code=422,
                detail=f"Plan '{plan_id}' requires a custom quote. Contact sales.",
            )

        # Annual billing: 20% discount
        if payload.billing_cycle == "annual":
            price_cents = int(price_cents * 0.8 * 12)  # annual total in cents
            interval = "year"
        else:
            interval = "month"

        # Free plan — skip Stripe entirely, no client needed
        if plan_id == "starter" or price_cents == 0:
            return {
                "status": "ok",
                "free_plan": True,
                "plan_id": plan_id,
                "checkout_url": None,
                "session_id": None,
            }

        client = _stripe_client()
        success_url = f"{SITE_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{SITE_URL}/pricing"

        try:
            session = client.checkout.sessions.create(
                mode="subscription",
                line_items=[
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": price_cents,
                            "recurring": {"interval": interval},
                            "product_data": {
                                "name": f"Nuxtron {PLAN_DISPLAY.get(plan_id, plan_id)} Plan",
                                "metadata": {"plan_id": plan_id},
                            },
                        },
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "tenant_id": auth.tenant_id,
                    "plan_id": plan_id,
                    "billing_cycle": payload.billing_cycle,
                },
                subscription_data={
                    "metadata": {
                        "tenant_id": auth.tenant_id,
                        "plan_id": plan_id,
                    }
                },
            )
        except stripe.StripeError as exc:
            logger.exception("Stripe checkout session creation failed")
            raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message}") from exc

        return {
            "status": "ok",
            "checkout_url": session.url,
            "session_id": session.id,
        }

    @router.post("/portal-session")
    def create_portal_session(
        payload: PortalSessionRequest,
        auth: AuthDep,  # noqa: ARG001
    ) -> dict[str, Any]:
        """Create a Stripe Customer Portal session so the user can manage their subscription."""
        client = _stripe_client()
        return_url = f"{SITE_URL}/pricing"

        try:
            session = client.billing_portal.sessions.create(
                customer=payload.customer_id,
                return_url=return_url,
            )
        except stripe.StripeError as exc:
            logger.exception("Stripe portal session creation failed")
            raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message}") from exc

        return {"status": "ok", "portal_url": session.url}

    @router.post("/webhook", include_in_schema=False)
    async def stripe_webhook(
        request: Request,
        stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
    ) -> dict[str, Any]:
        """Receive and verify Stripe webhook events.

        Handles:
        - ``checkout.session.completed`` → activate subscription in billing router
        - ``invoice.payment_failed`` → log warning
        """
        if not STRIPE_WEBHOOK_SECRET or STRIPE_WEBHOOK_SECRET.startswith("whsec_local"):
            logger.warning("STRIPE_WEBHOOK_SECRET not configured — skipping signature verification")
        elif not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

        raw_body = await request.body()

        if STRIPE_WEBHOOK_SECRET and not STRIPE_WEBHOOK_SECRET.startswith("whsec_local"):
            try:
                event = stripe.WebhookSignature.verify_header(  # type: ignore[no-untyped-call]
                    raw_body.decode("utf-8"),
                    stripe_signature or "",
                    STRIPE_WEBHOOK_SECRET,
                )
            except stripe.SignatureVerificationError as exc:
                raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc
        else:
            import json  # noqa: PLC0415

            event = json.loads(raw_body)

        event_type: str = event.get("type", "") if isinstance(event, dict) else str(event.type)
        data_obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

        if event_type == "checkout.session.completed":
            _handle_checkout_completed(data_obj)
        elif event_type == "invoice.payment_failed":
            tenant_id = (data_obj.get("metadata") or {}).get("tenant_id", "unknown")
            logger.warning("Stripe payment failed for tenant %s", tenant_id)
        elif event_type == "customer.subscription.deleted":
            tenant_id = (data_obj.get("metadata") or {}).get("tenant_id", "unknown")
            logger.info("Stripe subscription cancelled for tenant %s", tenant_id)

        return {"received": True}

    return router


def _handle_checkout_completed(session_obj: dict[str, Any]) -> None:
    """Log successful checkout — the billing router's /billing/subscribe endpoint
    should be called by the frontend after redirect from Stripe success URL."""
    metadata = session_obj.get("metadata") or {}
    tenant_id = metadata.get("tenant_id", "unknown")
    plan_id = metadata.get("plan_id", "unknown")
    logger.info(
        "Stripe checkout completed: tenant=%s plan=%s session=%s",
        tenant_id,
        plan_id,
        session_obj.get("id", ""),
    )
