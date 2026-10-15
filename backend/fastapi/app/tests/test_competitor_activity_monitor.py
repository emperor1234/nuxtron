from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-competitor-monitor-tenant"}

UNAVAILABLE_REQUESTS: list[tuple[str, str, dict[str, Any] | None]] = [
    ("post", "/eyeon/monitors", {"domain": "competitor.example"}),
    ("get", "/eyeon/monitors", None),
    ("delete", "/eyeon/monitors/monitor-id", None),
    ("get", "/eyeon/feed?limit=1", None),
    ("get", "/eyeon/feed/monitor-id?limit=1", None),
    ("get", "/eyeon/content-changes", None),
    ("get", "/eyeon/ad-changes", None),
    ("get", "/eyeon/keyword-changes", None),
    ("get", "/eyeon/backlink-changes", None),
    ("post", "/eyeon/alerts", {"event_types": ["content_published"], "severity": "warning"}),
    ("get", "/eyeon/alerts", None),
    ("get", "/eyeon/summary", None),
]


@pytest.mark.parametrize(("method", "path", "payload"), UNAVAILABLE_REQUESTS)
def test_competitor_activity_endpoints_fail_closed_without_real_monitoring_sources(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    request = getattr(client, method)
    if payload is None:
        response = request(path, headers=HEADERS)
    else:
        response = request(path, headers=HEADERS, json=payload)

    assert response.status_code == 501, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "NOT_IMPLEMENTED"
    assert "no sample events are generated" in detail["message"].lower()


def test_competitor_activity_routes_still_require_authentication(client: TestClient) -> None:
    response = client.get("/eyeon/monitors")
    assert response.status_code in {401, 403}
