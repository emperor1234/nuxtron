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


def test_promptwatch_end_to_end_automation_suite(client: TestClient) -> None:
    tenant_id = "tenant-promptwatch-search-everywhere"

    products = client.get(
        "/search-everywhere/promptwatch/products",
        headers=_headers(tenant_id),
    )
    assert products.status_code == 200, products.text
    products_payload = products.json()
    assert products_payload["status"] == "ok"
    assert products_payload["count"] >= 7

    detail = client.get(
        "/search-everywhere/promptwatch/products/detail/prompt-tracing",
        headers=_headers(tenant_id),
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["product"]["production_grade_ready"] is False

    wiring_apply = client.post(
        "/search-everywhere/promptwatch/wiring/apply",
        headers=_headers(tenant_id),
        json={
            "providers": ["PromptWatch", "OpenAI"],
            "include_all_missing": True,
            "include_optional_auth": True,
        },
    )
    assert wiring_apply.status_code == 200, wiring_apply.text
    wiring_apply_payload = wiring_apply.json()
    assert wiring_apply_payload.get("gate", {}).get("passed") is True

    full = client.post(
        "/search-everywhere/promptwatch/full-automation",
        headers=_headers(tenant_id),
        json={
            "seed_keyword": "llm prompt observability",
            "your_domain": "nuxtron.ai",
            "competitor_domains": ["promptwatch.com", "langsmith.com"],
            "location": "United States",
            "language": "en",
            "max_results": 10,
            "require_live_providers": False,
        },
    )
    assert full.status_code == 200, full.text
    full_payload = full.json()
    assert "promptwatch_modules" in full_payload
    assert full_payload.get("production_gate", {}).get("passed") is True

    verification = client.get(
        "/search-everywhere/promptwatch/verification-report",
        headers=_headers(tenant_id),
    )
    assert verification.status_code == 200, verification.text
    verification_payload = verification.json()
    assert verification_payload.get("verification", {}).get("slice_ready") is True
