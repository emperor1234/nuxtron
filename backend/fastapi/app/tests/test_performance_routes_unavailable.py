"""Every customer Performance API operation remains unavailable without measured evidence."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from backend.fastapi.app.routers.tool_integrations import TOOLS
from fastapi.testclient import TestClient

pytestmark = pytest.mark.no_legacy

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "performance-unavailable-tenant"}

CALLS: list[tuple[str, str, dict[str, object]]] = [
    ("post", "/seo-platform/performance/audit", {"json": {"url": "https://example.com"}}),
    ("post", "/seo-platform/performance/rum/ingest", {"json": {"url": "https://example.com", "metric_name": "LCP", "value": 1200}}),
    ("get", "/seo-platform/performance/rum/summary", {"params": {"url": "https://example.com"}}),
    ("post", "/seo-platform/performance/tests", {"json": {"url": "https://example.com"}}),
    ("get", "/seo-platform/performance/tests/test-id", {}),
    ("post", "/seo-platform/performance/monitor/create", {"json": {"url": "https://example.com"}}),
    ("get", "/seo-platform/performance/monitors", {}),
    ("post", "/seo-platform/performance/monitors/test-id/run", {}),
    ("get", "/seo-platform/performance/alerts/events", {}),
    ("get", "/seo-platform/performance/report/analysis-id", {}),
    ("post", "/seo-platform/performance/report/analysis-id/share", {"json": {}}),
    ("get", "/seo-platform/performance/report/shared/share-token", {}),
    (
        "post",
        "/seo-platform/performance/reports/compare",
        {"json": {"baseline_analysis_id": "base", "candidate_analysis_id": "candidate"}},
    ),
    ("post", "/seo-platform/performance/auto-fix", {"json": {"url": "https://example.com"}}),
    ("get", "/seo-platform/performance/history", {"params": {"url": "https://example.com"}}),
    ("get", "/seo-platform/performance/crux/history", {"params": {"url": "https://example.com"}}),
    ("get", "/seo-platform/performance/browser-profiles", {}),
    ("get", "/seo-platform/performance/capabilities", {}),
    ("get", "/seo-platform/performance/test-locations", {}),
    ("get", "/seo-platform/performance/vendors", {}),
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(("method", "path", "options"), CALLS)
def test_performance_routes_fail_closed_without_model_work(
    client: TestClient, method: str, path: str, options: dict[str, object]
) -> None:
    with patch(
        "backend.fastapi.app.domains.seo.platform.services.extract_waterfall._ollama_json",
        new_callable=AsyncMock,
    ) as model:
        response = getattr(client, method)(path, headers=H, **options)

    assert response.status_code == 501, f"{method.upper()} {path} returned {response.status_code}"
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
    model.assert_not_awaited()


def test_retired_measurement_providers_are_not_advertised_as_customer_integrations() -> None:
    integration_keys = {str(tool.get("key", "")) for tool in TOOLS}
    assert {"lighthouse", "playwright_cdp", "web_vitals"}.isdisjoint(integration_keys)
