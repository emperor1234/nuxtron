"""
Tests for auth.py _UserStore methods (memory path, no DB).
Covers: _find_mem, email_exists, create_user, fetch_password_hash,
        set_reset_token, consume_reset_token, and _UserAuthHandlers._issue_jwt.
"""
from __future__ import annotations

import os
import time
from unittest.mock import MagicMock

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)


def _make_store(mem: list | None = None):
    """Create a _UserStore with no-DB path (get_db_ready returns False)."""
    from backend.fastapi.app.routers.auth import _UserStore  # noqa: PLC0415
    users_memory: list = mem if mem is not None else []
    return _UserStore(
        get_db_ready=lambda: False,
        db_dsn=lambda: "",
        users_memory=users_memory,
    )


class TestUserStoreMemory:
    def test_find_mem_returns_none_when_empty(self) -> None:
        store = _make_store()
        assert store._find_mem("t1", "h1") is None

    def test_find_mem_returns_matching_user(self) -> None:
        user = {"tenant_id": "t1", "email_hash": "h1", "id": 1}
        store = _make_store([user])
        result = store._find_mem("t1", "h1")
        assert result is not None
        assert result["id"] == 1

    def test_find_mem_returns_none_for_wrong_tenant(self) -> None:
        user = {"tenant_id": "t1", "email_hash": "h1", "id": 1}
        store = _make_store([user])
        assert store._find_mem("other", "h1") is None

    def test_email_exists_false_when_not_found(self) -> None:
        store = _make_store()
        assert store.email_exists("t1", "h1") is False

    def test_email_exists_true_when_found(self) -> None:
        user = {"tenant_id": "t1", "email_hash": "h1", "id": 1}
        store = _make_store([user])
        assert store.email_exists("t1", "h1") is True

    def test_create_user_adds_to_memory(self) -> None:
        mem: list = []
        store = _make_store(mem)
        uid = store.create_user("t1", "h1", "cipher1", "pwhash1", "namecip1")
        assert uid == 1
        assert len(mem) == 1
        assert mem[0]["email_hash"] == "h1"

    def test_create_user_increments_id(self) -> None:
        mem: list = [{"id": 1, "tenant_id": "t1", "email_hash": "h1"}]
        store = _make_store(mem)
        uid = store.create_user("t1", "h2", "c2", "pw2", "n2")
        assert uid == 2

    def test_fetch_password_hash_returns_none_when_not_found(self) -> None:
        store = _make_store()
        result = store.fetch_password_hash("t1", "h1")
        assert result is None

    def test_fetch_password_hash_returns_id_and_hash(self) -> None:
        user = {"id": 7, "tenant_id": "t1", "email_hash": "h1", "password_hash": "myhash"}
        store = _make_store([user])
        result = store.fetch_password_hash("t1", "h1")
        assert result == (7, "myhash", ["user"])

    def test_fetch_password_hash_returns_persisted_roles(self) -> None:
        user = {"id": 7, "tenant_id": "t1", "email_hash": "h1", "password_hash": "myhash", "roles": "admin"}
        store = _make_store([user])
        result = store.fetch_password_hash("t1", "h1")
        assert result == (7, "myhash", ["admin"])

    def test_create_user_defaults_to_user_role(self) -> None:
        # Self-registration must never be able to produce anything but the
        # baseline role — admin is granted only out of band, via the Django
        # superadmin console, never through this store method's default path.
        mem: list = []
        store = _make_store(mem)
        uid = store.create_user("t1", "h1", "cipher1", "pwhash1", "namecip1")
        assert uid == 1
        assert mem[0]["roles"] == "user"
        result = store.fetch_password_hash("t1", "h1")
        assert result == (1, "pwhash1", ["user"])

    def test_set_reset_token_returns_false_when_user_not_found(self) -> None:
        store = _make_store()
        result = store.set_reset_token("t1", "h1", "tok123", int(time.time()) + 3600)
        assert result is False

    def test_set_reset_token_updates_user(self) -> None:
        user = {"id": 1, "tenant_id": "t1", "email_hash": "h1"}
        store = _make_store([user])
        result = store.set_reset_token("t1", "h1", "tok123", int(time.time()) + 3600)
        assert result is True
        assert user["reset_token"] == "tok123"

    def test_consume_reset_token_returns_false_for_wrong_user(self) -> None:
        store = _make_store()
        result = store.consume_reset_token("t1", "h1", "tok", "newhash", int(time.time()))
        assert result is False

    def test_consume_reset_token_returns_false_for_wrong_token(self) -> None:
        user = {"id": 1, "tenant_id": "t1", "email_hash": "h1", "reset_token": "correct", "reset_token_expires": None}
        store = _make_store([user])
        result = store.consume_reset_token("t1", "h1", "wrong", "newhash", int(time.time()))
        assert result is False

    def test_consume_reset_token_returns_false_when_expired(self) -> None:
        past = int(time.time()) - 100
        user = {
            "id": 1, "tenant_id": "t1", "email_hash": "h1",
            "reset_token": "tok", "reset_token_expires": past,
        }
        store = _make_store([user])
        result = store.consume_reset_token("t1", "h1", "tok", "newhash", int(time.time()))
        assert result is False

    def test_consume_reset_token_success(self) -> None:
        future = int(time.time()) + 3600
        user = {
            "id": 1, "tenant_id": "t1", "email_hash": "h1",
            "reset_token": "tok", "reset_token_expires": future,
        }
        store = _make_store([user])
        result = store.consume_reset_token("t1", "h1", "tok", "newhash", int(time.time()))
        assert result is True
        assert user["password_hash"] == "newhash"
        assert user["reset_token"] is None

    def test_consume_reset_token_with_no_expiry(self) -> None:
        user = {
            "id": 1, "tenant_id": "t1", "email_hash": "h1",
            "reset_token": "tok", "reset_token_expires": None,
        }
        store = _make_store([user])
        result = store.consume_reset_token("t1", "h1", "tok", "newhash", int(time.time()))
        assert result is True


class TestUserAuthHandlersIssueJwt:
    def _make_handlers(self):
        import hashlib
        import hmac  # noqa: E401, PLC0415

        from backend.fastapi.app.routers.auth import _UserAuthHandlers  # noqa: PLC0415

        def sign(payload, secret):
            import base64
            import json  # noqa: E401, PLC0415
            header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
            body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
            sig = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).hexdigest()
            return f"{header}.{body}.{sig}"

        handlers = _UserAuthHandlers.__new__(_UserAuthHandlers)
        handlers._sign = sign
        handlers._hash_pw = lambda pw: "hash:" + pw
        handlers._verify_pw = lambda pw, h: h == "hash:" + pw
        handlers._encrypt = lambda v: v + "_encrypted"
        handlers._hash_email = lambda e: "h:" + e
        handlers._security_mem = []
        handlers._rl = MagicMock()
        handlers._store = _make_store()
        return handlers

    def test_issue_jwt_returns_token_and_expiry(self) -> None:
        h = self._make_handlers()
        token, exp = h._issue_jwt("tenant1", 42, "user@example.com")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3
        assert exp > int(time.time())

    def test_issue_jwt_expiry_is_3600_seconds_from_now(self) -> None:
        h = self._make_handlers()
        before = int(time.time())
        _, exp = h._issue_jwt("t1", 1, "a@b.com")
        assert exp >= before + 3599
        assert exp <= before + 3601

    def test_log_does_not_raise(self) -> None:
        h = self._make_handlers()
        h._log("tenant1", "login", "user@test.com")  # Should not raise
