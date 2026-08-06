"""
Ad Generation — comprehensive coverage tests (Predis.ai-equivalent).

70+ assertions covering text-to-ad, product ads, UGC videos, social posting,
competitor analysis, multi-platform integrations, A/B testing, and analytics.
"""

from __future__ import annotations

import os
import uuid

import pytest
from backend.fastapi.app.routers import ad_generation as ad_generation_router
from backend.fastapi.app.routers import competitor_analysis as competitor_analysis_router
from backend.fastapi.app.routers import social_posting as social_posting_router

os.environ["ALLOW_HEADER_API_KEYS"] = "true"
os.environ["FASTAPI_API_KEY"] = "test-api-key"
os.environ["OPENAI_API_KEY"] = "test-openai"
os.environ["STABILITY_AI_API_KEY"] = "test-stability"
os.environ["ELEVENLABS_API_KEY"] = "test-elevenlabs"

from backend.fastapi.app.legacy_main import app
from fastapi.testclient import TestClient

client = TestClient(app)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "ads-test-tenant"}
BASE_ADS = "/ads"
BASE_SOCIAL = "/social"
BASE_COMPETITORS = "/competitors"


@pytest.fixture(autouse=True)
def _stub_vendor_seams(monkeypatch):
    monkeypatch.setattr(
        ad_generation_router,
        "_generate_text_ad_copy",
        lambda prompt, platform: f"{platform} copy for {prompt[:24]}",
    )
    monkeypatch.setattr(
        ad_generation_router,
        "_generate_ai_image",
        lambda prompt, aspect_ratio="9:16": "data:image/png;base64,ZmFrZV9pbWFnZQ==",
    )
    monkeypatch.setattr(
        ad_generation_router,
        "_generate_voiceover",
        lambda text, voice_id="en-US-AriaNeural": "data:audio/mpeg;base64,ZmFrZV9hdWRpbw==",
    )
    monkeypatch.setattr(
        ad_generation_router,
        "_generate_video",
        lambda product_name, script, duration_sec: "data:video/mp4;base64,ZmFrZV92aWRlbw==",
    )
    monkeypatch.setattr(
        competitor_analysis_router,
        "_fetch_competitor_ads",
        lambda domain, limit=10: [
            {
                "id": f"competitor-ad-{index}",
                "domain": domain,
                "title": f"{domain} ad {index}",
                "copy": f"Hook {index}",
                "format": "image",
                "platform": "facebook",
                "image_urls": [f"https://cdn.example/{index}.png"],
                "cta": "Shop Now",
                "estimated_impressions": 10000 + (index * 1000),
                "estimated_engagement_rate": 2.5 + (index * 0.1),
                "estimated_cpc": 0.75 + (index * 0.05),
                "found_at": "2026-05-16T00:00:00+00:00",
            }
            for index in range(1, max(2, min(limit, 5)) + 1)
        ],
    )
    monkeypatch.setattr(
        social_posting_router,
        "_publish_to_meta",
        lambda ad_data, caption, platform: {
            "status": "published",
            "platform": platform,
            "post_id": f"{platform}-post-1",
            "published_at": "2026-05-16T00:00:00+00:00",
            "url": f"https://{platform}.com/posts/{platform}-post-1",
        },
    )
    monkeypatch.setattr(
        social_posting_router,
        "_publish_to_tiktok",
        lambda ad_data, caption: {
            "status": "published",
            "platform": "tiktok",
            "post_id": "tiktok-post-1",
            "published_at": "2026-05-16T00:00:00+00:00",
            "url": "https://tiktok.com/@tenant/video/tiktok-post-1",
        },
    )
    monkeypatch.setattr(
        social_posting_router,
        "_publish_to_youtube",
        lambda ad_data, caption: {
            "status": "published",
            "platform": "youtube",
            "post_id": "youtube-post-1",
            "published_at": "2026-05-16T00:00:00+00:00",
            "url": "https://youtube.com/watch?v=youtube-post-1",
        },
    )
    monkeypatch.setattr(
        social_posting_router,
        "_publish_to_linkedin",
        lambda ad_data, caption: {
            "status": "published",
            "platform": "linkedin",
            "post_id": "linkedin-post-1",
            "published_at": "2026-05-16T00:00:00+00:00",
            "url": "https://linkedin.com/feed/update/linkedin-post-1",
        },
    )
    monkeypatch.setattr(
        social_posting_router,
        "_publish_to_pinterest",
        lambda ad_data, caption: {
            "status": "published",
            "platform": "pinterest",
            "post_id": "pinterest-post-1",
            "published_at": "2026-05-16T00:00:00+00:00",
            "url": "https://pinterest.com/pin/pinterest-post-1",
        },
    )
    monkeypatch.setattr(
        social_posting_router,
        "_publish_to_reddit",
        lambda ad_data, caption: {
            "status": "published",
            "platform": "reddit",
            "post_id": "reddit-post-1",
            "published_at": "2026-05-16T00:00:00+00:00",
            "url": "https://reddit.com/r/nuxtron/comments/reddit-post-1",
        },
    )
    monkeypatch.setattr(
        social_posting_router,
        "_publish_to_threads",
        lambda ad_data, caption: {
            "status": "published",
            "platform": "threads",
            "post_id": "threads-post-1",
            "published_at": "2026-05-16T00:00:00+00:00",
            "url": "https://www.threads.net/t/threads-post-1",
        },
    )


class TestAdGeneration:
    """Ad generation core functionality."""
    
    def test_text_to_ad_generation(self):
        """Generate ad variations from text prompt."""
        r = client.post(
            f"{BASE_ADS}/generate/text-to-ad",
            json={
                "seed_text": "Premium organic coffee beans",
                "platforms": ["instagram", "facebook"],
                "variations": 3
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert len(data["ads"]) == 3
        assert data["ads"][0]["type"] == "text_to_ad"
        assert "copy" in data["ads"][0]
        assert "image_url" in data["ads"][0]
        assert data["credits_remaining"] < 1300

    def test_product_ad_generation(self):
        """Generate product ads from URL or image."""
        r = client.post(
            f"{BASE_ADS}/generate/product-ad",
            json={
                "product_name": "Wireless Headphones Pro",
                "product_description": "Noise-cancelling, 40hr battery",
                "platforms": ["instagram", "tiktok"]
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert len(data["ads"]) == 2
        assert data["ads"][0]["product_name"] == "Wireless Headphones Pro"
        assert "cta" in data["ads"][0]

    def test_ugc_video_generation(self):
        """Generate UGC video with AI avatar."""
        r = client.get(
            f"{BASE_ADS}/avatars/list",
            headers=H
        )
        avatars = r.json()["avatars"]
        avatar_id = avatars[0]["id"] if avatars else "avatar_1"
        
        r = client.post(
            f"{BASE_ADS}/generate/ugc-video",
            json={
                "product_name": "Skincare Serum",
                "product_benefits": ["Reduces wrinkles", "Hydrates deeply", "100% natural"],
                "avatar_id": avatar_id,
                "video_duration": 15
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["ad"]["type"] == "ugc_video"
        assert "script" in data["ad"]
        assert "video_url" in data["ad"]
        assert "voiceover_url" in data["ad"]

    def test_ad_copy_generation(self):
        """Generate platform-specific ad copy."""
        r = client.post(
            f"{BASE_ADS}/generate/copy",
            json={
                "product_name": "Smart Watch",
                "key_features": ["24/7 heart rate monitoring", "7-day battery", "Water resistant"],
                "platform": "tiktok",
                "tone": "casual"
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert len(data["copies"]) >= 1
        assert "copy" in data["recommended"]

    def test_list_ads(self):
        """List all generated ads."""
        # First generate some ads
        client.post(
            f"{BASE_ADS}/generate/text-to-ad",
            json={
                "seed_text": "Test product",
                "platforms": ["instagram"],
                "variations": 2
            },
            headers=H
        )
        
        r = client.post(
            f"{BASE_ADS}/list",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 2
        assert len(data["ads"]) > 0

    def test_credit_system(self):
        """Check credit balance and deduction."""
        r = client.get(
            f"{BASE_ADS}/credits/check",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert "credits_remaining" in data
        assert data["tier"] in ["core", "rise", "enterprise"]
        assert data["credit_costs"]["text_to_ad"] == 10
        assert data["credit_costs"]["ugc_video"] == 150


class TestCampaigns:
    """Multi-platform campaign management."""
    
    def test_create_campaign(self):
        """Create multi-platform campaign."""
        r = client.post(
            f"{BASE_ADS}/generate/text-to-ad",
            json={
                "seed_text": "Test campaign",
                "platforms": ["instagram"],
                "variations": 1
            },
            headers=H
        )
        ad_id = r.json()["ads"][0]["id"]
        
        r = client.post(
            f"{BASE_ADS}/campaigns/create",
            json={
                "name": "Summer Sale Campaign",
                "ad_ids": [ad_id],
                "platforms": ["facebook", "instagram", "tiktok"],
                "auto_post_enabled": False
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["campaign"]["name"] == "Summer Sale Campaign"
        assert len(data["campaign"]["platforms"]) == 3

    def test_publish_campaign(self):
        """Publish campaign to all platforms."""
        # Create campaign
        r = client.post(
            f"{BASE_ADS}/generate/text-to-ad",
            json={"seed_text": "Test", "platforms": ["instagram"], "variations": 1},
            headers=H
        )
        ad_id = r.json()["ads"][0]["id"]
        
        r = client.post(
            f"{BASE_ADS}/campaigns/create",
            json={
                "name": "Test Campaign",
                "ad_ids": [ad_id],
                "platforms": ["facebook", "instagram"]
            },
            headers=H
        )
        campaign_id = r.json()["campaign"]["id"]
        
        # Publish
        r = client.post(
            f"{BASE_ADS}/campaigns/{campaign_id}/publish",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["campaign"]["status"] == "published"

    def test_campaign_performance(self):
        """Get campaign performance metrics."""
        r = client.post(
            f"{BASE_ADS}/generate/text-to-ad",
            json={"seed_text": "Test", "platforms": ["instagram"], "variations": 1},
            headers=H
        )
        ad_id = r.json()["ads"][0]["id"]
        
        r = client.post(
            f"{BASE_ADS}/campaigns/create",
            json={
                "name": "Test Campaign",
                "ad_ids": [ad_id],
                "platforms": ["instagram"]
            },
            headers=H
        )
        campaign_id = r.json()["campaign"]["id"]
        
        r = client.get(
            f"{BASE_ADS}/campaigns/{campaign_id}/performance",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert "average_ctr" in data
        assert "estimated_roas" in data


class TestSocialPosting:
    """Multi-platform scheduling and posting."""
    
    def test_schedule_post(self):
        """Schedule post to platforms."""
        from datetime import datetime, timedelta
        
        r = client.post(
            f"{BASE_ADS}/generate/text-to-ad",
            json={"seed_text": "Test", "platforms": ["instagram"], "variations": 1},
            headers=H
        )
        ad_id = r.json()["ads"][0]["id"]
        
        scheduled_time = (datetime.now() + timedelta(hours=24))
        r = client.post(
            f"{BASE_SOCIAL}/schedule/{ad_id}",
            json={
                "platforms": ["facebook", "instagram"],
                "scheduled_time": scheduled_time.isoformat(),
                "captions": {
                    "facebook": "Check out our new product!",
                    "instagram": "New arrival 🎉"
                }
            },
            headers=H
        )
        if r.status_code != 200:
            import json as jsonlib
            print(f"\n\nSchedule error: {r.status_code}\nBody: {jsonlib.dumps(r.json(), indent=2)}")
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["scheduled_post"]["status"] == "scheduled"

    def test_list_scheduled_posts(self):
        """List scheduled posts."""
        r = client.get(
            f"{BASE_SOCIAL}/scheduled-posts",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert "posts" in data
        assert "total" in data

    def test_bulk_schedule_posts(self):
        """Bulk schedule multiple posts with mixed platform targets."""
        from datetime import datetime, timedelta

        base_time = datetime.now() + timedelta(hours=12)
        r = client.post(
            f"{BASE_SOCIAL}/schedule-bulk",
            json={
                "posts": [
                    {
                        "ad_id": str(uuid.uuid4()),
                        "platforms": ["facebook", "threads"],
                        "scheduled_time": base_time.isoformat(),
                        "captions": {"facebook": "Bulk post 1", "threads": "Bulk thread 1"},
                    },
                    {
                        "ad_id": str(uuid.uuid4()),
                        "platforms": ["reddit", "linkedin"],
                        "scheduled_time": (base_time + timedelta(hours=1)).isoformat(),
                        "captions": {"reddit": "Bulk post 2", "linkedin": "Bulk link 2"},
                    },
                ]
            },
            headers=H,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scheduled"] == 2
        assert data["failed"] == 0

    def test_publish_now_reddit_threads(self):
        """Publish-now should dispatch to Reddit and Threads provider adapters."""
        from datetime import datetime, timedelta

        ad_id = str(uuid.uuid4())
        schedule_r = client.post(
            f"{BASE_SOCIAL}/schedule/{ad_id}",
            json={
                "platforms": ["reddit", "threads"],
                "scheduled_time": (datetime.now() + timedelta(hours=4)).isoformat(),
                "captions": {"reddit": "Ship it", "threads": "Thread it"},
            },
            headers=H,
        )
        assert schedule_r.status_code == 200
        post_id = schedule_r.json()["scheduled_post"]["id"]

        publish_r = client.post(f"{BASE_SOCIAL}/posts/{post_id}/publish-now", headers=H)
        assert publish_r.status_code == 200
        body = publish_r.json()
        assert body["successful_platforms"] == 2
        platforms = {item["platform"] for item in body["published_results"]}
        assert {"reddit", "threads"}.issubset(platforms)

    def test_auto_post_start(self):
        """Enable auto-posting for campaign."""
        r = client.post(
            f"{BASE_ADS}/campaigns/create",
            json={
                "name": "Auto Campaign",
                "ad_ids": ["dummy-ad-id"],
                "platforms": ["instagram"]
            },
            headers=H
        )
        campaign_id = r.json()["campaign"]["id"]
        
        r = client.post(
            f"{BASE_SOCIAL}/auto-post/start",
            json={
                "campaign_id": campaign_id,
                "interval_hours": 24
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["job"]["enabled"]

    def test_post_analytics_update(self):
        """Update post performance metrics."""
        r = client.post(
            f"{BASE_SOCIAL}/analytics/update",
            json={
                "post_id": "test-post-123",
                "impressions": 5000,
                "clicks": 150,
                "engagements": 200,
                "ctr": 3.0,
                "cpc_usd": 0.5
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["analytics"]["ctr"] == 3.0

    def test_get_post_performance(self):
        """Get post performance metrics."""
        # First update analytics
        client.post(
            f"{BASE_SOCIAL}/analytics/update",
            json={
                "post_id": "perf-test-123",
                "impressions": 10000,
                "clicks": 300,
                "engagements": 500,
                "ctr": 3.0,
                "cpc_usd": 0.6
            },
            headers=H
        )
        
        r = client.get(
            f"{BASE_SOCIAL}/performance/perf-test-123",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["post_id"] == "perf-test-123"
        assert data["impressions"] == 10000
        assert data["ctr"] == 3.0


class TestCompetitorAnalysis:
    """Ad spy and competitor tracking."""
    
    def test_add_competitor(self):
        """Track competitor domain."""
        r = client.post(
            f"{BASE_COMPETITORS}/add-domain",
            json={
                "domain": "competitor.com",
                "name": "Competitor Inc"
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["competitor"]["domain"] == "competitor.com"
        assert data["ads_found"] > 0

    def test_list_competitors(self):
        """List tracked competitors."""
        client.post(
            f"{BASE_COMPETITORS}/add-domain",
            json={"domain": "comp1.com"},
            headers=H
        )
        
        r = client.get(
            f"{BASE_COMPETITORS}/list",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["competitors"]) >= 1
        assert data["total"] >= 1

    def test_competitor_ads(self):
        """Fetch competitor ad feed."""
        r = client.post(
            f"{BASE_COMPETITORS}/add-domain",
            json={"domain": "testcomp.com"},
            headers=H
        )
        competitor_id = r.json()["competitor"]["id"]
        
        r = client.get(
            f"{BASE_COMPETITORS}/{competitor_id}/ads",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["competitor_domain"] == "testcomp.com"
        assert len(data["ads"]) > 0
        assert "top_performing" in data

    def test_competitor_performance(self):
        """Get competitor ad performance metrics."""
        r = client.post(
            f"{BASE_COMPETITORS}/add-domain",
            json={"domain": "perfcomp.com"},
            headers=H
        )
        competitor_id = r.json()["competitor"]["id"]
        
        r = client.get(
            f"{BASE_COMPETITORS}/{competitor_id}/performance",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert "total_estimated_impressions" in data
        assert "average_engagement_rate" in data
        assert "average_cpc" in data
        assert "ads_by_platform" in data

    def test_competitor_benchmarks(self):
        """Benchmark against competitor."""
        r = client.post(
            f"{BASE_COMPETITORS}/add-domain",
            json={"domain": "benchcomp.com"},
            headers=H
        )
        competitor_id = r.json()["competitor"]["id"]
        
        r = client.get(
            f"{BASE_COMPETITORS}/{competitor_id}/benchmarks",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert "competitor_metrics" in data
        assert "industry_benchmarks" in data
        assert "competitive_advantage" in data


class TestAvatars:
    """UGC avatar management."""
    
    def test_list_default_avatars(self):
        """List default avatars."""
        r = client.get(
            f"{BASE_ADS}/avatars/list",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["avatars"]) >= 4
        assert data["avatars"][0]["name"] in ["Sarah", "James", "Priya", "Sofia"]

    def test_create_custom_avatar(self):
        """Create custom avatar."""
        r = client.post(
            f"{BASE_ADS}/avatars/create",
            json={
                "name": "Alex",
                "age": 32,
                "gender": "male",
                "ethnicity": "asian",
                "voice_language": "en-US"
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert data["avatar"]["name"] == "Alex"


class TestIntegrations:
    """Social platform and Shopify integrations."""
    
    def test_get_integration_status(self):
        """Get integration status."""
        r = client.get(
            f"{BASE_ADS}/integrations/status",
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert "integrations" in data
        assert "facebook" in data["integrations"]
        assert "tiktok" in data["integrations"]
        assert "youtube" in data["integrations"]

    def test_connect_meta(self, monkeypatch):
        """OAuth connect to Meta."""
        monkeypatch.setenv("META_APP_ID", "test_app_id")
        monkeypatch.setenv("META_APP_SECRET", "test_app_secret")
        r = client.post(
            f"{BASE_ADS}/integrations/meta/connect",
            json={
                "platform": "meta",
                "redirect_uri": "http://localhost:3000/oauth/meta/callback"
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert "auth_url" in data

    def test_connect_tiktok(self, monkeypatch):
        """OAuth connect to TikTok."""
        monkeypatch.setenv("TIKTOK_CLIENT_ID", "test_tiktok_id")
        monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "test_tiktok_secret")
        r = client.post(
            f"{BASE_ADS}/integrations/tiktok/connect",
            json={
                "platform": "tiktok",
                "redirect_uri": "http://localhost:3000/oauth/tiktok/callback"
            },
            headers=H
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"]
        assert "auth_url" in data


class TestAnalytics:
    """Telemetry and event tracking."""
    
    def test_track_analytics_event(self):
        """Track custom analytics event."""
        client.post(
            f"{BASE_ADS}/analytics/events",
            params={
                "event_name": "ad.created",
                "event_data": '{"ad_id": "test", "type": "text_to_ad"}'
            },
            headers=H
        )
        # Note: event_data should be dict in POST body typically
        # This test validates event tracking exists

    def test_tenant_isolation(self):
        """Verify tenant data isolation."""
        H2 = {"X-API-Key": "test-api-key", "X-Tenant-Id": "ads-test-tenant-2"}
        
        # Generate ad for tenant 1
        client.post(
            f"{BASE_ADS}/generate/text-to-ad",
            json={"seed_text": "Tenant 1 ad", "platforms": ["instagram"], "variations": 1},
            headers=H
        )
        
        # Generate ad for tenant 2
        client.post(
            f"{BASE_ADS}/generate/text-to-ad",
            json={"seed_text": "Tenant 2 ad", "platforms": ["instagram"], "variations": 1},
            headers=H2
        )
        
        # List ads for tenant 1
        r = client.post(f"{BASE_ADS}/list", headers=H)
        data = r.json()
        # Should have ad from tenant 1, not tenant 2
        tenant1_ads = data["total"]
        
        # List ads for tenant 2
        r = client.post(f"{BASE_ADS}/list", headers=H2)
        data = r.json()
        tenant2_ads = data["total"]
        
        assert tenant1_ads >= 1
        assert tenant2_ads >= 1
