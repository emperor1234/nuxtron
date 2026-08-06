"""
Unit tests for vault_config.py - vault initialization and configuration helpers.
Uses mocks to avoid real vault/DB connections.
"""
from __future__ import annotations

import logging
import os
import sys
import types

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest

# vault_config.py does `from vault import SecretsManager, get_secrets_manager`
# where `vault` is actually `backend.fastapi.app.vault` (a local package).
# We must stub it before importing vault_config.
_vault_stub = types.ModuleType("vault")
_mock_manager = MagicMock()
_mock_manager.health_check.return_value = {
    "hashicorp_vault": {"connected": False, "address": "http://vault:8200"},
    "supabase_vault": {"ready": False, "url": "https://supabase.example.com"},
    "primary_backend": "local",
    "local_fallback_enabled": True,
}
_mock_manager.get_api_key.return_value = "test-api-key"
_mock_manager.get_encryption_key.return_value = "test-enc-key"
_mock_manager.get_database_password.return_value = None
_mock_manager.get_secret.return_value = None
_vault_stub.SecretsManager = MagicMock
_vault_stub.get_secrets_manager = MagicMock(return_value=_mock_manager)
sys.modules.setdefault("vault", _vault_stub)

import backend.fastapi.app.vault_config as vault_config_mod  # noqa: E402

PATCH_TARGET = "backend.fastapi.app.vault_config.get_secrets_manager"


def _make_mock_manager(
    api_key=None,
    enc_key=None,
    db_password=None,
):
    manager = MagicMock()
    manager.get_api_key.return_value = api_key or "test-api-key"
    manager.get_encryption_key.return_value = enc_key or "test-enc-key"
    manager.get_database_password.return_value = db_password
    manager.get_secret.return_value = None
    manager.health_check.return_value = {
        "hashicorp_vault": {"connected": False, "address": "http://vault:8200"},
        "supabase_vault": {"ready": False, "url": "https://supabase.example.com"},
        "primary_backend": "local",
        "local_fallback_enabled": True,
    }
    return manager


class TestInitializeSecretsManager:
    def test_returns_manager(self):
        mock_mgr = _make_mock_manager()
        with patch(PATCH_TARGET, return_value=mock_mgr):
            result = vault_config_mod.initialize_secrets_manager()
            assert result is mock_mgr

    def test_calls_health_check(self):
        mock_mgr = _make_mock_manager()
        with patch(PATCH_TARGET, return_value=mock_mgr):
            vault_config_mod.initialize_secrets_manager()
            mock_mgr.health_check.assert_called_once()

    def test_connected_vault_branch(self):
        mock_mgr = _make_mock_manager()
        mock_mgr.health_check.return_value = {
            "hashicorp_vault": {"connected": True, "address": "http://vault:8200"},
            "supabase_vault": {"ready": True, "url": "https://example.supabase.co"},
            "primary_backend": "hashicorp",
            "local_fallback_enabled": False,
        }
        with patch(PATCH_TARGET, return_value=mock_mgr):
            result = vault_config_mod.initialize_secrets_manager()
            assert result is mock_mgr


class TestLoadSecretsFromVault:
    def test_returns_dict_of_secrets(self):
        mock_mgr = _make_mock_manager()
        with patch(PATCH_TARGET, return_value=mock_mgr), patch.dict(os.environ, {}, clear=False):
            secrets = vault_config_mod.load_secrets_from_vault()
            assert isinstance(secrets, dict)
            assert "FASTAPI_API_KEY" in secrets
            assert "APP_ENC_KEY" in secrets

    def test_sets_env_var_for_api_key(self):
        mock_mgr = _make_mock_manager(api_key="my-test-key-xyz")
        with patch(PATCH_TARGET, return_value=mock_mgr), patch.dict(os.environ, {}, clear=False):
            vault_config_mod.load_secrets_from_vault()
            assert os.environ.get("FASTAPI_API_KEY") is not None

    def test_none_secrets_dont_crash(self):
        manager = MagicMock()
        manager.get_api_key.return_value = None
        manager.get_encryption_key.return_value = None
        manager.get_database_password.return_value = None
        manager.get_secret.return_value = None
        with patch(PATCH_TARGET, return_value=manager), patch.dict(os.environ, {}, clear=False):
            secrets = vault_config_mod.load_secrets_from_vault()
            assert isinstance(secrets, dict)


class TestGetVaultSecret:
    def test_returns_secret_value(self):
        mock_mgr = _make_mock_manager()
        mock_mgr.get_secret.return_value = "my-secret-value"
        with patch(PATCH_TARGET, return_value=mock_mgr):
            val = vault_config_mod.get_vault_secret("MY_SECRET", required=False)
            assert val == "my-secret-value"

    def test_returns_none_when_not_required(self):
        mock_mgr = _make_mock_manager()
        mock_mgr.get_secret.return_value = None
        with patch(PATCH_TARGET, return_value=mock_mgr):
            val = vault_config_mod.get_vault_secret("MISSING_SECRET", required=False)
            assert val is None

    def test_raises_when_required_and_missing(self):
        mock_mgr = _make_mock_manager()
        mock_mgr.get_secret.return_value = None
        with patch(PATCH_TARGET, return_value=mock_mgr):
            with pytest.raises(RuntimeError, match="Required secret not found"):
                vault_config_mod.get_vault_secret("REQUIRED_SECRET", required=True)

    def test_passes_path_and_field(self):
        mock_mgr = _make_mock_manager()
        mock_mgr.get_secret.return_value = "value"
        with patch(PATCH_TARGET, return_value=mock_mgr):
            vault_config_mod.get_vault_secret(
                "SECRET", secret_path="my/path", secret_field="field", required=False
            )
            mock_mgr.get_secret.assert_called_with(
                "SECRET", secret_path="my/path", secret_field="field"
            )


class TestConfigureVaultLogging:
    def test_verbose_mode_sets_debug(self):
        vault_config_mod.configure_vault_logging(verbose=True)
        vault_logger = logging.getLogger("vault")
        assert vault_logger.level == logging.DEBUG

    def test_normal_mode_sets_info(self):
        vault_config_mod.configure_vault_logging(verbose=False)
        vault_logger = logging.getLogger("vault")
        assert vault_logger.level == logging.INFO


class TestGetVaultHealth:
    def test_returns_dict_with_required_keys(self):
        mock_mgr = _make_mock_manager()
        with patch(PATCH_TARGET, return_value=mock_mgr):
            health = vault_config_mod.get_vault_health()
            assert isinstance(health, dict)
            assert "vaults" in health
            assert "primary" in health
            assert "timestamp" in health

    def test_vaults_has_hashicorp_and_supabase(self):
        mock_mgr = _make_mock_manager()
        with patch(PATCH_TARGET, return_value=mock_mgr):
            health = vault_config_mod.get_vault_health()
            assert "hashicorp" in health["vaults"]
            assert "supabase" in health["vaults"]

    def test_primary_backend_is_string(self):
        mock_mgr = _make_mock_manager()
        with patch(PATCH_TARGET, return_value=mock_mgr):
            health = vault_config_mod.get_vault_health()
            assert isinstance(health["primary"], str)
