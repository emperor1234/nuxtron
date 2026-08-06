"""Tests for vault/hashicorp_vault.py — HashiCorpVaultClient."""
from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

# Mock hvac at import time since it may not be installed
mock_hvac = MagicMock()
sys.modules.setdefault("hvac", mock_hvac)

from backend.fastapi.app.vault.hashicorp_vault import HashiCorpVaultClient  # noqa: E402


def _make_client(**kwargs):
    """Create a HashiCorpVaultClient with test defaults."""
    defaults = {
        "vault_addr": "http://test-vault:8200",
        "vault_token": "test-token",
    }
    defaults.update(kwargs)
    return HashiCorpVaultClient(**defaults)


class TestDetectAuthMethod:
    def test_token_when_token_set(self):
        c = _make_client(vault_token="mytoken")
        assert c._auth_method == "token"

    def test_jwt_when_role_and_jwt(self):
        c = _make_client(vault_token=None, vault_role="my-role", vault_jwt="jwt-value")
        assert c._auth_method == "jwt"

    def test_kubernetes_when_role_only(self):
        c = _make_client(vault_token=None, vault_role="k8s-role", vault_jwt=None)
        assert c._auth_method == "kubernetes"

    def test_token_when_nothing_set(self):
        with patch.dict(os.environ, {}, clear=True):
            c = HashiCorpVaultClient(vault_addr="http://v:8200")
        assert c._auth_method == "token"


class TestConnect:
    def test_token_auth_returns_true(self):
        c = _make_client(vault_token="tok")
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        with patch("backend.fastapi.app.vault.hashicorp_vault.hvac.Client", return_value=mock_client):
            result = c.connect()
        assert result is True

    def test_connect_exception_returns_false(self):
        c = _make_client(vault_token="tok")
        with patch("backend.fastapi.app.vault.hashicorp_vault.hvac.Client", side_effect=Exception("fail")):
            result = c.connect()
        assert result is False

    def test_jwt_auth_calls_jwt_login(self):
        c = _make_client(vault_token=None, vault_role="r", vault_jwt="j")
        mock_client = MagicMock()
        with patch("backend.fastapi.app.vault.hashicorp_vault.hvac.Client", return_value=mock_client):
            result = c.connect()
        assert result is True
        mock_client.auth.jwt.jwt_login.assert_called_once_with(role="r", jwt="j")

    def test_no_auth_method_returns_false(self):
        c = _make_client(vault_token=None, vault_role=None, vault_jwt=None)
        c._auth_method = "token"  # no token set → falls through
        mock_client = MagicMock()
        with patch("backend.fastapi.app.vault.hashicorp_vault.hvac.Client", return_value=mock_client):
            result = c.connect()
        # token auth requires vault_token to be truthy
        assert result is False


class TestGetSecret:
    def test_returns_none_when_not_connected(self):
        c = _make_client()
        c.client = None
        assert c.get_secret("secret/data/myapp/db") is None

    def test_reads_from_vault(self):
        c = _make_client()
        mock_client = MagicMock()
        mock_client.secrets.kv.read_secret_version.return_value = {
            "data": {"data": {"password": "s3cr3t"}}
        }
        c.client = mock_client
        result = c.get_secret("secret/data/app/db", key="password")
        assert result == "s3cr3t"

    def test_returns_full_dict_when_no_key(self):
        c = _make_client()
        mock_client = MagicMock()
        mock_client.secrets.kv.read_secret_version.return_value = {
            "data": {"data": {"user": "admin", "pass": "pw"}}
        }
        c.client = mock_client
        result = c.get_secret("secret/data/db")
        assert result == {"user": "admin", "pass": "pw"}

    def test_returns_cached_value_within_ttl(self):
        c = _make_client(cache_ttl_seconds=3600)
        mock_client = MagicMock()
        c.client = mock_client
        # Pre-populate cache
        c.cache["secret/mypath"] = ({"key": "val"}, datetime.now(UTC))
        result = c.get_secret("secret/mypath", key="key")
        assert result == "val"
        mock_client.secrets.kv.read_secret_version.assert_not_called()

    def test_refreshes_expired_cache(self):
        c = _make_client(cache_ttl_seconds=10)
        mock_client = MagicMock()
        mock_client.secrets.kv.read_secret_version.return_value = {
            "data": {"data": {"k": "fresh"}}
        }
        c.client = mock_client
        old_time = datetime.now(UTC) - timedelta(seconds=3600)
        c.cache["secret/p"] = ({"k": "old"}, old_time)
        result = c.get_secret("secret/p", key="k")
        assert result == "fresh"

    def test_returns_none_on_exception(self):
        c = _make_client()
        mock_client = MagicMock()
        mock_client.secrets.kv.read_secret_version.side_effect = Exception("oops")
        c.client = mock_client
        assert c.get_secret("bad/path") is None


class TestGetDatabaseCredentials:
    def test_returns_none_when_not_connected(self):
        c = _make_client()
        c.client = None
        assert c.get_database_credentials("role") is None

    def test_returns_dict_on_success(self):
        c = _make_client()
        mock_client = MagicMock()
        mock_client.secrets.database.generate_credentials.return_value = {
            "data": {"username": "u", "password": "p"}
        }
        c.client = mock_client
        result = c.get_database_credentials("myrole")
        assert result == {"username": "u", "password": "p"}

    def test_returns_none_on_exception(self):
        c = _make_client()
        mock_client = MagicMock()
        mock_client.secrets.database.generate_credentials.side_effect = Exception("err")
        c.client = mock_client
        assert c.get_database_credentials("role") is None


class TestRotateSecret:
    def test_returns_false_when_not_connected(self):
        c = _make_client()
        c.client = None
        assert c.rotate_secret("path", {"k": "v"}) is False

    def test_rotates_and_clears_cache(self):
        c = _make_client()
        mock_client = MagicMock()
        c.client = mock_client
        c.cache["path"] = ({"old": "val"}, datetime.now(UTC))
        result = c.rotate_secret("path", {"k": "new"})
        assert result is True
        assert "path" not in c.cache

    def test_returns_false_on_exception(self):
        c = _make_client()
        mock_client = MagicMock()
        mock_client.secrets.kv.create_or_update_secret.side_effect = Exception("err")
        c.client = mock_client
        assert c.rotate_secret("path", {"k": "v"}) is False


class TestClearCache:
    def test_clears_all_entries(self):
        c = _make_client()
        c.cache["a"] = ({"x": 1}, datetime.now(UTC))
        c.cache["b"] = ({"y": 2}, datetime.now(UTC))
        c.clear_cache()
        assert c.cache == {}


class TestIsConnected:
    def test_not_connected_when_no_client(self):
        c = _make_client()
        c.client = None
        assert c.is_connected() is False

    def test_connected_when_authenticated(self):
        c = _make_client()
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        c.client = mock_client
        assert c.is_connected() is True

    def test_not_connected_on_exception(self):
        c = _make_client()
        mock_client = MagicMock()
        mock_client.is_authenticated.side_effect = Exception("fail")
        c.client = mock_client
        assert c.is_connected() is False


class TestGetVaultClient:
    def test_returns_singleton(self):
        from backend.fastapi.app.vault import hashicorp_vault
        hashicorp_vault._vault_instance = None
        with patch.object(HashiCorpVaultClient, "connect", return_value=False):
            c1 = hashicorp_vault.get_vault_client()
            c2 = hashicorp_vault.get_vault_client()
        assert c1 is c2
        # Reset for other tests
        hashicorp_vault._vault_instance = None
