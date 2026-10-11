from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException

from backend.fastapi.app import database, deps, oidc
from backend.fastapi.app.production_middleware import validate_environment
from backend.fastapi.app.security_context import OrganizationContext


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(private_key, claims: dict) -> str:
    header = _b64url(json.dumps({"alg": "RS256", "kid": "test-key", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{header}.{payload}.{_b64url(signature)}"


@pytest.fixture
def oidc_settings() -> oidc.OIDCSettings:
    return oidc.OIDCSettings(
        issuer="https://nuxtron.us.auth0.com",
        audience="https://api.nuxtron.test",
        jwks_url="https://nuxtron.us.auth0.com/.well-known/jwks.json",
    )


@pytest.fixture
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def jwks_loader(monkeypatch, private_key):
    async def load(settings: oidc.OIDCSettings, *, force_refresh: bool = False) -> dict:
        return {"test-key": private_key.public_key()}

    monkeypatch.setattr(oidc, "_load_jwks", load)


@pytest.mark.asyncio
async def test_oidc_accepts_valid_auth0_style_claims(oidc_settings, private_key, jwks_loader):
    claims = {
        "iss": f"{oidc_settings.issuer}/",
        "aud": [oidc_settings.audience],
        "sub": "auth0|alice",
        "organization_id": "org-acme",
        "roles": ["operator"],
        "exp": int(time.time()) + 300,
        "jti": "jti-1",
    }
    verified = await oidc.verify_oidc_jwt(_token(private_key, claims), oidc_settings)
    assert verified["sub"] == "auth0|alice"
    assert verified["organization_id"] == "org-acme"


@pytest.mark.asyncio
async def test_oidc_rejects_invalid_audience(oidc_settings, private_key, jwks_loader):
    claims = {
        "iss": f"{oidc_settings.issuer}/",
        "aud": ["https://wrong.example"],
        "sub": "auth0|alice",
        "organization_id": "org-acme",
        "exp": int(time.time()) + 300,
    }
    with pytest.raises(oidc.OIDCVerificationError, match="audience"):
        await oidc.verify_oidc_jwt(_token(private_key, claims), oidc_settings)


@pytest.mark.asyncio
async def test_oidc_rejects_missing_organization_claim(oidc_settings, private_key, jwks_loader):
    claims = {
        "iss": f"{oidc_settings.issuer}/",
        "aud": oidc_settings.audience,
        "sub": "auth0|alice",
        "exp": int(time.time()) + 300,
    }
    with pytest.raises(oidc.OIDCVerificationError, match="organization"):
        await oidc.verify_oidc_jwt(_token(private_key, claims), oidc_settings)


@pytest.mark.asyncio
async def test_production_revocation_check_fails_closed_on_redis_outage(monkeypatch):
    async def no_redis():
        return None

    monkeypatch.setattr(deps, "_is_production_environment", lambda: True)
    monkeypatch.setattr("app.redis_cache.get_redis", no_redis)
    with pytest.raises(HTTPException) as exc_info:
        await deps._is_token_revoked("jti-production")
    assert exc_info.value.status_code == 503


def test_organization_context_is_derived_from_verified_auth_context():
    context = OrganizationContext.from_auth(
        deps.AuthContext(
            tenant_id="org-acme",
            external_organization_id="org-acme",
            auth_mode="oidc_bearer",
            subject="auth0|alice",
            roles=["operator"],
            jti="jti-1",
        )
    )
    assert context.organization_id == "org-acme"
    assert context.external_organization_id == "org-acme"
    assert context.subject == "auth0|alice"
    assert context.allows_role("operator") is True
    assert context.allows_role("billing_admin") is False


def test_organization_scoped_session_requires_an_organization():
    with pytest.raises(ValueError, match="organization_id is required"):
        with database.organization_scoped_session(" "):
            pass


def test_organization_scoped_session_works_for_local_sqlite():
    with database.organization_scoped_session("org-acme") as session:
        assert session.is_active is True


def test_rls_foundation_migration_has_fail_closed_read_and_write_policies():
    migration = (
        Path(__file__).resolve().parents[2] / "alembic" / "versions" / "6c3e8f1a2b77_organization_rls_foundation.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert "FOR ALL" in source
    assert "USING ({column} = NULLIF(current_setting('{setting}', true), '')::uuid)" in source
    assert "WITH CHECK ({column} = NULLIF(current_setting('{setting}', true), '')::uuid)" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "oauth_tokens" in source
    assert "intel_targets" in source


def test_production_environment_requires_oidc_and_strict_mapping(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SIGNING_KEY", "legacy-only-test-key")
    monkeypatch.setenv("APP_ENC_KEY", "app-encryption-test-key")
    monkeypatch.setenv("PASSWORD_PEPPER", "password-pepper-test")
    monkeypatch.delenv("AUTH0_ISSUER", raising=False)
    monkeypatch.delenv("AUTH0_AUDIENCE", raising=False)
    monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("ORG_IDENTITY_MAPPING_REQUIRED", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(RuntimeError, match="AUTH0_ISSUER"):
        validate_environment()


def test_production_environment_requires_durable_infrastructure(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SIGNING_KEY", "legacy-only-test-key")
    monkeypatch.setenv("APP_ENC_KEY", "app-encryption-test-key")
    monkeypatch.setenv("PASSWORD_PEPPER", "password-pepper-test")
    monkeypatch.setenv("AUTH0_ISSUER", "https://tenant.example.auth0.com/")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://api.example.com")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "credential-encryption-test-key")
    monkeypatch.setenv("ORG_IDENTITY_MAPPING_REQUIRED", "true")
    monkeypatch.setenv("SECURITY_AUDIT_DURABLE", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_environment()


def test_organization_resolver_handles_database_factory_failure_in_compatibility_mode(monkeypatch):
    from backend.fastapi.app.domains.identity import organization_identity

    monkeypatch.setenv("ORG_IDENTITY_MAPPING_REQUIRED", "false")
    monkeypatch.setattr(
        organization_identity,
        "get_db_session_sync",
        lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    resolved = organization_identity.resolve_external_organization("org-acme")
    assert resolved.external_organization_id == "org-acme"
    assert resolved.tenant_id == "org-acme"


def test_organization_resolver_fails_closed_when_mapping_is_required(monkeypatch):
    from backend.fastapi.app.domains.identity import organization_identity

    monkeypatch.setenv("ORG_IDENTITY_MAPPING_REQUIRED", "true")
    monkeypatch.setattr(
        organization_identity,
        "get_db_session_sync",
        lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    with pytest.raises(HTTPException) as exc_info:
        organization_identity.resolve_external_organization("org-acme")
    assert exc_info.value.status_code == 503
