"""Vault integration package — HashiCorp Vault secrets.

Supabase Vault has been removed from the project (PostgreSQL is used directly).
``SupabaseVaultClient`` / ``get_supabase_vault_client`` are re-exported here as
permanently-disabled stubs purely to preserve import compatibility for legacy
call sites; they never contact Supabase.
"""

from .hashicorp_vault import HashiCorpVaultClient, get_vault_client
from .secrets_manager import (
    SecretsManager,
    VaultBackend,
    get_secrets_manager,
)
from .supabase_vault import SupabaseVaultClient, get_supabase_vault_client

__all__ = [
    'HashiCorpVaultClient',
    'get_vault_client',
    'SupabaseVaultClient',
    'get_supabase_vault_client',
    'SecretsManager',
    'VaultBackend',
    'get_secrets_manager',
]
