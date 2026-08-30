"""Baseline application smoke tests for safe modularisation work."""

from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "smoke-test-api-key")


def test_application_imports_and_registers_core_routes() -> None:
    """The application must be importable from its package, not cwd-dependent."""
    from backend.fastapi.app.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    # Count unique paths: some routers intentionally expose the same routes
    # under versioned prefixes, so ``len(app.routes)`` is higher than this.
    assert len(paths) >= 1_900
    assert "/healthz" in paths
    assert "/ai/gateway/generate" in paths
    assert "/ai/security/analytics" in paths


def test_sensitive_ai_routes_require_authentication() -> None:
    from fastapi.testclient import TestClient

    from backend.fastapi.app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/ai/security/analytics").status_code in {401, 403}
        assert client.post("/ai/gateway/generate", json={"prompt": "test"}).status_code in {401, 403}


def test_content_generate_requires_authentication() -> None:
    from fastapi.testclient import TestClient

    from backend.fastapi.app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/content/generate", json={"topic": "launch", "audience": "founders", "channel": "linkedin"})
        assert response.status_code in {401, 403}


def test_integrations_tools_and_metrics_require_authentication() -> None:
    from fastapi.testclient import TestClient

    from backend.fastapi.app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/integrations/tools").status_code in {401, 403}
        assert client.get("/metrics").status_code in {401, 403}


def test_frontend_compat_and_semrush_routes_exist_and_require_auth() -> None:
    from fastapi.testclient import TestClient

    from backend.fastapi.app.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/ai/gateway/status" in paths
    assert "/search-everywhere/semrush/projects" in paths
    assert "/social/trends" in paths
    assert "/ops/finance/credits/ledger" in paths

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/ai/gateway/status").status_code in {401, 403}


def test_wildcard_cors_does_not_allow_credentials(monkeypatch) -> None:
    """A permissive development origin must never enable browser credentials."""
    monkeypatch.setenv("CORS_ORIGINS", "*")

    from fastapi.testclient import TestClient

    from backend.fastapi.app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.options(
            "/healthz",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.headers.get("access-control-allow-credentials") != "true"
