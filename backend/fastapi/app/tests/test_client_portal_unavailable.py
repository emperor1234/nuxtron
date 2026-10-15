from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "client-portal-unavailable-test"}
UNAVAILABLE_REQUESTS: list[tuple[str, str, dict[str, Any] | None, bool]] = [
    ("post", "/client-portal/clients", {"name": "Acme"}, True),
    ("get", "/client-portal/clients", None, True),
    ("get", "/client-portal/clients/client-id", None, True),
    ("patch", "/client-portal/clients/client-id", {"name": "Acme Updated"}, True),
    ("delete", "/client-portal/clients/client-id", None, True),
    ("post", "/client-portal/reports", {"client_id": "client-id", "domains": ["example.com"]}, True),
    ("get", "/client-portal/reports", None, True),
    ("get", "/client-portal/reports/report-id", None, True),
    ("get", "/client-portal/reports/report-id/download", None, True),
    ("delete", "/client-portal/reports/report-id", None, True),
    ("post", "/client-portal/share-link", {"report_id": "report-id"}, True),
    ("get", "/client-portal/share-link/share-token", None, False),
    (
        "post",
        "/client-portal/templates",
        {"name": "Template", "sections": ["overview"]},
        True,
    ),
    ("get", "/client-portal/templates", None, True),
    ("post", "/client-portal/schedules", {"client_id": "client-id", "frequency": "monthly"}, True),
    ("get", "/client-portal/schedules", None, True),
    ("delete", "/client-portal/schedules/schedule-id", None, True),
]


@pytest.mark.parametrize(("method", "path", "payload", "requires_auth"), UNAVAILABLE_REQUESTS)
def test_client_portal_routes_fail_closed_without_fabricated_success(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    requires_auth: bool,
) -> None:
    request = getattr(client, method)
    kwargs: dict[str, Any] = {}
    if requires_auth:
        kwargs["headers"] = HEADERS
    if payload is not None:
        kwargs["json"] = payload

    response = request(path, **kwargs)

    assert response.status_code == 501, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "NOT_IMPLEMENTED"
    assert "no sample metrics are generated" in detail["message"].lower()


def test_client_portal_tenant_routes_still_require_authentication(client: TestClient) -> None:
    response = client.get("/client-portal/clients")
    assert response.status_code in {401, 403}


def test_client_portal_501_contract_is_documented_for_every_route(client: TestClient) -> None:
    paths = client.app.openapi()["paths"]
    route_paths = {path for path in paths if path.startswith("/client-portal/")}
    assert len(route_paths) == 10
    for path in route_paths:
        for operation in paths[path].values():
            assert "501" in operation["responses"]
