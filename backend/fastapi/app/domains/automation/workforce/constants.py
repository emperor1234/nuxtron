"""Automation/Workforce constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from fastapi import Depends
from typing import Annotated
from typing import Literal

AuthDep = Annotated[AuthContext, Depends(require_auth)]

RoleType = Literal[
    "social_media",
    "seo",
    "geo",
    "ads",
    "growth_metrics",
    "competitor_strategy",
    "social_listening",
    "industry_news",
    "event_outreach",
    "media_outreach",
    "cvr_optimization",
]

MissionStatus = Literal["draft", "pending_approval", "approved", "running", "completed", "failed", "rejected"]

_META_ME_URL = "https://graph.facebook.com/v20.0/me?fields=id,name"

PROVIDER_CATALOG: dict[str, dict[str, str]] = {
    "x": {
        "name": "X",
        "kind": "social",
        "auth_type": "bearer",
        "test_url": "https://api.x.com/2/users/me",
        "action_url": "https://api.x.com/2/tweets",
    },
    "facebook": {"name": "Facebook", "kind": "social", "auth_type": "bearer", "test_url": _META_ME_URL},
    "instagram": {"name": "Instagram", "kind": "social", "auth_type": "bearer", "test_url": _META_ME_URL},
    "threads": {"name": "Threads", "kind": "social", "auth_type": "bearer", "test_url": _META_ME_URL},
    "tiktok": {
        "name": "TikTok",
        "kind": "social",
        "auth_type": "bearer",
        "test_url": "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id",
    },
    "youtube": {
        "name": "YouTube",
        "kind": "social",
        "auth_type": "bearer",
        "test_url": "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true",
    },
    "google_analytics": {
        "name": "Google Analytics",
        "kind": "analytics",
        "auth_type": "bearer",
        "test_url": "https://analyticsdata.googleapis.com/v1beta/properties",
    },
    "google_search_console": {
        "name": "Google Search Console",
        "kind": "analytics",
        "auth_type": "bearer",
        "test_url": "https://searchconsole.googleapis.com/webmasters/v3/sites",
    },
    "slack": {
        "name": "Slack",
        "kind": "collaboration",
        "auth_type": "bearer",
        "test_url": "https://slack.com/api/auth.test",
        "action_url": "https://slack.com/api/chat.postMessage",
    },
}

DEFAULT_AI_GATEWAY_PATH = "/ai/gateway/generate"

JSON_CONTENT_TYPE = "application/json"
