"""Social Workspace brand service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.persistence import _sw_load_profile_from_db
from ....domains.social.persistence import _sw_save_profile_to_db
from ....domains.social.schemas import BrandProfileRequest
from ....domains.social.schemas import UgcTemplateProfileRequest
from ..constants import AVATAR_PRESET_CATALOG
from ..constants import DEFAULT_BACKGROUND_MEDIA
from ..constants import DEFAULT_FONT_FAMILY
from ..constants import DEFAULT_SUBTITLES_LANGUAGE
from ..constants import JSON_CONTENT_TYPE
from ..constants import VOICEOVER_GLOBAL_LIBRARY
from ..constants import _DEFAULT_KEYWORDS
from .workspace import _normalized_text
from .workspace import _sw_http_error
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any
import httpx
import os


def _normalize_avatar_profile(source: dict[str, Any] | None) -> dict[str, str]:
    payload = source or {}
    mode = str(payload.get("mode") or "catalog").strip().lower()
    if mode not in {"catalog", "custom", "scratch"}:
        mode = "catalog"
    return {
        "mode": mode,
        "preset_id": str(payload.get("preset_id") or "").strip(),
        "name": str(payload.get("name") or "Creator").strip() or "Creator",
        "location": str(payload.get("location") or "").strip(),
        "ethnicity": str(payload.get("ethnicity") or "").strip(),
        "gender": str(payload.get("gender") or "").strip(),
        "age_range": str(payload.get("age_range") or "").strip(),
        "style": str(payload.get("style") or "").strip(),
        "face_type": str(payload.get("face_type") or "").strip(),
        "eye_style": str(payload.get("eye_style") or "").strip(),
        "body_shape": str(payload.get("body_shape") or "").strip(),
        "body_proportions": str(payload.get("body_proportions") or "").strip(),
    }


def _normalize_voiceover_engine(source: dict[str, Any] | None) -> dict[str, str]:
    payload = source or {}
    return {
        "language": str(payload.get("language") or "English").strip() or "English",
        "voice_name": str(payload.get("voice_name") or "").strip(),
        "style": str(payload.get("style") or "Narration").strip() or "Narration",
        "tone": str(payload.get("tone") or "Professional").strip() or "Professional",
        "accent": str(payload.get("accent") or "US").strip() or "US",
        "use_case": str(payload.get("use_case") or "Narration").strip() or "Narration",
    }


def _normalize_ugc_template_profile(source: dict[str, Any] | None) -> dict[str, Any]:
    payload = source or {}
    return {
        "style_category_id": _normalized_text(payload, "style_category_id", "no-discount-promo"),
        "preview_template_id": _normalized_text(payload, "preview_template_id", "tpl-value-story"),
        "caption_pack_id": _normalized_text(payload, "caption_pack_id", "ugc-main-launch"),
        "platform": _normalized_text(payload, "platform", "Instagram"),
        "objective": _normalized_text(payload, "objective", "Sales"),
        "hook_style": _normalized_text(payload, "hook_style", "Announcement"),
        "script_style": _normalized_text(payload, "script_style", "Storytelling"),
        "aspect_ratio": _normalized_text(payload, "aspect_ratio", "9:16"),
        "auto_adjust_platforms": bool(payload.get("auto_adjust_platforms", True)),
        "background_media": _normalized_text(payload, "background_media", DEFAULT_BACKGROUND_MEDIA),
        "subtitles_auto": bool(payload.get("subtitles_auto", True)),
        "subtitles_language": _normalized_text(payload, "subtitles_language", DEFAULT_SUBTITLES_LANGUAGE),
    }


def _sw_profile_defaults(st: _SocialWorkspaceState, tenant_id: str) -> dict[str, Any]:
    with st.lock:
        from_db = _sw_load_profile_from_db(st, tenant_id)
        if from_db:
            existing_memory = next(
                (profile for profile in st.brand_profiles if profile.get("tenant_id") == tenant_id), None
            )
            if existing_memory is None:
                from_db.setdefault("id", len(st.brand_profiles) + 1)
                st.brand_profiles.append(from_db)
            else:
                existing_memory.update(from_db)
                from_db = existing_memory
            from_db["avatar_profile"] = _normalize_avatar_profile(from_db.get("avatar_profile"))
            from_db["voiceover_engine"] = _normalize_voiceover_engine(from_db.get("voiceover_engine"))
            from_db["ugc_template_profile"] = _normalize_ugc_template_profile(from_db.get("ugc_template_profile"))
            return from_db
        existing = next((profile for profile in st.brand_profiles if profile.get("tenant_id") == tenant_id), None)
        if existing:
            existing["avatar_profile"] = _normalize_avatar_profile(existing.get("avatar_profile"))
            existing["voiceover_engine"] = _normalize_voiceover_engine(existing.get("voiceover_engine"))
            existing["ugc_template_profile"] = _normalize_ugc_template_profile(existing.get("ugc_template_profile"))
            return existing
        profile = {
            "id": len(st.brand_profiles) + 1,
            "tenant_id": tenant_id,
            "business_name": "Nuxtron Brand Studio",
            "industry": "marketing",
            "website": "https://nuxtron.local",
            "logo_url": None,
            "logo_dark_url": None,
            "description": "AI-assisted content operations for multi-channel growth teams.",
            "tone": "professional",
            "keywords": ["growth", "content ops"] + _DEFAULT_KEYWORDS,
            "hashtags": ["#growth", "#socialmedia", "#nuxtron"],
            "timezone": "UTC",
            "ethnicity": None,
            "voiceover": None,
            "avatar_profile": _normalize_avatar_profile(
                {
                    "mode": "catalog",
                    "preset_id": "ava-creator-01",
                    "name": "Mila Harper",
                    "ethnicity": "European",
                    "gender": "female",
                    "age_range": "25-34",
                    "style": "Modern Casual",
                    "face_type": "Oval",
                    "eye_style": "Almond",
                    "body_shape": "Athletic",
                    "body_proportions": "Balanced",
                    "location": "New York, US",
                }
            ),
            "voiceover_engine": _normalize_voiceover_engine(
                {
                    "language": "English",
                    "voice_name": "Liam",
                    "style": "Narration",
                    "tone": "Confident",
                    "accent": "US",
                    "use_case": "Narration",
                }
            ),
            "ugc_template_profile": _normalize_ugc_template_profile(
                {
                    "style_category_id": "no-discount-promo",
                    "preview_template_id": "tpl-value-story",
                    "caption_pack_id": "ugc-main-launch",
                    "platform": "Instagram",
                    "objective": "Sales",
                    "hook_style": "Announcement",
                    "script_style": "Storytelling",
                    "aspect_ratio": "9:16",
                    "auto_adjust_platforms": True,
                    "background_media": DEFAULT_BACKGROUND_MEDIA,
                    "subtitles_auto": True,
                    "subtitles_language": DEFAULT_SUBTITLES_LANGUAGE,
                }
            ),
            "brand_colors": ["#f8fafc", "#84cc16", "#93c5fd"],
            "title_font_family": DEFAULT_FONT_FAMILY,
            "subtitle_font_family": DEFAULT_FONT_FAMILY,
            "title_font_weight": "Regular",
            "subtitle_font_weight": "Regular",
            "title_case_type": "Auto",
            "subtitle_case_type": "Auto",
            "use_custom_font_title": False,
            "use_custom_font_subtitle": False,
            "custom_font_title": None,
            "custom_font_subtitle": None,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        st.brand_profiles.append(profile)
        _sw_save_profile_to_db(st, profile)
        return profile


def _ugc_http_json_request(
    method: str, url: str, headers: dict[str, str], json_payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Make HTTP request to UGC vendor API with timeout/error handling."""
    try:
        with httpx.Client(timeout=15.0) as client:
            if method.upper() == "GET":
                resp = client.get(url, headers=headers)
            elif method.upper() == "POST":
                resp = client.post(url, headers=headers, json=json_payload)
            else:
                raise _sw_http_error(status_code=502, detail="Unsupported HTTP method")
            if resp.status_code >= 400:
                raise _sw_http_error(status_code=502, detail=f"UGC vendor error: {resp.status_code}")
            return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError):
        raise _sw_http_error(status_code=504, detail="UGC discovery service timeout")
    except Exception as e:
        raise _sw_http_error(status_code=502, detail=f"UGC discovery service error: {str(e)}")


def _fetch_ugc_assets(brand_domain: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch UGC assets from external discovery API (production vendor integration)."""
    endpoint = os.getenv("UGC_DISCOVERY_ENDPOINT", "").strip()
    api_key = os.getenv("UGC_DISCOVERY_API_KEY", "").strip()
    if not endpoint or not api_key:
        raise _sw_http_error(status_code=503, detail="UGC discovery service not configured")
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": JSON_CONTENT_TYPE}
        payload = {
            "domain": brand_domain,
            "limit": limit,
            "include_sentiment": True,
            "include_engagement_metrics": True,
        }
        result = _ugc_http_json_request("POST", endpoint, headers, payload)
        if not isinstance(result.get("assets"), list):
            raise _sw_http_error(status_code=502, detail="UGC vendor response missing assets list")
        assets: list[dict[str, Any]] = []
        for item in result.get("assets", []):
            asset = {
                "id": len(assets) + 1,
                "network": item.get("platform", "instagram"),
                "author": item.get("author_handle", "unknown"),
                "author_followers": item.get("author_followers", 0),
                "media_type": item.get("media_type", "image"),
                "caption": item.get("caption", ""),
                "media_url": item.get("media_url"),
                "thumbnail_url": item.get("thumbnail_url"),
                "engagement": item.get("engagement_count", 0),
                "sentiment": item.get("sentiment", "neutral"),
                "rights_status": "pending",
                "approved": None,
                "tags": item.get("tags", []),
                "created_at": datetime.now(UTC).isoformat(),
            }
            assets.append(asset)
        return assets
    except HTTPException:
        raise
    except Exception as e:
        raise _sw_http_error(status_code=502, detail=f"UGC fetch failed: {str(e)}")


def _sw_seed_ugc(st: _SocialWorkspaceState, tenant_id: str) -> None:
    """Load UGC assets from production vendor API (fail-closed)."""
    with st.lock:
        if any((item.get("tenant_id") == tenant_id for item in st.ugc_assets)):
            return
    try:
        assets = _fetch_ugc_assets(brand_domain=f"{tenant_id}.example.com", limit=20)
        with st.lock:
            for asset in assets:
                asset["tenant_id"] = tenant_id
                st.ugc_assets.append(asset)
    except HTTPException:
        raise
    except Exception:
        raise _sw_http_error(status_code=503, detail="UGC discovery service unavailable")


def _sw_avatar_catalog(tenant_id: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "presets": AVATAR_PRESET_CATALOG,
        "ethnicities": sorted({item["ethnicity"] for item in AVATAR_PRESET_CATALOG}),
        "genders": sorted({item["gender"] for item in AVATAR_PRESET_CATALOG}),
        "styles": sorted({item["style"] for item in AVATAR_PRESET_CATALOG}),
        "face_types": sorted({item["face_type"] for item in AVATAR_PRESET_CATALOG}),
        "eye_styles": sorted({item["eye_style"] for item in AVATAR_PRESET_CATALOG}),
        "body_shapes": sorted({item["body_shape"] for item in AVATAR_PRESET_CATALOG}),
        "body_proportions": sorted({item["body_proportions"] for item in AVATAR_PRESET_CATALOG}),
        "age_ranges": sorted({item["age_range"] for item in AVATAR_PRESET_CATALOG}),
    }


def _sw_voiceover_catalog(tenant_id: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "voices": VOICEOVER_GLOBAL_LIBRARY,
        "languages": sorted({str(item["language"]) for item in VOICEOVER_GLOBAL_LIBRARY}),
        "accents": sorted({str(item["accent"]) for item in VOICEOVER_GLOBAL_LIBRARY}),
        "styles": sorted({str(item["style"]) for item in VOICEOVER_GLOBAL_LIBRARY}),
        "tones": sorted({str(item["tone"]) for item in VOICEOVER_GLOBAL_LIBRARY}),
        "use_cases": ["Narration", "Presentation", "Tutorial", "Character Dialogue"],
    }


def _sw_build_brand_fields(payload: BrandProfileRequest, profile: dict[str, Any]) -> dict[str, Any]:
    avatar_profile = _normalize_avatar_profile(
        payload.avatar_profile if isinstance(payload.avatar_profile, dict) else profile.get("avatar_profile")
    )
    voiceover_engine = _normalize_voiceover_engine(
        payload.voiceover_engine if isinstance(payload.voiceover_engine, dict) else profile.get("voiceover_engine")
    )
    ugc_template_profile = _normalize_ugc_template_profile(
        payload.ugc_template_profile
        if isinstance(payload.ugc_template_profile, dict)
        else profile.get("ugc_template_profile")
    )
    return {
        "business_name": payload.business_name.strip(),
        "industry": payload.industry.strip(),
        "website": payload.website,
        "logo_url": payload.logo_url,
        "logo_dark_url": payload.logo_dark_url,
        "description": payload.description,
        "tone": payload.tone.strip(),
        "keywords": [keyword.strip() for keyword in payload.keywords if keyword.strip()],
        "hashtags": [tag.strip() for tag in payload.hashtags if tag.strip()],
        "timezone": payload.timezone.strip() or "UTC",
        "ethnicity": payload.ethnicity.strip() if payload.ethnicity else None,
        "voiceover": payload.voiceover.strip() if payload.voiceover else voiceover_engine.get("voice_name") or None,
        "avatar_profile": avatar_profile,
        "voiceover_engine": voiceover_engine,
        "ugc_template_profile": ugc_template_profile,
        "brand_colors": [color.strip() for color in payload.brand_colors if color.strip()][:12],
        "title_font_family": payload.title_font_family.strip() or DEFAULT_FONT_FAMILY,
        "subtitle_font_family": payload.subtitle_font_family.strip() or DEFAULT_FONT_FAMILY,
        "title_font_weight": payload.title_font_weight.strip() or "Regular",
        "subtitle_font_weight": payload.subtitle_font_weight.strip() or "Regular",
        "title_case_type": payload.title_case_type.strip() or "Auto",
        "subtitle_case_type": payload.subtitle_case_type.strip() or "Auto",
        "use_custom_font_title": bool(payload.use_custom_font_title),
        "use_custom_font_subtitle": bool(payload.use_custom_font_subtitle),
        "custom_font_title": payload.custom_font_title.strip() if payload.custom_font_title else None,
        "custom_font_subtitle": payload.custom_font_subtitle.strip() if payload.custom_font_subtitle else None,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _sw_update_brand_profile(st: _SocialWorkspaceState, payload: BrandProfileRequest, tenant_id: str) -> dict[str, Any]:
    with st.lock:
        profile = next((item for item in st.brand_profiles if item.get("tenant_id") == tenant_id), None)
        if profile is None:
            profile = {"id": len(st.brand_profiles) + 1, "tenant_id": tenant_id}
            st.brand_profiles.append(profile)
        profile.update(_sw_build_brand_fields(payload, profile))
        updated = profile.copy()
    _sw_save_profile_to_db(st, updated)
    _sw_audit(st, tenant_id, "social_brand_profile_updated", updated["id"])
    return {"status": "ok", "tenant_id": tenant_id, "brand_profile": updated}


def _sw_update_ugc_template(
    st: _SocialWorkspaceState, payload: UgcTemplateProfileRequest, tenant_id: str
) -> dict[str, Any]:
    profile = _sw_profile_defaults(st, tenant_id)
    with st.lock:
        profile["ugc_template_profile"] = _normalize_ugc_template_profile(
            {
                "style_category_id": payload.style_category_id,
                "preview_template_id": payload.preview_template_id,
                "caption_pack_id": payload.caption_pack_id,
                "platform": payload.platform,
                "objective": payload.objective,
                "hook_style": payload.hook_style,
                "script_style": payload.script_style,
                "aspect_ratio": payload.aspect_ratio,
                "auto_adjust_platforms": payload.auto_adjust_platforms,
                "background_media": payload.background_media,
                "subtitles_auto": payload.subtitles_auto,
                "subtitles_language": payload.subtitles_language,
            }
        )
        profile["updated_at"] = datetime.now(UTC).isoformat()
        updated = profile.copy()
    _sw_save_profile_to_db(st, updated)
    _sw_audit(st, tenant_id, "social_ugc_template_profile_updated", updated.get("id"))
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "ugc_template_profile": updated["ugc_template_profile"],
        "brand_profile": updated,
    }
