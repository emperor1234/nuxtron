"""UGC operations remain unavailable until creator consent and publishing are verifiable."""

import os
from importlib import import_module

import pytest
from starlette.testclient import TestClient

os.environ["ALLOW_HEADER_API_KEYS"] = "true"
os.environ["FASTAPI_API_KEY"] = "test-api-key"

legacy_app = import_module("backend.fastapi.app.legacy_main").app
main_app = import_module("backend.fastapi.app.main").app

AUTH_HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "ugc-test-tenant"}

UGC_ROUTES = [
    ("GET", "/social/ugc", None),
    ("POST", "/social/ugc/discover", {"brand_domain": "brand.example", "limit": 10}),
    ("PATCH", "/social/ugc/1/approve", {"approved": True, "note": "reviewed"}),
    (
        "POST",
        "/social/ugc/1/republish",
        {"scheduled_time": "2030-01-01T10:00:00Z", "target_networks": ["instagram"], "add_credit": True},
    ),
    ("POST", "/social/ugc/1/request-rights", {"message": "May we use this?"}),
    ("POST", "/social/ugc/batch/approve", {"asset_ids": [1]}),
    ("GET", "/social/ugc/performance?asset_id=1", None),
]


@pytest.mark.parametrize("application", [main_app, legacy_app], ids=["main", "legacy"])
@pytest.mark.parametrize(("method", "path", "payload"), UGC_ROUTES)
def test_all_ugc_operations_fail_closed_without_success_or_cache(
    application, method: str, path: str, payload: dict | None
) -> None:
    response = TestClient(application).request(method, path, headers=AUTH_HEADERS, json=payload)

    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
    assert "no-store" in response.headers.get("cache-control", "").lower()


@pytest.mark.parametrize("application", [main_app, legacy_app], ids=["main", "legacy"])
def test_ugc_requires_authentication(application) -> None:
    response = TestClient(application).post(
        "/social/ugc/discover",
        json={"brand_domain": "brand.example"},
    )
    assert response.status_code in {401, 403}


def test_every_ugc_operation_documents_only_501_in_openapi() -> None:
    expected = {
        ("/social/ugc", "get"),
        ("/social/ugc/discover", "post"),
        ("/social/ugc/{asset_id}/approve", "patch"),
        ("/social/ugc/{asset_id}/republish", "post"),
        ("/social/ugc/{asset_id}/request-rights", "post"),
        ("/social/ugc/batch/approve", "post"),
        ("/social/ugc/performance", "get"),
    }
    paths = main_app.openapi()["paths"]
    for path, method in expected:
        responses = paths[path][method]["responses"]
        assert "501" in responses, f"{method.upper()} {path} must document unavailable data"
        assert "200" not in responses, f"{method.upper()} {path} must not advertise success"
