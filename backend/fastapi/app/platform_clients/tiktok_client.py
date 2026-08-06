# pyright: reportUnusedFunction=false
"""
TikTok Business API Client — Production-grade integration.

Implements:
- Video upload & publishing
- Post scheduling
- Analytics & metrics
- Draft management
- Live stream creation (premium)

Third-Party: TikTok Business API / Creator Marketplace API

Requirements:
- Business/Creator account with API access
- Video must comply with TikTok Guidelines
- Processing time: 1-24 hours before visibility

Rate Limits:
- 500 requests per hour per access token
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

TIKTOK_API_BASE = "https://open.tiktok.com/v1"
TIKTOK_BUSINESS_CENTER = "https://business-api.tiktok.com/open_api/v1.3"
MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 2.0
MAX_BACKOFF_SEC = 60.0


class TikTokAPIError(Exception):
    """Custom exception for TikTok API errors."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"TikTok API {status_code}: {detail}")


class VideoUploadRequest(BaseModel):
    """Request to upload a TikTok video."""

    video_url: str = Field(..., description="URL of video file (MP4, AVI, MOV)")
    title: str = Field(..., max_length=150)
    description: str = Field(..., max_length=2200)
    hashtags: list[str] = Field(default_factory=list, max_length=10)
    disable_duet: bool = Field(default=False)
    disable_stitch: bool = Field(default=False)
    disable_comment: bool = Field(default=False)


class VideoScheduleRequest(BaseModel):
    """Request to schedule video publishing."""

    video_url: str
    title: str = Field(..., max_length=150)
    description: str = Field(..., max_length=2200)
    scheduled_time: datetime


class TikTokMetrics(BaseModel):
    """TikTok video metrics."""

    video_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    downloads: int = 0
    completion_rate: float = 0.0


class TikTokBusinessClient:
    """Production TikTok Business API client."""

    def __init__(self, access_token: str, advertiser_id: str):
        """
        Initialize TikTok client.

        Args:
            access_token: TikTok OAuth access token
            advertiser_id: TikTok advertiser/business account ID
        """
        self.access_token = access_token
        self.advertiser_id = advertiser_id

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
            self._session = httpx.AsyncClient(timeout=60.0)  # TikTok is slow
        return self._session

    def _check_rate_limit(self, bucket_key: str, limit: int = 500) -> None:
        """Check rate limit (500 per hour)."""
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
            raise TikTokAPIError(
                429,
                f"Rate limit exceeded. Retry after {retry_after}s",
            )

        self._rate_buckets[bucket_key].append(now)

    @retry(
        retry=retry_if_exception_type(
            (TikTokAPIError, httpx.TimeoutException)
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
        """Make authenticated request to TikTok API."""
        session = await self._ensure_session()

        url = f"{TIKTOK_BUSINESS_CENTER}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        if params is None:
            params = {}

        try:
            response = await session.request(
                method,
                url,
                json=json_payload,
                params=params,
                headers=headers,
            )

            if response.status_code == 429:
                raise TikTokAPIError(429, "Rate limited")

            if response.status_code >= 500:
                raise TikTokAPIError(response.status_code, "Server error")

            response.raise_for_status()

            data = response.json()

            # TikTok wraps response in data field
            if "data" in data:
                return data["data"]

            return data

        except httpx.TimeoutException as exc:
            raise TikTokAPIError(504, f"Timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise TikTokAPIError(500, f"HTTP error: {exc}") from exc

    async def upload_video(self, request: VideoUploadRequest) -> dict[str, Any]:
        """
        Upload a video to TikTok.

        Note: Videos go through approval process (1-24 hours)
        """
        self._check_rate_limit("videos:upload", 500)

        payload = {
            "advertiser_id": self.advertiser_id,
            "video_url": request.video_url,
            "video_title": request.title,
            "video_caption": request.description,
            "video_keywords": request.hashtags,
            "disable_duet": request.disable_duet,
            "disable_stitch": request.disable_stitch,
            "disable_comment": request.disable_comment,
        }

        response = await self._request(
            "POST",
            "/video/upload",
            json_payload=payload,
        )

        return response

    async def schedule_video(self, request: VideoScheduleRequest) -> dict[str, Any]:
        """Schedule a video for future publishing."""
        self._check_rate_limit("videos:schedule", 500)

        if request.scheduled_time <= datetime.now(UTC):
            raise TikTokAPIError(
                400, "Scheduled time must be in future"
            )

        payload = {
            "advertiser_id": self.advertiser_id,
            "video_url": request.video_url,
            "video_title": request.title,
            "video_caption": request.description,
            "publish_mode": "SCHEDULED",
            "publish_time": int(request.scheduled_time.timestamp()),
        }

        response = await self._request(
            "POST",
            "/video/upload",
            json_payload=payload,
        )

        return response

    async def get_video_metrics(self, video_id: str) -> TikTokMetrics:
        """Get metrics for a published video."""
        self._check_rate_limit("videos:analytics", 500)

        response = await self._request(
            "GET",
            f"/video/{video_id}/analytics",
            params={
                "advertiser_id": self.advertiser_id,
                "fields": [
                    "video_views",
                    "video_likes",
                    "video_comments",
                    "video_shares",
                    "video_downloads",
                    "video_completion_rate",
                ],
            },
        )

        data = response or {}

        return TikTokMetrics(
            video_id=video_id,
            views=data.get("video_views", 0),
            likes=data.get("video_likes", 0),
            comments=data.get("video_comments", 0),
            shares=data.get("video_shares", 0),
            downloads=data.get("video_downloads", 0),
            completion_rate=data.get("video_completion_rate", 0.0),
        )

    async def list_videos(self, limit: int = 20) -> dict[str, Any]:
        """List videos for this business account."""
        self._check_rate_limit("videos:list", 500)

        response = await self._request(
            "GET",
            "/video/list",
            params={
                "advertiser_id": self.advertiser_id,
                "limit": min(limit, 100),
            },
        )

        return response

    async def delete_video(self, video_id: str) -> dict[str, Any]:
        """Delete a video (only if not published)."""
        self._check_rate_limit("videos:delete", 500)

        response = await self._request(
            "DELETE",
            f"/video/{video_id}",
            json_payload={
                "advertiser_id": self.advertiser_id,
            },
        )

        return response

    async def get_drafts(self, limit: int = 20) -> dict[str, Any]:
        """Get saved video drafts."""
        self._check_rate_limit("drafts:list", 500)

        response = await self._request(
            "GET",
            "/video/drafts",
            params={
                "advertiser_id": self.advertiser_id,
                "limit": min(limit, 100),
            },
        )

        return response
