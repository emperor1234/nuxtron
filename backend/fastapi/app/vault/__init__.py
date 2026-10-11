"""HashiCorp Vault integration package."""

from .hashicorp_vault import HashiCorpVaultClient, get_vault_client
from .secrets_manager import (
    SecretsManager,
    VaultBackend,
    get_secrets_manager,
)

__all__ = [
    'HashiCorpVaultClient',
    'get_vault_client',
    'SecretsManager',
    'VaultBackend',
    'get_secrets_manager',
]
