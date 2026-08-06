from __future__ import annotations

import datetime

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

    from backend.fastapi.app import legacy_main as lm
    from backend.fastapi.app import memory_stores

    for store in memory_stores.get_all_stores().values():
        store.clear()

    lm._rate_buckets.clear()
    lm._ai_generated_assets_memory.clear()
    lm._content_generations_memory.clear()
    lm._content_generation_jobs_memory.clear()
    with lm._content_generation_telemetry_lock:
        lm._content_generation_telemetry['strict_rejections_total'] = 0
        lm._content_generation_telemetry['strict_rejections_by_reason'] = {}
        lm._content_generation_telemetry['fallback_attempts_total'] = 0
        lm._content_generation_telemetry['fallback_attempts_by_reason'] = {}
        lm._content_generation_telemetry['timeout_failures_total'] = 0
        lm._content_generation_telemetry['updated_at'] = None

    yield


@pytest.fixture
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db() -> None:
    return None
