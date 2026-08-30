"""Contract tests for the explicit FastAPI composition root in ``app.bootstrap``."""

from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
BASELINE_PATH = Path(__file__).parent / "contracts" / "route_openapi_manifest.json"

MODULE_LINE_TARGET = 300
WIRING_MODULE_LINE_LIMIT = 150
WIRING_MODULES = frozenset({"context_registry.py"})

# Declared bottom-up: Starlette stores ``user_middleware`` in reverse order of
# registration, so this is the exact inverse of the ``add_middleware`` calls.
EXPECTED_MIDDLEWARE_STACK = (
    "CORSMiddleware",
    "TrustedHostMiddleware",
    "RequestTracingMiddleware",
    "SensitiveRouteTokenMiddleware",
    "SecurityHeadersMiddleware",
)

# Frozen 2026-08-29: these paths are served by two different routers today and
# the first registration wins. Extraction must not add to this set.
KNOWN_SHADOWED_ROUTE_KEYS = frozenset(
    {
        ("/analytics/export", ("GET",)),
        ("/social/calendar", ("GET",)),
        ("/social/listening/mentions", ("GET",)),
        ("/social/team/invite", ("POST",)),
        ("/social/team/members", ("GET",)),
    }
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
def created_apps() -> tuple[Any, Any]:
    from backend.fastapi.app.bootstrap.application import create_app

    return create_app(), create_app()


@pytest.mark.no_legacy
def test_bootstrap_imports_have_no_database_network_or_worker_side_effects() -> None:
    environment = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
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

    assert repeated == KNOWN_SHADOWED_ROUTE_KEYS
    assert all(count <= 2 for count in keys.values())


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
