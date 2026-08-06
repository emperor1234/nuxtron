"""
Additional tests for bridges.py pure handler functions.
These take all dependencies as kwargs, so they can be tested without the DB/router.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock


def _make_auth(tenant_id: str = "t-1") -> object:
    """Create a simple auth context stub."""
    auth = MagicMock()
    auth.tenant_id = tenant_id
    return auth


def _redis_key(tenant_id: str, key: str) -> str:
    return f"{tenant_id}:{key}"


def _no_redis():
    return None


class TestHandleCacheSet:
    def test_set_memory_fallback(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheSetRequest,
            _handle_cache_set,
        )
        memory: list[dict] = []
        payload = RedisCacheSetRequest(key="my-key", value="hello", ttl_seconds=60)
        result = _handle_cache_set(
            payload=payload,
            auth=_make_auth(),
            redis_ops_memory=memory,
            append_bounded=lambda lst, item: lst.append(item),
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        assert result["status"] == "ok"
        assert result["source"] == "memory-fallback"
        assert len(memory) == 1

    def test_set_redis_success(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheSetRequest,
            _handle_cache_set,
        )
        mock_redis = MagicMock()
        mock_redis.setex.return_value = True
        result = _handle_cache_set(
            payload=RedisCacheSetRequest(key="k", value="v", ttl_seconds=30),
            auth=_make_auth(),
            redis_ops_memory=[],
            append_bounded=lambda l, i: l.append(i),
            redis_key=_redis_key,
            redis_client=lambda: mock_redis,
        )
        assert result["source"] == "redis"
        assert result["status"] == "ok"

    def test_set_redis_failure_falls_back(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheSetRequest,
            _handle_cache_set,
        )
        mock_redis = MagicMock()
        mock_redis.setex.side_effect = Exception("Connection refused")
        memory: list[dict] = []
        result = _handle_cache_set(
            payload=RedisCacheSetRequest(key="k", value="v", ttl_seconds=30),
            auth=_make_auth(),
            redis_ops_memory=memory,
            append_bounded=lambda l, i: l.append(i),
            redis_key=_redis_key,
            redis_client=lambda: mock_redis,
        )
        assert result["source"] == "memory-fallback"

    def test_set_deduplicates_same_key(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheSetRequest,
            _handle_cache_set,
        )
        memory: list[dict] = [{"key": "t-1:key1", "op": "set"}]
        _handle_cache_set(
            payload=RedisCacheSetRequest(key="key1", value="new-value", ttl_seconds=60),
            auth=_make_auth("t-1"),
            redis_ops_memory=memory,
            append_bounded=lambda l, i: l.append(i),
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        # Old entry removed, new one added
        assert len(memory) == 1
        assert memory[0]["value"] == "new-value"


class TestHandleCacheGet:
    def test_get_memory_hit(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheGetRequest,
            _handle_cache_get,
        )
        expires = (datetime.now(UTC) + timedelta(seconds=60)).isoformat()
        memory = [{"key": "t-1:mykey", "op": "set", "value": "cached-value", "expires_at": expires}]
        result = _handle_cache_get(
            payload=RedisCacheGetRequest(key="mykey"),
            auth=_make_auth("t-1"),
            redis_ops_memory=memory,
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        assert result["found"] is True
        assert result["value"] == "cached-value"
        assert result["source"] == "memory-fallback"

    def test_get_memory_miss(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheGetRequest,
            _handle_cache_get,
        )
        result = _handle_cache_get(
            payload=RedisCacheGetRequest(key="nonexistent"),
            auth=_make_auth(),
            redis_ops_memory=[],
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        assert result["found"] is False
        assert result["value"] is None

    def test_get_expired_entry_not_returned(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheGetRequest,
            _handle_cache_get,
        )
        expires = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
        memory = [{"key": "t-1:oldkey", "op": "set", "value": "stale", "expires_at": expires}]
        result = _handle_cache_get(
            payload=RedisCacheGetRequest(key="oldkey"),
            auth=_make_auth("t-1"),
            redis_ops_memory=memory,
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        assert result["found"] is False

    def test_get_from_redis(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheGetRequest,
            _handle_cache_get,
        )
        mock_redis = MagicMock()
        mock_redis.get.return_value = "redis-value"
        mock_redis.ttl.return_value = 120
        result = _handle_cache_get(
            payload=RedisCacheGetRequest(key="mykey"),
            auth=_make_auth(),
            redis_ops_memory=[],
            redis_key=_redis_key,
            redis_client=lambda: mock_redis,
        )
        assert result["source"] == "redis"
        assert result["value"] == "redis-value"
        assert result["found"] is True


class TestHandleCacheDelete:
    def test_delete_memory(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheDeleteRequest,
            _handle_cache_delete,
        )
        memory: list[dict] = [{"key": "t-1:del-key"}]
        result = _handle_cache_delete(
            payload=RedisCacheDeleteRequest(key="del-key"),
            auth=_make_auth("t-1"),
            redis_ops_memory=memory,
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        assert result["deleted"] is True
        assert len(memory) == 0

    def test_delete_memory_miss(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheDeleteRequest,
            _handle_cache_delete,
        )
        memory: list[dict] = []
        result = _handle_cache_delete(
            payload=RedisCacheDeleteRequest(key="nonexistent"),
            auth=_make_auth(),
            redis_ops_memory=memory,
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        assert result["deleted"] is False

    def test_delete_via_redis(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheDeleteRequest,
            _handle_cache_delete,
        )
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1
        result = _handle_cache_delete(
            payload=RedisCacheDeleteRequest(key="k"),
            auth=_make_auth(),
            redis_ops_memory=[],
            redis_key=_redis_key,
            redis_client=lambda: mock_redis,
        )
        assert result["source"] == "redis"
        assert result["deleted"] is True


class TestHandleCacheFlushPrefix:
    def test_flush_memory(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheFlushPrefixRequest,
            _handle_cache_flush_prefix,
        )
        memory: list[dict] = [
            {"key": "t-1:prefix:a"},
            {"key": "t-1:prefix:b"},
            {"key": "t-1:other:c"},
        ]
        result = _handle_cache_flush_prefix(
            payload=RedisCacheFlushPrefixRequest(prefix="prefix:"),
            auth=_make_auth("t-1"),
            redis_ops_memory=memory,
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        assert result["keys_deleted"] == 2
        assert len(memory) == 1
        assert result["source"] == "memory-fallback"

    def test_flush_via_redis(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheFlushPrefixRequest,
            _handle_cache_flush_prefix,
        )
        mock_redis = MagicMock()
        mock_redis.scan_iter.return_value = ["t-1:prefix:a", "t-1:prefix:b"]
        result = _handle_cache_flush_prefix(
            payload=RedisCacheFlushPrefixRequest(prefix="prefix:"),
            auth=_make_auth("t-1"),
            redis_ops_memory=[],
            redis_key=_redis_key,
            redis_client=lambda: mock_redis,
        )
        assert result["source"] == "redis"
        assert result["keys_deleted"] == 2

    def test_flush_nothing_matches(self) -> None:
        from backend.fastapi.app.routers.bridges import (
            RedisCacheFlushPrefixRequest,
            _handle_cache_flush_prefix,
        )
        memory: list[dict] = [{"key": "t-1:other:x"}]
        result = _handle_cache_flush_prefix(
            payload=RedisCacheFlushPrefixRequest(prefix="nomatch:"),
            auth=_make_auth("t-1"),
            redis_ops_memory=memory,
            redis_key=_redis_key,
            redis_client=_no_redis,
        )
        assert result["keys_deleted"] == 0
        assert len(memory) == 1


class TestHandleSlackSendMessage:
    def test_no_bot_token_queues_to_memory(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.bridges import (
            SlackSendMessageRequest,
            _handle_slack_send_message,
        )
        memory: list[dict] = []
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": ""}, clear=False):
            result = _handle_slack_send_message(
                payload=SlackSendMessageRequest(channel="#general", text="Hello!"),
                auth=_make_auth(),
                slack_messages_memory=memory,
                append_bounded=lambda l, i: l.append(i),
            )
        assert result["status"] == "ok"
        assert result["result"]["status"] == "queued"
        assert len(memory) == 1

    def test_exception_queues_to_memory(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.bridges import (
            SlackSendMessageRequest,
            _handle_slack_send_message,
        )
        memory: list[dict] = []
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-fake"}, clear=False):
            with patch("httpx.Client") as mock_client_cls:
                mock_client_cls.return_value.__enter__.return_value.post.side_effect = Exception("network")
                result = _handle_slack_send_message(
                    payload=SlackSendMessageRequest(channel="#general", text="Hello!"),
                    auth=_make_auth(),
                    slack_messages_memory=memory,
                    append_bounded=lambda l, i: l.append(i),
                )
        assert result["status"] == "ok"
        assert result["result"]["status"] == "queued-after-error"


class TestHandleSlackWebhookMessage:
    def test_no_webhook_url_queues(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.bridges import (
            SlackWebhookMessageRequest,
            _handle_slack_webhook_message,
        )
        memory: list[dict] = []
        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": ""}, clear=False):
            result = _handle_slack_webhook_message(
                payload=SlackWebhookMessageRequest(text="Webhook test"),
                auth=_make_auth(),
                slack_messages_memory=memory,
                append_bounded=lambda l, i: l.append(i),
            )
        assert result["status"] == "ok"
        assert result["result"]["status"] == "queued"

    def test_exception_queues_webhook(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.bridges import (
            SlackWebhookMessageRequest,
            _handle_slack_webhook_message,
        )
        memory: list[dict] = []
        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/fake"}, clear=False):
            with patch("httpx.Client") as mock_client_cls:
                mock_client_cls.return_value.__enter__.return_value.post.side_effect = Exception("net")
                result = _handle_slack_webhook_message(
                    payload=SlackWebhookMessageRequest(text="Test message"),
                    auth=_make_auth(),
                    slack_messages_memory=memory,
                    append_bounded=lambda l, i: l.append(i),
                )
        assert result["result"]["status"] == "queued-after-error"


class TestHandleTwilioSendSms:
    def test_no_twilio_config_queues(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.bridges import (
            TwilioSendSmsRequest,
            _handle_twilio_send_sms,
        )
        memory: list[dict] = []
        with patch.dict(os.environ, {"TWILIO_ACCOUNT_SID": "", "TWILIO_AUTH_TOKEN": ""}, clear=False):
            result = _handle_twilio_send_sms(
                payload=TwilioSendSmsRequest(to="+15555555555", body="Hello!"),
                auth=_make_auth(),
                twilio_messages_memory=memory,
                append_bounded=lambda l, i: l.append(i),
            )
        assert result["status"] == "ok"
        assert result["result"]["status"] == "queued"

    def test_exception_queues_sms(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.bridges import (
            TwilioSendSmsRequest,
            _handle_twilio_send_sms,
        )
        memory: list[dict] = []
        with patch.dict(os.environ, {"TWILIO_ACCOUNT_SID": "ACtest", "TWILIO_AUTH_TOKEN": "token", "TWILIO_FROM_NUMBER": "+15551234567"}, clear=False):
            with patch("httpx.Client") as mock_client_cls:
                mock_client_cls.return_value.__enter__.return_value.post.side_effect = Exception("network")
                result = _handle_twilio_send_sms(
                    payload=TwilioSendSmsRequest(to="+15555555555", body="Test"),
                    auth=_make_auth(),
                    twilio_messages_memory=memory,
                    append_bounded=lambda l, i: l.append(i),
                )
        assert result["result"]["status"] == "queued-after-error"


class TestHandleTwilioMakeCall:
    def test_no_twilio_config_queues_call(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.bridges import (
            TwilioMakeCallRequest,
            _handle_twilio_make_call,
        )
        memory: list[dict] = []
        with patch.dict(os.environ, {"TWILIO_ACCOUNT_SID": "", "TWILIO_AUTH_TOKEN": ""}, clear=False):
            result = _handle_twilio_make_call(
                payload=TwilioMakeCallRequest(to="+15555555555", twiml_url="https://example.com/twiml"),
                auth=_make_auth(),
                twilio_messages_memory=memory,
                append_bounded=lambda l, i: l.append(i),
            )
        assert result["status"] == "ok"
        assert result["result"]["status"] == "queued"
        assert result["result"]["type"] == "call"

    def test_exception_queues_call(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.bridges import (
            TwilioMakeCallRequest,
            _handle_twilio_make_call,
        )
        memory: list[dict] = []
        with patch.dict(os.environ, {"TWILIO_ACCOUNT_SID": "ACtest", "TWILIO_AUTH_TOKEN": "token", "TWILIO_FROM_NUMBER": "+15551234567"}, clear=False):
            with patch("httpx.Client") as mock_client_cls:
                mock_client_cls.return_value.__enter__.return_value.post.side_effect = Exception("net")
                result = _handle_twilio_make_call(
                    payload=TwilioMakeCallRequest(to="+15555555555", twiml_url="https://example.com/twiml"),
                    auth=_make_auth(),
                    twilio_messages_memory=memory,
                    append_bounded=lambda l, i: l.append(i),
                )
        assert result["result"]["status"] == "queued-after-error"
