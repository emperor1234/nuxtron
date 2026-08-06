"""Tests for vault/secrets_manager.py — SecretsManager unified vault interface."""
from __future__ import annotations

import os

# Ensure hvac is mocked before importing secrets_manager
import sys
from unittest.mock import MagicMock, patch

if "hvac" not in sys.modules:
    sys.modules["hvac"] = MagicMock()


def _make_manager(hashicorp_connected: bool = False, supabase_ready: bool = False, **kwargs):
    """Create a SecretsManager with mocked backends."""
    from backend.fastapi.app.vault.secrets_manager import SecretsManager

    mock_hashi = MagicMock()
    mock_hashi.is_connected.return_value = hashicorp_connected
    mock_hashi.get_secret.return_value = None
    mock_hashi.get_database_credentials.return_value = None

    mock_supa = MagicMock()
    mock_supa.is_ready = supabase_ready
    mock_supa.get_secret.return_value = None
    mock_supa.get_database_config.return_value = None

    with (
        patch("backend.fastapi.app.vault.secrets_manager.get_vault_client", return_value=mock_hashi),
        patch("backend.fastapi.app.vault.secrets_manager.get_supabase_vault_client", return_value=mock_supa),
    ):
        mgr = SecretsManager(**kwargs)

    mgr.hashicorp = mock_hashi
    mgr.supabase = mock_supa
    return mgr, mock_hashi, mock_supa


class TestDetectPrimaryBackend:
    def test_hashicorp_primary_when_connected(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, _, _ = _make_manager(hashicorp_connected=True)
        assert mgr.primary_backend == VaultBackend.HASHICORP

    def test_supabase_primary_when_hashicorp_not_connected(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, _, _ = _make_manager(hashicorp_connected=False, supabase_ready=True)
        assert mgr.primary_backend == VaultBackend.SUPABASE

    def test_hashicorp_default_when_nothing_available(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, _, _ = _make_manager(hashicorp_connected=False, supabase_ready=False)
        assert mgr.primary_backend == VaultBackend.HASHICORP


class TestGetSecret:
    def test_returns_hashicorp_value(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, mock_hashi, _ = _make_manager(hashicorp_connected=True)
        mock_hashi.is_connected.return_value = True
        mock_hashi.get_secret.return_value = "vault-secret"
        result = mgr.get_secret("MY_SECRET", secret_path="secret/data/app/MY_SECRET", backend=VaultBackend.HASHICORP)
        assert result == "vault-secret"

    def test_falls_back_to_supabase(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, mock_hashi, mock_supa = _make_manager(supabase_ready=True)
        mock_hashi.is_connected.return_value = False
        mock_supa.is_ready = True
        mock_supa.get_secret.return_value = "supa-secret"
        result = mgr.get_secret("MY_SECRET", backend=VaultBackend.HASHICORP)
        assert result == "supa-secret"

    def test_falls_back_to_env_var(self):
        mgr, mock_hashi, mock_supa = _make_manager()
        mock_hashi.is_connected.return_value = False
        mock_supa.is_ready = False
        with patch.dict(os.environ, {"MY_ENV_SECRET": "env-value"}):
            result = mgr.get_secret("MY_ENV_SECRET")
        assert result == "env-value"

    def test_returns_none_when_nowhere_found(self):
        mgr, mock_hashi, mock_supa = _make_manager()
        mock_hashi.is_connected.return_value = False
        mock_supa.is_ready = False
        os.environ.pop("NONEXISTENT_SECRET_XYZ", None)
        result = mgr.get_secret("NONEXISTENT_SECRET_XYZ")
        assert result is None

    def test_supabase_backend_queries_supabase_first(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, mock_hashi, mock_supa = _make_manager(supabase_ready=True)
        mock_supa.is_ready = True
        mock_supa.get_secret.return_value = "supa-first"
        result = mgr.get_secret("MY_KEY", backend=VaultBackend.SUPABASE)
        assert result == "supa-first"
        mock_supa.get_secret.assert_called_once()


class TestGetFromHashicorp:
    def test_returns_none_when_not_connected(self):
        mgr, mock_hashi, _ = _make_manager()
        mock_hashi.is_connected.return_value = False
        assert mgr._get_from_hashicorp("MY_KEY") is None

    def test_uses_custom_path(self):
        mgr, mock_hashi, _ = _make_manager(hashicorp_connected=True)
        mock_hashi.is_connected.return_value = True
        mock_hashi.get_secret.return_value = "value"
        result = mgr._get_from_hashicorp("MY_KEY", secret_path="custom/path", secret_field="field")
        mock_hashi.get_secret.assert_called_once_with("custom/path", key="field")
        assert result == "value"

    def test_uses_default_path_when_none(self):
        mgr, mock_hashi, _ = _make_manager(hashicorp_connected=True)
        mock_hashi.is_connected.return_value = True
        mock_hashi.get_secret.return_value = None
        mgr._get_from_hashicorp("MY_KEY")
        mock_hashi.get_secret.assert_called_once_with("secret/data/app/MY_KEY", key="MY_KEY")

    def test_returns_none_on_exception(self):
        mgr, mock_hashi, _ = _make_manager(hashicorp_connected=True)
        mock_hashi.is_connected.return_value = True
        mock_hashi.get_secret.side_effect = Exception("boom")
        assert mgr._get_from_hashicorp("KEY") is None


class TestGetFromSupabase:
    def test_returns_none_when_not_ready(self):
        mgr, _, mock_supa = _make_manager()
        mock_supa.is_ready = False
        assert mgr._get_from_supabase("KEY") is None

    def test_returns_value_when_ready(self):
        mgr, _, mock_supa = _make_manager(supabase_ready=True)
        mock_supa.is_ready = True
        mock_supa.get_secret.return_value = "supa-val"
        assert mgr._get_from_supabase("KEY") == "supa-val"

    def test_returns_none_on_exception(self):
        mgr, _, mock_supa = _make_manager(supabase_ready=True)
        mock_supa.is_ready = True
        mock_supa.get_secret.side_effect = Exception("err")
        assert mgr._get_from_supabase("KEY") is None


class TestGetDatabaseCredentials:
    def test_supabase_returns_db_config(self):
        mgr, _, mock_supa = _make_manager(supabase_ready=True)
        mock_supa.get_database_config.return_value = {"url": "postgres://..."}
        result = mgr.get_database_credentials("supabase")
        assert result == {"url": "postgres://..."}

    def test_dynamic_creds_from_hashicorp(self):
        mgr, mock_hashi, _ = _make_manager(hashicorp_connected=True)
        mock_hashi.is_connected.return_value = True
        mock_hashi.get_database_credentials.return_value = {"username": "u", "password": "p"}
        result = mgr.get_database_credentials("myrole")
        assert result == {"username": "u", "password": "p"}

    def test_static_env_fallback(self):
        mgr, mock_hashi, _ = _make_manager()
        mock_hashi.is_connected.return_value = False
        with patch.dict(os.environ, {"DB_HOST": "localhost", "DB_NAME": "mydb"}):
            result = mgr.get_database_credentials("default")
        assert result["host"] == "localhost"
        assert result["database"] == "mydb"


class TestSetSecret:
    def test_hashicorp_set(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, mock_hashi, _ = _make_manager(hashicorp_connected=True)
        mock_hashi.is_connected.return_value = True
        mock_hashi.rotate_secret.return_value = True
        result = mgr.set_secret("MY_KEY", "val", backend=VaultBackend.HASHICORP)
        assert result is True

    def test_supabase_set(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, _, mock_supa = _make_manager(supabase_ready=True)
        mock_supa.is_ready = True
        mock_supa.store_secret.return_value = True
        result = mgr.set_secret("MY_KEY", "val", backend=VaultBackend.SUPABASE)
        assert result is True

    def test_returns_none_when_no_backend(self):
        from backend.fastapi.app.vault.secrets_manager import VaultBackend
        mgr, mock_hashi, mock_supa = _make_manager()
        mock_hashi.is_connected.return_value = False
        mock_supa.is_ready = False
        # Returns False explicitly when no backend is available
        result = mgr.set_secret("KEY", "val", backend=VaultBackend.SUPABASE)
        assert result is False


class TestRotateSecret:
    def test_rotates_via_hashicorp_when_connected(self):
        mgr, mock_hashi, _ = _make_manager(hashicorp_connected=True)
        mock_hashi.is_connected.return_value = True
        mock_hashi.rotate_secret.return_value = True
        result = mgr.rotate_secret("MY_KEY", secret_path="secret/data/app/MY_KEY")
        assert result is True

    def test_returns_false_when_not_available(self):
        mgr, mock_hashi, _ = _make_manager()
        mock_hashi.is_connected.return_value = False
        result = mgr.rotate_secret("KEY")
        assert result is False


class TestConvenienceMethods:
    def test_get_api_key_calls_get_secret(self):
        mgr, _, _ = _make_manager()
        mgr.get_secret = MagicMock(return_value="api-key-val")
        result = mgr.get_api_key()
        mgr.get_secret.assert_called_once_with(
            "FASTAPI_API_KEY",
            secret_path="secret/data/app/api/FASTAPI_API_KEY"
        )
        assert result == "api-key-val"

    def test_get_encryption_key_calls_get_secret(self):
        mgr, _, _ = _make_manager()
        mgr.get_secret = MagicMock(return_value="enc-key")
        result = mgr.get_encryption_key()
        mgr.get_secret.assert_called_once()
        assert result == "enc-key"

    def test_get_database_password_calls_get_secret(self):
        mgr, _, _ = _make_manager()
        mgr.get_secret = MagicMock(return_value="db-pass")
        result = mgr.get_database_password()
        mgr.get_secret.assert_called_once()
        assert result == "db-pass"


class TestHealthCheck:
    def test_returns_health_dict(self):
        mgr, mock_hashi, mock_supa = _make_manager()
        mock_hashi.is_connected.return_value = False
        mock_supa.is_ready = False
        result = mgr.health_check()
        assert "hashicorp_vault" in result
        assert "supabase_vault" in result
        assert result["hashicorp_vault"]["connected"] is False
        assert result["supabase_vault"]["ready"] is False
