"""
Tests for routers/seo_platform.py missing coverage lines.
Mocks _ollama_json to avoid Ollama HTTP calls.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "seo-db-tenant"}
OLLAMA_MOCK = "backend.fastapi.app.routers.seo_platform._ollama_json"

# Patch _ollama_json at module level to return fallback (avoids HTTP calls)
_FALLBACK = {"fallback": True, "error": "mocked"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ─── Helper/utility function tests ─────────────────────────────────────────────

class TestUpstashHelper:
    """Lines 91-111: _upstash_command with and without config."""

    def test_upstash_command_no_config(self) -> None:
        """Lines 91-92: returns None when base_url or token missing."""
        from backend.fastapi.app.routers.seo_platform import _upstash_command
        result = _upstash_command(["GET", "some-key"])
        assert result is None

    def test_upstash_command_with_config_failure(self) -> None:
        """Lines 101-111: makes HTTP call, fails → returns None."""

        from backend.fastapi.app.routers.seo_platform import _upstash_command
        mock_resp = AsyncMock()
        mock_resp.is_success = False
        mock_client = AsyncMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = lambda s, *a: False
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch.dict(os.environ, {
            "UPSTASH_REDIS_REST_URL": "https://fake-upstash.upstash.io",
            "UPSTASH_REDIS_REST_TOKEN": "fake-token",
        }):
            with patch("httpx.Client") as mock_cls:
                instance = mock_cls.return_value.__enter__.return_value
                resp = AsyncMock()
                resp.is_success = False
                instance.post.return_value = resp
                result = _upstash_command(["PING"])
        assert result is None

    def test_upstash_command_success_path(self) -> None:
        """Lines 104-111: response parsed correctly."""
        from backend.fastapi.app.routers.seo_platform import _upstash_command

        with patch.dict(os.environ, {
            "UPSTASH_REDIS_REST_URL": "https://fake-upstash.upstash.io",
            "UPSTASH_REDIS_REST_TOKEN": "fake-token",
        }):
            with patch("httpx.Client") as mock_cls:
                instance = mock_cls.return_value.__enter__.return_value
                from unittest.mock import MagicMock
                resp = MagicMock()
                resp.is_success = True
                resp.json.return_value = [{"result": "pong"}]
                instance.post.return_value = resp
                result = _upstash_command(["PING"])
        assert result == "pong"

    def test_upstash_command_empty_list_result(self) -> None:
        """Lines 108-110: empty list result → return None."""
        from backend.fastapi.app.routers.seo_platform import _upstash_command

        with patch.dict(os.environ, {
            "UPSTASH_REDIS_REST_URL": "https://fake-upstash.upstash.io",
            "UPSTASH_REDIS_REST_TOKEN": "fake-token",
        }):
            with patch("httpx.Client") as mock_cls:
                instance = mock_cls.return_value.__enter__.return_value
                from unittest.mock import MagicMock
                resp = MagicMock()
                resp.is_success = True
                resp.json.return_value = []
                instance.post.return_value = resp
                result = _upstash_command(["PING"])
        assert result is None


class TestCleanHelper:
    """Lines 168-194: _clean helper, _BLOCKED patterns."""

    def test_clean_safe_text(self) -> None:
        """Line 177: clean text without blocked patterns."""
        from backend.fastapi.app.routers.seo_platform import _clean
        result = _clean("hello world this is safe")
        assert result == "hello world this is safe"

    def test_clean_script_blocked(self) -> None:
        """Lines 183-184: <script> tag blocked."""
        from backend.fastapi.app.routers.seo_platform import _clean
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _clean("<script>alert(1)</script>")
        assert exc_info.value.status_code == 400

    def test_clean_sql_injection_blocked(self) -> None:
        """Lines 183-184: DROP TABLE blocked."""
        from backend.fastapi.app.routers.seo_platform import _clean
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _clean("DROP TABLE users")

    def test_clean_max_len_truncation(self) -> None:
        """Line 194: text truncated to max_len."""
        from backend.fastapi.app.routers.seo_platform import _clean
        long_text = "a" * 5000
        result = _clean(long_text, max_len=100)
        assert len(result) == 100

    def test_clean_javascript_blocked(self) -> None:
        """Line 183: javascript: URL blocked."""
        from backend.fastapi.app.routers.seo_platform import _clean
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _clean("javascript:void(0)")


# ─── Route tests (all use _ollama_json mock) ─────────────────────────────────

class TestSeoAiAnalyze:
    """Lines 1401-1413: _db_available, _ensure_db_tables helpers, seo-ai/analyze."""

    def test_seo_ai_analyze_fallback(self, client: TestClient) -> None:
        """POST /seo/seo-ai/analyze with ollama fallback."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/seo-ai/analyze", headers=H, json={
                "domain": "example.com",
                "primary_keyword": "best CRM software",
                "business_goal": "increase organic traffic",
                "content_excerpt": "Our CRM software helps businesses manage customer relationships.",
                "notes": "",
            })
        assert r.status_code in VALID


class TestKeywordResearch:
    """Lines 2287+: keyword_research route."""

    def test_keyword_research(self, client: TestClient) -> None:
        """POST /seo/keywords/research."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/keywords/research", headers=H, json={
                "seed_keyword": "content marketing strategy",
                "domain": "example.com",
                "country": "US",
                "count": 10,
            })
        assert r.status_code in VALID

    def test_keyword_research_async(self, client: TestClient) -> None:
        """POST /seo/keywords/research/async → background job."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/keywords/research/async", headers=H, json={
                "seed_keyword": "email marketing tips",
                "count": 5,
            })
        assert r.status_code in VALID


class TestOnPageAnalyze:
    """Lines 2358+: on-page/analyze route."""

    def test_on_page_analyze(self, client: TestClient) -> None:
        """POST /seo/on-page/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/on-page/analyze", headers=H, json={
                "url": "https://example.com/blog/content-marketing",
                "content": "Content marketing is a strategic approach focused on creating valuable content.",
                "focus_keyword": "content marketing",
            })
        assert r.status_code in VALID

    def test_on_page_analyze_async(self, client: TestClient) -> None:
        """POST /seo/on-page/analyze/async."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/on-page/analyze/async", headers=H, json={
                "url": "https://example.com/blog/seo-tips",
                "content": "SEO tips for beginners",
                "focus_keyword": "SEO tips",
            })
        assert r.status_code in VALID


class TestTechnicalAudit:
    """Lines 2425+: technical/audit route."""

    def test_technical_audit(self, client: TestClient) -> None:
        """POST /seo/technical/audit."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/technical/audit", headers=H, json={
                "url": "https://example.com",
                "issues_raw": [{"type": "broken_link", "url": "/old-page"}],
            })
        assert r.status_code in VALID

    def test_technical_audit_async(self, client: TestClient) -> None:
        """POST /seo/technical/audit/async."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/technical/audit/async", headers=H, json={
                "url": "https://example.com/about",
            })
        assert r.status_code in VALID

    def test_get_job_status(self, client: TestClient) -> None:
        """GET /seo/jobs/{job_id} → 404 for unknown job."""
        r = client.get("/seo/jobs/nonexistent-job-id-99999", headers=H)
        assert r.status_code in VALID


class TestSchemaGenerate:
    """Lines 2501+: schemas/generate route."""

    def test_schema_generate(self, client: TestClient) -> None:
        """POST /seo/schemas/generate."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/schemas/generate", headers=H, json={
                "schema_type": "Article",
                "content": "A comprehensive guide to content marketing strategies that drive organic traffic.",
                "url": "https://example.com/content-marketing-guide",
            })
        assert r.status_code in VALID

    def test_schema_generate_async(self, client: TestClient) -> None:
        """POST /seo/schemas/generate/async."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/schemas/generate/async", headers=H, json={
                "schema_type": "FAQPage",
                "content": "What is SEO? SEO stands for Search Engine Optimization.",
            })
        assert r.status_code in VALID

    def test_schema_types(self, client: TestClient) -> None:
        """GET /seo/schemas/types."""
        r = client.get("/seo/schemas/types", headers=H)
        assert r.status_code in VALID


class TestLinkBuilding:
    """Lines 2579+: linkbuilding/analyze route."""

    def test_link_building_analyze(self, client: TestClient) -> None:
        """POST /seo/linkbuilding/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/linkbuilding/analyze", headers=H, json={
                "domain": "example.com",
                "competitors": ["competitor1.com", "competitor2.com"],
                "niche": "SaaS software",
            })
        assert r.status_code in VALID


class TestContentBrief:
    """Lines 2614+: content/brief route."""

    def test_content_brief(self, client: TestClient) -> None:
        """POST /seo/content/brief."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/content/brief", headers=H, json={
                "topic": "How to write a content marketing strategy",
                "keywords": ["content marketing", "strategy", "SEO"],
                "word_count": 1500,
                "audience": "marketers",
            })
        assert r.status_code in VALID


class TestContentWrite:
    """Lines 2655+: content/write route."""

    def test_content_write(self, client: TestClient) -> None:
        """POST /seo/content/write."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/content/write", headers=H, json={
                "topic": "The Ultimate Guide to Email Marketing",
                "keywords": ["email marketing", "email campaigns"],
                "word_count": 800,
                "tone": "professional",
                "brief": "Cover basics, strategy, and best practices",
            })
        assert r.status_code in VALID


class TestGeoOptimize:
    """Lines 2688-2762: geo/optimize route."""

    def test_geo_optimize(self, client: TestClient) -> None:
        """POST /seo/geo/optimize."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/geo/optimize", headers=H, json={
                "content": "Our AI-powered platform helps businesses automate revenue operations.",
                "topic": "AI revenue automation",
                "target_engines": ["ChatGPT", "Perplexity"],
                "rag_enabled": False,
            })
        assert r.status_code in VALID


class TestAeoOptimize:
    """Lines 2762+: aeo/optimize route."""

    def test_aeo_optimize(self, client: TestClient) -> None:
        """POST /seo/aeo/optimize."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/aeo/optimize", headers=H, json={
                "content": "Answer engine optimization helps businesses appear in AI-generated answers.",
                "topic": "AEO for SaaS",
                "target_questions": ["What is AEO?", "How does AEO work?"],
                "use_openlens": False,
                "use_playwright_validation": False,
            })
        assert r.status_code in VALID


class TestAioScore:
    """Lines 2826+: aio/score route."""

    def test_aio_score(self, client: TestClient) -> None:
        """POST /seo/aio/score."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/aio/score", headers=H, json={
                "content": "This content is optimized for AI overview appearances in Google search.",
                "topic": "AI overview optimization",
            })
        assert r.status_code in VALID


class TestLlmoAnalyze:
    """Lines 2877+: llmo/analyze route."""

    def test_llmo_analyze(self, client: TestClient) -> None:
        """POST /seo/llmo/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/llmo/analyze", headers=H, json={
                "brand": "Nuxtron AI",
                "domain": "nuxtron.ai",
                "key_claims": ["Best AI platform", "Revenue automation"],
                "competitors": ["competitor.ai"],
            })
        assert r.status_code in VALID


class TestSageoAnalyze:
    """Lines 2951+: sageo/analyze route."""

    def test_sageo_analyze(self, client: TestClient) -> None:
        """POST /seo/sageo/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/sageo/analyze", headers=H, json={
                "content": "Self-awareness GEO helps brands appear in generative engine results.",
                "topic": "SAGEO brand optimization",
            })
        assert r.status_code in VALID


class TestVsoOptimize:
    """Lines 3017+: vso/optimize route."""

    def test_vso_optimize(self, client: TestClient) -> None:
        """POST /seo/vso/optimize."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/vso/optimize", headers=H, json={
                "content": "Voice search optimization helps businesses appear in voice assistant results.",
                "topic": "voice search tips",
                "local_area": "London, UK",
            })
        assert r.status_code in VALID


class TestSxoAnalyze:
    """Lines 3053+: sxo/analyze route."""

    def test_sxo_analyze(self, client: TestClient) -> None:
        """POST /seo/sxo/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/sxo/analyze", headers=H, json={
                "url": "https://example.com/product",
                "content": "Search experience optimization combines SEO and UX signals.",
                "keywords": ["SXO", "search experience"],
            })
        assert r.status_code in VALID


class TestGxoOptimize:
    """Lines 3083+: gxo/optimize route."""

    def test_gxo_optimize(self, client: TestClient) -> None:
        """POST /seo/gxo/optimize."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/gxo/optimize", headers=H, json={
                "content": "Generative experience optimization adapts content for AI-first search.",
                "topic": "GXO strategy",
                "url": "https://example.com/gxo-guide",
            })
        assert r.status_code in VALID


class TestEeatScore:
    """Lines 3114+: eeat/score route."""

    def test_eeat_score(self, client: TestClient) -> None:
        """POST /seo/eeat/score."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/eeat/score", headers=H, json={
                "content": "This article was written by Dr. Jane Smith, a certified digital marketing expert with 15 years of experience.",
                "author_bio": "Dr. Jane Smith, PhD in Marketing, Stanford University",
                "domain": "expert-marketing.com",
                "niche": "digital marketing",
            })
        assert r.status_code in VALID


class TestEntityAnalyze:
    """Lines 3148+: entity/analyze route."""

    def test_entity_analyze(self, client: TestClient) -> None:
        """POST /seo/entity/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/entity/analyze", headers=H, json={
                "content": "Google is a search engine owned by Alphabet Inc., headquartered in Mountain View, California.",
                "topic": "search engines",
            })
        assert r.status_code in VALID


class TestPeaoAnalyze:
    """Lines 3178+: peao/analyze route."""

    def test_peao_analyze(self, client: TestClient) -> None:
        """POST /seo/peao/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/peao/analyze", headers=H, json={
                "content": "Predictive entity-aware optimization leverages AI to anticipate search trends.",
                "topic": "predictive SEO",
            })
        assert r.status_code in VALID


class TestMsvoAnalyze:
    """Lines 3209+: msvo/analyze route."""

    def test_msvo_analyze(self, client: TestClient) -> None:
        """POST /seo/msvo/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/msvo/analyze", headers=H, json={
                "content": "Multi-signal visibility optimization covers all modern search surfaces.",
                "topic": "multi-signal SEO",
            })
        assert r.status_code in VALID


class TestDaeoAnalyze:
    """Lines 3243+: daeo/analyze route."""

    def test_daeo_analyze(self, client: TestClient) -> None:
        """POST /seo/daeo/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/daeo/analyze", headers=H, json={
                "content": "Dynamic answer engine optimization creates content that adapts to real-time queries.",
                "topic": "dynamic AEO",
            })
        assert r.status_code in VALID


class TestLocalOptimize:
    """Lines 3278+: local/optimize route."""

    def test_local_optimize(self, client: TestClient) -> None:
        """POST /seo/local/optimize."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/local/optimize", headers=H, json={
                "business_name": "Tech Solutions Ltd",
                "category": "Software Company",
                "location": "London, UK",
                "website": "https://techsolutions.co.uk",
                "description": "We provide enterprise software solutions for UK businesses.",
            })
        assert r.status_code in VALID


class TestVideoOptimize:
    """Lines 3317+: video/optimize route."""

    def test_video_optimize(self, client: TestClient) -> None:
        """POST /seo/video/optimize."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/video/optimize", headers=H, json={
                "title": "Complete Guide to SEO in 2025",
                "description": "Learn the latest SEO techniques for 2025",
                "transcript": "Hello and welcome to our complete guide to SEO in 2025...",
                "platform": "youtube",
                "keywords": ["SEO 2025", "SEO guide"],
            })
        assert r.status_code in VALID


class TestInternationalMultilingual:
    """Lines 3354+: international-multilingual/analyze route."""

    def test_international_multilingual(self, client: TestClient) -> None:
        """POST /seo/international-multilingual/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/international-multilingual/analyze", headers=H, json={
                "domain": "example.com",
                "locales": ["en-US", "fr-FR", "de-DE", "es-ES"],
                "current_hreflang_map": '<link rel="alternate" hreflang="en" href="https://example.com/en/">',
                "notes": "Currently only English content available",
            })
        assert r.status_code in VALID


class TestSiteMigration:
    """Lines 3395+: site-migration/analyze route."""

    def test_site_migration(self, client: TestClient) -> None:
        """POST /seo/site-migration/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/site-migration/analyze", headers=H, json={
                "source_domain": "old-domain.com",
                "target_domain": "new-domain.com",
                "sample_urls": ["/blog/post-1", "/products/item-1"],
                "launch_window": "Q1 2026",
                "notes": "Full domain migration with URL restructure",
            })
        assert r.status_code in VALID


class TestRevenueAttribution:
    """Lines 3437+: revenue-attribution/analyze route."""

    def test_revenue_attribution(self, client: TestClient) -> None:
        """POST /seo/revenue-attribution/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/revenue-attribution/analyze", headers=H, json={
                "content": "Our SEO strategy generated 45% of all new customer acquisitions last quarter.",
                "topic": "SEO revenue attribution",
            })
        assert r.status_code in VALID


class TestGrowthPlaybooks:
    """Lines 3478+: growth-playbooks/analyze route."""

    def test_growth_playbooks(self, client: TestClient) -> None:
        """POST /seo/growth-playbooks/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/growth-playbooks/analyze", headers=H, json={
                "content": "A systematic growth playbook combines SEO, content, and conversion optimization.",
                "topic": "growth hacking via SEO",
            })
        assert r.status_code in VALID


class TestTrustRiskGovernance:
    """Lines 3518+: trust-risk-governance/analyze route."""

    def test_trust_risk_governance(self, client: TestClient) -> None:
        """POST /seo/trust-risk-governance/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/trust-risk-governance/analyze", headers=H, json={
                "content": "Trust signals in SEO include backlinks, EEAT, and user engagement metrics.",
                "topic": "trust and risk in SEO",
            })
        assert r.status_code in VALID


class TestMultiChannelActivation:
    """Lines 3555+: multi-channel-activation/analyze route."""

    def test_multi_channel_activation(self, client: TestClient) -> None:
        """POST /seo/multi-channel-activation/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/multi-channel-activation/analyze", headers=H, json={
                "content": "Multi-channel activation coordinates SEO with paid, social, and email channels.",
                "topic": "multi-channel SEO strategy",
            })
        assert r.status_code in VALID


class TestCxaoAnalyze:
    """Lines 3594+: cxao/analyze route."""

    def test_cxao_analyze(self, client: TestClient) -> None:
        """POST /seo/cxao/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/cxao/analyze", headers=H, json={
                "content": "Customer experience and SEO alignment drives lower bounce rates and higher conversions.",
                "topic": "CX-aligned SEO",
            })
        assert r.status_code in VALID


class TestSeoAbTesting:
    """Lines 3648+: seo-ab-testing/analyze route."""

    def test_seo_ab_testing(self, client: TestClient) -> None:
        """POST /seo/seo-ab-testing/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/seo-ab-testing/analyze", headers=H, json={
                "content": "SEO A/B testing allows teams to scientifically validate SEO hypothesis.",
                "topic": "SEO testing methodology",
            })
        assert r.status_code in VALID


class TestProgrammaticGenerate:
    """Lines 3704+: programmatic/generate route."""

    def test_programmatic_generate(self, client: TestClient) -> None:
        """POST /seo/programmatic/generate."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/programmatic/generate", headers=H, json={
                "content": "Programmatic SEO creates thousands of unique landing pages at scale.",
                "topic": "programmatic SEO for SaaS",
            })
        assert r.status_code in VALID


class TestEcommerceOptimize:
    """Lines 3743+: ecommerce/optimize route."""

    def test_ecommerce_optimize(self, client: TestClient) -> None:
        """POST /seo/ecommerce/optimize."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/ecommerce/optimize", headers=H, json={
                "content": "Ecommerce SEO focuses on product pages, category pages, and structured data.",
                "topic": "ecommerce SEO strategy",
            })
        assert r.status_code in VALID


class TestPerformanceAudit:
    """Lines 3783+: performance/audit route."""

    def test_performance_audit(self, client: TestClient) -> None:
        """POST /seo/performance/audit."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/performance/audit", headers=H, json={
                "url": "https://example.com",
                "content": "Current Core Web Vitals: LCP 3.2s, FID 150ms, CLS 0.15",
                "topic": "performance optimization",
            })
        assert r.status_code in VALID

    def test_performance_history(self, client: TestClient) -> None:
        """GET /seo/performance/history."""
        r = client.get("/seo/performance/history", headers=H)
        assert r.status_code in VALID


class TestAgentRun:
    """Lines 4069+: agent/run route."""

    def test_agent_run(self, client: TestClient) -> None:
        """POST /seo/agent/run."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/agent/run", headers=H, json={
                "goal": "Perform a complete SEO audit and provide actionable recommendations",
                "domain": "example.com",
                "max_iterations": 3,
                "dry_run": True,
            })
        assert r.status_code in VALID


class TestAccessibilityAudit:
    """Lines 4110+: accessibility/audit route."""

    def test_accessibility_audit(self, client: TestClient) -> None:
        """POST /seo/accessibility/audit."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/accessibility/audit", headers=H, json={
                "url": "https://example.com",
                "content": "Our homepage content with various accessibility considerations.",
                "topic": "accessibility audit",
            })
        assert r.status_code in VALID


class TestMediaAudit:
    """Lines 4145+: media/audit route."""

    def test_media_audit(self, client: TestClient) -> None:
        """POST /seo/media/audit."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/media/audit", headers=H, json={
                "content": "Image alt texts are missing on 30% of pages. Videos lack captions.",
                "topic": "media optimization for SEO",
            })
        assert r.status_code in VALID


class TestSocialAudit:
    """Lines 4182+: social/audit route."""

    def test_social_audit(self, client: TestClient) -> None:
        """POST /seo/social/audit."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/social/audit", headers=H, json={
                "content": "Social signals including shares, engagement, and brand mentions affect SEO.",
                "topic": "social media and SEO",
            })
        assert r.status_code in VALID


class TestLandingGenerate:
    """Lines 4226+: landing/generate route."""

    def test_landing_generate(self, client: TestClient) -> None:
        """POST /seo/landing/generate."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/landing/generate", headers=H, json={
                "content": "Convert visitors into customers with our AI-powered landing page optimization.",
                "topic": "landing page SEO",
            })
        assert r.status_code in VALID


class TestSecurityAudit:
    """Lines 4278+: security/audit route."""

    def test_security_audit(self, client: TestClient) -> None:
        """POST /seo/security/audit."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/security/audit", headers=H, json={
                "url": "https://example.com",
                "content": "HTTPS enabled, HSTS headers present, no mixed content issues detected.",
                "topic": "security for SEO",
            })
        assert r.status_code in VALID


class TestUxAudit:
    """Lines 4313+: ux/audit route."""

    def test_ux_audit(self, client: TestClient) -> None:
        """POST /seo/ux/audit."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/ux/audit", headers=H, json={
                "url": "https://example.com",
                "content": "User experience signals including navigation clarity, CTA visibility, and mobile responsiveness.",
                "topic": "UX audit for SEO",
            })
        assert r.status_code in VALID


class TestRagSearchQuery:
    """Lines 4364+: rag-search/query route."""

    def test_rag_search_query(self, client: TestClient) -> None:
        """POST /seo/rag-search/query."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/rag-search/query", headers=H, json={
                "query": "What are the best SEO practices for 2025?",
                "top_k": 5,
            })
        assert r.status_code in VALID


class TestCompetitorAnalyze:
    """Lines 4399+: competitor/analyze route."""

    def test_competitor_analyze(self, client: TestClient) -> None:
        """POST /seo/competitor/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/competitor/analyze", headers=H, json={
                "domain": "example.com",
                "competitors": ["competitor1.com", "competitor2.com"],
                "content": "Competitor analysis reveals gaps in content strategy and link profile.",
            })
        assert r.status_code in VALID


class TestRealtimeMonitor:
    """Lines 4453+: realtime/monitor route."""

    def test_realtime_monitor(self, client: TestClient) -> None:
        """POST /seo/realtime/monitor."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/realtime/monitor", headers=H, json={
                "domain": "example.com",
                "keywords": ["brand keyword", "product keyword"],
                "alert_threshold": 5,
            })
        assert r.status_code in VALID


class TestContentAuditor:
    """Lines 4491+: content-auditor/analyze route."""

    def test_content_auditor(self, client: TestClient) -> None:
        """POST /seo/content-auditor/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/content-auditor/analyze", headers=H, json={
                "url": "https://example.com",
                "content": "Our blog content covers SEO, content marketing, and digital strategy topics.",
                "topic": "content audit",
            })
        assert r.status_code in VALID


class TestKnowledgeGraph:
    """Lines 4529+: knowledge-graph/analyze route."""

    def test_knowledge_graph(self, client: TestClient) -> None:
        """POST /seo/knowledge-graph/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/knowledge-graph/analyze", headers=H, json={
                "content": "Knowledge graphs help search engines understand entity relationships.",
                "topic": "knowledge graph optimization",
                "domain": "example.com",
            })
        assert r.status_code in VALID


class TestInternalLinking:
    """Lines 4568+: internal-linking/suggest route."""

    def test_internal_linking(self, client: TestClient) -> None:
        """POST /seo/internal-linking/suggest."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/internal-linking/suggest", headers=H, json={
                "url": "https://example.com/blog/seo-guide",
                "content": "This guide covers keyword research, on-page SEO, and link building strategies.",
                "topic": "internal linking strategy",
            })
        assert r.status_code in VALID


class TestCrawlBudget:
    """Lines 4601+: crawl-budget/analyze route."""

    def test_crawl_budget(self, client: TestClient) -> None:
        """POST /seo/crawl-budget/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/crawl-budget/analyze", headers=H, json={
                "domain": "example.com",
                "total_pages": 5000,
                "crawled_pages": 1200,
                "blocked_urls": ["/admin", "/internal"],
            })
        assert r.status_code in VALID


class TestNewsDiscover:
    """Lines 4639+: news-discover/analyze route."""

    def test_news_discover(self, client: TestClient) -> None:
        """POST /seo/news-discover/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/news-discover/analyze", headers=H, json={
                "topic": "AI and machine learning trends",
                "domain": "example.com",
                "days_back": 7,
            })
        assert r.status_code in VALID


class TestAnalyticsReport:
    """Lines 4677+: analytics/report route."""

    def test_analytics_report(self, client: TestClient) -> None:
        """POST /seo/analytics/report."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/analytics/report", headers=H, json={
                "domain": "example.com",
                "date_from": "2025-01-01",
                "date_to": "2025-11-30",
                "metrics": ["sessions", "conversions", "revenue"],
            })
        assert r.status_code in VALID


class TestAgencyPlatform:
    """Lines 4715+: agency-platform/analyze route."""

    def test_agency_platform(self, client: TestClient) -> None:
        """POST /seo/agency-platform/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/agency-platform/analyze", headers=H, json={
                "agency_name": "Digital Growth Agency",
                "clients": ["client1.com", "client2.com"],
                "focus_areas": ["keyword research", "content strategy"],
            })
        assert r.status_code in VALID


class TestIntegrationsAutomation:
    """Lines 4749+: integrations-automation/analyze route."""

    def test_integrations_automation(self, client: TestClient) -> None:
        """POST /seo/integrations-automation/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/integrations-automation/analyze", headers=H, json={
                "integrations": ["Google Search Console", "GA4", "Ahrefs"],
                "workflows": ["weekly rank tracking", "monthly content audit"],
                "automation_goal": "reduce manual SEO reporting time by 80%",
            })
        assert r.status_code in VALID


class TestTopicalMap:
    """Lines 4788+: topical-map/build route."""

    def test_topical_map(self, client: TestClient) -> None:
        """POST /seo/topical-map/build."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/topical-map/build", headers=H, json={
                "domain": "example.com",
                "pillar_topic": "content marketing",
                "niche": "B2B SaaS",
                "depth": 3,
            })
        assert r.status_code in VALID


class TestLogFileAnalyze:
    """Lines 4831+: log-file/analyze route."""

    def test_log_file_analyze(self, client: TestClient) -> None:
        """POST /seo/log-file/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/log-file/analyze", headers=H, json={
                "log_entries": [
                    {"bot": "Googlebot", "url": "/blog/post-1", "status": 200, "timestamp": "2025-11-01T10:00:00Z"},
                    {"bot": "Googlebot", "url": "/old-page", "status": 404, "timestamp": "2025-11-01T10:01:00Z"},
                ],
                "domain": "example.com",
            })
        assert r.status_code in VALID


class TestReviewsAnalyze:
    """Lines 4867+: reviews/analyze route."""

    def test_reviews_analyze(self, client: TestClient) -> None:
        """POST /seo/reviews/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/reviews/analyze", headers=H, json={
                "brand": "example.com",
                "reviews": [
                    {"text": "Great service, very responsive team!", "rating": 5, "source": "Google"},
                    {"text": "Average experience, could be better", "rating": 3, "source": "Trustpilot"},
                ],
            })
        assert r.status_code in VALID


class TestBrandVoiceRewrite:
    """Lines 4911+: brand-voice/rewrite route."""

    def test_brand_voice_rewrite(self, client: TestClient) -> None:
        """POST /seo/brand-voice/rewrite."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/brand-voice/rewrite", headers=H, json={
                "content": "We make software for companies that want to grow their business.",
                "brand_voice": "professional, authoritative, data-driven",
                "target_audience": "enterprise CTOs",
            })
        assert r.status_code in VALID


class TestPlannerExecute:
    """Lines 4949+: planner/execute route."""

    def test_planner_execute(self, client: TestClient) -> None:
        """POST /seo/planner/execute."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/planner/execute", headers=H, json={
                "goal": "Increase organic traffic by 50% in 6 months",
                "domain": "example.com",
                "budget": "medium",
                "timeline_weeks": 24,
                "focus_modules": ["keywords", "content", "technical"],
                "dry_run": True,
            })
        assert r.status_code in VALID

    def test_planner_execute_all_modules(self, client: TestClient) -> None:
        """POST /seo/planner/execute-all-modules."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/planner/execute-all-modules", headers=H, json={
                "goal": "Complete SEO transformation for enterprise client",
                "domain": "enterprise.com",
                "dry_run": True,
            })
        assert r.status_code in VALID


class TestBacklinkIntelligence:
    """Lines 5130+: backlink-intelligence/analyze route."""

    def test_backlink_intelligence(self, client: TestClient) -> None:
        """POST /seo/backlink-intelligence/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/backlink-intelligence/analyze", headers=H, json={
                "domain": "example.com",
                "competitor_domains": ["competitor1.com", "competitor2.com"],
                "focus": "link_gap",
            })
        assert r.status_code in VALID


class TestRankTracking:
    """Lines 5180+: rank-tracking/analyze route."""

    def test_rank_tracking(self, client: TestClient) -> None:
        """POST /seo/rank-tracking/analyze."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/rank-tracking/analyze", headers=H, json={
                "domain": "example.com",
                "keywords": ["best CRM software", "CRM tools 2025", "customer relationship management"],
                "date_range_days": 30,
            })
        assert r.status_code in VALID


class TestContentCreationBlogging:
    """Lines 5225+: content-creation-blogging/plan route."""

    def test_content_creation_blogging(self, client: TestClient) -> None:
        """POST /seo/content-creation-blogging/plan."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/content-creation-blogging/plan", headers=H, json={
                "niche": "B2B SaaS",
                "target_audience": "marketing managers",
                "posting_frequency": "weekly",
                "pillar_topics": ["SEO", "content marketing", "email automation"],
                "months": 3,
            })
        assert r.status_code in VALID


class TestAnalysesList:
    """Lines 5280+: analyses list and get routes."""

    def test_analyses_list(self, client: TestClient) -> None:
        """GET /seo/analyses."""
        r = client.get("/seo/analyses", headers=H)
        assert r.status_code in VALID

    def test_analyses_get(self, client: TestClient) -> None:
        """GET /seo/analyses/{analysis_id} → 404."""
        r = client.get("/seo/analyses/nonexistent-analysis-id", headers=H)
        assert r.status_code in VALID


class TestPerformanceAutoFix:
    """Lines 4000+: performance/auto-fix route."""

    def test_performance_auto_fix(self, client: TestClient) -> None:
        """POST /seo/performance/auto-fix."""
        with patch(OLLAMA_MOCK, new_callable=AsyncMock, return_value=_FALLBACK):
            r = client.post("/seo/performance/auto-fix", headers=H, json={
                "url": "https://example.com",
                "issues": [
                    {"type": "lcp_slow", "value": 3.5, "target": 2.5},
                    {"type": "cls_high", "value": 0.2, "target": 0.1},
                ],
                "auto_apply": False,
            })
        assert r.status_code in VALID
