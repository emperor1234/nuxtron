# pyright: reportUnusedFunction=false
"""
LinkedIn Official API Client — Production-grade integration.

Implements:
- Post creation (personal/organization)
- Article publishing
- Post scheduling
- DM sending
- Analytics
- Comment replies

Third-Party: LinkedIn Official API (requires Business Admin approval)

Rate Limits:
- Create content: 1 request per 200ms (300/min)
- Share visibility: 1 per second (60/min)
- Analytics: 300 per minute
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 1.0
MAX_BACKOFF_SEC = 60.0


class LinkedInAPIError(Exception):
    """Custom exception for LinkedIn API errors."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"LinkedIn API {status_code}: {detail}")


class PostRequest(BaseModel):
    """Request to create a LinkedIn post."""

    text: str = Field(..., max_length=3000)
    visibility: str = Field(default="PUBLIC", pattern=r"^(PUBLIC|CONNECTIONS|LOGGED_IN)$")


class ArticlePublishRequest(BaseModel):
    """Request to publish a LinkedIn article."""

    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=100000)
    summary: str | None = Field(None, max_length=500)
    canonical_url: str | None = None


class PostScheduleRequest(BaseModel):
    """Request to schedule a LinkedIn post."""

    text: str = Field(..., max_length=3000)
    scheduled_time: datetime


class MessageRequest(BaseModel):
    """Request to send LinkedIn message."""

    recipient_urn: str = Field(..., description="LinkedIn URN of recipient")
    subject: str | None = Field(None, max_length=200)
    message_text: str = Field(..., max_length=10000)


class LinkedInMetrics(BaseModel):
    """LinkedIn post metrics."""

    post_id: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    impressions: int = 0
    clicks: int = 0


class LinkedInGraphClient:
    """Production LinkedIn Official API client."""

    def __init__(self, access_token: str, actor_urn: str):
        """
        Initialize LinkedIn client.

        Args:
            access_token: OAuth2 access token
            actor_urn: LinkedIn actor URN (urn:li:person:12345 or urn:li:organization:67890)
        """
        self.access_token = access_token
        self.actor_urn = actor_urn

        # Rate limit tracking
        self._rate_buckets: dict[str, list[float]] = {}
        self._session: httpx.AsyncClient | None = None

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()

    async def _ensure_session(self) -> httpx.AsyncClient:
        """Lazily create async HTTP session."""
        if self._session is None:
            self._session = httpx.AsyncClient(timeout=30.0)
        return self._session

    def _check_rate_limit(self, bucket_key: str, limit: int, window_sec: int = 60) -> None:
        """Check rate limit."""
        now = time.time()
        window_start = now - window_sec

        if bucket_key not in self._rate_buckets:
            self._rate_buckets[bucket_key] = []

        self._rate_buckets[bucket_key] = [
            t for t in self._rate_buckets[bucket_key] if t >= window_start
        ]

        if len(self._rate_buckets[bucket_key]) >= limit:
            retry_after = int(
                window_sec - (now - self._rate_buckets[bucket_key][0]) + 1
            )
            raise LinkedInAPIError(
                429,
                f"Rate limit exceeded. Retry after {retry_after}s",
            )

        self._rate_buckets[bucket_key].append(now)

    @retry(
        retry=retry_if_exception_type(
            (LinkedInAPIError, httpx.TimeoutException)
        ),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(
            multiplier=1, min=INITIAL_BACKOFF_SEC, max=MAX_BACKOFF_SEC
        ),
        after=after_log(logger, logging.WARNING),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to LinkedIn API."""
        session = await self._ensure_session()

        url = f"{LINKEDIN_API_BASE}{endpoint}"

        if headers is None:
            headers = {}

        headers["Authorization"] = f"Bearer {self.access_token}"
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"

        try:
            response = await session.request(
                method,
                url,
                json=json_payload,
                params=params,
                headers=headers,
            )

            if response.status_code == 429:
                raise LinkedInAPIError(429, "Rate limited")

            if response.status_code >= 500:
                raise LinkedInAPIError(response.status_code, "Server error")

            response.raise_for_status()

            return response.json() if response.content else {"success": True}

        except httpx.TimeoutException as exc:
            raise LinkedInAPIError(504, f"Timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LinkedInAPIError(500, f"HTTP error: {exc}") from exc

    async def create_post(self, request: PostRequest) -> dict[str, Any]:
        """Create a LinkedIn post."""
        self._check_rate_limit("posts:create", 300, window_sec=60)

        payload = {
            "author": self.actor_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": request.text,
                    },
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": request.visibility,
            },
        }

        response = await self._request(
            "POST",
            "/ugcPosts",
            json_payload=payload,
        )

        return response

    async def publish_article(self, request: ArticlePublishRequest) -> dict[str, Any]:
        """Publish a LinkedIn article."""
        self._check_rate_limit("articles:publish", 300, window_sec=60)

        payload = {
            "author": self.actor_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": request.summary or request.title,
                    },
                    "shareMediaCategory": "ARTICLE",
                    "media": [
                        {
                            "status": "READY",
                            "media": request.canonical_url or "",
                            "title": {
                                "text": request.title,
                            },
                            "description": {
                                "text": request.summary or "",
                            },
                        }
                    ],
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
            },
        }

        response = await self._request(
            "POST",
            "/ugcPosts",
            json_payload=payload,
        )

        return response

    async def schedule_post(self, request: PostScheduleRequest) -> dict[str, Any]:
        """Schedule a LinkedIn post."""
        self._check_rate_limit("posts:schedule", 300, window_sec=60)

        if request.scheduled_time <= datetime.now(UTC):
            raise LinkedInAPIError(
                400, "Scheduled time must be in future"
            )

        payload = {
            "author": self.actor_urn,
            "lifecycleState": "DRAFT",
            "firstPublishedAt": int(request.scheduled_time.timestamp() * 1000),
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": request.text,
                    },
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
            },
        }

        response = await self._request(
            "POST",
            "/ugcPosts",
            json_payload=payload,
        )

        return response

    async def send_message(self, request: MessageRequest) -> dict[str, Any]:
        """Send a LinkedIn message."""
        self._check_rate_limit("messages:send", 300, window_sec=60)

        payload = {
            "sender": self.actor_urn,
            "recipients": [request.recipient_urn],
            "subject": request.subject or "Message",
            "body": request.message_text,
        }

        response = await self._request(
            "POST",
            "/messaging/conversations",
            json_payload=payload,
        )

        return response

    async def get_post_metrics(self, post_id: str) -> LinkedInMetrics:
        """Get metrics for a LinkedIn post."""
        self._check_rate_limit("analytics", 300, window_sec=60)

        response = await self._request(
            "GET",
            f"/ugcPosts/{post_id}?q=author&author={self.actor_urn}",
        )

        # LinkedIn's analytics endpoint structure
        metrics_data = response.get("elements", [{}])[0].get("metrics", {})

        return LinkedInMetrics(
            post_id=post_id,
            likes=metrics_data.get("likeCount", 0),
            comments=metrics_data.get("commentCount", 0),
            shares=metrics_data.get("shareCount", 0),
            impressions=metrics_data.get("impressionCount", 0),
            clicks=metrics_data.get("clickCount", 0),
        )

    async def delete_post(self, post_id: str) -> dict[str, Any]:
        """Delete a LinkedIn post."""
        self._check_rate_limit("posts:delete", 300, window_sec=60)

        response = await self._request(
            "DELETE",
            f"/ugcPosts/{post_id}",
        )

        return response

    async def reply_to_comment(
        self, comment_id: str, reply_text: str
    ) -> dict[str, Any]:
        """Reply to a comment on a post."""
        self._check_rate_limit("comments:reply", 300, window_sec=60)

        payload = {
            "actor": self.actor_urn,
            "object": comment_id,
            "message": {
                "text": reply_text,
            },
        }

        response = await self._request(
            "POST",
            "/comments",
            json_payload=payload,
        )

        return response
