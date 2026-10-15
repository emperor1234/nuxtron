"""Fail-closed contract tests for the retired server-backed Rank Tracker."""

from __future__ import annotations

import os

import pytest

os.environ["ALLOW_HEADER_API_KEYS"] = "true"
os.environ["FASTAPI_API_KEY"] = "test-api-key"

import backend.fastapi.app.routers.rank_tracker as rank_tracker  # noqa: E402
from backend.fastapi.app.legacy_main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)
BASE = "/rank-tracker"
HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rank-review-tenant"}

ROUTES = [
    ("POST", "/tracked-keywords", {"keyword": "seo tools"}, None),
    ("GET", "/tracked-keywords", None, None),
    ("DELETE", "/tracked-keywords/keyword-id", None, None),
    ("POST", "/add-project", {"domain": "example.com", "location": "US", "search_engine": "Google"}, None),
    ("GET", "/projects", None, None),
    ("DELETE", "/projects/project-id", None, None),
    ("GET", "/positions", None, None),
    ("POST", "/positions/check", {"keywords": ["seo software"]}, None),
    ("POST", "/competitors", {"domain": "other.example"}, None),
    ("GET", "/competitors", None, None),
    ("DELETE", "/competitors/competitor-id", None, None),
    ("GET", "/history", None, None),
    ("GET", "/lost-gained", None, None),
    ("GET", "/visibility-score", None, None),
    ("GET", "/forecasts", None, None),
    ("GET", "/analytics", None, None),
    ("POST", "/alerts/set", {"keyword_id": "keyword-id", "alert_type": "rank_drop", "threshold": 5}, None),
    ("GET", "/alerts", None, None),
    ("GET", "/keyword-research/sources", None, None),
    ("GET", "/keyword-research/vendors", None, None),
    ("POST", "/keyword-research/discover", {"seed_keyword": "workflow software", "location": "United States", "language": "en", "max_results": 20}, None),
    ("POST", "/keyword-research/content-gap", {"your_domain": "example.com", "competitor_domains": ["other.example"], "max_results": 10}, None),
    ("POST", "/oauth/google-ads-callback", None, {"code": "code", "state": "state"}),
    ("POST", "/oauth/gsc-callback", None, {"code": "code", "state": "state"}),
    ("POST", "/provider-config/init-oauth", None, {"provider": "google_keyword_planner", "redirect_uri": "https://example.com/callback"}),
    ("GET", "/provider-config/status", None, None),
]


def unexpected_call(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("retired Rank Tracker routes must not read stores or call providers")


@pytest.mark.parametrize("method,path,payload,params", ROUTES)
def test_rank_tracker_routes_fail_closed_before_side_effects(
    method: str,
    path: str,
    payload: dict[str, object] | None,
    params: dict[str, str] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for helper in (
        "_get_projects",
        "_get_tracked_keywords",
        "_get_competitors",
        "_get_position_history",
        "_get_alerts",
        "_get_provider_config",
        "_run_provider_chain",
        "_http_json_request",
    ):
        if hasattr(rank_tracker, helper):
            monkeypatch.setattr(rank_tracker, helper, unexpected_call)

    request_options: dict[str, object] = {"headers": HEADERS}
    if payload is not None:
        request_options["json"] = payload
    if params is not None:
        request_options["params"] = params

    response = client.request(method, f"{BASE}{path}", **request_options)

    assert response.status_code == 501, f"{method} {path}: {response.text}"
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"


def test_rank_tracker_openapi_does_not_advertise_success_responses() -> None:
    from backend.fastapi.app.main import app as main_app

    paths = main_app.openapi()["paths"]
    for path, path_item in paths.items():
        if not path.startswith("/rank-tracker/"):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            assert "501" in responses, f"{method.upper()} {path} lacks the 501 contract"
            assert "200" not in responses and "201" not in responses, f"{method.upper()} {path} advertises success"


def test_authentication_is_still_required_before_unavailable_response() -> None:
    response = client.get(f"{BASE}/positions")
    assert response.status_code in {401, 403}
