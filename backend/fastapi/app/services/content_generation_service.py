"""Content Generation Service (AI-powered)

Extracted from legacy_main.py: generate_content, generate_ads, analyze_seo.
These functions use the AI Gateway and media asset generation.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

import httpx
from fastapi import Depends
from pydantic import BaseModel, Field, HttpUrl

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]


class AiGatewayGenerateRequest(BaseModel):
    provider: Literal['auto', 'openai', 'anthropic', 'google_vertex'] = 'auto'
    prompt: str = Field(min_length=1, max_length=12000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=120)
    max_tokens: int = Field(default=500, ge=1, le=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    target_roi: float = Field(default=0.70, ge=0.0, le=20.0)
    value_per_1k_tokens: float = Field(default=0.006, ge=0.0001, le=50.0)
    quality_floor: float = Field(default=0.80, ge=0.0, le=1.0)

JsonObject = dict[str, object]

# ── Memory Store References (set by legacy_main.py) ──────────
_content_generations_memory = []
_rate_buckets = {}
_rate_lock = None
_enforce_rate_limit = None
_run_optional_ai_generation = None
_generate_media_asset_bundle = None
_json_object = dict
_content_generation_note_telemetry = None
_content_generation_strict_production_mode = None


def set_memory_stores(
    content_generations_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
    run_optional_ai_generation=None,
    generate_media_asset_bundle=None,
    json_object=None,
    content_generation_note_telemetry=None,
    content_generation_strict_production_mode=None,
) -> None:
    """Inject memory store references and helpers from legacy_main.py."""
    global _content_generations_memory, _rate_buckets, _rate_lock, _enforce_rate_limit
    global _run_optional_ai_generation, _generate_media_asset_bundle, _json_object
    global _content_generation_note_telemetry, _content_generation_strict_production_mode
    if content_generations_memory is not None:
        _content_generations_memory = content_generations_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit
    if run_optional_ai_generation is not None:
        _run_optional_ai_generation = run_optional_ai_generation
    if generate_media_asset_bundle is not None:
        _generate_media_asset_bundle = generate_media_asset_bundle
    if json_object is not None:
        _json_object = json_object
    if content_generation_note_telemetry is not None:
        _content_generation_note_telemetry = content_generation_note_telemetry
    if content_generation_strict_production_mode is not None:
        _content_generation_strict_production_mode = content_generation_strict_production_mode


# ── Helper: Platform Requirements ────────────────────────────


_PLATFORM_REQUIREMENTS: dict[str, list[str]] = {
    'instagram': ['image', 'video', 'story', 'reel', 'carousel', 'text'],
    'facebook': ['image', 'video', 'story', 'reel', 'text'],
    'youtube': ['video', 'short', 'text'],
    'tiktok': ['video', 'short', 'voice', 'text'],
    'linkedin': ['image', 'video', 'document', 'text'],
    'x': ['image', 'video', 'voice', 'text'],
    'threads': ['image', 'video', 'short', 'text'],
    'snapchat': ['image', 'video', 'story', 'short', 'text'],
    'pinterest': ['image', 'video', 'text'],
    'reddit': ['image', 'video', 'link', 'text'],
    'blog': ['image', 'video', 'long_text'],
}


def _get_platform_requirements(channel: str) -> list[str]:
    return _PLATFORM_REQUIREMENTS.get(channel, ['text'])


# ── Content Generation ────────────────────────────────────────


def generate_content(payload: ContentRequest, auth: AuthDep) -> JsonObject:
    platform_requirements = _get_platform_requirements(payload.channel)

    requested_formats = [item.strip().lower() for item in payload.target_formats if item.strip()]
    active_formats = platform_requirements
    if requested_formats:
        active_formats = sorted({*active_formats, *requested_formats})

    default_prompt = (
        f"Create high-converting {payload.channel} campaign assets for topic '{payload.topic}' targeting '{payload.audience}'. "
        f"Tone is {payload.tone}. Generate text post, image prompt, video script, voiceover script, reel script, and short-video script. "
        f"Respect platform requirements: {', '.join(active_formats)}."
    )
    ai_prompt = (payload.prompt or '').strip() or default_prompt
    ai_system_prompt = (payload.system_prompt or '').strip() or (
        'You are an expert social performance marketer. Return concise, production-ready outputs with clear headings for '
        'Text Post, Image Prompt, Video Script, Voiceover Script, Reel Script, Short Video Script, and CTA variants.'
    )

    ai_payload = AiGatewayGenerateRequest(
        provider=payload.provider,
        prompt=ai_prompt,
        system_prompt=ai_system_prompt,
        max_tokens=900,
        temperature=0.7,
    )

    created_at = datetime.now(UTC).isoformat()
    selected_provider, selected_model, ai_result, ai_text = _run_optional_ai_generation(ai_payload, auth, created_at)

    keywords = [payload.topic.lower().replace(' ', '-'), payload.audience.lower().replace(' ', '-'), 'nuxtron']
    if 'reel' in active_formats:
        keywords.append('reels')
    if 'short' in active_formats:
        keywords.append('shorts')
    hashtags = [f"#{item}" for item in keywords]
    fallback_headline = f"{payload.topic}: a {payload.tone} plan for {payload.audience}"
    fallback_body = (
        f"This {payload.channel} post is optimized for {payload.audience}. "
        f"Start with a strong hook about {payload.topic}, add one proof point, "
        "and finish with a clear call to action."
    )
    ai_lines = [line.strip(' -') for line in ai_text.splitlines() if line.strip()]
    headline = (ai_lines[0] if ai_lines else fallback_headline)[:120]
    body = ai_text or fallback_body
    media_bundle = _generate_media_asset_bundle(
        tenant_id=auth.tenant_id,
        prompt=ai_prompt,
        text_seed=body,
        requested_provider=payload.provider,
    )

    image_asset = _json_object(media_bundle.get('image', {})) or {}
    video_asset = _json_object(media_bundle.get('video', {})) or {}
    voice_asset = _json_object(media_bundle.get('voice', {})) or {}

    response: JsonObject = {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'channel': payload.channel,
        'tone': payload.tone,
        'headline': headline,
        'body': body,
        'hashtags': hashtags,
        'provider_used': str(ai_result.get('provider', selected_provider) or selected_provider),
        'model_used': str(ai_result.get('model', selected_model or '') or ''),
        'ai_status': 'generated' if ai_text else 'fallback',
        'platform_requirements': {
            'channel': payload.channel,
            'required_formats': active_formats,
            'all_social_accounts': _PLATFORM_REQUIREMENTS,
        },
        'outputs': {
            'text': body,
            'image_prompt': f"Product-focused {payload.channel} image concept for {payload.topic} targeting {payload.audience}.",
            'image_url': str(image_asset.get('download_url', '') or ''),
            'image_mime_type': str(image_asset.get('mime_type', '') or ''),
            'video_url': str(video_asset.get('download_url', '') or ''),
            'video_mime_type': str(video_asset.get('mime_type', '') or ''),
            'video_script': f"Hook: {headline}. Scene flow should prioritize product benefit and end with a sales CTA.",
            'voice_url': str(voice_asset.get('download_url', '') or ''),
            'voice_mime_type': str(voice_asset.get('mime_type', '') or ''),
            'voiceover_script': f"{headline}. {fallback_body}",
            'reel_script': f"Reel version: 3 fast cuts, clear hook, social proof, CTA for {payload.topic}.",
            'short_video_script': f"Short version: 15-30 seconds, one key outcome for {payload.audience}, strong CTA.",
        },
        'generated_assets': media_bundle,
    }

    if payload.include_seo:
        response['seo'] = {
            'meta_title': headline[:60],
            'meta_description': body[:155],
            'focus_keyword': payload.topic,
        }

    generation_id = f"cg-{uuid.uuid4().hex[:10]}"
    response['generation_id'] = generation_id
    response['generation_record'] = {
        'generation_id': generation_id,
        'tenant_id': auth.tenant_id,
        'topic': payload.topic,
        'audience': payload.audience,
        'channel': payload.channel,
        'tone': payload.tone,
        'headline': headline,
        'body': body,
        'generated_assets': media_bundle,
        'created_at': created_at,
    }

    fallback_assets = [
        _json_object(asset)
        for asset in (
            media_bundle.get('image', {}),
            media_bundle.get('voice', {}),
            media_bundle.get('video', {}),
        )
        if str(_json_object(asset).get('generation_status', 'generated')) != 'generated'
    ]
    for _ in fallback_assets:
        _content_generation_note_telemetry('fallback_attempts_total', 'media_fallback')

    strict_mode = _content_generation_strict_production_mode()
    response['production_mode'] = 'strict-real-generation' if strict_mode else 'best-effort'

    if strict_mode and not ai_text.strip():
        _content_generation_note_telemetry('strict_rejections_total', 'missing_ai_text')
        raise Exception('AI text generation returned no output in strict mode.')

    if strict_mode and fallback_assets:
        _content_generation_note_telemetry('strict_rejections_total', 'media_fallback')
        raise Exception(
            'Strict content generation mode rejected fallback media assets. Configure real providers for all modalities.'
        )

    _content_generations_memory.append(
        {
            'generation_id': generation_id,
            'tenant_id': auth.tenant_id,
            'topic': payload.topic,
            'audience': payload.audience,
            'channel': payload.channel,
            'tone': payload.tone,
            'headline': headline,
            'body': body,
            'generated_assets': media_bundle,
            'created_at': created_at,
            'response': response,
        }
    )

    return response


# ── Ads Generation ────────────────────────────────────────────


def generate_ads(payload: AdsRequest, auth: AuthDep) -> JsonObject:
    formats = sorted({'text', 'image', 'video', 'voice', 'reel', 'short', *[item.strip().lower() for item in payload.target_formats if item.strip()]})
    prompt = (payload.prompt or '').strip() or (
        f"Create ad assets for {payload.product} targeting {payload.audience} on {payload.platform}. "
        f"Objective: {payload.objective}. Include text ad copy, image prompt, video script, voiceover script, reel script, and short-video script."
    )
    system_prompt = (payload.system_prompt or '').strip() or (
        'You are an ad creative strategist. Focus on conversion-first output and platform-native formatting.'
    )

    ai_payload = AiGatewayGenerateRequest(
        provider=payload.provider,
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=900,
        temperature=0.7,
    )

    created_at = datetime.now(UTC).isoformat()
    selected_provider, selected_model, ai_result, ai_text = _run_optional_ai_generation(ai_payload, auth, created_at)

    media_bundle = _generate_media_asset_bundle(
        tenant_id=auth.tenant_id,
        prompt=prompt,
        text_seed=ai_text or f'{payload.product} for {payload.audience}',
        requested_provider=payload.provider,
    )

    image_asset = _json_object(media_bundle.get('image', {})) or {}
    video_asset = _json_object(media_bundle.get('video', {})) or {}
    voice_asset = _json_object(media_bundle.get('voice', {})) or {}

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'platform': payload.platform,
        'objective': payload.objective,
        'headlines': [
            f"{payload.product} for {payload.audience}",
            f"Scale {payload.objective} with {payload.product}",
            f"Built for {payload.audience}: {payload.product}",
        ],
        'descriptions': [
            f"Launch a {payload.platform} campaign focused on {payload.objective}.",
            'Use one offer, one proof point, and one frictionless CTA.',
        ],
        'cta': 'Start Free Trial',
        'provider_used': str(ai_result.get('provider', selected_provider) or selected_provider),
        'model_used': str(ai_result.get('model', selected_model or '') or ''),
        'ai_status': 'generated' if ai_text else 'fallback',
        'required_formats': formats,
        'outputs': {
            'text': ai_text or f"{payload.product} for {payload.audience}. Objective: {payload.objective}.",
            'image_prompt': f"High-conversion {payload.platform} ad visual for {payload.product} focused on {payload.objective}.",
            'image_url': str(image_asset.get('download_url', '') or ''),
            'image_mime_type': str(image_asset.get('mime_type', '') or ''),
            'video_script': f"15-30 second ad script for {payload.product} with a direct {payload.objective} CTA.",
            'video_url': str(video_asset.get('download_url', '') or ''),
            'video_mime_type': str(video_asset.get('mime_type', '') or ''),
            'voiceover_script': f"Discover {payload.product}. Built for {payload.audience}. Start now.",
            'voice_url': str(voice_asset.get('download_url', '') or ''),
            'voice_mime_type': str(voice_asset.get('mime_type', '') or ''),
            'reel_script': f"Reel cut for {payload.product}: hook, value proof, CTA in under 20 seconds.",
            'short_video_script': f"Short-form version for {payload.platform}: punchy hook, one proof, one CTA.",
        },
        'generated_assets': media_bundle,
    }


# ── SEO Analysis ──────────────────────────────────────────────


def analyze_seo(payload: SeoRequest, auth: AuthDep) -> JsonObject:
    content_lower = payload.content.lower()
    keyword_lower = payload.target_keyword.lower()
    keyword_count = content_lower.count(keyword_lower)
    word_count = len(payload.content.split())
    density = 0.0 if word_count == 0 else round((keyword_count / word_count) * 100, 2)

    score = 60
    checks = {
        'has_url': payload.url is not None,
        'keyword_present': keyword_count > 0,
        'good_length': 300 <= word_count <= 2000,
        'balanced_density': 0.5 <= density <= 2.5,
    }
    score += sum(10 for passed in checks.values() if passed)

    recommendations: list[str] = []
    if not checks['keyword_present']:
        recommendations.append('Add the target keyword in the first 100 words.')
    if not checks['good_length']:
        recommendations.append('Keep content length between 300 and 2000 words for stronger ranking signals.')
    if not checks['balanced_density']:
        recommendations.append('Adjust keyword frequency to keep density between 0.5% and 2.5%.')
    if not checks['has_url']:
        recommendations.append('Include canonical URL for complete on-page SEO checks.')

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'score': min(score, 100),
        'word_count': word_count,
        'keyword_count': keyword_count,
        'keyword_density_percent': density,
        'checks': checks,
        'recommendations': recommendations,
    }


# ── Request Models ────────────────────────────────────────────

class ContentRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=180)
    audience: str = Field(min_length=3, max_length=120)
    channel: Literal['linkedin', 'x', 'instagram', 'facebook', 'blog', 'tiktok', 'youtube', 'threads', 'snapchat', 'pinterest', 'reddit']
    tone: Literal['professional', 'casual', 'bold', 'friendly'] = 'professional'
    include_seo: bool = True
    prompt: str | None = Field(default=None, max_length=12000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    provider: Literal['auto', 'openai', 'anthropic', 'google_vertex'] = 'auto'
    target_formats: list[str] = Field(default_factory=list, max_length=16)


class AdsRequest(BaseModel):
    product: str = Field(min_length=2, max_length=140)
    audience: str = Field(min_length=2, max_length=120)
    platform: Literal['google', 'meta', 'linkedin', 'tiktok', 'instagram', 'youtube', 'facebook', 'x', 'threads', 'snapchat']
    objective: Literal['traffic', 'leads', 'sales', 'awareness']
    prompt: str | None = Field(default=None, max_length=12000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    provider: Literal['auto', 'openai', 'anthropic', 'google_vertex'] = 'auto'
    target_formats: list[str] = Field(default_factory=list, max_length=16)


class SeoRequest(BaseModel):
    url: HttpUrl | None = None
    target_keyword: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=20, max_length=10000)

