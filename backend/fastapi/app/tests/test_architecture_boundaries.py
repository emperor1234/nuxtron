"""AST-based dependency and size guardrails for modularisation."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).parents[1]
CONTEXTS_ROOT = APP_ROOT / "contexts"

ALLOWED_INCLUDE_ROUTER_PATHS = frozenset(
    {
        Path("bootstrap/context_registry.py"),
        Path("composition.py"),
        Path("legacy_main.py"),
        Path("main_social.py"),
        Path("router_registration.py"),
        Path("routers/ops.py"),
    }
)
FORBIDDEN_DEPENDENCIES = {
    "aiohttp",
    "fastapi",
    "httpx",
    "psycopg",
    "psycopg2",
    "requests",
    "sqlalchemy",
}
HTTP_METHOD_DECORATORS = {
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
    "trace",
}
LEGACY_SIZE_RATCHET = {
    "composition.py": 13,
    "legacy_main.py": 2_740,
    # Contract-freeze baseline (2026-08-29): this ceiling may only decrease.
    "router_registration.py": 1_123,
}


@dataclass(frozen=True)
class TemporarySizeRatchet:
    ceiling: int
    reason: str


# Temporary exceptions must name one migrated file, explain the split plan, and
# use its current line count as the ceiling. Lower ceilings as files shrink.
TEMPORARY_SIZE_RATCHETS: dict[str, TemporarySizeRatchet] = {}


def _python_files(root: Path) -> Iterator[Path]:
    if not root.exists():
        return
    yield from sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
    )


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _include_router_calls(path: Path) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
    ]


def _is_allowed_composition_path(path: Path) -> bool:
    try:
        relative = path.relative_to(APP_ROOT)
    except ValueError:
        return False
    return relative in ALLOWED_INCLUDE_ROUTER_PATHS


def _import_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _module_parts(path: Path, app_root: Path = APP_ROOT) -> list[str]:
    relative = path.relative_to(app_root).with_suffix("")
    suffix = list(relative.parts)
    if suffix[-1] == "__init__":
        suffix.pop()
    return ["backend", "fastapi", "app", *suffix]


def _resolved_from_module(path: Path, node: ast.ImportFrom, app_root: Path = APP_ROOT) -> list[str]:
    if node.level == 0:
        return (node.module or "").split(".")
    package = _module_parts(path, app_root)
    if path.name != "__init__.py":
        package.pop()
    base = package[: len(package) - node.level + 1]
    return [*base, *((node.module or "").split(".") if node.module else [])]


def _context_reference(module: list[str]) -> tuple[str, list[str]] | None:
    prefixes = (["app", "contexts"], ["backend", "fastapi", "app", "contexts"])
    for prefix in prefixes:
        if module[: len(prefix)] == prefix and len(module) > len(prefix):
            return module[len(prefix)], module[len(prefix) + 1 :]
    return None


def _cross_context_import_violations(
    path: Path,
    *,
    contexts_root: Path = CONTEXTS_ROOT,
    app_root: Path = APP_ROOT,
) -> list[tuple[int, str]]:
    current_context = path.relative_to(contexts_root).parts[0]
    violations: list[tuple[int, str]] = []

    for node in ast.walk(_tree(path)):
        imports: list[tuple[list[str], bool]] = []
        if isinstance(node, ast.Import):
            imports.extend((alias.name.split("."), False) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _resolved_from_module(path, node, app_root)
            if module in (["app", "contexts"], ["backend", "fastapi", "app", "contexts"]):
                imports.extend(([*module, alias.name], False) for alias in node.names)
            else:
                imports.append((module, all(alias.name == "public" for alias in node.names)))

        for module, imports_public_from_context in imports:
            reference = _context_reference(module)
            if reference is None:
                continue
            imported_context, suffix = reference
            if imported_context == current_context:
                continue
            if suffix == ["public"] or (not suffix and imports_public_from_context):
                continue
            violations.append((node.lineno, ".".join(module)))

    return violations


def _router_receiver_names(tree: ast.Module) -> set[str]:
    names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and (node.id == "router" or node.id.endswith("_router"))
    }
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        constructor = value.func
        constructor_name = (
            constructor.id
            if isinstance(constructor, ast.Name)
            else constructor.attr
            if isinstance(constructor, ast.Attribute)
            else ""
        )
        if constructor_name not in {"APIRouter", "FastAPI"}:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names


def _immutable_method_constants(tree: ast.Module) -> dict[str, tuple[str, ...]]:
    constants: dict[str, tuple[str, ...]] = {}
    for node in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if (
            not isinstance(target, ast.Name)
            or not target.id.isupper()
            or not isinstance(value, ast.Tuple)
            or not all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in value.elts)
        ):
            continue
        constants[target.id] = tuple(str(element.value).upper() for element in value.elts)
    return constants


def _static_methods(value: ast.expr, constants: dict[str, tuple[str, ...]]) -> tuple[str, ...] | None:
    if isinstance(value, ast.Name):
        return constants.get(value.id)
    if isinstance(value, ast.Constant) and value.value is None:
        return ("GET",)
    if not isinstance(value, (ast.List, ast.Set, ast.Tuple)):
        return None
    if not all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in value.elts):
        return None
    return tuple(dict.fromkeys(str(element.value).upper() for element in value.elts))


def _api_route_method_count(decorator: ast.Call, constants: dict[str, tuple[str, ...]]) -> int | None:
    methods_keyword = next((keyword for keyword in decorator.keywords if keyword.arg == "methods"), None)
    if methods_keyword is None:
        return 1
    methods = _static_methods(methods_keyword.value, constants)
    return None if methods is None else len(methods)


def _endpoint_analysis(path: Path) -> tuple[int, list[str]]:
    tree = _tree(path)
    router_names = _router_receiver_names(tree)
    constants = _immutable_method_constants(tree)
    count = 0
    violations: list[str] = []
    try:
        display_path = path.relative_to(APP_ROOT).as_posix()
    except ValueError:
        display_path = path.name
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            receiver = decorator.func.value
            if not isinstance(receiver, ast.Name) or receiver.id not in router_names:
                continue
            if decorator.func.attr in HTTP_METHOD_DECORATORS:
                count += 1
            elif decorator.func.attr == "api_route":
                method_count = _api_route_method_count(decorator, constants)
                if method_count is None:
                    violations.append(
                        f"{display_path}:{decorator.lineno} api_route methods are not statically determinable"
                    )
                else:
                    count += method_count
    return count, violations


def _endpoint_count(path: Path) -> int:
    count, violations = _endpoint_analysis(path)
    if violations:
        raise ValueError("\n".join(violations))
    return count


def _is_router_module(path: Path, *, contexts_root: Path = CONTEXTS_ROOT) -> bool:
    relative = path.relative_to(contexts_root)
    parts = relative.parts
    under_api_package = len(parts) >= 3 and parts[1] == "api"
    context_level_router = len(parts) == 2 and path.stem in {"api", "router", "routes"}
    return under_api_package or context_level_router


def _is_wiring_module(path: Path, *, contexts_root: Path = CONTEXTS_ROOT) -> bool:
    relative = path.relative_to(contexts_root)
    return len(relative.parts) == 2 and path.stem in {"bootstrap", "wiring"}


def _module_size_violation(
    path: Path,
    lines: int,
    *,
    contexts_root: Path = CONTEXTS_ROOT,
    ratchets: dict[str, TemporarySizeRatchet] = TEMPORARY_SIZE_RATCHETS,
) -> str | None:
    relative = path.relative_to(contexts_root).as_posix()
    if lines > 500:
        return f"{relative} has {lines} lines (hard limit 500)"
    if _is_wiring_module(path, contexts_root=contexts_root):
        return f"{relative} has {lines} lines (wiring limit 150)" if lines > 150 else None
    if _is_router_module(path, contexts_root=contexts_root):
        return f"{relative} has {lines} lines (router limit 250)" if lines > 250 else None
    if lines <= 300:
        return None

    ratchet = ratchets.get(relative)
    if ratchet is None:
        return f"{relative} has {lines} lines (300-line target requires a temporary ratchet)"
    if not ratchet.reason.strip() or not 300 < ratchet.ceiling <= 500:
        return f"{relative} has an invalid temporary ratchet"
    if lines > ratchet.ceiling:
        return f"{relative} grew past its temporary {ratchet.ceiling}-line ratchet to {lines} lines"
    if lines < ratchet.ceiling:
        return (
            f"{relative} temporary ratchet {ratchet.ceiling} must equal its current freeze size {lines}; "
            "lower the ceiling"
        )
    return None


def test_include_router_is_confined_to_composition_locations() -> None:
    violations: list[str] = []
    for path in _python_files(APP_ROOT):
        calls = _include_router_calls(path)
        if not calls or _is_allowed_composition_path(path):
            continue
        for call in calls:
            violations.append(f"{path.relative_to(APP_ROOT)}:{call.lineno}")

    assert not violations, "include_router() is only allowed in bootstrap/composition modules:\n" + "\n".join(violations)


def test_application_and_domain_layers_are_framework_independent() -> None:
    violations: list[str] = []
    for path in _python_files(CONTEXTS_ROOT):
        relative_parts = path.relative_to(CONTEXTS_ROOT).parts
        if not {"application", "domain"}.intersection(relative_parts):
            continue
        forbidden = sorted(_import_roots(path) & FORBIDDEN_DEPENDENCIES)
        if forbidden:
            violations.append(f"{path.relative_to(APP_ROOT)} imports {', '.join(forbidden)}")

    assert not violations, "Framework/database/HTTP imports crossed an inner-layer boundary:\n" + "\n".join(violations)


def test_cross_context_imports_use_public_modules_only() -> None:
    violations = [
        f"{path.relative_to(APP_ROOT)}:{line} imports {module}"
        for path in _python_files(CONTEXTS_ROOT)
        for line, module in _cross_context_import_violations(path)
    ]
    assert not violations, "Cross-context imports must target the other context's public.py:\n" + "\n".join(violations)


def test_new_and_migrated_modules_respect_size_limits() -> None:
    violations: list[str] = []
    for path in _python_files(CONTEXTS_ROOT):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        size_violation = _module_size_violation(path, lines)
        if size_violation:
            violations.append(size_violation)
        if _is_router_module(path):
            endpoint_count, endpoint_violations = _endpoint_analysis(path)
            violations.extend(endpoint_violations)
            if endpoint_count > 8:
                violations.append(f"{path.relative_to(APP_ROOT)} has {endpoint_count} endpoints (limit 8)")

    assert not violations, "New/migrated module size ratchets failed:\n" + "\n".join(violations)


def test_legacy_hotspots_may_only_shrink() -> None:
    violations = []
    for relative, ceiling in LEGACY_SIZE_RATCHET.items():
        lines = len((APP_ROOT / relative).read_text(encoding="utf-8").splitlines())
        if lines > ceiling:
            violations.append(f"{relative} grew from its {ceiling}-line ceiling to {lines} lines")
    assert not violations, "Legacy hotspots must not grow:\n" + "\n".join(violations)


def test_composition_allowlist_uses_explicit_paths() -> None:
    assert _is_allowed_composition_path(APP_ROOT / "composition.py")
    assert _is_allowed_composition_path(APP_ROOT / "routers" / "ops.py")
    assert not _is_allowed_composition_path(APP_ROOT / "bootstrap.py")
    assert not _is_allowed_composition_path(APP_ROOT / "application.py")
    assert not _is_allowed_composition_path(APP_ROOT / "main_unreviewed.py")


def test_include_router_detection_is_receiver_agnostic(tmp_path: Path) -> None:
    source = tmp_path / "rogue.py"
    source.write_text("arbitrary_name.include_router(feature_router)\n", encoding="utf-8")

    assert len(_include_router_calls(source)) == 1
    assert not _is_allowed_composition_path(source)


def test_cross_context_imports_match_only_application_context_roots(tmp_path: Path) -> None:
    contexts_root = tmp_path / "contexts"
    source = contexts_root / "orders" / "application" / "handler.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "from app.contexts.billing.public import Invoice",
                "from backend.fastapi.app.contexts.billing.public import Payment",
                "from vendor.contexts.billing.internal import Unrelated",
            ]
        ),
        encoding="utf-8",
    )

    assert _cross_context_import_violations(source, contexts_root=contexts_root, app_root=tmp_path) == []


@pytest.mark.parametrize(
    "statement",
    [
        "from app.contexts import billing",
        "from backend.fastapi.app.contexts import billing",
        "from app.contexts.billing.internal import Invoice",
        "import backend.fastapi.app.contexts.billing.internal",
    ],
)
def test_cross_context_imports_reject_package_and_internal_access(tmp_path: Path, statement: str) -> None:
    contexts_root = tmp_path / "contexts"
    source = contexts_root / "orders" / "application" / "handler.py"
    source.parent.mkdir(parents=True)
    source.write_text(f"{statement}\n", encoding="utf-8")

    assert _cross_context_import_violations(source, contexts_root=contexts_root, app_root=tmp_path)


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("billing/api/schemas.py", True),
        ("billing/api/nested/helpers.py", True),
        ("billing/api.py", True),
        ("billing/routes.py", True),
        ("billing/router.py", True),
        ("billing/domain/routes.py", False),
    ],
)
def test_router_limits_cover_the_entire_api_surface(tmp_path: Path, relative: str, expected: bool) -> None:
    contexts_root = tmp_path / "contexts"
    assert _is_router_module(contexts_root / relative, contexts_root=contexts_root) is expected


def test_endpoint_count_handles_api_route_and_ignores_unrelated_decorators(tmp_path: Path) -> None:
    source = tmp_path / "router.py"
    source.write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                "router = APIRouter()",
                "",
                "@router.api_route('/items', methods=['GET', 'POST'])",
                "def items(): pass",
                "",
                "@router.get('/health')",
                "def health(): pass",
                "",
                "@cache.get('items')",
                "def cached_items(): pass",
            ]
        ),
        encoding="utf-8",
    )

    assert _endpoint_count(source) == 3


def test_endpoint_count_recognizes_apirouter_assignment(tmp_path: Path) -> None:
    source = tmp_path / "routes.py"
    source.write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                "feature = APIRouter()",
                "",
                "@feature.post('/items')",
                "def create_item(): pass",
            ]
        ),
        encoding="utf-8",
    )

    assert _endpoint_count(source) == 1


def test_endpoint_count_resolves_immutable_module_method_constant(tmp_path: Path) -> None:
    source = tmp_path / "routes.py"
    source.write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                "ITEM_METHODS = ('GET', 'POST')",
                "router = APIRouter()",
                "",
                "@router.api_route('/items', methods=ITEM_METHODS)",
                "def items(): pass",
            ]
        ),
        encoding="utf-8",
    )

    count, violations = _endpoint_analysis(source)

    assert count == 2
    assert violations == []


def test_endpoint_count_fails_closed_for_dynamic_api_route_methods(tmp_path: Path) -> None:
    source = tmp_path / "routes.py"
    source.write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                "router = APIRouter()",
                "",
                "@router.api_route('/items', methods=load_methods())",
                "def items(): pass",
            ]
        ),
        encoding="utf-8",
    )

    count, violations = _endpoint_analysis(source)

    assert count == 0
    assert violations == ["routes.py:4 api_route methods are not statically determinable"]


def test_module_size_target_requires_a_documented_temporary_ratchet(tmp_path: Path) -> None:
    contexts_root = tmp_path / "contexts"
    module = contexts_root / "billing" / "domain" / "ledger.py"
    relative = "billing/domain/ledger.py"
    ratchets = {
        relative: TemporarySizeRatchet(
            ceiling=350,
            reason="Split posting rules during billing migration",
        )
    }

    assert _module_size_violation(module, 300, contexts_root=contexts_root, ratchets={}) is None
    assert _module_size_violation(module, 301, contexts_root=contexts_root, ratchets={}) is not None
    assert _module_size_violation(module, 350, contexts_root=contexts_root, ratchets=ratchets) is None
    assert _module_size_violation(module, 351, contexts_root=contexts_root, ratchets=ratchets) is not None


def test_temporary_size_ratchet_has_no_growth_headroom(tmp_path: Path) -> None:
    contexts_root = tmp_path / "contexts"
    module = contexts_root / "billing" / "domain" / "ledger.py"
    ratchets = {
        "billing/domain/ledger.py": TemporarySizeRatchet(
            ceiling=350,
            reason="Split posting rules during billing migration",
        )
    }

    violation = _module_size_violation(module, 349, contexts_root=contexts_root, ratchets=ratchets)

    assert violation is not None
    assert "must equal its current freeze size" in violation


def test_module_size_hard_limit_cannot_be_excepted(tmp_path: Path) -> None:
    contexts_root = tmp_path / "contexts"
    module = contexts_root / "billing" / "domain" / "ledger.py"
    ratchets = {
        "billing/domain/ledger.py": TemporarySizeRatchet(
            ceiling=501,
            reason="Invalid attempted exception",
        )
    }

    violation = _module_size_violation(module, 501, contexts_root=contexts_root, ratchets=ratchets)

    assert violation is not None
    assert "hard limit 500" in violation
