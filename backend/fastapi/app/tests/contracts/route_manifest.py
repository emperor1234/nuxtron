"""Build and verify a deterministic route/OpenAPI contract manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HTTP_METHODS = frozenset({"delete", "get", "head", "options", "patch", "post", "put", "trace"})
MANIFEST_VERSION = 1
DEFAULT_BASELINE = Path(__file__).with_name("route_openapi_manifest.json")


@dataclass(frozen=True)
class SchemaFailureExpectation:
    methods: frozenset[str]
    operation_id: str
    exception: str
    normalized_detail: str


KNOWN_SCHEMA_FAILURES = {
    (frozenset({"POST"}), "/content/generate/async"): SchemaFailureExpectation(
        methods=frozenset({"POST"}),
        operation_id="submit_content_generation_job_content_generate_async_post",
        exception="PydanticUserError",
        normalized_detail="content_request_model:is-not-fully-defined:class-not-fully-defined",
    )
}


class UnexpectedSchemaGenerationError(RuntimeError):
    """Raised when a route outside the fixed legacy allowlist breaks OpenAPI."""


def _resolve_local_refs(value: Any, document: Mapping[str, Any], seen: frozenset[str] = frozenset()) -> Any:
    if isinstance(value, Mapping):
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/") and reference not in seen:
            resolved: Any = document
            for part in reference[2:].split("/"):
                resolved = resolved[part.replace("~1", "/").replace("~0", "~")]
            resolved = _resolve_local_refs(resolved, document, seen | {reference})
            siblings = {
                str(key): _resolve_local_refs(item, document, seen)
                for key, item in value.items()
                if key != "$ref"
            }
            if isinstance(resolved, Mapping):
                return {**resolved, **siblings}
            return {"allOf": [resolved], **siblings}
        return {str(key): _resolve_local_refs(item, document, seen) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_resolve_local_refs(item, document, seen) for item in value]
    return value


def _content_schemas(content: object, document: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(content, Mapping):
        return {}
    schemas: dict[str, Any] = {}
    for media_type, media in content.items():
        if isinstance(media, Mapping) and "schema" in media:
            schemas[str(media_type)] = _resolve_local_refs(media["schema"], document)
    return schemas


def _request_schemas(
    path_item: Mapping[str, Any],
    operation: Mapping[str, Any],
    document: Mapping[str, Any],
) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    parameters = [*path_item.get("parameters", []), *operation.get("parameters", [])]
    if parameters:
        selected["parameters"] = _resolve_local_refs(parameters, document)
    request_body = _resolve_local_refs(operation.get("requestBody", {}), document)
    if isinstance(request_body, Mapping):
        content = _content_schemas(request_body.get("content"), document)
        if content:
            selected["content"] = content
    return selected


def _response_schemas(operation: Mapping[str, Any], document: Mapping[str, Any]) -> dict[str, Any]:
    responses = operation.get("responses")
    if not isinstance(responses, Mapping):
        return {}
    selected: dict[str, Any] = {}
    for status, response in responses.items():
        resolved = _resolve_local_refs(response, document)
        if not isinstance(resolved, Mapping):
            continue
        content = _content_schemas(resolved.get("content"), document)
        if content:
            selected[str(status)] = content
    return selected


def _stable_hash(value: Mapping[str, Any]) -> str | None:
    if not value:
        return None
    canonical = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def build_route_manifest(openapi: Mapping[str, Any]) -> dict[str, Any]:
    """Return one deterministic contract record per OpenAPI HTTP operation."""
    paths = openapi.get("paths")
    if not isinstance(paths, Mapping):
        raise ValueError("OpenAPI document must contain a paths mapping")

    routes: list[dict[str, Any]] = []
    for path, raw_path_item in paths.items():
        if not isinstance(raw_path_item, Mapping):
            continue
        path_item = _resolve_local_refs(raw_path_item, openapi)
        for method, raw_operation in path_item.items():
            normalized_method = str(method).lower()
            if normalized_method not in HTTP_METHODS or not isinstance(raw_operation, Mapping):
                continue
            operation = _resolve_local_refs(raw_operation, openapi)
            routes.append(
                {
                    "method": normalized_method.upper(),
                    "operation_id": operation.get("operationId"),
                    "path": str(path),
                    "request_schema_hash": _stable_hash(_request_schemas(path_item, operation, openapi)),
                    "response_schema_hash": _stable_hash(_response_schemas(operation, openapi)),
                }
            )

    routes.sort(key=lambda route: (route["path"], route["method"], str(route["operation_id"])))
    return {"manifest_version": MANIFEST_VERSION, "routes": routes}


def _generate_openapi(app: Any, routes: list[Any]) -> dict[str, Any]:
    from fastapi.openapi.utils import get_openapi

    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        summary=app.summary,
        description=app.description,
        routes=routes,
        separate_input_output_schemas=app.separate_input_output_schemas,
    )


def _normalize_schema_error_detail(error: Exception) -> str:
    detail = " ".join(str(error).split())
    required_markers = (
        "ForwardRef('content_request_model')",
        "is not fully defined",
        "/class-not-fully-defined",
    )
    if all(marker in detail for marker in required_markers):
        return "content_request_model:is-not-fully-defined:class-not-fully-defined"
    return detail


def _route_failure_expectation(route: Any, error: Exception) -> SchemaFailureExpectation:
    path = getattr(route, "path", None)
    methods = frozenset(str(method).upper() for method in (getattr(route, "methods", None) or []))
    operation_id = getattr(route, "unique_id", None)
    exception_name = type(error).__name__
    normalized_detail = _normalize_schema_error_detail(error)

    expectation = KNOWN_SCHEMA_FAILURES.get((methods, path))
    if (
        expectation is not None
        and methods == expectation.methods
        and operation_id == expectation.operation_id
        and exception_name == expectation.exception
        and normalized_detail == expectation.normalized_detail
    ):
        return expectation

    identity = f"{'/'.join(sorted(methods)) or '<no-method>'} {path or '<no-path>'}"
    raise UnexpectedSchemaGenerationError(
        f"Unexpected OpenAPI schema failure for {identity} ({operation_id}): "
        f"{exception_name}: {normalized_detail}"
    ) from error


def _partition_openapi_routes(app: Any, routes: list[Any]) -> tuple[list[Any], list[tuple[Any, SchemaFailureExpectation]]]:
    """Separate legacy routes whose unresolved annotations break schema generation."""
    try:
        _generate_openapi(app, routes)
    except Exception as error:  # noqa: BLE001 - converted to a strict allowlisted failure below
        if len(routes) == 1:
            return [], [(routes[0], _route_failure_expectation(routes[0], error))]
        midpoint = len(routes) // 2
        left_valid, left_invalid = _partition_openapi_routes(app, routes[:midpoint])
        right_valid, right_invalid = _partition_openapi_routes(app, routes[midpoint:])
        return left_valid + right_valid, left_invalid + right_invalid
    return routes, []


def build_app_route_manifest(app: Any) -> dict[str, Any]:
    """Build the exact app manifest while isolating legacy OpenAPI defects."""
    all_routes = list(app.routes)
    valid_routes, allowed_failures = _partition_openapi_routes(app, all_routes)
    try:
        openapi = _generate_openapi(app, valid_routes)
    except Exception as error:  # noqa: BLE001 - a group-only failure is unexpected and fatal
        raise UnexpectedSchemaGenerationError(
            f"Unexpected OpenAPI schema failure while combining {len(valid_routes)} individually valid routes: "
            f"{type(error).__name__}: {error}"
        ) from error
    manifest = build_route_manifest(openapi)
    represented = {(route["method"], route["path"]) for route in manifest["routes"]}

    for route, expectation in allowed_failures:
        path = getattr(route, "path", None)
        if not isinstance(path, str):
            continue
        for method in sorted(expectation.methods):
            key = (method.upper(), path)
            if key in represented or method.lower() not in HTTP_METHODS:
                continue
            manifest["routes"].append(
                {
                    "method": method.upper(),
                    "operation_id": getattr(route, "unique_id", None),
                    "path": path,
                    "request_schema_hash": None,
                    "response_schema_hash": None,
                    "schema_generation_failure": {
                        "exception": expectation.exception,
                        "normalized_detail": expectation.normalized_detail,
                    },
                }
            )

    manifest["routes"].sort(key=lambda route: (route["path"], route["method"], str(route["operation_id"])))
    return manifest


def write_manifest(manifest: Mapping[str, Any], baseline_path: Path = DEFAULT_BASELINE) -> None:
    baseline_path.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def assert_manifest_matches(manifest: Mapping[str, Any], baseline_path: Path = DEFAULT_BASELINE) -> None:
    if not baseline_path.exists():
        raise AssertionError(f"Route contract baseline is missing: {baseline_path}")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert manifest == baseline, (
        "Route/OpenAPI contract changed. Review the API difference, then regenerate the baseline with "
        "`PYTHONPATH=. backend/fastapi/.venv312/bin/python -m "
        "backend.fastapi.app.tests.contracts.route_manifest --write` if intentional."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="replace the checked-in baseline")
    args = parser.parse_args()

    from backend.fastapi.app.main import app

    manifest = build_app_route_manifest(app)
    if args.write:
        write_manifest(manifest)
    else:
        assert_manifest_matches(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
