"""
Vault integration initialization and configuration for FastAPI.
"""

import logging
import os

from .vault import SecretsManager, get_secrets_manager

logger = logging.getLogger(__name__)


def initialize_secrets_manager() -> SecretsManager:
    """
    Initialize the secrets manager on application startup.
    Performs health checks and logs configuration.
    """
    manager = get_secrets_manager()

    # Log health status
    health = manager.health_check()
    logger.info('═' * 60)
    logger.info('🔐 VAULT INITIALIZATION REPORT')
    logger.info('═' * 60)

    if health['hashicorp_vault']['connected']:
        logger.info(f"✓ HashiCorp Vault: {health['hashicorp_vault']['address']}")
    else:
        logger.warning('⚠ HashiCorp Vault: Not connected')

    logger.info(f"→ Primary Backend: {health['primary_backend']}")
    logger.info(f"→ Local Fallback: {'Enabled' if health['local_fallback_enabled'] else 'Disabled'}")
    logger.info('═' * 60)

    return manager


def load_secrets_from_vault() -> dict[str, str | None]:
    """
    Load critical secrets from vault on startup.
    Returns a dict of secret_name -> secret_value.
    """
    manager = get_secrets_manager()

    critical_secrets = {
        'FASTAPI_API_KEY': manager.get_api_key(),
        'APP_ENC_KEY': manager.get_encryption_key(),
        'PASSWORD_PEPPER': manager.get_secret(
            'PASSWORD_PEPPER',
            secret_path=os.getenv('VAULT_PASSWORD_PEPPER_PATH', 'nuxtron/security'),
            secret_field=os.getenv('VAULT_PASSWORD_PEPPER_FIELD', 'password_pepper'),
        ),
        'DB_PASSWORD': manager.get_database_password(),
        'JWT_SECRET': manager.get_secret('JWT_SECRET'),
        'SAML_PRIVATE_KEY': manager.get_secret('SAML_PRIVATE_KEY'),
        'NIST_MLKEM_PUBLIC_KEY': manager.get_secret(
            'NIST_MLKEM_PUBLIC_KEY',
            secret_path=os.getenv('VAULT_NIST_PQC_PATH', 'nuxtron/pqc'),
            secret_field=os.getenv('VAULT_NIST_MLKEM_PUBLIC_KEY_FIELD', 'mlkem_public_key'),
        ),
        'NIST_MLKEM_PRIVATE_KEY': manager.get_secret(
            'NIST_MLKEM_PRIVATE_KEY',
            secret_path=os.getenv('VAULT_NIST_PQC_PATH', 'nuxtron/pqc'),
            secret_field=os.getenv('VAULT_NIST_MLKEM_PRIVATE_KEY_FIELD', 'mlkem_private_key'),
        ),
    }

    logger.info('📦 Loaded secrets from vault:')
    for name, value in critical_secrets.items():
        status = '✓' if value else '✗'
        logger.info(f'  {status} {name}')
        if value:
            os.environ[name] = value

    return critical_secrets


def get_vault_secret(
    secret_name: str,
    secret_path: str | None = None,
    secret_field: str | None = None,
    required: bool = True,
) -> str | None:
    """
    Get a secret from vault with optional requirement check.
    
    Args:
        secret_name: Name of the secret
        secret_path: Optional vault path override
        required: Whether secret is required (raises if missing)
        
    Returns:
        Secret value or None
        
    Raises:
        RuntimeError: If required=True and secret not found
    """
    manager = get_secrets_manager()
    secret = manager.get_secret(secret_name, secret_path=secret_path, secret_field=secret_field)

    if not secret and required:
        raise RuntimeError(f'Required secret not found: {secret_name}')

    return secret


def configure_vault_logging(verbose: bool = False) -> None:
    """Configure logging for vault operations."""
    vault_logger = logging.getLogger('vault')

    if verbose:
        vault_logger.setLevel(logging.DEBUG)
    else:
        vault_logger.setLevel(logging.INFO)

    logger.info(f'Vault logging: {"VERBOSE (DEBUG)" if verbose else "NORMAL (INFO)"}')


# Vault health check endpoint data
def get_vault_health() -> dict:
    """Get vault health status for /healthz endpoint."""
    manager = get_secrets_manager()
    health = manager.health_check()

    return {
        'vaults': {
            'hashicorp': health['hashicorp_vault'],
        },
        'primary': health['primary_backend'],
        'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
    }
