"""
Unified vendor integration manager for all third-party services.
This is the central hub for configuring and managing all API integrations.
Production-grade with encryption, rate limiting, error handling.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import httpx
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class VendorType(StrEnum):
    """Supported vendor categories"""
    SOCIAL_MEDIA = "social_media"
    AI_SERVICE = "ai_service"
    VECTOR_DB = "vector_db"
    SEARCH_ENGINE = "search_engine"
    ANALYTICS = "analytics"
    CRM = "crm"
    PAYMENT = "payment"
    NOTIFICATION = "notification"
    STORAGE = "storage"
    MONITORING = "monitoring"


class PlatformType(StrEnum):
    """Social media platforms"""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    REDDIT = "reddit"
    SNAPCHAT = "snapchat"
    YOUTUBE = "youtube"
    THREADS = "threads"
    BLUESKY = "bluesky"


@dataclass
class VendorCredentials:
    """Encrypted vendor credentials storage"""
    vendor_type: VendorType
    platform: str | None
    api_key: str
    api_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    endpoint_url: str | None = None
    additional_config: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding sensitive data"""
        return {
            'vendor_type': self.vendor_type.value,
            'platform': self.platform,
            'api_key': '***REDACTED***',
            'endpoint_url': self.endpoint_url,
        }


class CredentialVault:
    """Secure credential storage with encryption"""
    
    def __init__(self):
        # Use environment-based encryption key (rotate in production)
        encryption_key = os.getenv('CREDENTIAL_ENCRYPTION_KEY', '')
        if not encryption_key:
            # Generate a default key for development (MUST be set in production)
            encryption_key = Fernet.generate_key().decode()
            logger.warning("Using default encryption key. Set CREDENTIAL_ENCRYPTION_KEY in production!")
        
        self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        self._credentials: dict[str, dict[str, Any]] = {}
    
    def store(self, vendor_id: str, credentials: VendorCredentials) -> None:
        """Store encrypted credentials"""
        encrypted_api_key = self.cipher.encrypt(credentials.api_key.encode()).decode()
        encrypted_secret = None
        if credentials.api_secret:
            encrypted_secret = self.cipher.encrypt(credentials.api_secret.encode()).decode()
        
        self._credentials[vendor_id] = {
            'vendor_type': credentials.vendor_type.value,
            'platform': credentials.platform,
            'api_key': encrypted_api_key,
            'api_secret': encrypted_secret,
            'access_token': credentials.access_token,
            'refresh_token': credentials.refresh_token,
            'expires_at': credentials.expires_at.isoformat() if credentials.expires_at else None,
            'endpoint_url': credentials.endpoint_url,
            'additional_config': credentials.additional_config,
        }
    
    def retrieve(self, vendor_id: str) -> VendorCredentials | None:
        """Retrieve and decrypt credentials"""
        if vendor_id not in self._credentials:
            return None
        
        cred_data = self._credentials[vendor_id]
        try:
            api_key = self.cipher.decrypt(cred_data['api_key'].encode()).decode()
            api_secret = None
            if cred_data.get('api_secret'):
                api_secret = self.cipher.decrypt(cred_data['api_secret'].encode()).decode()
            
            expires_at = None
            if cred_data.get('expires_at'):
                expires_at = datetime.fromisoformat(cred_data['expires_at'])
            
            return VendorCredentials(
                vendor_type=VendorType(cred_data['vendor_type']),
                platform=cred_data.get('platform'),
                api_key=api_key,
                api_secret=api_secret,
                access_token=cred_data.get('access_token'),
                refresh_token=cred_data.get('refresh_token'),
                expires_at=expires_at,
                endpoint_url=cred_data.get('endpoint_url'),
                additional_config=cred_data.get('additional_config'),
            )
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for {vendor_id}: {e}")
            return None

    def delete(self, vendor_id: str) -> bool:
        """Delete credentials for a vendor. Returns True when credentials existed."""
        return self._credentials.pop(vendor_id, None) is not None

    def has(self, vendor_id: str) -> bool:
        """Check whether credentials exist for a vendor id."""
        return vendor_id in self._credentials


class RateLimiter:
    """Rate limiting for API calls"""
    
    def __init__(self):
        self._request_times: dict[str, list[datetime]] = {}
        self._limits: dict[str, dict[str, int]] = {}
    
    def set_limit(self, vendor_id: str, requests_per_minute: int, requests_per_hour: int | None = None) -> None:
        """Set rate limits"""
        self._limits[vendor_id] = {
            'per_minute': requests_per_minute,
            'per_hour': requests_per_hour or (requests_per_minute * 60),
        }
    
    def is_allowed(self, vendor_id: str) -> bool:
        """Check if request is allowed"""
        if vendor_id not in self._limits:
            return True
        
        now = datetime.utcnow()
        if vendor_id not in self._request_times:
            self._request_times[vendor_id] = []
        
        # Clean up old requests
        one_hour_ago = now - timedelta(hours=1)
        self._request_times[vendor_id] = [t for t in self._request_times[vendor_id] if t > one_hour_ago]
        
        # Check minute limit
        one_minute_ago = now - timedelta(minutes=1)
        minute_requests = len([t for t in self._request_times[vendor_id] if t > one_minute_ago])
        if minute_requests >= self._limits[vendor_id]['per_minute']:
            return False
        
        # Check hour limit
        hour_requests = len(self._request_times[vendor_id])
        if hour_requests >= self._limits[vendor_id]['per_hour']:
            return False
        
        return True
    
    def record_request(self, vendor_id: str) -> None:
        """Record a request"""
        if vendor_id not in self._request_times:
            self._request_times[vendor_id] = []
        self._request_times[vendor_id].append(datetime.utcnow())


class VendorManager:
    """Central vendor integration manager"""
    
    def __init__(self):
        self.vault = CredentialVault()  # type: ignore[no-untyped-call]
        self.rate_limiter = RateLimiter()  # type: ignore[no-untyped-call]
        self._vendors: dict[str, dict[str, Any]] = {}
        self._initialize_vendors()
    
    def _initialize_vendors(self) -> None:
        """Initialize vendor configurations from environment"""
        # Social Media Platforms
        self._register_vendor(
            'meta_graph_api',
            VendorType.SOCIAL_MEDIA,
            'https://graph.instagram.com/v18.0',
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
        self._register_vendor(
            'linkedin_api',
            VendorType.SOCIAL_MEDIA,
            'https://api.linkedin.com/v2',
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
        self._register_vendor(
            'twitter_api',
            VendorType.SOCIAL_MEDIA,
            'https://api.twitter.com/2',
            rate_limit_per_min=300,
            rate_limit_per_hour=15000,
        )
        self._register_vendor(
            'tiktok_api',
            VendorType.SOCIAL_MEDIA,
            'https://open.tiktokapis.com/v1',
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
        self._register_vendor(
            'reddit_api',
            VendorType.SOCIAL_MEDIA,
            'https://oauth.reddit.com',
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
        self._register_vendor(
            'youtube_api',
            VendorType.SOCIAL_MEDIA,
            'https://www.googleapis.com/youtube/v3',
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
        
        # AI Services
        self._register_vendor(
            'openai_api',
            VendorType.AI_SERVICE,
            'https://api.openai.com/v1',
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
        self._register_vendor(
            'anthropic_api',
            VendorType.AI_SERVICE,
            'https://api.anthropic.com',
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
        
        # Vector Databases
        self._register_vendor(
            'pinecone_api',
            VendorType.VECTOR_DB,
            os.getenv('PINECONE_INDEX_ENDPOINT', 'https://index.pinecone.io'),
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
        
        # Search
        self._register_vendor(
            'elasticsearch',
            VendorType.SEARCH_ENGINE,
            os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200'),
            rate_limit_per_min=1000,
            rate_limit_per_hour=60000,
        )
        
        # Analytics
        self._register_vendor(
            'google_analytics',
            VendorType.ANALYTICS,
            'https://analytics.googleapis.com',
            rate_limit_per_min=600,
            rate_limit_per_hour=36000,
        )

        # CRM
        self._register_vendor(
            'hubspot_api',
            VendorType.CRM,
            'https://api.hubapi.com',
            rate_limit_per_min=100,
            rate_limit_per_hour=4000,
        )

        # Advertising
        self._register_vendor(
            'google_ads_api',
            VendorType.ANALYTICS,
            'https://googleads.googleapis.com',
            rate_limit_per_min=120,
            rate_limit_per_hour=7200,
        )
        self._register_vendor(
            'microsoft_ads_api',
            VendorType.ANALYTICS,
            'https://api.ads.microsoft.com',
            rate_limit_per_min=120,
            rate_limit_per_hour=7200,
        )
        self._register_vendor(
            'amazon_ads_api',
            VendorType.ANALYTICS,
            'https://advertising-api.amazon.com',
            rate_limit_per_min=120,
            rate_limit_per_hour=7200,
        )
        self._register_vendor(
            'apple_search_ads_api',
            VendorType.ANALYTICS,
            'https://api.searchads.apple.com',
            rate_limit_per_min=120,
            rate_limit_per_hour=7200,
        )
        self._register_vendor(
            'youtube_ads_api',
            VendorType.ANALYTICS,
            'https://googleads.googleapis.com',
            rate_limit_per_min=120,
            rate_limit_per_hour=7200,
        )
        
        # Payment Processing
        self._register_vendor(
            'stripe_api',
            VendorType.PAYMENT,
            'https://api.stripe.com',
            rate_limit_per_min=100,
            rate_limit_per_hour=6000,
        )
        
        # Notifications
        self._register_vendor(
            'firebase_messaging',
            VendorType.NOTIFICATION,
            'https://fcm.googleapis.com',
            rate_limit_per_min=1000,
            rate_limit_per_hour=60000,
        )
        
        # Monitoring
        self._register_vendor(
            'datadog_api',
            VendorType.MONITORING,
            'https://api.datadoghq.com',
            rate_limit_per_min=60,
            rate_limit_per_hour=3600,
        )
    
    def _register_vendor(
        self,
        vendor_id: str,
        vendor_type: VendorType,
        endpoint_url: str,
        rate_limit_per_min: int,
        rate_limit_per_hour: int,
    ) -> None:
        """Register a vendor"""
        self._vendors[vendor_id] = {
            'vendor_type': vendor_type,
            'endpoint_url': endpoint_url,
            'registered_at': datetime.utcnow(),
        }
        self.rate_limiter.set_limit(vendor_id, rate_limit_per_min, rate_limit_per_hour)
        logger.info(f"Registered vendor: {vendor_id}")
    
    def store_credentials(self, vendor_id: str, credentials: VendorCredentials) -> None:
        """Store vendor credentials"""
        if vendor_id not in self._vendors:
            raise ValueError(f"Unknown vendor: {vendor_id}")
        
        self.vault.store(vendor_id, credentials)
        logger.info(f"Stored credentials for {vendor_id}")
    
    def get_credentials(self, vendor_id: str) -> VendorCredentials | None:
        """Retrieve vendor credentials"""
        return self.vault.retrieve(vendor_id)

    def revoke_credentials(self, vendor_id: str) -> bool:
        """Revoke credentials for a vendor id. Returns True if credentials were removed."""
        if vendor_id not in self._vendors:
            raise ValueError(f"Unknown vendor: {vendor_id}")
        removed = self.vault.delete(vendor_id)
        if removed:
            logger.info(f"Revoked credentials for {vendor_id}")
        return removed

    def has_credentials(self, vendor_id: str) -> bool:
        """Check whether credentials are configured for a known vendor id."""
        if vendor_id not in self._vendors:
            return False
        return self.vault.has(vendor_id)
    
    async def make_request(
        self,
        vendor_id: str,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make authenticated request to vendor API with rate limiting"""
        
        if vendor_id not in self._vendors:
            raise ValueError(f"Unknown vendor: {vendor_id}")
        
        if not self.rate_limiter.is_allowed(vendor_id):
            raise RuntimeError(f"Rate limit exceeded for {vendor_id}")
        
        credentials = self.get_credentials(vendor_id)
        if not credentials:
            raise ValueError(f"No credentials configured for {vendor_id}")
        
        vendor_config = self._vendors[vendor_id]
        url = f"{vendor_config['endpoint_url']}{endpoint}"
        
        # Prepare headers with authentication
        request_headers = headers or {}
        request_headers['User-Agent'] = 'Nuxtron/1.0 (Production)'
        
        # Add authentication based on vendor type
        self._add_auth_headers(vendor_id, credentials, request_headers)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json_data,
                    params=params,
                )
                
                self.rate_limiter.record_request(vendor_id)
                
                if response.status_code >= 400:
                    logger.error(
                        f"Vendor API error: {vendor_id} - {response.status_code} - {response.text}"
                    )
                    raise RuntimeError(
                        f"Vendor API error: {response.status_code} - {response.text[:500]}"
                    )
                
                return response.json()
        
        except httpx.TimeoutException:
            logger.error(f"Timeout calling {vendor_id}")
            raise RuntimeError(f"Request timeout: {vendor_id}")
        except Exception as e:
            logger.error(f"Error calling {vendor_id}: {e}")
            raise
    
    def _add_auth_headers(
        self,
        vendor_id: str,
        credentials: VendorCredentials,
        headers: dict[str, str],
    ) -> None:
        """Add authentication headers based on vendor type"""
        
        if credentials.vendor_type == VendorType.SOCIAL_MEDIA:
            if vendor_id == 'twitter_api':
                headers['Authorization'] = f"Bearer {credentials.access_token}"
            else:
                headers['Authorization'] = f"Bearer {credentials.access_token}"
        
        elif credentials.vendor_type == VendorType.AI_SERVICE:
            if 'openai' in vendor_id:
                headers['Authorization'] = f"Bearer {credentials.api_key}"
                headers['OpenAI-Organization'] = credentials.additional_config.get(
                    'organization_id', ''
                ) if credentials.additional_config else ''
            elif 'anthropic' in vendor_id:
                headers['x-api-key'] = credentials.api_key
        
        elif credentials.vendor_type == VendorType.PAYMENT:
            headers['Authorization'] = f"Bearer {credentials.api_key}"
        
        elif credentials.vendor_type == VendorType.ANALYTICS:
            headers['Authorization'] = f"Bearer {credentials.access_token}"
        
        else:
            # Default: API Key in header
            headers['Authorization'] = f"Bearer {credentials.api_key}"


# Global vendor manager instance
_vendor_manager: VendorManager | None = None


def get_vendor_manager() -> VendorManager:
    """Get or create vendor manager instance"""
    global _vendor_manager
    if _vendor_manager is None:
        _vendor_manager = VendorManager()  # type: ignore[no-untyped-call]
    return _vendor_manager
