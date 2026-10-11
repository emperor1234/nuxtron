"""Social/Inbox constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from ....integrations.vendor_manager import get_vendor_manager
from .services.classify_message import _build_suggested_replies
from .services.classify_message import _classify_message
from fastapi import Depends
from typing import Annotated

AuthDep = Annotated[AuthContext, Depends(require_auth)]

MESSAGE_NOT_FOUND = "Inbox message not found."

REPLY_NOT_FOUND = "Saved reply not found."

LOCK_NOT_HELD = "Lock not held by caller or already released."

MESSAGE_TYPES = {"question", "complaint", "compliment", "spam", "conversation", "crisis"}

SENTIMENT_VALUES = {"positive", "neutral", "negative"}

MESSAGE_STATUSES = {"pending", "in_progress", "complete", "flagged", "requires_approval"}

NETWORK_VALUES = {"facebook", "instagram", "x", "linkedin", "tiktok", "youtube", "whatsapp", "google", "reddit"}

SOURCE_TYPES = {"dm", "comment", "mention", "review", "story_reply", "live_comment", "ad_comment"}

_NETWORK_VENDOR_MAP = {
    "facebook": "meta_graph_api",
    "instagram": "meta_graph_api",
    "linkedin": "linkedin_api",
    "twitter": "twitter_api",
    "x": "twitter_api",
    "tiktok": "tiktok_api",
    "reddit": "reddit_api",
    "youtube": "youtube_api",
}

vendor_manager = get_vendor_manager()

_ai_classify = _classify_message

_suggested_replies = _build_suggested_replies
