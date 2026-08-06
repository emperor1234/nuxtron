"""Coverage for smart_inbox.py — full route handler bodies."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "smart-inbox-coverage-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestSmartInboxCoverage:
    """Cover all Smart Inbox route handler bodies."""

    # ── Message ingestion ────────────────────────────────────────────────────

    def test_ingest_question_message(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "instagram",
                "source_type": "comment",
                "author_handle": "user_curious",
                "author_display_name": "Curious User",
                "author_follower_count": 1200,
                "text": "What are your shipping times? Do you ship internationally?",
                "external_message_id": "ext-001",
                "crm_contact_id": "crm-123",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["created"] is True
        assert data["message"]["message_type"] == "question"
        assert data["message"]["sentiment"] in ("neutral", "negative")
        assert "suggested_replies" in data["message"]

    def test_ingest_dedup_same_external_id(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "instagram",
                "source_type": "comment",
                "author_handle": "user_curious",
                "text": "What are your shipping times?",
                "external_message_id": "ext-001",  # same as above
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["created"] is False

    def test_ingest_complaint_message(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "facebook",
                "source_type": "dm",
                "author_handle": "unhappy_customer",
                "author_follower_count": 500,
                "text": "This product is terrible and broken. I want a refund!",
                "external_message_id": "ext-complaint-001",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["message"]["message_type"] == "complaint"
        assert data["message"]["sentiment"] == "negative"

    def test_ingest_compliment_message(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "linkedin",
                "source_type": "mention",
                "author_handle": "happy_fan",
                "author_follower_count": 50000,
                "text": "This product is amazing and awesome! Thank you so much!",
                "external_message_id": "ext-compliment-001",
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["message"]["message_type"] == "compliment"
        assert r.json()["message"]["sentiment"] == "positive"

    def test_ingest_spam_message(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "facebook",
                "source_type": "comment",
                "author_handle": "spammer_99",
                "author_follower_count": 0,
                "text": "click here to win free money limited offer congratulations you won!",
                "external_message_id": "ext-spam-001",
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["message"]["message_type"] == "spam"

    def test_ingest_crisis_message(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "instagram",
                "source_type": "dm",
                "author_handle": "concerned_media",
                "author_follower_count": 100000,
                "text": "There's a safety recall on your product. There's a potential lawsuit developing.",
                "external_message_id": "ext-crisis-001",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["message"]["message_type"] == "crisis"
        assert data["message"]["priority_score"] >= 100

    def test_ingest_conversation_neutral(self, client: TestClient) -> None:
        """No question mark, not pos/neg dominant → 'conversation' + 'neutral'."""
        r = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "linkedin",
                "source_type": "dm",
                "author_handle": "neutral_user",
                "text": "Hello, I just wanted to say hi.",
                "external_message_id": "ext-conv-001",
                "parent_message_id": "parent-thread-1",
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["message"]["message_type"] == "conversation"

    # ── List messages ────────────────────────────────────────────────────────

    def test_list_messages(self, client: TestClient) -> None:
        r = client.get("/inbox/messages", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 5
        # Sorted by priority_score descending
        scores = [m["priority_score"] for m in data["messages"]]
        assert scores == sorted(scores, reverse=True)

    def test_list_messages_by_status(self, client: TestClient) -> None:
        r = client.get("/inbox/messages?status=pending", headers=H)
        assert r.status_code == 200
        for m in r.json()["messages"]:
            assert m["status"] == "pending"

    def test_list_messages_by_network(self, client: TestClient) -> None:
        r = client.get("/inbox/messages?network=instagram", headers=H)
        assert r.status_code == 200
        for m in r.json()["messages"]:
            assert m["network"] == "instagram"

    def test_list_messages_by_type(self, client: TestClient) -> None:
        r = client.get("/inbox/messages?message_type=complaint", headers=H)
        assert r.status_code == 200
        for m in r.json()["messages"]:
            assert m["message_type"] == "complaint"

    def test_list_messages_by_sentiment(self, client: TestClient) -> None:
        r = client.get("/inbox/messages?sentiment=positive", headers=H)
        assert r.status_code == 200
        for m in r.json()["messages"]:
            assert m["sentiment"] == "positive"

    def test_list_messages_unread_only(self, client: TestClient) -> None:
        r = client.get("/inbox/messages?unread_only=true", headers=H)
        assert r.status_code == 200
        for m in r.json()["messages"]:
            assert not m["read"]

    def test_list_messages_assigned_filter(self, client: TestClient) -> None:
        r = client.get("/inbox/messages?assigned_to=nobody_yet", headers=H)
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_mention_alerts(self, client: TestClient) -> None:
        seed = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "instagram",
                "source_type": "mention",
                "author_handle": "alert_seed_user",
                "author_follower_count": 25000,
                "text": "This is broken and I need help right now.",
                "external_message_id": "ext-mention-alert-seed-1",
            },
        )
        assert seed.status_code in (200, 201)
        r = client.get("/inbox/mentions/alerts", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        assert data["count"] >= 1
        severities = {item["severity"] for item in data["alerts"]}
        assert severities.intersection({"medium", "high", "critical"})

    # ── Get single message ───────────────────────────────────────────────────

    def test_get_message_marks_read(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][0]["id"]

        r = client.get(f"/inbox/messages/{msg_id}", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["message"]["read"] is True
        assert "notes" in data
        assert "lock" in data

    def test_get_message_with_thread(self, client: TestClient) -> None:
        # Ingest a threaded reply
        client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "linkedin",
                "source_type": "dm",
                "author_handle": "thread_user",
                "text": "A follow-up message in the thread.",
                "parent_message_id": "parent-thread-1",
                "external_message_id": "ext-thread-reply-1",
            },
        )
        # Get the original conv message with parent_message_id=parent-thread-1
        list_r = client.get("/inbox/messages?message_type=conversation", headers=H)
        conv_msg_id = list_r.json()["messages"][0]["id"]
        r = client.get(f"/inbox/messages/{conv_msg_id}", headers=H)
        assert r.status_code == 200
        # thread may or may not be populated depending on order, but no error

    def test_get_message_missing(self, client: TestClient) -> None:
        r = client.get("/inbox/messages/9999", headers=H)
        assert r.status_code == 404

    # ── Update message ───────────────────────────────────────────────────────

    def test_update_message_assign_and_tag(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][0]["id"]

        r = client.patch(
            f"/inbox/messages/{msg_id}",
            headers=H,
            json={
                "assigned_to": "agent_sarah",
                "status": "in_progress",
                "tags": ["billing", "urgent"],
                "due_at": "2026-06-01T09:00:00Z",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["message"]["assigned_to"] == "agent_sarah"
        assert data["message"]["status"] == "in_progress"
        assert "billing" in data["message"]["tags"]

    def test_update_message_status_complete(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][0]["id"]
        r = client.patch(f"/inbox/messages/{msg_id}", headers=H, json={"status": "complete"})
        assert r.status_code in (200, 201)
        assert r.json()["message"]["status"] == "complete"
        assert "completed_at" in r.json()["message"]

    def test_update_message_invalid_status(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][0]["id"]
        r = client.patch(f"/inbox/messages/{msg_id}", headers=H, json={"status": "not_a_status"})
        assert r.status_code == 422

    def test_update_message_missing(self, client: TestClient) -> None:
        r = client.patch("/inbox/messages/9999", headers=H, json={"status": "pending"})
        assert r.status_code == 404

    # ── Internal notes ───────────────────────────────────────────────────────

    def test_add_note(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][0]["id"]

        r = client.post(
            f"/inbox/messages/{msg_id}/notes",
            headers=H,
            json={"author": "agent_sarah", "note": "Customer was very upset. Escalating to Tier-2 support."},
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["note"]["author"] == "agent_sarah"
        assert data["note"]["message_id"] == msg_id

    def test_add_note_missing_message(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/messages/9999/notes",
            headers=H,
            json={"author": "agent_bob", "note": "Test note"},
        )
        assert r.status_code == 404

    def test_list_notes(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][0]["id"]

        r = client.get(f"/inbox/messages/{msg_id}/notes", headers=H)
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_list_notes_missing_message(self, client: TestClient) -> None:
        r = client.get("/inbox/messages/9999/notes", headers=H)
        assert r.status_code == 404

    def test_auto_respond_with_saved_reply(self, client: TestClient) -> None:
        create_reply = client.post(
            "/inbox/saved-replies",
            headers=H,
            json={
                "title": "Instagram Support",
                "body": "Thanks for the mention. We can help right away.",
                "networks": ["instagram"],
            },
        )
        assert create_reply.status_code in (200, 201)
        reply_id = create_reply.json()["reply"]["id"]

        ingest = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "instagram",
                "source_type": "mention",
                "author_handle": "brand_fan",
                "text": "Love this drop!",
                "external_message_id": "ext-auto-respond-1",
            },
        )
        assert ingest.status_code in (200, 201)
        message_id = ingest.json()["message"]["id"]

        respond = client.post(
            f"/inbox/messages/{message_id}/auto-respond",
            headers=H,
            json={"saved_reply_id": reply_id, "responder": "agent_jade"},
        )
        assert respond.status_code == 200
        payload = respond.json()
        assert payload["response"]["source"] == "saved_reply"
        assert payload["response"]["delivered"] is True
        assert payload["message"]["status"] == "complete"
        assert payload["message"]["replied"] is True

    def test_auto_respond_requires_approval_for_crisis(self, client: TestClient) -> None:
        ingest = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "twitter",
                "source_type": "mention",
                "author_handle": "newsdesk",
                "author_follower_count": 150000,
                "text": "There is a dangerous safety scandal and lawsuit risk.",
                "external_message_id": "ext-auto-respond-crisis-1",
            },
        )
        assert ingest.status_code in (200, 201)
        message_id = ingest.json()["message"]["id"]

        respond = client.post(
            f"/inbox/messages/{message_id}/auto-respond",
            headers=H,
            json={"suggestion_index": 0, "responder": "agent_lee"},
        )
        assert respond.status_code == 200
        payload = respond.json()
        assert payload["response"]["approval_required"] is True
        assert payload["response"]["delivered"] is False
        assert payload["message"]["status"] == "requires_approval"
        assert payload["message"]["replied"] is False

    def test_approve_staged_auto_response(self, client: TestClient) -> None:
        ingest = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "twitter",
                "source_type": "mention",
                "author_handle": "press_watch",
                "author_follower_count": 175000,
                "text": "This safety scandal needs an immediate response.",
                "external_message_id": "ext-auto-respond-crisis-approve-1",
            },
        )
        assert ingest.status_code in (200, 201)
        message_id = ingest.json()["message"]["id"]

        stage = client.post(
            f"/inbox/messages/{message_id}/auto-respond",
            headers=H,
            json={"suggestion_index": 1, "responder": "agent_mina"},
        )
        assert stage.status_code == 200
        assert stage.json()["message"]["status"] == "requires_approval"

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(return_value={"id": "vendor-reply-1", "ok": True})
            approve = client.post(
                f"/inbox/messages/{message_id}/approve-response",
                headers=H,
                json={"approver": "manager_zoe", "note": "Approved for public reply"},
            )

        assert approve.status_code == 200
        payload = approve.json()
        assert payload["message"]["status"] == "complete"
        assert payload["message"]["replied"] is True
        assert payload["response"]["approved_by"] == "manager_zoe"
        assert payload["response"]["delivered"] is True
        assert payload["message"]["response_delivery_vendor"] == "twitter_api"
        assert payload["message"]["response_delivery_result"]["id"] == "vendor-reply-1"
        mocked_vendor_manager.make_request.assert_awaited_once()

        alerts = client.get("/inbox/mentions/alerts", headers=H)
        assert alerts.status_code == 200
        unresolved_ids = {item["message_id"] for item in alerts.json()["alerts"]}
        assert message_id not in unresolved_ids

    def test_reject_staged_auto_response(self, client: TestClient) -> None:
        ingest = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "twitter",
                "source_type": "mention",
                "author_handle": "risk_signal",
                "author_follower_count": 95000,
                "text": "Potential legal safety issue needs escalation.",
                "external_message_id": "ext-auto-respond-crisis-reject-1",
            },
        )
        assert ingest.status_code in (200, 201)
        message_id = ingest.json()["message"]["id"]

        stage = client.post(
            f"/inbox/messages/{message_id}/auto-respond",
            headers=H,
            json={"suggestion_index": 2, "responder": "agent_nova"},
        )
        assert stage.status_code == 200
        assert stage.json()["message"]["status"] == "requires_approval"

        reject = client.post(
            f"/inbox/messages/{message_id}/reject-response",
            headers=H,
            json={"reviewer": "manager_zoe", "note": "Tone needs revision before reply"},
        )
        assert reject.status_code == 200
        payload = reject.json()
        assert payload["message"]["status"] == "in_progress"
        assert payload["message"]["replied"] is False
        assert payload["response"]["rejected_by"] == "manager_zoe"
        assert payload["response"]["delivered"] is False

    def test_pending_approvals_queue(self, client: TestClient) -> None:
        ingest = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "twitter",
                "source_type": "mention",
                "author_handle": "review_queue_signal",
                "author_follower_count": 125000,
                "text": "Major safety concern and legal escalation risk.",
                "external_message_id": "ext-approval-queue-1",
            },
        )
        assert ingest.status_code in (200, 201)
        message_id = ingest.json()["message"]["id"]

        stage = client.post(
            f"/inbox/messages/{message_id}/auto-respond",
            headers=H,
            json={"suggestion_index": 0, "responder": "agent_sam"},
        )
        assert stage.status_code == 200
        assert stage.json()["message"]["status"] == "requires_approval"

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.get_credentials.return_value = None
            queue = client.get("/inbox/approvals/pending?network=twitter", headers=H)

        assert queue.status_code == 200
        payload = queue.json()
        assert payload["count"] >= 1
        item = next(item for item in payload["items"] if item["message_id"] == message_id)
        assert item["delivery_vendor"] == "twitter_api"
        assert item["delivery_ready"] is False
        assert "Missing vendor credentials" in item["delivery_blocker"]

    def test_approve_response_failure_enters_delivery_dlq(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "2")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")

        ingest = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "twitter",
                "source_type": "mention",
                "author_handle": "delivery_fail_signal",
                "author_follower_count": 140000,
                "text": "Urgent safety issue requires official response.",
                "external_message_id": "ext-delivery-fail-1",
            },
        )
        assert ingest.status_code in (200, 201)
        message_id = ingest.json()["message"]["id"]

        stage = client.post(
            f"/inbox/messages/{message_id}/auto-respond",
            headers=H,
            json={"suggestion_index": 0, "responder": "agent_fail_case"},
        )
        assert stage.status_code == 200
        assert stage.json()["message"]["status"] == "requires_approval"

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=RuntimeError("provider timeout"))
            approve = client.post(
                f"/inbox/messages/{message_id}/approve-response",
                headers=H,
                json={"approver": "manager_zoe", "note": "Attempting live send"},
            )

        assert approve.status_code == 502

        dlq = client.get("/inbox/delivery-failures", headers=H)
        assert dlq.status_code == 200
        payload = dlq.json()
        assert payload["count"] >= 1
        item = next(item for item in payload["items"] if item["message_id"] == message_id)
        assert item["status"] == "pending_retry"
        assert item["vendor_id"] == "twitter_api"
        assert len(item["errors"]) == 2
        assert item["payload"]["idempotency_key"].startswith("inbox-reply:")

    def test_replay_delivery_failure_succeeds_idempotently(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "2")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")

        ingest = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "twitter",
                "source_type": "mention",
                "author_handle": "delivery_retry_signal",
                "author_follower_count": 160000,
                "text": "Serious safety escalation requires immediate approved reply.",
                "external_message_id": "ext-delivery-replay-1",
            },
        )
        assert ingest.status_code in (200, 201)
        message_id = ingest.json()["message"]["id"]

        stage = client.post(
            f"/inbox/messages/{message_id}/auto-respond",
            headers=H,
            json={"suggestion_index": 0, "responder": "agent_retry_case"},
        )
        assert stage.status_code == 200

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=RuntimeError("provider timeout"))
            approve = client.post(
                f"/inbox/messages/{message_id}/approve-response",
                headers=H,
                json={"approver": "manager_zoe", "note": "Initial send attempt"},
            )

        assert approve.status_code == 502

        dlq = client.get("/inbox/delivery-failures", headers=H)
        assert dlq.status_code == 200
        failure = next(item for item in dlq.json()["items"] if item["message_id"] == message_id)

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(return_value={"id": "vendor-retry-1", "ok": True})
            replay = client.post(
                f"/inbox/delivery-failures/{failure['id']}/replay",
                headers=H,
                json={"operator": "manager_zoe", "note": "Retry delivery from DLQ"},
            )

            assert replay.status_code == 200
            replay_payload = replay.json()
            assert replay_payload["replayed"] is True
            assert replay_payload["message"]["response_delivery_status"] == "sent"
            assert replay_payload["message"]["response_delivery_attempts"] == 3
            assert replay_payload["failure"]["status"] == "resolved"
            assert replay_payload["response"]["idempotency_key"] == failure["payload"]["idempotency_key"]
            assert mocked_vendor_manager.make_request.await_count == 1
            _, kwargs = mocked_vendor_manager.make_request.await_args
            assert kwargs["headers"]["Idempotency-Key"] == failure["payload"]["idempotency_key"]

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(return_value={"id": "vendor-retry-2", "ok": True})
            replay_again = client.post(
                f"/inbox/delivery-failures/{failure['id']}/replay",
                headers=H,
                json={"operator": "manager_zoe", "note": "Duplicate retry should skip"},
            )

        assert replay_again.status_code == 200
        replay_again_payload = replay_again.json()
        assert replay_again_payload["replayed"] is False
        assert replay_again_payload["reason"] == "already_delivered"
        mocked_vendor_manager.make_request.assert_not_awaited()

    def test_resolve_delivery_failure_returns_message_to_manual_handling(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "2")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")

        ingest = client.post(
            "/inbox/messages",
            headers=H,
            json={
                "network": "twitter",
                "source_type": "mention",
                "author_handle": "delivery_manual_followup_signal",
                "author_follower_count": 110000,
                "text": "Urgent legal safety issue needs executive response.",
                "external_message_id": "ext-delivery-resolve-1",
            },
        )
        assert ingest.status_code in (200, 201)
        message_id = ingest.json()["message"]["id"]

        stage = client.post(
            f"/inbox/messages/{message_id}/auto-respond",
            headers=H,
            json={"suggestion_index": 0, "responder": "agent_manual_case"},
        )
        assert stage.status_code == 200

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=RuntimeError("provider timeout"))
            approve = client.post(
                f"/inbox/messages/{message_id}/approve-response",
                headers=H,
                json={"approver": "manager_zoe", "note": "Initial send attempt"},
            )

        assert approve.status_code == 502

        dlq = client.get("/inbox/delivery-failures?status=pending_retry", headers=H)
        assert dlq.status_code == 200
        failure = next(item for item in dlq.json()["items"] if item["message_id"] == message_id)

        resolve = client.post(
            f"/inbox/delivery-failures/{failure['id']}/resolve",
            headers=H,
            json={"operator": "manager_zoe", "note": "Escalating to manual executive handling"},
        )

        assert resolve.status_code == 200
        resolve_payload = resolve.json()
        assert resolve_payload["resolved"] is True
        assert resolve_payload["failure"]["status"] == "resolved"
        assert resolve_payload["failure"]["resolution"] == "manual_followup"
        assert resolve_payload["message"]["status"] == "in_progress"
        assert resolve_payload["message"]["response_delivery_status"] == "manual_followup_required"
        assert resolve_payload["message"]["response_delivery_failure_id"] is None

        resolved_list = client.get("/inbox/delivery-failures?status=resolved", headers=H)
        assert resolved_list.status_code == 200
        resolved_item = next(item for item in resolved_list.json()["items"] if item["id"] == failure["id"])
        assert resolved_item["resolution"] == "manual_followup"

        resolve_again = client.post(
            f"/inbox/delivery-failures/{failure['id']}/resolve",
            headers=H,
            json={"operator": "manager_zoe", "note": "No-op second resolution"},
        )
        assert resolve_again.status_code == 200
        assert resolve_again.json()["resolved"] is False
        assert resolve_again.json()["reason"] == "already_resolved"

    def test_bulk_resolve_delivery_failures(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "2")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")

        message_ids: list[int] = []
        for seed_idx in (1, 2):
            ingest = client.post(
                "/inbox/messages",
                headers=H,
                json={
                    "network": "twitter",
                    "source_type": "mention",
                    "author_handle": f"bulk_resolve_signal_{seed_idx}",
                    "author_follower_count": 120000 + seed_idx,
                    "text": "Critical safety issue needs approved response and then manual handling.",
                    "external_message_id": f"ext-delivery-bulk-resolve-{seed_idx}",
                },
            )
            assert ingest.status_code in (200, 201)
            message_id = ingest.json()["message"]["id"]
            message_ids.append(message_id)

            stage = client.post(
                f"/inbox/messages/{message_id}/auto-respond",
                headers=H,
                json={"suggestion_index": 0, "responder": "agent_bulk_resolve_case"},
            )
            assert stage.status_code == 200

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=RuntimeError("provider timeout"))
            for message_id in message_ids:
                approve = client.post(
                    f"/inbox/messages/{message_id}/approve-response",
                    headers=H,
                    json={"approver": "manager_zoe", "note": "Trigger DLQ for bulk resolve test"},
                )
                assert approve.status_code == 502

        dlq = client.get("/inbox/delivery-failures?status=pending_retry", headers=H)
        assert dlq.status_code == 200
        failures = [item for item in dlq.json()["items"] if item["message_id"] in message_ids]
        assert len(failures) == 2
        failure_ids = [item["id"] for item in failures]

        bulk_resolve = client.post(
            "/inbox/delivery-failures/resolve-bulk",
            headers=H,
            json={
                "failure_ids": [failure_ids[0], failure_ids[0], failure_ids[1], 999999],
                "operator": "manager_zoe",
                "note": "Bulk escalation to manual handling",
            },
        )
        assert bulk_resolve.status_code == 200
        bulk_payload = bulk_resolve.json()
        assert bulk_payload["resolved_count"] == 2
        assert bulk_payload["already_resolved_count"] == 0
        assert bulk_payload["not_found_count"] == 1
        assert set(bulk_payload["resolved_ids"]) == set(failure_ids)
        assert bulk_payload["not_found_ids"] == [999999]
        assert set(bulk_payload["updated_message_ids"]) == set(message_ids)

        for message_id in message_ids:
            message_r = client.get(f"/inbox/messages/{message_id}", headers=H)
            assert message_r.status_code == 200
            message = message_r.json()["message"]
            assert message["status"] == "in_progress"
            assert message["response_delivery_status"] == "manual_followup_required"
            assert message["response_delivery_failure_id"] is None

        bulk_resolve_again = client.post(
            "/inbox/delivery-failures/resolve-bulk",
            headers=H,
            json={
                "failure_ids": failure_ids,
                "operator": "manager_zoe",
                "note": "Second pass should no-op",
            },
        )
        assert bulk_resolve_again.status_code == 200
        again_payload = bulk_resolve_again.json()
        assert again_payload["resolved_count"] == 0
        assert again_payload["already_resolved_count"] == 2
        assert again_payload["not_found_count"] == 0

    def test_bulk_replay_delivery_failures(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "2")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")

        message_ids: list[int] = []
        for seed_idx in (1, 2):
            ingest = client.post(
                "/inbox/messages",
                headers=H,
                json={
                    "network": "twitter",
                    "source_type": "mention",
                    "author_handle": f"bulk_replay_signal_{seed_idx}",
                    "author_follower_count": 130000 + seed_idx,
                    "text": "Critical safety issue requires response replay workflow.",
                    "external_message_id": f"ext-delivery-bulk-replay-{seed_idx}",
                },
            )
            assert ingest.status_code in (200, 201)
            message_id = ingest.json()["message"]["id"]
            message_ids.append(message_id)

            stage = client.post(
                f"/inbox/messages/{message_id}/auto-respond",
                headers=H,
                json={"suggestion_index": 0, "responder": "agent_bulk_replay_case"},
            )
            assert stage.status_code == 200

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=RuntimeError("provider timeout"))
            for message_id in message_ids:
                approve = client.post(
                    f"/inbox/messages/{message_id}/approve-response",
                    headers=H,
                    json={"approver": "manager_zoe", "note": "Create DLQ for bulk replay"},
                )
                assert approve.status_code == 502

        dlq = client.get("/inbox/delivery-failures?status=pending_retry", headers=H)
        assert dlq.status_code == 200
        failures = [item for item in dlq.json()["items"] if item["message_id"] in message_ids]
        assert len(failures) == 2
        failure_ids = [item["id"] for item in failures]

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=[
                {"id": "vendor-bulk-replay-1", "ok": True},
                {"id": "vendor-bulk-replay-2", "ok": True},
            ])
            bulk_replay = client.post(
                "/inbox/delivery-failures/replay-bulk",
                headers=H,
                json={
                    "failure_ids": [failure_ids[0], failure_ids[0], failure_ids[1], 999999],
                    "operator": "manager_zoe",
                    "note": "Bulk retry operation",
                },
            )

            assert bulk_replay.status_code == 200
            payload = bulk_replay.json()
            assert payload["count"] == 3
            assert payload["replayed_count"] == 2
            assert payload["failed_count"] == 0
            assert payload["not_found_count"] == 1
            assert mocked_vendor_manager.make_request.await_count == 2

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(return_value={"id": "vendor-bulk-replay-3", "ok": True})
            bulk_replay_again = client.post(
                "/inbox/delivery-failures/replay-bulk",
                headers=H,
                json={
                    "failure_ids": failure_ids,
                    "operator": "manager_zoe",
                    "note": "Second bulk retry should skip",
                },
            )

        assert bulk_replay_again.status_code == 200
        again_payload = bulk_replay_again.json()
        assert again_payload["replayed_count"] == 0
        assert again_payload["failed_count"] == 0
        assert again_payload["skipped_count"] == 2
        statuses = {item["status"] for item in again_payload["items"]}
        assert statuses == {"already_delivered"}
        mocked_vendor_manager.make_request.assert_not_awaited()

    def test_replay_pending_delivery_failures_limit(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "2")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")

        message_ids: list[int] = []
        for seed_idx in (1, 2, 3):
            ingest = client.post(
                "/inbox/messages",
                headers=H,
                json={
                    "network": "reddit",
                    "source_type": "mention",
                    "author_handle": f"pending_replay_signal_{seed_idx}",
                    "author_follower_count": 135000 + seed_idx,
                    "text": "Critical issue requiring queue-based replay.",
                    "external_message_id": f"ext-delivery-pending-replay-{seed_idx}",
                },
            )
            assert ingest.status_code in (200, 201)
            message_id = ingest.json()["message"]["id"]
            message_ids.append(message_id)

            stage = client.post(
                f"/inbox/messages/{message_id}/auto-respond",
                headers=H,
                json={"suggestion_index": 0, "responder": "agent_pending_replay_case"},
            )
            assert stage.status_code == 200

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=RuntimeError("provider timeout"))
            for message_id in message_ids:
                approve = client.post(
                    f"/inbox/messages/{message_id}/approve-response",
                    headers=H,
                    json={"approver": "manager_zoe", "note": "Queue seed for replay-pending"},
                )
                assert approve.status_code == 502

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=[
                {"id": "vendor-pending-replay-1", "ok": True},
                {"id": "vendor-pending-replay-2", "ok": True},
            ])
            replay_pending = client.post(
                "/inbox/delivery-failures/replay-pending",
                headers=H,
                json={"operator": "manager_zoe", "note": "Run limited queue replay", "limit": 2, "network": "reddit"},
            )

        assert replay_pending.status_code == 200
        payload = replay_pending.json()
        assert payload["requested_limit"] == 2
        assert payload["selected_count"] == 2
        assert payload["replayed_count"] == 2
        assert payload["failed_count"] == 0
        assert len(payload["selected_failure_ids"]) == 2
        assert mocked_vendor_manager.make_request.await_count == 2

        pending_after_first = client.get("/inbox/delivery-failures?status=pending_retry", headers=H)
        assert pending_after_first.status_code == 200
        pending_ids = {
            item["message_id"]
            for item in pending_after_first.json()["items"]
            if item["message_id"] in message_ids
        }
        assert len(pending_ids) == 1

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(return_value={"id": "vendor-pending-replay-3", "ok": True})
            replay_pending_second = client.post(
                "/inbox/delivery-failures/replay-pending",
                headers=H,
                json={"operator": "manager_zoe", "note": "Drain remaining queue", "limit": 5, "network": "reddit"},
            )

        assert replay_pending_second.status_code == 200
        payload_second = replay_pending_second.json()
        assert payload_second["selected_count"] == 1
        assert payload_second["replayed_count"] == 1
        assert payload_second["failed_count"] == 0
        mocked_vendor_manager.make_request.assert_awaited_once()

        pending_after_second = client.get("/inbox/delivery-failures?status=pending_retry", headers=H)
        assert pending_after_second.status_code == 200
        pending_ids_after_second = {
            item["message_id"]
            for item in pending_after_second.json()["items"]
            if item["message_id"] in message_ids
        }
        assert not pending_ids_after_second

    def test_replay_pending_run_history(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "2")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")
        monkeypatch.setenv("INBOX_ALERT_NO_SELECTION_MIN_RUNS", "2")
        monkeypatch.setenv("INBOX_ALERT_NO_SELECTION_RATIO_HIGH", "0.5")
        monkeypatch.setenv("INBOX_ALERT_OPERATOR_LATENCY_SPIKE_MULTIPLIER", "1.5")
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": "smart-inbox-replay-runs-tenant"}

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=RuntimeError("provider unavailable"))

            create = client.post(
                "/inbox/messages",
                headers=headers,
                json={
                    "network": "twitter",
                    "source_type": "mention",
                    "author_handle": "replay_runs_signal",
                    "author_follower_count": 126500,
                    "text": "Escalation issue requires approved response.",
                    "external_message_id": "replay-runs-failure-seed-001",
                },
            )
            assert create.status_code in (200, 201)
            message_id = int(create.json()["message"]["id"])

            stage = client.post(
                f"/inbox/messages/{message_id}/auto-respond",
                headers=headers,
                json={"suggestion_index": 0, "responder": "agent_replay_runs_case"},
            )
            assert stage.status_code == 200

            approve = client.post(
                f"/inbox/messages/{message_id}/approve-response",
                headers=headers,
                json={"approver": "manager_zoe", "note": "Seed pending replay"},
            )
            assert approve.status_code == 502

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(return_value={"id": "vendor-replay-run-1", "ok": True})
            replay = client.post(
                "/inbox/delivery-failures/replay-pending",
                headers=headers,
                json={"operator": "manager_zoe", "note": "Replay this queue", "limit": 5, "network": "twitter"},
            )

        assert replay.status_code == 200
        replay_payload = replay.json()
        assert replay_payload["selected_count"] == 1
        assert replay_payload["replayed_count"] == 1
        assert replay_payload["network_filter"] == "twitter"
        assert replay_payload["run"]["selected_count"] == 1
        assert replay_payload["run"]["duration_ms"] >= 0

        replay_empty = client.post(
            "/inbox/delivery-failures/replay-pending",
            headers=headers,
            json={"operator": "manager_zoe", "note": "No pending expected", "limit": 5, "network": "twitter"},
        )
        assert replay_empty.status_code == 200
        assert replay_empty.json()["selected_count"] == 0
        assert replay_empty.json()["run"]["duration_ms"] >= 0

        runs = client.get("/inbox/delivery-failures/replay-runs?limit=10", headers=headers)
        assert runs.status_code == 200
        runs_payload = runs.json()
        assert runs_payload["count"] >= 2
        assert isinstance(runs_payload["items"], list)
        assert runs_payload["items"][0]["selected_count"] == 0
        assert runs_payload["items"][0]["network_filter"] == "twitter"
        assert runs_payload["items"][1]["selected_count"] == 1
        assert runs_payload["items"][1]["operator"] == "manager_zoe"

        filtered = client.get("/inbox/delivery-failures/replay-runs?network=reddit", headers=headers)
        assert filtered.status_code == 200
        assert filtered.json()["count"] == 0

        metrics = client.get("/inbox/delivery-failures/metrics?network=twitter", headers=headers)
        assert metrics.status_code == 200
        metrics_payload = metrics.json()
        replay_metrics = metrics_payload["replay_run_metrics"]
        assert replay_metrics["total_runs"] >= 2
        assert replay_metrics["runs_with_no_selection"] >= 1
        assert replay_metrics["selected_total"] >= 1
        assert replay_metrics["replayed_total"] >= 1
        assert replay_metrics["replayed_success_rate"] == 1.0
        assert replay_metrics["no_selection_ratio"] >= 0.0
        assert replay_metrics["by_operator"]["manager_zoe"] >= 2
        assert isinstance(replay_metrics["recent_runs"], list)
        assert isinstance(metrics_payload["alerts"], list)
        assert metrics_payload["alert_thresholds"]["no_selection_min_runs"] == 2
        assert metrics_payload["alert_thresholds"]["no_selection_ratio_high"] == 0.5
        assert any(item["code"] == "replay_runs_no_selection_spike" for item in metrics_payload["alerts"])

        performance = client.get(
            "/inbox/delivery-failures/replay-runs/performance?window_hours=24&network=twitter",
            headers=headers,
        )
        assert performance.status_code == 200
        performance_payload = performance.json()
        assert performance_payload["window_hours"] == 24
        assert performance_payload["network_filter"] == "twitter"
        assert performance_payload["total_runs"] >= 2
        assert performance_payload["total_selected"] >= 1
        assert performance_payload["total_replayed"] >= 1
        assert performance_payload["overall_success_rate"] == 1.0
        assert isinstance(performance_payload["anomaly_summary"], dict)
        assert performance_payload["anomaly_summary"]["total_alerts"] >= 0
        assert isinstance(performance_payload["anomaly_thresholds"], dict)
        assert isinstance(performance_payload["operators"], list)
        assert performance_payload["operators"][0]["operator"] == "manager_zoe"
        assert performance_payload["operators"][0]["runs"] >= 2
        assert performance_payload["operators"][0]["avg_duration_ms"] >= 0
        assert performance_payload["operators"][0]["p50_duration_ms"] >= 0
        assert performance_payload["operators"][0]["p95_duration_ms"] >= 0
        assert isinstance(performance_payload["operators"][0]["alerts"], list)

        perf_filtered = client.get(
            "/inbox/delivery-failures/replay-runs/performance?window_hours=24&operator=manager_zoe",
            headers=headers,
        )
        assert perf_filtered.status_code == 200
        perf_filtered_payload = perf_filtered.json()
        assert perf_filtered_payload["operator_filter"] == "manager_zoe"
        assert perf_filtered_payload["total_runs"] >= 2
        assert len(perf_filtered_payload["operators"]) == 1
        assert isinstance(perf_filtered_payload["operators"][0]["alerts"], list)

        ops_config = client.get("/inbox/ops-config", headers=headers)
        assert ops_config.status_code == 200
        ops_payload = ops_config.json()
        assert ops_payload["replay"]["delivery_max_retries"] == 2
        assert ops_payload["replay"]["delivery_backoff_seconds"] == 0.0
        assert ops_payload["metrics_alert_thresholds"]["no_selection_min_runs"] == 2
        assert ops_payload["metrics_alert_thresholds"]["no_selection_ratio_high"] == 0.5
        assert ops_payload["performance_alert_thresholds"]["operator_latency_spike_multiplier"] == 1.5

    def test_delivery_failure_metrics_summary(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "2")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": "smart-inbox-metrics-tenant"}

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.make_request = AsyncMock(side_effect=RuntimeError("provider unavailable"))

            create = client.post(
                "/inbox/messages",
                headers=headers,
                json={
                    "network": "twitter",
                    "source_type": "mention",
                    "author_handle": "metrics_delivery_signal",
                    "author_follower_count": 125000,
                    "text": "Urgent safety issue requires official response.",
                    "external_message_id": "metrics-delivery-failure-001",
                },
            )
            assert create.status_code in (200, 201)
            message_id = int(create.json()["message"]["id"])

            stage = client.post(
                f"/inbox/messages/{message_id}/auto-respond",
                headers=headers,
                json={"suggestion_index": 0, "responder": "agent_metrics_case"},
            )
            assert stage.status_code == 200
            assert stage.json()["message"]["status"] == "requires_approval"

            approve = client.post(
                f"/inbox/messages/{message_id}/approve-response",
                headers=headers,
                json={"approver": "qa_reviewer", "note": "Trigger DLQ path"},
            )
            assert approve.status_code == 502

        pending_before = client.get("/inbox/delivery-failures?status=pending_retry", headers=headers)
        assert pending_before.status_code == 200
        failure_id = int(pending_before.json()["items"][0]["id"])

        resolve = client.post(
            f"/inbox/delivery-failures/{failure_id}/resolve",
            headers=headers,
            json={"operator": "qa_reviewer", "note": "Handled manually"},
        )
        assert resolve.status_code == 200

        metrics = client.get("/inbox/delivery-failures/metrics", headers=headers)
        assert metrics.status_code == 200
        payload = metrics.json()

        assert payload["total_failures"] == 1
        assert payload["pending_count"] == 0
        assert payload["resolved_count"] == 1
        assert payload["pending_ratio"] == 0.0
        assert payload["by_status"]["resolved"] == 1
        assert payload["by_network"]["twitter"] == 1
        assert payload["by_resolution"]["manual_followup"] == 1
        assert payload["network_filter"] is None
        assert isinstance(payload["recent_operations"], list)
        assert isinstance(payload["alerts"], list)
        assert isinstance(payload["alert_thresholds"], dict)
        assert payload["replay_run_metrics"]["total_runs"] >= 0
        assert isinstance(payload["replay_run_metrics"]["by_operator"], dict)
        assert isinstance(payload["replay_run_metrics"]["recent_runs"], list)
        assert payload["replay_run_metrics"]["no_selection_ratio"] >= 0.0

    def test_ops_runbooks_and_go_live_gate(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INBOX_DELIVERY_MAX_RETRIES", "3")
        monkeypatch.setenv("INBOX_DELIVERY_BACKOFF_SECONDS", "0")
        monkeypatch.setenv("INBOX_DELIVERY_MAX_BACKOFF_SECONDS", "2")
        monkeypatch.setenv("SOCIAL_CONTRACT_MATRIX_LIVE_ENABLED", "true")
        headers = {"X-API-Key": "test-api-key", "X-Tenant-Id": "smart-inbox-go-live-tenant"}

        runbooks = client.get("/inbox/ops/runbooks", headers=headers)
        assert runbooks.status_code == 200
        runbook_payload = runbooks.json()
        assert runbook_payload["count"] >= 7
        assert any(item["code"] == "replay_success_rate_low" for item in runbook_payload["items"])

        single = client.get("/inbox/ops/runbooks?code=operator_latency_spike", headers=headers)
        assert single.status_code == 200
        assert single.json()["count"] == 1
        assert single.json()["items"][0]["code"] == "operator_latency_spike"

        with patch("backend.fastapi.app.routers.smart_inbox.vendor_manager") as mocked_vendor_manager:
            mocked_vendor_manager.get_credentials.return_value = object()
            go_live = client.get("/inbox/ops/go-live-gate", headers=headers)

        assert go_live.status_code == 200
        gate_payload = go_live.json()
        assert gate_payload["overall_ready"] is True
        assert gate_payload["failed_count"] == 0
        assert gate_payload["check_count"] >= 6
        check_codes = {item["code"] for item in gate_payload["checks"]}
        assert "runbook_coverage_complete" in check_codes
        assert "vendor_credentials_configured" in check_codes
        assert "live_contract_checks_enabled" in check_codes

    # ── Collision detection (locking) ────────────────────────────────────────

    def test_acquire_lock(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][1]["id"]

        r = client.post(
            f"/inbox/messages/{msg_id}/lock",
            headers=H,
            json={"locked_by": "agent_alice"},
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["lock"]["locked_by"] == "agent_alice"
        assert data["collision_detected"] is False

    def test_acquire_lock_renew_same_agent(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][1]["id"]

        r = client.post(
            f"/inbox/messages/{msg_id}/lock",
            headers=H,
            json={"locked_by": "agent_alice"},  # same agent — should renew
        )
        assert r.status_code in (200, 201)
        assert r.json()["collision_detected"] is False

    def test_acquire_lock_collision(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][1]["id"]

        r = client.post(
            f"/inbox/messages/{msg_id}/lock",
            headers=H,
            json={"locked_by": "agent_bob"},  # different agent — should 409
        )
        assert r.status_code == 409

    def test_acquire_lock_missing_message(self, client: TestClient) -> None:
        r = client.post("/inbox/messages/9999/lock", headers=H, json={"locked_by": "agent_x"})
        assert r.status_code == 404

    def test_release_lock(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][1]["id"]

        r = client.delete(
            f"/inbox/messages/{msg_id}/lock",
            headers=H,
            params={"locked_by": "agent_alice"},
        )
        assert r.status_code in (200, 201)
        assert r.json()["released"] is True

    def test_release_lock_not_held(self, client: TestClient) -> None:
        list_r = client.get("/inbox/messages", headers=H)
        msg_id = list_r.json()["messages"][1]["id"]

        r = client.delete(
            f"/inbox/messages/{msg_id}/lock",
            headers=H,
            params={"locked_by": "nobody"},  # lock already released
        )
        assert r.status_code == 404

    # ── Inbox stats ──────────────────────────────────────────────────────────

    def test_inbox_stats(self, client: TestClient) -> None:
        r = client.get("/inbox/stats", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 5
        assert "byStatus" in data
        assert "byMessageType" in data
        assert "bySentiment" in data
        assert "byNetwork" in data
        assert "avgPriorityScore" in data
        assert "replyRate" in data

    def test_inbox_stats_empty_tenant(self, client: TestClient) -> None:
        H2 = {"X-API-Key": "test-api-key", "X-Tenant-Id": "inbox-empty-tenant"}
        r = client.get("/inbox/stats", headers=H2)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["avgPriorityScore"] == 0.0
        assert data["replyRate"] == 0.0

    # ── Saved replies ────────────────────────────────────────────────────────

    def test_create_saved_reply(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/saved-replies",
            headers=H,
            json={
                "title": "Standard Shipping Response",
                "body": "Thank you for your question! Standard shipping takes 3-5 business days.",
                "tags": ["shipping", "logistics"],
                "networks": ["instagram", "facebook"],
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["reply"]["title"] == "Standard Shipping Response"
        assert "shipping" in data["reply"]["tags"]

    def test_create_saved_reply_minimal(self, client: TestClient) -> None:
        r = client.post(
            "/inbox/saved-replies",
            headers=H,
            json={
                "title": "Generic Thanks",
                "body": "Thank you for reaching out! We'll get back to you shortly.",
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["reply"]["networks"] == []  # empty = all networks

    def test_list_saved_replies(self, client: TestClient) -> None:
        r = client.get("/inbox/saved-replies", headers=H)
        assert r.status_code == 200
        assert r.json()["count"] >= 2

    def test_list_saved_replies_search(self, client: TestClient) -> None:
        r = client.get("/inbox/saved-replies?search=shipping", headers=H)
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_list_saved_replies_tag_filter(self, client: TestClient) -> None:
        r = client.get("/inbox/saved-replies?tag=shipping", headers=H)
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_list_saved_replies_network_filter(self, client: TestClient) -> None:
        r = client.get("/inbox/saved-replies?network=instagram", headers=H)
        assert r.status_code == 200

    def test_update_saved_reply(self, client: TestClient) -> None:
        list_r = client.get("/inbox/saved-replies", headers=H)
        reply_id = list_r.json()["replies"][0]["id"]

        r = client.patch(
            f"/inbox/saved-replies/{reply_id}",
            headers=H,
            json={
                "title": "Updated Shipping Response",
                "tags": ["shipping", "delivery", "updated"],
                "networks": ["instagram"],
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["reply"]["title"] == "Updated Shipping Response"

    def test_update_saved_reply_body(self, client: TestClient) -> None:
        list_r = client.get("/inbox/saved-replies", headers=H)
        reply_id = list_r.json()["replies"][0]["id"]

        r = client.patch(
            f"/inbox/saved-replies/{reply_id}",
            headers=H,
            json={"body": "Updated body copy for response template."},
        )
        assert r.status_code in (200, 201)
        assert r.json()["reply"]["body"] == "Updated body copy for response template."

    def test_update_saved_reply_missing(self, client: TestClient) -> None:
        r = client.patch("/inbox/saved-replies/9999", headers=H, json={"title": "Ghost"})
        assert r.status_code == 404

    def test_delete_saved_reply(self, client: TestClient) -> None:
        # Create one to delete
        r_create = client.post(
            "/inbox/saved-replies",
            headers=H,
            json={"title": "Delete Me", "body": "This will be deleted."},
        )
        reply_id = r_create.json()["reply"]["id"]

        r = client.delete(f"/inbox/saved-replies/{reply_id}", headers=H)
        assert r.status_code in (200, 201)
        assert r.json()["deleted"] is True

    def test_delete_saved_reply_missing(self, client: TestClient) -> None:
        r = client.delete("/inbox/saved-replies/9999", headers=H)
        assert r.status_code == 404
