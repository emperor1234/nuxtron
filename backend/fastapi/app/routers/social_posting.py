# pyright: reportUnusedFunction=false
"""
Social Media Posting router — Multi-platform scheduling, auto-posting, analytics.

Endpoints:
---------
POST   /social/schedule/{ad_id}            – Schedule ad post to platforms
POST   /social/auto-post/start             – Enable auto-posting for campaign
POST   /social/auto-post/stop              – Disable auto-posting
GET    /social/scheduled-posts             – List all scheduled posts
POST   /social/posts/{id}/publish-now      – Publish scheduled post immediately
POST   /social/analytics/update            – Update post performance metrics
GET    /social/performance/{post_id}       – Get post performance
"""

from __future__ import annotations

import os
import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/social", tags=["Social Media"])

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# { tenant_id: [scheduled_post, ...] }
_scheduled_posts: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [post_analytics, ...] }
_post_analytics: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [auto_post_job, ...] }
_auto_post_jobs: dict[str, list[dict[str, Any]]] = {}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SchedulePostRequest(BaseModel):
    platforms: list[str] = Field(..., description="Platforms to post to (facebook, instagram, tiktok, etc.)")
    scheduled_time: datetime = Field(..., description="When to publish")
    captions: dict[str, str] | None = Field(None, description="Platform-specific captions")
    hashtags: dict[str, list[str]] | None = Field(None, description="Platform-specific hashtags")


class BulkScheduleItem(BaseModel):
    ad_id: str = Field(..., min_length=1, max_length=120)
    platforms: list[str] = Field(..., min_length=1, max_length=10)
    scheduled_time: datetime = Field(..., description="When to publish")
    captions: dict[str, str] | None = Field(None, description="Platform-specific captions")
    hashtags: dict[str, list[str]] | None = Field(None, description="Platform-specific hashtags")


class BulkScheduleRequest(BaseModel):
    posts: list[BulkScheduleItem] = Field(..., min_length=1, max_length=200)

class UpdateAnalyticsRequest(BaseModel):
    post_id: str = Field(..., description="Post ID")
    impressions: int = Field(..., ge=0)
    clicks: int = Field(..., ge=0)
    engagements: int = Field(..., ge=0)
    ctr: float = Field(..., ge=0, le=100)
    cpc_usd: float = Field(default=0.0, ge=0)

class AutoPostRequest(BaseModel):
    campaign_id: str = Field(..., description="Campaign to auto-post")
    interval_hours: int = Field(default=24, ge=1, le=720)
    enabled: bool = Field(default=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_utc_datetime(value: datetime | str) -> datetime:
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        parsed = value

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


_SUPPORTED_PLATFORMS = {
    "facebook",
    "instagram",
    "tiktok",
    "youtube",
    "linkedin",
    "pinterest",
    "reddit",
    "threads",
}


def _normalize_platforms(platforms: list[str]) -> list[str]:
    normalized = [p.strip().lower() for p in platforms if p and p.strip()]
    unique = list(dict.fromkeys(normalized))
    if not unique:
        raise HTTPException(status_code=422, detail="At least one platform is required")
    unsupported = [p for p in unique if p not in _SUPPORTED_PLATFORMS]
    if unsupported:
        raise HTTPException(status_code=422, detail=f"Unsupported platforms: {', '.join(unsupported)}")
    return unique


def _validate_scheduled_time(scheduled_time: datetime) -> datetime:
    scheduled_utc = _ensure_utc_datetime(scheduled_time)
    now_utc = datetime.now(UTC)
    if scheduled_utc < now_utc - timedelta(minutes=2):
        raise HTTPException(status_code=422, detail="Scheduled time cannot be in the past")
    if scheduled_utc > now_utc + timedelta(days=365):
        raise HTTPException(status_code=422, detail="Scheduled time cannot exceed 365 days")
    return scheduled_utc


def _http_json_request(method: str, url: str, headers: dict[str, str], json_payload: dict[str, Any]) -> dict[str, Any]:
    timeout_sec = float(os.getenv("SOCIAL_PROVIDER_HTTP_TIMEOUT_SECONDS", "15.0"))
    try:
        with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
            response = client.request(method, url, headers=headers, json=json_payload)
            response.raise_for_status()
            return response.json() if response.content else {}
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Social provider timeout") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Social provider error: {exc}") from exc

def _get_scheduled_posts(tid: str) -> list[dict[str, Any]]:
    with _lock:
        return _scheduled_posts.setdefault(tid, [])

def _get_auto_post_jobs(tid: str) -> list[dict[str, Any]]:
    with _lock:
        return _auto_post_jobs.setdefault(tid, [])

def _publish_to_meta(ad_data: dict[str, Any], caption: str, platform: str) -> dict[str, Any]:
    """Publish to Facebook or Instagram via Meta Graph API."""
    access_token = os.getenv("META_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise HTTPException(status_code=503, detail="Meta not configured")
    
    page_id = os.getenv("META_PAGE_ID", "").strip()
    if not page_id:
        raise HTTPException(status_code=503, detail="Meta page not configured")

    graph_base = os.getenv("META_GRAPH_BASE", "https://graph.facebook.com/v18.0").strip()
    if platform == "instagram":
        ig_user_id = os.getenv("META_IG_USER_ID", "").strip()
        if not ig_user_id:
            raise HTTPException(status_code=503, detail="Meta Instagram user not configured")
        create_media = _http_json_request(
            "POST",
            f"{graph_base}/{ig_user_id}/media",
            headers={"Authorization": f"Bearer {access_token}"},
            json_payload={"caption": caption, "media_type": "IMAGE", "image_url": ad_data.get("image_url", "")},
        )
        creation_id = create_media.get("id") or create_media.get("creation_id")
        if not creation_id:
            raise HTTPException(status_code=502, detail="Meta Instagram publish response missing media id")
        published = _http_json_request(
            "POST",
            f"{graph_base}/{ig_user_id}/media_publish",
            headers={"Authorization": f"Bearer {access_token}"},
            json_payload={"creation_id": creation_id},
        )
        post_id = published.get("id") or creation_id
        return {
            "status": "published",
            "platform": platform,
            "post_id": post_id,
            "published_at": _now(),
            "url": f"https://instagram.com/p/{post_id}",
        }

    response = _http_json_request(
        "POST",
        f"{graph_base}/{page_id}/feed",
        headers={"Authorization": f"Bearer {access_token}"},
        json_payload={"message": caption, "link": ad_data.get("link", "")},
    )
    post_id = response.get("id") or response.get("post_id")
    if not post_id:
        raise HTTPException(status_code=502, detail="Meta publish response missing id")
    
    return {
        "status": "published",
        "platform": platform,
        "post_id": post_id,
        "published_at": _now(),
        "url": f"https://{platform}.com/posts/{post_id}"
    }

def _publish_to_tiktok(ad_data: dict[str, Any], caption: str) -> dict[str, Any]:
    """Publish to TikTok via TikTok Ads API."""
    access_token = os.getenv("TIKTOK_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise HTTPException(status_code=503, detail="TikTok not configured")
    
    advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID", "").strip()
    if not advertiser_id:
        raise HTTPException(status_code=503, detail="TikTok advertiser not configured")

    response = _http_json_request(
        "POST",
        os.getenv("TIKTOK_VIDEO_UPLOAD_ENDPOINT", "https://business-api.tiktok.com/open_api/v1.3/video/upload/").strip(),
        headers={"Access-Token": access_token},
        json_payload={"advertiser_id": advertiser_id, "caption": caption, "ad_id": ad_data.get("ad_id")},
    )
    post_id = response.get("data", {}).get("video_id") or response.get("video_id") or response.get("id")
    if not post_id:
        raise HTTPException(status_code=502, detail="TikTok publish response missing id")
    
    return {
        "status": "published",
        "platform": "tiktok",
        "post_id": post_id,
        "published_at": _now(),
        "url": f"https://tiktok.com/@{advertiser_id}/video/{post_id}"
    }

def _publish_to_youtube(ad_data: dict[str, Any], caption: str) -> dict[str, Any]:
    """Publish to YouTube via YouTube API."""
    access_token = os.getenv("YOUTUBE_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise HTTPException(status_code=503, detail="YouTube not configured")

    response = _http_json_request(
        "POST",
        os.getenv("YOUTUBE_UPLOAD_ENDPOINT", "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=resumable").strip(),
        headers={"Authorization": f"Bearer {access_token}"},
        json_payload={"snippet": {"title": caption[:100], "description": caption}, "status": {"privacyStatus": "public"}},
    )
    post_id = response.get("id") or response.get("videoId") or response.get("video_id")
    if not post_id:
        raise HTTPException(status_code=502, detail="YouTube publish response missing id")
    
    return {
        "status": "published",
        "platform": "youtube",
        "post_id": post_id,
        "published_at": _now(),
        "url": f"https://youtube.com/watch?v={post_id}"
    }

def _publish_to_linkedin(ad_data: dict[str, Any], caption: str) -> dict[str, Any]:
    """Publish to LinkedIn via LinkedIn API."""
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise HTTPException(status_code=503, detail="LinkedIn not configured")
    
    person_id = os.getenv("LINKEDIN_PERSON_ID", "").strip()
    if not person_id:
        raise HTTPException(status_code=503, detail="LinkedIn person not configured")

    response = _http_json_request(
        "POST",
        os.getenv("LINKEDIN_POST_ENDPOINT", "https://api.linkedin.com/v2/ugcPosts").strip(),
        headers={"Authorization": f"Bearer {access_token}", "X-Restli-Protocol-Version": "2.0.0"},
        json_payload={"author": f"urn:li:person:{person_id}", "lifecycleState": "PUBLISHED", "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": caption}, "shareMediaCategory": "IMAGE"}}},
    )
    post_id = response.get("id") or response.get("urn") or response.get("activity_id")
    if not post_id:
        raise HTTPException(status_code=502, detail="LinkedIn publish response missing id")
    
    return {
        "status": "published",
        "platform": "linkedin",
        "post_id": post_id,
        "published_at": _now(),
        "url": f"https://linkedin.com/feed/update/{post_id}"
    }

def _publish_to_pinterest(ad_data: dict[str, Any], caption: str) -> dict[str, Any]:
    """Publish to Pinterest via Pinterest API."""
    access_token = os.getenv("PINTEREST_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise HTTPException(status_code=503, detail="Pinterest not configured")

    response = _http_json_request(
        "POST",
        os.getenv("PINTEREST_PIN_ENDPOINT", "https://api.pinterest.com/v5/pins").strip(),
        headers={"Authorization": f"Bearer {access_token}"},
        json_payload={"title": caption[:100], "description": caption, "link": ad_data.get("link", "")},
    )
    post_id = response.get("id") or response.get("pin_id")
    if not post_id:
        raise HTTPException(status_code=502, detail="Pinterest publish response missing id")
    
    return {
        "status": "published",
        "platform": "pinterest",
        "post_id": post_id,
        "published_at": _now(),
        "url": f"https://pinterest.com/pin/{post_id}"
    }


def _publish_to_reddit(ad_data: dict[str, Any], caption: str) -> dict[str, Any]:
    """Publish to Reddit via Reddit OAuth API."""
    access_token = os.getenv("REDDIT_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise HTTPException(status_code=503, detail="Reddit not configured")

    subreddit = os.getenv("REDDIT_SUBREDDIT", "").strip()
    if not subreddit:
        raise HTTPException(status_code=503, detail="Reddit subreddit not configured")

    response = _http_json_request(
        "POST",
        os.getenv("REDDIT_SUBMIT_ENDPOINT", "https://oauth.reddit.com/api/submit").strip(),
        headers={"Authorization": f"Bearer {access_token}"},
        json_payload={
            "sr": subreddit,
            "kind": "link",
            "title": caption[:300] or f"Post {ad_data.get('ad_id', '')}".strip(),
            "url": ad_data.get("link", "https://nuxtron.local"),
        },
    )
    post_id = response.get("json", {}).get("data", {}).get("id") or response.get("id")
    if not post_id:
        raise HTTPException(status_code=502, detail="Reddit publish response missing id")

    return {
        "status": "published",
        "platform": "reddit",
        "post_id": post_id,
        "published_at": _now(),
        "url": f"https://reddit.com/r/{subreddit}/comments/{post_id}",
    }


def _publish_to_threads(ad_data: dict[str, Any], caption: str) -> dict[str, Any]:
    """Publish to Threads via Threads Graph API."""
    access_token = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise HTTPException(status_code=503, detail="Threads not configured")

    user_id = os.getenv("THREADS_USER_ID", "").strip()
    if not user_id:
        raise HTTPException(status_code=503, detail="Threads user not configured")

    graph_base = os.getenv("THREADS_GRAPH_BASE", "https://graph.threads.net/v1.0").strip()
    create_resp = _http_json_request(
        "POST",
        f"{graph_base}/{user_id}/threads",
        headers={"Authorization": f"Bearer {access_token}"},
        json_payload={"text": caption or ad_data.get("caption", ""), "media_type": "TEXT"},
    )
    creation_id = create_resp.get("id") or create_resp.get("creation_id")
    if not creation_id:
        raise HTTPException(status_code=502, detail="Threads publish response missing creation id")

    publish_resp = _http_json_request(
        "POST",
        f"{graph_base}/{user_id}/threads_publish",
        headers={"Authorization": f"Bearer {access_token}"},
        json_payload={"creation_id": creation_id},
    )
    post_id = publish_resp.get("id") or creation_id
    return {
        "status": "published",
        "platform": "threads",
        "post_id": post_id,
        "published_at": _now(),
        "url": f"https://www.threads.net/t/{post_id}",
    }


def _publish_to_platform(platform: str, ad_data: dict[str, Any], caption: str) -> dict[str, Any]:
    if platform == "facebook":
        return _publish_to_meta(ad_data, caption, "facebook")
    if platform == "instagram":
        return _publish_to_meta(ad_data, caption, "instagram")
    if platform == "tiktok":
        return _publish_to_tiktok(ad_data, caption)
    if platform == "youtube":
        return _publish_to_youtube(ad_data, caption)
    if platform == "linkedin":
        return _publish_to_linkedin(ad_data, caption)
    if platform == "pinterest":
        return _publish_to_pinterest(ad_data, caption)
    if platform == "reddit":
        return _publish_to_reddit(ad_data, caption)
    if platform == "threads":
        return _publish_to_threads(ad_data, caption)
    return {"status": "unsupported", "platform": platform}

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/schedule/{ad_id}")
def schedule_post(ad_id: str, payload: SchedulePostRequest, auth: AuthDep) -> dict[str, Any]:
    """Schedule ad post to one or more platforms."""
    scheduled_time = _validate_scheduled_time(payload.scheduled_time)
    platforms = _normalize_platforms(payload.platforms)
    scheduled_post = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "ad_id": ad_id,
        "platforms": platforms,
        "scheduled_time": scheduled_time.isoformat(),
        "captions": payload.captions or {},
        "hashtags": payload.hashtags or {},
        "status": "scheduled",
        "created_at": _now(),
        "published_posts": []
    }
    
    with _lock:
        _scheduled_posts.setdefault(auth.tenant_id, []).append(scheduled_post)
    
    return {
        "success": True,
        "scheduled_post": scheduled_post,
        "platforms_count": len(platforms)
    }


@router.post("/schedule-bulk")
def bulk_schedule_posts(payload: BulkScheduleRequest, auth: AuthDep) -> dict[str, Any]:
    """Bulk schedule posts in one API request with per-item validation results."""
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for item in payload.posts:
        try:
            scheduled_time = _validate_scheduled_time(item.scheduled_time)
            platforms = _normalize_platforms(item.platforms)
            scheduled_post = {
                "id": str(uuid.uuid4()),
                "tenant_id": auth.tenant_id,
                "ad_id": item.ad_id,
                "platforms": platforms,
                "scheduled_time": scheduled_time.isoformat(),
                "captions": item.captions or {},
                "hashtags": item.hashtags or {},
                "status": "scheduled",
                "created_at": _now(),
                "published_posts": [],
            }
            with _lock:
                _scheduled_posts.setdefault(auth.tenant_id, []).append(scheduled_post)
            successes.append({"ad_id": item.ad_id, "scheduled_post": scheduled_post})
        except HTTPException as exc:
            failures.append({"ad_id": item.ad_id, "status_code": exc.status_code, "detail": exc.detail})

    return {
        "success": len(successes) > 0,
        "tenant_id": auth.tenant_id,
        "scheduled": len(successes),
        "failed": len(failures),
        "items": successes,
        "errors": failures,
    }

@router.post("/posts/{post_id}/publish-now")
def publish_now(post_id: str, auth: AuthDep) -> dict[str, Any]:
    """Publish scheduled post immediately to all platforms."""
    posts = _get_scheduled_posts(auth.tenant_id)
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post["status"] = "published"
    post["published_at"] = _now()
    published_results = []
    
    for platform in post["platforms"]:
        caption = post["captions"].get(platform, "")
        result = _publish_to_platform(platform, {"ad_id": post["ad_id"]}, caption)
        
        published_results.append(result)
    
    post["published_posts"] = published_results
    
    return {
        "success": True,
        "post_id": post_id,
        "published_results": published_results,
        "successful_platforms": len([r for r in published_results if r["status"] == "published"])
    }

@router.get("/scheduled-posts")
def list_scheduled_posts(auth: AuthDep, limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    """List all scheduled posts for tenant."""
    posts = _get_scheduled_posts(auth.tenant_id)
    now_utc = datetime.now(UTC)
    upcoming = [p for p in posts if _ensure_utc_datetime(p["scheduled_time"]) > now_utc]
    upcoming.sort(key=lambda p: p["scheduled_time"])
    
    return {
        "posts": upcoming[:limit],
        "total": len(posts),
        "upcoming_count": len(upcoming),
        "tenant_id": auth.tenant_id
    }

@router.post("/auto-post/start")
def start_auto_posting(payload: AutoPostRequest, auth: AuthDep) -> dict[str, Any]:
    """Enable auto-posting for campaign."""
    job = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "campaign_id": payload.campaign_id,
        "interval_hours": payload.interval_hours,
        "enabled": payload.enabled,
        "created_at": _now(),
        "last_post_at": None,
        "next_post_at": _now(),
        "posts_count": 0
    }
    
    with _lock:
        _auto_post_jobs.setdefault(auth.tenant_id, []).append(job)
    
    return {
        "success": True,
        "job": job,
        "message": f"Auto-posting enabled for campaign. Posts every {payload.interval_hours} hours."
    }

@router.post("/auto-post/stop")
def stop_auto_posting(campaign_id: str, auth: AuthDep) -> dict[str, Any]:
    """Disable auto-posting for campaign."""
    jobs = _get_auto_post_jobs(auth.tenant_id)
    job = next((j for j in jobs if j["campaign_id"] == campaign_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Auto-post job not found")
    
    job["enabled"] = False
    job["stopped_at"] = _now()
    
    return {
        "success": True,
        "job": job,
        "message": "Auto-posting disabled."
    }

@router.post("/analytics/update")
def update_post_analytics(payload: UpdateAnalyticsRequest, auth: AuthDep) -> dict[str, Any]:
    """Update post performance metrics."""
    analytics = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "post_id": payload.post_id,
        "impressions": payload.impressions,
        "clicks": payload.clicks,
        "engagements": payload.engagements,
        "ctr": payload.ctr,
        "cpc_usd": payload.cpc_usd,
        "updated_at": _now()
    }
    
    with _lock:
        _post_analytics.setdefault(auth.tenant_id, []).append(analytics)
    
    return {
        "success": True,
        "analytics": analytics,
        "estimated_roas": round(1.5 + (payload.ctr / 100), 2)
    }

@router.get("/performance/{post_id}")
def get_post_performance(post_id: str, auth: AuthDep) -> dict[str, Any]:
    """Get post performance metrics."""
    analytics_list = _post_analytics.get(auth.tenant_id, [])
    analytics = [a for a in analytics_list if a["post_id"] == post_id]
    
    if not analytics:
        return {
            "post_id": post_id,
            "impressions": 0,
            "clicks": 0,
            "ctr": 0.0,
            "engagements": 0,
            "status": "no_data"
        }
    
    latest = analytics[-1]
    
    return {
        "post_id": post_id,
        "impressions": latest["impressions"],
        "clicks": latest["clicks"],
        "ctr": latest["ctr"],
        "engagements": latest["engagements"],
        "cpc_usd": latest["cpc_usd"],
        "estimated_roas": round(1.5 + (latest["ctr"] / 100), 2),
        "last_updated": latest["updated_at"]
    }
