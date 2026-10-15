"""Tests for the shared Redis security-counter readiness adapter."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from backend.fastapi.app.domains.identity import security_redis


def test_security_redis_ready_pings_shared_client(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(security_redis, "get_sync_redis", lambda: client)

    assert security_redis.security_redis_ready() is True
    client.ping.assert_called_once_with()


def test_security_redis_ready_fails_closed_when_ping_fails(monkeypatch) -> None:
    client = MagicMock()
    client.ping.side_effect = OSError("connection refused")
    monkeypatch.setattr(security_redis, "get_sync_redis", lambda: client)
    monkeypatch.setattr(security_redis, "_client", client)
    monkeypatch.setattr(security_redis, "_client_init_failed", False)
    monkeypatch.setattr(security_redis, "_retry_after_monotonic", 0.0)

    assert security_redis.security_redis_ready() is False
    assert security_redis._client is None
    assert security_redis._client_init_failed is True


def test_sync_redis_retries_after_bounded_cooldown(monkeypatch) -> None:
    now = [100.0]
    attempts = [0]
    client = MagicMock()

    class FakeRedis:
        @staticmethod
        def from_url(*_args: Any, **_kwargs: Any) -> MagicMock:
            attempts[0] += 1
            if attempts[0] == 1:
                raise OSError("temporary outage")
            return client

    class FakeRedisModule:
        Redis = FakeRedis

    monkeypatch.setattr(security_redis, "redis_sync", FakeRedisModule)
    monkeypatch.setattr(security_redis.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(security_redis, "_client", None)
    monkeypatch.setattr(security_redis, "_client_init_failed", False)
    monkeypatch.setattr(security_redis, "_retry_after_monotonic", 0.0)

    assert security_redis.get_sync_redis() is None
    assert security_redis.get_sync_redis() is None
    assert attempts[0] == 1

    now[0] += security_redis._RETRY_INTERVAL_SECONDS + 0.1
    assert security_redis.get_sync_redis() is client
    assert attempts[0] == 2
