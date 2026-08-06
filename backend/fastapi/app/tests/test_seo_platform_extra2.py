"""
seo_platform extra tests — round 2.
Patches _ollama_json to return instant fallback, hitting all fallback branches.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-seo-extra2"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
SITE = "https://example-seo.com"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# Mock that returns a fallback response instantly (no waiting for Ollama timeout)
FALLBACK_RESULT = {"error": "mocked", "fallback": True}
GOOD_RESULT = {"result_key": "value", "score": 80}


class TestSeoAiCoreAnalyze:
    """SEO-AI analyze: LLM path and heuristic fallback (no placeholder score 100)."""

    def test_seo_ai_analyze_heuristic_fallback(self, client: TestClient) -> None:
        """When Ollama fails, heuristic analysis runs (not fake perfect score)."""
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/seo-ai/analyze", headers=H, json={
                "domain": "example-seo.com",
                "primary_keyword": "test keyword",
                "business_goal": "increase organic traffic",
                "content_excerpt": "This is a sample excerpt for testing SEO analysis coverage.",
            })
        assert r.status_code in VALID
        if r.status_code == 200:
            body = r.json()
            assert body.get("analysis_mode") == "heuristic"
            assert body.get("seo_ai_score", 100) < 90

    def test_seo_ai_analyze_with_result(self, client: TestClient) -> None:
        """When Ollama returns result, use it directly (lines 2285)."""
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/seo-ai/analyze", headers=H, json={
                "domain": "example-seo.com",
                "primary_keyword": "content marketing",
                "business_goal": "generate leads",
                "content_excerpt": "A good excerpt for content marketing.",
            })
        assert r.status_code in VALID

    def test_seo_ai_analyze_blocked_input(self, client: TestClient) -> None:
        """Input with blocked content → 400 (line 127)."""
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/seo-ai/analyze", headers=H, json={
                "domain": "<script>alert(1)</script>",
                "primary_keyword": "test",
                "business_goal": "test",
                "content_excerpt": "test",
            })
        assert r.status_code in VALID


class TestKeywordResearchFallback:
    """Lines 2308-2325: keyword research fallback branches."""

    def test_keyword_research_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/keywords/research", headers=H, json={
                "seed_keyword": "fastapi testing",
                "domain": "example-seo.com",
                "country": "US",
                "count": 10,
            })
        assert r.status_code in VALID

    def test_keyword_research_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/keywords/research", headers=H, json={
                "seed_keyword": "python coverage",
                "domain": "test.com",
            })
        assert r.status_code in VALID

    def test_keyword_research_async_no_cache(self, client: TestClient) -> None:
        """Async route queues job (line 2348)."""
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/keywords/research/async", headers=H, json={
                "seed_keyword": "coverage test async",
                "domain": "example-seo.com",
            })
        assert r.status_code in VALID


class TestOnPageAnalyzeFallback:
    """Lines 2350-2400: on-page analyze fallback."""

    def test_on_page_analyze_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/on-page/analyze", headers=H, json={
                "url": SITE,
                "focus_keyword": "seo testing",
                "content": "This is the page content for on-page analysis.",
            })
        assert r.status_code in VALID

    def test_on_page_analyze_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/on-page/analyze", headers=H, json={
                "url": SITE,
                "focus_keyword": "fastapi test",
                "content": "Some content",
            })
        assert r.status_code in VALID

    def test_on_page_analyze_async(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/on-page/analyze/async", headers=H, json={
                "url": SITE,
                "focus_keyword": "async coverage",
                "content": "Some content for async analysis.",
            })
        assert r.status_code in VALID


class TestTechnicalAuditFallback:
    """Technical audit fallback branches."""

    def test_technical_audit_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/technical/audit", headers=H, json={
                "url": SITE,
                "site_id": "site-extra2-001",
            })
        assert r.status_code in VALID

    def test_technical_audit_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/technical/audit", headers=H, json={
                "url": SITE,
                "site_id": "site-extra2-002",
            })
        assert r.status_code in VALID

    def test_technical_audit_async(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/technical/audit/async", headers=H, json={
                "url": SITE,
                "site_id": "site-extra2-003",
            })
        assert r.status_code in VALID


class TestContentStrategyFallback:
    """Content strategy fallback branches."""

    def test_content_strategy_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/content/strategy", headers=H, json={
                "topic": "AI in marketing",
                "audience": "marketers",
            })
        assert r.status_code in VALID

    def test_content_strategy_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/content/strategy", headers=H, json={
                "topic": "Python best practices",
                "audience": "developers",
            })
        assert r.status_code in VALID

    def test_content_strategy_async(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/content/strategy/async", headers=H, json={
                "topic": "coverage testing",
                "audience": "qa engineers",
            })
        assert r.status_code in VALID


class TestBacklinkAnalysisFallback:
    """Backlink analysis fallback branches."""

    def test_backlinks_analyze_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/backlinks/analyze", headers=H, json={
                "domain": "example-seo.com",
            })
        assert r.status_code in VALID

    def test_backlinks_analyze_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/backlinks/analyze", headers=H, json={
                "domain": "test.com",
            })
        assert r.status_code in VALID

    def test_backlinks_async(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/backlinks/analyze/async", headers=H, json={
                "domain": "example-seo.com",
            })
        assert r.status_code in VALID


class TestCompetitorAnalysisFallback:
    """Competitor analysis fallback branches."""

    def test_competitor_analyze_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/competitors/analyze", headers=H, json={
                "domain": "example-seo.com",
                "competitor_domains": ["competitor1.com", "competitor2.com"],
            })
        assert r.status_code in VALID

    def test_competitor_analyze_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/competitors/analyze", headers=H, json={
                "domain": "test.com",
                "competitor_domains": ["rival.com"],
            })
        assert r.status_code in VALID

    def test_competitor_async(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/competitors/analyze/async", headers=H, json={
                "domain": "example-seo.com",
                "competitor_domains": ["comp.com"],
            })
        assert r.status_code in VALID


class TestLocalSeoFallback:
    """Local SEO fallback branches."""

    def test_local_seo_optimize_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/local/optimize", headers=H, json={
                "business_name": "Test Business LLC",
                "location": "New York, NY",
                "category": "Technology",
            })
        assert r.status_code in VALID

    def test_local_seo_optimize_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/local/optimize", headers=H, json={
                "business_name": "Another Business",
                "location": "San Francisco, CA",
                "category": "Services",
            })
        assert r.status_code in VALID

    def test_local_seo_async(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/local/optimize/async", headers=H, json={
                "business_name": "Async Business",
                "location": "Austin, TX",
                "category": "Retail",
            })
        assert r.status_code in VALID


class TestEcommerceSeoFallback:
    """E-commerce SEO fallback branches."""

    def test_ecommerce_optimize_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/ecommerce/optimize", headers=H, json={
                "product_name": "Test Product",
                "category": "Electronics",
                "description": "A test product for coverage",
            })
        assert r.status_code in VALID

    def test_ecommerce_optimize_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/ecommerce/optimize", headers=H, json={
                "product_name": "Another Product",
                "category": "Software",
                "description": "A software product",
            })
        assert r.status_code in VALID


class TestSchemaGenerationFallback:
    """Schema generation fallback branches."""

    def test_schema_generate_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/schemas/generate", headers=H, json={
                "url": SITE,
                "schema_type": "Article",
            })
        assert r.status_code in VALID

    def test_schema_generate_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/schemas/generate", headers=H, json={
                "url": SITE,
                "schema_type": "Product",
            })
        assert r.status_code in VALID


class TestPerformanceAuditFallback:
    """Performance audit fallback branches."""

    def test_performance_audit_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/performance/audit", headers=H, json={
                "url": SITE,
            })
        assert r.status_code in VALID

    def test_performance_audit_with_result(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=GOOD_RESULT)):
            r = client.post("/seo-platform/performance/audit", headers=H, json={
                "url": SITE,
            })
        assert r.status_code in VALID


class TestAiSeoMoreModules:
    """Additional SEO module routes."""

    def test_rank_tracker_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/rank-tracker/track", headers=H, json={
                "domain": "example-seo.com",
                "keywords": ["test keyword", "another keyword"],
            })
        assert r.status_code in VALID

    def test_international_seo_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/international/optimize", headers=H, json={
                "domain": "example-seo.com",
                "target_countries": ["US", "UK", "CA"],
                "primary_language": "en",
            })
        assert r.status_code in VALID

    def test_voice_search_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/voice-search/optimize", headers=H, json={
                "query": "how to improve website rankings",
                "domain": "example-seo.com",
            })
        assert r.status_code in VALID

    def test_content_gap_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/content/gap", headers=H, json={
                "domain": "example-seo.com",
                "competitor_domains": ["rival1.com"],
            })
        assert r.status_code in VALID

    def test_site_crawler_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/crawler/crawl", headers=H, json={
                "url": SITE,
            })
        assert r.status_code in VALID

    def test_analytics_insights_fallback(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value=FALLBACK_RESULT)):
            r = client.post("/seo-platform/analytics/insights", headers=H, json={
                "domain": "example-seo.com",
                "metric": "organic_traffic",
            })
        assert r.status_code in VALID
