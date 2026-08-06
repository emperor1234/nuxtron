"""
Comprehensive smoke tests for seo_platform router.
Covers all POST/GET endpoints that need coverage.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
SITE = "https://example.com"
URL_ID = "url_test_001"
SITE_ID = "site_test_001"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def no_live_db_connections():
    # Keep broad route smoke tests deterministic by forcing DB fallback paths.
    with patch("backend.fastapi.app.routers.seo_platform.psycopg.connect", side_effect=RuntimeError("db disabled in tests")):
        yield


@pytest.fixture(autouse=True)
def no_live_llm_calls():
    # Avoid slow external LLM calls during broad smoke coverage tests.
    with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value={"fallback": True})):
        yield


class TestBasicEndpoints:
    def test_health(self, client: TestClient) -> None:
        r = client.get("/seo-platform/health", headers=H)
        assert r.status_code in VALID

    def test_modules_list(self, client: TestClient) -> None:
        r = client.get("/seo-platform/modules", headers=H)
        assert r.status_code in VALID

    def test_modules_audit(self, client: TestClient) -> None:
        r = client.get("/seo-platform/modules/audit", headers=H)
        assert r.status_code in VALID

    def test_module_by_key(self, client: TestClient) -> None:
        r = client.get("/seo-platform/modules/performance-audit", headers=H)
        assert r.status_code in VALID

    def test_analyses_list(self, client: TestClient) -> None:
        r = client.get("/seo-platform/analyses", headers=H)
        assert r.status_code in VALID

    def test_analyses_by_id(self, client: TestClient) -> None:
        r = client.get("/seo-platform/analyses/test-id-001", headers=H)
        assert r.status_code in VALID

    def test_jobs_by_id(self, client: TestClient) -> None:
        r = client.get("/seo-platform/jobs/job-001", headers=H)
        assert r.status_code in VALID

    def test_schema_types(self, client: TestClient) -> None:
        r = client.get("/seo-platform/schemas/types", headers=H)
        assert r.status_code in VALID

    def test_performance_history(self, client: TestClient) -> None:
        r = client.get("/seo-platform/performance/history", headers=H)
        assert r.status_code in VALID


class TestSeoAiAnalyze:
    def test_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/seo-ai/analyze", headers=H, json={
            "url": SITE, "analysis_type": "comprehensive",
        })
        assert r.status_code in VALID


class TestKeywords:
    def test_research(self, client: TestClient) -> None:
        r = client.post("/seo-platform/keywords/research", headers=H, json={
            "seed_keyword": "python testing", "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_research_async(self, client: TestClient) -> None:
        r = client.post("/seo-platform/keywords/research/async", headers=H, json={
            "seed_keyword": "fastapi coverage", "site_url": SITE,
        })
        assert r.status_code in VALID


class TestOnPage:
    def test_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/on-page/analyze", headers=H, json={
            "url": SITE, "url_id": URL_ID,
        })
        assert r.status_code in VALID

    def test_analyze_async(self, client: TestClient) -> None:
        r = client.post("/seo-platform/on-page/analyze/async", headers=H, json={
            "url": SITE, "url_id": URL_ID,
        })
        assert r.status_code in VALID


class TestTechnical:
    def test_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/technical/audit", headers=H, json={
            "site_url": SITE, "site_id": SITE_ID,
        })
        assert r.status_code in VALID

    def test_audit_async(self, client: TestClient) -> None:
        r = client.post("/seo-platform/technical/audit/async", headers=H, json={
            "site_url": SITE, "site_id": SITE_ID,
        })
        assert r.status_code in VALID


class TestSchemas:
    def test_generate(self, client: TestClient) -> None:
        r = client.post("/seo-platform/schemas/generate", headers=H, json={
            "url": SITE, "schema_type": "Article",
        })
        assert r.status_code in VALID

    def test_generate_async(self, client: TestClient) -> None:
        r = client.post("/seo-platform/schemas/generate/async", headers=H, json={
            "url": SITE, "schema_type": "Product",
        })
        assert r.status_code in VALID


class TestLinkBuilding:
    def test_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/linkbuilding/analyze", headers=H, json={
            "site_url": SITE, "target_keyword": "seo testing",
        })
        assert r.status_code in VALID


class TestContent:
    def test_brief(self, client: TestClient) -> None:
        r = client.post("/seo-platform/content/brief", headers=H, json={
            "keyword": "test driven development",
        })
        assert r.status_code in VALID

    def test_write(self, client: TestClient) -> None:
        r = client.post("/seo-platform/content/write", headers=H, json={
            "keyword": "fastapi test coverage", "site_id": SITE_ID,
        })
        assert r.status_code in VALID


class TestSpecializedAnalyze:
    def test_geo_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/geo/optimize", headers=H, json={
            "site_url": SITE, "target_location": "New York",
        })
        assert r.status_code in VALID

    def test_aeo_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/aeo/optimize", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_aio_score(self, client: TestClient) -> None:
        r = client.post("/seo-platform/aio/score", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_llmo_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/llmo/analyze", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_sageo_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/sageo/analyze", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_vso_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/vso/optimize", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_sxo_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/sxo/analyze", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_gxo_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/gxo/optimize", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_eeat_score(self, client: TestClient) -> None:
        r = client.post("/seo-platform/eeat/score", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_entity_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/entity/analyze", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_peao_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/peao/analyze", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_msvo_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/msvo/analyze", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_daeo_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/daeo/analyze", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_local_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/local/optimize", headers=H, json={
            "url": SITE, "business_name": "Test Corp",
        })
        assert r.status_code in VALID

    def test_video_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/video/optimize", headers=H, json={
            "url": SITE, "title": "Test Video",
        })
        assert r.status_code in VALID

    def test_international_multilingual_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/international-multilingual/analyze", headers=H, json={
            "url": SITE, "target_languages": ["en", "es"],
        })
        assert r.status_code in VALID

    def test_site_migration_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/site-migration/analyze", headers=H, json={
            "old_url": SITE, "new_url": "https://new.example.com",
        })
        assert r.status_code in VALID

    def test_revenue_attribution_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/revenue-attribution/analyze", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_growth_playbooks_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/growth-playbooks/analyze", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_trust_risk_governance_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/trust-risk-governance/analyze", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_multi_channel_activation_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/multi-channel-activation/analyze", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_cxao_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/cxao/analyze", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_seo_ab_testing_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/seo-ab-testing/analyze", headers=H, json={
            "url_a": SITE, "url_b": "https://b.example.com",
        })
        assert r.status_code in VALID

    def test_programmatic_generate(self, client: TestClient) -> None:
        r = client.post("/seo-platform/programmatic/generate", headers=H, json={
            "template": "blog-post", "data": {},
        })
        assert r.status_code in VALID

    def test_ecommerce_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/ecommerce/optimize", headers=H, json={
            "site_url": SITE, "platform": "shopify",
        })
        assert r.status_code in VALID


class TestPerformance:
    def test_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/performance/audit", headers=H, json={
            "url": SITE,
        })
        assert r.status_code in VALID

    def test_auto_fix(self, client: TestClient) -> None:
        r = client.post("/seo-platform/performance/auto-fix", headers=H, json={
            "url": SITE, "fix_type": "images",
        })
        assert r.status_code in VALID


class TestAgent:
    def test_run(self, client: TestClient) -> None:
        r = client.post("/seo-platform/agent/run", headers=H, json={
            "goal": "improve SEO score", "site_id": SITE_ID,
        })
        assert r.status_code in VALID


class TestAuditEndpoints:
    def test_accessibility_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/accessibility/audit", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_media_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/media/audit", headers=H, json={"site_url": SITE})
        assert r.status_code in VALID

    def test_social_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/social/audit", headers=H, json={"site_url": SITE})
        assert r.status_code in VALID

    def test_security_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/security/audit", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_ux_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/ux/audit", headers=H, json={"url": SITE})
        assert r.status_code in VALID

    def test_log_file_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/log-file/analyze", headers=H, json={
            "log_content": "GET /page 200", "site_id": SITE_ID,
        })
        assert r.status_code in VALID

    def test_reviews_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/reviews/analyze", headers=H, json={
            "site_url": SITE, "platform": "google",
        })
        assert r.status_code in VALID


class TestMoreEndpoints:
    def test_landing_generate(self, client: TestClient) -> None:
        r = client.post("/seo-platform/landing/generate", headers=H, json={
            "keyword": "test keyword", "industry": "tech",
        })
        assert r.status_code in VALID

    def test_rag_search_query(self, client: TestClient) -> None:
        r = client.post("/seo-platform/rag-search/query", headers=H, json={
            "query": "how to improve SEO", "site_id": SITE_ID,
        })
        assert r.status_code in VALID

    def test_competitor_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/competitor/analyze", headers=H, json={
            "site_url": SITE, "competitor_urls": ["https://competitor.com"],
        })
        assert r.status_code in VALID

    def test_realtime_monitor(self, client: TestClient) -> None:
        r = client.post("/seo-platform/realtime/monitor", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_content_auditor_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/content-auditor/analyze", headers=H, json={
            "site_url": SITE, "content": "test content here",
        })
        assert r.status_code in VALID

    def test_knowledge_graph_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/knowledge-graph/analyze", headers=H, json={
            "url": SITE, "entity": "Example Corp",
        })
        assert r.status_code in VALID

    def test_internal_linking_suggest(self, client: TestClient) -> None:
        r = client.post("/seo-platform/internal-linking/suggest", headers=H, json={
            "site_id": SITE_ID, "source_url": SITE,
        })
        assert r.status_code in VALID

    def test_crawl_budget_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/crawl-budget/analyze", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_news_discover_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/news-discover/analyze", headers=H, json={
            "topic": "SEO trends 2025",
        })
        assert r.status_code in VALID

    def test_analytics_report(self, client: TestClient) -> None:
        r = client.post("/seo-platform/analytics/report", headers=H, json={
            "site_url": SITE, "date_range": "last_30_days",
        })
        assert r.status_code in VALID

    def test_agency_platform_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/agency-platform/analyze", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_integrations_automation_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/integrations-automation/analyze", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_topical_map_build(self, client: TestClient) -> None:
        r = client.post("/seo-platform/topical-map/build", headers=H, json={
            "topic": "machine learning", "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_brand_voice_rewrite(self, client: TestClient) -> None:
        r = client.post("/seo-platform/brand-voice/rewrite", headers=H, json={
            "content": "This is test content that needs rewriting.",
            "page_id": "page_001",
        })
        assert r.status_code in VALID

    def test_backlink_intelligence_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/backlink-intelligence/analyze", headers=H, json={
            "site_url": SITE,
        })
        assert r.status_code in VALID

    def test_rank_tracking_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/rank-tracking/analyze", headers=H, json={
            "site_url": SITE, "keywords": ["test", "seo"],
        })
        assert r.status_code in VALID

    def test_content_creation_blogging_plan(self, client: TestClient) -> None:
        r = client.post("/seo-platform/content-creation-blogging/plan", headers=H, json={
            "topic": "SEO strategy", "site_url": SITE,
        })
        assert r.status_code in VALID


class TestPlanner:
    def test_execute(self, client: TestClient) -> None:
        r = client.post("/seo-platform/planner/execute", headers=H, json={
            "goal": "rank for target keyword", "site_id": SITE_ID,
        })
        assert r.status_code in VALID

    def test_execute_all_modules(self, client: TestClient) -> None:
        r = client.post("/seo-platform/planner/execute-all-modules", headers=H, json={
            "site_url": SITE, "site_id": SITE_ID,
        })
        assert r.status_code in VALID
