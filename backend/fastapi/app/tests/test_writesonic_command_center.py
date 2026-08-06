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


def _headers(tenant_id: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": tenant_id,
        "X-API-Key": os.environ.get("FASTAPI_API_KEY", "test-api-key"),
    }


def test_writesonic_end_to_end_automation_suite(client: TestClient) -> None:
    tenant_id = "tenant-writesonic-search-everywhere"

    products = client.get(
        "/search-everywhere/writesonic/products",
        headers=_headers(tenant_id),
    )
    assert products.status_code == 200, products.text
    products_payload = products.json()
    assert products_payload["status"] == "ok"
    assert products_payload["count"] >= 6

    detail = client.get(
        "/search-everywhere/writesonic/products/detail/chatsonic",
        headers=_headers(tenant_id),
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["product"]["production_grade_ready"] is False

    features_before = client.get(
        "/search-everywhere/writesonic/features",
        headers=_headers(tenant_id),
    )
    assert features_before.status_code == 200, features_before.text
    features_before_payload = features_before.json()
    assert features_before_payload.get("summary", {}).get("features_total", 0) >= 18
    assert features_before_payload.get("summary", {}).get("integration_configured_pct") == 0.0

    wiring_apply = client.post(
        "/search-everywhere/writesonic/wiring/apply",
        headers=_headers(tenant_id),
        json={
            "providers": ["OpenAI", "WordPress"],
            "include_all_missing": True,
            "include_optional_auth": True,
        },
    )
    assert wiring_apply.status_code == 200, wiring_apply.text
    wiring_apply_payload = wiring_apply.json()
    assert wiring_apply_payload.get("gate", {}).get("passed") is True

    full = client.post(
        "/search-everywhere/writesonic/full-automation",
        headers=_headers(tenant_id),
        json={
            "seed_keyword": "ai content automation",
            "your_domain": "nuxtron.ai",
            "competitor_domains": ["writesonic.com", "jasper.ai"],
            "location": "United States",
            "language": "en",
            "max_results": 10,
            "require_live_providers": False,
        },
    )
    assert full.status_code == 200, full.text
    full_payload = full.json()
    assert "writesonic_modules" in full_payload
    assert "photosonic" in full_payload.get("writesonic_modules", {})
    assert "audiosonic" in full_payload.get("writesonic_modules", {})
    assert "feature_registry_summary" in full_payload
    assert full_payload.get("feature_registry_summary", {}).get("features_total", 0) >= 18
    assert full_payload.get("production_gate", {}).get("passed") is True

    features_after = client.get(
        "/search-everywhere/writesonic/features",
        headers=_headers(tenant_id),
    )
    assert features_after.status_code == 200, features_after.text
    features_after_payload = features_after.json()
    assert features_after_payload.get("summary", {}).get("integration_configured_pct") == 100.0
    assert features_after_payload.get("summary", {}).get("e2e_verified_pct") == 100.0

    verification = client.get(
        "/search-everywhere/writesonic/verification-report",
        headers=_headers(tenant_id),
    )
    assert verification.status_code == 200, verification.text
    verification_payload = verification.json()
    assert verification_payload.get("verification", {}).get("slice_ready") is True
    assert len(verification_payload.get("verification", {}).get("feature_evidence_table", [])) >= 18
