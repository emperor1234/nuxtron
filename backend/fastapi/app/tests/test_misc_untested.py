"""Tests for untested helper functions across various modules."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest

# ─── transparent_encryption: _derive_chacha_key, _pqc_available ──────────────

class TestDeriveChachaKey:
    def test_returns_bytes(self):
        from backend.fastapi.app.transparent_encryption import _derive_chacha_key
        result = _derive_chacha_key()
        assert isinstance(result, bytes)

    def test_returns_32_bytes(self):
        from backend.fastapi.app.transparent_encryption import _derive_chacha_key
        result = _derive_chacha_key()
        assert len(result) == 32

    def test_deterministic(self):
        from backend.fastapi.app.transparent_encryption import _derive_chacha_key
        r1 = _derive_chacha_key()
        r2 = _derive_chacha_key()
        assert r1 == r2


class TestPqcAvailable:
    def test_returns_bool(self):
        from backend.fastapi.app.transparent_encryption import _pqc_available
        result = _pqc_available()
        assert isinstance(result, bool)

    def test_returns_false_if_provider_unavailable(self):
        from backend.fastapi.app.transparent_encryption import _pqc_provider
        # This is deterministic; if the provider says unavailable, _pqc_available is False
        provider = _pqc_provider()
        from backend.fastapi.app.transparent_encryption import _pqc_available
        expected = provider != "unavailable"
        assert _pqc_available() == expected


# ─── deps.py: _audit_api_usage ───────────────────────────────────────────────

class TestAuditApiUsage:
    def _make_request(self, store=None):
        """Create a mock request with app state."""
        request = MagicMock()
        request.app.state.api_usage_audit = store if store is not None else []
        request.headers.get = MagicMock(side_effect=lambda k, d='': {
            'X-Forwarded-For': '',
            'User-Agent': 'test-agent',
        }.get(k, d))
        request.client = MagicMock()
        request.client.host = '127.0.0.1'
        request.method = 'GET'
        request.url.path = '/test'
        return request

    @pytest.mark.asyncio
    async def test_appends_to_store(self):
        from backend.fastapi.app.deps import _audit_api_usage
        store = []
        req = self._make_request(store)
        await _audit_api_usage(req, tenant_id="t1", auth_mode="api_key", api_key_value="key123")
        assert len(store) == 1

    @pytest.mark.asyncio
    async def test_record_has_expected_keys(self):
        from backend.fastapi.app.deps import _audit_api_usage
        store = []
        req = self._make_request(store)
        await _audit_api_usage(req, tenant_id="t1", auth_mode="api_key", api_key_value="key123")
        record = store[0]
        assert record["tenant_id"] == "t1"
        assert record["auth_mode"] == "api_key"
        assert record["method"] == "GET"
        assert record["path"] == "/test"

    @pytest.mark.asyncio
    async def test_noop_when_store_not_list(self):
        from backend.fastapi.app.deps import _audit_api_usage
        req = self._make_request(store=None)
        req.app.state.api_usage_audit = "not-a-list"
        # Should not raise
        await _audit_api_usage(req, tenant_id="t1", auth_mode="api_key", api_key_value=None)

    @pytest.mark.asyncio
    async def test_no_api_key_no_fingerprint(self):
        from backend.fastapi.app.deps import _audit_api_usage
        store = []
        req = self._make_request(store)
        await _audit_api_usage(req, tenant_id="t1", auth_mode="bearer", api_key_value=None)
        assert store[0]["api_key_fingerprint"] is None

    @pytest.mark.asyncio
    async def test_prunes_when_over_max(self):
        from backend.fastapi.app.deps import _audit_api_usage
        store = [{"id": i} for i in range(2000)]
        req = self._make_request(store)
        with patch.dict(os.environ, {"API_USAGE_AUDIT_MAX": "100"}):
            await _audit_api_usage(req, tenant_id="t1", auth_mode="api_key", api_key_value="k")
        assert len(store) <= 100

    @pytest.mark.asyncio
    async def test_forwarded_for_header_used(self):
        from backend.fastapi.app.deps import _audit_api_usage
        store = []
        req = self._make_request(store)
        req.headers.get = MagicMock(side_effect=lambda k, d='': {
            'X-Forwarded-For': '10.0.0.1, 192.168.1.1',
            'User-Agent': 'test',
        }.get(k, d))
        await _audit_api_usage(req, tenant_id="t1", auth_mode="api_key", api_key_value=None)
        assert store[0]["ip_hash"] != ''


class TestSecretsManagerClearCaches:
    def test_clear_caches_calls_hashicorp(self):
        from backend.fastapi.app.vault.secrets_manager import SecretsManager
        mgr = SecretsManager.__new__(SecretsManager)
        mgr.hashicorp = MagicMock()
        mgr.clear_caches()
        mgr.hashicorp.clear_cache.assert_called_once()
