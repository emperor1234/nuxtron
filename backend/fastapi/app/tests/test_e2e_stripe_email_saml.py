"""E2E tests for Stripe billing router, email provider router, and SAML auth router.

These tests run against the live FastAPI app (TestClient) with mock env vars.
No real Stripe / email calls are made — the endpoints return 503 when keys are
placeholder values, or follow the free-plan path without Stripe.
"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_local_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_local_placeholder")
os.environ.setdefault("EMAIL_PROVIDER", "resend")
os.environ.setdefault("RESEND_API_KEY", "local-mock-resend-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant-e2e"}


def _bearer_header(subject: str) -> dict[str, str]:
    """Build a bearer-auth header for a self-issued JWT test subject.

    /auth/jwt/issue now requires bearer auth (not a shared API key) to mint a
    token, and only for the caller's own subject — see routers/auth.py. This
    mints the FIRST token directly (bypassing the endpoint, as a test fixture
    would) so tests can then exercise /auth/jwt/issue as a real bearer-authed
    caller, matching how a client would actually use this API.
    """
    import base64
    import hashlib
    import hmac
    import json
    import time

    def b64url(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "tenant_id": "test-tenant-e2e",
        "roles": ["user"],
        "iat": now,
        "exp": now + 3600,
        "iss": "test-harness",
        "jti": hashlib.sha256(f"{subject}:{now}".encode()).hexdigest()[:24],
    }
    head = b64url(json.dumps(header, separators=(",", ":")).encode())
    body = b64url(json.dumps(payload, separators=(",", ":")).encode())
    # Resolve the same way deps._resolve_jwt_secret does at verify time,
    # rather than hardcoding "test-api-key" — stays correct even if an
    # earlier test in the same process changed JWT_SIGNING_KEY/FASTAPI_API_KEY.
    secret = os.environ.get("JWT_SIGNING_KEY") or os.environ.get("FASTAPI_API_KEY", "test-api-key")
    sig = hmac.new(secret.encode("utf-8"), f"{head}.{body}".encode("ascii"), hashlib.sha256).digest()
    token = f"{head}.{body}.{b64url(sig)}"
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app  # type: ignore[import-untyped]

    # Ensure DB tables exist for CRM routes (creates SQLite test DB)
    try:
        from backend.fastapi.app.database import init_db  # type: ignore[import-untyped]
        init_db()
    except Exception:
        pass  # Non-fatal — CRM smoke tests may return 500 if tables absent

    return TestClient(app, raise_server_exceptions=False)


# ── Billing plans (existing endpoint) ────────────────────────────────────────

class TestBillingPlans:
    def test_list_plans_ok(self, client: TestClient) -> None:
        r = client.get("/billing/plans", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert len(data["plans"]) >= 4

    def test_plan_has_required_fields(self, client: TestClient) -> None:
        r = client.get("/billing/plans", headers=H)
        plan = r.json()["plans"][0]
        assert "id" in plan
        assert "price_monthly" in plan
        assert "ai_credits" in plan

    def test_subscribe_starter(self, client: TestClient) -> None:
        r = client.post("/billing/subscribe", headers=H, json={"plan_id": "starter", "billing_cycle": "monthly"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["subscription"]["plan_id"] == "starter"

    def test_subscribe_pro(self, client: TestClient) -> None:
        r = client.post("/billing/subscribe", headers=H, json={"plan_id": "pro", "billing_cycle": "monthly"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    def test_subscribe_invalid_plan(self, client: TestClient) -> None:
        r = client.post("/billing/subscribe", headers=H, json={"plan_id": "nonexistent", "billing_cycle": "monthly"})
        assert r.status_code == 422

    def test_billing_usage(self, client: TestClient) -> None:
        r = client.get("/billing/usage", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "credit_balance" in data
        assert "current_plan" in data

    def test_billing_invoices(self, client: TestClient) -> None:
        r = client.get("/billing/invoices", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "invoices" in data

    def test_credits_quote(self, client: TestClient) -> None:
        r = client.post("/billing/credits/quote", headers=H, json={"amount": 1000})
        assert r.status_code == 200
        data = r.json()
        assert data["quote"]["credits"] == 1000
        assert data["quote"]["total_usd"] > 0

    def test_cancel_subscription(self, client: TestClient) -> None:
        # Subscribe first to ensure there is an active subscription
        client.post("/billing/subscribe", headers=H, json={"plan_id": "pro", "billing_cycle": "monthly"})
        r = client.post("/billing/cancel", headers=H)
        assert r.status_code == 200


# ── Stripe billing router ─────────────────────────────────────────────────────

class TestStripeBilling:
    def test_checkout_session_free_plan(self, client: TestClient) -> None:
        """Starter plan should return free_plan=True without calling Stripe."""
        r = client.post("/billing/stripe/checkout-session", headers=H, json={
            "plan_id": "starter",
            "billing_cycle": "monthly",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["free_plan"] is True
        assert data["checkout_url"] is None

    def test_checkout_session_paid_plan_no_stripe_key(self, client: TestClient) -> None:
        """When STRIPE_SECRET_KEY is a local placeholder, should return 503."""
        r = client.post("/billing/stripe/checkout-session", headers=H, json={
            "plan_id": "pro",
            "billing_cycle": "monthly",
        })
        assert r.status_code == 503

    def test_checkout_session_invalid_plan(self, client: TestClient) -> None:
        r = client.post("/billing/stripe/checkout-session", headers=H, json={
            "plan_id": "bogus_plan",
            "billing_cycle": "monthly",
        })
        assert r.status_code == 422

    def test_checkout_session_annual_billing(self, client: TestClient) -> None:
        """Annual billing for starter should still return free_plan."""
        r = client.post("/billing/stripe/checkout-session", headers=H, json={
            "plan_id": "starter",
            "billing_cycle": "annual",
        })
        assert r.status_code == 200
        assert r.json()["free_plan"] is True

    def test_webhook_no_signature_with_local_secret(self, client: TestClient) -> None:
        """Webhook with whsec_local_placeholder should skip verification and return 200."""
        r = client.post(
            "/billing/stripe/webhook",
            json={"type": "checkout.session.completed", "data": {"object": {"metadata": {}, "id": "cs_test"}}},
        )
        assert r.status_code == 200
        assert r.json()["received"] is True

    def test_portal_session_no_stripe_key(self, client: TestClient) -> None:
        r = client.post("/billing/stripe/portal-session", headers=H, json={"customer_id": "cus_test123"})
        assert r.status_code == 503


# ── Email provider router ─────────────────────────────────────────────────────

class TestEmailProvider:
    def test_config_status(self, client: TestClient) -> None:
        r = client.get("/email/config/status", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "providers" in data
        assert "active_provider" in data

    def test_send_transactional_provider_not_configured(self, client: TestClient) -> None:
        """With local mock key, Resend returns not-configured → queued gracefully."""
        r = client.post("/email/transactional/send", headers=H, json={
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "Hello from E2E test",
        })
        # 200 (queued) or 502 (provider error); 503 not expected here
        assert r.status_code in {200, 502}
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "ok"
            assert data["delivery_status"] in {"sent", "queued"}

    def test_send_transactional_missing_required_fields(self, client: TestClient) -> None:
        r = client.post("/email/transactional/send", headers=H, json={"to": "test@example.com"})
        assert r.status_code == 422

    def test_send_transactional_with_html(self, client: TestClient) -> None:
        r = client.post("/email/transactional/send", headers=H, json={
            "to": "test@example.com",
            "subject": "HTML Test",
            "body": "Plain text fallback",
            "html": "<h1>Hello HTML</h1>",
        })
        assert r.status_code in {200, 502}

    def test_send_transactional_explicit_provider(self, client: TestClient) -> None:
        r = client.post("/email/transactional/send", headers=H, json={
            "to": "test@example.com",
            "subject": "Provider Test",
            "body": "Testing SMTP provider",
            "provider": "smtp",
        })
        # SMTP not configured in test env → queued gracefully
        assert r.status_code in {200, 502}

    def test_send_transactional_invalid_provider(self, client: TestClient) -> None:
        """Invalid provider string: still attempts (falls through); doesn't crash."""
        r = client.post("/email/transactional/send", headers=H, json={
            "to": "test@example.com",
            "subject": "Bad Provider",
            "body": "test",
            "provider": "nonexistent_provider",
        })
        assert r.status_code in {200, 502}


# ── SAML/SSO auth endpoints ───────────────────────────────────────────────────

class TestSamlAuth:
    def test_metadata_saml_disabled(self, client: TestClient) -> None:
        """With SAML_ENABLED=false (default), metadata endpoint returns 503."""
        r = client.get("/auth/saml/metadata")
        assert r.status_code == 503

    def test_login_saml_disabled(self, client: TestClient) -> None:
        r = client.get("/auth/saml/login", headers=H)
        assert r.status_code == 503

    def test_acs_saml_disabled(self, client: TestClient) -> None:
        r = client.post("/auth/saml/acs", headers=H, json={
            "saml_response": "dGVzdC1zYW1sLXJlc3BvbnNlLWJhc2U2NC1wbGFjZWhvbGRlcg=="
        })
        assert r.status_code == 503


# ── JWT Auth (should always work) ────────────────────────────────────────────

class TestJwtAuth:
    def test_issue_jwt(self, client: TestClient) -> None:
        # /auth/jwt/issue requires an authenticated bearer session (not a
        # shared API key) and can only self-issue for the caller's own
        # subject unless the caller holds an elevated role — see
        # routers/auth.py's impersonation-closing fix.
        r = client.post("/auth/jwt/issue", headers=_bearer_header("test-user@example.com"), json={
            "subject": "test-user@example.com",
            "expires_in_seconds": 3600,
            "roles": ["user"],
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data["result"]

    def test_verify_jwt_roundtrip(self, client: TestClient) -> None:
        # Issue
        r = client.post("/auth/jwt/issue", headers=_bearer_header("e2e@test.com"), json={"subject": "e2e@test.com", "expires_in_seconds": 3600, "roles": ["user"]})
        token = r.json()["result"]["token"]
        # Verify
        r2 = client.post("/auth/jwt/verify", headers=H, json={"token": token})
        assert r2.status_code == 200
        data = r2.json()
        assert data["valid"] is True
        assert data["claims"]["sub"] == "e2e@test.com"

    def test_verify_invalid_jwt(self, client: TestClient) -> None:
        r = client.post("/auth/jwt/verify", headers=H, json={"token": "invalid.jwt.token.that.is.long.enough.to.pass.validation"})
        assert r.status_code == 200
        assert r.json()["valid"] is False


# ── Smoke test — key routes all return non-500 ────────────────────────────────

class TestSmokeRoutes:
    ROUTES = [
        ("GET", "/billing/plans"),
        ("GET", "/billing/usage"),
        ("GET", "/billing/invoices"),
        ("GET", "/email/config/status"),
        ("GET", "/crm/contacts"),
        ("GET", "/crm/deals"),
        ("GET", "/social/accounts"),
        ("GET", "/analytics/dashboard"),
    ]

    @pytest.mark.parametrize("method,path", ROUTES)
    def test_route_responds(self, client: TestClient, method: str, path: str) -> None:
        if method == "GET":
            r = client.get(path, headers=H)
        else:
            r = client.post(path, headers=H)
        assert r.status_code < 500, f"{method} {path} returned {r.status_code}: {r.text[:200]}"
