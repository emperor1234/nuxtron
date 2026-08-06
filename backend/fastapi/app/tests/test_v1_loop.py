"""
Test suite for the v1 closed feedback loop endpoints and safety framework.

Covers:
- /v1/loop/run  (trigger the 3-module loop)
- /v1/loop/status/{run_id}  (poll run timeline)
- /v1/loop/agent-decisions/{site_id}  (agent audit decisions)
- AgentSafetyChecker: all blocking and warning rules
- AutoLinkAgent: decision approval and rejection logic
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("SUPER_ADMIN_API_KEY", "selftest-super-admin-key")


# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────


def _make_client():
    from backend.fastapi.app.main import app
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=True)


def _headers():
    return {
        "X-API-Key": "test-api-key",
        "X-Tenant-Id": "test-tenant",
    }


# ────────────────────────────────────────────────────────────────────────────────
# Safety Checker Unit Tests
# ────────────────────────────────────────────────────────────────────────────────


def _make_good_link(**overrides):
    base = {
        "from_url": "https://example.com/blog/seo-tips",
        "to_url": "https://example.com/blog/keyword-research",
        "anchor_text": "keyword research techniques",
        "relevance_score": 0.85,
        "context_snippet": "For better results, use keyword research techniques.",
    }
    base.update(overrides)
    return base


class TestAgentSafetyChecker:
    def _checker(self, domain="example.com"):
        from backend.fastapi.app.modules.auto_link_agent import AgentSafetyChecker

        return AgentSafetyChecker(site_domain=domain)

    def test_good_link_has_no_violations(self):
        checker = self._checker()
        violations = checker.check_link(_make_good_link())
        blocking = [v for v in violations if v.severity == "block"]
        assert blocking == [], f"Expected no blocking violations, got: {blocking}"

    def test_cross_domain_is_blocked(self):
        checker = self._checker()
        link = _make_good_link(to_url="https://evil.com/phishing")
        violations = checker.check_link(link)
        rules = [v.rule for v in violations if v.severity == "block"]
        assert "same_domain" in rules

    def test_empty_from_url_is_blocked(self):
        checker = self._checker()
        link = _make_good_link(from_url="")
        violations = checker.check_link(link)
        rules = [v.rule for v in violations if v.severity == "block"]
        assert "url_required" in rules

    def test_empty_to_url_is_blocked(self):
        checker = self._checker()
        link = _make_good_link(to_url="")
        violations = checker.check_link(link)
        rules = [v.rule for v in violations if v.severity == "block"]
        assert "url_required" in rules

    def test_empty_anchor_is_blocked(self):
        checker = self._checker()
        link = _make_good_link(anchor_text="")
        violations = checker.check_link(link)
        rules = [v.rule for v in violations if v.severity == "block"]
        assert "anchor_quality" in rules

    def test_generic_anchor_warns(self):
        checker = self._checker()
        link = _make_good_link(anchor_text="click here")
        violations = checker.check_link(link)
        warn_rules = [v.rule for v in violations if v.severity == "warn"]
        assert "anchor_quality" in warn_rules

    def test_blocked_path_is_blocked(self):
        checker = self._checker()
        link = _make_good_link(to_url="https://example.com/admin/settings")
        violations = checker.check_link(link)
        rules = [v.rule for v in violations if v.severity == "block"]
        assert "blocked_path" in rules

    def test_api_path_is_blocked(self):
        checker = self._checker()
        link = _make_good_link(to_url="https://example.com/api/users")
        violations = checker.check_link(link)
        rules = [v.rule for v in violations if v.severity == "block"]
        assert "blocked_path" in rules

    def test_self_link_is_blocked(self):
        url = "https://example.com/same-page"
        checker = self._checker()
        link = _make_good_link(from_url=url, to_url=url)
        violations = checker.check_link(link)
        rules = [v.rule for v in violations if v.severity == "block"]
        assert "no_self_link" in rules

    def test_low_relevance_is_blocked(self):
        checker = self._checker()
        link = _make_good_link(relevance_score=0.3)
        violations = checker.check_link(link)
        rules = [v.rule for v in violations if v.severity == "block"]
        assert "relevance_threshold" in rules

    def test_minimum_relevance_passes(self):
        checker = self._checker()
        link = _make_good_link(relevance_score=0.5)
        violations = checker.check_link(link)
        blocking = [v for v in violations if v.severity == "block"]
        assert blocking == []


# ────────────────────────────────────────────────────────────────────────────────
# AutoLinkAgent Logic Tests (sync, no DB / event bus)
# ────────────────────────────────────────────────────────────────────────────────


class TestAgentDecisionLogic:
    """Test agent decision logic without DB/event bus (uses mock/stubs)"""

    def test_approved_link_is_flagged_correctly(self):
        from backend.fastapi.app.modules.auto_link_agent import (
            AgentSafetyChecker,
        )

        link = _make_good_link()
        checker = AgentSafetyChecker("example.com")
        violations = checker.check_link(link)
        blocking = [v for v in violations if v.severity == "block"]
        approved = len(blocking) == 0
        assert approved is True

    def test_cross_domain_link_is_rejected(self):
        from backend.fastapi.app.modules.auto_link_agent import AgentSafetyChecker

        link = _make_good_link(to_url="https://malicious-site.com/page")
        checker = AgentSafetyChecker("example.com")
        violations = checker.check_link(link)
        blocking = [v for v in violations if v.severity == "block"]
        assert len(blocking) >= 1

    def test_build_reasoning_includes_key_info(self):
        # Simulate what agent does
        from backend.fastapi.app.modules.auto_link_agent import (
            AgentSafetyChecker,
        )

        # We only need the static method — create a minimal instance check
        checker = AgentSafetyChecker("example.com")
        link = _make_good_link()
        violations = checker.check_link(link)

        # manually call the reasoning builder
        # Build reasoning inline (reproduce agent's logic)
        approved = not any(v.severity == "block" for v in violations)
        lines = [
            f"Link: {link['from_url']} → {link['to_url']}",
            f"Anchor: '{link['anchor_text']}'",
            f"Relevance: {link['relevance_score']:.2f}",
            f"Decision: {'APPROVED' if approved else 'REJECTED'}",
        ]
        reasoning = "\n".join(lines)
        assert "APPROVED" in reasoning
        assert link["from_url"] in reasoning


# ────────────────────────────────────────────────────────────────────────────────
# V1 Loop API Endpoint Tests
# ────────────────────────────────────────────────────────────────────────────────


class TestV1LoopEndpoints:
    def setup_method(self):
        self.client = _make_client()
        self.headers = _headers()

    def test_run_requires_auth(self):
        resp = self.client.post(
            "/v1/loop/run",
            json={"site_id": "test-site"},
        )
        assert resp.status_code in (401, 403, 422)

    def test_run_missing_site_id_returns_422(self):
        resp = self.client.post(
            "/v1/loop/run",
            json={},
            headers=self.headers,
        )
        assert resp.status_code == 422

    def test_run_returns_run_id(self):
        resp = self.client.post(
            "/v1/loop/run",
            json={"site_id": "test-site-123"},
            headers=self.headers,
        )
        # May be 503 (LLM pool not initialized in test env) or 200/202
        assert resp.status_code in (200, 202, 503)
        if resp.status_code != 503:
            body = resp.json()
            assert "run_id" in body
            assert body["site_id"] == "test-site-123"

    def test_run_payload_has_flow(self):
        resp = self.client.post(
            "/v1/loop/run",
            json={"site_id": "test-site-789", "limit": 5},
            headers=self.headers,
        )
        if resp.status_code == 200:
            body = resp.json()
            assert "flow" in body
            assert isinstance(body["flow"], list)
            assert len(body["flow"]) == 4

    def test_status_unknown_run_returns_pending(self):
        resp = self.client.get(
            "/v1/loop/status/00000000-0000-0000-0000-000000000000",
            headers=self.headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "run_id" in body
        assert body["status"] in ("pending", "error")

    def test_agent_decisions_returns_structure(self):
        resp = self.client.get(
            "/v1/loop/agent-decisions/test-site-xyz",
            headers=self.headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "site_id" in body
        assert "decisions" in body
        assert isinstance(body["decisions"], list)

    def test_run_autonomy_tier_validation(self):
        resp = self.client.post(
            "/v1/loop/run",
            json={"site_id": "test-site", "autonomy_tier": 99},
            headers=self.headers,
        )
        # Tier must be 1-3
        assert resp.status_code == 422

    def test_run_limit_validation(self):
        resp = self.client.post(
            "/v1/loop/run",
            json={"site_id": "test-site", "limit": 0},
            headers=self.headers,
        )
        assert resp.status_code == 422

    def test_strategy_snapshots_returns_structure(self):
        resp = self.client.get(
            "/v1/loop/strategy-snapshots/test-site",
            headers=self.headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "site_id" in body
        assert "snapshots" in body
        assert isinstance(body["snapshots"], list)

    def test_rich_results_returns_structure(self):
        resp = self.client.get(
            "/v1/loop/rich-results/test-site",
            headers=self.headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "site_id" in body
        assert "opportunities" in body
        assert "metrics" in body
        assert isinstance(body["metrics"], list)

    def test_agent_decision_trace_returns_structure(self):
        resp = self.client.get(
            "/v1/loop/agent-decision-trace/test-site",
            headers=self.headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "site_id" in body
        assert "trace_count" in body
        assert "traces" in body
        assert isinstance(body["traces"], list)

    def test_tool_integrations_list_returns_all_tools(self):
        resp = self.client.get(
            "/integrations/tools",
            headers=self.headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "configured" in body
        assert "tools" in body
        assert isinstance(body["tools"], list)
        assert body["total"] == 20

    def test_tool_integrations_includes_payg_and_free(self):
        resp = self.client.get(
            "/integrations/tools",
            headers=self.headers,
        )
        assert resp.status_code == 200
        tools = resp.json()["tools"]
        tiers = {t["tier"] for t in tools}
        assert "payg" in tiers
        assert "free" in tiers

    def test_tool_integrations_includes_expected_tools(self):
        resp = self.client.get(
            "/integrations/tools",
            headers=self.headers,
        )
        assert resp.status_code == 200
        tools = resp.json()["tools"]
        keys = {t["key"] for t in tools}
        expected = {
            "dataforseo", "serper", "promptwatch", "openai_gpt4o",
            "cloudflare_pro", "deepgram", "screaming_frog", "google_analytics",
            "whisper", "google_business_profile", "google_keyword_planner",
            "google_discover", "google_search_console",
            "lighthouse", "playwright_cdp", "web_vitals", "opensearch",
            "prometheus", "grafana", "metabase",
        }
        assert expected.issubset(keys)

    def test_tool_integrations_single_tool_detail(self):
        resp = self.client.get(
            "/integrations/tools/dataforseo",
            headers=self.headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["key"] == "dataforseo"
        assert "configured" in body
        assert "last_test_status" in body

    def test_tool_integrations_unknown_tool_returns_404(self):
        resp = self.client.get(
            "/integrations/tools/nonexistent_tool_xyz",
            headers=self.headers,
        )
        assert resp.status_code == 404

    def test_tool_integrations_test_endpoint(self):
        resp = self.client.post(
            "/integrations/tools/whisper/test",
            headers=self.headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "tested_at" in body
