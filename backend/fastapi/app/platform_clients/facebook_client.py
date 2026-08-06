# pyright: reportUnusedFunction=false
"""
Facebook Graph API Client — Production-grade integration.

Implements:
- Page post creation & scheduling
- Message sending (Messenger)
- Insights & metrics
- Comment management & replies
- Feed fetching

Third-Party: Facebook Graph API v18+

Rate Limits:
- Standard: 200 calls per hour per user
- Page posts: 600 per hour
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

FACEBOOK_API_BASE = "https://graph.facebook.com/v18.0"
MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 1.0
MAX_BACKOFF_SEC = 60.0


class FacebookAPIError(Exception):
    """Custom exception for Facebook API errors."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Facebook API {status_code}: {detail}")


class PagePostCreateRequest(BaseModel):
    """Request to create a page post."""

    message: str = Field(..., max_length=5000)
    link: str | None = Field(None, description="Link to share")
    picture: str | None = Field(None, description="Image URL")
    type: str = Field(default="FEED", pattern=r"^(FEED|PHOTO|VIDEO)$")


class PagePostScheduleRequest(BaseModel):
    """Request to schedule a page post."""

    message: str = Field(..., max_length=5000)
    scheduled_publish_time: datetime
    link: str | None = None
    picture: str | None = None


class MessengerMessageRequest(BaseModel):
    """Request to send Messenger message."""

    recipient_id: str
    message_text: str = Field(..., max_length=2000)


class FacebookInsights(BaseModel):
    """Facebook post insights."""

    post_id: str
    page_reach: int = 0
    page_impressions: int = 0
    engaged_users: int = 0
    engagement: int = 0
    reactions: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0


class FacebookGraphClient:
    """Production Facebook Graph API client."""

    def __init__(self, access_token: str, page_id: str):
        """
        Initialize Facebook client.

        Args:
            access_token: Facebook Graph API access token
            page_id: Facebook page ID
        """
        self.access_token = access_token
        self.page_id = page_id

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

    def _check_rate_limit(self, bucket_key: str, limit: int) -> None:
        """Check rate limit (calls per hour)."""
        now = time.time()
        window_start = now - 3600  # 1-hour window

        if bucket_key not in self._rate_buckets:
            self._rate_buckets[bucket_key] = []

        self._rate_buckets[bucket_key] = [
            t for t in self._rate_buckets[bucket_key] if t >= window_start
        ]

        if len(self._rate_buckets[bucket_key]) >= limit:
            retry_after = int(
                3600 - (now - self._rate_buckets[bucket_key][0]) + 1
            )
            raise FacebookAPIError(
                429,
                f"Rate limit exceeded. Retry after {retry_after}s",
            )

        self._rate_buckets[bucket_key].append(now)

    @retry(
        retry=retry_if_exception_type(
            (FacebookAPIError, httpx.TimeoutException)
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
    ) -> dict[str, Any]:
        """Make authenticated request to Facebook Graph API."""
        session = await self._ensure_session()

        if params is None:
            params = {}
        params["access_token"] = self.access_token

        url = f"{FACEBOOK_API_BASE}{endpoint}"

        try:
            response = await session.request(
                method,
                url,
                json=json_payload,
                params=params,
            )

            if response.status_code == 429:
                raise FacebookAPIError(429, "Rate limited")

            if response.status_code >= 500:
                raise FacebookAPIError(response.status_code, "Server error")

            response.raise_for_status()

            return response.json() if response.content else {}

        except httpx.TimeoutException as exc:
            raise FacebookAPIError(504, f"Timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise FacebookAPIError(500, f"HTTP error: {exc}") from exc

    async def create_page_post(self, request: PagePostCreateRequest) -> dict[str, Any]:
        """Create a page post."""
        self._check_rate_limit("page_posts", 600)

        payload = {
            "message": request.message,
        }

        if request.link:
            payload["link"] = request.link
        if request.picture:
            payload["picture"] = request.picture

        response = await self._request(
            "POST",
            f"/{self.page_id}/feed",
            json_payload=payload,
        )

        return response

    async def schedule_page_post(
        self, request: PagePostScheduleRequest
    ) -> dict[str, Any]:
        """Schedule a page post for future publication."""
        self._check_rate_limit("page_posts", 600)

        if request.scheduled_publish_time <= datetime.now(UTC):
            raise FacebookAPIError(400, "Scheduled time must be in future")

        payload = {
            "message": request.message,
            "scheduled_publish_time": int(request.scheduled_publish_time.timestamp()),
        }

        if request.link:
            payload["link"] = request.link

        response = await self._request(
            "POST",
            f"/{self.page_id}/feed",
            json_payload=payload,
        )

        return response

    async def send_message(self, request: MessengerMessageRequest) -> dict[str, Any]:
        """Send Messenger message to a user."""
        self._check_rate_limit("messages", 200)

        payload = {
            "recipient": {"id": request.recipient_id},
            "message": {"text": request.message_text},
        }

        response = await self._request(
            "POST",
            "/me/messages",
            json_payload=payload,
        )

        return response

    async def get_page_insights(self, post_id: str) -> FacebookInsights:
        """Get insights for a specific post."""
        self._check_rate_limit("insights", 200)

        metrics = [
            "engagement",
            "impressions",
            "reach",
            "reactions.summary(total_count).limit(0)",
        ]

        response = await self._request(
            "GET",
            f"/{post_id}/insights",
            params={
                "metric": ",".join(metrics),
            },
        )

        data = response.get("data", [])
        insights_map = {item["name"]: item.get("values", [{}])[0].get("value", 0) for item in data}

        return FacebookInsights(
            post_id=post_id,
            page_impressions=insights_map.get("impressions", 0),
            engagement=insights_map.get("engagement", 0),
        )

    async def delete_post(self, post_id: str) -> dict[str, Any]:
        """Delete a page post."""
        self._check_rate_limit("posts:delete", 100)

        response = await self._request("DELETE", f"/{post_id}")

        return response

    async def get_post_comments(self, post_id: str, limit: int = 10) -> dict[str, Any]:
        """Get comments on a post."""
        self._check_rate_limit("comments", 200)

        response = await self._request(
            "GET",
            f"/{post_id}/comments",
            params={
                "limit": min(limit, 100),
                "fields": "id,message,created_time,from",
            },
        )

        return response

    async def reply_to_comment(
        self, comment_id: str, message: str
    ) -> dict[str, Any]:
        """Reply to a comment."""
        self._check_rate_limit("comments:reply", 200)

        response = await self._request(
            "POST",
            f"/{comment_id}/private_replies",
            json_payload={"message": message},
        )

        return response
