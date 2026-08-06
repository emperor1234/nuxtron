from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestCdnAnalyticsCoverage:
    def test_register_provider_and_dashboard(self, client: TestClient) -> None:
        tenant = "cdn-coverage-tenant"
        register = client.post(
            "/api/v1/cdn/register",
            params={"provider": "vercel", "api_key": "test-key", "X-Tenant-Id": tenant},
        )
        assert register.status_code == 200
        assert register.json()["status"] == "registered"

        sync = client.post(
            "/api/v1/cdn/sync",
            params={"hours": 24, "X-Tenant-Id": tenant},
        )
        assert sync.status_code == 200
        assert "vercel" in sync.json()
        assert sync.json()["vercel"] >= 1

        dashboard = client.get(
            "/api/v1/cdn/dashboard",
            params={"days": 7, "X-Tenant-Id": tenant},
        )
        assert dashboard.status_code == 200
        body = dashboard.json()
        assert "providers" in body
        assert "vercel" in body["providers"]
        assert body["providers"]["vercel"]["total_requests"] > 0

    def test_provider_analytics_and_costs(self, client: TestClient) -> None:
        tenant = "cdn-coverage-tenant-2"
        client.post(
            "/api/v1/cdn/register",
            params={"provider": "cloudflare", "api_key": "test-key", "X-Tenant-Id": tenant},
        )

        provider = client.get(
            "/api/v1/cdn/provider/cloudflare",
            params={"days": 7, "X-Tenant-Id": tenant},
        )
        assert provider.status_code == 200
        assert provider.json()["provider"] == "cloudflare"

        costs = client.get(
            "/api/v1/cdn/costs",
            params={"X-Tenant-Id": tenant},
        )
        assert costs.status_code == 200
        body = costs.json()
        assert body["total_cost"] > 0
        assert body["cheapest_provider"]
