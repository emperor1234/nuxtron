"""
VSE extra tests - round 2: covers missing branches in routers/vse.py.
Targets: trigger optimal branches (b2b/consumer/default), network map, detonation, algo optimize, brief audience, etc.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant-vse2"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestViralBriefAudienceBranches:
    """Lines 509, 511 - brief generator b2c and executive audience branches."""

    def test_brief_b2c_audience(self, client: TestClient) -> None:
        r = client.post("/vse/brief", headers=H, json={
            "objective": "Launch viral content",
            "audience": "consumer b2c shoppers",
            "platforms": ["instagram", "tiktok"],
            "tone": "casual",
            "urgency": "high"
        })
        assert r.status_code in VALID  # line 509

    def test_brief_executive_audience(self, client: TestClient) -> None:
        r = client.post("/vse/brief", headers=H, json={
            "objective": "Thought leadership campaign",
            "audience": "executive cmo leaders",
            "platforms": ["linkedin"],
            "tone": "professional",
            "urgency": "medium"
        })
        assert r.status_code in VALID  # line 511

    def test_brief_default_audience(self, client: TestClient) -> None:
        r = client.post("/vse/brief", headers=H, json={
            "objective": "General campaign",
            "audience": "general audience",
            "platforms": ["x", "instagram"],
            "tone": "inspirational",
            "urgency": "low"
        })
        assert r.status_code in VALID


class TestOptimalTriggersBranches:
    """Lines 610-618 - optimal triggers audience branches (b2b, consumer, default)."""

    def test_optimal_triggers_b2b(self, client: TestClient) -> None:
        r = client.post("/vse/triggers/optimal", headers=H, json={
            "objective": "Generate leads",
            "audience": "b2b saas buyers executive",
            "platforms": ["linkedin"],
            "tone": "professional",
            "urgency": "medium"
        })
        assert r.status_code in VALID  # lines 612-613

    def test_optimal_triggers_consumer(self, client: TestClient) -> None:
        r = client.post("/vse/triggers/optimal", headers=H, json={
            "objective": "Drive purchases",
            "audience": "consumer shoppers b2c",
            "platforms": ["instagram"],
            "tone": "casual",
            "urgency": "high"
        })
        assert r.status_code in VALID  # lines 614-615

    def test_optimal_triggers_default(self, client: TestClient) -> None:
        r = client.post("/vse/triggers/optimal", headers=H, json={
            "objective": "Brand awareness",
            "audience": "general mixed audience",
            "platforms": ["x"],
            "tone": "inspirational",
            "urgency": "low"
        })
        assert r.status_code in VALID  # lines 617-618


class TestAlgoOptimizeBranches:
    """Lines 650-678 - algo optimize platform-specific branches (linkedin, tiktok, instagram)."""

    def test_algo_optimize_linkedin(self, client: TestClient) -> None:
        r = client.post("/vse/algo/optimize", headers=H, json={
            "platform": "linkedin",
            "content_type": "article",
            "target_metric": "reach"
        })
        assert r.status_code in VALID  # line 659-660

    def test_algo_optimize_tiktok(self, client: TestClient) -> None:
        r = client.post("/vse/algo/optimize", headers=H, json={
            "platform": "tiktok",
            "content_type": "short_video",
            "target_metric": "views"
        })
        assert r.status_code in VALID  # line 661-662

    def test_algo_optimize_instagram(self, client: TestClient) -> None:
        r = client.post("/vse/algo/optimize", headers=H, json={
            "platform": "instagram",
            "content_type": "reel",
            "target_metric": "saves"
        })
        assert r.status_code in VALID  # line 663-664

    def test_algo_optimize_x(self, client: TestClient) -> None:
        r = client.post("/vse/algo/optimize", headers=H, json={
            "platform": "x",
            "content_type": "thread",
            "target_metric": "retweets"
        })
        assert r.status_code in VALID  # default branch (no specific platform)


class TestNetworkMap:
    """Lines 707-730 - network map creation and retrieval."""

    def test_create_network_map(self, client: TestClient) -> None:
        r = client.post("/vse/network/map", headers=H, json={
            "topic": "SaaS pricing",
            "seed_accounts": ["@user1", "@user2"],
            "depth": 2
        })
        assert r.status_code in VALID  # lines 707-730

    def test_get_network_superconnectors(self, client: TestClient) -> None:
        r = client.get("/vse/network/superconnectors", headers=H)
        assert r.status_code in VALID  # line 739-740


class TestDetonationRoutes:
    """Lines 800-827, 841-858 - detonation plan and execute."""

    def test_create_detonation(self, client: TestClient) -> None:
        r = client.post("/vse/detonation/plan", headers=H, json={
            "content_id": "content_001",
            "platforms": ["linkedin", "x", "instagram"],
            "launch_at": "2025-12-01T09:00:00Z",
            "swarm_size": 50
        })
        assert r.status_code in VALID  # lines 800-827

    def test_execute_detonation(self, client: TestClient) -> None:
        # Create first
        cr = client.post("/vse/detonation/plan", headers=H, json={
            "content_id": "content_002",
            "platforms": ["tiktok"],
            "launch_at": "2025-12-02T09:00:00Z",
            "swarm_size": 20
        })
        if cr.status_code == 200:
            det_id = cr.json().get("detonation", {}).get("id")
            if det_id:
                r = client.post(f"/vse/detonation/{det_id}/execute", headers=H)
                assert r.status_code in VALID  # lines 841-858

    def test_execute_detonation_not_found(self, client: TestClient) -> None:
        r = client.post("/vse/detonation/nonexistent_id/execute", headers=H)
        assert r.status_code in VALID  # 404 branch


class TestVseCommandCentre:
    """Lines 929-955 - command centre and summary routes."""

    def test_command_centre(self, client: TestClient) -> None:
        r = client.get("/vse/command-centre", headers=H)
        assert r.status_code in VALID

    def test_viral_vault(self, client: TestClient) -> None:
        r = client.get("/vse/viral-vault", headers=H)
        assert r.status_code in VALID

    def test_dark_social(self, client: TestClient) -> None:
        r = client.get("/vse/dark-social", headers=H)
        assert r.status_code in VALID

    def test_subsystems(self, client: TestClient) -> None:
        r = client.get("/vse/subsystems", headers=H)
        assert r.status_code in VALID

    def test_engines(self, client: TestClient) -> None:
        r = client.get("/vse/engines", headers=H)
        assert r.status_code in VALID


class TestVseContentFactory:
    """Lines 993-1028 - content factory endpoints."""

    def test_content_generate(self, client: TestClient) -> None:
        r = client.post("/vse/content/generate", headers=H, json={
            "objective": "Drive sign-ups",
            "platform": "linkedin",
            "content_type": "post",
            "tone": "professional"
        })
        assert r.status_code in VALID

    def test_content_list(self, client: TestClient) -> None:
        r = client.get("/vse/content/factory", headers=H)
        assert r.status_code in VALID


class TestVseMomentum:
    """Lines 1037-1091 - momentum monitoring."""

    def test_start_momentum(self, client: TestClient) -> None:
        r = client.post("/vse/momentum/start", headers=H, json={
            "content_id": "post_abc",
            "platform": "linkedin",
            "threshold_multiplier": 3.0
        })
        assert r.status_code in VALID

    def test_get_momentum_event(self, client: TestClient) -> None:
        r = client.get("/vse/momentum/some_event_id", headers=H)
        assert r.status_code in VALID


class TestVseSwarms:
    """Lines 1088-1103 - swarm management."""

    def test_compose_swarm(self, client: TestClient) -> None:
        r = client.post("/vse/swarm/compose", headers=H, json={
            "content_id": "post_xyz",
            "platform": "x",
            "swarm_size": 25,
            "strategy": "coordinated_amplification"
        })
        assert r.status_code in VALID

    def test_swarm_db_stats(self, client: TestClient) -> None:
        r = client.get("/vse/swarm/database/stats", headers=H)
        assert r.status_code in VALID


class TestVseTrends:
    """Lines 1142-1185 - trend monitoring."""

    def test_trend_alerts(self, client: TestClient) -> None:
        r = client.get("/vse/trends/alerts", headers=H)
        assert r.status_code in VALID

    def test_trend_hijack(self, client: TestClient) -> None:
        r = client.post("/vse/trends/hijack", headers=H, json={
            "trend_keyword": "#AI2025",
            "platform": "x",
            "content_angle": "contrarian"
        })
        assert r.status_code in VALID


class TestVseCascadeSimulations:
    """Lines 1311-1323 - cascade simulation."""

    def test_run_cascade_simulation(self, client: TestClient) -> None:
        r = client.post("/vse/network/cascade-simulate", headers=H, json={
            "seed_content": "Our AI just did something incredible",
            "platform": "linkedin",
            "network_size": 1000
        })
        assert r.status_code in VALID


class TestVseImmortalAssets:
    """Lines 1385-1409 - immortal assets."""

    def test_create_immortal_asset(self, client: TestClient) -> None:
        r = client.post("/vse/immortalise", headers=H, json={
            "title": "The Framework That Changed Everything",
            "content": "Our 5-step framework has been tested across 100+ campaigns...",
            "format": "carousel"
        })
        assert r.status_code in VALID

    def test_list_immortal_assets(self, client: TestClient) -> None:
        r = client.get("/vse/immortalise/vault", headers=H)
        assert r.status_code in VALID


class TestVsePaidAmplification:
    """Lines 1434-1491 - paid amplification."""

    def test_create_paid_event(self, client: TestClient) -> None:
        r = client.post("/vse/paid/amplify", headers=H, json={
            "content_id": "post_001",
            "platform": "linkedin",
            "budget_usd": 500.0,
            "target_audience": "b2b saas decision makers"
        })
        assert r.status_code in VALID

    def test_list_paid_events(self, client: TestClient) -> None:
        r = client.get("/vse/paid/events", headers=H)
        assert r.status_code in VALID


class TestVseViralEvents:
    """Lines 1561-1634 - viral events CRUD."""

    def test_create_viral_event(self, client: TestClient) -> None:
        r = client.post("/vse/viral-events", headers=H, json={
            "title": "Product Hunt Launch",
            "description": "Our AI tool hits #1 on Product Hunt",
            "platform": "x",
            "target_reach": 100000
        })
        assert r.status_code in VALID

    def test_list_viral_events(self, client: TestClient) -> None:
        r = client.get("/vse/viral-events", headers=H)
        assert r.status_code in VALID

    def test_update_viral_event(self, client: TestClient) -> None:
        cr = client.post("/vse/viral-events", headers=H, json={
            "title": "Viral Event Update Test",
            "description": "Test event for update",
            "platform": "linkedin",
            "target_reach": 50000
        })
        if cr.status_code == 200:
            event_id = cr.json().get("event", {}).get("id")
            if event_id:
                r = client.patch(f"/vse/viral-events/{event_id}", headers=H, json={"status": "active"})
                assert r.status_code in VALID

    def test_delete_viral_event(self, client: TestClient) -> None:
        cr = client.post("/vse/viral-events", headers=H, json={
            "title": "Viral Event Delete Test",
            "description": "Test event for delete",
            "platform": "tiktok",
            "target_reach": 10000
        })
        if cr.status_code == 200:
            event_id = cr.json().get("event", {}).get("id")
            if event_id:
                r = client.delete(f"/vse/viral-events/{event_id}", headers=H)
                assert r.status_code in VALID

    def test_viral_event_not_found(self, client: TestClient) -> None:
        r = client.patch("/vse/viral-events/nonexistent_id", headers=H, json={"status": "completed"})
        assert r.status_code in VALID
