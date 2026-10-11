"""Regression gates for the workflow decomposition and social durability seam."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.fastapi.app.domains.social import persistence

APP_ROOT = Path(__file__).parents[1]


def test_workflow_router_is_only_a_compatibility_alias() -> None:
    source = (APP_ROOT / "routers/workflows.py").read_text()
    assert len(source.splitlines()) <= 20
    assert "sys.modules" in source


def test_workflow_graph_is_independently_importable() -> None:
    from backend.fastapi.app.domains.workflows.graph import validate_steps, preview_graph_path

    assert validate_steps([{"step_id": "a", "action_type": "add_tag"}])["errors"] == []
    result = preview_graph_path([{"step_id": "a", "next_step_id": "a"}], "a")
    assert result["halt_reason"] == "cycle_detected:a"


@pytest.mark.parametrize("operation", ["read", "write"])
def test_social_profile_database_failure_is_not_success_in_production(monkeypatch, operation) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    state = persistence._SocialWorkspaceState(
        enforce_rate_limit=lambda *_: None,
        db_dsn_fn=lambda: "postgresql://unused",
        db_ready_fn=lambda: True,
        db_initialized=True,
    )

    def unavailable(*args, **kwargs):
        raise OSError("database unavailable")

    monkeypatch.setattr(persistence.psycopg, "connect", unavailable)
    with pytest.raises(HTTPException) as caught:
        if operation == "read":
            persistence._sw_load_profile_from_db(state, "org-a")
        else:
            persistence._sw_save_profile_to_db(state, {"tenant_id": "org-a"})
    assert caught.value.status_code == 503
    assert "database unavailable" not in str(caught.value.detail)


def test_social_profile_reads_cannot_smuggle_another_organization(monkeypatch) -> None:
    state = persistence._SocialWorkspaceState(
        enforce_rate_limit=lambda *_: None,
        db_dsn_fn=lambda: "postgresql://unused",
        db_ready_fn=lambda: True,
        db_initialized=True,
    )

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def cursor(self):
            return self

        def execute(self, *args):
            pass

        def fetchone(self):
            return ({"tenant_id": "org-b", "business_name": "private"},)

    monkeypatch.setattr(persistence.psycopg, "connect", lambda *_: Connection())
    with pytest.raises(HTTPException) as caught:
        persistence._sw_load_profile_from_db(state, "org-a")
    assert caught.value.status_code == 503
