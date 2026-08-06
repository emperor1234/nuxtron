"""Tests for vault/supabase_vault.py and vault/secrets_manager.py."""
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from backend.fastapi.app.vault.supabase_vault import SupabaseVaultClient

# ── SupabaseVaultClient ───────────────────────────────────────────────────────

def _make_ready_client(url="https://fake.supabase.co", key="anon-key", **kwargs):
    """Create a SupabaseVaultClient with supabase import mocked."""
    with patch("builtins.__import__", side_effect=lambda name, *a, **kw: (
        MagicMock() if name == "supabase" else __import__(name, *a, **kw)
    )):
        client = SupabaseVaultClient(supabase_url=url, supabase_key=key, **kwargs)
    return client


class TestSupabaseVaultClientInit:
    def test_not_ready_without_credentials(self):
        client = SupabaseVaultClient(supabase_url=None, supabase_key=None)
        assert client.is_ready is False

    def test_ready_with_valid_credentials(self):
        client = _make_ready_client()
        assert client.is_ready is True

    def test_not_ready_on_import_error(self):
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "supabase":
                raise ImportError("supabase not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            client = SupabaseVaultClient(
                supabase_url="https://fake.supabase.co",
                supabase_key="key",
            )
        assert client.is_ready is False


class TestSupabaseVaultClientGetSecret:
    def test_returns_none_when_not_ready(self):
        client = SupabaseVaultClient()
        assert client.get_secret("MY_SECRET") is None

    def test_returns_env_fallback(self):
        client = _make_ready_client()
        with patch.dict(os.environ, {"SUPABASE_VAULT_MY_KEY": "myvalue"}):
            result = client.get_secret("MY_KEY")
        assert result == "myvalue"

    def test_caches_result(self):
        client = _make_ready_client()
        with patch.dict(os.environ, {"SUPABASE_VAULT_CACHED_KEY": "cached-val"}):
            client.get_secret("CACHED_KEY")  # populate cache
        assert "CACHED_KEY" in client.cache

    def test_returns_cached_value(self):
        client = _make_ready_client()
        client.cache["MYKEY"] = ("cached-secret", datetime.now(UTC))
        result = client.get_secret("MYKEY")
        assert result == "cached-secret"

    def test_ignores_expired_cache(self):
        client = _make_ready_client(cache_ttl_seconds=60)
        old_time = datetime.now(UTC) - timedelta(seconds=3600)
        client.cache["EXPIRED_KEY"] = ("old-value", old_time)
        with patch.dict(os.environ, {"SUPABASE_VAULT_EXPIRED_KEY": "new-value"}):
            result = client.get_secret("EXPIRED_KEY")
        assert result == "new-value"

    def test_returns_none_when_env_not_set(self):
        client = _make_ready_client()
        os.environ.pop("SUPABASE_VAULT_NONEXISTENT", None)
        result = client.get_secret("NONEXISTENT")
        assert result is None


class TestSupabaseVaultClientStoreSecret:
    def test_store_returns_false_when_not_ready(self):
        client = SupabaseVaultClient()
        result = client.store_secret("key", "value")
        assert result is False

    def test_store_returns_true_and_caches(self):
        client = _make_ready_client()
        result = client.store_secret("mykey", "myvalue")
        assert result is True
        assert "mykey" in client.cache


class TestSupabaseVaultClientHelpers:
    def test_get_jwt_secret(self):
        client = SupabaseVaultClient(supabase_jwt_secret="jwt-secret-123")
        assert client.get_jwt_secret() == "jwt-secret-123"

    def test_clear_cache(self):
        client = _make_ready_client(url="https://projectid.supabase.co")
        client.cache["k"] = ("v", datetime.now(UTC))
        client.clear_cache()
        assert client.cache == {}

    def test_get_database_config_returns_none_without_url(self):
        client = SupabaseVaultClient()
        result = client.get_database_config()
        assert result is None

    def test_get_database_config_returns_dict(self):
        client = _make_ready_client(url="https://projectid.supabase.co")
        with patch.dict(os.environ, {"SUPABASE_VAULT_db_password": "dbpass"}):
            result = client.get_database_config()
        assert isinstance(result, dict)
        assert "host" in result
        assert "database" in result
