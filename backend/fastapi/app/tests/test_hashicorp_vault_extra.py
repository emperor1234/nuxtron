"""
Tests for HashiCorpVaultClient._detect_auth_method not covered by existing tests.
"""
from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

from backend.fastapi.app.vault.hashicorp_vault import HashiCorpVaultClient


class TestDetectAuthMethod:
    def test_token_when_vault_token_set(self) -> None:
        with patch.dict(os.environ, {"VAULT_TOKEN": "s.abc123", "VAULT_ROLE": "", "VAULT_JWT": ""}):
            client = HashiCorpVaultClient(vault_token="s.abc123")
            assert client._detect_auth_method() == "token"

    def test_jwt_when_role_and_jwt_set(self) -> None:
        client = HashiCorpVaultClient.__new__(HashiCorpVaultClient)
        client.vault_token = None
        client.vault_role = "my-role"
        client.vault_jwt = "my-jwt-token"
        assert client._detect_auth_method() == "jwt"

    def test_kubernetes_when_only_role_set(self) -> None:
        client = HashiCorpVaultClient.__new__(HashiCorpVaultClient)
        client.vault_token = None
        client.vault_role = "my-role"
        client.vault_jwt = None
        assert client._detect_auth_method() == "kubernetes"

    def test_fallback_to_token_when_nothing_set(self) -> None:
        client = HashiCorpVaultClient.__new__(HashiCorpVaultClient)
        client.vault_token = None
        client.vault_role = None
        client.vault_jwt = None
        assert client._detect_auth_method() == "token"
