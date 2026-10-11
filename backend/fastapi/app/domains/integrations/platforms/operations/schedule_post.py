"""Integrations/Platforms use cases: schedule post."""

from __future__ import annotations
from ..services import local_repository as persistence_adapter
from ..services import clients as provider_clients
from .....deps import AuthContext
from .....deps import require_auth
from .....platform_clients.facebook_client import PagePostScheduleRequest
from .....platform_clients.instagram_client import PostScheduleRequest as InstagramPostScheduleRequest
from .....platform_clients.linkedin_client import PostScheduleRequest as LinkedInPostScheduleRequest
from .....platform_clients.tiktok_client import VideoScheduleRequest
from .....platform_clients.twitter_client import TweetScheduleRequest
from ..constants import _SUPPORTED_PLATFORMS
from ..constants import _inbox_messages
from ..constants import _lock
from ..constants import _scheduled_posts
from ..constants import _vendor_manager
from ..runtime import ContextRuntime
from ..schemas import MessageAssignRequest
from ..schemas import MessageReplyRequest
from ..schemas import PlatformScheduleRequest
from ..schemas import SchedulePostRequest
from ..services.clients import _platform_vendor_id
from ..services.clients import _require_platform_credentials
from ..services.clients import _validate_schedule_request
from datetime import UTC
from datetime import datetime
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from typing import Any
import uuid


async def execute_schedule_post(
    runtime: ContextRuntime, request: SchedulePostRequest, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Schedule post across multiple platforms."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:schedule", 300, 60)
    platforms = [platform.strip().lower() for platform in request.platforms]
    if not platforms or any((platform not in _SUPPORTED_PLATFORMS for platform in platforms)):
        raise HTTPException(status_code=422, detail="Unsupported platform requested.")
    _validate_schedule_request(request, list(dict.fromkeys(platforms)), auth.tenant_id)
    scheduled_results: list[dict[str, Any]] = []
    scheduled_records: list[dict[str, Any]] = []
    for platform in dict.fromkeys(platforms):
        credentials = _require_platform_credentials(platform, auth.tenant_id)
        client = provider_clients._build_platform_client(platform, credentials)
        try:
            if platform == "twitter":
                result = await client.schedule_tweet(
                    TweetScheduleRequest(text=request.content, media_ids=None, scheduled_at=request.scheduled_at)
                )
            elif platform == "facebook":
                result = await client.schedule_page_post(
                    PagePostScheduleRequest(message=request.content, scheduled_publish_time=request.scheduled_at)
                )
            elif platform == "instagram":
                result = await client.schedule_post(
                    InstagramPostScheduleRequest(
                        media_type="CAROUSEL" if len(request.media_urls) > 1 else "SINGLE_IMAGE",
                        media_urls=request.media_urls,
                        caption=request.content,
                        scheduled_timestamp=request.scheduled_at,
                    )
                )
            elif platform == "linkedin":
                result = await client.schedule_post(
                    LinkedInPostScheduleRequest(text=request.content, scheduled_time=request.scheduled_at)
                )
            elif platform == "tiktok":
                if not request.media_urls:
                    raise HTTPException(status_code=422, detail="TikTok scheduling requires a video URL.")
                result = await client.schedule_video(
                    VideoScheduleRequest(
                        video_url=request.media_urls[0],
                        title=request.content[:150],
                        description=request.content,
                        scheduled_time=request.scheduled_at,
                    )
                )
            else:
                raise HTTPException(status_code=422, detail=f"Unsupported platform: {platform}")
            scheduled_results.append({"platform": platform, "result": result})
            scheduled_records.append(
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": auth.tenant_id,
                    "platform": platform,
                    "content": request.content,
                    "media_urls": request.media_urls or [],
                    "hashtags": request.hashtags or [],
                    "scheduled_at": request.scheduled_at.isoformat(),
                    "status": "scheduled",
                    "provider_response": result,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
        finally:
            await client.close()
    with _lock:
        if auth.tenant_id not in _scheduled_posts:
            _scheduled_posts[auth.tenant_id] = []
        tenant_posts = _scheduled_posts[auth.tenant_id]
        original_count = len(tenant_posts)
        tenant_posts.extend(scheduled_records)
        try:
            persistence_adapter._persist_scheduled_posts_or_raise()
        except HTTPException:
            del tenant_posts[original_count:]
            raise
    return {
        "status": "scheduled",
        "scheduled_at": request.scheduled_at.isoformat(),
        "platforms": platforms,
        "results": scheduled_results,
    }


async def execute_schedule_single_platform_post(
    runtime: ContextRuntime, platform: str, request: PlatformScheduleRequest, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Schedule content for a single platform."""
    normalized_platform = platform.strip().lower()
    if normalized_platform not in _SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=422, detail="Unsupported platform requested.")
    return await execute_schedule_post(
        runtime,
        SchedulePostRequest(
            content=request.content,
            media_urls=request.media_urls,
            platforms=[normalized_platform],
            scheduled_at=request.scheduled_at,
            hashtags=request.hashtags,
        ),
        auth,
    )


def execute_list_scheduled_posts(runtime: ContextRuntime, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """List all scheduled posts."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:scheduled:list", 300, 60)
    with _lock:
        posts = _scheduled_posts.get(auth.tenant_id, [])
    return {"status": "ok", "count": len(posts), "posts": posts[:20]}


def execute_cancel_scheduled_post(
    runtime: ContextRuntime, post_id: str, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Cancel a scheduled post that has not been published yet."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:schedule:cancel", 200, 60)
    with _lock:
        posts = _scheduled_posts.get(auth.tenant_id, [])
        post = next((p for p in posts if p["id"] == post_id), None)
        if post is None:
            raise HTTPException(status_code=404, detail="Post not found")
        if post.get("status") == "published":
            raise HTTPException(status_code=409, detail="Published posts cannot be cancelled")
        previous_status = post.get("status")
        previous_cancelled_at = post.get("cancelled_at")
        post["status"] = "cancelled"
        post["cancelled_at"] = datetime.now(UTC).isoformat()
        try:
            persistence_adapter._persist_scheduled_posts_or_raise()
        except HTTPException:
            post["status"] = previous_status
            if previous_cancelled_at is None:
                post.pop("cancelled_at", None)
            else:
                post["cancelled_at"] = previous_cancelled_at
            raise
    return {"status": "cancelled", "post_id": post_id}


async def execute_get_post_metrics(
    runtime: ContextRuntime, post_id: str, platform: str = Query(...), auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Get performance metrics for a post."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:metrics", 600, 60)
    normalized = platform.strip().lower()
    if normalized not in _SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=422, detail="Unsupported platform requested.")
    credentials = _require_platform_credentials(normalized, auth.tenant_id)
    client = provider_clients._build_platform_client(normalized, credentials)
    try:
        if normalized == "twitter":
            metrics = await client.get_tweet_metrics(post_id)
        elif normalized == "facebook":
            metrics = await client.get_page_insights(post_id)
        elif normalized == "instagram":
            metrics = await client.get_post_insights(post_id)
        elif normalized == "linkedin":
            metrics = await client.get_post_metrics(post_id)
        elif normalized == "tiktok":
            metrics = await client.get_video_metrics(post_id)
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported platform: {normalized}")
        if hasattr(metrics, "model_dump"):
            payload = metrics.model_dump()
        else:
            payload = dict(metrics)
        payload["platform"] = normalized
        return payload
    finally:
        await client.close()


def execute_analytics_dashboard(runtime: ContextRuntime, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Multi-platform analytics overview."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:analytics:dashboard", 300, 60)
    return {
        "status": "ok",
        "platforms": {
            platform: {
                "connected": _vendor_manager.has_credentials(_platform_vendor_id(platform, auth.tenant_id)),
                "vendor_id": _platform_vendor_id(platform, auth.tenant_id),
            }
            for platform in _SUPPORTED_PLATFORMS
        },
        "summary": "Use /platforms/posts/{post_id}/metrics?platform=<platform> for real platform metrics.",
    }


def execute_get_inbox(
    runtime: ContextRuntime,
    auth: AuthContext = Depends(require_auth),
    platform: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Get unified inbox across platforms."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:list", 600, 60)
    with _lock:
        messages = _inbox_messages.get(auth.tenant_id, [])
        if platform:
            messages = [m for m in messages if m["platform"] == platform]
    return {"status": "ok", "count": len(messages), "messages": messages[:limit]}


def execute_get_message(
    runtime: ContextRuntime, message_id: str, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Get a specific message from unified inbox."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:get", 600, 60)
    with _lock:
        messages = _inbox_messages.get(auth.tenant_id, [])
        message = next((m for m in messages if m.get("id") == message_id), None)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "ok", "message": message}


async def execute_reply_to_message(
    runtime: ContextRuntime, message_id: str, request: MessageReplyRequest, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Reply to a message and persist thread history."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:messages:reply", 600, 60)
    sent_at = datetime.now(UTC).isoformat()
    reply = {
        "id": f"r_{uuid.uuid4().hex[:16]}",
        "text": request.reply_text,
        "is_internal": request.is_internal,
        "author_id": auth.tenant_id,
        "sent_at": sent_at,
    }
    with _lock:
        messages = _inbox_messages.get(auth.tenant_id, [])
        message = next((m for m in messages if m.get("id") == message_id), None)
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
        thread = [item for item in message.get("thread", []) if isinstance(item, dict)]
        thread.append(reply)
        message["thread"] = thread
        message["last_replied_at"] = sent_at
        message["status"] = "internal_note" if request.is_internal else "replied"
        persistence_adapter._persist_inbox_messages_or_raise()
    return {"status": "sent", "message_id": message_id, "reply": reply, "thread_size": len(thread)}


def execute_assign_message(
    runtime: ContextRuntime, message_id: str, request: MessageAssignRequest, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Assign a message to a team member."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:messages:assign", 600, 60)
    assigned_at = datetime.now(UTC).isoformat()
    with _lock:
        messages = _inbox_messages.get(auth.tenant_id, [])
        message = next((m for m in messages if m.get("id") == message_id), None)
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
        message["assignee_id"] = request.assignee_id
        message["assigned_at"] = assigned_at
        persistence_adapter._persist_inbox_messages_or_raise()
    return {
        "status": "assigned",
        "message_id": message_id,
        "assignee_id": request.assignee_id,
        "assigned_at": assigned_at,
    }


def execute_platform_health(runtime: ContextRuntime, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Check connection health for all platforms."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:health", 300, 60)
    return {
        "status": "ok",
        "platforms": {
            platform: {
                "connected": _vendor_manager.has_credentials(_platform_vendor_id(platform, auth.tenant_id)),
                "last_checked": datetime.now(UTC).isoformat(),
            }
            for platform in _SUPPORTED_PLATFORMS
        },
    }
