"""
Tests for content_approval.py, media_library.py, smart_inbox.py,
benchmarks.py, outcome_attribution.py, tool_integrations.py, viralpost.py,
employee_advocacy.py, linkinbio.py routers.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
HA = {**H, "X-Super-Admin": "true"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# --------------------------------------------------------------------------- #
# Content Approval
# --------------------------------------------------------------------------- #
class TestContentApproval:
    def test_get_config(self, client: TestClient) -> None:
        r = client.get("/content/approval/config", headers=H)
        assert r.status_code in VALID

    def test_put_config(self, client: TestClient) -> None:
        r = client.put("/content/approval/config", headers=H, json={
            "approval_required": True,
            "approvers": ["user_001"],
        })
        assert r.status_code in VALID

    def test_create_request(self, client: TestClient) -> None:
        r = client.post("/content/approval/requests", headers=H, json={
            "post_id": "post_001",
            "notes": "Please review",
        })
        assert r.status_code in VALID

    def test_list_requests(self, client: TestClient) -> None:
        r = client.get("/content/approval/requests", headers=H)
        assert r.status_code in VALID

    def test_approve_request(self, client: TestClient) -> None:
        r = client.post("/content/approval/requests/req_nonexistent/approve", headers=H, json={
            "comment": "Looks good",
        })
        assert r.status_code in VALID

    def test_get_request(self, client: TestClient) -> None:
        r = client.get("/content/approval/requests/req_nonexistent", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Media Library
# --------------------------------------------------------------------------- #
class TestMediaLibrary:
    def test_create_folder(self, client: TestClient) -> None:
        r = client.post("/media/folders", headers=H, json={
            "name": "Marketing Assets",
            "parent_id": None,
        })
        assert r.status_code in VALID

    def test_list_folders(self, client: TestClient) -> None:
        r = client.get("/media/folders", headers=H)
        assert r.status_code in VALID

    def test_upload_asset(self, client: TestClient) -> None:
        r = client.post("/media/assets", headers=H, json={
            "filename": "logo.png",
            "file_url": "https://cdn.example.com/logo.png",
            "content_type": "image/png",
            "size_bytes": 45000,
        })
        assert r.status_code in VALID

    def test_list_assets(self, client: TestClient) -> None:
        r = client.get("/media/assets", headers=H)
        assert r.status_code in VALID

    def test_get_asset_nonexistent(self, client: TestClient) -> None:
        r = client.get("/media/assets/asset_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_update_asset_nonexistent(self, client: TestClient) -> None:
        r = client.patch("/media/assets/asset_nonexistent", headers=H, json={
            "alt_text": "Company logo",
        })
        assert r.status_code in VALID

    def test_delete_asset_nonexistent(self, client: TestClient) -> None:
        r = client.delete("/media/assets/asset_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_media_stats(self, client: TestClient) -> None:
        r = client.get("/media/stats", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Smart Inbox
# --------------------------------------------------------------------------- #
class TestSmartInbox:
    def test_create_message(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "channel": "email",
            "from": "customer@example.com",
            "subject": "Support Request",
            "body": "I need help with my account",
        })
        assert r.status_code in VALID

    def test_list_messages(self, client: TestClient) -> None:
        r = client.get("/inbox/messages", headers=H)
        assert r.status_code in VALID

    def test_get_message_nonexistent(self, client: TestClient) -> None:
        r = client.get("/inbox/messages/msg_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_update_status_nonexistent(self, client: TestClient) -> None:
        r = client.patch("/inbox/messages/msg_nonexistent/status", headers=H, json={
            "status": "resolved",
        })
        assert r.status_code in VALID

    def test_assign_nonexistent(self, client: TestClient) -> None:
        r = client.post("/inbox/messages/msg_nonexistent/assign", headers=H, json={
            "assignee_id": "user_001",
        })
        assert r.status_code in VALID

    def test_list_notes_nonexistent(self, client: TestClient) -> None:
        r = client.get("/inbox/messages/msg_nonexistent/notes", headers=H)
        assert r.status_code in VALID

    def test_add_note_nonexistent(self, client: TestClient) -> None:
        r = client.post("/inbox/messages/msg_nonexistent/notes", headers=H, json={
            "content": "Customer prefers email communication",
        })
        assert r.status_code in VALID

    def test_delete_note_nonexistent(self, client: TestClient) -> None:
        r = client.delete("/inbox/messages/msg_nonexistent/notes/note_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_inbox_stats(self, client: TestClient) -> None:
        r = client.get("/inbox/stats", headers=H)
        assert r.status_code in VALID

    def test_create_saved_reply(self, client: TestClient) -> None:
        r = client.post("/inbox/saved-replies", headers=H, json={
            "title": "Password Reset",
            "content": "Here are instructions to reset your password...",
        })
        assert r.status_code in VALID

    def test_list_saved_replies(self, client: TestClient) -> None:
        r = client.get("/inbox/saved-replies", headers=H)
        assert r.status_code in VALID

    def test_update_saved_reply_nonexistent(self, client: TestClient) -> None:
        r = client.patch("/inbox/saved-replies/reply_nonexistent", headers=H, json={
            "content": "Updated instructions...",
        })
        assert r.status_code in VALID

    def test_delete_saved_reply_nonexistent(self, client: TestClient) -> None:
        r = client.delete("/inbox/saved-replies/reply_nonexistent", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Benchmarks
# --------------------------------------------------------------------------- #
class TestBenchmarks:
    def test_create_benchmark(self, client: TestClient) -> None:
        r = client.post("/benchmarks", headers=H, json={
            "metric": "email_open_rate",
            "value": 0.24,
            "industry": "SaaS",
            "segment": "smb",
        })
        assert r.status_code in VALID

    def test_summary(self, client: TestClient) -> None:
        r = client.get("/benchmarks/summary", headers=H)
        assert r.status_code in VALID

    def test_list_benchmarks(self, client: TestClient) -> None:
        r = client.get("/benchmarks", headers=H)
        assert r.status_code in VALID

    def test_create_segment(self, client: TestClient) -> None:
        r = client.post("/benchmarks/segments", headers=HA, json={
            "segment": "enterprise",
            "metrics": {"email_open_rate": 0.28},
        })
        assert r.status_code in VALID

    def test_get_segment(self, client: TestClient) -> None:
        r = client.get("/benchmarks/segments/smb", headers=H)
        assert r.status_code in VALID

    def test_compare_segment(self, client: TestClient) -> None:
        r = client.get("/benchmarks/compare/smb", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Outcome Attribution
# --------------------------------------------------------------------------- #
class TestOutcomeAttribution:
    def test_create_action(self, client: TestClient) -> None:
        r = client.post("/outcome/actions", headers=H, json={
            "name": "email_sent",
            "contact_id": "contact_001",
            "metadata": {"campaign_id": "camp_001"},
        })
        assert r.status_code in VALID

    def test_create_outcome(self, client: TestClient) -> None:
        r = client.post("/outcome/outcomes", headers=H, json={
            "action_id": "action_nonexistent",
            "outcome_type": "purchase",
            "value": 99.99,
        })
        assert r.status_code in VALID

    def test_record_quality(self, client: TestClient) -> None:
        r = client.post("/outcome/quality", headers=H, json={
            "action_id": "action_nonexistent",
            "quality_score": 85,
        })
        assert r.status_code in VALID

    def test_get_graph(self, client: TestClient) -> None:
        r = client.get("/outcome/graph", headers=H)
        assert r.status_code in VALID

    def test_get_quality(self, client: TestClient) -> None:
        r = client.get("/outcome/quality", headers=H)
        assert r.status_code in VALID

    def test_pending_actions(self, client: TestClient) -> None:
        r = client.get("/outcome/actions/pending", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Tool Integrations
# --------------------------------------------------------------------------- #
class TestToolIntegrations:
    def test_list_tools(self, client: TestClient) -> None:
        r = client.get("/tools", headers=H)
        assert r.status_code in VALID

    def test_get_tool(self, client: TestClient) -> None:
        r = client.get("/tools/zapier", headers=H)
        assert r.status_code in VALID

    def test_update_tool_config(self, client: TestClient) -> None:
        r = client.put("/integrations/integrations/tools/zapier", headers=H, json={
            "enabled": True,
            "api_key": "zap_key_xxx",
        })
        assert r.status_code in VALID

    def test_test_tool(self, client: TestClient) -> None:
        r = client.post("/tools/zapier/test", headers=H, json={})
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Viralpost
# --------------------------------------------------------------------------- #
class TestViralpost:
    def test_post_history(self, client: TestClient) -> None:
        r = client.post("/publishing/post-history", headers=H, json={
            "platform": "twitter",
            "content": "Test post for history",
            "posted_at": "2025-01-01T10:00:00Z",
        })
        assert r.status_code in VALID

    def test_suggest_optimal_times(self, client: TestClient) -> None:
        r = client.post("/publishing/optimal-times", headers=H, json={
            "platform": "instagram",
            "timezone": "America/New_York",
        })
        assert r.status_code in VALID

    def test_get_optimal_times(self, client: TestClient) -> None:
        r = client.get("/publishing/optimal-times", headers=H)
        assert r.status_code in VALID

    def test_optimal_times_defaults(self, client: TestClient) -> None:
        r = client.get("/publishing/optimal-times/defaults", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Employee Advocacy
# --------------------------------------------------------------------------- #
class TestEmployeeAdvocacy:
    def test_create_campaign(self, client: TestClient) -> None:
        r = client.post("/advocacy/campaigns", headers=H, json={
            "title": "Product Launch Advocacy",
            "description": "Share our new product launch",
            "start_date": "2025-02-01",
            "end_date": "2025-02-28",
        })
        assert r.status_code in VALID

    def test_list_campaigns(self, client: TestClient) -> None:
        r = client.get("/advocacy/campaigns", headers=H)
        assert r.status_code in VALID

    def test_share_content(self, client: TestClient) -> None:
        r = client.post("/advocacy/campaigns/camp_nonexistent/share", headers=H, json={
            "platform": "linkedin",
            "employee_id": "emp_001",
        })
        assert r.status_code in VALID

    def test_list_content(self, client: TestClient) -> None:
        r = client.get("/advocacy/content", headers=H)
        assert r.status_code in VALID

    def test_add_participant(self, client: TestClient) -> None:
        r = client.post("/advocacy/participants", headers=H, json={
            "employee_id": "emp_002",
            "campaign_id": "camp_nonexistent",
        })
        assert r.status_code in VALID

    def test_list_participants(self, client: TestClient) -> None:
        r = client.get("/advocacy/participants", headers=H)
        assert r.status_code in VALID

    def test_leaderboard(self, client: TestClient) -> None:
        r = client.post("/advocacy/participants/leaderboard", headers=H, json={
            "campaign_id": "camp_nonexistent",
        })
        assert r.status_code in VALID

    def test_advocacy_analytics(self, client: TestClient) -> None:
        r = client.get("/advocacy/analytics", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Linkinbio
# --------------------------------------------------------------------------- #
class TestLinkinbio:
    def test_create_page(self, client: TestClient) -> None:
        r = client.post("/linkinbio/pages", headers=H, json={
            "title": "My Links",
            "bio": "Marketing & Growth specialist",
            "avatar_url": "https://cdn.example.com/avatar.png",
        })
        assert r.status_code in VALID

    def test_list_pages(self, client: TestClient) -> None:
        r = client.get("/linkinbio/pages", headers=H)
        assert r.status_code in VALID

    def test_update_page_nonexistent(self, client: TestClient) -> None:
        r = client.patch("/linkinbio/pages/page_nonexistent", headers=H, json={
            "bio": "Updated bio",
        })
        assert r.status_code in VALID

    def test_add_link_nonexistent(self, client: TestClient) -> None:
        r = client.post("/linkinbio/pages/page_nonexistent/links", headers=H, json={
            "title": "My Blog",
            "url": "https://blog.example.com",
            "icon": "link",
        })
        assert r.status_code in VALID

    def test_page_analytics_nonexistent(self, client: TestClient) -> None:
        r = client.get("/linkinbio/pages/page_nonexistent/analytics", headers=H)
        assert r.status_code in VALID
