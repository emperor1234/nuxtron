"""
Tests for SEO platform analysis endpoints, Products, Playbooks, Documents,
Tenants, Trust Center, Trends, Media, and Ops routers.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("SUPER_ADMIN_API_KEY", "selftest-super-admin-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}


def _bearer_header(tenant_id: str = "test-tenant", subject: str = "ops-test-user") -> dict[str, str]:
    """Bearer auth for routes under the /ops/siem token-only policy.

    SensitiveRouteTokenMiddleware now covers /ops/siem (previously it only
    matched a bare /siem prefix, which no real route used — see
    production_middleware.py), so SIEM routes reject X-API-Key auth outright.
    """
    import base64
    import hashlib
    import hmac
    import json
    import time

    def b64url(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "roles": ["admin"],
        "iat": now,
        "exp": now + 3600,
        "iss": "test-harness",
        "jti": hashlib.sha256(f"{subject}:{now}".encode()).hexdigest()[:24],
    }
    head = b64url(json.dumps(header, separators=(",", ":")).encode())
    body = b64url(json.dumps(payload, separators=(",", ":")).encode())
    # Resolve the same way deps._resolve_jwt_secret does at verify time,
    # rather than hardcoding "test-api-key" — this stays correct even if an
    # earlier test in the same process has changed JWT_SIGNING_KEY/
    # FASTAPI_API_KEY via os.environ without a fixture that reverts it.
    secret = os.environ.get("JWT_SIGNING_KEY") or os.environ.get("FASTAPI_API_KEY", "test-api-key")
    sig = hmac.new(secret.encode("utf-8"), f"{head}.{body}".encode("ascii"), hashlib.sha256).digest()
    token = f"{head}.{body}.{b64url(sig)}"
    return {"Authorization": f"Bearer {token}"}


SA = {
    "X-API-Key": "selftest-super-admin-key",
    "X-Tenant-Id": "test-tenant",
    "X-Super-Admin-Key": "selftest-super-admin-key",
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def no_live_seo_platform_dependencies():
    # Keep seo_platform endpoint tests deterministic and fast.
    with patch("backend.fastapi.app.routers.seo_platform.psycopg.connect", side_effect=RuntimeError("db disabled in tests")):
        with patch("backend.fastapi.app.routers.seo_platform._ollama_json", new=AsyncMock(return_value={"fallback": True})):
            yield


# ── SEO Platform Analysis Endpoints ──────────────────────────────────────────

class TestSEOAnalyze:
    def test_keyword_research(self, client: TestClient) -> None:
        r = client.post("/seo-platform/keywords/research", headers=H, json={
            "url": "https://example.com",
            "seed_keywords": ["seo tips"],
        })
        assert r.status_code < 500

    def test_on_page_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/on-page/analyze", headers=H, json={
            "url": "https://example.com/blog/post-1",
            "keyword": "seo optimization",
        })
        assert r.status_code < 500

    def test_technical_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/technical/audit", headers=H, json={
            "url": "https://example.com",
        })
        assert r.status_code < 500

    def test_schema_generate(self, client: TestClient) -> None:
        r = client.post("/seo-platform/schemas/generate", headers=H, json={
            "url": "https://example.com/product/widget",
            "schema_type": "Product",
        })
        assert r.status_code < 500

    def test_content_brief(self, client: TestClient) -> None:
        r = client.post("/seo-platform/content/brief", headers=H, json={
            "keyword": "best crm software",
            "target_audience": "small businesses",
        })
        assert r.status_code < 500

    def test_local_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/local/optimize", headers=H, json={
            "business_name": "Test Business",
            "location": "New York, NY",
        })
        assert r.status_code < 500

    def test_eeat_score(self, client: TestClient) -> None:
        r = client.post("/seo-platform/eeat/score", headers=H, json={
            "url": "https://example.com/about",
        })
        assert r.status_code < 500

    def test_link_building(self, client: TestClient) -> None:
        r = client.post("/seo-platform/linkbuilding/analyze", headers=H, json={
            "url": "https://example.com",
            "target_keyword": "seo tools",
        })
        assert r.status_code < 500

    def test_internal_linking(self, client: TestClient) -> None:
        r = client.post("/seo-platform/internal-linking/suggest", headers=H, json={
            "url": "https://example.com/blog/topic",
            "site_pages": [],
        })
        assert r.status_code < 500

    def test_competitor_analyze(self, client: TestClient) -> None:
        r = client.post("/seo-platform/competitor/analyze", headers=H, json={
            "url": "https://example.com",
            "competitor_urls": ["https://competitor.com"],
        })
        assert r.status_code < 500

    def test_performance_audit(self, client: TestClient) -> None:
        r = client.post("/seo-platform/performance/audit", headers=H, json={
            "url": "https://example.com",
        })
        assert r.status_code < 500

    def test_content_auditor(self, client: TestClient) -> None:
        r = client.post("/seo-platform/content-auditor/analyze", headers=H, json={
            "url": "https://example.com",
        })
        assert r.status_code < 500

    def test_aio_score(self, client: TestClient) -> None:
        r = client.post("/seo-platform/aio/score", headers=H, json={
            "content": "This is some content to analyze for AI optimization.",
            "target_keyword": "ai seo",
        })
        assert r.status_code < 500

    def test_geo_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/geo/optimize", headers=H, json={
            "content": "Our business serves customers worldwide.",
            "target_location": "United States",
        })
        assert r.status_code < 500

    def test_aeo_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/aeo/optimize", headers=H, json={
            "question": "What is the best CRM software?",
            "content": "Our CRM is the best because...",
        })
        assert r.status_code < 500

    def test_video_optimize(self, client: TestClient) -> None:
        r = client.post("/seo-platform/video/optimize", headers=H, json={
            "title": "How to Use SEO Tools",
            "description": "In this video we explain SEO tools.",
        })
        assert r.status_code < 500

    def test_seo_health(self, client: TestClient) -> None:
        r = client.get("/seo-platform/health", headers=H)
        assert r.status_code == 200

    def test_schema_types(self, client: TestClient) -> None:
        r = client.get("/seo-platform/schemas/types", headers=H)
        assert r.status_code == 200


# ── Products ──────────────────────────────────────────────────────────────────

class TestProducts:
    def test_list_products(self, client: TestClient) -> None:
        r = client.get("/products", headers=H)
        assert r.status_code == 200

    def test_catalog_stats(self, client: TestClient) -> None:
        r = client.get("/products/catalog/stats", headers=H)
        assert r.status_code == 200

    def test_list_categories(self, client: TestClient) -> None:
        r = client.get("/products/categories", headers=H)
        assert r.status_code == 200

    def test_create_category(self, client: TestClient) -> None:
        r = client.post("/products/categories", headers=H, json={
            "name": "Electronics",
            "slug": "electronics",
        })
        assert r.status_code in {200, 201}

    def test_create_product(self, client: TestClient) -> None:
        r = client.post("/products", headers=H, json={
            "name": "Widget Pro",
            "sku": "WP-001",
            "price": 29.99,
            "currency": "USD",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("product", data)

    def test_get_product(self, client: TestClient) -> None:
        r = client.post("/products", headers=H, json={
            "name": "Gadget",
            "sku": "G-001",
            "price": 9.99,
        })
        pid = r.json().get("id", 1)
        r2 = client.get(f"/products/{pid}", headers=H)
        assert r2.status_code == 200

    def test_update_product(self, client: TestClient) -> None:
        r = client.post("/products", headers=H, json={"name": "Update Me", "sku": "UM-001", "price": 5.0})
        pid = r.json().get("id", 1)
        r2 = client.patch(f"/products/{pid}", headers=H, json={"price": 6.99})
        assert r2.status_code < 500

    def test_delete_product(self, client: TestClient) -> None:
        r = client.post("/products", headers=H, json={"name": "Delete Me", "sku": "DM-001", "price": 1.0})
        pid = r.json().get("id", 1)
        r2 = client.delete(f"/products/{pid}", headers=H)
        assert r2.status_code in {200, 204}


# ── Documents ─────────────────────────────────────────────────────────────────

class TestDocuments:
    def test_list_documents(self, client: TestClient) -> None:
        r = client.get("/documents", headers=H)
        assert r.status_code == 200

    def test_create_document(self, client: TestClient) -> None:
        r = client.post("/documents", headers=H, json={
            "title": "Q1 Report",
            "content": "This is the content of the Q1 report.",
            "document_type": "report",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("document", data)

    def test_get_document(self, client: TestClient) -> None:
        r = client.post("/documents", headers=H, json={
            "title": "Fetch Doc",
            "content": "Fetch this document.",
        })
        did = r.json().get("id", 1)
        r2 = client.get(f"/documents/{did}", headers=H)
        assert r2.status_code == 200

    def test_delete_document(self, client: TestClient) -> None:
        r = client.post("/documents", headers=H, json={
            "title": "Delete Doc",
            "content": "Delete this.",
        })
        did = r.json().get("id", 1)
        r2 = client.delete(f"/documents/{did}", headers=H)
        assert r2.status_code in {200, 204}

    def test_share_document(self, client: TestClient) -> None:
        r = client.post("/documents", headers=H, json={
            "title": "Share Doc",
            "content": "Share this.",
        })
        did = r.json().get("id", 1)
        r2 = client.post(f"/documents/{did}/share", headers=H, json={
            "emails": ["colleague@example.com"],
            "permission": "view",
        })
        assert r2.status_code < 500


# ── Tenants ───────────────────────────────────────────────────────────────────

class TestTenants:
    def test_list_tenants(self, client: TestClient) -> None:
        r = client.get("/tenants", headers=H)
        assert r.status_code == 200

    def test_create_tenant(self, client: TestClient) -> None:
        r = client.post("/tenants", headers=H, json={
            "display_name": "Test Tenant Corp",
            "plan": "starter",
        })
        assert r.status_code in {200, 201, 409}


# ── Trust Center ──────────────────────────────────────────────────────────────

class TestTrustCenter:
    def test_posture(self, client: TestClient) -> None:
        r = client.get("/trust-center/posture", headers=H)
        assert r.status_code == 200

    def test_list_policies(self, client: TestClient) -> None:
        r = client.get("/trust-center/policies", headers=H)
        assert r.status_code == 200

    def test_create_policy(self, client: TestClient) -> None:
        r = client.post("/trust-center/policies", headers=H, json={
            "policy_key": "data_retention",
            "new_value": {"retention_years": 7},
            "change_reason": "Annual policy review update",
        })
        assert r.status_code in {200, 201}

    def test_list_incidents(self, client: TestClient) -> None:
        r = client.get("/trust-center/incidents", headers=H)
        assert r.status_code == 200

    def test_create_incident(self, client: TestClient) -> None:
        r = client.post("/trust-center/incidents", headers=H, json={
            "title": "Data Access Anomaly",
            "severity": "medium",
            "description": "Unusual access pattern detected.",
        })
        assert r.status_code in {200, 201}

    def test_approval_chains(self, client: TestClient) -> None:
        r = client.get("/trust-center/approval-chains", headers=H)
        assert r.status_code == 200

    def test_create_approval_chain(self, client: TestClient) -> None:
        r = client.post("/trust-center/approval-chains", headers=H, json={
            "chain_name": "Security Approval",
            "action_type": "policy_change",
            "steps": [{"approver": "security@example.com", "order": 1}],
        })
        assert r.status_code in {200, 201}

    def test_create_snapshot(self, client: TestClient) -> None:
        r = client.post("/trust-center/snapshots", headers=H, json={
            "label": "Pre-release snapshot",
        })
        assert r.status_code < 500


# ── Trends ────────────────────────────────────────────────────────────────────

class TestTrends:
    def test_signals(self, client: TestClient) -> None:
        r = client.get("/trends/signals", headers=H)
        assert r.status_code == 200

    def test_ingest_signal(self, client: TestClient) -> None:
        r = client.post("/trends/signals/ingest", headers=H, json={
            "topic": "AI Tools",
            "source": "twitter",
            "volume": 1500,
        })
        assert r.status_code < 500

    def test_recommendations(self, client: TestClient) -> None:
        r = client.get("/trends/recommendations", headers=H)
        assert r.status_code in {200, 404}

    def test_select_trend(self, client: TestClient) -> None:
        r = client.post("/trends/select", headers=H, json={
            "topic": "AI-Powered SEO",
            "action": "create_content",
        })
        assert r.status_code < 500

    def test_generate_content(self, client: TestClient) -> None:
        r = client.post("/trends/content/generate", headers=H, json={
            "topic": "Best SEO Practices 2026",
            "format": "blog_post",
        })
        assert r.status_code < 500

    def test_forecast(self, client: TestClient) -> None:
        r = client.get("/trends/forecast", headers=H)
        assert r.status_code == 200

    def test_generate_forecast(self, client: TestClient) -> None:
        r = client.post("/trends/forecast/generate", headers=H, json={
            "topics": ["AI", "SEO"],
            "horizon_days": 30,
        })
        assert r.status_code < 500

    def test_track_performance(self, client: TestClient) -> None:
        r = client.post("/trends/performance/track", headers=H, json={
            "topic": "AI Tools",
            "content_id": "blog-001",
            "views": 1500,
        })
        assert r.status_code < 500

    def test_analytics_dashboard(self, client: TestClient) -> None:
        r = client.get("/trends/analytics/dashboard", headers=H)
        assert r.status_code == 200

    def test_analytics_indicators(self, client: TestClient) -> None:
        r = client.get("/trends/analytics/indicators", headers=H)
        assert r.status_code == 200


# ── Playbooks ─────────────────────────────────────────────────────────────────

class TestPlaybooks:
    def test_list_playbooks(self, client: TestClient) -> None:
        r = client.get("/playbooks", headers=H)
        assert r.status_code == 200

    def test_create_playbook(self, client: TestClient) -> None:
        r = client.post("/playbooks", headers=H, json={
            "name": "Product Launch Playbook",
            "description": "A product launch playbook template",
            "steps": ["create_social_post", "send_email"],
        })
        assert r.status_code in {200, 201}

    def test_run_playbook(self, client: TestClient) -> None:
        r = client.post("/playbooks", headers=H, json={
            "name": "Run Me",
            "description": "Playbook to be run in test",
        })
        pid = r.json().get("playbook_id") or r.json().get("id") or "pb-custom-test"
        r2 = client.post("/playbooks/run", headers=H, json={
            "playbook_id": str(pid),
            "config": {},
        })
        assert r2.status_code < 500

    def test_list_runs(self, client: TestClient) -> None:
        r = client.get("/playbooks/runs/list", headers=H)
        assert r.status_code == 200


# ── Ops Endpoints ─────────────────────────────────────────────────────────────

class TestOpsEndpoints:
    def test_audit_log(self, client: TestClient) -> None:
        r = client.get("/ops/audit-log", headers=H)
        assert r.status_code == 200

    def test_platform_status(self, client: TestClient) -> None:
        r = client.get("/ops/platform/status", headers=H)
        assert r.status_code == 200

    def test_platform_capabilities(self, client: TestClient) -> None:
        r = client.get("/ops/platform/capabilities", headers=H)
        assert r.status_code == 200

    def test_platform_metrics_summary(self, client: TestClient) -> None:
        r = client.get("/ops/platform/metrics-summary", headers=H)
        assert r.status_code == 200

    def test_platform_anti_failure(self, client: TestClient) -> None:
        r = client.get("/ops/platform/anti-failure-status", headers=H)
        assert r.status_code == 200

    def test_growth_suite(self, client: TestClient) -> None:
        r = client.get("/ops/platform/growth-suite", headers=H)
        assert r.status_code == 200

    def test_growth_suite_bootstrap(self, client: TestClient) -> None:
        r = client.post("/ops/platform/growth-suite/bootstrap", headers=H)
        assert r.status_code < 500

    def test_use_case_coverage(self, client: TestClient) -> None:
        r = client.get("/ops/platform/use-case-coverage", headers=H)
        assert r.status_code == 200

    def test_siem_cases(self, client: TestClient) -> None:
        r = client.get("/ops/siem/cases", headers=_bearer_header())
        assert r.status_code == 200

    def test_create_siem_case(self, client: TestClient) -> None:
        r = client.post("/ops/siem/cases", headers=_bearer_header(), json={
            "title": "Suspicious login attempt",
            "severity": "high",
            "description": "Multiple failed login attempts from unusual IP.",
        })
        assert r.status_code in {200, 201}

    def test_siem_vulnerabilities(self, client: TestClient) -> None:
        r = client.get("/ops/siem/vulnerabilities", headers=_bearer_header())
        assert r.status_code == 200

    def test_siem_compliance(self, client: TestClient) -> None:
        r = client.get("/ops/siem/compliance", headers=_bearer_header())
        assert r.status_code == 200

    def test_siem_run_auto_pentest(self, client: TestClient) -> None:
        r = client.post("/ops/siem/auto-pentest/run", headers=H, json={
            "target": "https://staging.example.com",
            "scan_type": "light",
        })
        assert r.status_code < 500

    def test_siem_dead_code_scan(self, client: TestClient) -> None:
        r = client.post("/ops/siem/dead-code/scan", headers=H, json={})
        assert r.status_code < 500

    def test_siem_soar_run(self, client: TestClient) -> None:
        r = client.post("/ops/siem/soar/run", headers=H, json={
            "playbook": "isolate_endpoint",
            "target": "host-123",
        })
        assert r.status_code < 500

    def test_ops_zap_scan(self, client: TestClient) -> None:
        r = client.post("/ops/siem/zap/scan", headers=H, json={
            "target": "https://example.com",
        })
        assert r.status_code < 500

    def test_finance_hub(self, client: TestClient) -> None:
        r = client.get("/ops/finance/hub", headers=H)
        assert r.status_code == 200

    def test_security_api_usage(self, client: TestClient) -> None:
        r = client.get("/ops/security/api-usage", headers=H)
        assert r.status_code == 200
