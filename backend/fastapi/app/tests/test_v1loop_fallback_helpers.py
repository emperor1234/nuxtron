"""Tests for small helper functions in v1_loop.py and fallback_pressure_guard.py."""
import os
from unittest.mock import patch

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")


class TestGetApiKey:
    def test_returns_env_var(self):
        from backend.fastapi.app.routers.v1_loop import _get_api_key
        with patch.dict(os.environ, {"FASTAPI_API_KEY": "my-secret-key"}, clear=False):
            assert _get_api_key() == "my-secret-key"

    def test_returns_empty_when_unset(self):
        from backend.fastapi.app.routers.v1_loop import _get_api_key
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FASTAPI_API_KEY", None)
            result = _get_api_key()
            assert result == ""

    def test_strips_whitespace(self):
        from backend.fastapi.app.routers.v1_loop import _get_api_key
        with patch.dict(os.environ, {"FASTAPI_API_KEY": "  my-key  "}, clear=False):
            assert _get_api_key() == "my-key"


class TestFallbackPressureHeaders:
    def test_returns_dict_with_expected_keys(self):
        from backend.fastapi.app.fallback_pressure_guard import _headers
        result = _headers("tenant-123")
        assert "X-API-Key" in result
        assert "X-Tenant-Id" in result

    def test_tenant_id_set_correctly(self):
        from backend.fastapi.app.fallback_pressure_guard import _headers
        result = _headers("my-tenant")
        assert result["X-Tenant-Id"] == "my-tenant"

    def test_api_key_from_env(self):
        from backend.fastapi.app.fallback_pressure_guard import _headers
        with patch.dict(os.environ, {"FASTAPI_API_KEY": "custom-key"}, clear=False):
            result = _headers("t")
            assert result["X-API-Key"] == "custom-key"

    def test_api_key_fallback(self):
        from backend.fastapi.app.fallback_pressure_guard import _headers
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FASTAPI_API_KEY", None)
            result = _headers("t")
            assert result["X-API-Key"] == "change-this-fastapi-key"
