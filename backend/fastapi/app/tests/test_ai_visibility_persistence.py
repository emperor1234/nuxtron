from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")


def _headers(tenant_id: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": tenant_id,
        "X-API-Key": os.environ.get("FASTAPI_API_KEY", "test-api-key"),
    }


def test_answer_engine_sync_is_durable(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "ai_visibility.db"
    monkeypatch.setenv("AI_VISIBILITY_DB_PATH", str(db_path))

    from backend.fastapi.app.persistence import ai_visibility_store

    ai_visibility_store._store = None

    from backend.fastapi.app.answer_engine.insights import AISearchEngine, AISentiment, BrandMention
    from backend.fastapi.app.main import app
    from backend.fastapi.app.routers import answer_engine as answer_engine_router

    async def _fake_sync(brand_name: str, tenant_id: str = "default") -> list[BrandMention]:
        return [
            BrandMention(
                tenant_id=tenant_id,
                brand_name=brand_name,
                search_engine=AISearchEngine.PERPLEXITY,
                query=f"best {brand_name}",
                answer_text=f"{brand_name} is frequently cited in this category.",
                source_url="https://example.com/research",
                sentiment=AISentiment.POSITIVE,
                confidence=0.91,
            )
        ]

    monkeypatch.setattr(answer_engine_router, "sync_brand_mentions", _fake_sync)

    client = TestClient(app, raise_server_exceptions=False)
    tenant_id = "tenant-otterly"

    r_sync = client.post("/api/v1/answer-engine/sync/nuxtron", headers=_headers(tenant_id))
    assert r_sync.status_code == 200, r_sync.text

    r_insights = client.get("/api/v1/answer-engine/insights/nuxtron", headers=_headers(tenant_id))
    assert r_insights.status_code == 200, r_insights.text
    payload = r_insights.json()
    assert payload["total_mentions_7d"] >= 1

    r_mentions = client.get("/api/v1/answer-engine/insights/nuxtron/mentions", headers=_headers(tenant_id))
    assert r_mentions.status_code == 200, r_mentions.text
    assert len(r_mentions.json()) >= 1

    r_citations = client.get("/api/v1/answer-engine/analytics/nuxtron/citations", headers=_headers(tenant_id))
    assert r_citations.status_code == 200, r_citations.text
    assert r_citations.json()["total_domains"] >= 1


def test_prompt_volumes_analysis_replays_persisted_events(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "prompt_volumes.db"
    monkeypatch.setenv("AI_VISIBILITY_DB_PATH", str(db_path))

    from backend.fastapi.app.persistence import ai_visibility_store

    ai_visibility_store._store = None

    from backend.fastapi.app.main import app
    from backend.fastapi.app.prompt_volumes.core import prompt_volumes_collector

    client = TestClient(app, raise_server_exceptions=False)
    tenant_id = "tenant-prompts"

    r_record_1 = client.post(
        "/api/v1/prompt-volumes/record-prompt",
        headers=_headers(tenant_id),
        params={"keyword": "best ai visibility tracker", "sources": ["ChatGPT", "Perplexity"], "brand_name": "Nuxtron"},
    )
    assert r_record_1.status_code == 200, r_record_1.text

    r_record_2 = client.post(
        "/api/v1/prompt-volumes/record-prompt",
        headers=_headers(tenant_id),
        params={"keyword": "how to improve ai citations", "sources": ["Gemini"], "brand_name": "Nuxtron"},
    )
    assert r_record_2.status_code == 200, r_record_2.text

    # Simulate process-memory loss; analysis must still work from durable store.
    prompt_volumes_collector.volumes.clear()
    prompt_volumes_collector.history.clear()

    r_analysis = client.get(
        "/api/v1/prompt-volumes/analysis",
        headers=_headers(tenant_id),
        params={"days": 7, "top_n": 20},
    )
    assert r_analysis.status_code == 200, r_analysis.text
    analysis = r_analysis.json()
    assert analysis["total_prompt_volume"] >= 2
    assert analysis["total_unique_keywords"] >= 2
