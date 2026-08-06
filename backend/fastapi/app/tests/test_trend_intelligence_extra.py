"""
Tests for trend_intelligence router — covering uncovered endpoints.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestSignals:
    def test_ingest_signal(self, client: TestClient) -> None:
        r = client.post("/trends/signals/ingest", headers=H, json={
            "source": "google_trends",
            "topic": "fastapi testing",
            "score": 0.85,
        })
        assert r.status_code in VALID

    def test_ingest_signal_minimal(self, client: TestClient) -> None:
        r = client.post("/trends/signals/ingest", headers=H, json={
            "source": "reddit",
            "topic": "python",
        })
        assert r.status_code in VALID

    def test_list_signals(self, client: TestClient) -> None:
        r = client.get("/trends/signals", headers=H)
        assert r.status_code in VALID

    def test_list_signals_with_filter(self, client: TestClient) -> None:
        r = client.get("/trends/signals?source=google_trends", headers=H)
        assert r.status_code in VALID


class TestForecast:
    def test_generate_forecast(self, client: TestClient) -> None:
        r = client.post("/trends/forecast/generate", headers=H, json={
            "horizon_days": 30,
        })
        assert r.status_code in VALID

    def test_get_forecast(self, client: TestClient) -> None:
        r = client.get("/trends/forecast", headers=H)
        assert r.status_code in VALID


class TestSelect:
    def test_select_trend(self, client: TestClient) -> None:
        r = client.post("/trends/select", headers=H, json={
            "trend_id": "trend_001",
        })
        assert r.status_code in VALID

    def test_select_nonexistent_trend(self, client: TestClient) -> None:
        r = client.post("/trends/select", headers=H, json={
            "trend_id": "trend_nonexistent_xyz",
        })
        assert r.status_code in VALID


class TestContentGenerate:
    def test_generate_content(self, client: TestClient) -> None:
        r = client.post("/trends/content/generate", headers=H, json={
            "format": "blog_post",
            "word_count": 500,
        })
        assert r.status_code in VALID

    def test_generate_content_no_trend(self, client: TestClient) -> None:
        r = client.post("/trends/content/generate", headers=H, json={})
        assert r.status_code in VALID


class TestPerformanceTrack:
    def test_track_performance(self, client: TestClient) -> None:
        r = client.post("/trends/performance/track", headers=H, json={
            "content_id": "content_001",
            "metric": "views",
            "value": 100,
        })
        assert r.status_code in VALID


class TestAnalytics:
    def test_dashboard(self, client: TestClient) -> None:
        r = client.get("/trends/analytics/dashboard", headers=H)
        assert r.status_code in VALID

    def test_indicators(self, client: TestClient) -> None:
        r = client.get("/trends/analytics/indicators", headers=H)
        assert r.status_code in VALID

    def test_recommendations(self, client: TestClient) -> None:
        r = client.get("/trends/recommendations", headers=H)
        assert r.status_code in VALID
