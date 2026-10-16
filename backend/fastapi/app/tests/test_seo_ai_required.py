"""SEO analyses never return invented results in strict (production) mode."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "seo-strict-tenant"}
CONTENT = "Lightweight trail running shoes for beginners with grip and comfort. " * 10


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEO_STRICT_NO_MOCK", "1")


def test_templated_estimates_are_refused_without_an_ai_model(client: TestClient, strict: None) -> None:
    r = client.post("/seo-platform/llmo/analyze", headers=H, json={"brand": "StrictBrand", "domain": "strict.example"})
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "AI_MODEL_UNAVAILABLE"


def test_link_prospects_are_not_invented(client: TestClient, strict: None) -> None:
    r = client.post("/seo-platform/linkbuilding/analyze", headers=H, json={"domain": "strict.example"})
    assert r.status_code == 503


def test_deterministic_text_analysis_still_works(client: TestClient, strict: None) -> None:
    r = client.post(
        "/seo-platform/on-page/analyze",
        headers=H,
        json={"url": "https://strict.example/shoes", "content": CONTENT, "focus_keyword": "trail running shoes"},
    )
    assert r.status_code == 200
    assert r.json()["word_count"] > 0


def test_responses_carry_no_fabricated_enrichment(client: TestClient) -> None:
    r = client.post(
        "/seo-platform/aeo/optimize",
        headers=H,
        json={"content": CONTENT, "topic": "trail running shoes"},
    )
    assert r.status_code == 200
    body = r.json()
    for invented in ("module_intelligence", "serp_intelligence", "ai_insights", "autonomous_next_steps"):
        assert invented not in body
