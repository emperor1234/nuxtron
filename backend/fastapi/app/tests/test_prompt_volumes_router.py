"""Tests for Prompt Volumes router hardening."""

import os
from pathlib import Path

import pytest
from backend.fastapi.app.routers import prompt_volumes as prompt_volumes_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "prompt-volumes-test-tenant"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
    monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AI_VISIBILITY_DB_PATH", str(tmp_path / "prompt_volumes_test.db"))

    from backend.fastapi.app.persistence import ai_visibility_store

    ai_visibility_store._store = None
    prompt_volumes_router.prompt_volumes_collector.volumes.clear()
    prompt_volumes_router.prompt_volumes_collector.history.clear()

    app = FastAPI()
    app.include_router(prompt_volumes_router.router)
    return TestClient(app, raise_server_exceptions=False)


class TestPromptVolumesRouterDevelopmentMode:
    def test_record_prompt_requires_auth_in_development(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/prompt-volumes/record-prompt",
            params={"keyword": "what is acme"},
        )
        assert response.status_code == 401

    def test_record_prompt_accepts_valid_auth_in_development(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/prompt-volumes/record-prompt",
            headers=H,
            params={"keyword": "what is acme", "brand_name": "Acme", "sources": ["ChatGPT"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "recorded"

    def test_analysis_read_succeeds_in_development_with_auth(self, client: TestClient) -> None:
        client.post(
            "/api/v1/prompt-volumes/record-prompt",
            headers=H,
            params={"keyword": "what is acme", "brand_name": "Acme", "sources": ["ChatGPT"]},
        )

        response = client.get("/api/v1/prompt-volumes/analysis", headers=H)
        assert response.status_code == 200
        data = response.json()
        assert data["total_unique_keywords"] >= 1


class TestPromptVolumesRouterProductionMode:
    def test_record_prompt_succeeds_in_production_with_durable_store(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
        monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("AI_VISIBILITY_DB_PATH", str(tmp_path / "prompt_volumes_prod_test.db"))

        from backend.fastapi.app.persistence import ai_visibility_store

        ai_visibility_store._store = None
        prompt_volumes_router.prompt_volumes_collector.volumes.clear()
        prompt_volumes_router.prompt_volumes_collector.history.clear()

        app = FastAPI()
        app.include_router(prompt_volumes_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/v1/prompt-volumes/record-prompt",
            headers=H,
            params={"keyword": "what is acme", "sources": ["ChatGPT"]},
        )
        assert response.status_code == 200
        assert response.json().get("status") == "recorded"

    def test_record_prompt_still_requires_auth_in_production(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
        monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
        monkeypatch.setenv("ENVIRONMENT", "production")

        app = FastAPI()
        app.include_router(prompt_volumes_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/v1/prompt-volumes/record-prompt",
            params={"keyword": "what is acme"},
        )
        assert response.status_code == 401

    def test_analysis_read_succeeds_in_production_with_auth(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
        monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("AI_VISIBILITY_DB_PATH", str(tmp_path / "prompt_volumes_prod_analysis.db"))

        from backend.fastapi.app.persistence import ai_visibility_store

        ai_visibility_store._store = None
        prompt_volumes_router.prompt_volumes_collector.volumes.clear()
        prompt_volumes_router.prompt_volumes_collector.history.clear()

        app = FastAPI()
        app.include_router(prompt_volumes_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/prompt-volumes/analysis", headers=H)
        assert response.status_code == 200
        data = response.json()
        assert data["total_prompt_volume"] == 0

    def test_invalid_keyword_type_returns_400_with_auth_in_production(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
        monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
        monkeypatch.setenv("ENVIRONMENT", "production")

        app = FastAPI()
        app.include_router(prompt_volumes_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/prompt-volumes/by-type/not-a-type", headers=H)
        assert response.status_code == 400
