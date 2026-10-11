"""Integrations/Platforms request contracts."""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from pydantic import Field
from typing import Any


class OAuthAuthorizeRequest(BaseModel):
    """Request OAuth authorization."""

    platform: str = Field(..., pattern="^(twitter|facebook|instagram|linkedin|tiktok)$")
    redirect_uri: str = Field(..., description="Callback URI after authorization")
    scopes: list[str] | None = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback payload for credential persistence."""

    code: str | None = None
    state: str | None = None
    redirect_uri: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    additional_config: dict[str, Any] | None = None


class PublishRequest(BaseModel):
    """Request to publish content."""

    content: str = Field(..., max_length=5000)
    media_urls: list[str] | None = None
    hashtags: list[str] | None = None
    scheduled_at: datetime | None = None


class SchedulePostRequest(BaseModel):
    """Request to schedule post."""

    content: str
    media_urls: list[str] | None = None
    platforms: list[str] = Field(default=..., min_length=1)
    scheduled_at: datetime
    hashtags: list[str] | None = None


class PlatformScheduleRequest(BaseModel):
    """Request to schedule post for a single platform."""

    content: str
    media_urls: list[str] | None = None
    scheduled_at: datetime
    hashtags: list[str] | None = None


class MessageReplyRequest(BaseModel):
    """Request to reply to message."""

    reply_text: str = Field(..., max_length=2000)
    is_internal: bool = Field(default=False, description="Internal note only?")


class MessageAssignRequest(BaseModel):
    """Request to assign a message to a team member."""

    assignee_id: str = Field(..., min_length=1, max_length=160)


class MessageTagRequest(BaseModel):
    """Request to add labels to a message."""

    tags: list[str] = Field(..., min_length=1)
