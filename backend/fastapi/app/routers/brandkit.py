# pyright: reportUnusedFunction=false
"""
Brand Kit router — Simplified-parity centralised brand management hub.

Endpoints
---------
GET    /brand-kit                           – Fetch full brand kit (or auto-create default)
PATCH  /brand-kit/colors                   – Update color palette
PATCH  /brand-kit/fonts                    – Update font settings
PATCH  /brand-kit/logos                    – Update logo URLs
PATCH  /brand-kit/voice                    – Update brand voice / tone
PATCH  /brand-kit/messaging                – Update key messaging (tagline, value prop, elevator pitch)
PATCH  /brand-kit/writing-rules            – Update writing style rules (use/avoid terms)
GET    /brand-kit/knowledge-base           – List knowledge-base entries
POST   /brand-kit/knowledge-base           – Add entry (URL or text snippet)
DELETE /brand-kit/knowledge-base/{entry_id} – Remove entry
POST   /brand-kit/generate-preview         – Generate on-brand AI content preview
GET    /brand-kit/analytics                – Usage analytics (generations using the kit)
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/brand-kit", tags=["Brand Kit"])

# ---------------------------------------------------------------------------
# In-memory store  (keyed by tenant_id)
# ---------------------------------------------------------------------------

_lock = threading.Lock()

_DEFAULT_KIT: dict[str, Any] = {
    "colors": {
        "primary": "#3B82F6",
        "secondary": "#22C55E",
        "accent": "#A855F7",
        "background": "#0D1117",
        "text": "#ECEDEE",
        "muted": "#8A92A4",
    },
    "fonts": {
        "heading": {"family": "Inter", "weight": "700", "size_px": 32},
        "body": {"family": "Inter", "weight": "400", "size_px": 16},
        "display": {"family": "Inter", "weight": "800", "size_px": 48},
    },
    "logos": {
        "main": "",
        "icon": "",
        "dark_variant": "",
        "light_variant": "",
    },
    "voice": {
        "tone_preset": "professional",  # professional | friendly | bold | playful | witty | custom
        "custom_description": "",
        "formality": "neutral",   # formal | neutral | casual
        "emotion": "confident",   # confident | empathetic | energetic | calm
    },
    "messaging": {
        "brand_name": "",
        "tagline": "",
        "value_proposition": "",
        "elevator_pitch": "",
        "target_audience": "",
    },
    "writing_rules": {
        "terms_to_use": [],
        "terms_to_avoid": [],
        "preferred_sentences": "short",  # short | medium | long
        "use_oxford_comma": True,
        "capitalize_brand_name": True,
        "notes": "",
    },
}

_kits: dict[str, dict[str, Any]] = {}
_knowledge_bases: dict[str, list[dict[str, Any]]] = {}
_analytics: dict[str, dict[str, Any]] = {}


def _get_kit(tenant_id: str) -> dict[str, Any]:
    """Return kit, auto-initialising from default template."""
    import copy

    with _lock:
        if tenant_id not in _kits:
            _kits[tenant_id] = copy.deepcopy(_DEFAULT_KIT)
            _kits[tenant_id]["tenant_id"] = tenant_id
            _kits[tenant_id]["created_at"] = datetime.now(UTC).isoformat()
            _kits[tenant_id]["updated_at"] = datetime.now(UTC).isoformat()
        return _kits[tenant_id]


def _touch(tenant_id: str) -> None:
    with _lock:
        if tenant_id in _kits:
            _kits[tenant_id]["updated_at"] = datetime.now(UTC).isoformat()


def _record_generation(tenant_id: str, content_type: str) -> None:
    with _lock:
        if tenant_id not in _analytics:
            _analytics[tenant_id] = {
                "total_generations": 0,
                "by_type": {},
                "last_generated_at": None,
            }
        _analytics[tenant_id]["total_generations"] += 1
        _analytics[tenant_id]["by_type"].setdefault(content_type, 0)
        _analytics[tenant_id]["by_type"][content_type] += 1
        _analytics[tenant_id]["last_generated_at"] = datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ColorPatch(BaseModel):
    primary: str | None = None
    secondary: str | None = None
    accent: str | None = None
    background: str | None = None
    text: str | None = None
    muted: str | None = None


class FontSpec(BaseModel):
    family: str | None = None
    weight: str | None = None
    size_px: int | None = None


class FontsPatch(BaseModel):
    heading: FontSpec | None = None
    body: FontSpec | None = None
    display: FontSpec | None = None


class LogosPatch(BaseModel):
    main: str | None = None
    icon: str | None = None
    dark_variant: str | None = None
    light_variant: str | None = None


class VoicePatch(BaseModel):
    tone_preset: str | None = Field(None, description="professional | friendly | bold | playful | witty | custom")
    custom_description: str | None = None
    formality: str | None = Field(None, description="formal | neutral | casual")
    emotion: str | None = Field(None, description="confident | empathetic | energetic | calm")


class MessagingPatch(BaseModel):
    brand_name: str | None = None
    tagline: str | None = None
    value_proposition: str | None = None
    elevator_pitch: str | None = None
    target_audience: str | None = None


class WritingRulesPatch(BaseModel):
    terms_to_use: list[str] | None = None
    terms_to_avoid: list[str] | None = None
    preferred_sentences: str | None = Field(None, description="short | medium | long")
    use_oxford_comma: bool | None = None
    capitalize_brand_name: bool | None = None
    notes: str | None = None


class KnowledgeBaseEntryCreate(BaseModel):
    entry_type: str = Field(..., description="url | text | pdf_title")
    content: str = Field(..., description="URL or text snippet")
    label: str = Field("", description="Human-readable label")


class GeneratePreviewRequest(BaseModel):
    content_type: str = Field(
        "social_caption",
        description="social_caption | blog_intro | ad_copy | email_subject | tagline_variant",
    )
    topic: str = Field("", description="Optional topic or product to write about")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TONE_ADVERB_MAP: dict[str, str] = {
    "professional": "authoritatively and professionally",
    "friendly": "in a warm and approachable manner",
    "bold": "with bold conviction",
    "playful": "playfully and with wit",
    "witty": "with sharp wit and clever wordplay",
    "custom": "in the brand's unique custom voice",
}

CONTENT_TEMPLATES: dict[str, str] = {
    "social_caption": (
        "Write a compelling social media caption {tone_phrase} for {brand_name}. "
        "Topic: {topic}. Tagline: {tagline}. Max 280 chars."
    ),
    "blog_intro": (
        "Write a 3-sentence blog introduction {tone_phrase} for {brand_name}. "
        "Topic: {topic}. Value proposition: {value_prop}."
    ),
    "ad_copy": (
        "Write a 25-word ad headline and 40-word body copy {tone_phrase} for {brand_name}. "
        "Target audience: {audience}. Topic: {topic}."
    ),
    "email_subject": (
        "Generate 3 A/B test email subject lines {tone_phrase} for {brand_name}. "
        "Topic: {topic}. Max 60 chars each."
    ),
    "tagline_variant": (
        "Generate 5 tagline variants {tone_phrase} for {brand_name}. "
        "Current tagline: {tagline}. Value prop: {value_prop}."
    ),
}

PREVIEW_SAMPLES: dict[str, list[str]] = {
    "social_caption": [
        "🚀 {brand_name} just changed the game. Built for growth. Powered by AI. Your audience won't know what hit them. #GrowthMindset",
        "Stop guessing. Start winning. {brand_name} gives you the data, the tools, and the edge you need. Ready?",
        "Your next 1,000 followers aren't going to find you by accident. Let {brand_name} lead them to you. ✨",
    ],
    "blog_intro": [
        "The content landscape has never moved faster—and most brands are sprinting to keep up. At {brand_name}, we believe speed and quality aren't mutually exclusive. Here's how smart teams are publishing more, worrying less, and winning bigger.",
        "Every great brand has a story worth telling. The challenge is finding the time, the words, and the right moment to tell it. That's where {brand_name} comes in.",
    ],
    "ad_copy": [
        "Headline: Scale Without Limits\nBody: {brand_name} automates your content pipeline so you can focus on what actually moves the needle. Less busywork. More growth.",
        "Headline: Your Brand Voice, Amplified\nBody: Every post, ad, and email—perfectly on-brand, every time. {brand_name} makes consistency effortless.",
    ],
    "email_subject": [
        "Your competitors are already using this…",
        "3 things {brand_name} does that your current stack can't",
        "[New] Scale your content 10× without hiring anyone",
    ],
    "tagline_variant": [
        "Create More. Stress Less.",
        "One Platform. Total Control.",
        "Your Brand, Always On.",
        "Built for Growth. Designed for You.",
        "Ship Great Content. Consistently.",
    ],
}


def _fill_template(template_key: str, kit: dict[str, Any], topic: str) -> str:
    msg = kit.get("messaging", {})
    voice = kit.get("voice", {})
    brand_name = msg.get("brand_name") or "Your Brand"
    tagline = msg.get("tagline") or "powered by AI"
    value_prop = msg.get("value_proposition") or "the best platform for growth"
    audience = msg.get("target_audience") or "marketers and creators"
    tone_phrase = TONE_ADVERB_MAP.get(voice.get("tone_preset", "professional"), "professionally")

    import random

    samples = PREVIEW_SAMPLES.get(template_key, ["Generated content goes here."])
    base = random.choice(samples)  # noqa: S311  # non-cryptographic
    return base.format(
        brand_name=brand_name,
        tagline=tagline,
        value_prop=value_prop,
        audience=audience,
        tone_phrase=tone_phrase,
        topic=topic or "your product",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def get_brand_kit(auth: AuthDep) -> dict[str, Any]:
    """Return the full brand kit for this tenant, auto-creating defaults."""
    kit = _get_kit(auth.tenant_id)
    kb = _get_kb(auth.tenant_id)
    return {"brand_kit": {**kit, "knowledge_base_count": len(kb)}}


@router.patch("/colors")
async def patch_colors(body: ColorPatch, auth: AuthDep) -> dict[str, Any]:
    kit = _get_kit(auth.tenant_id)
    with _lock:
        for field, value in body.model_dump(exclude_none=True).items():
            kit["colors"][field] = value
    _touch(auth.tenant_id)
    return {"brand_kit": kit}


@router.patch("/fonts")
async def patch_fonts(body: FontsPatch, auth: AuthDep) -> dict[str, Any]:
    kit = _get_kit(auth.tenant_id)
    with _lock:
        for slot, spec in (body.model_dump(exclude_none=True)).items():
            if isinstance(spec, dict):
                for k, v in spec.items():
                    if v is not None:
                        kit["fonts"][slot][k] = v
    _touch(auth.tenant_id)
    return {"brand_kit": kit}


@router.patch("/logos")
async def patch_logos(body: LogosPatch, auth: AuthDep) -> dict[str, Any]:
    kit = _get_kit(auth.tenant_id)
    with _lock:
        for field, value in body.model_dump(exclude_none=True).items():
            kit["logos"][field] = value
    _touch(auth.tenant_id)
    return {"brand_kit": kit}


@router.patch("/voice")
async def patch_voice(body: VoicePatch, auth: AuthDep) -> dict[str, Any]:
    valid_presets = {"professional", "friendly", "bold", "playful", "witty", "custom"}
    if body.tone_preset and body.tone_preset not in valid_presets:
        raise HTTPException(status_code=422, detail=f"tone_preset must be one of {sorted(valid_presets)}")
    kit = _get_kit(auth.tenant_id)
    with _lock:
        for field, value in body.model_dump(exclude_none=True).items():
            kit["voice"][field] = value
    _touch(auth.tenant_id)
    return {"brand_kit": kit}


@router.patch("/messaging")
async def patch_messaging(body: MessagingPatch, auth: AuthDep) -> dict[str, Any]:
    kit = _get_kit(auth.tenant_id)
    with _lock:
        for field, value in body.model_dump(exclude_none=True).items():
            kit["messaging"][field] = value
    _touch(auth.tenant_id)
    return {"brand_kit": kit}


@router.patch("/writing-rules")
async def patch_writing_rules(body: WritingRulesPatch, auth: AuthDep) -> dict[str, Any]:
    kit = _get_kit(auth.tenant_id)
    with _lock:
        for field, value in body.model_dump(exclude_none=True).items():
            kit["writing_rules"][field] = value
    _touch(auth.tenant_id)
    return {"brand_kit": kit}


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

def _get_kb(tenant_id: str) -> list[dict[str, Any]]:
    with _lock:
        return _knowledge_bases.setdefault(tenant_id, [])


@router.get("/knowledge-base")
async def list_knowledge_base(auth: AuthDep) -> dict[str, Any]:
    entries = _get_kb(auth.tenant_id)
    return {"entries": list(entries), "total": len(entries)}


@router.post("/knowledge-base", status_code=201)
async def add_knowledge_base_entry(body: KnowledgeBaseEntryCreate, auth: AuthDep) -> dict[str, Any]:
    valid_types = {"url", "text", "pdf_title"}
    if body.entry_type not in valid_types:
        raise HTTPException(status_code=422, detail=f"entry_type must be one of {sorted(valid_types)}")
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="content must not be empty")

    entry: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "entry_type": body.entry_type,
        "content": body.content.strip(),
        "label": body.label.strip() or body.content.strip()[:60],
        "created_at": datetime.now(UTC).isoformat(),
        "status": "indexed",
    }
    with _lock:
        _knowledge_bases.setdefault(auth.tenant_id, []).append(entry)
    return {"entry": entry}


@router.delete("/knowledge-base/{entry_id}", status_code=200)
async def delete_knowledge_base_entry(entry_id: str, auth: AuthDep) -> dict[str, Any]:
    with _lock:
        entries = _knowledge_bases.setdefault(auth.tenant_id, [])
        original = len(entries)
        _knowledge_bases[auth.tenant_id] = [e for e in entries if e["id"] != entry_id]
        removed = original - len(_knowledge_bases[auth.tenant_id])
    if removed == 0:
        raise HTTPException(status_code=404, detail="Knowledge base entry not found")
    return {"deleted": entry_id}


# ---------------------------------------------------------------------------
# AI Preview Generation
# ---------------------------------------------------------------------------

@router.post("/generate-preview")
async def generate_preview(body: GeneratePreviewRequest, auth: AuthDep) -> dict[str, Any]:
    valid_types = set(CONTENT_TEMPLATES.keys())
    if body.content_type not in valid_types:
        raise HTTPException(status_code=422, detail=f"content_type must be one of {sorted(valid_types)}")

    kit = _get_kit(auth.tenant_id)
    preview_text = _fill_template(body.content_type, kit, body.topic)
    _record_generation(auth.tenant_id, body.content_type)

    writing_rules = kit.get("writing_rules", {})
    terms_to_use = writing_rules.get("terms_to_use", [])
    terms_to_avoid = writing_rules.get("terms_to_avoid", [])

    compliance: dict[str, Any] = {
        "uses_required_terms": [t for t in terms_to_use if t.lower() in preview_text.lower()],
        "avoids_banned_terms": all(t.lower() not in preview_text.lower() for t in terms_to_avoid),
        "brand_name_present": bool(kit.get("messaging", {}).get("brand_name")),
        "tone_applied": kit.get("voice", {}).get("tone_preset", "professional"),
    }

    return {
        "preview": {
            "content_type": body.content_type,
            "topic": body.topic,
            "generated_text": preview_text,
            "brand_kit_snapshot": {
                "tone": kit.get("voice", {}).get("tone_preset"),
                "brand_name": kit.get("messaging", {}).get("brand_name"),
                "primary_color": kit.get("colors", {}).get("primary"),
                "heading_font": kit.get("fonts", {}).get("heading", {}).get("family"),
            },
            "compliance_check": compliance,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics")
async def get_analytics(auth: AuthDep) -> dict[str, Any]:
    with _lock:
        data = _analytics.get(auth.tenant_id, {
            "total_generations": 0,
            "by_type": {},
            "last_generated_at": None,
        })
    kit = _get_kit(auth.tenant_id)
    kb = _get_kb(auth.tenant_id)
    return {
        "analytics": {
            **data,
            "kit_completeness": _kit_completeness(kit),
            "knowledge_base_entries": len(kb),
            "colors_configured": bool(kit.get("colors", {}).get("primary")),
            "fonts_configured": bool(kit.get("fonts", {}).get("heading", {}).get("family")),
            "logos_configured": bool(kit.get("logos", {}).get("main")),
            "voice_configured": kit.get("voice", {}).get("tone_preset") != "professional"
            or bool(kit.get("voice", {}).get("custom_description")),
            "messaging_configured": bool(kit.get("messaging", {}).get("tagline")),
        }
    }


def _kit_completeness(kit: dict[str, Any]) -> int:
    """Return 0-100 completeness score."""
    checks = [
        bool(kit.get("colors", {}).get("primary")),
        bool(kit.get("fonts", {}).get("heading", {}).get("family")),
        bool(kit.get("logos", {}).get("main")),
        bool(kit.get("voice", {}).get("tone_preset")),
        bool(kit.get("messaging", {}).get("brand_name")),
        bool(kit.get("messaging", {}).get("tagline")),
        bool(kit.get("messaging", {}).get("value_proposition")),
        bool(kit.get("writing_rules", {}).get("terms_to_use")),
    ]
    return round((sum(1 for c in checks if c) / len(checks)) * 100)
