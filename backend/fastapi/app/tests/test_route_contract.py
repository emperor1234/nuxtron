"""Contract tests for the exact HTTP/OpenAPI surface."""

from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest
from backend.fastapi.app.tests.contracts import route_manifest
from backend.fastapi.app.tests.contracts.route_manifest import (
    UnexpectedSchemaGenerationError,
    assert_manifest_matches,
    build_app_route_manifest,
    build_route_manifest,
)

BASELINE_PATH = Path(__file__).parent / "contracts" / "route_openapi_manifest.json"


def _sample_openapi() -> dict[str, object]:
    return {
        "openapi": "3.1.0",
        "components": {
            "schemas": {
                "Widget": {"type": "object", "properties": {"id": {"type": "string"}}},
                "WidgetInput": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
        "paths": {
            "/widgets/{widget_id}": {
                "get": {
                    "operationId": "get_widget",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Widget"}
                                }
                            }
                        }
                    },
                },
                "post": {
                    "operationId": "replace_widget",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/WidgetInput"}
                            }
                        }
                    },
                    "responses": {"204": {"description": "Updated"}},
                },
            }
        },
    }


def test_route_manifest_is_deterministic_and_schema_sensitive() -> None:
    spec = _sample_openapi()

    manifest = build_route_manifest(spec)
    assert manifest == build_route_manifest(copy.deepcopy(spec))
    assert [(route["method"], route["path"]) for route in manifest["routes"]] == [
        ("GET", "/widgets/{widget_id}"),
        ("POST", "/widgets/{widget_id}"),
    ]

    changed_spec = copy.deepcopy(spec)
    paths = changed_spec["paths"]
    assert isinstance(paths, dict)
    get_operation = paths["/widgets/{widget_id}"]["get"]
    get_operation["responses"]["200"]["content"]["application/json"]["schema"] = {
        "type": "string"
    }
    changed_manifest = build_route_manifest(changed_spec)

    assert (
        manifest["routes"][0]["response_schema_hash"]
        != changed_manifest["routes"][0]["response_schema_hash"]
    )


def test_openapi_31_ref_siblings_affect_request_and_response_hashes() -> None:
    spec = _sample_openapi()
    path_item = spec["paths"]["/widgets/{widget_id}"]
    path_item["post"]["requestBody"]["content"]["application/json"]["schema"]["description"] = "request v1"
    path_item["get"]["responses"]["200"]["content"]["application/json"]["schema"]["description"] = "response v1"
    original = build_route_manifest(spec)

    changed = copy.deepcopy(spec)
    changed_path_item = changed["paths"]["/widgets/{widget_id}"]
    changed_path_item["post"]["requestBody"]["content"]["application/json"]["schema"]["description"] = "request v2"
    changed_path_item["get"]["responses"]["200"]["content"]["application/json"]["schema"]["description"] = "response v2"
    updated = build_route_manifest(changed)

    assert original["routes"][1]["request_schema_hash"] != updated["routes"][1]["request_schema_hash"]
    assert original["routes"][0]["response_schema_hash"] != updated["routes"][0]["response_schema_hash"]


def _fake_app(route: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        routes=[route],
        title="test",
        version="1",
        openapi_version="3.1.0",
        summary=None,
        description="",
        separate_input_output_schemas=True,
    )


def test_known_schema_failure_is_allowlisted_and_represented(monkeypatch: pytest.MonkeyPatch) -> None:
    known_route = SimpleNamespace(
        path="/content/generate/async",
        methods={"POST"},
        unique_id="submit_content_generation_job_content_generate_async_post",
    )

    class PydanticUserError(Exception):
        pass

    def fake_generate_openapi(_app: object, routes: list[object]) -> dict[str, object]:
        if routes:
            raise PydanticUserError(
                "ForwardRef('content_request_model') is not fully defined; "
                "https://errors.pydantic.dev/2.11/u/class-not-fully-defined"
            )
        return {"openapi": "3.1.0", "paths": {}}

    monkeypatch.setattr(route_manifest, "_generate_openapi", fake_generate_openapi)

    manifest = build_app_route_manifest(_fake_app(known_route))

    assert manifest["routes"] == [
        {
            "method": "POST",
            "operation_id": "submit_content_generation_job_content_generate_async_post",
            "path": "/content/generate/async",
            "request_schema_hash": None,
            "response_schema_hash": None,
            "schema_generation_failure": {
                "exception": "PydanticUserError",
                "normalized_detail": "content_request_model:is-not-fully-defined:class-not-fully-defined",
            },
        }
    ]


def test_schema_failure_allowance_requires_exact_method_set(monkeypatch: pytest.MonkeyPatch) -> None:
    mixed_method_route = SimpleNamespace(
        path="/content/generate/async",
        methods={"GET", "POST"},
        unique_id="submit_content_generation_job_content_generate_async_post",
    )

    class PydanticUserError(Exception):
        pass

    def fake_generate_openapi(_app: object, routes: list[object]) -> dict[str, object]:
        if routes:
            raise PydanticUserError(
                "ForwardRef('content_request_model') is not fully defined; "
                "https://errors.pydantic.dev/2.11/u/class-not-fully-defined"
            )
        return {"openapi": "3.1.0", "paths": {}}

    monkeypatch.setattr(route_manifest, "_generate_openapi", fake_generate_openapi)

    with pytest.raises(UnexpectedSchemaGenerationError, match=r"GET/POST /content/generate/async"):
        build_app_route_manifest(_fake_app(mixed_method_route))


def test_schema_failure_allowance_rejects_near_match_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    known_route = SimpleNamespace(
        path="/content/generate/async",
        methods={"POST"},
        unique_id="submit_content_generation_job_content_generate_async_post",
    )

    class PydanticUserError(Exception):
        pass

    def fake_generate_openapi(_app: object, routes: list[object]) -> dict[str, object]:
        if routes:
            raise PydanticUserError("ForwardRef('content_request_model') is not fully defined")
        return {"openapi": "3.1.0", "paths": {}}

    monkeypatch.setattr(route_manifest, "_generate_openapi", fake_generate_openapi)

    with pytest.raises(UnexpectedSchemaGenerationError, match="PydanticUserError"):
        build_app_route_manifest(_fake_app(known_route))


def test_unexpected_schema_failure_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    unknown_route = SimpleNamespace(
        path="/new-broken-route",
        methods={"GET"},
        unique_id="new_broken_route_get",
    )

    def fake_generate_openapi(_app: object, routes: list[object]) -> dict[str, object]:
        if routes:
            raise RuntimeError("new schema failure")
        return {"openapi": "3.1.0", "paths": {}}

    monkeypatch.setattr(route_manifest, "_generate_openapi", fake_generate_openapi)

    with pytest.raises(UnexpectedSchemaGenerationError, match=r"GET /new-broken-route.*RuntimeError"):
        build_app_route_manifest(_fake_app(unknown_route))


def test_current_route_manifest_matches_checked_in_baseline() -> None:
    from backend.fastapi.app.main import app

    assert_manifest_matches(build_app_route_manifest(app), BASELINE_PATH)
