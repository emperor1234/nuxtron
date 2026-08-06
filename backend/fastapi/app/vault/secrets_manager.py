"""
Unified Secrets Manager — HashiCorp Vault with environment fallback.

Historically this module coordinated HashiCorp Vault and a Supabase Vault
backend. Supabase has been removed from the project (we use PostgreSQL
directly); this manager now resolves secrets from HashiCorp Vault first, then
the process environment. The ``VaultBackend`` enum is retained for API
stability but only ``HASHICORP`` is a live backend.
"""

import logging
import os
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from .hashicorp_vault import get_vault_client

logger = logging.getLogger(__name__)


class VaultBackend(StrEnum):
    """Available vault backends. Only HASHICORP is live after Supabase removal."""

    HASHICORP = 'hashicorp'
    AUTO = 'auto'  # Resolves to HASHICORP (the only live backend).


class SecretsManager:
    """
    Secrets manager backed by HashiCorp Vault with an environment-variable
    fallback. Provides caching and a single retrieval interface.
    """

    def __init__(
        self,
        primary_backend: VaultBackend = VaultBackend.AUTO,
        enable_local_fallback: bool = True,
        cache_ttl_seconds: int = 3600,
    ):
        self.primary_backend = (
            VaultBackend.HASHICORP if primary_backend == VaultBackend.AUTO else primary_backend
        )
        self.enable_local_fallback = enable_local_fallback
        self.cache_ttl_seconds = cache_ttl_seconds

        self.hashicorp = get_vault_client()

        logger.info(f'✓ SecretsManager initialized (primary: {self.primary_backend.value})')

    def get_secret(
        self,
        secret_name: str,
        secret_path: str | None = None,
        secret_field: str | None = None,
        backend: VaultBackend | None = None,
    ) -> str | None:
        """
        Retrieve a secret.

        Resolution order: HashiCorp Vault → local environment variable → None.
        """
        del backend  # Only HashiCorp remains; kept for API compatibility.

        lookups: list[Callable[[], str | None]] = [
            lambda: self._get_from_hashicorp(secret_name, secret_path, secret_field),
        ]

        for lookup in lookups:
            secret = lookup()
            if secret:
                return secret

        if self.enable_local_fallback:
            secret = os.getenv(secret_name)
            if secret:
                logger.debug(f'📦 Using local env fallback for {secret_name}')
                return secret

        logger.warning(f'⚠ Secret not found: {secret_name}')
        return None

    def _get_from_hashicorp(
        self,
        secret_name: str,
        secret_path: str | None = None,
        secret_field: str | None = None,
    ) -> str | None:
        """Try to retrieve secret from HashiCorp Vault."""
        if not self.hashicorp.is_connected():
            return None

        try:
            if secret_path:
                return self.hashicorp.get_secret(secret_path, key=secret_field or secret_name)
            # Try standard path patterns
            path = f'secret/data/app/{secret_name}'
            return self.hashicorp.get_secret(path, key=secret_field or secret_name)
        except Exception as e:
            logger.debug(f'→ HashiCorp retrieval failed for {secret_name}: {e}')
            return None

    def get_database_credentials(
        self,
        role_or_source: str = 'default',
    ) -> dict[str, str] | None:
        """
        Retrieve database credentials.

        ``role_or_source`` is a HashiCorp database-role name. (The previous
        ``'supabase'`` special-case is removed; Supabase is no longer used.)
        """
        # Try HashiCorp for dynamic credentials
        if self.hashicorp.is_connected():
            creds = self.hashicorp.get_database_credentials(role_or_source)
            if creds:
                logger.info(f'✓ Got dynamic DB creds from HashiCorp for role {role_or_source}')
                return creds

        # Fallback to static config (POSTGRES_* / DB_* env)
        return {
            'host': os.getenv('POSTGRES_HOST', os.getenv('DB_HOST', '')),
            'port': os.getenv('POSTGRES_PORT', os.getenv('DB_PORT', '5432')),
            'user': os.getenv('POSTGRES_USER', os.getenv('DB_USER', '')),
            'password': os.getenv('POSTGRES_PASSWORD', os.getenv('DB_PASSWORD', '')),
            'database': os.getenv('POSTGRES_DB', os.getenv('DB_NAME', '')),
        }

    def set_secret(
        self,
        secret_name: str,
        secret_value: str,
        secret_path: str | None = None,
        backend: VaultBackend | None = None,
    ) -> bool:
        """Store a secret in HashiCorp Vault."""
        del backend  # Only HashiCorp remains.

        if self.hashicorp.is_connected():
            path = secret_path or f'secret/data/app/{secret_name}'
            return self.hashicorp.rotate_secret(path, {secret_name: secret_value})

        logger.error('✗ Cannot set secret - HashiCorp Vault not available')
        return False

    def rotate_secret(
        self,
        secret_name: str,
        secret_path: str | None = None,
    ) -> bool:
        """Rotate/refresh a secret in HashiCorp Vault."""
        if self.hashicorp.is_connected() and secret_path:
            return self.hashicorp.rotate_secret(secret_path, {})

        logger.warning(f'⚠ Cannot rotate secret {secret_name} - vault not available')
        return False

    def get_api_key(self, key_name: str = 'FASTAPI_API_KEY') -> str | None:
        """Get API key from vault."""
        return self.get_secret(key_name, secret_path=f'secret/data/app/api/{key_name}')

    def get_encryption_key(self, key_name: str = 'APP_ENC_KEY') -> str | None:
        """Get encryption key from vault."""
        return self.get_secret(key_name, secret_path=f'secret/data/app/crypto/{key_name}')

    def get_database_password(self) -> str | None:
        """Get database password from vault."""
        return self.get_secret('DB_PASSWORD', secret_path='secret/data/database/password')

    def health_check(self) -> dict[str, Any]:
        """Check health status of the HashiCorp Vault backend."""
        return {
            'hashicorp_vault': {
                'connected': self.hashicorp.is_connected(),
                'address': self.hashicorp.vault_addr if self.hashicorp else None,
            },
            'primary_backend': self.primary_backend.value,
            'local_fallback_enabled': self.enable_local_fallback,
        }

    def clear_caches(self) -> None:
        """Clear all secret caches."""
        self.hashicorp.clear_cache()
        logger.info('🗑️ All secret caches cleared')


# Global singleton
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the secrets manager singleton."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
