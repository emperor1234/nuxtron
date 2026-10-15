"""Contract tests for the retired, fail-closed Ads Control Tower API."""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

import pytest
from backend.fastapi.app.integrations.vendor_manager import get_vendor_manager
from backend.fastapi.app.main import app
from fastapi.testclient import TestClient

BASE = "/ads-control-tower"
HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "ads-control-tower-contract"}
LEGACY_OPERATIONS = [
    ("GET", "/ab-test/campaign-1/suggestions", None),
    ("POST", "/assets/auto-resize", {"asset_url": "https://example.invalid/ad.png", "platforms": ["google_ads"]}),
    ("GET", "/audience-insights", None),
    ("GET", "/best-time", None),
    ("GET", "/calendar", None),
    ("POST", "/calendar/drag-reschedule", {"campaign_id": "campaign-1", "new_date": "2026-10-14"}),
    ("GET", "/campaigns", None),
    ("POST", "/campaigns", {"campaign_name": "Do not create", "platform": "google_ads"}),
    ("DELETE", "/campaigns/campaign-1", None),
    ("GET", "/campaigns/campaign-1", None),
    ("PATCH", "/campaigns/campaign-1", {"campaign_name": "Do not update"}),
    ("POST", "/campaigns/campaign-1/approve", {"decision": "approved"}),
    ("POST", "/campaigns/campaign-1/duplicate", {"new_name": "Do not duplicate"}),
    ("POST", "/campaigns/campaign-1/metrics", {"impressions": 100}),
    ("POST", "/campaigns/campaign-1/publish", {"publish_all_connected_accounts": True}),
    ("POST", "/campaigns/campaign-1/request-approval", {"reviewer_email": "reviewer@example.invalid"}),
    ("GET", "/connectors", None),
    ("DELETE", "/connectors/google_ads", None),
    ("GET", "/connectors/google_ads/credentials/status", None),
    ("POST", "/connectors/google_ads/oauth/callback", {"code": "untrusted-test-code", "state": "untrusted-test-state"}),
    ("POST", "/connectors/google_ads/oauth/start", None),
    ("GET", "/credits", None),
    ("GET", "/forecast", None),
    ("GET", "/health", None),
    ("GET", "/kpis", None),
    ("GET", "/notifications", None),
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("method,path,payload", LEGACY_OPERATIONS)
def test_every_legacy_operation_fails_closed(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    response = client.request(method, f"{BASE}{path}", headers=HEADERS, json=payload)
    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
    assert response.headers["cache-control"] == "no-store"


def test_ads_api_requires_authentication(client: TestClient) -> None:
    response = client.get(f"{BASE}/health")
    assert response.status_code in (401, 403)


def test_openapi_exposes_only_typed_unavailable_catchall() -> None:
    paths = app.openapi()["paths"]
    path = f"{BASE}/{{legacy_path}}"
    operation = paths[path]["get"]
    assert "501" in operation["responses"]
    assert "200" not in operation["responses"]
    assert all(candidate == path for candidate in paths if candidate.startswith(f"{BASE}/"))


def test_fake_oauth_callback_does_not_store_vendor_credentials(client: TestClient) -> None:
    manager = get_vendor_manager()
    manager.revoke_credentials("google_ads_api")

    response = client.post(
        f"{BASE}/connectors/google_ads/oauth/callback",
        headers=HEADERS,
        json={"code": "untrusted-test-code", "state": "untrusted-test-state"},
    )

    assert response.status_code == 501
    assert manager.has_credentials("google_ads_api") is False
