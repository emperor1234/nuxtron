"""
Integration tests for the API Governance router.

These tests build an in-process FastAPI TestClient with a lightweight
ApiGovernanceContext (no DB, no vault) and exercise every endpoint end-to-end,
verifying request/response contracts, persistence calls, and security enforcement.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections.abc import Generator
from unittest.mock import patch

import pytest

# Prevent legacy_main DB init from running during import
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("JWT_SIGNING_KEY", "integration-test-secret")
os.environ.setdefault("APP_ENC_KEY", "A" * 44)  # 32 bytes base64-encoded placeholder

# ── Helpers ───────────────────────────────────────────────────────────────── #

_JWT_SECRET = "integration-test-secret"
_TENANT = "tenant-integration"


def _make_jwt(claims: dict, secret: str = _JWT_SECRET, expired: bool = False) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    if expired:
        claims = {**claims, "exp": int(time.time()) - 3600}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


def _bearer(token: str, tenant_id: str = _TENANT) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id}


# ── Fixtures ──────────────────────────────────────────────────────────────── #

@pytest.fixture()
def client() -> Generator:
    """Minimal FastAPI app wired with the governance router."""
    from backend.fastapi.app.routers.api_governance import (
        ApiGovernanceContext,
        create_api_governance_router,
    )
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    persist_calls: list[int] = []

    def _noop_rate_limit(key: str, limit: int, window: int) -> None:
        pass

    def _noop_persist() -> None:
        persist_calls.append(1)

    ctx = ApiGovernanceContext(
        enforce_rate_limit=_noop_rate_limit,
        te_encrypt=lambda s: f"enc:{s}",
        provider_store=[],
        usage_store=[],
        incident_store=[],
        notification_store=[],
        ira_events_store=[],
        siem_cases_store=[],
        vault_hashicorp_health=lambda: {"enabled": False},
        vault_supabase_health=lambda: {"enabled": False},
        persist=_noop_persist,
    )

    app = FastAPI()
    app.include_router(create_api_governance_router(ctx))
    # Expose persist_calls for inspection
    app.state.persist_calls = persist_calls

    with (
        patch.dict(os.environ, {"JWT_SIGNING_KEY": _JWT_SECRET}),
        TestClient(app, raise_server_exceptions=True) as c,
    ):
        c.app_persist_calls = persist_calls  # type: ignore[attr-defined]
        yield c


@pytest.fixture()
def token() -> str:
    return _make_jwt({"tenant_id": _TENANT})


@pytest.fixture()
def expired_token() -> str:
    return _make_jwt({"tenant_id": _TENANT}, expired=True)


# ── Security: token-only policy ───────────────────────────────────────────── #

class TestTokenOnlyPolicy:
    def test_kpi_rejects_api_key_auth(self, client) -> None:
        """API key auth must be rejected with 403 on governance endpoints."""
        with patch.dict(os.environ, {"ALLOW_HEADER_API_KEYS": "true", "JWT_SIGNING_KEY": _JWT_SECRET}):
            resp = client.get(
                "/api-governance/kpi",
                headers={"X-API-Key": "test-api-key", "X-Tenant-Id": _TENANT},
            )
        assert resp.status_code == 403

    def test_kpi_requires_bearer(self, client, token) -> None:
        resp = client.get("/api-governance/kpi", headers=_bearer(token))
        assert resp.status_code == 200

    def test_expired_token_rejected(self, client, expired_token) -> None:
        resp = client.get("/api-governance/kpi", headers=_bearer(expired_token))
        assert resp.status_code == 401


# ── Provider CRUD ─────────────────────────────────────────────────────────── #

class TestProviderUpsert:
    def _provider_payload(self, name: str = "OpenAI-GPT4") -> dict:
        return {
            "name": name,
            "vendor": "OpenAI",
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4-turbo",
            "billing_unit": "token",
            "token": "sk-test-secret-key-1234567890",
            "cost_per_token_usd": 0.00003,
            "cost_per_credit_usd": 0.0,
            "credits_purchased": 0.0,
            "tokens_purchased": 1000000,
            "target_margin": 0.67,
        }

    def test_upsert_creates_provider(self, client, token) -> None:
        resp = client.post(
            "/api-governance/providers",
            json=self._provider_payload(),
            headers=_bearer(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["provider"]["name"] == "OpenAI-GPT4"
        # Token must NEVER be returned in plaintext
        tok = data["provider"].get("token_encrypted", "")
        assert "sk-test" not in tok, "Plaintext token leaked in response"
        assert "enc:" not in tok or "..." in tok or tok.startswith("enc:") and len(tok) <= 20

    def test_upsert_calls_persist(self, client, token) -> None:
        client.post(
            "/api-governance/providers",
            json=self._provider_payload("Persist-Test"),
            headers=_bearer(token),
        )
        assert len(client.app_persist_calls) >= 1

    def test_upsert_idempotent(self, client, token) -> None:
        payload = self._provider_payload("Idempotent-Provider")
        client.post("/api-governance/providers", json=payload, headers=_bearer(token))
        client.post("/api-governance/providers", json=payload, headers=_bearer(token))
        resp = client.get("/api-governance/providers", headers=_bearer(token))
        providers = resp.json()["providers"]
        names = [p["name"] for p in providers]
        assert names.count("Idempotent-Provider") == 1, "Upsert should not create duplicates"

    def test_token_too_short_rejected(self, client, token) -> None:
        payload = {**self._provider_payload(), "token": "short"}
        resp = client.post("/api-governance/providers", json=payload, headers=_bearer(token))
        assert resp.status_code == 422


# ── Provider list ─────────────────────────────────────────────────────────── #

class TestProviderList:
    def test_list_empty_initially(self, client, token) -> None:
        resp = client.get("/api-governance/providers", headers=_bearer(token))
        assert resp.status_code == 200
        assert resp.json()["providers"] == []

    def test_list_scoped_to_tenant(self, client, token) -> None:
        # Add a provider for a different tenant — should not appear in list
        other_token = _make_jwt({"tenant_id": "other-tenant"})
        client.post(
            "/api-governance/providers",
            json={
                "name": "Other-Tenant-Provider",
                "vendor": "AWS",
                "endpoint": "https://bedrock.us-east-1.amazonaws.com/model/invoke",
                "token": "AKIAIOSFODNN7EXAMPLE",
                "billing_unit": "token",
                "tokens_purchased": 500000,
                "target_margin": 0.65,
            },
            headers=_bearer(other_token),
        )
        resp = client.get("/api-governance/providers", headers=_bearer(token))
        providers = resp.json()["providers"]
        assert all(p["tenant_id"] == _TENANT for p in providers)


# ── Usage recording ───────────────────────────────────────────────────────── #

class TestUsageRecording:
    def _create_provider(self, client, token, name: str = "Usage-Test-Provider") -> int:
        resp = client.post(
            "/api-governance/providers",
            json={
                "name": name,
                "vendor": "Anthropic",
                "endpoint": "https://api.anthropic.com/v1/messages",
                "token": "sk-ant-test-key-abcdef123456",
                "billing_unit": "token",
                "tokens_purchased": 1000000,
                "cost_per_token_usd": 0.000015,
                "target_margin": 0.67,
            },
            headers=_bearer(token),
        )
        return int(resp.json()["provider"]["id"])

    def test_record_usage_updates_provider_stats(self, client, token) -> None:
        pid = self._create_provider(client, token)
        resp = client.post(
            f"/api-governance/providers/{pid}/usage",
            json={
                "user_id": "user-001",
                "request_path": "/api/chat",
                "tokens_used": 10000,
                "credits_used": 0.0,
                "revenue_generated_usd": 1.0,
                "status_code": 200,
            },
            headers=_bearer(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["usage"]["tokens_used"] == 10000
        assert data["usage"]["cost_usd"] == pytest.approx(0.15, abs=0.01)
        assert data["usage"]["profit_usd"] == pytest.approx(0.85, abs=0.01)

    def test_disabled_provider_cannot_record_usage(self, client, token) -> None:
        pid = self._create_provider(client, token, "Disabled-Provider")
        client.post(
            f"/api-governance/providers/{pid}/disable",
            json={"reason": "test disable"},
            headers=_bearer(token),
        )
        resp = client.post(
            f"/api-governance/providers/{pid}/usage",
            json={
                "user_id": "user-002",
                "request_path": "/api/chat",
                "tokens_used": 100,
                "credits_used": 0.0,
                "revenue_generated_usd": 0.01,
                "status_code": 200,
            },
            headers=_bearer(token),
        )
        assert resp.status_code == 423

    def test_provider_auto_disabled_when_tokens_exhausted(self, client, token) -> None:
        resp = client.post(
            "/api-governance/providers",
            json={
                "name": "Low-Budget-Provider",
                "vendor": "Cohere",
                "endpoint": "https://api.cohere.ai/v1/generate",
                "token": "cohere-test-key-abcdef1234567",
                "billing_unit": "token",
                "tokens_purchased": 100,  # very few tokens
                "cost_per_token_usd": 0.00001,
                "target_margin": 0.67,
            },
            headers=_bearer(token),
        )
        pid = int(resp.json()["provider"]["id"])
        # Consume all tokens
        usage_resp = client.post(
            f"/api-governance/providers/{pid}/usage",
            json={
                "user_id": "user-001",
                "request_path": "/api/chat",
                "tokens_used": 100,
                "credits_used": 0.0,
                "revenue_generated_usd": 0.005,
                "status_code": 200,
            },
            headers=_bearer(token),
        )
        assert usage_resp.json()["provider_status"] == "disabled"


# ── KPI endpoint ──────────────────────────────────────────────────────────── #

class TestKPI:
    def test_kpi_returns_expected_shape(self, client, token) -> None:
        resp = client.get("/api-governance/kpi", headers=_bearer(token))
        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        for field in (
            "providers_total", "providers_active", "providers_disabled",
            "usage_events", "revenue_total_usd", "cost_total_usd",
            "profit_total_usd", "profit_margin_pct", "critical_incidents",
        ):
            assert field in kpis, f"Missing KPI field: {field}"

    def test_kpi_reflects_usage(self, client, token) -> None:
        # Create provider + usage, then check KPI sums
        client.post(
            "/api-governance/providers",
            json={
                "name": "KPI-Test-Provider",
                "vendor": "Mistral",
                "endpoint": "https://api.mistral.ai/v1/chat/completions",
                "token": "mistral-test-key-12345678abcd",
                "billing_unit": "token",
                "tokens_purchased": 2000000,
                "cost_per_token_usd": 0.000007,
                "target_margin": 0.67,
            },
            headers=_bearer(token),
        )
        providers = client.get("/api-governance/providers", headers=_bearer(token)).json()["providers"]
        pid = providers[-1]["id"]
        client.post(
            f"/api-governance/providers/{pid}/usage",
            json={
                "user_id": "kpi-user",
                "request_path": "/api/chat",
                "tokens_used": 50000,
                "credits_used": 0.0,
                "revenue_generated_usd": 2.0,
                "status_code": 200,
            },
            headers=_bearer(token),
        )
        kpis = client.get("/api-governance/kpi", headers=_bearer(token)).json()["kpis"]
        assert kpis["usage_events"] >= 1
        assert kpis["revenue_total_usd"] >= 2.0


# ── Encryption posture ────────────────────────────────────────────────────── #

class TestEncryptionPosture:
    def test_all_four_vectors_present(self, client, token) -> None:
        resp = client.get("/api-governance/security/encryption-posture", headers=_bearer(token))
        assert resp.status_code == 200
        enc = resp.json()["encryption"]
        for vector in ("at_rest", "in_transit", "in_use", "in_memory"):
            assert vector in enc, f"Missing encryption vector: {vector}"
            assert enc[vector]["enabled"] is True

    def test_quantum_nist_field_present(self, client, token) -> None:
        resp = client.get("/api-governance/security/encryption-posture", headers=_bearer(token))
        enc = resp.json()["encryption"]
        assert "quantum_nist" in enc
        assert "enabled" in enc["quantum_nist"]


# ── Incidents ─────────────────────────────────────────────────────────────── #

class TestIncidents:
    def test_incidents_list_empty_initially(self, client, token) -> None:
        resp = client.get("/api-governance/incidents", headers=_bearer(token))
        assert resp.status_code == 200
        assert resp.json()["incidents"] == []

    def test_disable_generates_incident(self, client, token) -> None:
        client.post(
            "/api-governance/providers",
            json={
                "name": "Incident-Provider",
                "vendor": "Google",
                "endpoint": "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent",
                "token": "google-ai-key-test-abcdefgh1234",
                "billing_unit": "token",
                "tokens_purchased": 500000,
                "target_margin": 0.67,
            },
            headers=_bearer(token),
        )
        providers = client.get("/api-governance/providers", headers=_bearer(token)).json()["providers"]
        pid = providers[-1]["id"]

        client.post(
            f"/api-governance/providers/{pid}/disable",
            json={"reason": "Emergency: suspected compromise"},
            headers=_bearer(token),
        )

        incidents = client.get("/api-governance/incidents", headers=_bearer(token)).json()["incidents"]
        assert len(incidents) >= 1
        assert any("disabled" in i["title"].lower() for i in incidents)


# ── Provider disable ──────────────────────────────────────────────────────── #

class TestProviderDisable:
    def test_disable_unknown_provider_returns_404(self, client, token) -> None:
        resp = client.post(
            "/api-governance/providers/99999/disable",
            json={"reason": "test"},
            headers=_bearer(token),
        )
        assert resp.status_code == 404

    def test_disable_other_tenant_provider_returns_404(self, client, token) -> None:
        other_token = _make_jwt({"tenant_id": "attacker-tenant"})
        client.post(
            "/api-governance/providers",
            json={
                "name": "Victim-Provider",
                "vendor": "TestVendor",
                "endpoint": "https://example.com/v1/api",
                "token": "victim-key-abcdefgh12345678",
                "billing_unit": "token",
                "tokens_purchased": 100000,
                "target_margin": 0.67,
            },
            headers=_bearer(token),
        )
        providers = client.get("/api-governance/providers", headers=_bearer(token)).json()["providers"]
        victim_id = providers[-1]["id"]

        # Attacker tries to disable victim's provider — must get 404, not 200
        resp = client.post(
            f"/api-governance/providers/{victim_id}/disable",
            json={"reason": "attacker reason"},
            headers=_bearer(other_token, "attacker-tenant"),
        )
        assert resp.status_code == 404
