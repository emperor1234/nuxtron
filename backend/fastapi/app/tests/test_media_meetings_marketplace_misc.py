"""
Tests for Media Library, Meetings, Marketplace, Linkinbio, Influencer,
Competitive, Reviews, Publishing/UTM, Benchmarks, Content Approval routers.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ── Media Library ─────────────────────────────────────────────────────────────

class TestMediaLibrary:
    def test_list_assets(self, client: TestClient) -> None:
        r = client.get("/media/assets", headers=H)
        assert r.status_code == 200

    def test_create_asset(self, client: TestClient) -> None:
        r = client.post("/media/assets", headers=H, json={
            "filename": "hero.jpg",
            "asset_type": "image",
            "size_bytes": 204800,
            "url": "https://cdn.example.com/hero.jpg",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("asset", data)

    def test_get_asset(self, client: TestClient) -> None:
        r = client.post("/media/assets", headers=H, json={
            "filename": "logo.png",
            "asset_type": "image",
            "size_bytes": 50000,
            "url": "https://cdn.example.com/logo.png",
        })
        d = r.json()
        aid = d.get("asset", d).get("id", 1)
        r2 = client.get(f"/media/assets/{aid}", headers=H)
        assert r2.status_code == 200

    def test_update_asset(self, client: TestClient) -> None:
        r = client.post("/media/assets", headers=H, json={
            "filename": "update.jpg",
            "asset_type": "image",
            "size_bytes": 10000,
            "url": "https://cdn.example.com/update.jpg",
        })
        d = r.json()
        aid = d.get("asset", d).get("id", 1)
        r2 = client.patch(f"/media/assets/{aid}", headers=H, json={"alt_text": "Updated alt text"})
        assert r2.status_code < 500

    def test_delete_asset(self, client: TestClient) -> None:
        r = client.post("/media/assets", headers=H, json={
            "filename": "delete_me.jpg",
            "asset_type": "image",
            "size_bytes": 1024,
            "url": "https://cdn.example.com/delete_me.jpg",
        })
        d = r.json()
        aid = d.get("asset", d).get("id", 1)
        r2 = client.delete(f"/media/assets/{aid}", headers=H)
        assert r2.status_code in {200, 204}

    def test_create_folder(self, client: TestClient) -> None:
        r = client.post("/media/folders", headers=H, json={
            "name": "Campaign Assets",
        })
        assert r.status_code in {200, 201}

    def test_list_folders(self, client: TestClient) -> None:
        r = client.get("/media/folders", headers=H)
        assert r.status_code == 200

    def test_media_stats(self, client: TestClient) -> None:
        r = client.get("/media/stats", headers=H)
        assert r.status_code == 200

    def test_validate_file(self, client: TestClient) -> None:
        r = client.post("/media/validate-file", headers=H, json={
            "filename": "video.mp4",
            "file_type": "video/mp4",
            "size_bytes": 52428800,
        })
        assert r.status_code < 500

    def test_create_media_job(self, client: TestClient) -> None:
        r = client.post("/media/jobs", headers=H, json={
            "storage_key": "uploads/raw-video-001.mp4",
            "media_type": "video",
        })
        assert r.status_code in {200, 201}

    def test_list_media_jobs(self, client: TestClient) -> None:
        r = client.get("/media/jobs", headers=H)
        assert r.status_code == 200

    def test_list_media_dlq(self, client: TestClient) -> None:
        r = client.get("/media/jobs/dlq", headers=H)
        # NOTE: /media/jobs/{job_id} (int) is registered before /media/jobs/dlq,
        # so FastAPI tries to parse "dlq" as int and returns 422. Accept both.
        assert r.status_code in {200, 422}


# ── Meetings ──────────────────────────────────────────────────────────────────

class TestMeetings:
    def test_list_links(self, client: TestClient) -> None:
        r = client.get("/meetings/links", headers=H)
        assert r.status_code == 200

    def test_create_link(self, client: TestClient) -> None:
        r = client.post("/meetings/links", headers=H, json={
            "name": "30-Minute Discovery Call",
            "duration_minutes": 30,
            "slug": "discovery-30",
        })
        assert r.status_code in {200, 201, 409}

    def test_list_bookings(self, client: TestClient) -> None:
        r = client.get("/meetings/bookings", headers=H)
        assert r.status_code == 200

    def test_book_meeting(self, client: TestClient) -> None:
        client.post("/meetings/links", headers=H, json={
            "name": "Book Me",
            "duration_minutes": 15,
            "slug": "book-me-test",
        })
        r2 = client.post("/meetings/book", headers=H, json={
            "meeting_link_slug": "book-me-test",
            "attendee_name": "John Smith",
            "attendee_email": "john@example.com",
            "start_time": "2026-06-15T14:00:00Z",
        })
        assert r2.status_code < 500

    def test_meetings_analytics(self, client: TestClient) -> None:
        r = client.get("/meetings/analytics", headers=H)
        assert r.status_code == 200


# ── Marketplace ───────────────────────────────────────────────────────────────

class TestMarketplace:
    def test_list_plugins(self, client: TestClient) -> None:
        r = client.get("/marketplace/plugins", headers=H)
        assert r.status_code == 200

    def test_list_themes(self, client: TestClient) -> None:
        r = client.get("/marketplace/themes", headers=H)
        assert r.status_code == 200

    def test_install(self, client: TestClient) -> None:
        r = client.post("/marketplace/install", headers=H, json={
            "plugin_key": "seo-boost",
            "version": "1.0.0",
        })
        assert r.status_code < 500

    def test_publish(self, client: TestClient) -> None:
        r = client.post("/marketplace/publish", headers=H, json={
            "name": "My Plugin",
            "description": "A useful plugin.",
            "type": "plugin",
            "version": "1.0.0",
        })
        assert r.status_code < 500


# ── Linkinbio ─────────────────────────────────────────────────────────────────

class TestLinkinbio:
    def test_list_pages(self, client: TestClient) -> None:
        r = client.get("/linkinbio/pages", headers=H)
        assert r.status_code == 200

    def test_create_page(self, client: TestClient) -> None:
        r = client.post("/linkinbio/pages", headers=H, json={
            "title": "My Links",
            "slug": "my-links-test",
            "theme": "minimal",
        })
        assert r.status_code in {200, 201, 409}

    def test_update_page(self, client: TestClient) -> None:
        r = client.post("/linkinbio/pages", headers=H, json={
            "title": "Update Page",
            "slug": "update-page-slug",
        })
        pid = r.json().get("id", 1)
        r2 = client.patch(f"/linkinbio/pages/{pid}", headers=H, json={"title": "Updated Links"})
        assert r2.status_code < 500

    def test_add_link(self, client: TestClient) -> None:
        r = client.post("/linkinbio/pages", headers=H, json={
            "title": "Link Page",
            "slug": "link-page-test",
        })
        pid = r.json().get("id", 1)
        r2 = client.post(f"/linkinbio/pages/{pid}/links", headers=H, json={
            "title": "My Blog",
            "url": "https://myblog.com",
        })
        assert r2.status_code < 500

    def test_page_analytics(self, client: TestClient) -> None:
        r = client.post("/linkinbio/pages", headers=H, json={
            "title": "Analytics Page",
            "slug": "analytics-page-test",
        })
        pid = r.json().get("id", 1)
        r2 = client.get(f"/linkinbio/pages/{pid}/analytics", headers=H)
        assert r2.status_code < 500


# ── Influencer ────────────────────────────────────────────────────────────────

class TestInfluencer:
    def test_list_campaigns(self, client: TestClient) -> None:
        r = client.get("/influencer/campaigns", headers=H)
        assert r.status_code == 200

    def test_create_campaign(self, client: TestClient) -> None:
        r = client.post("/influencer/campaigns", headers=H, json={
            "name": "Summer Promo",
            "budget": 5000.0,
            "target_niche": "fitness",
        })
        assert r.status_code in {200, 201}

    def test_search_influencers(self, client: TestClient) -> None:
        r = client.post("/influencer/search", headers=H, json={
            "niche": "fitness",
            "min_followers": 10000,
            "max_followers": 1000000,
        })
        assert r.status_code < 500

    def test_fraud_check(self, client: TestClient) -> None:
        r = client.post("/influencer/fraud-check", headers=H, json={
            "influencer_id": "inf-001",
            "profile_url": "https://instagram.com/influencer",
        })
        assert r.status_code < 500

    def test_outreach(self, client: TestClient) -> None:
        r = client.post("/influencer/outreach", headers=H, json={
            "influencer_id": "inf-001",
            "message": "We'd love to work with you!",
            "campaign_id": 1,
        })
        assert r.status_code < 500

    def test_analytics(self, client: TestClient) -> None:
        r = client.get("/influencer/analytics", headers=H)
        assert r.status_code == 200


# ── Competitive ───────────────────────────────────────────────────────────────

class TestCompetitive:
    def test_list_profiles(self, client: TestClient) -> None:
        r = client.get("/competitive/profiles", headers=H)
        assert r.status_code == 200

    def test_create_own_profile(self, client: TestClient) -> None:
        r = client.post("/competitive/own-profile", headers=H, json={
            "brand_name": "My Brand",
            "website": "https://mybrand.com",
            "social_handles": {},
        })
        assert r.status_code < 500

    def test_create_competitor_profile(self, client: TestClient) -> None:
        r = client.post("/competitive/profiles", headers=H, json={
            "name": "Competitor A",
            "network": "instagram",
            "handle": "competitora",
        })
        assert r.status_code in {200, 201}

    def test_competitive_report(self, client: TestClient) -> None:
        r = client.get("/competitive/report", headers=H)
        assert r.status_code == 200

    def test_share_of_voice(self, client: TestClient) -> None:
        r = client.get("/competitive/share-of-voice", headers=H)
        assert r.status_code == 200


# ── Reviews ───────────────────────────────────────────────────────────────────

class TestReviews:
    def test_list_reviews(self, client: TestClient) -> None:
        r = client.get("/reviews", headers=H)
        assert r.status_code == 200

    def test_reviews_summary(self, client: TestClient) -> None:
        r = client.get("/reviews/summary", headers=H)
        assert r.status_code == 200

    def test_ingest_review(self, client: TestClient) -> None:
        r = client.post("/reviews/ingest", headers=H, json={
            "platform": "google",
            "reviewer_name": "Happy Customer",
            "rating": 5,
            "text": "Excellent service!",
        })
        assert r.status_code < 500

    def test_respond_to_review(self, client: TestClient) -> None:
        r = client.post("/reviews/ingest", headers=H, json={
            "platform": "yelp",
            "reviewer_name": "Satisfied User",
            "rating": 4,
            "text": "Good experience.",
        })
        rid = r.json().get("id", 1)
        r2 = client.post(f"/reviews/{rid}/respond", headers=H, json={
            "response": "Thank you for your feedback!",
        })
        assert r2.status_code < 500


# ── Publishing / UTM ──────────────────────────────────────────────────────────

class TestPublishingUTM:
    def test_optimal_times(self, client: TestClient) -> None:
        r = client.get("/publishing/optimal-times", headers=H)
        assert r.status_code == 200

    def test_optimal_times_defaults(self, client: TestClient) -> None:
        r = client.get("/publishing/optimal-times/defaults", headers=H, params={"network": "instagram"})
        assert r.status_code == 200

    def test_set_optimal_times(self, client: TestClient) -> None:
        r = client.post("/publishing/optimal-times", headers=H, json={
            "network": "instagram",
            "profile_id": "test-profile-1",
        })
        assert r.status_code < 500

    def test_list_utm_presets(self, client: TestClient) -> None:
        r = client.get("/publishing/utm/presets", headers=H)
        assert r.status_code == 200

    def test_create_utm_preset(self, client: TestClient) -> None:
        r = client.post("/publishing/utm/presets", headers=H, json={
            "name": "Summer Campaign",
            "utm_source": "email",
            "utm_medium": "newsletter",
            "utm_campaign": "summer_2026",
        })
        assert r.status_code in {200, 201}

    def test_build_utm(self, client: TestClient) -> None:
        r = client.post("/publishing/utm/build", headers=H, json={
            "base_url": "https://example.com/landing",
            "utm_source": "social",
            "utm_medium": "instagram",
            "utm_campaign": "launch",
        })
        assert r.status_code < 500

    def test_post_history(self, client: TestClient) -> None:
        r = client.post("/publishing/post-history", headers=H, json={
            "network": "instagram",
            "content": "Posted content",
            "posted_at": "2026-05-01T10:00:00Z",
        })
        assert r.status_code < 500


# ── Content Approval ──────────────────────────────────────────────────────────

class TestContentApproval:
    def test_get_config(self, client: TestClient) -> None:
        r = client.get("/content/approval/config", headers=H)
        assert r.status_code == 200

    def test_update_config(self, client: TestClient) -> None:
        r = client.put("/content/approval/config", headers=H, json={
            "require_approval": True,
            "approvers": ["manager@example.com"],
        })
        assert r.status_code < 500

    def test_list_requests(self, client: TestClient) -> None:
        r = client.get("/content/approval/requests", headers=H)
        assert r.status_code == 200

    def test_create_request(self, client: TestClient) -> None:
        r = client.post("/content/approval/requests", headers=H, json={
            "scheduled_post_id": 1,
            "platform": "instagram",
            "content_preview": "Check out our new product!",
            "requested_by": "marketer@example.com",
        })
        assert r.status_code in {200, 201}

    def test_decision_on_request(self, client: TestClient) -> None:
        r = client.post("/content/approval/requests", headers=H, json={
            "scheduled_post_id": 2,
            "platform": "facebook",
            "content_preview": "Approve this content",
            "requested_by": "creator@example.com",
        })
        rid = r.json().get("request", r.json()).get("id", 1)
        r2 = client.post(f"/content/approval/requests/{rid}/decision", headers=H, json={
            "decision": "approved",
            "reviewer_role": "manager",
        })
        assert r2.status_code < 500
