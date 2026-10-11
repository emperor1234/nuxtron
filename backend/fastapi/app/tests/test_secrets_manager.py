"""Tests for the HashiCorp-backed secrets manager."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

if "hvac" not in sys.modules:
    sys.modules["hvac"] = MagicMock()


def _make_manager(*, connected: bool = False):
    from backend.fastapi.app.vault.secrets_manager import SecretsManager

    client = MagicMock()
    client.is_connected.return_value = connected
    client.get_secret.return_value = None
    client.get_database_credentials.return_value = None
    with patch(
        "backend.fastapi.app.vault.secrets_manager.get_vault_client",
        return_value=client,
    ):
        manager = SecretsManager()
    return manager, client


def test_hashicorp_is_the_primary_backend():
    from backend.fastapi.app.vault.secrets_manager import VaultBackend

    manager, _ = _make_manager()
    assert manager.primary_backend == VaultBackend.HASHICORP


def test_get_secret_returns_hashicorp_value():
    manager, client = _make_manager(connected=True)
    client.get_secret.return_value = "vault-secret"

    result = manager.get_secret(
        "MY_SECRET",
        secret_path="secret/data/app/MY_SECRET",
    )

    assert result == "vault-secret"


def test_get_secret_falls_back_to_environment():
    manager, client = _make_manager()
    client.is_connected.return_value = False
    with patch.dict(os.environ, {"MY_ENV_SECRET": "env-value"}):
        assert manager.get_secret("MY_ENV_SECRET") == "env-value"


def test_get_database_credentials_uses_dynamic_credentials():
    manager, client = _make_manager(connected=True)
    client.get_database_credentials.return_value = {
        "username": "user",
        "password": "password",
    }

    assert manager.get_database_credentials("app-role") == {
        "username": "user",
        "password": "password",
    }


def test_get_database_credentials_falls_back_to_postgres_environment():
    manager, _ = _make_manager()
    with patch.dict(
        os.environ,
        {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "nuxtron",
            "POSTGRES_USER": "nuxtron",
        },
    ):
        credentials = manager.get_database_credentials()

    assert credentials
    assert credentials["host"] == "localhost"
    assert credentials["database"] == "nuxtron"


def test_set_secret_uses_hashicorp():
    manager, client = _make_manager(connected=True)
    client.rotate_secret.return_value = True

    assert manager.set_secret("MY_KEY", "value") is True
    client.rotate_secret.assert_called_once()


def test_health_check_only_reports_hashicorp():
    manager, client = _make_manager()
    client.is_connected.return_value = False

    health = manager.health_check()

    assert set(health) == {
        "hashicorp_vault",
        "primary_backend",
        "local_fallback_enabled",
    }
