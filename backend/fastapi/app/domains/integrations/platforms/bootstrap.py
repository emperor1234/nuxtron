"""Integrations/Platforms HTTP composition and legacy import exports."""

from __future__ import annotations
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from .api import get_oauth_url, list_scheduled_posts, assign_message
from .services.oauth import _oauth_state_secret as _oauth_state_secret
from .services.oauth import _encode_oauth_state as _encode_oauth_state
from .services.oauth import _decode_oauth_state as _decode_oauth_state
from .services.oauth import _exchange_oauth_code as _exchange_oauth_code
from .configuration import _is_production_env as _is_production_env
from .services.local_repository import _schedule_store_path as _schedule_store_path
from .services.local_repository import _inbox_store_path as _inbox_store_path
from .services.local_repository import _load_json_store as _load_json_store
from .services.local_repository import _load_scheduled_posts_store as _load_scheduled_posts_store
from .services.local_repository import _load_inbox_messages_store as _load_inbox_messages_store
from .services.local_repository import _persist_json_store as _persist_json_store
from .services.local_repository import _persist_scheduled_posts_store as _persist_scheduled_posts_store
from .services.local_repository import _persist_inbox_messages_store as _persist_inbox_messages_store
from .services.local_repository import _persist_scheduled_posts_or_raise as _persist_scheduled_posts_or_raise
from .services.local_repository import _persist_inbox_messages_or_raise as _persist_inbox_messages_or_raise
from .services.clients import _platform_vendor_id as _platform_vendor_id
from .services.clients import _require_platform_credentials as _require_platform_credentials
from .services.clients import _validate_schedule_request as _validate_schedule_request
from .services.clients import _build_platform_client as _build_platform_client
from .services.clients import _close_client as _close_client
from .schemas import SchedulePostRequest as SchedulePostRequest
from .schemas import OAuthAuthorizeRequest as OAuthAuthorizeRequest
from .schemas import MessageReplyRequest as MessageReplyRequest
from .schemas import PublishRequest as PublishRequest
from .schemas import MessageTagRequest as MessageTagRequest
from .schemas import PlatformScheduleRequest as PlatformScheduleRequest
from .schemas import OAuthCallbackRequest as OAuthCallbackRequest
from .schemas import MessageAssignRequest as MessageAssignRequest
from .constants import _scheduled_posts as _scheduled_posts
from .constants import _lock as _lock
from .constants import _inbox_messages as _inbox_messages
from .constants import AuthDep as AuthDep
from .constants import _platform_clients as _platform_clients
from .constants import logger as logger
from .constants import _SUPPORTED_PLATFORMS as _SUPPORTED_PLATFORMS
from .constants import _vendor_manager as _vendor_manager
import json
import base64
import hashlib
import hmac
import logging
import os
import secrets
import threading
import time
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Annotated
from typing import Any
from urllib.parse import urlencode
import httpx
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from ....deps import AuthContext
from ....deps import require_auth
from ....integrations.vendor_manager import VendorCredentials
from ....integrations.vendor_manager import VendorType
from ....integrations.vendor_manager import get_vendor_manager
from ....platform_clients.facebook_client import FacebookGraphClient
from ....platform_clients.facebook_client import PagePostCreateRequest
from ....platform_clients.facebook_client import PagePostScheduleRequest
from ....platform_clients.instagram_client import CarouselPublishRequest
from ....platform_clients.instagram_client import InstagramGraphClient
from ....platform_clients.instagram_client import ReelPublishRequest
from ....platform_clients.instagram_client import StoryPublishRequest
from ....platform_clients.instagram_client import PostScheduleRequest as InstagramPostScheduleRequest
from ....platform_clients.linkedin_client import LinkedInGraphClient
from ....platform_clients.linkedin_client import PostRequest
from ....platform_clients.linkedin_client import PostScheduleRequest as LinkedInPostScheduleRequest
from ....platform_clients.tiktok_client import TikTokBusinessClient
from ....platform_clients.tiktok_client import VideoScheduleRequest
from ....platform_clients.tiktok_client import VideoUploadRequest
from ....platform_clients.twitter_client import TweetCreateRequest
from ....platform_clients.twitter_client import TweetScheduleRequest
from ....platform_clients.twitter_client import TwitterV2Client


def create_platform_integration_router(*, enforce_rate_limit: Callable[[str, int, int], None]) -> APIRouter:
    """Create platform integration router."""
    router = APIRouter(prefix="/platforms", tags=["Social Media Platforms"])
    runtime = ContextRuntime(enforce_rate_limit=enforce_rate_limit)
    get_oauth_url.register(router, runtime)
    list_scheduled_posts.register(router, runtime)
    assign_message.register(router, runtime)
    return router


_scheduled_posts.update(_load_scheduled_posts_store())
_inbox_messages.update(_load_inbox_messages_store())
