# pyright: reportUnusedFunction=false
"""
Platform client modules — real API integrations for social networks.

This package contains production-grade clients for:
- Twitter/X API v2
- Facebook Graph API
- Instagram Graph API
- LinkedIn Official API
- TikTok OAuth & Upload API

Each client handles:
- OAuth token management & refresh
- Rate limiting & backoff
- Error handling & retries
- Request/response serialization
"""

from . import facebook_client, instagram_client, linkedin_client, tiktok_client, twitter_client

__all__ = [
    'twitter_client',
    'facebook_client',
    'instagram_client',
    'linkedin_client',
    'tiktok_client',
]
