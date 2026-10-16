"""Social Workspace brand service."""

from datetime import UTC, datetime
from typing import Any

from ....domains.social.persistence import (
    _SocialWorkspaceState,
    _sw_audit,
    _sw_load_profile_from_db,
    _sw_save_profile_to_db,
)
from ....domains.social.schemas import BrandProfileRequest, UgcTemplateProfileRequest
from ..constants import (
    AVATAR_PRESET_CATALOG,
    DEFAULT_BACKGROUND_MEDIA,
    DEFAULT_FONT_FAMILY,
    DEFAULT_SUBTITLES_LANGUAGE,
    VOICEOVER_GLOBAL_LIBRARY,
)
from .workspace import _normalized_text


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
            "business_name": "",
            "industry": "",
            "website": "",
            "logo_url": None,
            "logo_dark_url": None,
            "description": "",
            "tone": "professional",
            "keywords": [],
            "hashtags": [],
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
            "brand_colors": [],
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
