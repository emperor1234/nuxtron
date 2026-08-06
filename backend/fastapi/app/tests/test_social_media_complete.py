"""
Comprehensive tests for social media management platform.
Tests publishing, analytics, engagement, and integrations end-to-end.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_vendor_manager():
    """Mock vendor manager"""
    manager = Mock()
    manager.get_credentials = Mock(return_value=Mock(
        access_token="test_token",
        additional_config={'page_id': '12345'},
    ))
    manager.make_request = AsyncMock(return_value={'id': 'post_123', 'data': {'id': 'post_123'}})
    return manager


@pytest.fixture
def db_session(db):
    """Get test database session"""
    return db


@pytest.fixture
def test_tenant_id():
    return "test-tenant-123"


@pytest.fixture
def test_user_id():
    return "test-user-123"


@pytest.fixture
def auth_headers(test_tenant_id):
    return {
        'X-Tenant-Id': test_tenant_id,
        'X-API-Key': 'test-api-key',
    }


# ============================================================================
# Publishing Tests
# ============================================================================

class TestPublishing:
    """Test social media publishing functionality"""
    
    @pytest.mark.asyncio
    async def test_create_content_draft(self, client: TestClient, auth_headers):
        """Test creating content in draft status"""
        response = client.post(
            "/social/content/create",
            json={
                "title": "New Product Launch",
                "caption": "Excited to announce our new product! #launch #innovation",
                "media_assets": [
                    {
                        "type": "image",
                        "url": "https://example.com/image.jpg",
                        "alt_text": "Product showcase"
                    }
                ],
                "platforms": ["instagram", "linkedin"],
                "requires_approval": False,
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'draft'
        assert data['title'] == "New Product Launch"
        assert len(data['platforms']) == 2
    
    @pytest.mark.asyncio
    async def test_create_content_requires_approval(self, client: TestClient, auth_headers):
        """Test creating content that requires approval"""
        response = client.post(
            "/social/content/create",
            json={
                "title": "Campaign Post",
                "caption": "Check out our latest campaign",
                "media_assets": [],
                "platforms": ["twitter"],
                "requires_approval": True,
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'pending_approval'
    
    @pytest.mark.asyncio
    async def test_approve_content(self, client: TestClient, auth_headers, db_session):
        """Test approving content"""
        # Create content first
        create_response = client.post(
            "/social/content/create",
            json={
                "title": "Test Post",
                "caption": "Test caption",
                "media_assets": [],
                "platforms": ["twitter"],
                "requires_approval": True,
            },
            headers=auth_headers,
        )
        content_id = create_response.json()['id']
        
        # Approve content
        response = client.post(
            f"/social/content/{content_id}/approve",
            json={
                "approval_notes": "Looks good to me"
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    @pytest.mark.asyncio
    async def test_publish_to_facebook(self, client: TestClient, auth_headers, mock_vendor_manager):
        """Test publishing to Facebook"""
        with patch('backend.fastapi.app.routers.social_media_router.vendor_manager', mock_vendor_manager):
            response = client.post(
                "/social/content/create",
                json={
                    "title": "Facebook Post",
                    "caption": "Hello Facebook!",
                    "media_assets": [],
                    "platforms": ["facebook"],
                    "requires_approval": False,
                },
                headers=auth_headers,
            )
            content_id = response.json()['id']
            
            # Publish
            publish_response = client.post(
                f"/social/content/{content_id}/publish",
                json={},
                headers=auth_headers,
            )
            
            assert publish_response.status_code == 200
            assert publish_response.json()['success'] is True

    @pytest.mark.asyncio
    async def test_publish_requires_approval_before_publish(self, client: TestClient, auth_headers):
        """Content marked for approval must be approved before publish."""
        create_response = client.post(
            "/social/content/create",
            json={
                "title": "Approval Gate Post",
                "caption": "Needs approval first",
                "media_assets": [],
                "platforms": ["linkedin"],
                "requires_approval": True,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        content_id = create_response.json()['id']

        blocked_response = client.post(
            f"/social/content/{content_id}/publish",
            json={},
            headers=auth_headers,
        )
        assert blocked_response.status_code == 409

        approve_response = client.post(
            f"/social/content/{content_id}/approve",
            json={"approval_notes": "Approved for release"},
            headers=auth_headers,
        )
        assert approve_response.status_code == 200

        publish_response = client.post(
            f"/social/content/{content_id}/publish",
            json={},
            headers=auth_headers,
        )
        assert publish_response.status_code == 200
        assert publish_response.json()['success'] is True
    
    @pytest.mark.asyncio
    async def test_schedule_content(self, client: TestClient, auth_headers):
        """Test scheduling content for future publication"""
        future_time = datetime.utcnow() + timedelta(days=7)
        
        response = client.post(
            "/social/content/create",
            json={
                "title": "Scheduled Post",
                "caption": "This will publish in a week",
                "media_assets": [],
                "platforms": ["twitter"],
                "requires_approval": False,
                "scheduled_for": future_time.isoformat(),
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'scheduled'
    
    @pytest.mark.asyncio
    async def test_list_content(self, client: TestClient, auth_headers):
        """Test listing content"""
        # Create multiple content items
        for i in range(3):
            client.post(
                "/social/content/create",
                json={
                    "title": f"Post {i}",
                    "caption": f"Caption {i}",
                    "media_assets": [],
                    "platforms": ["twitter"],
                },
                headers=auth_headers,
            )
        
        # List content
        response = client.get(
            "/social/content/list",
            headers=auth_headers,
        )
        
        assert response.status_code == 200


# ============================================================================
# Analytics Tests
# ============================================================================

class TestAnalytics:
    """Test analytics collection and reporting"""
    
    @pytest.mark.asyncio
    async def test_sync_analytics(self, client: TestClient, auth_headers):
        """Test triggering analytics sync"""
        response = client.post(
            "/social/analytics/sync",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    @pytest.mark.asyncio
    async def test_get_analytics_report(self, client: TestClient, auth_headers, db_session):
        """Test generating analytics report"""
        period_start = datetime.utcnow() - timedelta(days=30)
        period_end = datetime.utcnow()
        
        response = client.post(
            "/social/analytics/report",
            json={
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "platforms": ["facebook", "instagram"],
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'platforms' in data
    
    @pytest.mark.asyncio
    async def test_get_analytics_dashboard(self, client: TestClient, auth_headers):
        """Test getting analytics dashboard"""
        response = client.get(
            "/social/analytics/dashboard?days=30",
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]  # 404 if no data yet
    
    @pytest.mark.asyncio
    async def test_get_platform_analytics(self, client: TestClient, auth_headers):
        """Test getting platform-specific analytics"""
        response = client.get(
            "/social/analytics/platform/instagram?days=30",
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_generated_analytics_export_and_schedule_run(self, client: TestClient, auth_headers):
        """Analytics export should generate a real artifact and schedule run output."""
        create_report = client.post(
            "/analytics/reports",
            json={
                "name": "Exec Summary",
                "metrics": ["crm_contacts", "email_campaigns"],
                "dimensions": ["crm_deals"],
                "date_range": "last_30_days",
            },
            headers=auth_headers,
        )
        assert create_report.status_code == 200
        report_id = create_report.json()["report"]["id"]

        export_response = client.get(
            f"/analytics/export?report_id={report_id}&export_format=csv",
            headers=auth_headers,
        )
        assert export_response.status_code == 200
        export_payload = export_response.json()["export"]
        assert export_payload["status"] == "complete"
        assert export_payload["format"] == "csv"
        assert export_payload["row_count"] >= 1
        assert "period_start" in export_payload["content"]

        schedule_response = client.post(
            "/analytics/schedule",
            json={
                "report_id": report_id,
                "frequency": "weekly",
                "recipients": ["ops@example.com"],
            },
            headers=auth_headers,
        )
        assert schedule_response.status_code == 200
        schedule_id = schedule_response.json()["schedule"]["id"]

        run_response = client.post(f"/analytics/schedules/{schedule_id}/run", headers=auth_headers)
        assert run_response.status_code == 200
        delivery = run_response.json()["delivery"]
        assert delivery["status"] == "generated"
        assert delivery["row_count"] >= 1
        assert delivery["content_type"] == "text/csv"


# ============================================================================
# Engagement Tests
# ============================================================================

class TestEngagement:
    """Test engagement and interaction features"""
    
    @pytest.mark.asyncio
    async def test_get_mentions(self, client: TestClient, auth_headers):
        """Test getting mentions and tags"""
        response = client.get(
            "/social/engagement/mentions?hours=24",
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_post_comments(self, client: TestClient, auth_headers):
        """Test getting comments on a post"""
        response = client.get(
            "/social/engagement/comments/post_123",
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_comment_ingest_mentions_and_listening_flow(self, client: TestClient, auth_headers):
        """Comments should feed mentions and listening keyword results end-to-end."""
        create_response = client.post(
            "/social/content/create",
            json={
                "title": "Listening Seed",
                "caption": "Tracking competitor updates this week",
                "media_assets": [],
                "platforms": ["twitter"],
                "requires_approval": False,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        content_id = create_response.json()["id"]

        publish_response = client.post(
            f"/social/content/{content_id}/publish",
            json={},
            headers=auth_headers,
        )
        assert publish_response.status_code == 200

        keyword_response = client.post(
            "/social/listening/keywords/add",
            json={
                "keywords": ["competitor"],
                "platforms": ["twitter"],
            },
            headers=auth_headers,
        )
        assert keyword_response.status_code == 200

        ingest_comment = client.post(
            f"/social/engagement/comments/{content_id}?platform=twitter&author=analyst&text=competitor launch looked bad",
            headers=auth_headers,
        )
        assert ingest_comment.status_code == 200

        mentions = client.get("/social/engagement/mentions?hours=24", headers=auth_headers)
        assert mentions.status_code == 200
        assert mentions.json()["total"] >= 1

        listening = client.get(
            "/social/listening/results?keyword=competitor&hours=24&sentiment=negative",
            headers=auth_headers,
        )
        assert listening.status_code == 200
        assert listening.json()["results"]
        assert listening.json()["sentiment_breakdown"]["negative"] >= 1


# ============================================================================
# DM Automation Tests
# ============================================================================

class TestDMAutomation:
    """Test direct message automation"""
    
    @pytest.mark.asyncio
    async def test_create_dm_template(self, client: TestClient, auth_headers):
        """Test creating DM automation template"""
        response = client.post(
            "/social/automation/dm/template",
            json={
                "platform": "instagram",
                "name": "Welcome Message",
                "template_text": "Thanks for following! Check out our {product}.",
                "intent_keywords": ["hi", "hello", "welcome"],
            },
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_list_dm_templates(self, client: TestClient, auth_headers):
        """Test listing DM templates"""
        response = client.get(
            "/social/automation/dm/templates",
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_process_dm_matches_template(self, client: TestClient, auth_headers):
        """Inbound DM processing should match templates and return generated response."""
        create_template = client.post(
            "/social/automation/dm/template",
            json={
                "platform": "instagram",
                "name": "Support Reply",
                "template_text": "Thanks for reaching out about {product}.",
                "intent_keywords": ["help", "support"],
            },
            headers=auth_headers,
        )
        assert create_template.status_code == 200

        process_dm = client.post(
            "/social/automation/dm/process?platform=instagram&sender_handle=@user123&message_text=need help with setup",
            headers=auth_headers,
        )
        assert process_dm.status_code == 200
        payload = process_dm.json()
        assert payload["matched_template"] is True
        assert "Thanks for reaching out" in payload["event"]["reply_text"]

    @pytest.mark.asyncio
    async def test_dm_enable_toggle_controls_automation(self, client: TestClient, auth_headers):
        """DM automation should respect per-platform enable/disable state."""
        template_response = client.post(
            "/social/automation/dm/template",
            json={
                "platform": "instagram",
                "name": "Fallback",
                "template_text": "Hello from {product}",
                "intent_keywords": ["hello"],
            },
            headers=auth_headers,
        )
        assert template_response.status_code == 200

        disable_response = client.post(
            "/social/automation/dm/enable?platform=instagram&enabled=false",
            headers=auth_headers,
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["enabled"] is False

        processed_while_disabled = client.post(
            "/social/automation/dm/process?platform=instagram&sender_handle=@user987&message_text=hello there",
            headers=auth_headers,
        )
        assert processed_while_disabled.status_code == 200
        disabled_payload = processed_while_disabled.json()
        assert disabled_payload["automation_enabled"] is False
        assert disabled_payload["matched_template"] is False
        assert disabled_payload["event"]["reply_text"] == ""

        enable_response = client.post(
            "/social/automation/dm/enable?platform=instagram&enabled=true",
            headers=auth_headers,
        )
        assert enable_response.status_code == 200
        assert enable_response.json()["enabled"] is True

        processed_while_enabled = client.post(
            "/social/automation/dm/process?platform=instagram&sender_handle=@user987&message_text=hello there",
            headers=auth_headers,
        )
        assert processed_while_enabled.status_code == 200
        enabled_payload = processed_while_enabled.json()
        assert enabled_payload["automation_enabled"] is True
        assert enabled_payload["matched_template"] is True
        assert enabled_payload["event"]["reply_text"]


# ============================================================================
# Social Listening Tests
# ============================================================================

class TestSocialListening:
    """Test social listening features"""
    
    @pytest.mark.asyncio
    async def test_add_listening_keywords(self, client: TestClient, auth_headers):
        """Test adding keywords to monitor"""
        response = client.post(
            "/social/listening/keywords/add",
            json={
                "keywords": ["competitor", "industry"],
                "platforms": ["twitter", "reddit"],
            },
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_listening_results(self, client: TestClient, auth_headers):
        """Test getting listening results"""
        response = client.get(
            "/social/listening/results?keyword=competitor&hours=24",
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_listening_returns_trend_and_crisis_intelligence(self, client: TestClient, auth_headers):
        """Listening results should include trend, speaker, and crisis signals."""
        create_response = client.post(
            "/social/content/create",
            json={
                "title": "Listening Intelligence Seed",
                "caption": "Monitoring competitor sentiment closely",
                "media_assets": [],
                "platforms": ["twitter"],
                "requires_approval": False,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        content_id = create_response.json()["id"]

        keyword_response = client.post(
            "/social/listening/keywords/add",
            json={
                "keywords": ["competitor"],
                "platforms": ["twitter"],
            },
            headers=auth_headers,
        )
        assert keyword_response.status_code == 200

        for author, comment_text in [
            ("analyst-1", "competitor rollout was bad"),
            ("analyst-1", "competitor update is broken"),
            ("analyst-2", "competitor support is terrible"),
        ]:
            ingest = client.post(
                f"/social/engagement/comments/{content_id}?platform=twitter&author={author}&text={comment_text}",
                headers=auth_headers,
            )
            assert ingest.status_code == 200

        listening = client.get(
            "/social/listening/results?keyword=competitor&platform=twitter&hours=24",
            headers=auth_headers,
        )
        assert listening.status_code == 200
        payload = listening.json()
        assert payload["total_mentions"] >= 3
        assert payload["sentiment_breakdown"]["negative"] >= 3
        assert payload["top_speakers"]
        assert payload["top_speakers"][0]["author"] == "analyst-1"
        assert payload["keyword_volume"]["competitor"] >= 3
        assert payload["trend"]["direction"] in {"up", "stable", "down"}
        assert payload["crisis_alert"]["triggered"] is True


class TestReviews:
    """Test review ingestion and reply workflows."""

    @pytest.mark.asyncio
    async def test_ingest_and_reply_review(self, client: TestClient, auth_headers):
        ingest = client.post(
            "/social/reviews/ingest?platform=google&author=customer-a&rating=2&text=bad response time",
            headers=auth_headers,
        )
        assert ingest.status_code == 200
        review_id = ingest.json()["review"]["id"]

        reply = client.post(
            f"/social/reviews/replies/{review_id}",
            params={
                "platform": "google",
                "reply_text": "We are improving this now",
            },
            headers=auth_headers,
        )
        assert reply.status_code == 200
        assert reply.json()["success"] is True

        list_reviews = client.get("/social/reviews/hub?platform=google&min_rating=1", headers=auth_headers)
        assert list_reviews.status_code == 200
        assert list_reviews.json()["reply_count"] >= 1
        assert list_reviews.json()["reviews"]


class TestParityStatePersistence:
    """Ensure social parity workflow state survives store reload."""

    @staticmethod
    def _social_migration_sql_text() -> str:
        repo_root = Path(__file__).resolve().parents[4]
        migration_path = repo_root / "services" / "fastapi" / "sql" / "20260523_social_parity_state_schema.sql"
        return migration_path.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_social_state_persist_and_reload(self, client: TestClient, auth_headers, monkeypatch: pytest.MonkeyPatch, tmp_path):
        from backend.fastapi.app.routers import social_media_router as social_router_module

        state_path = tmp_path / "social-parity-state.json"
        monkeypatch.setenv("SOCIAL_PARITY_STATE_PATH", str(state_path))

        # Start from a clean in-memory and on-disk state.
        for store in social_router_module._state_store_maps().values():
            store.clear()
        social_router_module._persist_social_parity_state()

        create_response = client.post(
            "/social/content/create",
            json={
                "title": "Persistence Seed",
                "caption": "State should survive reload",
                "media_assets": [],
                "platforms": ["twitter"],
                "requires_approval": False,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        content_id = create_response.json()["id"]

        publish_response = client.post(
            f"/social/content/{content_id}/publish",
            json={},
            headers=auth_headers,
        )
        assert publish_response.status_code == 200

        comment_response = client.post(
            f"/social/engagement/comments/{content_id}?platform=twitter&author=qa&text=bad latency",
            headers=auth_headers,
        )
        assert comment_response.status_code == 200

        review_response = client.post(
            "/social/reviews/ingest?platform=google&author=qa-user&rating=2&text=bad support wait",
            headers=auth_headers,
        )
        assert review_response.status_code == 200

        assert state_path.exists()

        tenant_id = auth_headers["X-Tenant-Id"]
        social_router_module._parity_mentions_store.clear()
        social_router_module._parity_comments_store.clear()
        social_router_module._parity_reviews_store.clear()

        social_router_module._load_social_parity_state()

        assert social_router_module._parity_mentions_store.get(tenant_id)
        assert social_router_module._parity_comments_store.get(tenant_id)
        assert social_router_module._parity_reviews_store.get(tenant_id)

    @pytest.mark.asyncio
    async def test_social_state_db_persist_and_reload(self, client: TestClient, auth_headers, monkeypatch: pytest.MonkeyPatch, tmp_path):
        from backend.fastapi.app.database import get_db_session
        from backend.fastapi.app.routers import social_media_router as social_router_module

        monkeypatch.setenv("SOCIAL_PARITY_DB_ENABLED", "true")
        monkeypatch.setenv("SOCIAL_PARITY_STATE_PATH", str(tmp_path / "fallback-state.json"))
        social_router_module._db_state_loaded = False

        with get_db_session() as session:
            session.connection().connection.executescript(self._social_migration_sql_text())
            session.execute(text("DELETE FROM social_parity_state_versions"))
            session.execute(text("DELETE FROM social_parity_state"))

        create_response = client.post(
            "/social/content/create",
            json={
                "title": "DB Persistence Seed",
                "caption": "This state should reload from DB",
                "media_assets": [],
                "platforms": ["twitter"],
                "requires_approval": False,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        content_id = create_response.json()["id"]

        comment_response = client.post(
            f"/social/engagement/comments/{content_id}?platform=twitter&author=dbqa&text=bad queue lag",
            headers=auth_headers,
        )
        assert comment_response.status_code == 200

        tenant_id = auth_headers["X-Tenant-Id"]
        social_router_module._parity_content_store.clear()
        social_router_module._parity_mentions_store.clear()
        social_router_module._parity_comments_store.clear()

        with get_db_session() as session:
            social_router_module._load_social_parity_state_from_db(session)

        reloaded_mentions = social_router_module._parity_mentions_store.get(tenant_id, [])
        reloaded_comments = social_router_module._parity_comments_store.get(tenant_id, [])
        assert reloaded_mentions
        assert reloaded_comments
        assert any(str(item.get("id")) == content_id for item in social_router_module._parity_content_store.values())

    @pytest.mark.asyncio
    async def test_social_db_mode_requires_migrated_schema(self, client: TestClient, auth_headers, monkeypatch: pytest.MonkeyPatch, tmp_path):
        from backend.fastapi.app.database import get_db_session
        from backend.fastapi.app.routers import social_media_router as social_router_module

        monkeypatch.setenv("SOCIAL_PARITY_DB_ENABLED", "true")
        monkeypatch.setenv("SOCIAL_PARITY_STATE_PATH", str(tmp_path / "fallback-state.json"))
        social_router_module._db_state_loaded = False

        with get_db_session() as session:
            session.execute(text("DROP TABLE IF EXISTS social_parity_state_versions"))
            session.execute(text("DROP TABLE IF EXISTS social_parity_state"))

        create_response = client.post(
            "/social/content/create",
            json={
                "title": "DB Persistence Seed",
                "caption": "This state should reload from DB",
                "media_assets": [],
                "platforms": ["twitter"],
                "requires_approval": False,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 503
        assert "requires migrated schema" in create_response.json()["detail"]


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegrations:
    """Test platform integration management"""
    
    @pytest.mark.asyncio
    async def test_connect_facebook(self, client: TestClient, auth_headers):
        """Test connecting Facebook account"""
        response = client.post(
            "/social/integrations/facebook/connect",
            json={
                "api_key": "test_key",
                "access_token": "test_token",
                "additional_config": {
                    "page_id": "123456"
                },
            },
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 400]  # 400 if invalid credentials
    
    @pytest.mark.asyncio
    async def test_get_integration_status(self, client: TestClient, auth_headers):
        """Test getting integration status"""
        response = client.get(
            "/social/integrations/status",
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_vendor_catalog_endpoint(self, client: TestClient, auth_headers):
        """Vendor catalog should expose third-party providers and capabilities."""
        response = client.get("/social/integrations/vendors", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload.get("providers"), list)
        assert any(item.get("platform") == "facebook" for item in payload["providers"])

    @pytest.mark.asyncio
    async def test_credential_governance_rotate_revoke_and_status(self, client: TestClient, auth_headers):
        """Credential governance should support status, rotate, and revoke workflows."""
        connect = client.post(
            "/social/integrations/reddit/connect",
            json={
                "api_key": "seed_key",
                "access_token": "seed_token",
            },
            headers=auth_headers,
        )
        assert connect.status_code == 200

        status_before = client.get("/social/integrations/reddit/credentials/status", headers=auth_headers)
        assert status_before.status_code == 200
        assert status_before.json()["connected"] is True

        rotate = client.post(
            "/social/integrations/reddit/credentials/rotate",
            json={
                "api_key": "rotated_key",
                "access_token": "rotated_token",
                "reason": "routine rotation",
            },
            headers=auth_headers,
        )
        assert rotate.status_code == 200
        assert rotate.json()["rotated"] is True

        status_after_rotate = client.get("/social/integrations/reddit/credentials/status", headers=auth_headers)
        assert status_after_rotate.status_code == 200
        assert status_after_rotate.json()["connected"] is True
        assert isinstance(status_after_rotate.json()["events"], list)
        assert any(item["action"] == "rotated" for item in status_after_rotate.json()["events"])

        revoke = client.post(
            "/social/integrations/reddit/credentials/revoke?reason=incident_cleanup",
            headers=auth_headers,
        )
        assert revoke.status_code == 200
        assert revoke.json()["success"] is True

        status_after_revoke = client.get("/social/integrations/reddit/credentials/status", headers=auth_headers)
        assert status_after_revoke.status_code == 200
        assert status_after_revoke.json()["connected"] is False

    @pytest.mark.asyncio
    async def test_contract_matrix_offline(self, client: TestClient, auth_headers):
        """Contract matrix should report readiness without live checks by default."""
        response = client.get("/social/integrations/contracts/matrix", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["live_requested"] is False
        assert isinstance(payload["results"], list)
        assert payload["count"] == len(payload["results"])
        platforms = {item["platform"] for item in payload["results"]}
        assert {"reddit", "threads", "facebook"}.issubset(platforms)

    @pytest.mark.asyncio
    async def test_unified_go_live_gate(self, client: TestClient, auth_headers, monkeypatch: pytest.MonkeyPatch):
        """Unified gate should expose explicit blockers and pass/fail totals."""
        monkeypatch.setenv("SOCIAL_REQUIRED_PLATFORMS", "facebook,reddit")
        monkeypatch.setenv("SOCIAL_CONTRACT_MATRIX_LIVE_ENABLED", "true")
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "3")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")
        monkeypatch.setenv("INBOX_DELIVERY_MAX_BACKOFF_SECONDS", "1")

        # Seed required social credentials
        connect_fb = client.post(
            "/social/integrations/facebook/connect",
            json={"api_key": "fb_key", "access_token": "fb_token"},
            headers=auth_headers,
        )
        assert connect_fb.status_code == 200
        connect_reddit = client.post(
            "/social/integrations/reddit/connect",
            json={"api_key": "rd_key", "access_token": "rd_token"},
            headers=auth_headers,
        )
        assert connect_reddit.status_code == 200

        gate = client.get("/social/ops/go-live-gate", headers=auth_headers)
        assert gate.status_code == 200
        payload = gate.json()
        assert payload["check_count"] >= 5
        assert isinstance(payload["blockers"], list)
        codes = {item["code"] for item in payload["checks"]}
        assert "required_social_credentials_present" in codes
        assert "live_contract_checks_enabled" in codes
        assert "smart_inbox_retry_backoff_sane" in codes


# ============================================================================
# End-to-End Tests
# ============================================================================

class TestEndToEnd:
    """Complete end-to-end workflow tests"""
    
    @pytest.mark.asyncio
    async def test_complete_publishing_workflow(self, client: TestClient, auth_headers):
        """Test complete publishing workflow: create -> approve -> publish -> track"""
        
        # 1. Create content
        create_response = client.post(
            "/social/content/create",
            json={
                "title": "Product Launch",
                "caption": "Announcing our new feature! #launch",
                "media_assets": [
                    {
                        "type": "image",
                        "url": "https://example.com/launch.jpg",
                    }
                ],
                "platforms": ["facebook", "instagram", "twitter"],
                "requires_approval": True,
            },
            headers=auth_headers,
        )
        
        assert create_response.status_code == 200
        content = create_response.json()
        content_id = content['id']
        
        # 2. Approve content
        approve_response = client.post(
            f"/social/content/{content_id}/approve",
            json={"approval_notes": "Approved for launch"},
            headers=auth_headers,
        )
        
        assert approve_response.status_code == 200
        
        # 3. Publish content
        publish_response = client.post(
            f"/social/content/{content_id}/publish",
            json={"platforms": ["facebook", "instagram", "twitter"]},
            headers=auth_headers,
        )
        
        assert publish_response.status_code == 200
        
        # 4. Verify content was updated
        get_response = client.get(
            f"/social/content/{content_id}",
            headers=auth_headers,
        )
        
        assert get_response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_multi_platform_campaign(self, client: TestClient, auth_headers):
        """Test launching campaign across multiple platforms"""
        
        # Create content for multiple platforms
        platforms = ["facebook", "instagram", "linkedin", "twitter", "tiktok"]
        
        response = client.post(
            "/social/content/create",
            json={
                "title": "Q4 Campaign",
                "caption": "Join us for Q4! Limited time offer.",
                "media_assets": [
                    {
                        "type": "video",
                        "url": "https://example.com/campaign.mp4",
                        "duration_seconds": 30,
                    }
                ],
                "platforms": platforms,
                "requires_approval": False,
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert response.json()['platforms'] == platforms


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_bulk_schedule_content(self, client: TestClient, auth_headers):
        """Test bulk scheduling multiple content pieces"""
        
        # Create multiple content items
        content_ids = []
        for i in range(5):
            response = client.post(
                "/social/content/create",
                json={
                    "title": f"Daily Post {i}",
                    "caption": f"Daily content {i}",
                    "media_assets": [],
                    "platforms": ["twitter"],
                },
                headers=auth_headers,
            )
            if response.status_code == 200:
                content_ids.append(response.json()['id'])
        
        # Bulk schedule
        if content_ids:
            schedule_times = [
                (datetime.utcnow() + timedelta(days=i)).isoformat()
                for i in range(len(content_ids))
            ]
            
            response = client.post(
                "/social/calendar/bulk-schedule",
                json={
                    "content_ids": content_ids,
                    "schedule_times": schedule_times,
                },
                headers=auth_headers,
            )
            
            assert response.status_code in [200, 404]


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_create_content_missing_title(self, client: TestClient, auth_headers):
        """Test creating content without required fields"""
        response = client.post(
            "/social/content/create",
            json={
                "caption": "Missing title",
                "media_assets": [],
                "platforms": ["twitter"],
            },
            headers=auth_headers,
        )
        
        assert response.status_code in [400, 422]
    
    def test_publish_nonexistent_content(self, client: TestClient, auth_headers):
        """Test publishing non-existent content"""
        response = client.post(
            "/social/content/invalid-id/publish",
            json={},
            headers=auth_headers,
        )
        
        assert response.status_code in [404, 500]
    
    def test_invalid_platform(self, client: TestClient, auth_headers):
        """Test creating content with invalid platform"""
        response = client.post(
            "/social/content/create",
            json={
                "title": "Test",
                "caption": "Test",
                "media_assets": [],
                "platforms": ["invalid_platform"],
            },
            headers=auth_headers,
        )
        
        assert response.status_code in [400, 422]
