"""Tests for Answer Engine router hardening.

Validates that the Answer Engine router is production-safe by:
- Requiring real authentication (require_auth dependency)
- Gating write operations on in-memory storage (trigger_sync returns 503 in production)
- Allowing read operations in production
"""

import os
from pathlib import Path

import pytest
from backend.fastapi.app.routers import answer_engine as answer_engine_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'answer-engine-test-tenant'}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """Create a test client with the answer_engine router."""
    monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
    monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
    monkeypatch.setenv('ENVIRONMENT', 'development')
    monkeypatch.setenv('AI_VISIBILITY_DB_PATH', str(tmp_path / 'answer_engine_test.db'))

    from backend.fastapi.app.persistence import ai_visibility_store

    ai_visibility_store._store = None

    app = FastAPI()
    app.include_router(answer_engine_router.router)
    return TestClient(app, raise_server_exceptions=False)


class TestAnswerEngineRouterDevelopmentMode:
    """Test Answer Engine router behavior in development mode."""

    def test_sync_endpoint_requires_auth_in_development(self, client: TestClient):
        """Verify sync endpoint requires authentication even in development."""
        # Missing headers should fail
        response = client.post('/api/v1/answer-engine/sync/acme')
        assert response.status_code == 401
        assert 'Invalid API key' in response.text or 'unauthorized' in response.text.lower()

    def test_sync_endpoint_accepts_valid_auth_in_development(self, client: TestClient):
        """Verify sync endpoint accepts valid auth in development."""
        response = client.post('/api/v1/answer-engine/sync/acme', headers=H)

        # Should succeed or return valid response (may be 200 for sync start)
        assert response.status_code == 200
        assert response.json()['status'] == 'sync_started'

    def test_insights_endpoint_requires_auth_in_development(self, client: TestClient):
        """Verify get_insights endpoint requires authentication in development."""
        response = client.get('/api/v1/answer-engine/insights/acme')
        assert response.status_code == 401

    def test_insights_endpoint_accepts_valid_auth_in_development(self, client: TestClient):
        """Verify get_insights endpoint accepts valid auth in development."""
        response = client.get('/api/v1/answer-engine/insights/acme', headers=H)

        # Should return empty insights (or similar)
        assert response.status_code == 200


class TestAnswerEngineRouterProductionMode:
    """Test Answer Engine router behavior in production mode."""

    def test_sync_succeeds_in_production_with_durable_store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """Verify sync endpoint succeeds in production when durable store is available."""
        monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
        monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')
        monkeypatch.setenv('AI_VISIBILITY_DB_PATH', str(tmp_path / 'answer_engine_prod_test.db'))

        from backend.fastapi.app.persistence import ai_visibility_store

        ai_visibility_store._store = None

        app = FastAPI()
        app.include_router(answer_engine_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post('/api/v1/answer-engine/sync/acme', headers=H)

        assert response.status_code == 200
        assert response.json().get('status') == 'sync_started'

    def test_sync_still_requires_auth_in_production(self, monkeypatch: pytest.MonkeyPatch):
        """Verify sync endpoint still requires auth in production."""
        monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
        monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')

        app = FastAPI()
        app.include_router(answer_engine_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        # No headers - should fail auth first
        response = client.post('/api/v1/answer-engine/sync/acme')
        assert response.status_code == 401

    def test_insights_read_succeeds_in_production_with_auth(self, monkeypatch: pytest.MonkeyPatch):
        """Verify read operations work in production with auth."""
        monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
        monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')

        app = FastAPI()
        app.include_router(answer_engine_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get('/api/v1/answer-engine/insights/acme', headers=H)

        # Read should succeed
        assert response.status_code == 200

    def test_mentions_read_succeeds_in_production_with_auth(self, monkeypatch: pytest.MonkeyPatch):
        """Verify mentions list endpoint works in production with auth."""
        monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
        monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')

        app = FastAPI()
        app.include_router(answer_engine_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get('/api/v1/answer-engine/insights/acme/mentions', headers=H)

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_status_read_succeeds_in_production_with_auth(self, monkeypatch: pytest.MonkeyPatch):
        """Verify status endpoint works in production with auth."""
        monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
        monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')

        app = FastAPI()
        app.include_router(answer_engine_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get('/api/v1/answer-engine/status/acme', headers=H)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'never_synced'

    def test_timeline_read_succeeds_in_production_with_auth(self, monkeypatch: pytest.MonkeyPatch):
        """Verify timeline endpoint works in production with auth."""
        monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
        monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')

        app = FastAPI()
        app.include_router(answer_engine_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get('/api/v1/answer-engine/analytics/acme/timeline', headers=H)

        assert response.status_code == 200
        data = response.json()
        assert 'timeline' in data

    def test_by_engine_read_succeeds_in_production_with_auth(self, monkeypatch: pytest.MonkeyPatch):
        """Verify by_engine endpoint works in production with auth."""
        monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
        monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')

        app = FastAPI()
        app.include_router(answer_engine_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get('/api/v1/answer-engine/analytics/acme/by-engine', headers=H)

        assert response.status_code == 200
        data = response.json()
        assert 'by_engine' in data

    def test_sentiment_read_succeeds_in_production_with_auth(self, monkeypatch: pytest.MonkeyPatch):
        """Verify sentiment endpoint works in production with auth."""
        monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
        monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')

        app = FastAPI()
        app.include_router(answer_engine_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get('/api/v1/answer-engine/analytics/acme/sentiment', headers=H)

        assert response.status_code == 200
        data = response.json()
        assert 'sentiment' in data
