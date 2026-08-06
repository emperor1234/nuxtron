"""
HashiCorp Vault integration for secrets management.
Provides secure access to sensitive data with automatic rotation and caching.
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import hvac

logger = logging.getLogger(__name__)


class HashiCorpVaultClient:
    """
    Client for HashiCorp Vault integration.
    Handles authentication, secret retrieval, and caching.
    """

    def __init__(
        self,
        vault_addr: str | None = None,
        vault_token: str | None = None,
        vault_role: str | None = None,
        vault_jwt: str | None = None,
        cache_ttl_seconds: int = 3600,
    ):
        self.vault_addr = vault_addr or os.getenv('VAULT_ADDR', 'http://localhost:8200')
        self.vault_token = vault_token or os.getenv('VAULT_TOKEN')
        self.vault_role = vault_role or os.getenv('VAULT_ROLE')
        self.vault_jwt = vault_jwt or os.getenv('VAULT_JWT')
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache: dict[str, tuple[Any, datetime]] = {}
        self.client: hvac.Client | None = None
        self._auth_method = self._detect_auth_method()

    def _detect_auth_method(self) -> str:
        """Detect which authentication method to use."""
        if self.vault_token:
            return 'token'
        elif self.vault_role and self.vault_jwt:
            return 'jwt'
        elif self.vault_role:
            return 'kubernetes'
        else:
            return 'token'

    def connect(self) -> bool:
        """
        Establish connection and authenticate with Vault.
        Returns True if successful, False otherwise.
        """
        try:
            self.client = hvac.Client(url=self.vault_addr)

            if self._auth_method == 'token' and self.vault_token:
                self.client.token = self.vault_token
                self.client.is_authenticated()
                logger.info('✓ Connected to HashiCorp Vault (token auth)')
                return True

            elif self._auth_method == 'jwt' and self.vault_role and self.vault_jwt:
                self.client.auth.jwt.jwt_login(
                    role=self.vault_role,
                    jwt=self.vault_jwt,
                )
                logger.info('✓ Connected to HashiCorp Vault (JWT auth)')
                return True

            elif self._auth_method == 'kubernetes' and self.vault_role:
                with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as f:
                    jwt_token = f.read()
                self.client.auth.kubernetes.kubernetes_login(
                    role=self.vault_role,
                    jwt=jwt_token,
                )
                logger.info('✓ Connected to HashiCorp Vault (Kubernetes auth)')
                return True

            logger.warning('⚠ No valid Vault auth method configured')
            return False

        except Exception as e:
            logger.error(f'✗ Vault connection failed: {e}')
            return False

    def get_secret(self, secret_path: str, key: str | None = None) -> Any | None:
        """
        Retrieve a secret from Vault with caching.
        
        Args:
            secret_path: Path to secret in Vault (e.g., 'secret/data/myapp/database')
            key: Optional specific key within the secret object
            
        Returns:
            Secret value or None if not found
        """
        if not self.client:
            logger.error('✗ Vault client not connected')
            return None

        # Check cache first
        if secret_path in self.cache:
            value, timestamp = self.cache[secret_path]
            if datetime.now(UTC) - timestamp < timedelta(seconds=self.cache_ttl_seconds):
                logger.debug(f'📦 Cache hit for {secret_path}')
                return value[key] if key else value

        try:
            response = self.client.secrets.kv.read_secret_version(path=secret_path)
            secret_data = response['data']['data']

            # Cache the entire secret
            self.cache[secret_path] = (secret_data, datetime.now(UTC))

            result = secret_data.get(key) if key else secret_data
            logger.debug(f'✓ Retrieved secret from {secret_path}')
            return result

        except Exception as e:
            logger.error(f'✗ Failed to retrieve secret {secret_path}: {e}')
            return None

    def get_database_credentials(
        self,
        role_name: str,
    ) -> dict[str, str] | None:
        """
        Retrieve dynamically generated database credentials.
        
        Args:
            role_name: Vault role name for database
            
        Returns:
            Dict with 'username' and 'password' or None
        """
        if not self.client:
            return None

        try:
            response = self.client.secrets.database.generate_credentials(
                name=role_name
            )
            creds = response['data']
            logger.info(f'✓ Generated temp DB creds for role {role_name}')
            return {
                'username': creds.get('username'),
                'password': creds.get('password'),
            }
        except Exception as e:
            logger.error(f'✗ Failed to generate DB credentials: {e}')
            return None

    def rotate_secret(self, secret_path: str, new_value: dict[str, Any]) -> bool:
        """
        Rotate a secret by updating its value.
        
        Args:
            secret_path: Path to secret in Vault
            new_value: New secret data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        try:
            self.client.secrets.kv.create_or_update_secret(
                path=secret_path,
                secret_data=new_value,
            )
            # Clear from cache to force refresh
            self.cache.pop(secret_path, None)
            logger.info(f'✓ Rotated secret at {secret_path}')
            return True
        except Exception as e:
            logger.error(f'✗ Failed to rotate secret: {e}')
            return False

    def clear_cache(self) -> None:
        """Clear the secret cache."""
        self.cache.clear()
        logger.debug('🗑️ Vault cache cleared')

    def is_connected(self) -> bool:
        """Check if Vault connection is active."""
        if not self.client:
            return False
        try:
            return self.client.is_authenticated()
        except Exception:
            return False


# Singleton instance
_vault_instance: HashiCorpVaultClient | None = None


def get_vault_client() -> HashiCorpVaultClient:
    """Get or create the Vault client singleton."""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = HashiCorpVaultClient()
        if not _vault_instance.connect():
            logger.warning('⚠ Vault not available, fallback to env vars')
    return _vault_instance
