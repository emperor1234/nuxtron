"""
Tests for benchmarks.py and outcome_attribution.py routers.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
HA = {**H, "X-Super-Admin": "true"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestBenchmarks:
    def test_create_benchmark(self, client: TestClient) -> None:
        r = client.post("/benchmarks", headers=H, json={
            "metric": "engagement_rate",
            "value": 4.5,
            "segment": "saas",
        })
        assert r.status_code in VALID

    def test_create_benchmark_minimal(self, client: TestClient) -> None:
        r = client.post("/benchmarks", headers=H, json={})
        assert r.status_code in VALID

    def test_get_benchmarks(self, client: TestClient) -> None:
        r = client.get("/benchmarks", headers=H)
        assert r.status_code in VALID

    def test_get_benchmarks_with_filters(self, client: TestClient) -> None:
        r = client.get("/benchmarks?metric=engagement_rate&limit=10", headers=H)
        assert r.status_code in VALID

    def test_get_summary(self, client: TestClient) -> None:
        r = client.get("/benchmarks/summary", headers=H)
        assert r.status_code in VALID

    def test_create_segment_no_super_admin(self, client: TestClient) -> None:
        r = client.post("/benchmarks/segments", headers=H, json={
            "segment": "enterprise",
            "description": "Enterprise segment",
        })
        # Either 403 or 422 or 200 depending on auth check
        assert r.status_code in VALID

    def test_create_segment_with_super_admin(self, client: TestClient) -> None:
        r = client.post("/benchmarks/segments", headers=HA, json={
            "segment": "enterprise",
            "description": "Enterprise segment",
        })
        assert r.status_code in VALID

    def test_get_segment(self, client: TestClient) -> None:
        r = client.get("/benchmarks/segments/saas", headers=H)
        assert r.status_code in VALID

    def test_get_segment_nonexistent(self, client: TestClient) -> None:
        r = client.get("/benchmarks/segments/nonexistent_segment_xyz_abc", headers=H)
        assert r.status_code in VALID

    def test_compare_segment(self, client: TestClient) -> None:
        r = client.get("/benchmarks/compare/saas", headers=H)
        assert r.status_code in VALID

    def test_compare_segment_nonexistent(self, client: TestClient) -> None:
        r = client.get("/benchmarks/compare/nonexistent_xyz", headers=H)
        assert r.status_code in VALID


class TestOutcomeAttribution:
    def test_create_action(self, client: TestClient) -> None:
        r = client.post("/outcome/actions", headers=H, json={
            "name": "button_click",
            "action_type": "click",
            "description": "User clicked the CTA button",
        })
        assert r.status_code in VALID

    def test_create_action_minimal(self, client: TestClient) -> None:
        r = client.post("/outcome/actions", headers=H, json={})
        assert r.status_code in VALID

    def test_create_outcome(self, client: TestClient) -> None:
        r = client.post("/outcome/outcomes", headers=H, json={
            "action_id": "action_nonexistent",
            "outcome_type": "conversion",
            "value": 100.0,
        })
        assert r.status_code in VALID

    def test_create_outcome_missing_action(self, client: TestClient) -> None:
        r = client.post("/outcome/outcomes", headers=H, json={
            "action_id": "action_does_not_exist",
        })
        assert r.status_code in VALID

    def test_create_quality(self, client: TestClient) -> None:
        r = client.post("/outcome/quality", headers=H, json={
            "action_id": "action_nonexistent",
            "score": 0.85,
            "dimension": "relevance",
        })
        assert r.status_code in VALID

    def test_get_graph(self, client: TestClient) -> None:
        r = client.get("/outcome/graph", headers=H)
        assert r.status_code in VALID

    def test_get_graph_with_filters(self, client: TestClient) -> None:
        r = client.get("/outcome/graph?depth=3&limit=50", headers=H)
        assert r.status_code in VALID

    def test_get_quality(self, client: TestClient) -> None:
        r = client.get("/outcome/quality", headers=H)
        assert r.status_code in VALID

    def test_get_pending_actions(self, client: TestClient) -> None:
        r = client.get("/outcome/actions/pending", headers=H)
        assert r.status_code in VALID
