"""Fail-closed contracts for unsupported map-grid and local heatmap routes."""

from __future__ import annotations

import os

import pytest

os.environ["ALLOW_HEADER_API_KEYS"] = "true"
os.environ["FASTAPI_API_KEY"] = "test-api-key"

from backend.fastapi.app.main import app  # noqa: E402
from backend.fastapi.app.routers import local_heatmap, map_rank_tracker  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)
HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "local-rank-review-tenant"}

ROUTES = [
    ("POST", "/map-rank-tracker/projects", {"name": "Local", "business_name": "Example", "address": "", "lat": 40.0, "lng": -73.0}, None),
    ("GET", "/map-rank-tracker/projects", None, None),
    ("DELETE", "/map-rank-tracker/projects/project-id", None, None),
    ("POST", "/map-rank-tracker/keywords", {"project_id": "project-id", "keywords": ["plumber"]}, None),
    ("GET", "/map-rank-tracker/keywords/project-id", None, None),
    ("POST", "/map-rank-tracker/check", {"project_id": "project-id", "keyword_ids": []}, None),
    ("GET", "/map-rank-tracker/results/project-id", None, None),
    ("GET", "/map-rank-tracker/history/keyword-id", None, None),
    ("GET", "/map-rank-tracker/grid", None, {"keyword": "plumber", "lat": "40.0", "lng": "-73.0", "grid_size": "5"}),
    ("GET", "/map-rank-tracker/heatmap/keyword-id", None, None),
    ("GET", "/map-rank-tracker/competitors", None, {"keyword": "plumber", "lat": "40.0", "lng": "-73.0"}),
    ("POST", "/local-heatmap/business-profile", {"business_name": "Example", "address": "", "lat": 40.0, "lng": -73.0}, None),
    ("GET", "/local-heatmap/business-profile", None, None),
    ("POST", "/local-heatmap/scans", {"business_name": "Example", "keyword": "plumber", "center_lat": 40.0, "center_lng": -73.0}, None),
    ("GET", "/local-heatmap/scans", None, None),
    ("GET", "/local-heatmap/scans/scan-id", None, None),
    ("DELETE", "/local-heatmap/scans/scan-id", None, None),
    ("GET", "/local-heatmap/results/scan-id", None, None),
    ("GET", "/local-heatmap/history", None, None),
    ("GET", "/local-heatmap/comparison", None, {"scan_id_a": "scan-a", "scan_id_b": "scan-b"}),
]


def unexpected_call(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("unavailable map routes must not call providers or synthesize grids")


@pytest.mark.parametrize("method,path,payload,params", ROUTES)
def test_local_rank_routes_fail_closed_before_provider_or_storage_calls(
    method: str,
    path: str,
    payload: dict[str, object] | None,
    params: dict[str, str] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for module, helpers in (
        (map_rank_tracker, ("_dataforseo_request", "_places_nearby_search", "_make_grid_points", "_make_ranking_history")),
        (local_heatmap, ("_dataforseo_request", "_build_grid", "_aggregate")),
    ):
        for helper in helpers:
            if hasattr(module, helper):
                monkeypatch.setattr(module, helper, unexpected_call)

    request_options: dict[str, object] = {"headers": HEADERS}
    if payload is not None:
        request_options["json"] = payload
    if params is not None:
        request_options["params"] = params

    response = client.request(method, path, **request_options)

    assert response.status_code == 501, f"{method} {path}: {response.text}"
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"


def test_map_and_heatmap_openapi_responses_are_unavailable_only() -> None:
    paths = app.openapi()["paths"]
    for path, path_item in paths.items():
        if not path.startswith(("/map-rank-tracker/", "/local-heatmap/")):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            assert "501" in responses, f"{method.upper()} {path} lacks the 501 response"
            assert "200" not in responses and "201" not in responses, f"{method.upper()} {path} advertises success"


@pytest.mark.parametrize(
    "method,path,params",
    [
        ("GET", "/map-rank-tracker/projects", None),
        ("GET", "/map-rank-tracker/grid", {"keyword": "plumber", "lat": "40", "lng": "-73"}),
        ("GET", "/local-heatmap/business-profile", None),
        ("GET", "/local-heatmap/comparison", {"scan_id_a": "a", "scan_id_b": "b"}),
    ],
)
def test_map_and_heatmap_routes_require_authentication(
    method: str,
    path: str,
    params: dict[str, str] | None,
) -> None:
    response = client.request(method, path, params=params)

    assert response.status_code in {401, 403}
