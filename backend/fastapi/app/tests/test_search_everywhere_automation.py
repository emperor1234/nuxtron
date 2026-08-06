from __future__ import annotations

import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _headers(tenant_id: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": tenant_id,
        "X-API-Key": os.environ.get("FASTAPI_API_KEY", "test-api-key"),
    }


class TestSearchEverywhereAutomation:
    def test_cost_savings_calculator(self, client: TestClient) -> None:
        response = client.post(
            "/search-everywhere/cost-savings-calculator",
            headers=_headers("tenant-search-everywhere"),
            json={
                "sites_count": 20,
                "pages_per_site": 1000,
                "monthly_deployments": 4,
                "manual_minutes_per_page": 1.0,
                "hourly_rate_usd": 100,
                "automation_coverage_pct": 80,
                "tool_monthly_cost_usd": 500,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["output"]["automated_monthly_hours_saved"] > 0
        assert payload["output"]["annual_net_savings_usd"] > payload["output"]["net_monthly_savings_usd"]

    def test_ai_search_impact_calculator(self, client: TestClient) -> None:
        response = client.post(
            "/search-everywhere/ai-search-impact-calculator",
            headers=_headers("tenant-search-everywhere"),
            json={
                "monthly_sessions": 100000,
                "current_ai_visibility_pct": 2,
                "target_ai_visibility_pct": 10,
                "ai_ctr_pct": 15,
                "conversion_rate_pct": 2.5,
                "avg_order_value_usd": 120,
                "gross_margin_pct": 60,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["output"]["incremental_clicks_monthly"] > 0
        assert payload["output"]["incremental_revenue_annual_usd"] >= payload["output"]["incremental_revenue_monthly_usd"]

    def test_vendor_and_readiness_views(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"

        ace_site = client.post(
            "/ai-crawler/sites",
            headers=_headers(tenant_id),
            json={
                "domain": "inventory.example.com",
                "display_name": "Inventory",
                "cms_type": "next_js",
                "js_framework": "next",
                "cloudflare_zone_id": "zone-inventory-1",
            },
        )
        assert ace_site.status_code == 201, ace_site.text

        cms = client.post(
            "/cms/connections",
            headers=_headers(tenant_id),
            json={
                "cms_type": "wordpress",
                "display_name": "Inventory CMS",
                "api_url": "https://inventory.example.com/wp-json",
                "api_key": "wp-inventory-key",
            },
        )
        assert cms.status_code in (200, 201), cms.text

        platform = client.post(
            "/platforms/oauth/twitter/callback",
            headers=_headers(tenant_id),
            json={
                "access_token": "twitter-inventory-token",
                "refresh_token": "twitter-inventory-refresh",
            },
        )
        assert platform.status_code == 200, platform.text

        vendors = client.get("/search-everywhere/vendors", headers=_headers(tenant_id))
        assert vendors.status_code == 200, vendors.text
        vendors_payload = vendors.json()
        assert vendors_payload["status"] == "ok"
        assert vendors_payload["total"] >= 5
        assert isinstance(vendors_payload["vendors"], list)
        assert isinstance(vendors_payload.get("unified_vendor_chart"), list)
        assert "domain_inventory" in vendors_payload
        assert vendors_payload["inventory_summary"]["ai_crawler_enablement"]["sites"] >= 1
        assert vendors_payload["inventory_summary"]["cms"]["connections"] >= 1
        assert vendors_payload["inventory_summary"]["platform_integration"]["accounts_connected"] >= 1
        assert any(item.get("source") == "platform_integration" for item in vendors_payload["unified_vendor_chart"])
        assert any(item.get("source") == "cms" for item in vendors_payload["unified_vendor_chart"])
        assert any(item.get("source") == "ai_crawler_enablement" for item in vendors_payload["unified_vendor_chart"])

        report = client.get("/search-everywhere/vendors/report", headers=_headers(tenant_id))
        assert report.status_code == 200, report.text
        report_payload = report.json()
        assert report_payload["status"] == "ok"
        assert report_payload.get("summary", {}).get("domains", 0) >= 3
        assert isinstance(report_payload.get("domain_chart"), list)
        assert isinstance(report_payload.get("category_chart"), list)
        assert isinstance(report_payload.get("vendor_chart"), list)
        assert isinstance(report_payload.get("export_rows"), list)
        assert any(item.get("domain") == "platform_integration" for item in report_payload.get("domain_chart", []))
        assert any(item.get("source") == "cms" for item in report_payload.get("export_rows", []))

        report_csv = client.get("/search-everywhere/vendors/report?format=csv", headers=_headers(tenant_id))
        assert report_csv.status_code == 200, report_csv.text
        report_csv_payload = report_csv.json()
        assert report_csv_payload["status"] == "ok"
        assert report_csv_payload["format"] == "csv"
        assert report_csv_payload["count"] >= 1
        assert report_csv_payload["filename"].endswith(".csv")
        assert isinstance(report_csv_payload.get("csv"), str)
        assert "source,vendor,category,integration,configured_units,total_units,runtime_dependency" in report_csv_payload["csv"]
        assert '"cms"' in report_csv_payload["csv"]

        report_export_json = client.get("/search-everywhere/vendors/report/export?format=json", headers=_headers(tenant_id))
        assert report_export_json.status_code == 200, report_export_json.text
        report_export_json_payload = report_export_json.json()
        assert report_export_json_payload["status"] == "ok"
        assert report_export_json_payload["format"] == "json"
        assert report_export_json_payload["count"] >= 1
        assert report_export_json_payload["filename"].endswith(".json")
        assert isinstance(report_export_json_payload.get("json"), list)
        assert any(item.get("source") == "cms" for item in report_export_json_payload["json"])

        report_export_csv = client.get("/search-everywhere/vendors/report/export?format=csv", headers=_headers(tenant_id))
        assert report_export_csv.status_code == 200, report_export_csv.text
        report_export_csv_payload = report_export_csv.json()
        assert report_export_csv_payload["status"] == "ok"
        assert report_export_csv_payload["format"] == "csv"
        assert report_export_csv_payload["filename"].endswith(".csv")
        assert isinstance(report_export_csv_payload.get("csv"), str)

        readiness = client.get("/search-everywhere/readiness", headers=_headers(tenant_id))
        assert readiness.status_code == 200, readiness.text
        readiness_payload = readiness.json()
        assert readiness_payload["status"] == "ok"
        assert "grade" in readiness_payload["readiness"]
        assert "configured_pct" in readiness_payload["readiness"]
        assert "inventory_summary" in readiness_payload
        assert readiness_payload.get("cross_domain_inventory", {}).get("domains", 0) >= 3

        parity = client.get("/search-everywhere/semrush/parity-audit", headers=_headers(tenant_id))
        assert parity.status_code == 200, parity.text
        parity_payload = parity.json()
        assert parity_payload["status"] == "ok"
        assert isinstance(parity_payload.get("semrush_parity_chart"), list)
        assert parity_payload.get("summary", {}).get("modules_total", 0) >= 5
        assert parity_payload.get("summary", {}).get("implementation_pct") == 100.0
        assert isinstance(parity_payload.get("vendor_inventory"), list)
        assert any(item.get("vendor") == "Cloudflare" for item in parity_payload.get("vendor_inventory", []))

        airanklab_chart = client.get("/search-everywhere/airanklab/completion-chart", headers=_headers(tenant_id))
        assert airanklab_chart.status_code == 200, airanklab_chart.text
        airanklab_chart_payload = airanklab_chart.json()
        assert airanklab_chart_payload["status"] == "ok"
        assert airanklab_chart_payload.get("summary", {}).get("modules_total", 0) >= 4
        assert airanklab_chart_payload.get("summary", {}).get("implementation_pct") == 100.0
        assert isinstance(airanklab_chart_payload.get("feature_chart"), list)
        assert isinstance(airanklab_chart_payload.get("vendor_parity_chart"), list)
        assert airanklab_chart_payload.get("summary", {}).get("screenshot_features_total") == 31
        assert airanklab_chart_payload.get("summary", {}).get("screenshot_features_implemented") == 31
        assert airanklab_chart_payload.get("summary", {}).get("screenshot_features_implemented_pct") == 100.0
        screenshot_groups = airanklab_chart_payload.get("screenshot_category_groups", [])
        assert isinstance(screenshot_groups, list)
        assert len(screenshot_groups) == 8
        vendor_names = {str(item.get("vendor", "")) for item in airanklab_chart_payload.get("vendor_parity_chart", [])}
        assert {
            "Semrush",
            "Ahrefs",
            "seoClarity",
            "BrightEdge",
            "NoimosAI",
            "Conductor",
            "HubSpot",
            "Surfer SEO",
            "Moz Pro",
        }.issubset(vendor_names)
        assert isinstance(
            airanklab_chart_payload.get("third_party_inventory", {}).get("unified_vendor_chart", []),
            list,
        )

        airanklab_verification = client.get("/search-everywhere/airanklab/verification-report", headers=_headers(tenant_id))
        assert airanklab_verification.status_code == 200, airanklab_verification.text
        airanklab_verification_payload = airanklab_verification.json()
        assert airanklab_verification_payload["status"] == "ok"
        assert "verification" in airanklab_verification_payload
        assert "production_grade_ready" in airanklab_verification_payload["verification"]
        assert isinstance(airanklab_verification_payload.get("feature_chart"), list)

    def test_semrush_full_automation(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com", "moz.com"],
                "location": "United States",
                "language": "en",
                "max_results": 12,
                "require_live_providers": False,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "results" in payload
        assert "keyword_discovery" in payload["results"]
        assert "content_gap" in payload["results"]
        assert "backlink_audit" in payload["results"]
        assert "backlink_gap" in payload["results"]
        assert "parity_summary" in payload["results"]

    def test_semrush_full_automation_strict_live_failure(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.fastapi.app.routers import rank_tracker

        def strict_fail_discover(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise HTTPException(status_code=412, detail={"code": "live_provider_required", "message": "No live providers"})

        monkeypatch.setattr(rank_tracker, "keyword_research_discover", strict_fail_discover)

        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com"],
                "require_live_providers": True,
            },
        )
        assert response.status_code == 412
        assert response.json()["detail"]["code"] == "live_provider_required"

    def test_semrush_provider_checklist(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.get(
            "/search-everywhere/semrush/provider-checklist",
            headers=_headers(tenant_id),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "configured" in payload
        assert "total" in payload
        assert "configured_pct" in payload
        assert isinstance(payload.get("checklist"), list)
        assert any(item.get("provider") == "DataForSEO" for item in payload.get("checklist", []))

    def test_hubspot_full_e2e_audit(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        tenant_id = "tenant-hubspot-full-audit"

        for key, value in {
            "DATAFORSEO_LOGIN": "hubspot-dfs-user",
            "DATAFORSEO_API_KEY": "hubspot-dfs-key",
            "SERPER_API_KEY": "hubspot-serper-key",
            "GOOGLE_ADS_DEVELOPER_TOKEN": "hubspot-ads-dev",
            "GOOGLE_ADS_CUSTOMER_ID": "hubspot-ads-customer",
            "GOOGLE_OAUTH_ACCESS_TOKEN": "hubspot-google-oauth",
            "GSC_SITE_URL": "https://example-hubspot.com",
            "CLOUDFLARE_API_TOKEN": "hubspot-cloudflare",
            "SSR_PROXY_URL": "https://proxy.hubspot.example",
            "POSTHOG_HOST": "https://app.posthog.com",
            "POSTHOG_API_KEY": "hubspot-posthog",
            "SENTRY_DSN": "https://hubspot@sentry.example.com/1",
            "UPSTASH_REDIS_REST_URL": "https://upstash.hubspot.example",
            "UPSTASH_REDIS_REST_TOKEN": "hubspot-upstash-token",
        }.items():
            monkeypatch.setenv(key, value)

        response = client.get(
            "/search-everywhere/hubspot/full-e2e-audit",
            headers=_headers(tenant_id),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"

        summary = payload.get("summary", {})
        assert summary.get("products_total", 0) >= 10
        assert summary.get("required_routes_total", 0) >= 10
        assert summary.get("required_routes_implemented") == summary.get("required_routes_total")
        assert summary.get("implementation_pct") == 100.0
        assert summary.get("providers_total", 0) >= 9
        assert summary.get("providers_configured") == summary.get("providers_total")
        assert summary.get("integration_configured_pct") == 100.0
        assert summary.get("production_grade_ready") is True

        assert isinstance(payload.get("product_chart"), list)
        assert isinstance(payload.get("route_contract_chart"), list)
        assert isinstance(payload.get("provider_checklist"), list)
        assert isinstance(payload.get("third_party_vendor_chart"), list)
        assert isinstance(payload.get("how_it_works"), list)
        assert len(payload.get("how_it_works", [])) >= 4

        route_chart = payload.get("route_contract_chart", [])
        marketing_hub = next((item for item in route_chart if item.get("product_key") == "marketing-hub"), None)
        content_hub = next((item for item in route_chart if item.get("product_key") == "content-hub"), None)
        data_hub = next((item for item in route_chart if item.get("product_key") == "data-hub"), None)
        assert marketing_hub is not None
        assert content_hub is not None
        assert data_hub is not None
        assert marketing_hub.get("required_routes_total", 0) >= 1
        assert marketing_hub.get("required_routes_implemented", 0) >= 1
        assert not content_hub.get("missing_routes")
        assert not data_hub.get("missing_routes")

        boundaries = payload.get("validation_boundaries", {})
        assert isinstance(boundaries.get("validated_slice"), dict)
        assert isinstance(boundaries.get("not_validated"), list)

    def test_hubspot_operational_crm_service_commerce_routes(self, client: TestClient) -> None:
        tenant_id = "tenant-hubspot-operations"

        ticket = client.post(
            "/search-everywhere/hubspot/service/tickets",
            headers=_headers(tenant_id),
            json={"title": "Support issue", "priority": "high", "channel": "chat"},
        )
        assert ticket.status_code == 200, ticket.text

        article = client.post(
            "/search-everywhere/hubspot/service/knowledge-base/articles",
            headers=_headers(tenant_id),
            json={"title": "Setup Guide", "slug": "setup-guide", "status": "published"},
        )
        assert article.status_code == 200, article.text

        survey = client.post(
            "/search-everywhere/hubspot/service/surveys",
            headers=_headers(tenant_id),
            json={"name": "NPS Q2", "type": "nps", "audience": "active-customers"},
        )
        assert survey.status_code == 200, survey.text

        product = client.post(
            "/search-everywhere/hubspot/commerce/products",
            headers=_headers(tenant_id),
            json={"name": "Pro Plan", "sku": "PRO-001", "price": 99},
        )
        assert product.status_code == 200, product.text

        document = client.post(
            "/search-everywhere/hubspot/commerce/documents",
            headers=_headers(tenant_id),
            json={"name": "Quote #2026-001", "type": "quote", "amount": 990},
        )
        assert document.status_code == 200, document.text

        contact = client.post(
            "/search-everywhere/hubspot/crm/contacts",
            headers=_headers(tenant_id),
            json={"first_name": "Ravi", "last_name": "K", "email": "ravi@example.com"},
        )
        assert contact.status_code == 200, contact.text

        company = client.post(
            "/search-everywhere/hubspot/crm/companies",
            headers=_headers(tenant_id),
            json={"name": "Nuxtron", "domain": "nuxtron.ai"},
        )
        assert company.status_code == 200, company.text

        deal = client.post(
            "/search-everywhere/hubspot/crm/deals",
            headers=_headers(tenant_id),
            json={"name": "Enterprise Renewal", "amount": 25000, "stage": "proposal"},
        )
        assert deal.status_code == 200, deal.text

        landing_page = client.post(
            "/search-everywhere/hubspot/content/landing-pages",
            headers=_headers(tenant_id),
            json={"title": "Q3 Campaign", "slug": "q3-campaign", "status": "published"},
        )
        assert landing_page.status_code == 200, landing_page.text

        blog_post = client.post(
            "/search-everywhere/hubspot/content/blog-posts",
            headers=_headers(tenant_id),
            json={"title": "Revenue Ops Blueprint", "slug": "revenue-ops-blueprint", "status": "draft"},
        )
        assert blog_post.status_code == 200, blog_post.text

        podcast = client.post(
            "/search-everywhere/hubspot/content/podcasts",
            headers=_headers(tenant_id),
            json={"title": "Growth Weekly", "episode": 12, "status": "scheduled"},
        )
        assert podcast.status_code == 200, podcast.text

        sync_job = client.post(
            "/search-everywhere/hubspot/data/sync-jobs",
            headers=_headers(tenant_id),
            json={"source": "Salesforce", "target": "HubSpot", "mode": "bidirectional"},
        )
        assert sync_job.status_code == 200, sync_job.text

        quality_rule = client.post(
            "/search-everywhere/hubspot/data/quality-rules",
            headers=_headers(tenant_id),
            json={"name": "email-normalization", "field": "email", "action": "normalize"},
        )
        assert quality_rule.status_code == 200, quality_rule.text

        tickets = client.get("/search-everywhere/hubspot/service/tickets", headers=_headers(tenant_id))
        assert tickets.status_code == 200, tickets.text
        assert tickets.json().get("count", 0) >= 1

        articles = client.get("/search-everywhere/hubspot/service/knowledge-base/articles", headers=_headers(tenant_id))
        assert articles.status_code == 200, articles.text
        assert articles.json().get("count", 0) >= 1

        surveys = client.get("/search-everywhere/hubspot/service/surveys", headers=_headers(tenant_id))
        assert surveys.status_code == 200, surveys.text
        assert surveys.json().get("count", 0) >= 1

        products = client.get("/search-everywhere/hubspot/commerce/products", headers=_headers(tenant_id))
        assert products.status_code == 200, products.text
        assert products.json().get("count", 0) >= 1

        documents = client.get("/search-everywhere/hubspot/commerce/documents", headers=_headers(tenant_id))
        assert documents.status_code == 200, documents.text
        assert documents.json().get("count", 0) >= 1

        contacts = client.get("/search-everywhere/hubspot/crm/contacts", headers=_headers(tenant_id))
        assert contacts.status_code == 200, contacts.text
        assert contacts.json().get("count", 0) >= 1

        companies = client.get("/search-everywhere/hubspot/crm/companies", headers=_headers(tenant_id))
        assert companies.status_code == 200, companies.text
        assert companies.json().get("count", 0) >= 1

        deals = client.get("/search-everywhere/hubspot/crm/deals", headers=_headers(tenant_id))
        assert deals.status_code == 200, deals.text
        assert deals.json().get("count", 0) >= 1

        landing_pages = client.get("/search-everywhere/hubspot/content/landing-pages", headers=_headers(tenant_id))
        assert landing_pages.status_code == 200, landing_pages.text
        assert landing_pages.json().get("count", 0) >= 1

        blog_posts = client.get("/search-everywhere/hubspot/content/blog-posts", headers=_headers(tenant_id))
        assert blog_posts.status_code == 200, blog_posts.text
        assert blog_posts.json().get("count", 0) >= 1

        podcasts = client.get("/search-everywhere/hubspot/content/podcasts", headers=_headers(tenant_id))
        assert podcasts.status_code == 200, podcasts.text
        assert podcasts.json().get("count", 0) >= 1

        sync_jobs = client.get("/search-everywhere/hubspot/data/sync-jobs", headers=_headers(tenant_id))
        assert sync_jobs.status_code == 200, sync_jobs.text
        assert sync_jobs.json().get("count", 0) >= 1

        quality_rules = client.get("/search-everywhere/hubspot/data/quality-rules", headers=_headers(tenant_id))
        assert quality_rules.status_code == 200, quality_rules.text
        assert quality_rules.json().get("count", 0) >= 1

    def test_hubspot_wiring_contract_and_apply(self, client: TestClient) -> None:
        tenant_id = "tenant-hubspot-wiring"

        contract = client.get(
            "/search-everywhere/hubspot/wiring/required-keys",
            headers=_headers(tenant_id),
        )
        assert contract.status_code == 200, contract.text
        contract_payload = contract.json()
        assert contract_payload["status"] == "ok"
        wiring_contract = contract_payload.get("wiring_contract", {})
        assert isinstance(wiring_contract.get("required_keys"), list)
        assert isinstance(wiring_contract.get("allowlist"), list)
        assert "DATAFORSEO_LOGIN" in wiring_contract.get("allowlist", [])

        apply_response = client.post(
            "/search-everywhere/hubspot/wiring/apply",
            headers=_headers(tenant_id),
            json={
                "providers": ["DataForSEO", "Serper.dev", "Cloudflare"],
                "values": {
                    "DATAFORSEO_LOGIN": "hubspot-dfs-user",
                    "DATAFORSEO_API_KEY": "hubspot-dfs-key",
                    "SERPER_API_KEY": "hubspot-serper-key",
                    "GOOGLE_ADS_DEVELOPER_TOKEN": "hubspot-ads-dev",
                    "GOOGLE_ADS_CUSTOMER_ID": "hubspot-ads-customer",
                    "GOOGLE_OAUTH_ACCESS_TOKEN": "hubspot-google-oauth",
                    "GSC_SITE_URL": "https://example-hubspot.com",
                    "CLOUDFLARE_API_TOKEN": "hubspot-cloudflare",
                    "SSR_PROXY_URL": "https://proxy.hubspot.example",
                    "POSTHOG_HOST": "https://app.posthog.com",
                    "POSTHOG_API_KEY": "hubspot-posthog",
                    "SENTRY_DSN": "https://hubspot@sentry.example.com/1",
                    "UPSTASH_REDIS_REST_URL": "https://upstash.hubspot.example",
                    "UPSTASH_REDIS_REST_TOKEN": "hubspot-upstash-token",
                    "UNSUPPORTED_KEY": "should-be-rejected",
                },
            },
        )
        assert apply_response.status_code == 200, apply_response.text
        apply_payload = apply_response.json()
        assert apply_payload["status"] == "ok"
        assert "DATAFORSEO_LOGIN" in apply_payload.get("applied", {}).get("keys_applied", [])
        assert "UNSUPPORTED_KEY" in apply_payload.get("applied", {}).get("keys_rejected", [])
        assert apply_payload.get("checklist_summary", {}).get("configured") == apply_payload.get("checklist_summary", {}).get("total")
        assert apply_payload.get("completion_summary", {}).get("integration_configured_pct") == 100.0

    def test_airanklab_wiring_apply_and_verification(self, client: TestClient) -> None:
        tenant_id = "tenant-airanklab-wiring"

        required_keys_response = client.get(
            "/search-everywhere/airanklab/wiring/required-keys",
            headers=_headers(tenant_id),
        )
        assert required_keys_response.status_code == 200, required_keys_response.text
        required_keys_payload = required_keys_response.json()
        assert required_keys_payload["status"] == "ok"
        assert "wiring_contract" in required_keys_payload
        assert isinstance(required_keys_payload["wiring_contract"].get("required_keys", []), list)

        apply_payload = {
            "values": {
                "DATAFORSEO_LOGIN": "wire-user",
                "DATAFORSEO_API_KEY": "wire-key",
                "SERPER_API_KEY": "wire-serper",
                "GOOGLE_ADS_DEVELOPER_TOKEN": "wire-google-ads-dev",
                "GOOGLE_ADS_CUSTOMER_ID": "wire-google-ads-customer",
                "GOOGLE_OAUTH_ACCESS_TOKEN": "wire-google-oauth",
                "GSC_SITE_URL": "https://nuxtron.example.com",
                "CLOUDFLARE_API_TOKEN": "wire-cloudflare",
                "SSR_PROXY_URL": "https://proxy.nuxtron.example.com",
                "POSTHOG_HOST": "https://app.posthog.com",
                "POSTHOG_API_KEY": "wire-posthog",
                "SENTRY_DSN": "https://wire@sentry.example.com/1",
                "UPSTASH_REDIS_REST_URL": "https://upstash.example.com",
                "UPSTASH_REDIS_REST_TOKEN": "wire-upstash",
                "AHREFS_API_TOKEN": "wire-ahrefs",
                "OPENAI_API_KEY": "wire-openai",
                "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
                "WORDPRESS_SITE_URL": "https://cms.nuxtron.example.com",
                "WORDPRESS_APP_PASSWORD": "wire-wp-password",
                "CONTENTFUL_SPACE_ID": "wire-contentful-space",
                "CONTENTFUL_ACCESS_TOKEN": "wire-contentful-token",
                "ZAPIER_WEBHOOK_URL": "https://hooks.zapier.com/hooks/catch/wire",
            }
        }

        apply_response = client.post(
            "/search-everywhere/airanklab/wiring/apply",
            headers=_headers(tenant_id),
            json=apply_payload,
        )
        assert apply_response.status_code == 200, apply_response.text
        apply_result = apply_response.json()
        assert apply_result["status"] == "ok"
        assert len(apply_result.get("applied_keys", [])) >= 20

        verification_response = client.get(
            "/search-everywhere/airanklab/verification-report",
            headers=_headers(tenant_id),
        )
        assert verification_response.status_code == 200, verification_response.text
        verification_payload = verification_response.json()
        assert verification_payload["status"] == "ok"
        verification = verification_payload.get("verification", {})
        assert verification.get("implementation_pct") == 100.0
        assert verification.get("integration_configured_pct") == 100.0
        assert verification.get("parity_vendor_avg_implementation_pct") == 100.0
        assert verification.get("parity_vendor_avg_integration_pct") == 100.0
        assert verification.get("production_grade_ready") is True

    def test_semrush_production_gate(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/production-gate",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com"],
                "max_results": 10,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "gate" in payload
        assert "parity_summary" in payload
        assert "strict_live_probe" in payload
        assert "provider_checklist_summary" in payload
        assert payload["strict_live_probe"]["status"] in ("passed", "failed")

    def test_semrush_provider_bootstrap_all_missing(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/provider-bootstrap",
            headers=_headers(tenant_id),
            json={"providers": [], "include_configured": False},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "steps_total" in payload
        assert isinstance(payload.get("steps"), list)
        if payload["steps"]:
            first = payload["steps"][0]
            assert "provider" in first
            assert "required_missing" in first
            assert "verify_with" in first

    def test_semrush_provider_bootstrap_filtered(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/provider-bootstrap",
            headers=_headers(tenant_id),
            json={"providers": ["DataForSEO"], "include_configured": True},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert isinstance(payload.get("requested_providers"), list)
        assert "dataforseo" in payload.get("requested_providers", [])
        for step in payload.get("steps", []):
            assert step.get("provider", "").lower() == "dataforseo"

    def test_semrush_provider_probes_skips_unconfigured(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/provider-probes",
            headers=_headers(tenant_id),
            json={"providers": [], "include_unconfigured": False, "max_results": 3},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "summary" in payload
        assert isinstance(payload.get("probes"), list)
        assert payload["summary"]["providers_requested"] >= 1
        if payload["probes"]:
            assert payload["probes"][0]["status"] in ("skipped", "failed", "passed")

    def test_semrush_provider_probes_force_success(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.fastapi.app.routers import rank_tracker

        def fake_fetch_provider_keywords(*_args: object, **_kwargs: object) -> dict[str, object]:
            return {"keywords": ["alpha", "beta"], "cache_hit": False}

        monkeypatch.setattr(rank_tracker, "_fetch_provider_keywords", fake_fetch_provider_keywords)

        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/provider-probes",
            headers=_headers(tenant_id),
            json={"providers": ["serper"], "include_unconfigured": True, "max_results": 3},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["summary"]["providers_requested"] == 1
        assert payload["summary"]["passed"] == 1
        assert payload["summary"]["strict_live_ready"] is True

    def test_semrush_env_template_default(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/env-template",
            headers=_headers(tenant_id),
            json={"include_optional": False, "include_configured": False},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "env_template" in payload
        assert isinstance(payload.get("missing_keys"), list)
        assert payload["filename"].endswith(".env")

    def test_semrush_env_template_include_configured(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/semrush/env-template",
            headers=_headers(tenant_id),
            json={"include_optional": True, "include_configured": True},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert isinstance(payload.get("providers_included"), list)
        assert "DataForSEO" in payload.get("providers_included", [])

    def test_ahrefs_parity_and_full_automation(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        parity = client.get("/search-everywhere/ahrefs/parity-audit", headers=_headers(tenant_id))
        assert parity.status_code == 200, parity.text
        parity_payload = parity.json()
        assert parity_payload["status"] == "ok"
        assert isinstance(parity_payload.get("ahrefs_parity_chart"), list)
        assert isinstance(parity_payload.get("ahrefs_core_tools"), list)
        assert parity_payload.get("summary", {}).get("modules_total", 0) >= 6
        assert parity_payload.get("summary", {}).get("implementation_pct") == 100.0
        assert parity_payload.get("summary", {}).get("core_tools_total", 0) >= 15
        assert parity_payload.get("summary", {}).get("core_tools_average_coverage_pct", 0.0) >= 99.9
        assert parity_payload.get("completion_chart", {}).get("core_tools", {}).get("pct", 0.0) >= 99.9
        assert isinstance(parity_payload.get("vendor_inventory"), list)
        assert any(item.get("vendor") == "Ahrefs API" for item in parity_payload.get("vendor_inventory", []))

        verification = client.get("/search-everywhere/ahrefs/e2e-verification", headers=_headers(tenant_id))
        assert verification.status_code == 200, verification.text
        verification_payload = verification.json()
        assert verification_payload["status"] == "ok"
        assert verification_payload.get("framework") == "ahrefs"
        assert "GET /search-everywhere/ahrefs/e2e-verification" in verification_payload.get("automation_endpoints", [])
        assert verification_payload.get("parity", {}).get("summary", {}).get("core_tools_average_coverage_pct", 0.0) >= 99.9

        response = client.post(
            "/search-everywhere/ahrefs/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "seo analytics",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "moz.com", "ahrefs.com"],
                "location": "United States",
                "language": "en",
                "max_results": 12,
                "require_live_providers": False,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload.get("framework") == "ahrefs"
        assert "results" in payload
        assert "rank_tracking" in payload["results"]
        assert "backlink_overview" in payload["results"]
        assert "how_it_works" in payload
        assert len(payload["how_it_works"]) >= 4

    def test_ahrefs_provider_ops(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.fastapi.app.routers import rank_tracker

        def fake_fetch_provider_keywords(*_args: object, **_kwargs: object) -> dict[str, object]:
            return {"keywords": ["alpha", "beta"], "cache_hit": False}

        monkeypatch.setattr(rank_tracker, "_fetch_provider_keywords", fake_fetch_provider_keywords)

        tenant_id = "tenant-search-everywhere"
        checklist = client.get("/search-everywhere/ahrefs/provider-checklist", headers=_headers(tenant_id))
        assert checklist.status_code == 200, checklist.text
        checklist_payload = checklist.json()
        assert checklist_payload["status"] == "ok"
        assert isinstance(checklist_payload.get("checklist"), list)
        assert any(item.get("provider") == "Ahrefs API" for item in checklist_payload.get("checklist", []))

        bootstrap = client.post(
            "/search-everywhere/ahrefs/provider-bootstrap",
            headers=_headers(tenant_id),
            json={"providers": ["DataForSEO"], "include_configured": True},
        )
        assert bootstrap.status_code == 200, bootstrap.text
        bootstrap_payload = bootstrap.json()
        assert bootstrap_payload["status"] == "ok"
        assert isinstance(bootstrap_payload.get("steps"), list)

        probes = client.post(
            "/search-everywhere/ahrefs/provider-probes",
            headers=_headers(tenant_id),
            json={"providers": ["serper"], "include_unconfigured": True, "max_results": 3},
        )
        assert probes.status_code == 200, probes.text
        probes_payload = probes.json()
        assert probes_payload["status"] == "ok"
        assert probes_payload["summary"]["passed"] == 1

        env_template = client.post(
            "/search-everywhere/ahrefs/env-template",
            headers=_headers(tenant_id),
            json={"include_optional": False, "include_configured": False},
        )
        assert env_template.status_code == 200, env_template.text
        env_payload = env_template.json()
        assert env_payload["status"] == "ok"
        assert env_payload["filename"].endswith(".env")

        gate = client.post(
            "/search-everywhere/ahrefs/production-gate",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "seo analytics",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "moz.com"],
                "max_results": 10,
            },
        )
        assert gate.status_code == 200, gate.text
        gate_payload = gate.json()
        assert gate_payload["status"] == "ok"
        assert "gate" in gate_payload
        assert "strict_live_probe" in gate_payload
        assert gate_payload["strict_live_probe"]["status"] in ("passed", "failed")

    def test_surfer_parity_and_full_automation(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        parity = client.get("/search-everywhere/surfer/parity-audit", headers=_headers(tenant_id))
        assert parity.status_code == 200, parity.text
        parity_payload = parity.json()
        assert parity_payload["status"] == "ok"
        assert isinstance(parity_payload.get("surfer_parity_chart"), list)
        assert parity_payload.get("summary", {}).get("modules_total", 0) >= 8
        assert parity_payload.get("summary", {}).get("implementation_pct") == 100.0
        assert isinstance(parity_payload.get("vendor_inventory"), list)

        response = client.post(
            "/search-everywhere/surfer/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com", "moz.com"],
                "location": "United States",
                "language": "en",
                "max_results": 12,
                "require_live_providers": False,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "results" in payload
        assert "keyword_discovery" in payload["results"]
        assert "content_gap" in payload["results"]
        assert "backlink_audit" in payload["results"]
        assert "backlink_gap" in payload["results"]
        assert "parity_summary" in payload["results"]

    def test_surfer_provider_checklist(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.get(
            "/search-everywhere/surfer/provider-checklist",
            headers=_headers(tenant_id),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "configured" in payload
        assert "total" in payload
        assert "configured_pct" in payload
        assert isinstance(payload.get("checklist"), list)
        assert any(item.get("provider") == "DataForSEO" for item in payload.get("checklist", []))

    def test_surfer_wiring_plan(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.get(
            "/search-everywhere/surfer/wiring-plan",
            headers=_headers(tenant_id),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "parity_summary" in payload
        assert "wiring_plan" in payload
        plan = payload["wiring_plan"]
        assert "stages" in plan
        assert "prioritized_missing_providers" in plan
        assert isinstance(plan.get("prioritized_missing_providers"), list)
        if plan["prioritized_missing_providers"]:
            first = plan["prioritized_missing_providers"][0]
            assert first.get("priority") in ("P0", "P1", "P2")
            assert "provider" in first
            assert "required_missing" in first

    def test_surfer_setup_playbook(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.get(
            "/search-everywhere/surfer/setup-playbook",
            headers=_headers(tenant_id),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "parity_summary" in payload
        assert "setup_playbook" in payload
        playbook = payload["setup_playbook"]
        assert "execution_order" in playbook
        assert "providers" in playbook
        assert isinstance(playbook.get("providers"), list)
        if playbook["providers"]:
            first = playbook["providers"][0]
            assert "provider" in first
            assert "setup_notes" in first
            assert isinstance(first.get("preflight_commands_powershell"), list)
            assert "verify_with" in first

    def test_surfer_production_gate(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/surfer/production-gate",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com"],
                "max_results": 10,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "gate" in payload
        assert "parity_summary" in payload
        assert "strict_live_probe" in payload
        assert "provider_checklist_summary" in payload
        assert payload["strict_live_probe"]["status"] in ("passed", "failed")

    def test_surfer_provider_bootstrap_filtered(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/surfer/provider-bootstrap",
            headers=_headers(tenant_id),
            json={"providers": ["DataForSEO"], "include_configured": True},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert isinstance(payload.get("requested_providers"), list)
        assert "dataforseo" in payload.get("requested_providers", [])
        for step in payload.get("steps", []):
            assert step.get("provider", "").lower() == "dataforseo"

    def test_surfer_provider_probes_force_success(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.fastapi.app.routers import rank_tracker

        def fake_fetch_provider_keywords(*_args: object, **_kwargs: object) -> dict[str, object]:
            return {"keywords": ["alpha", "beta"], "cache_hit": False}

        monkeypatch.setattr(rank_tracker, "_fetch_provider_keywords", fake_fetch_provider_keywords)

        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/surfer/provider-probes",
            headers=_headers(tenant_id),
            json={"providers": ["serper"], "include_unconfigured": True, "max_results": 3},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["summary"]["providers_requested"] == 1
        assert payload["summary"]["passed"] == 1
        assert payload["summary"]["strict_live_ready"] is True

    def test_surfer_env_template_default(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        response = client.post(
            "/search-everywhere/surfer/env-template",
            headers=_headers(tenant_id),
            json={"include_optional": False, "include_configured": False},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert "env_template" in payload
        assert isinstance(payload.get("missing_keys"), list)
        assert payload["filename"].endswith(".env")

    def test_frase_parity_and_full_automation(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"
        parity = client.get("/search-everywhere/frase/parity-audit", headers=_headers(tenant_id))
        assert parity.status_code == 200, parity.text
        parity_payload = parity.json()
        assert parity_payload["status"] == "ok"
        assert isinstance(parity_payload.get("frase_parity_chart"), list)
        assert parity_payload.get("summary", {}).get("modules_total", 0) >= 6
        assert parity_payload.get("summary", {}).get("implementation_pct") == 100.0
        assert isinstance(parity_payload.get("vendor_inventory"), list)

        response = client.post(
            "/search-everywhere/frase/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com", "moz.com"],
                "location": "United States",
                "language": "en",
                "max_results": 12,
                "require_live_providers": False,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload.get("framework") == "frase"
        assert "results" in payload
        assert "frase_workflow" in payload
        assert "phase_1_discovery" in payload["frase_workflow"]

    def test_frase_wiring_setup_and_gate(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"

        wiring = client.get("/search-everywhere/frase/wiring-plan", headers=_headers(tenant_id))
        assert wiring.status_code == 200, wiring.text
        wiring_payload = wiring.json()
        assert wiring_payload["status"] == "ok"
        assert "wiring_plan" in wiring_payload
        assert "parity_summary" in wiring_payload

        playbook = client.get("/search-everywhere/frase/setup-playbook", headers=_headers(tenant_id))
        assert playbook.status_code == 200, playbook.text
        playbook_payload = playbook.json()
        assert playbook_payload["status"] == "ok"
        assert "setup_playbook" in playbook_payload
        assert "execution_order" in playbook_payload["setup_playbook"]

        gate = client.post(
            "/search-everywhere/frase/production-gate",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com"],
                "max_results": 10,
            },
        )
        assert gate.status_code == 200, gate.text
        gate_payload = gate.json()
        assert gate_payload["status"] == "ok"
        assert "gate" in gate_payload
        assert "strict_live_probe" in gate_payload
        assert gate_payload["strict_live_probe"]["status"] in ("passed", "failed")

    def test_frase_provider_ops(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.fastapi.app.routers import rank_tracker

        def fake_fetch_provider_keywords(*_args: object, **_kwargs: object) -> dict[str, object]:
            return {"keywords": ["alpha", "beta"], "cache_hit": False}

        monkeypatch.setattr(rank_tracker, "_fetch_provider_keywords", fake_fetch_provider_keywords)

        tenant_id = "tenant-search-everywhere"
        checklist = client.get("/search-everywhere/frase/provider-checklist", headers=_headers(tenant_id))
        assert checklist.status_code == 200, checklist.text
        checklist_payload = checklist.json()
        assert checklist_payload["status"] == "ok"
        assert isinstance(checklist_payload.get("checklist"), list)

        bootstrap = client.post(
            "/search-everywhere/frase/provider-bootstrap",
            headers=_headers(tenant_id),
            json={"providers": ["DataForSEO"], "include_configured": True},
        )
        assert bootstrap.status_code == 200, bootstrap.text
        bootstrap_payload = bootstrap.json()
        assert bootstrap_payload["status"] == "ok"
        assert isinstance(bootstrap_payload.get("steps"), list)

        probes = client.post(
            "/search-everywhere/frase/provider-probes",
            headers=_headers(tenant_id),
            json={"providers": ["serper"], "include_unconfigured": True, "max_results": 3},
        )
        assert probes.status_code == 200, probes.text
        probes_payload = probes.json()
        assert probes_payload["status"] == "ok"
        assert probes_payload["summary"]["passed"] == 1

        env_template = client.post(
            "/search-everywhere/frase/env-template",
            headers=_headers(tenant_id),
            json={"include_optional": False, "include_configured": False},
        )
        assert env_template.status_code == 200, env_template.text
        env_payload = env_template.json()
        assert env_payload["status"] == "ok"
        assert env_payload["filename"].endswith(".env")

    def test_sitebulb_project_run_and_gate(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"

        project = client.post(
            "/search-everywhere/sitebulb/projects",
            headers=_headers(tenant_id),
            json={
                "name": "Primary Commerce Crawl",
                "primary_domain": "nuxtron.ai",
                "crawl_urls": ["https://nuxtron.ai", "https://nuxtron.ai/pricing"],
                "render_javascript": True,
                "emulate_mobile": True,
                "max_urls": 5000,
                "default_seed_keyword": "social media management",
                "default_competitors": ["semrush.com", "ahrefs.com"],
            },
        )
        assert project.status_code == 200, project.text
        project_payload = project.json()
        assert project_payload["status"] == "ok"
        project_id = project_payload["project"]["id"]

        run = client.post(
            f"/search-everywhere/sitebulb/projects/{project_id}/run",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "competitor_domains": ["semrush.com", "ahrefs.com"],
                "max_results": 10,
                "require_live_providers": False,
            },
        )
        assert run.status_code == 200, run.text
        run_payload = run.json()
        assert run_payload["status"] == "ok"
        assert "run" in run_payload
        assert "issue_chart" in run_payload
        assert "results" in run_payload
        run_id = run_payload["run"]["id"]

        runs = client.get(
            "/search-everywhere/sitebulb/runs",
            headers=_headers(tenant_id),
            params={"project_id": project_id},
        )
        assert runs.status_code == 200, runs.text
        runs_payload = runs.json()
        assert runs_payload["status"] == "ok"
        assert runs_payload["count"] >= 1

        run_detail = client.get(
            f"/search-everywhere/sitebulb/runs/{run_id}",
            headers=_headers(tenant_id),
        )
        assert run_detail.status_code == 200, run_detail.text
        run_detail_payload = run_detail.json()
        assert run_detail_payload["status"] == "ok"
        assert run_detail_payload["run"]["id"] == run_id

        completion = client.get(
            "/search-everywhere/sitebulb/completion-chart",
            headers=_headers(tenant_id),
        )
        assert completion.status_code == 200, completion.text
        completion_payload = completion.json()
        assert completion_payload["status"] == "ok"
        assert "chart" in completion_payload
        assert "summary" in completion_payload
        assert completion_payload["summary"]["modules_total"] >= 6

        gate = client.get(
            "/search-everywhere/sitebulb/production-gate",
            headers=_headers(tenant_id),
        )
        assert gate.status_code == 200, gate.text
        gate_payload = gate.json()
        assert gate_payload["status"] == "ok"
        assert "gate" in gate_payload
        assert "completion_summary" in gate_payload
        assert "preflight" in gate_payload
        assert isinstance(gate_payload.get("missing_provider_steps"), list)
        assert "next_actions" in gate_payload

    def test_sitebulb_schedule_and_vendors(self, client: TestClient) -> None:
        tenant_id = "tenant-search-everywhere"

        project = client.post(
            "/search-everywhere/sitebulb/projects",
            headers=_headers(tenant_id),
            json={
                "name": "Weekly Technical Crawl",
                "primary_domain": "nuxtron.ai",
                "crawl_urls": ["https://nuxtron.ai/docs"],
                "render_javascript": True,
                "emulate_mobile": False,
                "max_urls": 2000,
                "default_seed_keyword": "seo analytics",
                "default_competitors": ["semrush.com", "moz.com"],
            },
        )
        assert project.status_code == 200, project.text
        project_id = project.json()["project"]["id"]

        schedule = client.post(
            "/search-everywhere/sitebulb/schedules",
            headers=_headers(tenant_id),
            json={"project_id": project_id, "cron": "0 2 * * 1", "enabled": True},
        )
        assert schedule.status_code == 200, schedule.text
        schedule_payload = schedule.json()
        assert schedule_payload["status"] == "ok"
        assert schedule_payload["schedule"]["project_id"] == project_id

        schedule_list = client.get(
            "/search-everywhere/sitebulb/schedules",
            headers=_headers(tenant_id),
        )
        assert schedule_list.status_code == 200, schedule_list.text
        schedule_list_payload = schedule_list.json()
        assert schedule_list_payload["status"] == "ok"
        assert schedule_list_payload["count"] >= 1

        execute = client.post(
            "/search-everywhere/sitebulb/schedules/execute",
            headers=_headers(tenant_id),
            json={"due_only": False},
        )
        assert execute.status_code == 200, execute.text
        execute_payload = execute.json()
        assert execute_payload["status"] == "ok"
        assert execute_payload["executed_count"] >= 1

        vendors = client.get(
            "/search-everywhere/sitebulb/vendors",
            headers=_headers(tenant_id),
        )
        assert vendors.status_code == 200, vendors.text
        vendors_payload = vendors.json()
        assert vendors_payload["status"] == "ok"
        assert vendors_payload["vendors_total"] >= 1
        assert isinstance(vendors_payload.get("vendor_chart"), list)

        preflight = client.get(
            "/search-everywhere/sitebulb/preflight",
            headers=_headers(tenant_id),
        )
        assert preflight.status_code == 200, preflight.text
        preflight_payload = preflight.json()
        assert preflight_payload["status"] == "ok"
        assert "configured" in preflight_payload
        assert "total" in preflight_payload
        assert "configured_pct" in preflight_payload
        assert isinstance(preflight_payload.get("missing_provider_steps"), list)
        if preflight_payload["missing_provider_steps"]:
            first = preflight_payload["missing_provider_steps"][0]
            assert first.get("priority") in ("P0", "P1")
            assert "provider" in first
            assert isinstance(first.get("preflight_commands_powershell"), list)

        env_template = client.post(
            "/search-everywhere/sitebulb/env-template",
            headers=_headers(tenant_id),
            json={"include_optional": False, "include_configured": False},
        )
        assert env_template.status_code == 200, env_template.text
        env_template_payload = env_template.json()
        assert env_template_payload["status"] == "ok"
        assert env_template_payload["filename"].endswith(".env")
        assert isinstance(env_template_payload.get("missing_keys"), list)
        assert isinstance(env_template_payload.get("env_template"), str)

        gate_progress = client.get(
            "/search-everywhere/sitebulb/gate-progress",
            headers=_headers(tenant_id),
        )
        assert gate_progress.status_code == 200, gate_progress.text
        gate_progress_payload = gate_progress.json()
        assert gate_progress_payload["status"] == "ok"
        assert "baseline" in gate_progress_payload
        assert "projection" in gate_progress_payload
        assert isinstance(gate_progress_payload.get("provider_progression"), list)
        assert isinstance(gate_progress_payload["projection"].get("provider_progression"), list)
        assert "integration_configured_pct" in gate_progress_payload["baseline"]
        assert "steps_to_100pct" in gate_progress_payload["projection"]
        if gate_progress_payload["provider_progression"]:
            first = gate_progress_payload["provider_progression"][0]
            assert first.get("priority") in ("P0", "P1")
            assert "integration_pct_if_added" in first

        bundle = client.post(
            "/search-everywhere/sitebulb/remediation-bundle",
            headers=_headers(tenant_id),
            json={"include_optional": False, "include_configured": False, "top_steps": 5},
        )
        assert bundle.status_code == 200, bundle.text
        bundle_payload = bundle.json()
        assert bundle_payload["status"] == "ok"
        assert "preflight" in bundle_payload
        assert "remediation_steps" in bundle_payload
        assert "gate" in bundle_payload
        assert "env_template" in bundle_payload
        assert "bundle" in bundle_payload
        assert "preflight" in bundle_payload["bundle"]
        assert "gate_progress" in bundle_payload["bundle"]
        assert "gate_state" in bundle_payload["bundle"]
        assert "env_template" in bundle_payload["bundle"]
        assert isinstance(bundle_payload["bundle"]["preflight"].get("missing_provider_steps"), list)
        assert isinstance(bundle_payload["bundle"]["gate_progress"].get("provider_progression"), list)
        assert isinstance(bundle_payload["bundle"]["env_template"].get("missing_keys"), list)

        export_json = client.get(
            "/search-everywhere/sitebulb/remediation-bundle/export",
            headers=_headers(tenant_id),
            params={"format": "json", "top_steps": 5, "include_optional": False, "include_configured": False},
        )
        assert export_json.status_code == 200, export_json.text
        export_json_payload = export_json.json()
        assert export_json_payload["status"] == "ok"
        assert export_json_payload["format"] == "json"
        assert export_json_payload["filename"].endswith(".json")
        assert isinstance(export_json_payload.get("json"), list)

        export_csv = client.get(
            "/search-everywhere/sitebulb/remediation-bundle/export",
            headers=_headers(tenant_id),
            params={"format": "csv", "top_steps": 5, "include_optional": False, "include_configured": False},
        )
        assert export_csv.status_code == 200, export_csv.text
        export_csv_payload = export_csv.json()
        assert export_csv_payload["status"] == "ok"
        assert export_csv_payload["format"] == "csv"
        assert export_csv_payload["filename"].endswith(".csv")
        assert isinstance(export_csv_payload.get("csv"), str)
        if export_csv_payload["count"] > 0:
            assert "provider,kind,priority,required_missing,integration_pct_if_added,gate_passed,gate_blockers" in export_csv_payload["csv"]

        verification = client.get(
            "/search-everywhere/sitebulb/verification-report",
            headers=_headers(tenant_id),
        )
        assert verification.status_code == 200, verification.text
        verification_payload = verification.json()
        assert verification_payload["status"] == "ok"
        assert "verification" in verification_payload
        section = verification_payload["verification"]
        assert "slice_ready" in section
        assert "slice_gate" in section
        assert isinstance(section.get("evidence_table"), list)
        assert "validation_boundaries" in section
        if section["evidence_table"]:
            first_row = section["evidence_table"][0]
            assert "check" in first_row
            assert first_row.get("status") in ("pass", "fail")

    def test_hootsuite_end_to_end_automation_suite(self, client: TestClient) -> None:
        tenant_id = "tenant-hootsuite-search-everywhere"

        products = client.get(
            "/search-everywhere/hootsuite/products",
            headers=_headers(tenant_id),
        )
        assert products.status_code == 200, products.text
        products_payload = products.json()
        assert products_payload["status"] == "ok"
        assert products_payload["count"] >= 6
        assert isinstance(products_payload.get("products"), list)

        detail = client.get(
            "/search-everywhere/hootsuite/products/detail/publishing",
            headers=_headers(tenant_id),
        )
        assert detail.status_code == 200, detail.text
        detail_payload = detail.json()
        assert detail_payload["status"] == "ok"
        assert detail_payload["product"]["implemented"] is True
        assert detail_payload["product"]["e2e_verified"] is True
        assert detail_payload["product"]["production_grade_ready"] is True

        product_run = client.post(
            "/search-everywhere/hootsuite/products/publishing/run",
            headers=_headers(tenant_id),
            json={"objective": "publish campaign", "context": {"network": "linkedin"}},
        )
        assert product_run.status_code == 200, product_run.text
        product_run_payload = product_run.json()
        assert product_run_payload["status"] == "ok"
        assert product_run_payload["result"]["implemented"] is True
        assert product_run_payload["result"]["e2e_verified"] is True

        checklist = client.get(
            "/search-everywhere/hootsuite/provider-checklist",
            headers=_headers(tenant_id),
        )
        assert checklist.status_code == 200, checklist.text
        checklist_payload = checklist.json()
        assert checklist_payload["status"] == "ok"
        assert checklist_payload["total"] >= checklist_payload["configured"]

        wiring_apply = client.post(
            "/search-everywhere/hootsuite/wiring/apply",
            headers=_headers(tenant_id),
            json={
                "providers": ["DataForSEO", "OpenAI"],
                "include_all_missing": True,
                "include_optional_auth": True,
            },
        )
        assert wiring_apply.status_code == 200, wiring_apply.text
        wiring_apply_payload = wiring_apply.json()
        assert wiring_apply_payload["status"] == "ok"
        assert wiring_apply_payload.get("gate", {}).get("passed") is True
        assert wiring_apply_payload.get("checklist_summary", {}).get("configured_pct") == 100.0

        full = client.post(
            "/search-everywhere/hootsuite/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "social media management",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["hootsuite.com", "sproutsocial.com"],
                "location": "United States",
                "language": "en",
                "max_results": 10,
                "require_live_providers": False,
            },
        )
        assert full.status_code == 200, full.text
        full_payload = full.json()
        assert full_payload["status"] == "ok"
        assert "results" in full_payload
        assert "hootsuite_modules" in full_payload
        assert isinstance(full_payload.get("third_parties_and_vendors"), list)
        assert any(item.get("vendor") == "Hootsuite" for item in full_payload.get("third_parties_and_vendors", []))
        assert full_payload.get("completion_summary", {}).get("implementation_pct") == 100.0
        full_e2e_pct = float(full_payload.get("completion_summary", {}).get("e2e_verified_pct", 0.0))
        full_integration_pct = float(full_payload.get("completion_summary", {}).get("integration_configured_pct", 0.0))
        assert 0.0 <= full_e2e_pct <= 100.0
        assert 0.0 <= full_integration_pct <= 100.0
        production_gate = full_payload.get("production_gate", {})
        assert isinstance(production_gate.get("passed"), bool)
        assert isinstance(production_gate.get("blockers"), list)
        if production_gate.get("passed"):
            assert production_gate.get("blockers") == []
        else:
            assert len(production_gate.get("blockers", [])) > 0

        completion = client.get(
            "/search-everywhere/hootsuite/completion-chart",
            headers=_headers(tenant_id),
        )
        assert completion.status_code == 200, completion.text
        completion_payload = completion.json()
        assert completion_payload["status"] == "ok"
        assert completion_payload.get("summary", {}).get("implementation_pct") == 100.0
        completion_e2e_pct = float(completion_payload.get("summary", {}).get("e2e_verified_pct", 0.0))
        assert 0.0 <= completion_e2e_pct <= 100.0
        completion_integration_pct = float(completion_payload.get("summary", {}).get("integration_configured_pct", 0.0))
        assert 0.0 <= completion_integration_pct <= 100.0

        gate = client.get(
            "/search-everywhere/hootsuite/production-gate",
            headers=_headers(tenant_id),
        )
        assert gate.status_code == 200, gate.text
        gate_payload = gate.json()
        assert gate_payload["status"] == "ok"
        assert gate_payload.get("gate", {}).get("passed") is True

        verification = client.get(
            "/search-everywhere/hootsuite/verification-report",
            headers=_headers(tenant_id),
        )
        assert verification.status_code == 200, verification.text
        verification_payload = verification.json()
        assert verification_payload["status"] == "ok"
        assert verification_payload.get("verification", {}).get("slice_ready") is True
        boundaries = verification_payload.get("verification", {}).get("validation_boundaries", {})
        assert boundaries.get("validated_slice") == "search_everywhere hootsuite product suite"

        vendors = client.get(
            "/search-everywhere/hootsuite/vendors",
            headers=_headers(tenant_id),
        )
        assert vendors.status_code == 200, vendors.text
        vendors_payload = vendors.json()
        assert vendors_payload["status"] == "ok"
        assert isinstance(vendors_payload.get("vendor_chart"), list)
        assert any(item.get("vendor") == "Hootsuite" for item in vendors_payload.get("vendor_chart", []))
        assert isinstance(vendors_payload.get("vendor_usage_by_feature"), dict)
        assert "reputation_management" in vendors_payload.get("vendor_usage_by_feature", {})

        features = client.get(
            "/search-everywhere/hootsuite/features",
            headers=_headers(tenant_id),
        )
        assert features.status_code == 200, features.text
        features_payload = features.json()
        assert features_payload["status"] == "ok"
        assert isinstance(features_payload.get("feature_matrix"), list)
        assert len(features_payload.get("feature_matrix", [])) >= 4
        summary = features_payload.get("summary", {})
        assert summary.get("implementation_pct") == 100.0
        assert summary.get("e2e_verified_pct") == 100.0
        assert isinstance(features_payload.get("coverage_chart"), list)

        features_automation = client.post(
            "/search-everywhere/hootsuite/features/automation",
            headers=_headers(tenant_id),
            json={
                "objective": "full social coverage",
                "brands": ["nuxtron"],
                "competitors": ["hootsuite.com", "sproutsocial.com"],
                "networks": ["facebook", "instagram", "linkedin", "x"],
                "timeframe_days": 90,
                "require_live_providers": False,
            },
        )
        assert features_automation.status_code == 200, features_automation.text
        features_automation_payload = features_automation.json()
        assert features_automation_payload["status"] == "ok"
        assert isinstance(features_automation_payload.get("automation_outputs"), dict)
        assert "reputation_management" in features_automation_payload.get("automation_outputs", {})
        assert "market_research" in features_automation_payload.get("automation_outputs", {})
        assert "social_media_management" in features_automation_payload.get("automation_outputs", {})
        assert isinstance(features_automation_payload.get("third_parties_and_vendors"), list)
        assert any(item.get("vendor") == "Talkwalker" for item in features_automation_payload.get("third_parties_and_vendors", []))

        parity = client.get(
            "/search-everywhere/hootsuite/parity-audit",
            headers=_headers(tenant_id),
        )
        assert parity.status_code == 200, parity.text
        parity_payload = parity.json()
        assert parity_payload["status"] == "ok"
        assert isinstance(parity_payload.get("feature_coverage_chart"), list)
        feature_summary = parity_payload.get("feature_summary", {})
        assert feature_summary.get("implementation_pct") == 100.0
        assert feature_summary.get("e2e_verified_pct") == 100.0


        wiring_apply = client.post(
            "/search-everywhere/brightedge/wiring/apply",
            headers=_headers(tenant_id),
            json={
                "providers": ["Google Search Console", "OpenAI"],
                "include_all_missing": True,
                "include_optional_auth": True,
            },
        )
        assert wiring_apply.status_code == 200, wiring_apply.text
        wiring_apply_payload = wiring_apply.json()
        assert wiring_apply_payload["status"] == "ok"
        assert wiring_apply_payload.get("gate", {}).get("passed") is True
        assert wiring_apply_payload.get("checklist_summary", {}).get("configured_pct") == 100.0

        full = client.post(
            "/search-everywhere/brightedge/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "enterprise seo and aeo",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["brightedge.com", "conductor.com"],
                "location": "United States",
                "language": "en",
                "max_results": 10,
                "require_live_providers": False,
            },
        )
        assert full.status_code == 200, full.text
        full_payload = full.json()
        assert full_payload["status"] == "ok"
        assert "results" in full_payload
        assert "brightedge_modules" in full_payload
        assert isinstance(full_payload.get("third_parties_and_vendors"), list)
        assert any(item.get("vendor") == "BrightEdge" for item in full_payload.get("third_parties_and_vendors", []))
        assert full_payload.get("completion_summary", {}).get("implementation_pct") == 100.0
        assert full_payload.get("completion_summary", {}).get("e2e_verified_pct") == 100.0
        assert full_payload.get("completion_summary", {}).get("integration_configured_pct") == 100.0
        assert full_payload.get("production_gate", {}).get("passed") is True

        completion = client.get(
            "/search-everywhere/brightedge/completion-chart",
            headers=_headers(tenant_id),
        )
        assert completion.status_code == 200, completion.text
        completion_payload = completion.json()
        assert completion_payload["status"] == "ok"
        assert completion_payload.get("summary", {}).get("implementation_pct") == 100.0
        assert completion_payload.get("summary", {}).get("e2e_verified_pct") == 100.0
        assert completion_payload.get("summary", {}).get("integration_configured_pct") == 100.0

        gate = client.get(
            "/search-everywhere/brightedge/production-gate",
            headers=_headers(tenant_id),
        )
        assert gate.status_code == 200, gate.text
        gate_payload = gate.json()
        assert gate_payload["status"] == "ok"
        assert gate_payload.get("gate", {}).get("passed") is True

        verification = client.get(
            "/search-everywhere/brightedge/verification-report",
            headers=_headers(tenant_id),
        )
        assert verification.status_code == 200, verification.text
        verification_payload = verification.json()
        assert verification_payload["status"] == "ok"
        assert verification_payload.get("verification", {}).get("slice_ready") is True
        boundaries = verification_payload.get("verification", {}).get("validation_boundaries", {})
        assert boundaries.get("validated_slice") == "search_everywhere brightedge product suite"

        vendors = client.get(
            "/search-everywhere/brightedge/vendors",
            headers=_headers(tenant_id),
        )
        assert vendors.status_code == 200, vendors.text
        vendors_payload = vendors.json()
        assert vendors_payload["status"] == "ok"
        assert isinstance(vendors_payload.get("vendor_chart"), list)
        assert any(item.get("vendor") == "BrightEdge" for item in vendors_payload.get("vendor_chart", []))

    def test_marketmuse_end_to_end_automation_suite(self, client: TestClient) -> None:
        tenant_id = "tenant-marketmuse-search-everywhere"

        products = client.get(
            "/search-everywhere/marketmuse/products",
            headers=_headers(tenant_id),
        )
        assert products.status_code == 200, products.text
        products_payload = products.json()
        assert products_payload["status"] == "ok"
        assert products_payload["count"] >= 6
        assert isinstance(products_payload.get("products"), list)

        detail = client.get(
            "/search-everywhere/marketmuse/products/detail/inventory",
            headers=_headers(tenant_id),
        )
        assert detail.status_code == 200, detail.text
        detail_payload = detail.json()
        assert detail_payload["status"] == "ok"
        assert detail_payload["product"]["implemented"] is True
        assert detail_payload["product"]["e2e_verified"] is True
        assert detail_payload["product"]["production_grade_ready"] is False

        product_run = client.post(
            "/search-everywhere/marketmuse/products/inventory/run",
            headers=_headers(tenant_id),
            json={"objective": "score inventory", "context": {"market": "enterprise"}},
        )
        assert product_run.status_code == 200, product_run.text
        product_run_payload = product_run.json()
        assert product_run_payload["status"] == "ok"
        assert product_run_payload["result"]["implemented"] is True
        assert product_run_payload["result"]["e2e_verified"] is True

        checklist = client.get(
            "/search-everywhere/marketmuse/provider-checklist",
            headers=_headers(tenant_id),
        )
        assert checklist.status_code == 200, checklist.text
        checklist_payload = checklist.json()
        assert checklist_payload["status"] == "ok"
        assert checklist_payload["total"] >= checklist_payload["configured"]

        wiring_apply = client.post(
            "/search-everywhere/marketmuse/wiring/apply",
            headers=_headers(tenant_id),
            json={
                "providers": ["Google Search Console", "OpenAI"],
                "include_all_missing": True,
                "include_optional_auth": True,
            },
        )
        assert wiring_apply.status_code == 200, wiring_apply.text
        wiring_apply_payload = wiring_apply.json()
        assert wiring_apply_payload["status"] == "ok"
        assert wiring_apply_payload.get("gate", {}).get("passed") is True
        assert wiring_apply_payload.get("checklist_summary", {}).get("configured_pct") == 100.0

        full = client.post(
            "/search-everywhere/marketmuse/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "ai content strategy",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["marketmuse.com", "brightedge.com"],
                "location": "United States",
                "language": "en",
                "max_results": 10,
                "require_live_providers": False,
            },
        )
        assert full.status_code == 200, full.text
        full_payload = full.json()
        assert full_payload["status"] == "ok"
        assert "results" in full_payload
        assert "marketmuse_modules" in full_payload
        assert isinstance(full_payload.get("third_parties_and_vendors"), list)
        assert any(item.get("vendor") == "MarketMuse" for item in full_payload.get("third_parties_and_vendors", []))
        assert full_payload.get("completion_summary", {}).get("implementation_pct") == 100.0
        assert full_payload.get("completion_summary", {}).get("e2e_verified_pct") == 100.0
        assert full_payload.get("completion_summary", {}).get("integration_configured_pct") == 100.0
        assert full_payload.get("production_gate", {}).get("passed") is True

        completion = client.get(
            "/search-everywhere/marketmuse/completion-chart",
            headers=_headers(tenant_id),
        )
        assert completion.status_code == 200, completion.text
        completion_payload = completion.json()
        assert completion_payload["status"] == "ok"
        assert completion_payload.get("summary", {}).get("implementation_pct") == 100.0
        assert completion_payload.get("summary", {}).get("e2e_verified_pct") == 100.0
        assert completion_payload.get("summary", {}).get("integration_configured_pct") == 100.0

        gate = client.get(
            "/search-everywhere/marketmuse/production-gate",
            headers=_headers(tenant_id),
        )
        assert gate.status_code == 200, gate.text
        gate_payload = gate.json()
        assert gate_payload["status"] == "ok"
        assert gate_payload.get("gate", {}).get("passed") is True

        verification = client.get(
            "/search-everywhere/marketmuse/verification-report",
            headers=_headers(tenant_id),
        )
        assert verification.status_code == 200, verification.text
        verification_payload = verification.json()
        assert verification_payload["status"] == "ok"
        assert verification_payload.get("verification", {}).get("slice_ready") is True
        boundaries = verification_payload.get("verification", {}).get("validation_boundaries", {})
        assert boundaries.get("validated_slice") == "search_everywhere marketmuse product suite"

        vendors = client.get(
            "/search-everywhere/marketmuse/vendors",
            headers=_headers(tenant_id),
        )
        assert vendors.status_code == 200, vendors.text
        vendors_payload = vendors.json()
        assert vendors_payload["status"] == "ok"
        assert isinstance(vendors_payload.get("vendor_chart"), list)
        assert any(item.get("vendor") == "MarketMuse" for item in vendors_payload.get("vendor_chart", []))

    def test_brightedge_end_to_end_automation_suite(self, client: TestClient) -> None:
        tenant_id = "tenant-brightedge-search-everywhere"

        products = client.get(
            "/search-everywhere/brightedge/products",
            headers=_headers(tenant_id),
        )
        assert products.status_code == 200, products.text
        products_payload = products.json()
        assert products_payload["status"] == "ok"
        assert products_payload["count"] >= 6
        assert isinstance(products_payload.get("products"), list)

        detail = client.get(
            "/search-everywhere/brightedge/products/detail/data-cube-x",
            headers=_headers(tenant_id),
        )
        assert detail.status_code == 200, detail.text
        detail_payload = detail.json()
        assert detail_payload["status"] == "ok"
        assert detail_payload["product"]["implemented"] is True
        assert detail_payload["product"]["e2e_verified"] is True
        assert detail_payload["product"]["production_grade_ready"] is False

        product_run = client.post(
            "/search-everywhere/brightedge/products/data-cube-x/run",
            headers=_headers(tenant_id),
            json={"objective": "track market demand", "context": {"market": "enterprise"}},
        )
        assert product_run.status_code == 200, product_run.text
        product_run_payload = product_run.json()
        assert product_run_payload["status"] == "ok"
        assert product_run_payload["result"]["implemented"] is True
        assert product_run_payload["result"]["e2e_verified"] is True

        checklist = client.get(
            "/search-everywhere/brightedge/provider-checklist",
            headers=_headers(tenant_id),
        )
        assert checklist.status_code == 200, checklist.text
        checklist_payload = checklist.json()
        assert checklist_payload["status"] == "ok"
        assert checklist_payload["total"] >= checklist_payload["configured"]

        wiring_apply = client.post(
            "/search-everywhere/brightedge/wiring/apply",
            headers=_headers(tenant_id),
            json={
                "providers": ["Google Search Console", "OpenAI"],
                "include_all_missing": True,
                "include_optional_auth": True,
            },
        )
        assert wiring_apply.status_code == 200, wiring_apply.text
        wiring_apply_payload = wiring_apply.json()
        assert wiring_apply_payload["status"] == "ok"
        assert wiring_apply_payload.get("gate", {}).get("passed") is True
        assert wiring_apply_payload.get("checklist_summary", {}).get("configured_pct") == 100.0

        full = client.post(
            "/search-everywhere/brightedge/full-automation",
            headers=_headers(tenant_id),
            json={
                "seed_keyword": "enterprise seo and aeo",
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["brightedge.com", "conductor.com"],
                "location": "United States",
                "language": "en",
                "max_results": 10,
                "require_live_providers": False,
            },
        )
        assert full.status_code == 200, full.text
        full_payload = full.json()
        assert full_payload["status"] == "ok"
        assert "results" in full_payload
        assert "brightedge_modules" in full_payload
        assert isinstance(full_payload.get("third_parties_and_vendors"), list)
        assert any(item.get("vendor") == "BrightEdge" for item in full_payload.get("third_parties_and_vendors", []))
        assert full_payload.get("completion_summary", {}).get("implementation_pct") == 100.0
        assert full_payload.get("completion_summary", {}).get("e2e_verified_pct") == 100.0
        assert full_payload.get("completion_summary", {}).get("integration_configured_pct") == 100.0
        assert full_payload.get("production_gate", {}).get("passed") is True

        completion = client.get(
            "/search-everywhere/brightedge/completion-chart",
            headers=_headers(tenant_id),
        )
        assert completion.status_code == 200, completion.text
        completion_payload = completion.json()
        assert completion_payload["status"] == "ok"
        assert completion_payload.get("summary", {}).get("implementation_pct") == 100.0
        assert completion_payload.get("summary", {}).get("e2e_verified_pct") == 100.0
        assert completion_payload.get("summary", {}).get("integration_configured_pct") == 100.0

        gate = client.get(
            "/search-everywhere/brightedge/production-gate",
            headers=_headers(tenant_id),
        )
        assert gate.status_code == 200, gate.text
        gate_payload = gate.json()
        assert gate_payload["status"] == "ok"
        assert gate_payload.get("gate", {}).get("passed") is True

        verification = client.get(
            "/search-everywhere/brightedge/verification-report",
            headers=_headers(tenant_id),
        )
        assert verification.status_code == 200, verification.text
        verification_payload = verification.json()
        assert verification_payload["status"] == "ok"
        assert verification_payload.get("verification", {}).get("slice_ready") is True
        boundaries = verification_payload.get("verification", {}).get("validation_boundaries", {})
        assert boundaries.get("validated_slice") == "search_everywhere brightedge product suite"

        vendors = client.get(
            "/search-everywhere/brightedge/vendors",
            headers=_headers(tenant_id),
        )
        assert vendors.status_code == 200, vendors.text
        vendors_payload = vendors.json()
        assert vendors_payload["status"] == "ok"
        assert isinstance(vendors_payload.get("vendor_chart"), list)
        assert any(item.get("vendor") == "BrightEdge" for item in vendors_payload.get("vendor_chart", []))
