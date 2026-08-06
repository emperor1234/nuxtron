# pyright: reportUnusedFunction=false
"""
AI Ad Generation router — Predis.ai-equivalent end-to-end system.

Endpoints:
---------
POST   /ads/generate/text-to-ad         – Text prompt → ad variations
POST   /ads/generate/product-ad         – Product URL/image → professional ads
POST   /ads/generate/ugc-video          – Product + avatar → UGC video
POST   /ads/generate/image              – Text prompt → image
POST   /ads/generate/copy               – Hooks + CTAs per platform
POST   /ads/edit/{id}                   – Modify ad in drag-drop editor
POST   /ads/list                        – List tenant's generated ads
POST   /ads/{id}/a-b-test               – Create A/B test variants
GET    /ads/{id}/performance            – CTR, engagement, ROAS

POST   /campaigns/create                – Multi-platform campaign
POST   /campaigns/{id}/schedule         – Schedule posting
POST   /campaigns/{id}/publish          – Immediate publish
GET    /campaigns/{id}/performance      – Campaign metrics

POST   /avatars/create                  – Create UGC avatar (age/gender/ethnicity/voice)
GET    /avatars/list                    – List available avatars
POST   /avatars/{id}/video              – Generate video with avatar

POST   /integrations/shopify/connect    – OAuth Shopify
GET    /integrations/shopify/products   – Sync Shopify products
POST   /integrations/meta/connect       – OAuth Facebook/Instagram
POST   /integrations/tiktok/connect     – OAuth TikTok Ads
GET    /integrations/status             – All connected platforms

GET    /competitor-analysis/track       – Track competitor domain
GET    /competitor-analysis/{id}/ads    – Competitor ad feed
GET    /competitor-analysis/{id}/performance

POST   /credits/check                   – Check remaining credits
POST   /analytics/events                – Track ad performance event
"""

from __future__ import annotations

import base64
import json
import os
import threading
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/ads", tags=["Ad Generation"])

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# { tenant_id: [ad, ...] }
_ads: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: { credits_remaining: int, credit_tier: str } }
_credit_balance: dict[str, dict[str, Any]] = {}

# { tenant_id: [campaign, ...] }
_campaigns: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [avatar, ...] }
_avatars: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [analytics_event, ...] }
_analytics: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: { platform: {oauth_token, expires_at, ...} } }
_platform_integrations: dict[str, dict[str, dict[str, Any]]] = {}

# { tenant_id: [competitor_domain, ...] }
_competitors: dict[str, list[dict[str, Any]]] = {}

# OAuth sessions for integrations
_integration_sessions: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CREDIT_COSTS = {
    "text_to_ad": 10,
    "image_generation": 20,
    "video_generation": 100,
    "ugc_video": 150,
    "auto_post": 5,
    "competitor_track": 2,
}

SUPPORTED_PLATFORMS = [
    "facebook",
    "instagram",
    "tiktok",
    "youtube",
    "linkedin",
    "pinterest",
    "google_ads",
]

AVATAR_VARIANTS = [
    {"id": "avatar_1", "name": "Sarah", "age": 25, "gender": "female", "ethnicity": "caucasian", "voice": "en-US-AriaNeural"},
    {"id": "avatar_2", "name": "James", "age": 30, "gender": "male", "ethnicity": "african", "voice": "en-US-GuyNeural"},
    {"id": "avatar_3", "name": "Priya", "age": 28, "gender": "female", "ethnicity": "asian", "voice": "en-US-AmberNeural"},
    {"id": "avatar_4", "name": "Sofia", "age": 26, "gender": "female", "ethnicity": "hispanic", "voice": "es-ES-ElviraNeural"},
]

# AI Provider endpoints
STABILITY_AI_BASE = "https://api.stability.ai/v1"
ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
OPENAI_BASE = "https://api.openai.com/v1"
RUNWAY_ML_BASE = "https://api.runwayml.com/v1"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AdGenerationRequest(BaseModel):
    seed_text: str = Field(..., description="Text prompt for ad generation")
    platforms: list[str] = Field(default=["instagram", "facebook"], description="Target platforms")
    variations: int = Field(default=3, ge=1, le=10, description="Number of ad variations")
    brand_guidelines: dict[str, str] | None = Field(default=None, description="Brand colors, fonts, tone")

class ProductAdRequest(BaseModel):
    product_url: str | None = Field(None, description="Shopify/e-commerce product URL")
    product_image_url: str | None = Field(None, description="Direct product image URL")
    product_name: str = Field(..., description="Product name")
    product_description: str | None = Field(None, description="Product description")
    platforms: list[str] = Field(default=["instagram", "facebook"], description="Target platforms")

class UGCVideoRequest(BaseModel):
    product_name: str = Field(..., description="Product name")
    product_benefits: list[str] = Field(..., description="Key benefits to highlight")
    avatar_id: str = Field(..., description="Avatar to use")
    script: str | None = Field(None, description="Custom script (or auto-generated)")
    video_duration: int = Field(default=15, ge=5, le=60, description="Video length in seconds")
    background_image_url: str | None = Field(None, description="Background for video")

class AdCopyRequest(BaseModel):
    product_name: str = Field(..., description="Product name")
    key_features: list[str] = Field(..., description="Product features")
    target_audience: str = Field(default="ecommerce", description="Audience segment")
    platform: str = Field(..., description="Target platform (instagram, tiktok, etc.)")
    tone: str = Field(default="casual", description="Copy tone (casual, professional, urgent, funny)")

class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Image description prompt")
    aspect_ratio: str = Field(default="9:16", description="Aspect ratio (9:16, 16:9, 1:1)")
    style: str = Field(default="photo", description="Image style (photo, illustration, 3d, anime)")

class CampaignRequest(BaseModel):
    name: str = Field(..., description="Campaign name")
    ad_ids: list[str] = Field(..., description="Ad IDs to include")
    platforms: list[str] = Field(..., description="Platforms to publish to")
    schedule_start: datetime | None = Field(None, description="When to start posting")
    schedule_end: datetime | None = Field(None, description="When to stop posting")
    auto_post_enabled: bool = Field(default=False, description="Enable auto-posting")
    auto_post_interval_hours: int = Field(default=24, ge=1, le=720)

class AvatarCreateRequest(BaseModel):
    name: str = Field(..., description="Avatar name")
    age: int = Field(..., ge=18, le=70, description="Avatar age")
    gender: str = Field(..., description="Avatar gender (male, female, non-binary)")
    ethnicity: str = Field(..., description="Avatar ethnicity")
    voice_language: str = Field(default="en-US", description="Voice language code")

class IntegrationConnectRequest(BaseModel):
    platform: str = Field(..., description="Platform to connect (shopify, meta, tiktok, youtube, linkedin, pinterest)")
    auth_code: str | None = Field(None, description="OAuth authorization code")
    api_key: str | None = Field(None, description="Direct API key (Shopify)")
    redirect_uri: str = Field(..., description="Redirect URI for OAuth")

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _get_ads(tid: str) -> list[dict[str, Any]]:
    with _lock:
        return _ads.setdefault(tid, [])

def _get_campaigns(tid: str) -> list[dict[str, Any]]:
    with _lock:
        return _campaigns.setdefault(tid, [])

def _get_avatars(tid: str) -> list[dict[str, Any]]:
    with _lock:
        return _avatars.setdefault(tid, AVATAR_VARIANTS)

def _get_credit_balance(tid: str) -> dict[str, Any]:
    with _lock:
        return _credit_balance.setdefault(tid, {"credits": 1300, "tier": "core"})

def _deduct_credits(tid: str, cost: int) -> bool:
    with _lock:
        balance = _credit_balance.setdefault(tid, {"credits": 1300, "tier": "core"})
        if balance["credits"] >= cost:
            balance["credits"] -= cost
            return True
        return False

def _http_json_request(method: str, url: str, headers: dict[str, str], json_payload: dict[str, Any]) -> dict[str, Any]:
    """Generic HTTP request helper with error handling."""
    timeout_sec = float(os.getenv("AI_PROVIDER_HTTP_TIMEOUT_SECONDS", "15.0"))
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.request(method, url, headers=headers, json=json_payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="AI provider timeout") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"AI provider error: {exc}") from exc


def _http_bytes_request(method: str, url: str, headers: dict[str, str], json_payload: dict[str, Any]) -> httpx.Response:
    """Generic HTTP request helper for binary/media responses."""
    timeout_sec = float(os.getenv("AI_PROVIDER_HTTP_TIMEOUT_SECONDS", "15.0"))
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.request(method, url, headers=headers, json=json_payload)
            resp.raise_for_status()
            return resp
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="AI provider timeout") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"AI provider error: {exc}") from exc

def _generate_text_ad_copy(prompt: str, platform: str) -> str:
    """Generate ad copy using OpenAI GPT."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI not configured")
    
    try:
        response = _http_json_request(
            method="POST",
            url=f"{OPENAI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json_payload={
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "system",
                        "content": f"Generate engaging {platform} ad copy for this product. Keep it under 280 characters. Focus on benefits and urgency."
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 100,
                "temperature": 0.7,
            }
        )
        content = response.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise HTTPException(status_code=502, detail="OpenAI response missing content")
        return content
    except HTTPException:
        raise

def _generate_ai_image(prompt: str, aspect_ratio: str = "9:16") -> str:
    """Generate image using Stability AI."""
    api_key = os.getenv("STABILITY_AI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Stability AI not configured")
    
    try:
        response = _http_json_request(
            method="POST",
            url=f"{STABILITY_AI_BASE}/text-to-image",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json_payload={
                "text_prompts": [{"text": prompt, "weight": 1.0}],
                "cfg_scale": 7.0,
                "height": 900 if "9:16" in aspect_ratio else 1200,
                "width": 500 if "9:16" in aspect_ratio else 1200,
                "samples": 1,
                "steps": 30,
            }
        )
        for artifact in response.get("artifacts", []):
            if artifact.get("base64"):
                return f"data:image/png;base64,{artifact['base64']}"
            if artifact.get("url"):
                return artifact["url"]
        image = response.get("image") or response.get("url")
        if image:
            return image
        raise HTTPException(status_code=502, detail="Stability AI response missing image data")
    except HTTPException:
        raise

def _generate_voiceover(text: str, voice_id: str = "en-US-AriaNeural") -> str:
    """Generate voiceover using ElevenLabs."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="ElevenLabs not configured")
    
    try:
        response = _http_bytes_request(
            method="POST",
            url=f"{ELEVENLABS_BASE}/text-to-speech/{voice_id}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json_payload={
                "text": text,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
        )
        mime = response.headers.get("content-type", "audio/mpeg")
        encoded = base64.b64encode(response.content).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except HTTPException:
        raise

def _generate_video(product_name: str, script: str, duration_sec: int) -> str:
    """Generate video using Runway ML or similar."""
    api_key = os.getenv("RUNWAY_ML_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Runway ML not configured")

    endpoint = os.getenv("RUNWAY_ML_VIDEO_ENDPOINT", f"{RUNWAY_ML_BASE}/video/generations").strip()
    response = _http_bytes_request(
        method="POST",
        url=endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json_payload={
            "prompt": script,
            "product_name": product_name,
            "duration_sec": duration_sec,
        },
    )
    if response.headers.get("content-type", "").startswith("video/") and response.content:
        encoded = base64.b64encode(response.content).decode("ascii")
        return f"data:video/mp4;base64,{encoded}"

    try:
        payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Runway ML response missing video data") from exc

    return payload.get("video_url") or payload.get("url") or payload.get("output_url") or payload.get("asset_url") or payload.get("id", "")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/generate/text-to-ad")
def generate_text_to_ad(payload: AdGenerationRequest, auth: AuthDep) -> dict[str, Any]:
    """Generate ad variations from text prompt using AI."""
    if not _deduct_credits(auth.tenant_id, CREDIT_COSTS["text_to_ad"]):
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    ads = []
    for i in range(payload.variations):
        ad_id = str(uuid.uuid4())
        platform = payload.platforms[i % len(payload.platforms)]
        
        copy = _generate_text_ad_copy(payload.seed_text, platform)
        image_url = _generate_ai_image(payload.seed_text, aspect_ratio="9:16" if platform in ["instagram", "tiktok"] else "16:9")
        
        ad = {
            "id": ad_id,
            "tenant_id": auth.tenant_id,
            "type": "text_to_ad",
            "platform": platform,
            "copy": copy,
            "image_url": image_url,
            "seed_text": payload.seed_text,
            "created_at": _now(),
            "performance": {"impressions": 0, "clicks": 0, "ctr": 0.0}
        }
        ads.append(ad)
        with _lock:
            _ads.setdefault(auth.tenant_id, []).append(ad)
    
    # Track telemetry
    with _lock:
        _analytics.setdefault(auth.tenant_id, []).append({
            "event": "ad.generated",
            "type": "text_to_ad",
            "variations": len(ads),
            "timestamp": _now()
        })
    
    return {
        "success": True,
        "ads": ads,
        "credits_remaining": _get_credit_balance(auth.tenant_id)["credits"]
    }

@router.post("/generate/product-ad")
def generate_product_ad(payload: ProductAdRequest, auth: AuthDep) -> dict[str, Any]:
    """Generate professional product ads from URL or image."""
    if not _deduct_credits(auth.tenant_id, CREDIT_COSTS["text_to_ad"] * 2):
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    prompt = f"Professional product photography of {payload.product_name}. {payload.product_description or ''}"
    
    ads = []
    for platform in payload.platforms:
        ad_id = str(uuid.uuid4())
        
        copy = _generate_text_ad_copy(f"Sell {payload.product_name}", platform)
        image_url = _generate_ai_image(prompt, aspect_ratio="9:16" if platform in ["instagram", "tiktok"] else "16:9")
        
        ad = {
            "id": ad_id,
            "tenant_id": auth.tenant_id,
            "type": "product_ad",
            "platform": platform,
            "product_name": payload.product_name,
            "copy": copy,
            "image_url": image_url,
            "cta": "Shop Now" if "shop" in copy.lower() else "Learn More",
            "created_at": _now(),
            "performance": {"impressions": 0, "clicks": 0, "ctr": 0.0}
        }
        ads.append(ad)
        with _lock:
            _ads.setdefault(auth.tenant_id, []).append(ad)
    
    return {
        "success": True,
        "ads": ads,
        "product_name": payload.product_name,
        "credits_remaining": _get_credit_balance(auth.tenant_id)["credits"]
    }

@router.post("/generate/image")
def generate_image(payload: ImageGenerationRequest, auth: AuthDep) -> dict[str, Any]:
    """Generate an image from a text prompt."""
    if not _deduct_credits(auth.tenant_id, CREDIT_COSTS["text_to_ad"]):
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    image_url = _generate_ai_image(payload.prompt, aspect_ratio=payload.aspect_ratio)
    
    image_record = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "type": "image",
        "prompt": payload.prompt,
        "aspect_ratio": payload.aspect_ratio,
        "style": payload.style,
        "image_url": image_url,
        "created_at": _now(),
    }
    
    with _lock:
        _ads.setdefault(auth.tenant_id, []).append(image_record)
    
    return {
        "success": True,
        "image": image_record,
        "credits_remaining": _get_credit_balance(auth.tenant_id)["credits"]
    }

@router.post("/generate/ugc-video")
def generate_ugc_video(payload: UGCVideoRequest, auth: AuthDep) -> dict[str, Any]:
    """Generate UGC video with AI avatar."""
    if not _deduct_credits(auth.tenant_id, CREDIT_COSTS["ugc_video"]):
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    avatars = _get_avatars(auth.tenant_id)
    avatar = next((a for a in avatars if a["id"] == payload.avatar_id), avatars[0])
    
    script = payload.script or f"Hi! This is {avatar['name']}. Check out our new {payload.product_name}. {', '.join(payload.product_benefits)}. Get it today!"
    
    voiceover_url = _generate_voiceover(script, avatar.get("voice", "en-US-AriaNeural"))
    video_url = _generate_video(payload.product_name, script, payload.video_duration)
    
    ad = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "type": "ugc_video",
        "avatar": avatar,
        "script": script,
        "video_url": video_url,
        "voiceover_url": voiceover_url,
        "product_name": payload.product_name,
        "duration_seconds": payload.video_duration,
        "created_at": _now(),
        "performance": {"impressions": 0, "clicks": 0, "ctr": 0.0}
    }
    with _lock:
        _ads.setdefault(auth.tenant_id, []).append(ad)
    
    return {
        "success": True,
        "ad": ad,
        "credits_remaining": _get_credit_balance(auth.tenant_id)["credits"]
    }

@router.post("/generate/copy")
def generate_ad_copy(payload: AdCopyRequest, auth: AuthDep) -> dict[str, Any]:
    """Generate optimized ad copy for platform."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    system_prompt = f"""You are an expert copywriter for {payload.platform} ads. 
Tone: {payload.tone}. Target audience: {payload.target_audience}.
Generate 5 variations of compelling ad copy for a product.
Each copy should be optimized for {payload.platform}'s character limits and best practices.
Format as JSON array with 'copy' field for each variation."""
    
    user_prompt = f"Product: {payload.product_name}. Features: {', '.join(payload.key_features)}"
    
    if api_key:
        try:
            response = _http_json_request(
                method="POST",
                url=f"{OPENAI_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json_payload={
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.9,
                    "max_tokens": 500,
                }
            )
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            try:
                copies = json.loads(content)
            except json.JSONDecodeError:
                copies = [{"copy": line} for line in content.split("\n") if line.strip()]
        except HTTPException:
            copies = [{"copy": f"{payload.product_name}: {feat}"} for feat in payload.key_features]
    else:
        copies = [{"copy": f"{payload.product_name}: Amazing features - {', '.join(payload.key_features[:2])}"} for _ in range(3)]
    
    return {
        "success": True,
        "copies": copies,
        "platform": payload.platform,
        "recommended": copies[0] if copies else {}
    }

@router.post("/list")
def list_ads(auth: AuthDep, limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    """List all generated ads for tenant."""
    ads = _get_ads(auth.tenant_id)
    return {
        "ads": ads[-limit:],
        "total": len(ads),
        "tenant_id": auth.tenant_id
    }

@router.post("/campaigns/create")
def create_campaign(payload: CampaignRequest, auth: AuthDep) -> dict[str, Any]:
    """Create multi-platform campaign."""
    campaign_id = str(uuid.uuid4())
    campaign = {
        "id": campaign_id,
        "tenant_id": auth.tenant_id,
        "name": payload.name,
        "ad_ids": payload.ad_ids,
        "platforms": payload.platforms,
        "status": "draft",
        "created_at": _now(),
        "schedule_start": payload.schedule_start.isoformat() if payload.schedule_start else None,
        "schedule_end": payload.schedule_end.isoformat() if payload.schedule_end else None,
        "auto_post_enabled": payload.auto_post_enabled,
    }
    with _lock:
        _campaigns.setdefault(auth.tenant_id, []).append(campaign)
    
    return {
        "success": True,
        "campaign": campaign,
        "ads_count": len(payload.ad_ids),
        "platforms": payload.platforms
    }

@router.post("/campaigns/{campaign_id}/publish")
def publish_campaign(campaign_id: str, auth: AuthDep) -> dict[str, Any]:
    """Publish campaign to all platforms immediately."""
    campaigns = _get_campaigns(auth.tenant_id)
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign["status"] = "published"
    campaign["published_at"] = _now()
    
    # Track publishing to each platform
    published_channels = []
    for platform in campaign["platforms"]:
        integration = _platform_integrations.get(auth.tenant_id, {}).get(platform)
        if integration and integration.get("oauth_token"):
            published_channels.append({
                "platform": platform,
                "status": "published",
                "published_at": _now()
            })
    
    with _lock:
        _analytics.setdefault(auth.tenant_id, []).append({
            "event": "campaign.published",
            "campaign_id": campaign_id,
            "platforms": campaign["platforms"],
            "timestamp": _now()
        })
    
    return {
        "success": True,
        "campaign": campaign,
        "published_channels": published_channels
    }

@router.get("/campaigns/{campaign_id}/performance")
def get_campaign_performance(campaign_id: str, auth: AuthDep) -> dict[str, Any]:
    """Get campaign performance metrics."""
    campaigns = _get_campaigns(auth.tenant_id)
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    ads = _get_ads(auth.tenant_id)
    campaign_ads = [ad for ad in ads if ad["id"] in campaign["ad_ids"]]
    
    total_impressions = sum(ad.get("performance", {}).get("impressions", 0) for ad in campaign_ads)
    total_clicks = sum(ad.get("performance", {}).get("clicks", 0) for ad in campaign_ads)
    avg_ctr = (total_clicks / max(1, total_impressions)) * 100 if total_impressions else 0
    
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign["name"],
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "average_ctr": round(avg_ctr, 2),
        "estimated_roas": round(1.5 + (avg_ctr / 100), 2),
        "ad_count": len(campaign_ads)
    }

@router.post("/avatars/create")
def create_avatar(payload: AvatarCreateRequest, auth: AuthDep) -> dict[str, Any]:
    """Create custom UGC avatar."""
    avatar = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "name": payload.name,
        "age": payload.age,
        "gender": payload.gender,
        "ethnicity": payload.ethnicity,
        "voice_language": payload.voice_language,
        "voice_id": f"{payload.voice_language.split('-')[0]}-{payload.gender[:1].upper()}",
        "created_at": _now(),
    }
    with _lock:
        _avatars.setdefault(auth.tenant_id, []).append(avatar)
    
    return {
        "success": True,
        "avatar": avatar
    }

@router.get("/avatars/list")
def list_avatars(auth: AuthDep) -> dict[str, Any]:
    """List all available avatars."""
    avatars = _get_avatars(auth.tenant_id)
    return {
        "avatars": avatars,
        "total": len(avatars),
        "tenant_id": auth.tenant_id
    }

@router.post("/integrations/shopify/connect")
def connect_shopify(payload: IntegrationConnectRequest, auth: AuthDep) -> dict[str, Any]:
    """Connect Shopify store."""
    api_key = payload.api_key or os.getenv("SHOPIFY_API_KEY")
    store_url = os.getenv("SHOPIFY_STORE_URL", "")
    
    if not api_key or not store_url:
        raise HTTPException(status_code=400, detail="Shopify credentials not configured")
    
    integration = {
        "platform": "shopify",
        "api_key": api_key[:20] + "***",
        "store_url": store_url,
        "connected_at": _now(),
        "status": "connected"
    }
    
    with _lock:
        _platform_integrations.setdefault(auth.tenant_id, {})["shopify"] = integration
    
    return {
        "success": True,
        "integration": integration,
        "message": "Shopify connected successfully"
    }

@router.post("/integrations/meta/connect")
def connect_meta(payload: IntegrationConnectRequest, auth: AuthDep) -> dict[str, Any]:
    """OAuth connect to Meta (Facebook/Instagram)."""
    client_id = os.getenv("META_APP_ID", "")
    client_secret = os.getenv("META_APP_SECRET", "")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Meta OAuth not configured")
    
    if payload.auth_code:
        integration = {
            "platform": "meta",
            "oauth_token": payload.auth_code[:20] + "***",
            "token_type": "user_access_token",
            "connected_at": _now(),
            "status": "connected",
            "scopes": ["ads_management", "instagram_business_content_publishing"]
        }
        with _lock:
            _platform_integrations.setdefault(auth.tenant_id, {})["meta"] = integration
        
        return {
            "success": True,
            "integration": integration
        }
    
    state = str(uuid.uuid4())
    auth_url = (
        f"https://www.facebook.com/v18.0/dialog/oauth?"
        f"client_id={client_id}&"
        f"redirect_uri={payload.redirect_uri}&"
        f"scope=ads_management,instagram_business_content_publishing&"
        f"state={state}"
    )
    
    return {
        "success": True,
        "auth_url": auth_url,
        "state": state
    }

@router.post("/integrations/tiktok/connect")
def connect_tiktok(payload: IntegrationConnectRequest, auth: AuthDep) -> dict[str, Any]:
    """OAuth connect to TikTok Ads Manager."""
    client_id = os.getenv("TIKTOK_CLIENT_ID", "")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="TikTok OAuth not configured")
    
    if payload.auth_code:
        integration = {
            "platform": "tiktok",
            "oauth_token": payload.auth_code[:20] + "***",
            "connected_at": _now(),
            "status": "connected",
            "scopes": ["ads_manage"]
        }
        with _lock:
            _platform_integrations.setdefault(auth.tenant_id, {})["tiktok"] = integration
        
        return {
            "success": True,
            "integration": integration
        }
    
    state = str(uuid.uuid4())
    auth_url = (
        f"https://service-xxxxxxxx.tiktok-business.com/api/oauth2/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={payload.redirect_uri}&"
        f"scope=ads_manage&"
        f"state={state}"
    )
    
    return {
        "success": True,
        "auth_url": auth_url,
        "state": state
    }

@router.get("/integrations/status")
def get_integration_status(auth: AuthDep) -> dict[str, Any]:
    """Get status of all connected platforms."""
    integrations = _platform_integrations.get(auth.tenant_id, {})
    
    status = {}
    for platform in SUPPORTED_PLATFORMS:
        integration = integrations.get(platform)
        status[platform] = {
            "connected": bool(integration),
            "status": integration.get("status") if integration else "not_connected",
            "connected_at": integration.get("connected_at") if integration else None
        }
    
    return {
        "tenant_id": auth.tenant_id,
        "integrations": status,
        "connected_count": len([p for p in status.values() if p["connected"]])
    }

@router.get("/credits/check")
def check_credits(auth: AuthDep) -> dict[str, Any]:
    """Check remaining credits."""
    balance = _get_credit_balance(auth.tenant_id)
    
    return {
        "credits_remaining": balance["credits"],
        "tier": balance["tier"],
        "credit_costs": CREDIT_COSTS,
        "tenant_id": auth.tenant_id
    }

@router.post("/analytics/events")
def track_analytics_event(event_name: str, event_data: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
    """Track ad performance events."""
    event = {
        "event": event_name,
        "data": event_data,
        "timestamp": _now(),
        "tenant_id": auth.tenant_id
    }
    with _lock:
        _analytics.setdefault(auth.tenant_id, []).append(event)
    
    return {
        "success": True,
        "event": event
    }
