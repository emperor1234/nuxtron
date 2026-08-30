from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")


def auth_headers(tenant: str) -> dict[str, str]:
    """Credentials for the CDN routes.

    Tenant travels as an authenticated header, not a query parameter: the
    routes now derive their tenant from the verified auth context.
    """
    return {"X-API-Key": os.environ["FASTAPI_API_KEY"], "X-Tenant-Id": tenant}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestCdnAnalyticsAuth:
    """Every CDN route requires authentication.

    Only /register used to declare it, which left the other ten open to
    anonymous callers — including the state-changing /failover.
    """

    @pytest.mark.parametrize(
        "method,path",
        [
            ("post", "/api/v1/cdn/register"),
            ("post", "/api/v1/cdn/sync"),
            ("get", "/api/v1/cdn/dashboard"),
            ("get", "/api/v1/cdn/provider/vercel"),
            ("get", "/api/v1/cdn/comparison"),
            ("get", "/api/v1/cdn/costs"),
            ("get", "/api/v1/cdn/metrics/vercel"),
            ("get", "/api/v1/cdn/health"),
            ("get", "/api/v1/cdn/recommendations"),
            ("post", "/api/v1/cdn/failover"),
            ("get", "/api/v1/cdn/load-distribution"),
        ],
    )
    def test_requires_authentication(self, client: TestClient, method: str, path: str) -> None:
        response = getattr(client, method)(path, params={"X-Tenant-Id": "victim-tenant"})
        assert response.status_code in (401, 403), (
            f"{method.upper()} {path} answered {response.status_code} without credentials"
        )


class TestCdnAnalyticsCoverage:
    def test_register_provider_and_dashboard(self, client: TestClient) -> None:
        tenant = "cdn-coverage-tenant"
        headers = auth_headers(tenant)

        register = client.post(
            "/api/v1/cdn/register",
            json={"provider": "vercel", "api_key": "test-key"},
            headers=headers,
        )
        assert register.status_code == 200
        assert register.json()["status"] == "registered"
        assert register.json()["tenant_id"] == tenant

        sync = client.post("/api/v1/cdn/sync", params={"hours": 24}, headers=headers)
        assert sync.status_code == 200
        assert "vercel" in sync.json()
        assert sync.json()["vercel"] >= 1

        dashboard = client.get("/api/v1/cdn/dashboard", params={"days": 7}, headers=headers)
        assert dashboard.status_code == 200
        body = dashboard.json()
        assert "providers" in body
        assert "vercel" in body["providers"]
        assert body["providers"]["vercel"]["total_requests"] > 0

    def test_provider_analytics_and_costs(self, client: TestClient) -> None:
        tenant = "cdn-coverage-tenant-2"
        headers = auth_headers(tenant)

        client.post(
            "/api/v1/cdn/register",
            json={"provider": "cloudflare", "api_key": "test-key"},
            headers=headers,
        )

        provider = client.get("/api/v1/cdn/provider/cloudflare", params={"days": 7}, headers=headers)
        assert provider.status_code == 200
        assert provider.json()["provider"] == "cloudflare"

        costs = client.get("/api/v1/cdn/costs", headers=headers)
        assert costs.status_code == 200
        body = costs.json()
        assert body["total_cost"] > 0
        assert body["cheapest_provider"]

    def test_tenant_comes_from_auth_not_query_string(self, client: TestClient) -> None:
        """A caller cannot select another tenant via ?X-Tenant-Id=."""
        headers = auth_headers("real-tenant")

        register = client.post(
            "/api/v1/cdn/register",
            json={"provider": "fastly", "api_key": "test-key"},
            params={"X-Tenant-Id": "victim-tenant"},
            headers=headers,
        )
        assert register.status_code == 200
        assert register.json()["tenant_id"] == "real-tenant"
