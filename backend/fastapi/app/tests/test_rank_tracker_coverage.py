"""
Rank Tracker — comprehensive coverage tests.

40+ assertions against the full rank-tracker router.
"""

from __future__ import annotations

import os
import uuid

os.environ["ALLOW_HEADER_API_KEYS"] = "true"
os.environ["FASTAPI_API_KEY"] = "test-api-key"

import backend.fastapi.app.routers.rank_tracker as rank_tracker  # noqa: E402
from backend.fastapi.app.legacy_main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rt-test-tenant"}
H2 = {"X-API-Key": "test-api-key", "X-Tenant-Id": "rt-test-tenant-2"}
BASE = "/rank-tracker"


class TestRankTrackerCoverage:
    # ------------------------------------------------------------------
    # Keywords CRUD
    # ------------------------------------------------------------------

    def test_add_keyword(self):
        keyword = f"digital-marketing-platform-{uuid.uuid4().hex[:6]}"
        r = client.post(f"{BASE}/tracked-keywords", json={
            "keyword": keyword,
            "target_url": "https://yourdomain.com/blog/marketing",
        }, headers=H)
        assert r.status_code == 201
        kw = r.json()["keyword"]
        assert kw["keyword"] == keyword
        assert "current_position" in kw
        assert 1 <= kw["current_position"] <= 100

    def test_add_keyword_has_metrics(self):
        kw_name = f"SEO-tools-{uuid.uuid4().hex[:6]}"
        r = client.post(f"{BASE}/tracked-keywords", json={
            "keyword": kw_name,
        }, headers=H)
        kw = r.json()["keyword"]
        for key in ("search_volume", "keyword_difficulty", "traffic_potential", "search_intent"):
            assert key in kw, f"Missing: {key}"

    def test_add_keyword_duplicate_returns_409(self):
        kw_name = f"unique-kw-{uuid.uuid4().hex[:6]}"
        client.post(f"{BASE}/tracked-keywords", json={"keyword": kw_name}, headers=H)
        r2 = client.post(f"{BASE}/tracked-keywords", json={"keyword": kw_name}, headers=H)
        assert r2.status_code == 409

    def test_list_keywords_returns_seeded(self):
        r = client.get(f"{BASE}/tracked-keywords", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert len(data["keywords"]) >= 1
        assert "tracking" in data

    def test_list_keywords_has_all_fields(self):
        r = client.get(f"{BASE}/tracked-keywords", headers=H)
        if r.json()["keywords"]:
            kw = r.json()["keywords"][0]
            for key in ("id", "keyword", "current_position", "search_volume", "position_change_30d"):
                assert key in kw, f"Missing: {key}"

    def test_delete_keyword(self):
        r = client.post(f"{BASE}/tracked-keywords", json={"keyword": f"del-kw-{uuid.uuid4().hex[:6]}"}, headers=H)
        kw_id = r.json()["keyword"]["id"]
        r2 = client.delete(f"{BASE}/tracked-keywords/{kw_id}", headers=H)
        assert r2.status_code == 200
        assert r2.json()["deleted"] == kw_id

    def test_delete_keyword_not_found(self):
        r = client.delete(f"{BASE}/tracked-keywords/{uuid.uuid4()}", headers=H)
        assert r.status_code == 404

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def test_add_project(self):
        r = client.post(f"{BASE}/add-project", json={
            "domain": "example.com",
            "location": "United Kingdom",
            "search_engine": "Google",
        }, headers=H)
        assert r.status_code == 201
        p = r.json()["project"]
        assert p["domain"] == "example.com"
        assert p["location"] == "United Kingdom"

    def test_add_project_seeded_values(self):
        r = client.get(f"{BASE}/projects", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_projects(self):
        r = client.get(f"{BASE}/projects", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "projects" in data
        assert "total" in data

    def test_delete_project(self):
        r = client.post(f"{BASE}/add-project", json={
            "domain": f"del-{uuid.uuid4().hex[:6]}.com",
        }, headers=H)
        p_id = r.json()["project"]["id"]
        r2 = client.delete(f"{BASE}/projects/{p_id}", headers=H)
        assert r2.status_code == 200
        assert r2.json()["deleted"] == p_id

    # ------------------------------------------------------------------
    # SERP Positions
    # ------------------------------------------------------------------

    def test_get_positions_returns_summary(self):
        r = client.get(f"{BASE}/positions", headers=H)
        assert r.status_code == 200
        data = r.json()
        summary = data["summary"]
        for key in ("total_keywords", "improved_30d", "dropped_30d", "top_10", "top_3"):
            assert key in summary, f"Missing summary key: {key}"

    def test_get_positions_pagination(self):
        r = client.get(f"{BASE}/positions?page=1&page_size=5", headers=H)
        assert r.status_code == 200
        assert len(r.json()["positions"]) <= 5

    def test_get_positions_page_calculation(self):
        r = client.get(f"{BASE}/positions?page=1&page_size=3", headers=H)
        data = r.json()
        assert "total" in data
        assert "pages" in data
        assert "page" in data

    def test_check_serp(self):
        r = client.post(f"{BASE}/positions/check", json={
            "keywords": ["SEO tool", "digital marketing"]
        }, headers=H)
        assert r.status_code == 200
        results = r.json()["serp_check"]
        assert len(results) == 2
        for result in results:
            assert "keyword" in result
            assert "position" in result
            assert 1 <= result["position"] <= 100

    def test_check_serp_single_keyword(self):
        r = client.post(f"{BASE}/positions/check", json={"keywords": ["test keyword"]}, headers=H)
        results = r.json()["serp_check"]
        assert len(results) == 1
        assert results[0]["keyword"] == "test keyword"

    # ------------------------------------------------------------------
    # Competitors
    # ------------------------------------------------------------------

    def test_add_competitor(self):
        r = client.post(f"{BASE}/competitors", json={
            "domain": f"comp-{uuid.uuid4().hex[:6]}.com"
        }, headers=H)
        assert r.status_code == 201
        c = r.json()["competitor"]
        assert "authority_score" in c
        assert "organic_keywords" in c
        assert "organic_traffic_estimate" in c

    def test_add_competitor_duplicate_returns_409(self):
        comp = f"comp-{uuid.uuid4().hex[:6]}.com"
        client.post(f"{BASE}/competitors", json={"domain": comp}, headers=H)
        r2 = client.post(f"{BASE}/competitors", json={"domain": comp}, headers=H)
        assert r2.status_code == 409

    def test_list_competitors(self):
        r = client.get(f"{BASE}/competitors", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "competitors" in data
        assert "total" in data

    def test_delete_competitor(self):
        r = client.post(f"{BASE}/competitors", json={"domain": f"del-{uuid.uuid4().hex[:6]}.com"}, headers=H)
        c_id = r.json()["competitor"]["id"]
        r2 = client.delete(f"{BASE}/competitors/{c_id}", headers=H)
        assert r2.status_code == 200
        assert r2.json()["deleted"] == c_id

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def test_history_aggregate_returns_timeseries(self):
        r = client.get(f"{BASE}/history?days=90", headers=H)
        assert r.status_code == 200
        data = r.json()["history"]
        assert "timeseries" in data
        assert "days" in data
        assert data["days"] == 90

    def test_history_timeseries_structure(self):
        r = client.get(f"{BASE}/history?days=30", headers=H)
        ts = r.json()["history"]["timeseries"]
        if ts:
            entry = ts[0]
            for key in ("date", "avg_position", "total_impressions", "total_clicks"):
                assert key in entry, f"Missing: {key}"

    def test_history_custom_days(self):
        r = client.get(f"{BASE}/history?days=180", headers=H)
        assert r.json()["history"]["days"] == 180

    def test_history_specific_keyword(self):
        # Get a keyword
        r_kw = client.get(f"{BASE}/tracked-keywords", headers=H)
        keywords = r_kw.json()["keywords"]
        if keywords:
            kw_id = keywords[0]["id"]
            r = client.get(f"{BASE}/history?keyword_id={kw_id}", headers=H)
            assert r.status_code == 200
            data = r.json()["history"]
            assert data["keyword_id"] == kw_id
            assert "keyword" in data

    # ------------------------------------------------------------------
    # Lost / Gained
    # ------------------------------------------------------------------

    def test_lost_gained_returns_structure(self):
        r = client.get(f"{BASE}/lost-gained", headers=H)
        assert r.status_code == 200
        data = r.json()["lost_gained"]
        for key in ("gained", "lost", "days"):
            assert key in data, f"Missing: {key}"

    def test_lost_gained_has_details(self):
        r = client.get(f"{BASE}/lost-gained?days=30", headers=H)
        data = r.json()["lost_gained"]
        if data["gained"]:
            item = data["gained"][0]
            for key in ("keyword", "previous_position", "current_position", "change", "traffic_delta"):
                assert key in item, f"Missing: {key}"

    # ------------------------------------------------------------------
    # Visibility Score
    # ------------------------------------------------------------------

    def test_visibility_score_returns_metrics(self):
        r = client.get(f"{BASE}/visibility-score", headers=H)
        assert r.status_code == 200
        data = r.json()["visibility"]
        for key in ("estimated_monthly_traffic", "visibility_score", "keywords_top_3", "keywords_top_10"):
            assert key in data, f"Missing: {key}"

    def test_visibility_score_0_to_100(self):
        r = client.get(f"{BASE}/visibility-score", headers=H)
        score = r.json()["visibility"]["visibility_score"]
        assert 0 <= score <= 100

    # ------------------------------------------------------------------
    # Forecasts
    # ------------------------------------------------------------------

    def test_forecasts_has_positions(self):
        r = client.get(f"{BASE}/forecasts", headers=H)
        assert r.status_code == 200
        forecasts = r.json()["forecasts"]
        assert len(forecasts) > 0
        positions = [f["position"] for f in forecasts]
        assert 1 in positions
        assert 10 in positions

    def test_forecast_structure(self):
        r = client.get(f"{BASE}/forecasts", headers=H)
        if r.json()["forecasts"]:
            f = r.json()["forecasts"][0]
            for key in ("position", "estimated_ctr", "estimated_monthly_clicks"):
                assert key in f, f"Missing: {key}"

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def test_analytics_returns_movers(self):
        r = client.get(f"{BASE}/analytics", headers=H)
        assert r.status_code == 200
        data = r.json()["analytics"]
        for key in ("total_keywords", "improved_count", "declined_count", "stable_count", "top_movers_up", "top_movers_down"):
            assert key in data, f"Missing: {key}"

    def test_analytics_movers_have_details(self):
        r = client.get(f"{BASE}/analytics", headers=H)
        movers = r.json()["analytics"]["top_movers_up"]
        if movers:
            m = movers[0]
            for key in ("keyword", "previous_position", "current_position", "change"):
                assert key in m, f"Missing: {key}"

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def test_set_alert(self):
        # Get a keyword
        r_kw = client.get(f"{BASE}/tracked-keywords", headers=H)
        keywords = r_kw.json()["keywords"]
        if keywords:
            kw_id = keywords[0]["id"]
            r = client.post(f"{BASE}/alerts/set", json={
                "keyword_id": kw_id,
                "alert_type": "rank_drop",
                "threshold": 5,
            }, headers=H)
            assert r.status_code == 201
            alert = r.json()["alert"]
            assert alert["keyword_id"] == kw_id
            assert alert["alert_type"] == "rank_drop"

    def test_get_alerts(self):
        r = client.get(f"{BASE}/alerts", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        assert "total" in data
        assert "active" in data

    # ------------------------------------------------------------------
    # Keyword Research
    # ------------------------------------------------------------------

    def test_keyword_research_sources(self):
        r = client.get(f"{BASE}/keyword-research/sources", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "sources" in data
        assert data["total_sources"] >= 1
        assert "priority_order" in data
        assert data["priority_order"][-1] == "nuxtron_synthetic"
        assert len(data["priority_order"]) >= 2
        assert "network_enabled" in data
        assert "cache_ttl_seconds" in data

    def test_keyword_research_vendors(self):
        r = client.get(f"{BASE}/keyword-research/vendors", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["strategy"] == "hybrid_multi_source_with_resilient_fallback"
        providers = data["providers"]
        assert isinstance(providers, list)
        assert len(providers) >= 5
        provider_keys = {provider["key"] for provider in providers}
        assert "dataforseo" in provider_keys
        assert "serper" in provider_keys
        assert "google_keyword_planner" in provider_keys
        assert "google_search_console" in provider_keys
        assert "nuxtron_synthetic" in provider_keys

    def test_google_keyword_planner_adapter(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "1234567890")
        monkeypatch.setenv("GOOGLE_OAUTH_ACCESS_TOKEN", "access-token")
        monkeypatch.setattr(rank_tracker, "_provider_network_enabled", lambda: True)
        monkeypatch.setattr(rank_tracker, "_keyword_provider_cache", {})

        captured = {}

        def fake_http_request(**kwargs):
            captured.update(kwargs)
            return {
                "results": [
                    {"text": "keyword planner one", "keywordIdeaMetrics": {"avgMonthlySearches": 1100}},
                    {"text": "keyword planner two", "keywordIdeaMetrics": {"avgMonthlySearches": 750}},
                ]
            }

        monkeypatch.setattr(rank_tracker, "_http_json_request", fake_http_request)

        keywords = rank_tracker._fetch_provider_keywords(
            provider_key="google_keyword_planner",
            operation="discover",
            payload={"seed_keyword": "social media management", "location": "United States", "language": "en", "max_results": 5},
            tenant_id="tenant-google-ads",
        )["keywords"]

        assert keywords[:2] == ["keyword planner one", "keyword planner two"]
        assert captured["method"] == "POST"
        assert "googleads.googleapis.com" in captured["url"]
        assert captured["headers"]["developer-token"] == "dev-token"
        assert captured["headers"]["Authorization"] == "Bearer access-token"

    def test_google_search_console_adapter(self, monkeypatch):
        monkeypatch.setenv("GSC_SITE_URL", "https://example.com/")
        monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN", "gsc-token")
        monkeypatch.setattr(rank_tracker, "_provider_network_enabled", lambda: True)
        monkeypatch.setattr(rank_tracker, "_keyword_provider_cache", {})

        captured = {}

        def fake_http_request(**kwargs):
            captured.update(kwargs)
            return {
                "rows": [
                    {"keys": ["example keyword"]},
                    {"keys": ["another keyword"]},
                ]
            }

        monkeypatch.setattr(rank_tracker, "_http_json_request", fake_http_request)

        keywords = rank_tracker._fetch_provider_keywords(
            provider_key="google_search_console",
            operation="content_gap",
            payload={"seed_keyword": "example", "location": "United States", "language": "en", "max_results": 5},
            tenant_id="tenant-gsc",
        )["keywords"]

        assert keywords == ["example keyword", "another keyword"]
        assert captured["method"] == "POST"
        assert "searchconsole.googleapis.com" in captured["url"]
        assert captured["headers"]["Authorization"] == "Bearer gsc-token"

    def test_google_language_resolution(self):
        assert rank_tracker._resolve_google_language_constant("en") == "1000"
        assert rank_tracker._resolve_google_language_constant("ja") == "1011"
        assert rank_tracker._resolve_google_language_constant("zz") == "1000"
        assert rank_tracker._resolve_google_language_constant("fr") == "1002"
        assert rank_tracker._resolve_google_language_constant("pt") == "1014"

    def test_google_geo_and_language_mapping(self, monkeypatch):
        assert rank_tracker._google_language_constant("en") == "1000"
        assert rank_tracker._google_language_constant("ja") == "1011"
        assert rank_tracker._google_language_constant("zz") == "1000"
        assert rank_tracker._google_geo_constant("United States") == "2840"
        assert rank_tracker._google_geo_constant("Singapore") == "2702"
        assert rank_tracker._google_geo_constant("United Arab Emirates") == "2784"
        assert rank_tracker._google_geo_constant("Unknownland") is None

        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "dev-token")
        monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "1234567890")
        monkeypatch.setenv("GOOGLE_OAUTH_ACCESS_TOKEN", "access-token")
        monkeypatch.setattr(rank_tracker, "_provider_network_enabled", lambda: True)
        monkeypatch.setattr(rank_tracker, "_keyword_provider_cache", {})

        calls = []

        def fake_http_request(**kwargs):
            calls.append(kwargs)
            if "geoTargetConstants:searchGeoTargetConstants" in kwargs["url"]:
                return {
                    "geoTargetConstantSuggestions": [
                        {"geoTargetConstant": {"resourceName": "geoTargetConstants/9999", "reach": 12345}},
                        {"geoTargetConstant": {"resourceName": "geoTargetConstants/8888", "reach": 100}},
                    ]
                }
            return {"results": [{"text": "fallback geo keyword", "keywordIdeaMetrics": {"avgMonthlySearches": 450}}]}

        monkeypatch.setattr(rank_tracker, "_http_json_request", fake_http_request)

        keywords = rank_tracker._fetch_provider_keywords(
            provider_key="google_keyword_planner",
            operation="discover",
            payload={"seed_keyword": "social media management", "location": "Costa Rica", "language": "en", "max_results": 5},
            tenant_id="tenant-geo-fallback",
        )["keywords"]

        assert keywords[0] == "fallback geo keyword"
        assert any("geoTargetConstants:searchGeoTargetConstants" in call["url"] for call in calls)
        assert any("geoTargetConstants/9999" in str(call.get("json_payload")) for call in calls)

    def test_granular_locale_resolution(self):
        assert rank_tracker._resolve_google_language_constant("en-us") == "1000"
        assert rank_tracker._resolve_google_language_constant("en-gb") == "1000"
        assert rank_tracker._resolve_google_language_constant("zh-hans") == "1013"
        assert rank_tracker._resolve_google_language_constant("zh-hant") == "1013"
        assert rank_tracker._resolve_google_language_constant("pt-br") == "1014"
        assert rank_tracker._resolve_google_language_constant("pt-pt") == "1014"
        assert rank_tracker._resolve_google_language_constant("es-mx") == "1003"
        assert rank_tracker._resolve_google_language_constant("fr-ca") == "1002"
        assert rank_tracker._resolve_google_language_constant("de-at") == "1001"
        assert rank_tracker._resolve_google_language_constant("en_us") == "1000"
        assert rank_tracker._resolve_google_language_constant("zh_cn") == "1013"

    def test_provider_configuration_per_tenant(self):
        cfg1 = rank_tracker._get_provider_config("tenant_1")
        cfg2 = rank_tracker._get_provider_config("tenant_2")
        assert cfg1 is not cfg2
        assert not rank_tracker._provider_configured_for_tenant("tenant_1", "google_keyword_planner")

    def test_oauth_session_creation(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test_client_id")
        r = client.post(
            f"{BASE}/provider-config/init-oauth",
            params={"provider": "google_keyword_planner", "redirect_uri": "http://localhost:3000/callback"},
            headers=H,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["provider"] == "google_keyword_planner"
        assert "auth_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["auth_url"]

    def test_provider_config_status(self):
        r = client.get(
            f"{BASE}/provider-config/status",
            headers=H,
        )
        assert r.status_code == 200
        data = r.json()
        assert "providers" in data
        assert "google_keyword_planner" in data["providers"]
        assert "google_search_console" in data["providers"]

    def test_keyword_research_discover(self):
        r = client.post(
            f"{BASE}/keyword-research/discover",
            json={
                "seed_keyword": "social media management",
                "location": "United States",
                "language": "en",
                "include_questions": True,
                "max_results": 20,
            },
            headers=H,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["seed_keyword"] == "social media management"
        assert len(data["opportunities"]) > 0
        assert len(data["clusters"]) > 0
        assert "providers_used" in data
        assert "provider_attempts" in data
        assert "provider_selected" in data
        assert "provider_strategy" in data
        assert "fallback_used" in data
        assert "fallback_reason" in data
        assert "telemetry" in data
        assert data["provider_strategy"] == "priority_live_then_deterministic_fallback"
        assert data["provider_attempts"]
        assert data["provider_attempts"][-1]["status"] == "success"
        telemetry = data["telemetry"]
        for key in (
            "operation",
            "attempt_count",
            "attempted_live_providers",
            "failed_live_attempts",
            "cache_hits",
            "result_count",
            "provider_latency_total_ms",
            "pipeline_latency_ms",
        ):
            assert key in telemetry, f"Missing telemetry key: {key}"
        assert telemetry["operation"] == "discover"
        assert telemetry["attempt_count"] == len(data["provider_attempts"])
        assert telemetry["result_count"] >= 0

    def test_keyword_research_content_gap(self):
        r = client.post(
            f"{BASE}/keyword-research/content-gap",
            json={
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com", "moz.com"],
                "max_results": 12,
            },
            headers=H,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["your_domain"] == "nuxtron.ai"
        assert len(data["opportunities"]) == 12
        assert "summary" in data
        assert "provider_strategy" in data
        assert "fallback_used" in data
        assert "fallback_reason" in data
        assert "provider_attempts" in data
        assert "telemetry" in data
        assert data["provider_strategy"] == "priority_live_then_deterministic_fallback"
        assert data["provider_attempts"][-1]["status"] == "success"
        telemetry = data["telemetry"]
        assert telemetry["operation"] == "content_gap"
        assert telemetry["attempt_count"] == len(data["provider_attempts"])
        assert "cache_hits" in telemetry
        assert "result_count" in telemetry

    def test_keyword_research_discover_strict_live_provider_required(self, monkeypatch):
        def fake_provider_chain(**_: object):
            return {
                "provider_strategy": "priority_live_then_deterministic_fallback",
                "provider_selected": "nuxtron_synthetic",
                "provider_attempts": [{"provider": "nuxtron_synthetic", "status": "success", "attempted": True}],
                "providers_used": ["nuxtron_synthetic"],
                "fallback_used": True,
                "fallback_reason": "no_live_provider_configured",
                "provider_keywords": ["synthetic keyword"],
                "telemetry": {"operation": "discover"},
            }

        monkeypatch.setattr(rank_tracker, "_run_provider_chain", fake_provider_chain)
        r = client.post(
            f"{BASE}/keyword-research/discover",
            json={
                "seed_keyword": "social media management",
                "location": "United States",
                "language": "en",
                "include_questions": True,
                "max_results": 20,
                "require_live_providers": True,
            },
            headers=H,
        )
        assert r.status_code == 412
        detail = r.json()["detail"]
        assert detail["code"] == "live_provider_required"

    def test_keyword_research_content_gap_strict_live_provider_required(self, monkeypatch):
        def fake_provider_chain(**_: object):
            return {
                "provider_strategy": "priority_live_then_deterministic_fallback",
                "provider_selected": "nuxtron_synthetic",
                "provider_attempts": [{"provider": "nuxtron_synthetic", "status": "success", "attempted": True}],
                "providers_used": ["nuxtron_synthetic"],
                "fallback_used": True,
                "fallback_reason": "no_live_provider_succeeded",
                "provider_keywords": ["synthetic gap keyword"],
                "telemetry": {"operation": "content_gap"},
            }

        monkeypatch.setattr(rank_tracker, "_run_provider_chain", fake_provider_chain)
        r = client.post(
            f"{BASE}/keyword-research/content-gap",
            json={
                "your_domain": "nuxtron.ai",
                "competitor_domains": ["semrush.com", "ahrefs.com", "moz.com"],
                "max_results": 12,
                "require_live_providers": True,
            },
            headers=H,
        )
        assert r.status_code == 412
        detail = r.json()["detail"]
        assert detail["code"] == "live_provider_required"

    # ------------------------------------------------------------------
    # Tenant Isolation
    # ------------------------------------------------------------------

    def test_tenant_isolation_keywords(self):
        kw_name = f"tenant-iso-{uuid.uuid4().hex[:6]}"
        client.post(f"{BASE}/tracked-keywords", json={"keyword": kw_name}, headers=H)
        r2 = client.get(f"{BASE}/tracked-keywords", headers=H2)
        keywords_t2 = [k["keyword"] for k in r2.json()["keywords"]]
        assert kw_name not in keywords_t2

    def test_tenant_isolation_projects(self):
        domain = f"iso-{uuid.uuid4().hex[:6]}.com"
        client.post(f"{BASE}/add-project", json={"domain": domain}, headers=H)
        r2 = client.get(f"{BASE}/projects", headers=H2)
        projects_t2 = [p["domain"] for p in r2.json()["projects"]]
        assert domain not in projects_t2

    def test_tenant_isolation_competitors(self):
        comp = f"iso-{uuid.uuid4().hex[:6]}.com"
        client.post(f"{BASE}/competitors", json={"domain": comp}, headers=H)
        r2 = client.get(f"{BASE}/competitors", headers=H2)
        comps_t2 = [c["domain"] for c in r2.json()["competitors"]]
        assert comp not in comps_t2

    # ------------------------------------------------------------------
    # Auth guards
    # ------------------------------------------------------------------

    def test_all_endpoints_require_auth(self):
        endpoints = [
            ("GET", f"{BASE}/tracked-keywords"),
            ("GET", f"{BASE}/projects"),
            ("GET", f"{BASE}/positions"),
            ("GET", f"{BASE}/competitors"),
            ("GET", f"{BASE}/history"),
            ("GET", f"{BASE}/lost-gained"),
            ("GET", f"{BASE}/visibility-score"),
            ("GET", f"{BASE}/forecasts"),
            ("GET", f"{BASE}/analytics"),
            ("GET", f"{BASE}/alerts"),
            ("GET", f"{BASE}/keyword-research/sources"),
            ("GET", f"{BASE}/keyword-research/vendors"),
        ]
        for method, url in endpoints:
            r = client.request(method, url)
            assert r.status_code in (401, 403, 422), f"{method} {url} should require auth, got {r.status_code}"
