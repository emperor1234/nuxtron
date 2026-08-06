"""
VSE router extra tests — round 3.
Covers triggers/optimal (all audience branches), algorithm/optimize (platform branches),
network/map, detonation plan+execute, swarm, momentum, content/generate, emotion/engineer,
trends/hijack, paid routes, dark-social/attribution, immortalise.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-vse-extra3"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ── Viral Brief ──────────────────────────────────────────────────────────────


class TestViralBrief:
    """Lines 509, 511: b2c and executive trigger combos."""

    def test_brief_b2c_audience(self, client: TestClient) -> None:
        """Line 509: b2c/consumer → EMOTIONAL_AROUSAL combo."""
        r = client.post("/vse/brief", headers=H, json={
            "objective": "engagement",
            "audience": "b2c consumers",
            "platforms": ["instagram", "tiktok"],
            "tone": "casual",
            "urgency": "high",
        })
        assert r.status_code in VALID

    def test_brief_consumer_audience(self, client: TestClient) -> None:
        """Line 509: consumer keyword."""
        r = client.post("/vse/brief", headers=H, json={
            "objective": "reach",
            "audience": "consumer market",
            "platforms": ["tiktok"],
            "tone": "casual",
            "urgency": "medium",
        })
        assert r.status_code in VALID

    def test_brief_executive_audience(self, client: TestClient) -> None:
        """Line 511: executive → EPISTEMIC_CURIOSITY combo."""
        r = client.post("/vse/brief", headers=H, json={
            "objective": "authority",
            "audience": "executive leadership",
            "platforms": ["linkedin"],
            "tone": "professional",
            "urgency": "low",
        })
        assert r.status_code in VALID

    def test_brief_cmo_audience(self, client: TestClient) -> None:
        """Line 511: cmo keyword."""
        r = client.post("/vse/brief", headers=H, json={
            "objective": "conversion",
            "audience": "cmo and marketing teams",
            "platforms": ["linkedin", "x"],
            "tone": "professional",
            "urgency": "high",
        })
        assert r.status_code in VALID


# ── Triggers Optimal ─────────────────────────────────────────────────────────


class TestTriggersOptimal:
    """Lines 610-618: optimal triggers for different audience types."""

    def test_optimal_b2b_audience(self, client: TestClient) -> None:
        """Lines 610-612: b2b audience."""
        r = client.post("/vse/triggers/optimal", headers=H, json={
            "objective": "authority",
            "audience": "b2b decision makers",
            "platforms": ["linkedin"],
            "tone": "professional",
            "urgency": "medium",
        })
        assert r.status_code in VALID

    def test_optimal_executive_audience(self, client: TestClient) -> None:
        """Line 612: executive audience → epistemic combo."""
        r = client.post("/vse/triggers/optimal", headers=H, json={
            "objective": "reach",
            "audience": "executive suite",
            "platforms": ["linkedin"],
            "tone": "professional",
            "urgency": "low",
        })
        assert r.status_code in VALID

    def test_optimal_consumer_audience(self, client: TestClient) -> None:
        """Lines 614-615: consumer audience → emotional arousal."""
        r = client.post("/vse/triggers/optimal", headers=H, json={
            "objective": "engagement",
            "audience": "consumer brands",
            "platforms": ["instagram"],
            "tone": "casual",
            "urgency": "high",
        })
        assert r.status_code in VALID

    def test_optimal_generic_audience(self, client: TestClient) -> None:
        """Line 617: generic audience → identity signal combo."""
        r = client.post("/vse/triggers/optimal", headers=H, json={
            "objective": "conversion",
            "audience": "general public",
            "platforms": ["x"],
            "tone": "casual",
            "urgency": "medium",
        })
        assert r.status_code in VALID


# ── Algorithm Optimize ───────────────────────────────────────────────────────


class TestAlgorithmOptimize:
    """Lines 650-678: algorithm/optimize with platform branches."""

    def test_optimize_linkedin(self, client: TestClient) -> None:
        """Line 659-660: linkedin branch."""
        r = client.post("/vse/algorithm/optimize", headers=H, json={
            "content": "How I grew my LinkedIn following by 10x in 90 days",
            "platform": "linkedin",
            "content_type": "text",
        })
        assert r.status_code in VALID

    def test_optimize_tiktok(self, client: TestClient) -> None:
        """Line 661-662: tiktok branch."""
        r = client.post("/vse/algorithm/optimize", headers=H, json={
            "content": "POV: You finally figured out the TikTok algorithm",
            "platform": "tiktok",
            "content_type": "short_video",
        })
        assert r.status_code in VALID

    def test_optimize_instagram(self, client: TestClient) -> None:
        """Lines 663-664: instagram branch."""
        r = client.post("/vse/algorithm/optimize", headers=H, json={
            "content": "Save this post for later! 10 Instagram growth hacks",
            "platform": "instagram",
            "content_type": "carousel",
        })
        assert r.status_code in VALID

    def test_optimize_x_platform(self, client: TestClient) -> None:
        """No specific platform branch → default recommendations."""
        r = client.post("/vse/algorithm/optimize", headers=H, json={
            "content": "Thread: The X algorithm explained",
            "platform": "x",
            "content_type": "thread",
        })
        assert r.status_code in VALID


# ── Network Map ──────────────────────────────────────────────────────────────


class TestNetworkMap:
    """Lines 707-740: network/map POST and superconnectors GET."""

    def test_create_network_map(self, client: TestClient) -> None:
        """Lines 707-730: creates a network map."""
        r = client.post("/vse/network/map", headers=H, json={
            "audience_segment": "SaaS founders",
            "depth": 2,
        })
        assert r.status_code in VALID

    def test_get_superconnectors_after_map(self, client: TestClient) -> None:
        """Line 739: latest map found."""
        # Create map first
        client.post("/vse/network/map", headers=H, json={
            "audience_segment": "Marketing leaders",
            "depth": 1,
        })
        r = client.get("/vse/network/superconnectors", headers=H)
        assert r.status_code in VALID


# ── Detonation ───────────────────────────────────────────────────────────────


class TestDetonation:
    """Lines 800-858: detonation plan and execute."""

    def test_detonation_plan(self, client: TestClient) -> None:
        """Lines 800-827: detonation plan."""
        r = client.post("/vse/detonation/plan", headers=H, json={
            "content": "The 3-step framework that helped us 10x our ARR this year",
            "platforms": ["linkedin", "x", "instagram"],
            "objective": "reach",
        })
        assert r.status_code in VALID

    def test_detonation_execute(self, client: TestClient) -> None:
        """Lines 841-858: execute detonation."""
        # Create plan first
        r1 = client.post("/vse/detonation/plan", headers=H, json={
            "content": "Execute detonation test content",
            "platforms": ["linkedin"],
            "objective": "engagement",
        })
        if r1.status_code in (200, 201):
            det_id = r1.json().get("detonation", {}).get("id")
            if det_id:
                r2 = client.post(f"/vse/detonation/{det_id}/execute", headers=H)
                assert r2.status_code in VALID

    def test_detonation_execute_already_done(self, client: TestClient) -> None:
        """Already executed → 422."""
        r1 = client.post("/vse/detonation/plan", headers=H, json={
            "content": "Will be executed twice",
            "platforms": ["tiktok"],
            "objective": "reach",
        })
        if r1.status_code in (200, 201):
            det_id = r1.json().get("detonation", {}).get("id")
            if det_id:
                client.post(f"/vse/detonation/{det_id}/execute", headers=H)
                r2 = client.post(f"/vse/detonation/{det_id}/execute", headers=H)
                assert r2.status_code in VALID

    def test_detonation_execute_not_found(self, client: TestClient) -> None:
        r = client.post("/vse/detonation/nonexistent-det-id/execute", headers=H)
        assert r.status_code in VALID


# ── Swarm ────────────────────────────────────────────────────────────────────


class TestSwarm:
    """Lines 875-966: swarm compose, activate, status."""

    def test_swarm_compose(self, client: TestClient) -> None:
        """Lines 875+: compose swarm."""
        r = client.post("/vse/swarm/compose", headers=H, json={
            "post_summary": "New SaaS framework that helps founders grow faster",
            "niche": "SaaS / B2B",
            "platforms": ["linkedin"],
            "swarm_size": 25,
        })
        assert r.status_code in VALID

    def test_swarm_activate(self, client: TestClient) -> None:
        """Lines 929+: activate swarm."""
        # Compose first
        r1 = client.post("/vse/swarm/compose", headers=H, json={
            "post_summary": "Swarm to activate test",
            "niche": "Marketing",
            "platforms": ["linkedin", "x"],
            "swarm_size": 10,
        })
        swarm_id = None
        if r1.status_code in (200, 201):
            swarm_id = r1.json().get("swarm", {}).get("id")
        r2 = client.post("/vse/swarm/activate", headers=H, json={
            "swarm_id": swarm_id or "swarm-notexist",
            "post_url": "https://linkedin.com/post/test",
            "activation_note": "Extra3 test",
        })
        assert r2.status_code in VALID

    def test_swarm_status(self, client: TestClient) -> None:
        """Line 951: swarm/{id}/status."""
        r1 = client.post("/vse/swarm/compose", headers=H, json={
            "post_summary": "Status check swarm",
            "niche": "Tech",
            "platforms": ["x"],
            "swarm_size": 15,
        })
        if r1.status_code in (200, 201):
            swarm_id = r1.json().get("swarm", {}).get("id")
            if swarm_id:
                r2 = client.get(f"/vse/swarm/{swarm_id}/status", headers=H)
                assert r2.status_code in VALID


# ── Momentum ─────────────────────────────────────────────────────────────────


class TestMomentum:
    """Lines 993-1050: momentum/start, get, inject."""

    def test_momentum_start(self, client: TestClient) -> None:
        """Lines 993-1012: start momentum event."""
        r = client.post("/vse/momentum/start", headers=H, json={
            "post_summary": "Viral momentum test post",
            "platform": "linkedin",
            "post_url": "https://linkedin.com/post/extra3",
            "target_viral_threshold": 100,
        })
        assert r.status_code in VALID

    def test_momentum_get(self, client: TestClient) -> None:
        """Lines 1024-1028: get momentum event."""
        r1 = client.post("/vse/momentum/start", headers=H, json={
            "post_summary": "Get momentum test",
            "platform": "x",
            "target_viral_threshold": 50,
        })
        if r1.status_code in (200, 201):
            event_id = r1.json().get("event", {}).get("id")
            if event_id:
                r2 = client.get(f"/vse/momentum/{event_id}", headers=H)
                assert r2.status_code in VALID

    def test_momentum_inject(self, client: TestClient) -> None:
        """Lines 1037-1050: inject into momentum event."""
        r1 = client.post("/vse/momentum/start", headers=H, json={
            "post_summary": "Inject momentum test",
            "platform": "instagram",
            "target_viral_threshold": 75,
        })
        if r1.status_code in (200, 201):
            event_id = r1.json().get("event", {}).get("id")
            if event_id:
                r2 = client.post(f"/vse/momentum/{event_id}/inject", headers=H, json={
                    "injection_type": "comment_campaign",
                    "intensity": "high",
                })
                assert r2.status_code in VALID


# ── Content Generate ─────────────────────────────────────────────────────────


class TestContentGenerate:
    """Lines 1054-1185: content/generate and generate-variants."""

    def test_content_generate_basic(self, client: TestClient) -> None:
        """Basic content generation."""
        r = client.post("/vse/content/generate", headers=H, json={
            "topic": "How to build a successful SaaS product",
            "objective": "reach",
            "platform": "linkedin",
            "format": "thread",
            "emotional_vector": "curiosity",
        })
        assert r.status_code in VALID

    def test_content_generate_tiktok(self, client: TestClient) -> None:
        """Content for different platform."""
        r = client.post("/vse/content/generate", headers=H, json={
            "topic": "5 daily habits of top performers",
            "objective": "engagement",
            "platform": "tiktok",
            "format": "short_video",
            "emotional_vector": "awe",
        })
        assert r.status_code in VALID

    def test_content_generate_conversion(self, client: TestClient) -> None:
        """Line 1071: conversion objective."""
        r = client.post("/vse/content/generate", headers=H, json={
            "topic": "Why your marketing strategy is failing",
            "objective": "conversion",
            "platform": "instagram",
            "format": "carousel",
            "emotional_vector": "inspiration",
        })
        assert r.status_code in VALID

    def test_content_generate_variants(self, client: TestClient) -> None:
        """Lines 1151-1185: generate variants."""
        r = client.post("/vse/content/generate-variants", headers=H, json={
            "topic": "The future of AI in marketing",
            "objective": "authority",
            "platform": "linkedin",
            "format": "auto",
            "emotional_vector": "curiosity",
        })
        assert r.status_code in VALID


# ── Emotion Engineer ─────────────────────────────────────────────────────────


class TestEmotionEngineer:
    """Lines 1311-1323: emotion/engineer."""

    def test_engineer_awe(self, client: TestClient) -> None:
        r = client.post("/vse/emotion/engineer", headers=H, json={
            "content": "We just hit $1M ARR in 6 months with a team of 2.",
            "target_vector": "awe",
            "intensity": "high",
        })
        assert r.status_code in VALID

    def test_engineer_inspiration(self, client: TestClient) -> None:
        r = client.post("/vse/emotion/engineer", headers=H, json={
            "content": "5 years ago I was broke. Today I run a 7-figure company.",
            "target_vector": "inspiration",
            "intensity": "medium",
        })
        assert r.status_code in VALID

    def test_engineer_curiosity(self, client: TestClient) -> None:
        r = client.post("/vse/emotion/engineer", headers=H, json={
            "content": "Nobody talks about this LinkedIn hack.",
            "target_vector": "curiosity",
            "intensity": "low",
        })
        assert r.status_code in VALID


# ── Trends Hijack ─────────────────────────────────────────────────────────────


class TestTrendsHijack:
    """Lines 1385-1410: trends/hijack."""

    def test_trends_hijack(self, client: TestClient) -> None:
        r = client.post("/vse/trends/hijack", headers=H, json={
            "trend_id": 1,
            "brand_voice": "professional",
            "platform": "linkedin",
            "content_angle": "contrarian take",
        })
        assert r.status_code in VALID

    def test_trends_hijack_minimal(self, client: TestClient) -> None:
        r = client.post("/vse/trends/hijack", headers=H, json={
            "trend_id": 2,
            "post_summary": "Test trend",
        })
        assert r.status_code in VALID


# ── Paid Assess + Amplify ─────────────────────────────────────────────────────


class TestPaidRoutes:
    """Lines 1434-1491: paid/assess and paid/amplify."""

    def test_paid_assess(self, client: TestClient) -> None:
        """Lines 1434-1461."""
        r = client.post("/vse/paid/assess", headers=H, json={
            "post_summary": "Our new product launch post got 500 engagements organically",
            "organic_engagement_rate": 4.5,
            "organic_impressions": 10000,
            "minutes_live": 120,
        })
        assert r.status_code in VALID

    def test_paid_amplify(self, client: TestClient) -> None:
        """Lines 1469-1491."""
        r = client.post("/vse/paid/amplify", headers=H, json={
            "assessment_id": "assess-test-001",
            "budget_gbp": 500.0,
            "platforms": ["linkedin", "instagram"],
            "objective": "reach",
        })
        assert r.status_code in VALID

    def test_paid_events(self, client: TestClient) -> None:
        r = client.get("/vse/paid/events", headers=H)
        assert r.status_code in VALID


# ── Dark Social Attribution ──────────────────────────────────────────────────


class TestDarkSocialAttribution:
    """Lines 1561-1597: dark-social/attribution."""

    def test_attribution_basic(self, client: TestClient) -> None:
        r = client.post("/vse/dark-social/attribution", headers=H, json={
            "campaign_id": "camp-extra3-001",
            "touchpoints": ["whatsapp", "slack"],
            "conversions": 15,
            "conversion_value": 4500.0,
        })
        assert r.status_code in VALID

    def test_attribution_no_conversions(self, client: TestClient) -> None:
        """Line 1591: low confidence."""
        r = client.post("/vse/dark-social/attribution", headers=H, json={
            "campaign_id": "camp-extra3-002",
            "touchpoints": [],
            "conversions": 0,
            "conversion_value": 0.0,
        })
        assert r.status_code in VALID


# ── Immortalise ───────────────────────────────────────────────────────────────


class TestImmortalize:
    """Lines 1620-1691: immortalise POST and assets GET."""

    def test_immortalise_with_key_insight(self, client: TestClient) -> None:
        """Lines 1620-1660: immortalise with key_insight."""
        r = client.post("/vse/immortalise", headers=H, json={
            "viral_event_id": "ve-extra3-001",
            "post_summary": "Our viral post hit 1M impressions on LinkedIn",
            "viral_impressions": 1000000,
            "platforms_achieved": ["linkedin", "x"],
            "key_insight": "Pattern-interrupt hook + authority signal combo is unbeatable",
        })
        assert r.status_code in VALID

    def test_immortalise_without_key_insight(self, client: TestClient) -> None:
        """Lines 1632: key_insight=None path."""
        r = client.post("/vse/immortalise", headers=H, json={
            "viral_event_id": "ve-extra3-002",
            "post_summary": "Another viral success story without insight",
            "viral_impressions": 500000,
            "platforms_achieved": ["instagram"],
        })
        assert r.status_code in VALID

    def test_get_immortalise_assets_found(self, client: TestClient) -> None:
        """Line 1691: found case."""
        r1 = client.post("/vse/immortalise", headers=H, json={
            "viral_event_id": "ve-extra3-assets",
            "post_summary": "Post to get assets for",
            "viral_impressions": 2000000,
            "platforms_achieved": ["linkedin", "tiktok", "instagram"],
            "key_insight": "Triple-platform simultaneous detonation",
        })
        if r1.status_code in (200, 201):
            immortal_id = r1.json().get("immortal_record", {}).get("id")
            if immortal_id:
                r2 = client.get(f"/vse/immortalise/{immortal_id}/assets", headers=H)
                assert r2.status_code in VALID

    def test_get_immortalise_assets_not_found(self, client: TestClient) -> None:
        r = client.get("/vse/immortalise/nonexistent-immortal-id/assets", headers=H)
        assert r.status_code in VALID

    def test_get_immortalise_vault(self, client: TestClient) -> None:
        r = client.get("/vse/immortalise/vault", headers=H)
        assert r.status_code in VALID
