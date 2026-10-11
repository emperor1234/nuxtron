"""Social publishing, team, calendar, and report contracts."""

from pydantic import BaseModel
from pydantic import Field
from typing import Any


class HashtagGroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    hashtags: list[str] = Field(..., min_length=1, max_length=30)
    description: str = Field(default="", max_length=300)


class HashtagGroupUpdateRequest(BaseModel):
    name: str | None = None
    hashtags: list[str] | None = None
    description: str | None = None


class FirstCommentRequest(BaseModel):
    post_id: str = Field(..., min_length=1)
    comment: str = Field(..., min_length=1, max_length=2200)


class ThreadPostRequest(BaseModel):
    post_id: str = Field(..., min_length=1)
    threads: list[str] = Field(..., min_length=1, max_length=25, description="List of tweet texts for the thread")


class CommunityCommentReplyRequest(BaseModel):
    comment_id: str = Field(..., min_length=1)
    reply: str = Field(..., min_length=1, max_length=2200)
    platform: str | None = None


class SavedCommentReplyCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1, max_length=2200)
    shortcut: str | None = Field(default=None, max_length=30)


class PostingScheduleRequest(BaseModel):
    account_id: int = Field(...)
    network: str = Field(..., min_length=1)
    slots: list[dict[str, Any]] = Field(..., description="List of {day: str, time: str} slots")
    timezone: str = Field(default="UTC")


class ContentTemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    content_type: str = Field(..., description="post|thread|story|reel|carousel")
    body: str = Field(..., min_length=1, max_length=5000)
    networks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TeamMemberInviteRequest(BaseModel):
    email: str = Field(..., min_length=5)
    role: str = Field(..., description="admin|editor|approver|analyst|viewer")
    channel_ids: list[int] = Field(default_factory=list, description="Empty = all channels")


class TeamMemberUpdateRequest(BaseModel):
    role: str | None = Field(default=None)
    channel_ids: list[int] | None = None


class StartPageUpdateRequest(BaseModel):
    title: str = Field(default="", max_length=100)
    bio: str = Field(default="", max_length=300)
    theme: str = Field(default="minimal", description="minimal|bold|elegant|creator")
    accent_color: str = Field(default="#1d4ed8")
    background_color: str = Field(default="#ffffff")
    avatar_url: str | None = None
    links: list[dict[str, Any]] = Field(default_factory=list)
    social_links: list[dict[str, Any]] = Field(default_factory=list)


class QueueReorderRequest(BaseModel):
    post_ids: list[str] = Field(..., min_length=1, description="Ordered list of post IDs")


class CalendarMoveRequest(BaseModel):
    new_scheduled_time: str = Field(..., min_length=10, max_length=64)


class CalendarAutoPostRequest(BaseModel):
    auto_post: bool


class AIAssistantRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    action: str = Field(..., description="rephrase|shorten|expand|casual|formal|generate|repurpose")
    target_platform: str | None = None
    tone: str | None = None


class LongformRepurposeRequest(BaseModel):
    source_title: str = Field(default="", max_length=200)
    source_url: str | None = Field(default=None, max_length=3000)
    source_text: str = Field(..., min_length=1, max_length=5000)
    target_platform: str = Field(default="LinkedIn", max_length=80)
    tone: str = Field(default="professional", max_length=80)
    variant_count: int = Field(default=3, ge=1, le=5)
    queue_first_variant: bool = False


class CustomReportRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    networks: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    date_range_days: int = Field(default=30, ge=1, le=365)
    include_logo: bool = Field(default=True)
    accent_color: str = Field(default="#1d4ed8")
    export_format: str = Field(default="pdf", description="pdf|csv|excel")
