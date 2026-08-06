"""Supabase Vault client — DISABLED.

This project now uses PostgreSQL directly (see ``app/database.py``) and
HashiCorp Vault for secrets (see ``app/vault/hashicorp_vault.py``). Supabase is
no longer a dependency.

This module is retained as a **permanently-disabled stub** so that existing
import sites (``legacy_main._supabase_vault_health``, ``vault.__init__``,
``vault.secrets_manager`` and the test suite) keep importing cleanly during the
transition. Every instance reports ``is_ready = False`` and every accessor
returns ``None`` / a no-op, so the Supabase backend can never be selected as a
secrets source and never imports the third-party ``supabase`` package.

Safe to delete entirely once the remaining import sites in ``legacy_main.py``
are removed.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Public flag so callers (and tests) can assert the backend is disabled.
SUPABASE_VAULT_DISABLED = True


class SupabaseVaultClient:
    """Disabled stub preserving the historical Supabase vault interface.

    All accessors are inert: ``is_ready`` is always ``False`` and reads return
    ``None``. No network calls are made and the ``supabase`` package is never
    imported.
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        supabase_jwt_secret: str | None = None,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        # Keep attribute names stable for health-reporting callers.
        self.supabase_url: str | None = supabase_url
        self.supabase_key: str | None = supabase_key
        self.supabase_jwt_secret: str | None = supabase_jwt_secret
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache: dict[str, tuple[Any, Any]] = {}
        self.is_ready = False
        logger.debug('SupabaseVaultClient is disabled (PostgreSQL + HashiCorp Vault in use).')

    def get_secret(self, vault_key: str) -> str | None:
        """Always returns None — Supabase backend is disabled."""
        return None

    def store_secret(self, vault_key: str, secret_value: str) -> bool:
        """Always returns False — Supabase backend is disabled."""
        logger.warning('store_secret(%r) ignored: Supabase Vault is disabled.', vault_key)
        return False

    def get_database_config(self) -> dict[str, str] | None:
        """Always returns None — use POSTGRES_* env / HashiCorp DB credentials."""
        return None

    def get_jwt_secret(self) -> str | None:
        """Always returns None — Supabase JWT secret is no longer used."""
        return None

    def clear_cache(self) -> None:
        """No-op — there is no cache to clear."""
        self.cache.clear()


def get_supabase_vault_client() -> SupabaseVaultClient:
    """Return a disabled singleton SupabaseVaultClient."""
    return SupabaseVaultClient()
