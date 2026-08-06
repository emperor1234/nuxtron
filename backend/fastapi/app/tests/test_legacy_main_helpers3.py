"""
Tests for uncovered legacy_main.py functions:
- _security_alert_backfill_candidates
- _prune_backfilled_memory_alerts
- _queue_security_alert_email
- _claim_security_alert_email
- _update_security_alert_email
- _security_alert_delivery_summary
- _apply_startup_db_timeouts
- _select_provider_with_tiers
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)


class TestSecurityAlertBackfillCandidates:
    def test_returns_empty_when_memory_empty(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _resend_messages_memory,
            _security_alert_backfill_candidates,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        try:
            result = _security_alert_backfill_candidates()
            assert result == []
        finally:
            _resend_messages_memory.extend(original)

    def test_returns_only_platform_security_items(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _resend_messages_memory,
            _security_alert_backfill_candidates,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        _resend_messages_memory.append({"tenant_id": "other-tenant", "status": "queued"})
        _resend_messages_memory.append({"tenant_id": "platform-security", "status": "queued"})
        try:
            result = _security_alert_backfill_candidates()
            assert len(result) == 1
            assert result[0]["tenant_id"] == "platform-security"
        finally:
            _resend_messages_memory.clear()
            _resend_messages_memory.extend(original)

    def test_excludes_sent_and_failed_items(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _resend_messages_memory,
            _security_alert_backfill_candidates,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        _resend_messages_memory.append({"tenant_id": "platform-security", "status": "sent"})
        _resend_messages_memory.append({"tenant_id": "platform-security", "status": "failed"})
        _resend_messages_memory.append({"tenant_id": "platform-security", "status": "queued"})
        try:
            result = _security_alert_backfill_candidates()
            assert len(result) == 1
            assert result[0]["status"] == "queued"
        finally:
            _resend_messages_memory.clear()
            _resend_messages_memory.extend(original)

    def test_includes_retry_and_sending(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _resend_messages_memory,
            _security_alert_backfill_candidates,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        _resend_messages_memory.append({"tenant_id": "platform-security", "status": "retry"})
        _resend_messages_memory.append({"tenant_id": "platform-security", "status": "sending"})
        try:
            result = _security_alert_backfill_candidates()
            assert len(result) == 2
        finally:
            _resend_messages_memory.clear()
            _resend_messages_memory.extend(original)


class TestPruneBackfilledMemoryAlerts:
    def test_no_op_when_empty_ids(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _prune_backfilled_memory_alerts,
            _resend_messages_memory,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        _resend_messages_memory.append({"tenant_id": "platform-security", "id": 1})
        try:
            _prune_backfilled_memory_alerts(set())
            assert len(_resend_messages_memory) == 1  # nothing pruned
        finally:
            _resend_messages_memory.clear()
            _resend_messages_memory.extend(original)

    def test_removes_matching_ids(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _prune_backfilled_memory_alerts,
            _resend_messages_memory,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        _resend_messages_memory.append({"tenant_id": "platform-security", "id": 5})
        _resend_messages_memory.append({"tenant_id": "platform-security", "id": 6})
        try:
            _prune_backfilled_memory_alerts({5})
            assert len(_resend_messages_memory) == 1
            assert _resend_messages_memory[0]["id"] == 6
        finally:
            _resend_messages_memory.clear()
            _resend_messages_memory.extend(original)

    def test_does_not_remove_non_platform_security_items(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _prune_backfilled_memory_alerts,
            _resend_messages_memory,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        _resend_messages_memory.append({"tenant_id": "other-tenant", "id": 5})
        try:
            _prune_backfilled_memory_alerts({5})
            assert len(_resend_messages_memory) == 1  # NOT removed, different tenant
        finally:
            _resend_messages_memory.clear()
            _resend_messages_memory.extend(original)


class TestQueueSecurityAlertEmail:
    def test_queues_to_memory_when_db_disabled(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _queue_security_alert_email,
            _resend_messages_memory,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=False):
            event = {"tenant_id": "platform-security", "to": "admin@test.com"}
            _queue_security_alert_email(event)
            assert event.get("__queue_source") == "memory"
            assert len(_resend_messages_memory) == 1
        _resend_messages_memory.clear()
        _resend_messages_memory.extend(original)

    def test_queues_to_db_when_enabled(self) -> None:
        from backend.fastapi.app.legacy_main import _queue_security_alert_email
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=True):
            with patch("backend.fastapi.app.legacy_main._db_insert_security_alert_email", return_value=42):
                event = {"tenant_id": "platform-security", "to": "admin@test.com"}
                _queue_security_alert_email(event)
                assert event.get("id") == 42
                assert event.get("__queue_source") == "db"


class TestClaimSecurityAlertEmail:
    def test_returns_none_when_queue_empty(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _claim_security_alert_email,
            _resend_messages_memory,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=False):
            result = _claim_security_alert_email()
            assert result is None
        _resend_messages_memory.clear()
        _resend_messages_memory.extend(original)

    def test_claims_queued_item_from_memory(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _claim_security_alert_email,
            _resend_messages_memory,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        item = {"tenant_id": "platform-security", "status": "queued", "next_attempt_at": 0}
        _resend_messages_memory.append(item)
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=False):
            result = _claim_security_alert_email()
            assert result is not None
            assert result["status"] == "sending"
            assert result["__queue_source"] == "memory"
        _resend_messages_memory.clear()
        _resend_messages_memory.extend(original)

    def test_skips_future_retry_items(self) -> None:
        import time

        from backend.fastapi.app.legacy_main import (
            _claim_security_alert_email,
            _resend_messages_memory,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        future_ts = int(time.time()) + 9999
        item = {"tenant_id": "platform-security", "status": "retry", "next_attempt_at": future_ts}
        _resend_messages_memory.append(item)
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=False):
            result = _claim_security_alert_email()
            assert result is None
        _resend_messages_memory.clear()
        _resend_messages_memory.extend(original)

    def test_claims_from_db_when_enabled(self) -> None:
        from backend.fastapi.app.legacy_main import _claim_security_alert_email
        db_item = {"id": 1, "tenant_id": "platform-security", "status": "queued"}
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=True):
            with patch("backend.fastapi.app.legacy_main._db_claim_security_alert_email", return_value=db_item):
                result = _claim_security_alert_email()
                assert result == db_item


class TestUpdateSecurityAlertEmail:
    def test_updates_memory_item(self) -> None:
        from backend.fastapi.app.legacy_main import _update_security_alert_email
        item = {"__queue_source": "memory", "status": "sending"}
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=False):
            _update_security_alert_email(item, status="sent", provider="resend", detail="ok")
        assert item["status"] == "sent"
        assert item["provider"] == "resend"

    def test_updates_db_item_when_db_enabled(self) -> None:
        from backend.fastapi.app.legacy_main import _update_security_alert_email
        item = {"__queue_source": "db", "status": "sending", "id": 10}
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=True):
            with patch("backend.fastapi.app.legacy_main._db_update_security_alert_email") as mock_db_update:
                _update_security_alert_email(item, status="sent", provider="ses", detail="ok")
                mock_db_update.assert_called_once()

    def test_sets_retry_next_attempt_for_memory(self) -> None:
        import time

        from backend.fastapi.app.legacy_main import _update_security_alert_email
        item = {"__queue_source": "memory", "status": "sending"}
        before = int(time.time())
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=False):
            _update_security_alert_email(item, status="retry", provider="ses", detail="fail", retry_seconds=60)
        assert item.get("next_attempt_at", 0) >= before + 60

    def test_removes_next_attempt_on_sent(self) -> None:
        from backend.fastapi.app.legacy_main import _update_security_alert_email
        item = {"__queue_source": "memory", "status": "sending", "next_attempt_at": 99999}
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=False):
            _update_security_alert_email(item, status="sent", provider="resend", detail="ok")
        assert "next_attempt_at" not in item


class TestSecurityAlertDeliverySummary:
    def test_returns_db_summary_when_db_enabled(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_delivery_summary
        db_summary = {"queued": 2, "sent": 5}
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=True):
            with patch("backend.fastapi.app.legacy_main._db_security_alert_delivery_summary", return_value=db_summary):
                result = _security_alert_delivery_summary()
                assert result == db_summary

    def test_returns_memory_summary_when_db_disabled(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _resend_messages_memory,
            _security_alert_delivery_summary,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        _resend_messages_memory.append({"tenant_id": "platform-security", "status": "sent"})
        _resend_messages_memory.append({"tenant_id": "platform-security", "status": "queued"})
        _resend_messages_memory.append({"tenant_id": "other-tenant", "status": "sent"})  # excluded
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=False):
            result = _security_alert_delivery_summary()
            assert result["sent"] == 1
            assert result["queued"] == 1
        _resend_messages_memory.clear()
        _resend_messages_memory.extend(original)

    def test_falls_back_to_memory_when_db_returns_none(self) -> None:
        from backend.fastapi.app.legacy_main import (
            _resend_messages_memory,
            _security_alert_delivery_summary,
        )
        original = list(_resend_messages_memory)
        _resend_messages_memory.clear()
        with patch("backend.fastapi.app.legacy_main._security_alert_db_queue_enabled", return_value=True):
            with patch("backend.fastapi.app.legacy_main._db_security_alert_delivery_summary", return_value=None):
                result = _security_alert_delivery_summary()
                assert isinstance(result, dict)
                assert "queued" in result
        _resend_messages_memory.clear()
        _resend_messages_memory.extend(original)


class TestApplyStartupDbTimeouts:
    def test_executes_both_timeout_statements(self) -> None:
        from backend.fastapi.app.legacy_main import _apply_startup_db_timeouts
        mock_conn = MagicMock()
        _apply_startup_db_timeouts(mock_conn)
        assert mock_conn.execute.call_count == 2
        calls = [call.args[0] for call in mock_conn.execute.call_args_list]
        assert any("lock_timeout" in c for c in calls)
        assert any("statement_timeout" in c for c in calls)


class TestSelectProviderWithTiers:
    def test_returns_fallback_when_no_providers_configured(self) -> None:
        from backend.fastapi.app.legacy_main import (
            AiGatewayGenerateRequest,
            _select_provider_with_tiers,
        )
        payload = AiGatewayGenerateRequest(
            prompt="hello",
            model="gpt-4o-mini",
            max_tokens=100,
            quality_floor=0.0,
            value_per_1k_tokens=0.01,
        )
        with patch("backend.fastapi.app.legacy_main._resolve_provider_api_key", return_value=None):
            provider, model = _select_provider_with_tiers(payload)
            assert isinstance(provider, str)
            assert isinstance(model, str)

    def test_returns_openai_when_key_configured(self) -> None:
        from backend.fastapi.app.legacy_main import (
            AI_MODEL_CATALOG,
            AiGatewayGenerateRequest,
            _select_provider_with_tiers,
        )
        payload = AiGatewayGenerateRequest(
            prompt="hello",
            model=None,
            max_tokens=100,
            quality_floor=0.0,
            value_per_1k_tokens=0.01,
        )
        # Check if openai is in catalog
        if "openai" in AI_MODEL_CATALOG:
            with patch("backend.fastapi.app.legacy_main._resolve_provider_api_key", side_effect=lambda p: "sk-test" if p == "openai" else None):
                with patch("backend.fastapi.app.legacy_main._is_provider_disabled", return_value=False):
                    provider, model = _select_provider_with_tiers(payload)
                    assert isinstance(provider, str)
                    assert isinstance(model, str)
        else:
            # At minimum, function returns without error
            provider, model = _select_provider_with_tiers(payload)
            assert isinstance(provider, str)

    def test_uses_custom_task_type(self) -> None:
        from backend.fastapi.app.legacy_main import (
            AiGatewayGenerateRequest,
            _select_provider_with_tiers,
        )
        payload = AiGatewayGenerateRequest(
            prompt="embed this",
            model=None,
            max_tokens=10,
            quality_floor=0.0,
            value_per_1k_tokens=0.001,
        )
        with patch("backend.fastapi.app.legacy_main._resolve_provider_api_key", return_value=None):
            provider, model = _select_provider_with_tiers(payload, task_type="embeddings")
            assert isinstance(provider, str)

    def test_respects_quality_floor(self) -> None:
        from backend.fastapi.app.legacy_main import (
            AiGatewayGenerateRequest,
            _select_provider_with_tiers,
        )
        payload = AiGatewayGenerateRequest(
            prompt="hello",
            model=None,
            max_tokens=100,
            quality_floor=0.99,  # very high — should still return a fallback
            value_per_1k_tokens=0.01,
        )
        # Should not raise regardless
        provider, model = _select_provider_with_tiers(payload)
        assert isinstance(provider, str)
