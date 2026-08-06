"""Production readiness smoke checks for FastAPI runtime behavior."""

from __future__ import annotations

import pytest
from backend.fastapi.app.config import validate_startup_security
from backend.fastapi.app.production_middleware import validate_environment
from fastapi.testclient import TestClient

PROD_HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "prod-smoke-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_health_and_metrics_endpoints_do_not_crash(client: TestClient) -> None:
    for path in ["/health", "/health/live", "/health/ready", "/metrics"]:
        response = client.get(path, headers=PROD_HEADERS)
        if path == "/health/ready":
            assert response.status_code in {200, 503}
        else:
            assert response.status_code < 500


def test_sensitive_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/autonomous-workforce/capabilities")
    assert response.status_code in {401, 403}


def test_validate_environment_production_minimum_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SIGNING_KEY", "prod-signing-key")
    monkeypatch.setenv("APP_ENC_KEY", "prod-enc-key")
    monkeypatch.setenv("PASSWORD_PEPPER", "prod-pepper")

    result = validate_environment()

    assert result["JWT_SIGNING_KEY"] == "prod-signing-key"
    assert result["APP_ENC_KEY"] == "prod-enc-key"
    assert result["PASSWORD_PEPPER"] == "prod-pepper"


def test_validate_startup_security_rejects_default_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECURITY_STRICT_MODE", "1")
    monkeypatch.setenv("APP_ENC_KEY", "enc-key")
    monkeypatch.setenv("PASSWORD_PEPPER", "pepper")
    monkeypatch.setenv("FASTAPI_API_KEY", "change-this-fastapi-key")

    with pytest.raises(RuntimeError, match="FASTAPI_API_KEY must be changed"):
        validate_startup_security()
