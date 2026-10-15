"""Contract tests for the explicit FastAPI composition root in ``app.bootstrap``."""

from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Iterator
from unittest.mock import patch

import pytest
from fastapi import Header, Request

REPO_ROOT = Path(__file__).resolve().parents[4]
BASELINE_PATH = Path(__file__).parent / "contracts" / "route_openapi_manifest.json"

MODULE_LINE_TARGET = 300
WIRING_MODULE_LINE_LIMIT = 150
WIRING_MODULES = frozenset({"context_registry.py"})

# Declared bottom-up: Starlette stores ``user_middleware`` in reverse order of
# registration, so this is the exact inverse of the ``add_middleware`` calls.
EXPECTED_MIDDLEWARE_STACK = (
    "TrustedProxyMiddleware",
    "CORSMiddleware",
    "TrustedHostMiddleware",
    "RequestTracingMiddleware",
    "SensitiveRouteTokenMiddleware",
    "SecurityHeadersMiddleware",
)

IMPORT_SIDE_EFFECT_GUARD = """
import asyncio
import socket


def _guard(kind):
    def _blocked(*args, **kwargs):
        raise AssertionError('import-time ' + kind)

    return _blocked


socket.socket.connect = _guard('socket connect')
socket.create_connection = _guard('socket create_connection')
asyncio.create_task = _guard('asyncio task creation')

import psycopg

psycopg.connect = _guard('psycopg connect')
psycopg.Connection.connect = _guard('psycopg connection open')

import backend.fastapi.app.bootstrap as bootstrap_package
import backend.fastapi.app.bootstrap.context_registry as context_registry
import backend.fastapi.app.bootstrap.lifespan as lifespan_module
import backend.fastapi.app.bootstrap.middleware as middleware_module
from backend.fastapi.app.bootstrap.application import app, create_app

assert app is bootstrap_package.app
assert callable(create_app)
assert context_registry is not None and lifespan_module is not None and middleware_module is not None
print('IMPORT_SIDE_EFFECT_GUARD_OK')
"""


def _route_keys(app: Any) -> Counter[tuple[str, tuple[str, ...]]]:
    return Counter(
        (getattr(route, "path", ""), tuple(sorted(getattr(route, "methods", None) or ())))
        for route in app.routes
    )


@pytest.fixture(scope="module")
def created_apps() -> Iterator[tuple[Any, Any]]:
    from backend.fastapi.app.bootstrap.application import create_app

    with patch.dict(
        os.environ,
        {"ALLOW_HEADER_API_KEYS": "1", "FASTAPI_API_KEY": "test-api-key"},
    ):
        yield create_app(), create_app()


@pytest.mark.no_legacy
def test_bootstrap_imports_have_no_database_network_or_worker_side_effects() -> None:
    dependency_paths = [path for path in sys.path if "site-packages" in path]
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(REPO_ROOT), *dependency_paths]),
        "NUXTRON_SKIP_STARTUP_DB_INIT": "1",
    }

    result = subprocess.run(
        [sys.executable, "-c", IMPORT_SIDE_EFFECT_GUARD],
        capture_output=True,
        text=True,
        env=environment,
        timeout=300,
        check=False,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "IMPORT_SIDE_EFFECT_GUARD_OK" in result.stdout


def test_create_app_registers_every_route_exactly_once(created_apps: tuple[Any, Any]) -> None:
    first, _ = created_apps

    keys = _route_keys(first)
    repeated = {key for key, count in keys.items() if count > 1}

    assert repeated == set()


def test_bootstrap_legacy_compatibility_imports_are_explicit_and_usable() -> None:
    from backend.fastapi.app import generated_asset_store
    from backend.fastapi.app import legacy_main as legacy
    from backend.fastapi.app.services import ai_providers, integrations

    assert legacy._minio_presign is integrations._minio_presign
    assert legacy._verify_stripe_signature is integrations._verify_stripe_signature
    assert legacy._generate_media_asset_bundle is ai_providers._generate_media_asset_bundle
    assert callable(legacy._run_optional_ai_generation)
    assert legacy._find_ai_generated_asset is generated_asset_store.find_generated_asset
    assert legacy._ai_generated_assets_memory is generated_asset_store.ai_generated_assets
    assert legacy._ai_generated_assets_lock is generated_asset_store.ai_generated_assets_lock

    legacy.reset_rate_limits_for_tests()
    assert legacy._find_ai_generated_asset(999_999, "missing") is None

    source = (REPO_ROOT / "backend/fastapi/app/legacy_main.py").read_text()
    assert "_minio_presign as _minio_presign" in source
    assert "_generate_media_asset_bundle as _generate_media_asset_bundle" in source


def test_merged_route_exception_set_is_frozen() -> None:
    from backend.fastapi.app.bootstrap.route_compatibility import FROZEN_MERGED_HTTP_ROUTE_KEYS

    expected = frozenset(
        {
            ("GET", "/analytics/export"),
            ("GET", "/social/calendar"),
            ("GET", "/social/listening/mentions"),
            ("POST", "/social/team/invite"),
            ("GET", "/social/team/members"),
        }
    )
    assert expected == FROZEN_MERGED_HTTP_ROUTE_KEYS


def test_route_merge_rejects_unexpected_and_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.bootstrap import route_compatibility
    from fastapi import FastAPI

    monkeypatch.setattr(
        route_compatibility,
        "FROZEN_MERGED_HTTP_ROUTE_KEYS",
        frozenset({("GET", "/expected")}),
    )

    unexpected = FastAPI()
    unexpected.get("/outside")(lambda: {"winner": "first"})
    unexpected.get("/outside")(lambda: {"winner": "last"})
    with pytest.raises(RuntimeError, match="Unexpected shadowed HTTP route"):
        route_compatibility.merge_frozen_http_route_overlaps(unexpected)

    missing = FastAPI()
    with pytest.raises(RuntimeError, match="Expected shadowed HTTP routes are absent"):
        route_compatibility.merge_frozen_http_route_overlaps(missing)


def test_route_merge_rejects_partial_and_inconsistent_overlaps(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.bootstrap import route_compatibility
    from fastapi import FastAPI

    frozen = frozenset({("GET", "/mixed"), ("POST", "/mixed")})
    monkeypatch.setattr(route_compatibility, "FROZEN_MERGED_HTTP_ROUTE_KEYS", frozen)

    partial = FastAPI()
    partial.get("/mixed")(lambda: {"winner": "first"})
    partial.api_route("/mixed", methods=["GET", "POST"])(lambda: {"winner": "last"})
    with pytest.raises(RuntimeError, match="Partially shadowed HTTP route"):
        route_compatibility.merge_frozen_http_route_overlaps(partial)

    inconsistent = FastAPI()
    inconsistent.get("/mixed")(lambda: {"winner": "get"})
    inconsistent.post("/mixed")(lambda: {"winner": "post"})
    inconsistent.api_route("/mixed", methods=["GET", "POST"])(lambda: {"winner": "last"})
    with pytest.raises(RuntimeError, match="Inconsistent shadowed HTTP route"):
        route_compatibility.merge_frozen_http_route_overlaps(inconsistent)


def test_route_merge_preserves_runtime_position_scope_and_openapi(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.bootstrap import route_compatibility
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    monkeypatch.setattr(
        route_compatibility,
        "FROZEN_MERGED_HTTP_ROUTE_KEYS",
        frozenset({("POST", "/merged")}),
    )
    application = FastAPI()
    application.get("/before")(lambda: {"before": True})

    async def runtime_winner(request: Request) -> dict[str, str]:
        return {"winner": "runtime", "scope_endpoint": request.scope["endpoint"].__name__}

    def contract_auth(x_contract: Annotated[str, Header()]) -> str:
        return x_contract

    application.post("/merged", name="runtime-winner")(runtime_winner)
    runtime_position = next(i for i, route in enumerate(application.routes) if route.name == "runtime-winner")

    async def openapi_winner() -> str:
        return "openapi"

    application.post(
        "/merged",
        name="openapi_winner",
        operation_id="openapi-winner",
        response_model=str,
        dependencies=[Depends(contract_auth)],
    )(openapi_winner)
    application.get("/after")(lambda: {"after": True})

    route_compatibility.merge_frozen_http_route_overlaps(application)

    merged = next(route for route in application.routes if getattr(route, "path", None) == "/merged")
    assert application.routes.index(merged) == runtime_position
    assert merged.name == "runtime-winner"
    assert merged.endpoint is runtime_winner
    assert merged.unique_id == "openapi-winner"
    assert TestClient(application).post("/merged").json() == {
        "winner": "runtime",
        "scope_endpoint": "runtime_winner",
    }
    operation = application.openapi()["paths"]["/merged"]["post"]
    assert operation["operationId"] == "openapi-winner"
    assert operation["summary"] == "Openapi Winner"
    assert operation["parameters"][0]["name"] == "x-contract"
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "string"


def test_team_invite_keeps_historical_runtime_auth_and_response(created_apps: tuple[Any, Any]) -> None:
    from fastapi.testclient import TestClient

    first, _ = created_apps
    client = TestClient(first, raise_server_exceptions=False)
    payload = {"email": "milestone-two@example.com", "role": "editor"}

    assert client.post("/social/team/invite", json=payload).status_code == 401

    response = client.post(
        "/social/team/invite",
        headers={"X-API-Key": "test-api-key", "X-Tenant-Id": "bootstrap-regression"},
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["invite"]["email"] == payload["email"]


def test_only_frozen_routes_diverge_between_runtime_and_openapi_metadata(
    created_apps: tuple[Any, Any],
) -> None:
    from backend.fastapi.app.bootstrap.route_compatibility import FROZEN_MERGED_HTTP_ROUTE_KEYS

    first, _ = created_apps
    expected = {
        ("GET", "/analytics/export"): (
            "export_data",
            "export_analytics_csv_analytics_export_get",
            "Export Analytics Csv",
        ),
        ("GET", "/social/calendar"): (
            "list_calendar_events",
            "get_content_calendar_social_calendar_get",
            "Get Content Calendar",
        ),
        ("GET", "/social/listening/mentions"): (
            "list_social_listening_mentions",
            "list_listening_mentions_social_listening_mentions_get",
            "List Listening Mentions",
        ),
        ("POST", "/social/team/invite"): (
            "invite_team_member_legacy",
            "invite_team_member_social_team_invite_post",
            "Invite Team Member",
        ),
        ("GET", "/social/team/members"): (
            "list_team_members",
            "list_team_members_social_team_members_get",
            "List Team Members",
        ),
    }

    actual = {}
    for route in first.routes:
        for method in getattr(route, "methods", None) or ():
            key = (method, getattr(route, "path", ""))
            if key in expected:
                actual[key] = (route.name, route.unique_id, route.summary)
                assert route.endpoint.__name__ == expected[key][0]

    assert first.state.merged_http_route_keys == FROZEN_MERGED_HTTP_ROUTE_KEYS
    assert set(expected) == FROZEN_MERGED_HTTP_ROUTE_KEYS
    assert actual == expected


def test_repeated_create_app_calls_are_independent_with_equal_route_manifests(
    created_apps: tuple[Any, Any],
) -> None:
    from backend.fastapi.app.bootstrap.application import app as module_level_app

    first, second = created_apps

    assert first is not second
    assert first is not module_level_app
    assert first.router is not second.router
    assert _route_keys(first) == _route_keys(second) == _route_keys(module_level_app)


def test_middleware_stack_is_configured_exactly_once(created_apps: tuple[Any, Any]) -> None:
    from backend.fastapi.app.bootstrap.application import app as module_level_app

    first, second = created_apps

    for app in (module_level_app, first, second):
        stack = tuple(middleware.cls.__name__ for middleware in app.user_middleware)
        assert stack == EXPECTED_MIDDLEWARE_STACK
        assert len(stack) == len(set(stack))


def test_main_composition_and_bootstrap_export_the_same_application() -> None:
    from backend.fastapi.app import bootstrap, composition, legacy_main, main
    from backend.fastapi.app.bootstrap import application

    assert main.app is application.app
    assert composition.app is application.app
    assert bootstrap.app is application.app
    assert legacy_main.app is application.app
    assert main.create_app is composition.create_app is application.create_app


def test_bootstrap_modules_respect_the_plan_size_limits() -> None:
    bootstrap_root = Path(__file__).parents[1] / "bootstrap"

    oversized = []
    for module in sorted(bootstrap_root.glob("*.py")):
        lines = len(module.read_text(encoding="utf-8").splitlines())
        limit = WIRING_MODULE_LINE_LIMIT if module.name in WIRING_MODULES else MODULE_LINE_TARGET
        if lines > limit:
            oversized.append(f"{module.name} has {lines} lines (limit {limit})")

    assert not oversized, "\n".join(oversized)


def test_freshly_created_app_matches_the_checked_in_route_contract(
    created_apps: tuple[Any, Any],
) -> None:
    from backend.fastapi.app.tests.contracts.route_manifest import (
        assert_manifest_matches,
        build_app_route_manifest,
    )

    first, _ = created_apps

    assert_manifest_matches(build_app_route_manifest(first), BASELINE_PATH)
