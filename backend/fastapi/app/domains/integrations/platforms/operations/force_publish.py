"""Integrations/Platforms use cases: force publish."""

from __future__ import annotations
from ..services import local_repository as persistence_adapter
from .....deps import AuthContext
from .....deps import require_auth
from ..constants import _SUPPORTED_PLATFORMS
from ..constants import _inbox_messages
from ..constants import _lock
from ..constants import _scheduled_posts
from ..constants import _vendor_manager
from ..runtime import ContextRuntime
from ..schemas import MessageTagRequest
from ..schemas import PublishRequest
from ..services.clients import _platform_vendor_id
from .get_oauth_url import execute_publish_post
from datetime import UTC
from datetime import datetime
from fastapi import Depends
from fastapi import HTTPException
from typing import Any


async def execute_force_publish(
    runtime: ContextRuntime, post_id: str, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Force immediate publication of scheduled post."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:publish:force", 100, 60)
    with _lock:
        posts = _scheduled_posts.get(auth.tenant_id, [])
        post = next((p for p in posts if p["id"] == post_id), None)
        if not post:
            raise HTTPException(404, "Post not found")
        if post.get("status") == "cancelled":
            raise HTTPException(status_code=409, detail="Cancelled posts cannot be published")
    publish_results: list[dict[str, Any]] = []
    for platform in post.get("platforms", [post.get("platform")]):
        if not platform:
            continue
        result = await execute_publish_post(
            runtime,
            platform,
            PublishRequest(
                content=str(post.get("content", "")),
                media_urls=list(post.get("media_urls") or []) or None,
                hashtags=list(post.get("hashtags") or []) or None,
            ),
            auth,
        )
        publish_results.append({"platform": platform, "result": result})
    with _lock:
        previous_status = post.get("status")
        previous_published_at = post.get("published_at")
        previous_results = post.get("published_results")
        post["status"] = "published"
        post["published_at"] = datetime.now(UTC).isoformat()
        post["published_results"] = publish_results
        try:
            persistence_adapter._persist_scheduled_posts_or_raise()
        except HTTPException:
            post["status"] = previous_status
            if previous_published_at is None:
                post.pop("published_at", None)
            else:
                post["published_at"] = previous_published_at
            if previous_results is None:
                post.pop("published_results", None)
            else:
                post["published_results"] = previous_results
            raise
    return {"status": "published", "post_id": post_id, "results": publish_results}


def execute_tag_message(
    runtime: ContextRuntime, message_id: str, request: MessageTagRequest, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Add tags/labels to a message."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:messages:tag", 600, 60)
    normalized_tags = [tag.strip() for tag in request.tags if tag.strip()]
    if not normalized_tags:
        raise HTTPException(status_code=422, detail="At least one non-empty tag is required")
    with _lock:
        messages = _inbox_messages.get(auth.tenant_id, [])
        message = next((m for m in messages if m.get("id") == message_id), None)
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
        existing_tags = [str(tag) for tag in message.get("tags", [])]
        merged_tags = list(dict.fromkeys(existing_tags + normalized_tags))
        message["tags"] = merged_tags
        persistence_adapter._persist_inbox_messages_or_raise()
    return {"status": "tagged", "message_id": message_id, "tags": merged_tags}


def execute_verify_accounts(runtime: ContextRuntime, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Verify configured platform credentials are present and not expired."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:accounts:verify", 300, 60)
    verification: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for platform in _SUPPORTED_PLATFORMS:
        credentials = _vendor_manager.get_credentials(_platform_vendor_id(platform, auth.tenant_id))
        if credentials is None:
            verification.append(
                {"platform": platform, "connected": False, "valid": False, "reason": "missing_credentials"}
            )
            continue
        expired = bool(credentials.expires_at and credentials.expires_at <= now)
        verification.append(
            {
                "platform": platform,
                "connected": True,
                "valid": not expired,
                "has_refresh_token": bool(credentials.refresh_token),
                "expires_at": credentials.expires_at.isoformat() if credentials.expires_at else None,
                "reason": "expired_token" if expired else "ok",
            }
        )
    return {"status": "ok", "accounts": verification}


async def execute_platform_analytics_summary(
    runtime: ContextRuntime, platform: str, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Return a platform-level summary from locally tracked scheduled posts."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:analytics:summary", 300, 60)
    normalized = platform.strip().lower()
    if normalized not in _SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=422, detail="Unsupported platform requested.")
    with _lock:
        posts = _scheduled_posts.get(auth.tenant_id, [])
        platform_posts = [post for post in posts if post.get("platform") == normalized]
    status_counts: dict[str, int] = {}
    for post in platform_posts:
        status = str(post.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "status": "ok",
        "platform": normalized,
        "total_posts": len(platform_posts),
        "status_breakdown": status_counts,
    }


def execute_compare_analytics(
    runtime: ContextRuntime, post_ids: list[str], auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Compare locally tracked scheduled-post states across selected post IDs."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:analytics:compare", 300, 60)
    if not post_ids:
        raise HTTPException(status_code=422, detail="post_ids cannot be empty")
    with _lock:
        posts = _scheduled_posts.get(auth.tenant_id, [])
        selected = [post for post in posts if str(post.get("id")) in set(post_ids)]
    comparison = [
        {
            "post_id": str(post.get("id")),
            "platform": post.get("platform"),
            "status": post.get("status"),
            "scheduled_at": post.get("scheduled_at"),
            "published_at": post.get("published_at"),
        }
        for post in selected
    ]
    return {"status": "ok", "requested": len(post_ids), "found": len(selected), "comparison": comparison}
