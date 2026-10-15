from __future__ import annotations

import datetime
import os

os.environ.setdefault("ENVIRONMENT", "development")

# Python 3.9 compatibility: datetime.UTC was added in 3.11.
if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.UTC  # type: ignore[attr-defined]

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_shared_fastapi_state(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("no_legacy"):
        yield
        return

    from backend.fastapi.app.testing_state import reset_process_state_for_tests

    include_redis = os.getenv("NUXTRON_TEST_RESET_REDIS", "").strip().lower() in {"1", "true", "yes", "on"}
    reset_process_state_for_tests(include_redis=include_redis)

    yield


@pytest.fixture
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db() -> None:
    return None
