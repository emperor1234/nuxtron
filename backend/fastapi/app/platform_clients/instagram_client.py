# pyright: reportUnusedFunction=false
"""
Instagram Graph API Client — Production-grade integration.

Implements:
- Reel & carousel post creation
- Story publishing
- Post scheduling
- DM sending
- Insights & analytics
- Comment management

Third-Party: Instagram Graph API (via Facebook Graph API)

Note: Instagram Graph API requires business account + approval.
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

INSTAGRAM_API_BASE = "https://graph.instagram.com/v18.0"
MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 1.0
MAX_BACKOFF_SEC = 60.0


class InstagramAPIError(Exception):
    """Custom exception for Instagram API errors."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Instagram API {status_code}: {detail}")


class ReelPublishRequest(BaseModel):
    """Request to publish an Instagram Reel."""

    video_url: str = Field(..., description="URL of video file")
    caption: str = Field(..., max_length=2200)
    thumbnail_url: str | None = None


class CarouselPublishRequest(BaseModel):
    """Request to publish carousel post (multiple images)."""

    media_urls: list[str] = Field(default=..., min_length=2, max_length=10)
    captions: list[str] | None = None
    main_caption: str | None = Field(None, max_length=2200)


class StoryPublishRequest(BaseModel):
    """Request to publish a story."""

    media_url: str = Field(..., description="Image or video URL")
    media_type: str = Field(..., pattern=r"^(IMAGE|VIDEO)$")
    sticker_type: str | None = Field(None, pattern=r"^(POLL|QUESTION|COUNTDOWN)$")


class PostScheduleRequest(BaseModel):
    """Request to schedule a post."""

    media_type: str = Field(..., pattern=r"^(CAROUSEL|REELS|SINGLE_IMAGE)$")
    media_urls: list[str]
    caption: str
    scheduled_timestamp: datetime


class InstagramDMRequest(BaseModel):
    """Request to send Instagram DM."""

    recipient_ig_user_id: str
    message_text: str = Field(..., max_length=1000)


class InstagramInsights(BaseModel):
    """Instagram post insights."""

    post_id: str
    impressions: int = 0
    reach: int = 0
    engagement: int = 0
    saves: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


class InstagramGraphClient:
    """Production Instagram Graph API client."""

    def __init__(self, access_token: str, ig_user_id: str):
        """
        Initialize Instagram client.

        Args:
            access_token: Facebook Graph API access token (for Instagram API)
            ig_user_id: Instagram Business Account ID
        """
        self.access_token = access_token
        self.ig_user_id = ig_user_id

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
        window_start = now - 3600

        if bucket_key not in self._rate_buckets:
            self._rate_buckets[bucket_key] = []

        self._rate_buckets[bucket_key] = [
            t for t in self._rate_buckets[bucket_key] if t >= window_start
        ]

        if len(self._rate_buckets[bucket_key]) >= limit:
            retry_after = int(
                3600 - (now - self._rate_buckets[bucket_key][0]) + 1
            )
            raise InstagramAPIError(
                429,
                f"Rate limit exceeded. Retry after {retry_after}s",
            )

        self._rate_buckets[bucket_key].append(now)

    @retry(
        retry=retry_if_exception_type(
            (InstagramAPIError, httpx.TimeoutException)
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
        """Make authenticated request to Instagram Graph API."""
        session = await self._ensure_session()

        if params is None:
            params = {}
        params["access_token"] = self.access_token

        url = f"{INSTAGRAM_API_BASE}{endpoint}"

        try:
            response = await session.request(
                method,
                url,
                json=json_payload,
                params=params,
            )

            if response.status_code == 429:
                raise InstagramAPIError(429, "Rate limited")

            if response.status_code >= 500:
                raise InstagramAPIError(response.status_code, "Server error")

            response.raise_for_status()

            return response.json() if response.content else {}

        except httpx.TimeoutException as exc:
            raise InstagramAPIError(504, f"Timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise InstagramAPIError(500, f"HTTP error: {exc}") from exc

    async def publish_reel(self, request: ReelPublishRequest) -> dict[str, Any]:
        """Publish an Instagram Reel."""
        self._check_rate_limit("reels:publish", 200)

        # Step 1: Create Reel media container
        container_response = await self._request(
            "POST",
            f"/{self.ig_user_id}/media",
            json_payload={
                "media_type": "REELS",
                "video_url": request.video_url,
                "caption": request.caption,
                "thumbnail_url": request.thumbnail_url,
            },
        )

        container_id = container_response.get("id")
        if not container_id:
            raise InstagramAPIError(
                400, "Failed to create reel media container"
            )

        # Step 2: Publish container
        publish_response = await self._request(
            "POST",
            f"/{self.ig_user_id}/media_publish",
            json_payload={"creation_id": container_id},
        )

        return publish_response

    async def publish_carousel(
        self, request: CarouselPublishRequest
    ) -> dict[str, Any]:
        """Publish a carousel post (multiple images)."""
        self._check_rate_limit("carousel:publish", 200)

        # Step 1: Create carousel items
        item_ids = []
        for _i, url in enumerate(request.media_urls):
            item_response = await self._request(
                "POST",
                f"/{self.ig_user_id}/media",
                json_payload={
                    "is_carousel_item": True,
                    "image_url": url,
                },
            )
            item_id = item_response.get("id")
            if item_id:
                item_ids.append(item_id)

        if len(item_ids) != len(request.media_urls):
            raise InstagramAPIError(
                400, "Failed to create all carousel items"
            )

        # Step 2: Create carousel container
        container_response = await self._request(
            "POST",
            f"/{self.ig_user_id}/media",
            json_payload={
                "media_type": "CAROUSEL",
                "children": item_ids,
                "caption": request.main_caption or "",
            },
        )

        container_id = container_response.get("id")

        # Step 3: Publish
        publish_response = await self._request(
            "POST",
            f"/{self.ig_user_id}/media_publish",
            json_payload={"creation_id": container_id},
        )

        return publish_response

    async def publish_story(self, request: StoryPublishRequest) -> dict[str, Any]:
        """Publish an Instagram story."""
        self._check_rate_limit("stories:publish", 300)

        payload = {
            "media_type": request.media_type,
            "image_url": request.media_url if request.media_type == "IMAGE" else None,
            "video_url": request.media_url if request.media_type == "VIDEO" else None,
        }

        if request.sticker_type:
            payload["sticker_type"] = request.sticker_type

        response = await self._request(
            "POST",
            f"/{self.ig_user_id}/stories",
            json_payload=payload,
        )

        return response

    async def schedule_post(self, request: PostScheduleRequest) -> dict[str, Any]:
        """Schedule a post for future publication."""
        self._check_rate_limit("posts:schedule", 200)

        if request.scheduled_timestamp <= datetime.now(UTC):
            raise InstagramAPIError(
                400, "Scheduled time must be in future"
            )

        payload = {
            "media_type": request.media_type,
            "caption": request.caption,
            "publish_mode": "SCHEDULED",
            "scheduled_publish_time": int(request.scheduled_timestamp.timestamp()),
        }

        if request.media_type == "CAROUSEL":
            payload["children"] = request.media_urls
        else:
            payload["image_url"] = request.media_urls[0]

        response = await self._request(
            "POST",
            f"/{self.ig_user_id}/media",
            json_payload=payload,
        )

        return response

    async def send_dm(self, request: InstagramDMRequest) -> dict[str, Any]:
        """Send Instagram Direct Message."""
        self._check_rate_limit("dms:send", 200)

        response = await self._request(
            "POST",
            f"/{self.ig_user_id}/messages",
            json_payload={
                "recipient_id": request.recipient_ig_user_id,
                "message_type": "TEXT",
                "text": request.message_text,
            },
        )

        return response

    async def get_post_insights(self, post_id: str) -> InstagramInsights:
        """Get insights for a specific post."""
        self._check_rate_limit("insights", 200)

        metrics = [
            "engagement",
            "impressions",
            "reach",
            "saved",
            "likes",
            "comments",
            "shares",
        ]

        response = await self._request(
            "GET",
            f"/{post_id}/insights",
            params={
                "metric": ",".join(metrics),
            },
        )

        data = response.get("data", [])
        insights_map = {
            item["name"]: item.get("values", [{}])[0].get("value", 0)
            for item in data
        }

        return InstagramInsights(
            post_id=post_id,
            impressions=insights_map.get("impressions", 0),
            reach=insights_map.get("reach", 0),
            engagement=insights_map.get("engagement", 0),
            saves=insights_map.get("saved", 0),
            likes=insights_map.get("likes", 0),
            comments=insights_map.get("comments", 0),
            shares=insights_map.get("shares", 0),
        )

    async def delete_post(self, post_id: str) -> dict[str, Any]:
        """Delete an Instagram post."""
        self._check_rate_limit("posts:delete", 100)

        response = await self._request("DELETE", f"/{post_id}")

        return response

    async def get_comments(self, post_id: str, limit: int = 10) -> dict[str, Any]:
        """Get comments on a post."""
        self._check_rate_limit("comments", 200)

        response = await self._request(
            "GET",
            f"/{post_id}/comments",
            params={
                "limit": min(limit, 50),
                "fields": "id,text,timestamp,from",
            },
        )

        return response
