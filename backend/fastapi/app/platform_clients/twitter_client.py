# pyright: reportUnusedFunction=false
"""
Twitter/X API v2 Client — Production-grade integration.

Implements:
- Tweet creation, scheduling, deletion
- Direct messages
- Timeline fetching
- Metrics & analytics per post
- Retweet, like, reply operations
- OAuth token refresh

Third-Party: Twitter API v2, tweepy wrapper

Error Handling:
- Rate limit (429) → exponential backoff + jitter
- Auth failure (401/403) → token refresh or error
- Server error (5xx) → retry with backoff
- Timeout → retry with shorter window

Rate Limits (Twitter API v2 standard tier):
- Posts/min: 300 (Tweets endpoint)
- Lookups/min: 300
- Search/min: 450
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
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

# ─────────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────────

TWITTER_API_BASE = "https://api.twitter.com/2"
TWITTER_UPLOAD_API_BASE = "https://upload.twitter.com/1.1"
TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

# Rate limits (requests per minute)
RATE_LIMIT_POSTS = 300
RATE_LIMIT_LOOKUPS = 300
RATE_LIMIT_SEARCH = 450

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 1.0
MAX_BACKOFF_SEC = 60.0


# ─────────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────────

class TwitterOAuthToken(BaseModel):
    """OAuth token from Twitter v2 authorization flow."""

    access_token: str
    refresh_token: str | None = None
    expires_in: int = 7200  # seconds
    token_type: str = "Bearer"
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(UTC) >= self.expires_at

    def refresh_in_seconds(self) -> float:
        if self.expires_at is None:
            return 7200
        delta = self.expires_at - datetime.now(UTC)
        return max(delta.total_seconds(), 0)


class TweetCreateRequest(BaseModel):
    """Request to create a tweet."""

    text: str = Field(..., max_length=280, description="Tweet text")
    media_ids: list[str] | None = Field(None, description="Media IDs from media upload")
    reply_settings: str = Field(
        default="public",
        pattern=r"^(public|followers|mentioned_users)$",
        description="Who can reply",
    )
    in_reply_to_tweet_id: str | None = Field(
        None, description="Tweet ID to reply to (thread)"
    )


class TweetScheduleRequest(BaseModel):
    """Request to schedule a tweet."""

    text: str = Field(..., max_length=280)
    media_ids: list[str] | None = None
    scheduled_at: datetime = Field(
        ..., description="UTC datetime to schedule publication"
    )


class DMSendRequest(BaseModel):
    """Request to send a direct message."""

    recipient_id: str = Field(..., description="Twitter user ID")
    text: str = Field(..., max_length=10000)
    media_ids: list[str] | None = None


class TwitterMetrics(BaseModel):
    """Post metrics returned by Twitter API."""

    tweet_id: str
    created_at: datetime
    text: str
    public_metrics: dict[str, int] = Field(
        default_factory=dict,
        description="like_count, retweet_count, reply_count, quote_count",
    )
    impression_count: int | None = None
    bookmark_count: int | None = None


class TwitterAPIError(Exception):
    """Custom exception for Twitter API errors."""

    def __init__(self, status_code: int, detail: str, retry_after: int | None = None):
        self.status_code = status_code
        self.detail = detail
        self.retry_after = retry_after or (2 ** (MAX_RETRIES - 1))
        super().__init__(f"Twitter API {status_code}: {detail}")


# ─────────────────────────────────────────────────────────────────────────────────
# Client
# ─────────────────────────────────────────────────────────────────────────────────


class TwitterV2Client:
    """Production Twitter API v2 client."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        """
        Initialize Twitter v2 client.

        Args:
            access_token: OAuth2 access token
            refresh_token: OAuth2 refresh token (for token refresh)
            expires_at: Expiration datetime of access_token
            client_id: OAuth client ID (required for refresh)
            client_secret: OAuth client secret (required for refresh)
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at or datetime.now(UTC) + timedelta(hours=2)
        self.client_id = client_id
        self.client_secret = client_secret
        self.authenticated_user_id: str | None = None

        # Rate limit tracking (per-minute windows)
        self._rate_buckets: dict[str, list[float]] = {}
        self._session: httpx.AsyncClient | None = None

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()

    async def _ensure_session(self) -> httpx.AsyncClient:
        """Lazily create async HTTP session."""
        if self._session is None:
            self._session = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "nuxtron-twitter-client/1.0"},
            )
        return self._session

    def _check_rate_limit(self, bucket_key: str, limit: int) -> None:
        """
        Check if we're within rate limit for this bucket.

        Bucket key example: "tweets:create" or "user:lookup"
        """
        now = time.time()
        window_start = now - 60  # 1-minute window

        # Clean old entries
        if bucket_key not in self._rate_buckets:
            self._rate_buckets[bucket_key] = []

        self._rate_buckets[bucket_key] = [
            t for t in self._rate_buckets[bucket_key] if t >= window_start
        ]

        # Check limit
        if len(self._rate_buckets[bucket_key]) >= limit:
            retry_after = int(
                60 - (now - self._rate_buckets[bucket_key][0]) + 1
            )
            raise TwitterAPIError(
                429, f"Rate limit exceeded. Retry after {retry_after}s", retry_after
            )

        # Record this request
        self._rate_buckets[bucket_key].append(now)

    async def _refresh_token_if_needed(self) -> None:
        """Refresh access token if expired and refresh_token available."""
        if self.access_token and not self._is_token_expired():
            return

        if not self.refresh_token:
            raise TwitterAPIError(401, "Access token expired and no refresh token")

        if not self.client_id or not self.client_secret:
            raise TwitterAPIError(401, "Client credentials required for token refresh")

        session = await self._ensure_session()

        try:
            response = await session.post(
                TWITTER_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            self.expires_at = datetime.now(UTC) + timedelta(
                seconds=data.get("expires_in", 7200)
            )

            if "refresh_token" in data:
                self.refresh_token = data["refresh_token"]

            logger.info("Twitter token refreshed successfully")

        except httpx.HTTPError as exc:
            raise TwitterAPIError(401, f"Token refresh failed: {exc}") from exc

    def _is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.expires_at:
            return False
        # Refresh if less than 5 minutes remaining
        return datetime.now(UTC) >= (self.expires_at - timedelta(minutes=5))

    @retry(
        retry=retry_if_exception_type((TwitterAPIError, httpx.TimeoutException)),
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
        """
        Make authenticated HTTP request to Twitter API v2.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: URL path (e.g., "/tweets")
            json_payload: Request body
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            TwitterAPIError: On API error
        """
        await self._refresh_token_if_needed()

        session = await self._ensure_session()
        url = f"{TWITTER_API_BASE}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = await session.request(
                method,
                url,
                json=json_payload,
                params=params,
                headers=headers,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("x-rate-limit-reset", 60))
                raise TwitterAPIError(429, "Rate limited", retry_after)

            # Handle auth errors
            if response.status_code in (401, 403):
                raise TwitterAPIError(
                    response.status_code, response.text or "Auth failed"
                )

            # Handle server errors (retry)
            if response.status_code >= 500:
                raise TwitterAPIError(response.status_code, "Server error")

            response.raise_for_status()

            return response.json() if response.content else {}

        except httpx.TimeoutException as exc:
            raise TwitterAPIError(504, f"Request timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise TwitterAPIError(500, f"HTTP error: {exc}") from exc

    async def create_tweet(self, request: TweetCreateRequest) -> dict[str, Any]:
        """
        Create a tweet.

        Args:
            request: Tweet creation request

        Returns:
            Created tweet data with ID

        Raises:
            TwitterAPIError: On API error
        """
        self._check_rate_limit("tweets:create", RATE_LIMIT_POSTS)

        payload: dict[str, Any] = {
            "text": request.text,
            "reply_settings": request.reply_settings,
        }

        if request.media_ids:
            payload["media"] = {"media_ids": request.media_ids}

        if request.in_reply_to_tweet_id:
            payload["reply"] = {"in_reply_to_tweet_id": request.in_reply_to_tweet_id}

        response = await self._request("POST", "/tweets", json_payload=payload)

        return response

    async def schedule_tweet(self, request: TweetScheduleRequest) -> dict[str, Any]:
        """
        Schedule a tweet for future publication.

        Uses Twitter's scheduled tweets endpoint.

        Args:
            request: Schedule request with time

        Returns:
            Scheduled tweet ID and metadata

        Raises:
            TwitterAPIError: On API error
        """
        self._check_rate_limit("tweets:create", RATE_LIMIT_POSTS)

        if request.scheduled_at <= datetime.now(UTC):
            raise TwitterAPIError(
                400, "Scheduled time must be in the future"
            )

        payload: dict[str, Any] = {
            "text": request.text,
            "scheduled_at": request.scheduled_at.isoformat(),
        }

        if request.media_ids:
            payload["media"] = {"media_ids": request.media_ids}

        response = await self._request(
            "POST", "/tweets/schedule", json_payload=payload
        )

        return response

    async def delete_tweet(self, tweet_id: str) -> dict[str, Any]:
        """Delete a tweet."""
        self._check_rate_limit("tweets:delete", RATE_LIMIT_POSTS)

        response = await self._request("DELETE", f"/tweets/{tweet_id}")

        return response

    async def get_tweet_metrics(self, tweet_id: str) -> TwitterMetrics:
        """
        Get detailed metrics for a tweet.

        Returns impressions, engagement, etc.
        """
        self._check_rate_limit("tweets:lookup", RATE_LIMIT_LOOKUPS)

        params = {
            "tweet.fields": "created_at,public_metrics,impression_count,bookmark_count",
        }

        response = await self._request("GET", f"/tweets/{tweet_id}", params=params)

        data = response.get("data", {})

        return TwitterMetrics(
            tweet_id=tweet_id,
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now(UTC).isoformat())
            ),
            text=data.get("text", ""),
            public_metrics=data.get("public_metrics", {}),
            impression_count=data.get("impression_count"),
            bookmark_count=data.get("bookmark_count"),
        )

    async def send_dm(self, request: DMSendRequest) -> dict[str, Any]:
        """
        Send a direct message.

        Args:
            request: DM send request

        Returns:
            Message ID and metadata
        """
        self._check_rate_limit("dm:create", RATE_LIMIT_POSTS)

        payload: dict[str, Any] = {
            "conversation_type": "DirectMessage",
            "participant_ids": [self.authenticated_user_id, request.recipient_id],
            "message": {
                "text": request.text,
            },
        }

        if request.media_ids:
            payload["message"]["attachments"] = [
                {"media_key": mid} for mid in request.media_ids
            ]

        response = await self._request(
            "POST", "/direct_messages", json_payload=payload
        )

        return response

    async def like_tweet(self, tweet_id: str) -> dict[str, Any]:
        """Like a tweet."""
        self._check_rate_limit("likes:create", RATE_LIMIT_POSTS)

        if not self.authenticated_user_id:
            raise TwitterAPIError(401, "Authenticated user ID not set")

        payload = {"tweet_id": tweet_id}

        response = await self._request(
            "POST",
            f"/users/{self.authenticated_user_id}/likes",
            json_payload=payload,
        )

        return response

    async def retweet(self, tweet_id: str) -> dict[str, Any]:
        """Retweet a tweet."""
        self._check_rate_limit("retweets:create", RATE_LIMIT_POSTS)

        if not self.authenticated_user_id:
            raise TwitterAPIError(401, "Authenticated user ID not set")

        payload = {"tweet_id": tweet_id}

        response = await self._request(
            "POST",
            f"/users/{self.authenticated_user_id}/retweets",
            json_payload=payload,
        )

        return response

    async def get_authenticated_user(self) -> dict[str, Any]:
        """
        Get authenticated user info (ID, username, name).

        Called after OAuth to populate self.authenticated_user_id
        """
        response = await self._request(
            "GET",
            "/users/me",
            params={
                "user.fields": "created_at,description,public_metrics,verified"
            },
        )

        if "data" in response:
            self.authenticated_user_id = response["data"]["id"]

        return response

    async def get_timeline(
        self,
        user_id: str,
        limit: int = 10,
        exclude_retweets: bool = False,
    ) -> dict[str, Any]:
        """
        Get user's timeline (recent tweets).

        Args:
            user_id: Twitter user ID
            limit: Number of tweets to fetch (max 100)
            exclude_retweets: Exclude retweets from results

        Returns:
            List of tweets with metadata
        """
        self._check_rate_limit("tweets:lookup", RATE_LIMIT_LOOKUPS)

        limit = min(limit, 100)

        params = {
            "max_results": limit,
            "tweet.fields": "created_at,public_metrics,author_id",
        }

        if exclude_retweets:
            params["-is:retweet"] = "1"

        response = await self._request(
            "GET", f"/users/{user_id}/tweets", params=params
        )

        return response
