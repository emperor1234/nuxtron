"""Executable structural contracts for the migrated bounded contexts."""

import ast
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).parents[1]
MIGRATED = (
    "workflows",
    "search",
    "social",
    "crm",
    "assistant",
    "seo/platform",
    "social/inbox",
    "search/crawlers",
    "content/media",
    "marketing/ads",
    "intelligence/platform",
    "automation/workforce",
    "marketing/growth",
    "integrations/platforms",
    "integrations/cms",
    "notifications/delivery",
    "search/visibility",
)


def _imports(path):
    package = list(path.relative_to(ROOT).with_suffix("").parts)
    if path.name != "__init__.py":
        package.pop()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.level:
            prefix = package[: len(package) - node.level + 1]
            yield ".".join(prefix + (node.module or "").split("."))


@pytest.mark.parametrize("context", MIGRATED)
def test_no_module_import_cycles(context) -> None:
    files = list((ROOT / "domains" / context).rglob("*.py"))
    modules = {".".join(p.relative_to(ROOT).with_suffix("").parts): p for p in files}
    edges = {name: set(_imports(path)) & modules.keys() for name, path in modules.items()}
    done, active = set(), []

    def visit(name):
        assert name not in active, "Circular domain imports: " + " -> ".join(active + [name])
        if name in done:
            return
        active.append(name)
        for dependency in edges[name]:
            visit(dependency)
        active.pop()
        done.add(name)

    for name in edges:
        visit(name)


@pytest.mark.parametrize("context", MIGRATED)
def test_migrated_http_adapters_remain_small(context) -> None:
    for path in (ROOT / "domains" / context / "api").glob("*.py"):
        tree = ast.parse(path.read_text())
        endpoints = [
            n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.decorator_list
        ]
        assert len(endpoints) <= 8, str(path)
        assert len(path.read_text().splitlines()) <= 250, str(path)
        assert not any("CREATE TABLE" in ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call)), str(path)


def test_workflow_database_errors_fail_closed_in_production(monkeypatch) -> None:
    from backend.fastapi.app.domains.workflows import repository

    monkeypatch.setenv("ENVIRONMENT", "production")

    def unavailable(*args, **kwargs):
        raise OSError("database-secret-host")

    monkeypatch.setattr(repository, "get_db_session", unavailable)
    with pytest.raises(HTTPException) as caught:
        repository.store_list_workflows("org-a")
    assert caught.value.status_code == 503
    assert "secret-host" not in str(caught.value.detail)


def test_workflow_persistence_cannot_be_disabled_in_production(monkeypatch) -> None:
    from backend.fastapi.app.domains.workflows import repository

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("WORKFLOWS_DB_PERSISTENCE", "false")
    with pytest.raises(HTTPException):
        repository.persistence_enabled()
