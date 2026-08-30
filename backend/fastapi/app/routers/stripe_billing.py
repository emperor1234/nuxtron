"""Secure Stripe Billing integration.

Stripe Checkout is the only path that can create a paid subscription or credit
purchase. Stripe-signed webhooks are the only path that can activate paid
entitlements. Client input selects a plan or credit quantity; it never supplies
a Price, amount, customer, payment status, or tenant.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import string
import threading
from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import urlparse

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ..database import get_db_session
from ..deps import AuthContext, require_auth
from ..models import (
    BillingCreditLedger,
    BillingCreditPurchase,
    BillingSubscription,
    StripeWebhookEvent,
)
from .billing import PLANS

logger = logging.getLogger(__name__)

AuthDep = Annotated[AuthContext, Depends(require_auth)]
JsonObject = dict[str, Any]

_PLAN_BY_ID = {str(plan["id"]): plan for plan in PLANS}
_PRICE_ENV: dict[tuple[str, str], str] = {
    ("pro", "monthly"): "STRIPE_PRICE_PRO_MONTHLY",
    ("pro", "annual"): "STRIPE_PRICE_PRO_ANNUAL",
    ("studio", "monthly"): "STRIPE_PRICE_STUDIO_MONTHLY",
    ("studio", "annual"): "STRIPE_PRICE_STUDIO_ANNUAL",
    ("enterprise", "monthly"): "STRIPE_PRICE_ENTERPRISE_MONTHLY",
    ("enterprise", "annual"): "STRIPE_PRICE_ENTERPRISE_ANNUAL",
}
_CREDIT_UNIT_PRICE_CENTS = 2
_lock = threading.RLock()


class CheckoutSessionRequest(BaseModel):
    plan_id: str = Field(min_length=1, max_length=40)
    billing_cycle: str = Field(default="monthly", pattern=r"^(monthly|annual)$")
    request_id: str = Field(min_length=16, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")


class CreditCheckoutRequest(BaseModel):
    credits: int = Field(ge=100, le=1_000_000)
    request_id: str = Field(min_length=16, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")


class SessionStatusRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=200, pattern=r"^cs_[A-Za-z0-9_]+$")


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _stripe_client() -> stripe.StripeClient:
    key = _env("STRIPE_SECRET_KEY")
    if not key or key.startswith(("sk_test_local", "rk_test_local")):
        raise HTTPException(status_code=503, detail="Stripe billing is not configured.")
    return stripe.StripeClient(
        key,
        stripe_version="2026-07-29.dahlia",
        max_network_retries=2,
    )


def _site_url() -> str:
    value = _env("SITE_URL") or "http://localhost:4173"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=503, detail="SITE_URL is not a valid absolute URL.")
    if _env("ENVIRONMENT").lower() == "production" and parsed.scheme != "https":
        raise HTTPException(status_code=503, detail="SITE_URL must use HTTPS in production.")
    return value.rstrip("/")


def _price_id(plan_id: str, billing_cycle: str) -> str:
    env_name = _PRICE_ENV.get((plan_id, billing_cycle), "")
    price_id = _env(env_name) if env_name else ""
    if not price_id.startswith("price_"):
        raise HTTPException(
            status_code=503,
            detail=f"Stripe Price is not configured for {plan_id} ({billing_cycle}).",
        )
    return price_id


def _integration_identifier() -> str:
    suffix = "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))
    return f"nuxtron_billing_{suffix}"


def _idempotency_key(kind: str, tenant_id: str, request_id: str) -> str:
    digest = hashlib.sha256(f"{kind}:{tenant_id}:{request_id}".encode()).hexdigest()
    return f"nuxtron_{kind}_{digest}"


def _as_dict(value: Any) -> JsonObject:
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except (TypeError, ValueError):
        return {}


def _metadata(value: Any) -> dict[str, str]:
    return {str(key): str(item) for key, item in _as_dict(value).items()}


def _invoice_subscription_id(invoice: JsonObject) -> str:
    direct = str(invoice.get("subscription") or "")
    if direct:
        return direct
    parent = _as_dict(invoice.get("parent"))
    details = _as_dict(parent.get("subscription_details"))
    return str(details.get("subscription") or "")


def _find_subscription(
    subscriptions: list[JsonObject],
    *,
    tenant_id: str | None = None,
    stripe_subscription_id: str | None = None,
) -> JsonObject | None:
    return next(
        (
            item
            for item in reversed(subscriptions)
            if (tenant_id is None or item.get("tenant_id") == tenant_id)
            and (
                stripe_subscription_id is None
                or item.get("stripe_subscription_id") == stripe_subscription_id
            )
        ),
        None,
    )


def create_stripe_billing_router(
    *,
    subscriptions_memory: list[JsonObject],
    invoices_memory: list[JsonObject],
    credit_ledger_memory: list[JsonObject],
    audit_log_memory: list[JsonObject],
) -> APIRouter:
    router = APIRouter(prefix="/billing/stripe", tags=["Stripe Billing"])

    def event_processed(event_id: str) -> bool:
        with get_db_session() as db:
            return (
                db.query(StripeWebhookEvent)
                .filter(StripeWebhookEvent.event_id == event_id)
                .first()
                is not None
            )

    def mark_event(event_id: str, event_type: str, tenant_id: str = "") -> None:
        with get_db_session() as db:
            db.add(
                StripeWebhookEvent(
                    event_id=event_id,
                    event_type=event_type,
                    tenant_id=tenant_id,
                )
            )
        audit_log_memory.append(
            {
                "id": len(audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": f"stripe_event:{event_id}",
                "event_type": event_type,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "stripe-webhook",
            }
        )

    def activate_subscription(session: JsonObject) -> str:
        metadata = _metadata(session.get("metadata"))
        if metadata.get("kind") != "nuxtron_subscription":
            return ""
        tenant_id = metadata.get("tenant_id", "")
        plan_id = metadata.get("plan_id", "")
        cycle = metadata.get("billing_cycle", "")
        if not tenant_id or plan_id not in _PLAN_BY_ID or cycle not in {"monthly", "annual"}:
            raise ValueError("Stripe subscription metadata is invalid.")
        if session.get("payment_status") not in {"paid", "no_payment_required"}:
            raise ValueError("Stripe Checkout Session is not paid.")

        now = datetime.now(UTC).isoformat()
        stripe_subscription_id = str(session.get("subscription") or "")
        stripe_customer_id = str(session.get("customer") or "")
        checkout_session_id = str(session.get("id") or "")
        if not (
            stripe_subscription_id.startswith("sub_")
            and stripe_customer_id.startswith("cus_")
            and checkout_session_id.startswith("cs_")
        ):
            raise ValueError("Stripe subscription identifiers are invalid.")
        with _lock:
            with get_db_session() as db:
                persisted = (
                    db.query(BillingSubscription)
                    .filter(
                        BillingSubscription.stripe_subscription_id
                        == stripe_subscription_id
                    )
                    .first()
                )
                if persisted is None:
                    for current in (
                        db.query(BillingSubscription)
                        .filter(
                            BillingSubscription.tenant_id == tenant_id,
                            BillingSubscription.status == "active",
                        )
                        .all()
                    ):
                        current.status = "superseded"
                    db.add(
                        BillingSubscription(
                            tenant_id=tenant_id,
                            stripe_subscription_id=stripe_subscription_id,
                            stripe_customer_id=stripe_customer_id,
                            stripe_checkout_session_id=checkout_session_id,
                            plan_id=plan_id,
                            billing_cycle=cycle,
                            status="active",
                        )
                    )
            existing = _find_subscription(
                subscriptions_memory,
                stripe_subscription_id=stripe_subscription_id,
            )
            if existing is not None:
                return tenant_id
            for item in subscriptions_memory:
                if item.get("tenant_id") == tenant_id and item.get("status") == "active":
                    item["status"] = "superseded"
                    item["updated_at"] = now
            plan = _PLAN_BY_ID[plan_id]
            subscriptions_memory.append(
                {
                    "id": len(subscriptions_memory) + 1,
                    "tenant_id": tenant_id,
                    "plan_id": plan_id,
                    "plan_display": plan["display"],
                    "billing_cycle": cycle,
                    "price": plan["price_annual"] if cycle == "annual" else plan["price_monthly"],
                    "currency": "USD",
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                    "stripe_customer_id": stripe_customer_id,
                    "stripe_subscription_id": stripe_subscription_id,
                    "stripe_checkout_session_id": checkout_session_id,
                }
            )
        return tenant_id

    def apply_credit_purchase(session: JsonObject) -> str:
        metadata = _metadata(session.get("metadata"))
        if metadata.get("kind") != "nuxtron_credit_topup":
            return ""
        tenant_id = metadata.get("tenant_id", "")
        try:
            invoice_id = int(metadata.get("invoice_id", "0"))
            credits = int(metadata.get("credits", "0"))
        except ValueError as exc:
            raise ValueError("Stripe credit metadata is invalid.") from exc
        if not tenant_id or invoice_id < 1 or credits < 1:
            raise ValueError("Stripe credit metadata is incomplete.")
        if session.get("payment_status") != "paid":
            raise ValueError("Stripe credit Checkout Session is not paid.")

        with _lock:
            with get_db_session() as db:
                purchase = (
                    db.query(BillingCreditPurchase)
                    .filter(
                        BillingCreditPurchase.id == invoice_id,
                        BillingCreditPurchase.tenant_id == tenant_id,
                    )
                    .first()
                )
                if purchase is None:
                    raise ValueError("Stripe credit purchase was not found.")
                if purchase.stripe_checkout_session_id != session.get("id"):
                    raise ValueError("Stripe Checkout Session does not match the credit purchase.")
                if int(session.get("amount_total") or -1) != purchase.amount_cents:
                    raise ValueError("Stripe payment amount does not match the server purchase.")
                if str(session.get("currency") or "").lower() != purchase.currency:
                    raise ValueError("Stripe payment currency does not match the server purchase.")
                existing_grant = (
                    db.query(BillingCreditLedger)
                    .filter(
                        BillingCreditLedger.stripe_checkout_session_id
                        == session.get("id")
                    )
                    .first()
                )
                if existing_grant is None:
                    db.add(
                        BillingCreditLedger(
                            tenant_id=tenant_id,
                            amount=purchase.credits,
                            reason="stripe_credit_topup",
                            stripe_checkout_session_id=str(session.get("id") or ""),
                        )
                    )
                purchase.status = "paid"
                purchase.stripe_payment_intent_id = str(
                    session.get("payment_intent") or ""
                )
            invoice = next(
                (
                    item
                    for item in invoices_memory
                    if item.get("id") == invoice_id
                    and item.get("tenant_id") == tenant_id
                    and item.get("invoice_type") == "credit_topup"
                ),
                None,
            )
            if invoice is None:
                raise ValueError("Stripe credit invoice was not found.")
            if invoice.get("stripe_checkout_session_id") != session.get("id"):
                raise ValueError("Stripe Checkout Session does not match the credit invoice.")
            expected_cents = int(invoice.get("amount_cents") or 0)
            if int(session.get("amount_total") or -1) != expected_cents:
                raise ValueError("Stripe payment amount does not match the server invoice.")
            if str(session.get("currency") or "").lower() != "usd":
                raise ValueError("Stripe payment currency does not match the server invoice.")
            if invoice.get("credits_applied"):
                return tenant_id
            credit_ledger_memory.append(
                {
                    "id": len(credit_ledger_memory) + 1,
                    "tenant_id": tenant_id,
                    "amount": credits,
                    "reason": "stripe_credit_topup",
                    "created_at": datetime.now(UTC).isoformat(),
                    "invoice_id": invoice_id,
                    "stripe_checkout_session_id": str(session.get("id") or ""),
                    "stripe_payment_intent_id": str(session.get("payment_intent") or ""),
                }
            )
            invoice["status"] = "paid"
            invoice["paid_at"] = datetime.now(UTC).isoformat()
            invoice["credits_applied"] = True
        return tenant_id

    def update_subscription_status(obj: JsonObject, status: str) -> str:
        metadata = _metadata(obj.get("metadata"))
        tenant_id = metadata.get("tenant_id", "")
        stripe_subscription_id = _invoice_subscription_id(obj) or str(obj.get("id") or "")
        with _lock:
            with get_db_session() as db:
                persisted = (
                    db.query(BillingSubscription)
                    .filter(
                        BillingSubscription.stripe_subscription_id
                        == stripe_subscription_id
                    )
                    .first()
                )
                if persisted is not None:
                    persisted.status = status
                    tenant_id = persisted.tenant_id
            subscription = _find_subscription(
                subscriptions_memory,
                tenant_id=tenant_id or None,
                stripe_subscription_id=stripe_subscription_id or None,
            )
            if subscription is not None:
                subscription["status"] = status
                subscription["updated_at"] = datetime.now(UTC).isoformat()
                tenant_id = str(subscription.get("tenant_id") or tenant_id)
        return tenant_id

    def apply_subscription_credits(invoice: JsonObject) -> str:
        stripe_invoice_id = str(invoice.get("id") or "")
        stripe_subscription_id = _invoice_subscription_id(invoice)
        if not stripe_invoice_id.startswith("in_") or not stripe_subscription_id.startswith("sub_"):
            return ""
        with _lock, get_db_session() as db:
            subscription = (
                db.query(BillingSubscription)
                .filter(
                    BillingSubscription.stripe_subscription_id
                    == stripe_subscription_id
                )
                .first()
            )
            if subscription is None:
                return ""
            existing = (
                db.query(BillingCreditLedger)
                .filter(BillingCreditLedger.stripe_invoice_id == stripe_invoice_id)
                .first()
            )
            if existing is not None:
                return subscription.tenant_id
            plan = _PLAN_BY_ID.get(subscription.plan_id)
            monthly_credits = int((plan or {}).get("ai_credits") or 0)
            credits = monthly_credits * (12 if subscription.billing_cycle == "annual" else 1)
            if credits <= 0:
                return subscription.tenant_id
            db.add(
                BillingCreditLedger(
                    tenant_id=subscription.tenant_id,
                    amount=credits,
                    reason=f"stripe_subscription_{subscription.plan_id}",
                    stripe_invoice_id=stripe_invoice_id,
                )
            )
            credit_ledger_memory.append(
                {
                    "id": len(credit_ledger_memory) + 1,
                    "tenant_id": subscription.tenant_id,
                    "amount": credits,
                    "reason": f"stripe_subscription_{subscription.plan_id}",
                    "created_at": datetime.now(UTC).isoformat(),
                    "stripe_invoice_id": stripe_invoice_id,
                }
            )
            return subscription.tenant_id

    @router.post("/checkout-session")
    def create_checkout_session(payload: CheckoutSessionRequest, auth: AuthDep) -> JsonObject:
        plan = _PLAN_BY_ID.get(payload.plan_id)
        if plan is None:
            raise HTTPException(status_code=422, detail=f"Unknown plan: {payload.plan_id}")
        if payload.plan_id == "starter":
            return {
                "status": "ok",
                "free_plan": True,
                "plan_id": "starter",
                "checkout_url": None,
                "session_id": None,
            }
        if payload.plan_id == "agency":
            raise HTTPException(status_code=422, detail="Agency plans require a custom quote.")
        with get_db_session() as db:
            active = (
                db.query(BillingSubscription)
                .filter(
                    BillingSubscription.tenant_id == auth.tenant_id,
                    BillingSubscription.status.in_(["active", "trialing", "past_due"]),
                )
                .first()
            )
            if active is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Manage the existing subscription in the Stripe customer portal.",
                )

        client = _stripe_client()
        site_url = _site_url()
        params: JsonObject = {
            "mode": "subscription",
            "line_items": [{"price": _price_id(payload.plan_id, payload.billing_cycle), "quantity": 1}],
            "success_url": f"{site_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{site_url}/billing",
            "client_reference_id": auth.tenant_id,
            "metadata": {
                "kind": "nuxtron_subscription",
                "tenant_id": auth.tenant_id,
                "plan_id": payload.plan_id,
                "billing_cycle": payload.billing_cycle,
            },
            "subscription_data": {
                "metadata": {
                    "kind": "nuxtron_subscription",
                    "tenant_id": auth.tenant_id,
                    "plan_id": payload.plan_id,
                    "billing_cycle": payload.billing_cycle,
                }
            },
            "integration_identifier": _integration_identifier(),
            "allow_promotion_codes": True,
        }
        if "@" in auth.subject:
            params["customer_email"] = auth.subject
        try:
            session = client.v1.checkout.sessions.create(
                params,
                options={
                    "idempotency_key": _idempotency_key(
                        "subscription", auth.tenant_id, payload.request_id
                    )
                },
            )
        except stripe.StripeError as exc:
            logger.exception("Stripe subscription Checkout creation failed")
            raise HTTPException(status_code=502, detail="Stripe could not create Checkout.") from exc
        return {"status": "ok", "checkout_url": session.url, "session_id": session.id}

    @router.post("/credit-checkout-session")
    def create_credit_checkout(payload: CreditCheckoutRequest, auth: AuthDep) -> JsonObject:
        client = _stripe_client()
        site_url = _site_url()
        amount_cents = payload.credits * _CREDIT_UNIT_PRICE_CENTS
        now = datetime.now(UTC).isoformat()
        durable_request_id = _idempotency_key(
            "credits", auth.tenant_id, payload.request_id
        )
        with get_db_session() as db:
            existing = (
                db.query(BillingCreditPurchase)
                .filter(BillingCreditPurchase.request_id == durable_request_id)
                .first()
            )
            if existing is not None and existing.stripe_checkout_session_id:
                session = client.v1.checkout.sessions.retrieve(
                    existing.stripe_checkout_session_id
                )
                return {
                    "status": "ok",
                    "checkout_url": session.url,
                    "session_id": session.id,
                    "invoice_id": existing.id,
                }
            purchase = BillingCreditPurchase(
                tenant_id=auth.tenant_id,
                request_id=durable_request_id,
                credits=payload.credits,
                amount_cents=amount_cents,
                currency="usd",
                status="creating_checkout",
            )
            db.add(purchase)
            db.flush()
            invoice_id = purchase.id
        with _lock:
            invoice: JsonObject = {
                "id": invoice_id,
                "tenant_id": auth.tenant_id,
                "subscription_id": None,
                "amount": amount_cents / 100,
                "amount_cents": amount_cents,
                "currency": "USD",
                "status": "creating_checkout",
                "created_at": now,
                "invoice_type": "credit_topup",
                "credits_requested": payload.credits,
                "payment_provider": "stripe",
                "credits_applied": False,
            }
            invoices_memory.append(invoice)
        try:
            session = client.v1.checkout.sessions.create(
                {
                    "mode": "payment",
                    "line_items": [
                        {
                            "quantity": 1,
                            "price_data": {
                                "currency": "usd",
                                "unit_amount": amount_cents,
                                "product_data": {"name": f"{payload.credits:,} Nuxtron AI credits"},
                            },
                        }
                    ],
                    "success_url": f"{site_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                    "cancel_url": f"{site_url}/billing",
                    "client_reference_id": auth.tenant_id,
                    "metadata": {
                        "kind": "nuxtron_credit_topup",
                        "tenant_id": auth.tenant_id,
                        "invoice_id": str(invoice_id),
                        "credits": str(payload.credits),
                    },
                    "integration_identifier": _integration_identifier(),
                },
                options={
                    "idempotency_key": durable_request_id
                },
            )
        except stripe.StripeError as exc:
            with get_db_session() as db:
                failed = db.get(BillingCreditPurchase, invoice_id)
                if failed is not None:
                    failed.status = "checkout_failed"
            with _lock:
                invoice["status"] = "checkout_failed"
            logger.exception("Stripe credit Checkout creation failed")
            raise HTTPException(status_code=502, detail="Stripe could not create Checkout.") from exc
        with _lock:
            invoice["status"] = "pending_payment"
            invoice["stripe_checkout_session_id"] = session.id
        with get_db_session() as db:
            persisted = db.get(BillingCreditPurchase, invoice_id)
            if persisted is not None:
                persisted.status = "pending_payment"
                persisted.stripe_checkout_session_id = session.id
        return {
            "status": "ok",
            "checkout_url": session.url,
            "session_id": session.id,
            "invoice_id": invoice_id,
        }

    @router.post("/portal-session")
    def create_portal_session(auth: AuthDep) -> JsonObject:
        with get_db_session() as db:
            persisted = (
                db.query(BillingSubscription)
                .filter(BillingSubscription.tenant_id == auth.tenant_id)
                .order_by(BillingSubscription.created_at.desc())
                .first()
            )
            customer_id = persisted.stripe_customer_id if persisted is not None else ""
        if not customer_id:
            with _lock:
                subscription = _find_subscription(
                    subscriptions_memory, tenant_id=auth.tenant_id
                )
                customer_id = str((subscription or {}).get("stripe_customer_id") or "")
        if not customer_id.startswith("cus_"):
            raise HTTPException(status_code=404, detail="No Stripe customer exists for this account.")
        try:
            session = _stripe_client().v1.billing_portal.sessions.create(
                {"customer": customer_id, "return_url": f"{_site_url()}/billing"}
            )
        except stripe.StripeError as exc:
            logger.exception("Stripe customer portal creation failed")
            raise HTTPException(status_code=502, detail="Stripe could not open the billing portal.") from exc
        return {"status": "ok", "portal_url": session.url}

    @router.post("/session-status")
    def checkout_session_status(payload: SessionStatusRequest, auth: AuthDep) -> JsonObject:
        try:
            session = _stripe_client().v1.checkout.sessions.retrieve(payload.session_id)
        except stripe.StripeError as exc:
            raise HTTPException(status_code=502, detail="Stripe could not retrieve Checkout.") from exc
        metadata = _metadata(session.metadata)
        if (
            str(session.client_reference_id or "") != auth.tenant_id
            or metadata.get("tenant_id") != auth.tenant_id
        ):
            raise HTTPException(status_code=404, detail="Checkout Session not found.")
        return {
            "status": "ok",
            "session_status": session.status,
            "payment_status": session.payment_status,
            "kind": metadata.get("kind", ""),
        }

    @router.post("/activate", deprecated=True)
    def activate_after_checkout(payload: SessionStatusRequest, auth: AuthDep) -> JsonObject:
        """Compatibility alias. It verifies status but never grants entitlements."""
        return checkout_session_status(payload, auth)

    @router.post("/webhook", include_in_schema=False)
    async def stripe_webhook(
        request: Request,
        stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
    ) -> JsonObject:
        webhook_secret = _env("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret or webhook_secret.startswith("whsec_local"):
            raise HTTPException(status_code=503, detail="Stripe webhook verification is not configured.")
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")
        raw_body = await request.body()
        try:
            event = _stripe_client().construct_event(
                raw_body, stripe_signature, webhook_secret
            )
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.") from exc

        event_id = str(event.id)
        event_type = str(event.type)
        obj = _as_dict(event.data.object)
        with _lock:
            if event_processed(event_id):
                return {"received": True, "duplicate": True}
            try:
                tenant_id = ""
                if event_type == "checkout.session.completed":
                    metadata = _metadata(obj.get("metadata"))
                    if metadata.get("kind") == "nuxtron_subscription":
                        tenant_id = activate_subscription(obj)
                    elif metadata.get("kind") == "nuxtron_credit_topup":
                        tenant_id = apply_credit_purchase(obj)
                elif event_type == "customer.subscription.deleted":
                    tenant_id = update_subscription_status(obj, "cancelled")
                elif event_type in {"customer.subscription.paused", "invoice.payment_failed"}:
                    tenant_id = update_subscription_status(obj, "past_due")
                elif event_type == "invoice.paid":
                    tenant_id = update_subscription_status(obj, "active")
                    credited_tenant = apply_subscription_credits(obj)
                    tenant_id = credited_tenant or tenant_id
                elif event_type in {
                    "customer.subscription.resumed",
                    "customer.subscription.updated",
                }:
                    status = str(obj.get("status") or "active")
                    tenant_id = update_subscription_status(obj, status)
                mark_event(event_id, event_type, tenant_id)
            except ValueError as exc:
                logger.warning("Rejected Stripe event %s: %s", event_id, exc)
                raise HTTPException(status_code=422, detail="Stripe event data is invalid.") from exc
        return {"received": True, "duplicate": False}

    return router
