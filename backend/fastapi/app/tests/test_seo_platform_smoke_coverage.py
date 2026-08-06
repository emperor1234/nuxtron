"""Broad smoke coverage for seo_platform.py endpoints.

These tests keep payloads minimal but valid to execute route bodies and reduce
large uncovered blocks in the SEO platform router.
"""
from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
# Speed up Ollama fallback paths during tests.
os.environ.setdefault("SEO_AI_TIMEOUT", "1")
os.environ.setdefault("OLLAMA_BASE_URL", "http://127.0.0.1:9")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "seo-platform-smoke-tenant"}
OK = (200, 201, 202)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _stub_ollama_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep smoke tests deterministic and fast by bypassing network-bound AI calls.
    async def _fake_ollama_json(*_args: object, **_kwargs: object) -> dict[str, object]:
        await asyncio.sleep(0)
        return {}

    from backend.fastapi.app.routers import seo_platform

    monkeypatch.setattr(seo_platform, "_ollama_json", _fake_ollama_json)


class TestSeoPlatformSmokeCoverage:
    def test_health_and_modules_endpoints(self, client: TestClient) -> None:
        r1 = client.get("/seo-platform/health", headers=H)
        r2 = client.get("/seo-platform/modules", headers=H)
        r3 = client.get("/seo-platform/modules/audit", headers=H)
        r4 = client.get("/seo-platform/modules/unknown_module", headers=H)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200
        assert r4.status_code == 404

    @pytest.mark.parametrize(
        ("path", "payload"),
        [
            ("/seo-platform/seo-ai/analyze", {"domain": "example.com", "primary_keyword": "crm software", "business_goal": "growth", "content_excerpt": "overview"}),
            ("/seo-platform/keywords/research", {"seed_keyword": "crm software", "domain": "example.com", "country": "US", "count": 5}),
            ("/seo-platform/on-page/analyze", {"url": "https://example.com", "focus_keyword": "crm", "content": "crm guide"}),
            ("/seo-platform/technical/audit", {"url": "https://example.com", "issues_raw": []}),
            ("/seo-platform/schemas/generate", {"schema_type": "Article", "content": "Hello world", "url": "https://example.com/post"}),
            ("/seo-platform/linkbuilding/analyze", {"domain": "example.com", "competitors": ["competitor.com"], "niche": "saas"}),
            ("/seo-platform/content/brief", {"topic": "crm software", "keywords": ["crm"], "word_count": 800, "audience": "b2b"}),
            ("/seo-platform/content/write", {"topic": "crm software", "keywords": ["crm"], "word_count": 700, "tone": "professional", "brief": "Write concise."}),
            ("/seo-platform/geo/optimize", {"content": "CRM overview", "topic": "crm", "target_engines": ["ChatGPT"]}),
            ("/seo-platform/aeo/optimize", {"content": "FAQ about CRM", "topic": "crm", "target_questions": ["What is CRM?"]}),
            ("/seo-platform/aio/score", {"content": "CRM article", "topic": "crm"}),
            ("/seo-platform/llmo/analyze", {"brand": "Acme", "domain": "example.com", "key_claims": ["Fast"], "competitors": ["other.com"]}),
            ("/seo-platform/vso/optimize", {"content": "Voice answers", "topic": "crm", "local_area": "Austin"}),
            ("/seo-platform/sxo/analyze", {"url": "https://example.com", "content": "Landing page", "keywords": ["crm"]}),
            ("/seo-platform/gxo/optimize", {"content": "Growth page", "topic": "crm", "url": "https://example.com"}),
            ("/seo-platform/eeat/score", {"content": "Expert advice", "author_bio": "SEO expert", "domain": "example.com", "niche": "saas"}),
            ("/seo-platform/entity/analyze", {"content": "Entity-rich text", "topic": "crm"}),
            ("/seo-platform/local/optimize", {"business_name": "Acme", "category": "Software", "location": "NYC", "website": "https://example.com", "description": "CRM provider"}),
            ("/seo-platform/video/optimize", {"title": "CRM Demo", "description": "Video desc", "transcript": "demo transcript", "platform": "youtube", "keywords": ["crm"]}),
            ("/seo-platform/programmatic/generate", {"template_topic": "City pages", "variable_sets": [{"city": "NYC"}], "page_count": 3}),
            ("/seo-platform/ecommerce/optimize", {"product_name": "CRM Suite", "category": "Software", "description": "All-in-one CRM", "keywords": ["crm"]}),
            ("/seo-platform/performance/audit", {"url": "https://example.com"}),
            ("/seo-platform/accessibility/audit", {"url": "https://example.com", "standard": "WCAG2.1AA"}),
            ("/seo-platform/media/audit", {"url": "https://example.com", "check_compression": True}),
            ("/seo-platform/social/audit", {"url": "https://example.com", "platforms": ["twitter", "linkedin"]}),
            ("/seo-platform/landing/generate", {"product_name": "CRM Suite", "target_keyword": "crm software", "audience": "b2b"}),
            ("/seo-platform/security/audit", {"url": "https://example.com", "check_cloaking": True}),
            ("/seo-platform/ux/audit", {"url": "https://example.com", "page_type": "landing", "traffic_source": "organic"}),
            ("/seo-platform/rag-search/query", {"query": "pricing", "site_domain": "example.com", "content_corpus": "pricing info", "top_k": 3}),
            ("/seo-platform/competitor/analyze", {"domain": "example.com", "competitors": ["other.com"], "target_keyword": "crm"}),
            ("/seo-platform/realtime/monitor", {"domain": "example.com", "tracked_queries": ["crm software"], "lookback_hours": 24}),
            ("/seo-platform/content-auditor/analyze", {"content": "Audit this content", "source_url": "https://example.com/a", "target_model": "gpt-4o"}),
            ("/seo-platform/knowledge-graph/analyze", {"domain": "example.com", "seed_entities": ["Brand", "Product", "Concept"]}),
            ("/seo-platform/internal-linking/suggest", {"page_url": "https://example.com/a", "page_content": "content", "target_urls": ["https://example.com/b"]}),
            ("/seo-platform/crawl-budget/analyze", {"domain": "example.com", "sample_urls": ["https://example.com/a"], "log_snippet": "GET /a 200"}),
            ("/seo-platform/news-discover/analyze", {"domain": "example.com", "recent_headlines": ["Headline"], "focus_topics": ["crm"]}),
            ("/seo-platform/analytics/report", {"goal": "Increase organic traffic", "domain": "example.com", "primary_keyword": "crm", "market": "us"}),
            ("/seo-platform/agency-platform/analyze", {"agency_name": "Acme Agency", "workspaces": ["client-a"], "governance_focus": "standard"}),
            ("/seo-platform/integrations-automation/analyze", {"domain": "example.com", "integrations": ["ga4"], "automation_goals": ["reporting"]}),
            ("/seo-platform/topical-map/build", {"seed_topic": "crm", "domain": "example.com", "depth": 2}),
            ("/seo-platform/log-file/analyze", {"log_snippet": "GET /home 200", "domain": "example.com"}),
            ("/seo-platform/reviews/analyze", {"brand": "Acme", "reviews_text": "Great support", "platforms": ["google"]}),
            ("/seo-platform/brand-voice/rewrite", {"content": "Hello there", "brand_name": "Acme", "tone": "professional"}),
            ("/seo-platform/planner/execute", {"goal": "Increase organic traffic", "domain": "example.com", "primary_keyword": "crm"}),
            ("/seo-platform/backlink-intelligence/analyze", {"domain": "example.com", "competitors": ["other.com"], "target_keywords": ["crm"]}),
            ("/seo-platform/rank-tracking/analyze", {"domain": "example.com", "keywords": ["crm software"], "location": "US"}),
            ("/seo-platform/content-creation-blogging/plan", {"topic": "crm software", "content_pillars": ["guides"], "target_keywords": ["crm"], "publication_frequency": "weekly"}),
        ],
    )
    def test_sync_endpoints_smoke(self, client: TestClient, path: str, payload: dict[str, object]) -> None:
        r = client.post(path, headers=H, json=payload)
        assert r.status_code in OK

    def test_async_job_endpoints(self, client: TestClient) -> None:
        async_calls = [
            ("/seo-platform/keywords/research/async", {"seed_keyword": "crm software", "domain": "example.com", "count": 5}),
            ("/seo-platform/on-page/analyze/async", {"url": "https://example.com", "focus_keyword": "crm", "content": "crm content"}),
            ("/seo-platform/technical/audit/async", {"url": "https://example.com", "issues_raw": []}),
            ("/seo-platform/schemas/generate/async", {"schema_type": "Article", "content": "Hello", "url": "https://example.com/post"}),
        ]

        for path, payload in async_calls:
            r = client.post(path, headers=H, json=payload)
            assert r.status_code in OK
            data = r.json()
            job_id = data.get("job_id")
            if isinstance(job_id, str) and job_id:
                job_r = client.get(f"/seo-platform/jobs/{job_id}", headers=H)
                assert job_r.status_code in OK

        missing = client.get("/seo-platform/jobs/no-such-job", headers=H)
        assert missing.status_code == 404

    def test_planner_execute_all_modules_and_analyses(self, client: TestClient) -> None:
        r = client.post(
            "/seo-platform/planner/execute-all-modules",
            headers=H,
            json={
                "goal": "Increase qualified traffic",
                "domain": "example.com",
                "primary_keyword": "crm",
                "market": "us",
                "include_groups": ["core", "ai"],
            },
        )
        assert r.status_code in OK

        list_r = client.get("/seo-platform/analyses", headers=H)
        assert list_r.status_code == 200

        items = list_r.json().get("analyses", [])
        if items:
            analysis_id = items[0].get("id")
            if analysis_id:
                get_r = client.get(f"/seo-platform/analyses/{analysis_id}", headers=H)
                assert get_r.status_code == 200

        missing_r = client.get("/seo-platform/analyses/not-found", headers=H)
        assert missing_r.status_code == 404
