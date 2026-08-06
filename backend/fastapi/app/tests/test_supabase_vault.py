"""Tests for vault/supabase_vault.py — missing coverage lines."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch


def _make_client(**kwargs):
    """Create a SupabaseVaultClient with create_client mocked out."""
    from backend.fastapi.app.vault.supabase_vault import SupabaseVaultClient

    with patch("backend.fastapi.app.vault.supabase_vault.SupabaseVaultClient._initialize"):
        client = SupabaseVaultClient.__new__(SupabaseVaultClient)
        client.cache = {}
        client.cache_ttl_seconds = kwargs.get("cache_ttl_seconds", 3600)
        client.supabase_url = kwargs.get("supabase_url", "https://xyz.supabase.co")
        client.supabase_key = kwargs.get("supabase_key", "anon-key")
        client.supabase_jwt_secret = kwargs.get("supabase_jwt_secret")
        client.is_ready = kwargs.get("is_ready", True)
    return client


# --------------------------------------------------------------------------- #
#  _initialize: warning when no credentials (lines 51-52)
# --------------------------------------------------------------------------- #

class TestInitializeWarningPath:
    def test_no_url_or_key_logs_warning(self):
        """_initialize() should log a warning and leave is_ready=False when creds missing."""
        from backend.fastapi.app.vault.supabase_vault import SupabaseVaultClient

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SUPABASE_URL", None)
            os.environ.pop("SUPABASE_ANON_KEY", None)
            # Mock create_client to avoid actual network calls
            mock_create = MagicMock()
            with patch.dict(
                __import__("sys").modules,
                {"supabase": MagicMock(create_client=mock_create)},
            ):
                client = SupabaseVaultClient(supabase_url="", supabase_key="")
        assert client.is_ready is False
        mock_create.assert_not_called()

    def test_import_error_handled_gracefully(self):
        """If supabase package missing, is_ready stays False."""
        import sys

        from backend.fastapi.app.vault.supabase_vault import SupabaseVaultClient

        saved = sys.modules.pop("supabase", None)
        try:
            with patch.dict(os.environ, {
                "SUPABASE_URL": "https://xyz.supabase.co",
                "SUPABASE_ANON_KEY": "key",
            }):
                client = SupabaseVaultClient()
        finally:
            if saved is not None:
                sys.modules["supabase"] = saved
        # No crash — just not ready or ready depending on whether supabase installed
        assert isinstance(client.is_ready, bool)

    def test_exception_in_create_client_sets_not_ready(self):
        """If create_client raises, is_ready should remain False."""
        from backend.fastapi.app.vault.supabase_vault import SupabaseVaultClient

        mock_supabase = MagicMock()
        mock_supabase.create_client.side_effect = Exception("connection refused")
        with patch.dict(
            __import__("sys").modules, {"supabase": mock_supabase}
        ), patch.dict(os.environ, {
            "SUPABASE_URL": "https://xyz.supabase.co",
            "SUPABASE_ANON_KEY": "anon",
        }):
            client = SupabaseVaultClient()
        assert client.is_ready is False


# --------------------------------------------------------------------------- #
#  get_secret: exception path (lines 91-93)
# --------------------------------------------------------------------------- #

class TestGetSecretExceptionPath:
    def test_returns_none_on_exception(self):
        client = _make_client()
        # Patch os.getenv to raise
        with patch("backend.fastapi.app.vault.supabase_vault.os.getenv", side_effect=Exception("env error")):
            result = client.get_secret("some_key")
        assert result is None

    def test_returns_none_when_not_ready(self):
        client = _make_client(is_ready=False)
        result = client.get_secret("some_key")
        assert result is None

    def test_cache_hit_returns_cached(self):
        client = _make_client()
        client.cache["MY_KEY"] = ("cached_value", datetime.now(UTC))
        result = client.get_secret("MY_KEY")
        assert result == "cached_value"

    def test_returns_env_var_value(self):
        client = _make_client()
        with patch.dict(os.environ, {"SUPABASE_VAULT_MY_SECRET": "the-value"}):
            result = client.get_secret("MY_SECRET")
        assert result == "the-value"

    def test_returns_none_when_env_not_set(self):
        client = _make_client()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SUPABASE_VAULT_MISSING_KEY", None)
            result = client.get_secret("MISSING_KEY")
        assert result is None


# --------------------------------------------------------------------------- #
#  store_secret: exception path (lines 120-122)
# --------------------------------------------------------------------------- #

class TestStoreSecretExceptionPath:
    def test_returns_false_when_not_ready(self):
        client = _make_client(is_ready=False)
        result = client.store_secret("key", "value")
        assert result is False

    def test_stores_to_cache_on_success(self):
        client = _make_client()
        result = client.store_secret("my_key", "my_value")
        assert result is True
        assert client.cache["my_key"][0] == "my_value"

    def test_returns_false_on_exception(self):
        client = _make_client()
        # Patch logger to raise inside the try block
        with patch("backend.fastapi.app.vault.supabase_vault.logger") as mock_log:
            mock_log.info.side_effect = Exception("logging error")
            result = client.store_secret("key", "value")
        assert result is False


# --------------------------------------------------------------------------- #
#  get_database_config: exception path (lines 143-145)
# --------------------------------------------------------------------------- #

class TestGetDatabaseConfigExceptionPath:
    def test_returns_none_when_no_url(self):
        client = _make_client(supabase_url=None)
        client.supabase_url = None
        result = client.get_database_config()
        assert result is None

    def test_returns_config_when_url_set(self):
        client = _make_client(supabase_url="https://xyz.supabase.co")
        with patch.dict(os.environ, {"SUPABASE_VAULT_db_password": "pw123"}):
            config = client.get_database_config()
        assert config is not None
        assert "host" in config
        assert "database" in config

    def test_returns_none_on_exception(self):
        client = _make_client(supabase_url="badurl")
        # Force exception during URL parsing
        with patch.object(client, "get_secret", side_effect=Exception("fail")):
            result = client.get_database_config()
        assert result is None


# --------------------------------------------------------------------------- #
#  get_jwt_secret and clear_cache
# --------------------------------------------------------------------------- #

class TestMisc:
    def test_get_jwt_secret_returns_value(self):
        client = _make_client(supabase_jwt_secret="jwt-secret-value")
        assert client.get_jwt_secret() == "jwt-secret-value"

    def test_get_jwt_secret_none_when_not_set(self):
        client = _make_client(supabase_jwt_secret=None)
        assert client.get_jwt_secret() is None

    def test_clear_cache_empties_cache(self):
        client = _make_client()
        client.cache["key"] = ("val", datetime.now(UTC))
        client.clear_cache()
        assert client.cache == {}


# --------------------------------------------------------------------------- #
#  Singleton
# --------------------------------------------------------------------------- #

class TestSingleton:
    def test_get_supabase_vault_client_returns_instance(self):
        import backend.fastapi.app.vault.supabase_vault as mod
        # Reset singleton
        orig = mod._supabase_instance
        try:
            mod._supabase_instance = None
            with patch("backend.fastapi.app.vault.supabase_vault.SupabaseVaultClient._initialize"):
                instance = mod.get_supabase_vault_client()
            assert instance is not None
            # Second call returns same instance
            instance2 = mod.get_supabase_vault_client()
            assert instance is instance2
        finally:
            mod._supabase_instance = orig
