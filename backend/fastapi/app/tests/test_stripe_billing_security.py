from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from backend.fastapi.app.deps import AuthContext, require_auth
from backend.fastapi.app.routers import stripe_billing
from backend.fastapi.app.routers.billing import create_billing_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeStripeClient:
    session_sequence = 0

    def __init__(self) -> None:
        self.created: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
        self.portal_created: list[dict[str, Any]] = []
        self.event: Any = None
        self.retrieved: Any = None
        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(
                sessions=SimpleNamespace(create=self.create_session, retrieve=self.retrieve_session)
            ),
            billing_portal=SimpleNamespace(
                sessions=SimpleNamespace(create=self.create_portal)
            ),
        )

    def create_session(
        self, params: dict[str, Any], options: dict[str, Any] | None = None
    ) -> Any:
        self.created.append((params, options))
        type(self).session_sequence += 1
        return SimpleNamespace(
            id=f"cs_test_{type(self).session_sequence}",
            url="https://checkout.stripe.test/session",
        )

    def retrieve_session(self, _session_id: str) -> Any:
        return self.retrieved

    def create_portal(self, params: dict[str, Any]) -> Any:
        self.portal_created.append(params)
        return SimpleNamespace(url="https://billing.stripe.test/portal")

    def construct_event(
        self, _payload: bytes, _signature: str, _secret: str
    ) -> Any:
        return self.event


@pytest.fixture()
def stores() -> dict[str, list[dict[str, Any]]]:
    return {
        "subscriptions": [],
        "invoices": [],
        "credits": [],
        "audit": [],
    }


@pytest.fixture()
def fake_stripe(monkeypatch: pytest.MonkeyPatch) -> FakeStripeClient:
    fake = FakeStripeClient()
    monkeypatch.setattr(stripe_billing, "_stripe_client", lambda: fake)
    monkeypatch.setenv("SITE_URL", "https://app.example.test")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_real_test")
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly")
    return fake


@pytest.fixture()
def client(
    stores: dict[str, list[dict[str, Any]]],
) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[require_auth] = lambda: AuthContext(
        tenant_id="tenant-real",
        auth_mode="bearer_jwt",
        subject="buyer@example.test",
        roles=["owner"],
    )
    app.include_router(
        create_billing_router(
            enforce_rate_limit=lambda *_args, **_kwargs: None,
            subscriptions_memory=stores["subscriptions"],
            invoices_memory=stores["invoices"],
            credit_ledger_memory=stores["credits"],
            audit_log_memory=stores["audit"],
        )
    )
    app.include_router(
        stripe_billing.create_stripe_billing_router(
            subscriptions_memory=stores["subscriptions"],
            invoices_memory=stores["invoices"],
            credit_ledger_memory=stores["credits"],
            audit_log_memory=stores["audit"],
        )
    )
    return TestClient(app, raise_server_exceptions=False)


def test_manual_paid_subscription_activation_is_disabled(client: TestClient) -> None:
    response = client.post(
        "/billing/subscribe",
        json={"plan_id": "pro", "billing_cycle": "monthly"},
    )
    assert response.status_code == 409


def test_client_side_credit_confirmation_is_disabled(client: TestClient) -> None:
    response = client.post(
        "/billing/credits/confirm",
        json={
            "invoice_id": 1,
            "payment_reference": "attacker",
            "provider_transaction_id": "attacker",
            "amount_usd": 0.01,
        },
    )
    assert response.status_code == 409


def test_subscription_checkout_uses_server_price_and_tenant(
    client: TestClient,
    fake_stripe: FakeStripeClient,
) -> None:
    response = client.post(
        "/billing/stripe/checkout-session",
        json={
            "plan_id": "pro",
            "billing_cycle": "monthly",
            "request_id": "request_1234567890",
            "amount_usd": 0.01,
            "customer": "cus_victim",
        },
    )
    assert response.status_code == 200
    params, options = fake_stripe.created[0]
    assert params["line_items"] == [{"price": "price_pro_monthly", "quantity": 1}]
    assert "price_data" not in params["line_items"][0]
    assert "payment_method_types" not in params
    assert params["client_reference_id"] == "tenant-real"
    assert params["metadata"]["tenant_id"] == "tenant-real"
    assert params["customer_email"] == "buyer@example.test"
    assert "customer" not in params
    assert options and str(options["idempotency_key"]).startswith("nuxtron_subscription_")


def test_portal_customer_is_derived_from_server_subscription(
    client: TestClient,
    stores: dict[str, list[dict[str, Any]]],
    fake_stripe: FakeStripeClient,
) -> None:
    stores["subscriptions"].append(
        {
            "tenant_id": "tenant-real",
            "status": "active",
            "stripe_customer_id": "cus_real",
        }
    )
    response = client.post(
        "/billing/stripe/portal-session",
        json={"customer_id": "cus_victim"},
    )
    assert response.status_code == 200
    assert fake_stripe.portal_created[0]["customer"] == "cus_real"


def test_webhook_fails_closed_without_signing_secret(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    response = client.post(
        "/billing/stripe/webhook",
        headers={"Stripe-Signature": "t=1,v1=bad"},
        content=b"{}",
    )
    assert response.status_code == 503


def test_credit_webhook_uses_server_amount_and_is_idempotent(
    client: TestClient,
    stores: dict[str, list[dict[str, Any]]],
    fake_stripe: FakeStripeClient,
) -> None:
    checkout = client.post(
        "/billing/stripe/credit-checkout-session",
        json={"credits": 1000, "request_id": "credit_request_1234"},
    )
    assert checkout.status_code == 200
    session_id = checkout.json()["session_id"]
    assert fake_stripe.created[0][0]["line_items"][0]["price_data"]["unit_amount"] == 2000

    session = {
        "id": session_id,
        "payment_status": "paid",
        "amount_total": 2000,
        "currency": "usd",
        "payment_intent": "pi_test",
        "metadata": {
            "kind": "nuxtron_credit_topup",
            "tenant_id": "tenant-real",
            "invoice_id": str(checkout.json()["invoice_id"]),
            "credits": "1000",
        },
    }
    fake_stripe.event = SimpleNamespace(
        id="evt_credit_paid",
        type="checkout.session.completed",
        data=SimpleNamespace(object=session),
    )
    first = client.post(
        "/billing/stripe/webhook",
        headers={"Stripe-Signature": "t=1,v1=test"},
        content=b"{}",
    )
    second = client.post(
        "/billing/stripe/webhook",
        headers={"Stripe-Signature": "t=1,v1=test"},
        content=b"{}",
    )
    assert first.status_code == 200
    assert second.json()["duplicate"] is True
    assert len(stores["credits"]) == 1
    assert stores["credits"][0]["amount"] == 1000


def test_webhook_rejects_amount_mismatch_without_granting_credits(
    client: TestClient,
    stores: dict[str, list[dict[str, Any]]],
    fake_stripe: FakeStripeClient,
) -> None:
    checkout = client.post(
        "/billing/stripe/credit-checkout-session",
        json={"credits": 1000, "request_id": "credit_request_5678"},
    )
    fake_stripe.event = SimpleNamespace(
        id="evt_wrong_amount",
        type="checkout.session.completed",
        data=SimpleNamespace(
            object={
                "id": checkout.json()["session_id"],
                "payment_status": "paid",
                "amount_total": 1,
                "currency": "usd",
                "metadata": {
                    "kind": "nuxtron_credit_topup",
                    "tenant_id": "tenant-real",
                    "invoice_id": str(checkout.json()["invoice_id"]),
                    "credits": "1000",
                },
            }
        ),
    )
    response = client.post(
        "/billing/stripe/webhook",
        headers={"Stripe-Signature": "t=1,v1=test"},
        content=b"{}",
    )
    assert response.status_code == 422
    assert stores["credits"] == []


def test_signed_subscription_events_activate_plan_and_grant_invoice_credits(
    client: TestClient,
    fake_stripe: FakeStripeClient,
) -> None:
    fake_stripe.event = SimpleNamespace(
        id="evt_subscription_checkout",
        type="checkout.session.completed",
        data=SimpleNamespace(
            object={
                "id": "cs_subscription_test",
                "subscription": "sub_subscription_test",
                "customer": "cus_subscription_test",
                "payment_status": "paid",
                "metadata": {
                    "kind": "nuxtron_subscription",
                    "tenant_id": "tenant-real",
                    "plan_id": "pro",
                    "billing_cycle": "monthly",
                },
            }
        ),
    )
    activated = client.post(
        "/billing/stripe/webhook",
        headers={"Stripe-Signature": "t=1,v1=test"},
        content=b"{}",
    )
    assert activated.status_code == 200

    fake_stripe.event = SimpleNamespace(
        id="evt_subscription_invoice",
        type="invoice.paid",
        data=SimpleNamespace(
            object={
                "id": "in_subscription_test",
                "subscription": "sub_subscription_test",
                "status": "paid",
            }
        ),
    )
    invoiced = client.post(
        "/billing/stripe/webhook",
        headers={"Stripe-Signature": "t=1,v1=test"},
        content=b"{}",
    )
    assert invoiced.status_code == 200

    usage = client.get("/billing/usage")
    assert usage.status_code == 200
    assert usage.json()["current_plan"] == "pro"
    assert usage.json()["credit_balance"] >= 5000
