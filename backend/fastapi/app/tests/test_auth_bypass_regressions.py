"""Regression tests for two authentication bypasses.

Both were reachable from the public internet through the Next.js proxy, which
forwards arbitrary paths to FastAPI with the service key attached.
"""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

# Imported at module scope on purpose: FastAPI resolves parameter annotations
# against module globals, so a locally-imported AuthDep would be treated as a
# query parameter and every request would 422 instead of authenticating.
from backend.fastapi.app.dependencies import AuthDep  # noqa: E402


@pytest.fixture()
def probe_client() -> TestClient:
    """A minimal AuthDep-protected route."""
    app = FastAPI()

    @app.get("/probe")
    def probe(auth: AuthDep) -> dict[str, str]:
        return {"tenant_id": auth.tenant_id}

    return TestClient(app, raise_server_exceptions=False)


def disable_pytest_shim(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn off the pytest-only bearer shim in `get_auth`.

    Call this from the test body, never from fixture setup: pytest rewrites
    PYTEST_CURRENT_TEST at the start of each phase, so a value cleared during
    setup is restored before the test itself runs.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


class TestBearerTestBypass:
    """`Authorization: Bearer test*` must not authenticate outside pytest.

    The branch in get_auth had no test-mode guard, so any token starting with
    "test" produced a populated AuthContext with auth_mode='bearer_jwt' — an
    unauthenticated bypass of every AuthDep route, and the exact mode that
    unlocks /auth/jwt/issue.
    """

    @pytest.mark.parametrize(
        "token",
        [
            "Bearer test",
            "Bearer test_token",
            "Bearer test-token-123",
            "bearer TEST_anything",
            "Bearer testing",
        ],
    )
    def test_bearer_test_tokens_are_rejected(
        self, probe_client: TestClient, monkeypatch: pytest.MonkeyPatch, token: str
    ) -> None:
        disable_pytest_shim(monkeypatch)
        response = probe_client.get("/probe", headers={"Authorization": token})
        assert response.status_code in (401, 403), (
            f"{token!r} authenticated as {response.json()!r}"
        )

    def test_missing_authorization_is_rejected(
        self, probe_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        disable_pytest_shim(monkeypatch)
        assert probe_client.get("/probe").status_code in (401, 403)

    def test_shim_still_available_to_the_suite(self, probe_client: TestClient) -> None:
        """Without the override, the shim stays available so existing tests pass."""
        response = probe_client.get("/probe", headers={"Authorization": "Bearer test_token"})
        assert response.status_code == 200
        assert response.json()["tenant_id"] == "test-tenant-123"


class TestJwtIssueAdditionalClaims:
    """additional_claims must not override server-owned claims.

    The handler built the reserved claims and then called
    `claims.update(payload.additional_claims)`, so a caller could pass
    {'tenant_id': victim, 'roles': ['super_admin']} and have the server sign
    it — defeating the subject and role checks immediately above.
    """

    def test_reserved_claims_are_enumerated(self) -> None:
        from backend.fastapi.app.routers.auth import _RESERVED_JWT_CLAIMS

        assert {"sub", "tenant_id", "roles", "iat", "exp", "iss", "jti"} <= _RESERVED_JWT_CLAIMS

    def test_reserved_claims_survive_a_hostile_payload(self) -> None:
        from backend.fastapi.app.routers.auth import _RESERVED_JWT_CLAIMS

        hostile = {
            "tenant_id": "victim-tenant",
            "roles": ["super_admin"],
            "sub": "someone-else",
            "exp": 9_999_999_999,
            "iss": "evil",
            "harmless": "kept",
        }
        extra = {k: v for k, v in hostile.items() if k not in _RESERVED_JWT_CLAIMS}
        claims = {
            **extra,
            "sub": "caller-id",
            "tenant_id": "caller-tenant",
            "roles": ["user"],
            "iat": 1_000,
            "exp": 4_600,
            "iss": "nuxtron-fastapi",
            "jti": "abc123",
        }

        assert claims["tenant_id"] == "caller-tenant"
        assert claims["roles"] == ["user"]
        assert claims["sub"] == "caller-id"
        assert claims["exp"] == 4_600
        assert claims["iss"] == "nuxtron-fastapi"
        # Non-reserved extras remain supported.
        assert claims["harmless"] == "kept"

    def test_source_merges_extras_before_reserved_claims(self) -> None:
        """Guards the merge *order*, which is what makes the filter effective."""
        import inspect

        from backend.fastapi.app.routers import auth as auth_module

        source = inspect.getsource(auth_module)
        assert "claims.update(payload.additional_claims)" not in source, (
            "additional_claims is merged over the reserved claims again"
        )
        assert "**extra_claims," in source
