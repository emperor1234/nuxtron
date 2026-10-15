from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    from backend.fastapi.app.bootstrap.application import app
    from backend.fastapi.app.deps import AuthContext, require_auth

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_auth] = lambda: AuthContext(
        tenant_id="auth-production-test",
        auth_mode="oidc_bearer",
        subject="auth-production-test-user",
        roles=["tenant_admin"],
    )
    test_client = TestClient(app, raise_server_exceptions=False)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("POST", "/auth/totp/setup", {}),
        ("POST", "/auth/totp/verify", {"secret": "JBSWY3DPEHPK3PXP", "code": "000000"}),
        ("POST", "/auth/jwt/issue", {"subject": "user-1", "roles": ["user"]}),
        ("POST", "/auth/jwt/verify", {"token": "a" * 24}),
        ("GET", "/auth/saml/metadata", None),
        ("GET", "/auth/saml/login", None),
        ("POST", "/auth/saml/acs", {"saml_response": "x" * 48}),
        ("POST", "/auth/register", {"email": "user@example.test", "password": "long-password-123"}),
        ("POST", "/auth/login", {"email": "user@example.test", "password": "long-password-123"}),
        ("POST", "/auth/password-reset/request", {"email": "user@example.test"}),
        (
            "POST",
            "/auth/password-reset/confirm",
            {"email": "user@example.test", "token": "a" * 32, "new_password": "new-long-password-123"},
        ),
    ],
)
def test_unconfigured_local_authentication_features_fail_explicitly_in_production(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SAML_ENABLED", "1")

    response = client.request(method, path, json=payload)

    assert response.status_code == 501, response.text
    assert isinstance(response.json().get("detail"), str)
    assert "production" in response.json()["detail"].lower()
