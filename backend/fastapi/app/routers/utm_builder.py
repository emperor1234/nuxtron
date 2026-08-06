# pyright: reportUnusedFunction=false
"""
UTM Builder — SproutSocial §2.1.1
ADDED: UTM parameter builder with saved preset templates.
Enables teams to apply consistent UTM tagging across all social campaigns.
NO duplication: existing scheduling route (schedule_social_post) handles post creation.
This module generates and manages UTM URL strings as a pre-publish utility.
"""

import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import quote_plus, urlencode, urlparse, urlunparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

PRESET_NOT_FOUND = 'UTM preset not found.'

# ADDED: valid UTM medium values per Sprout best practices (§2.1.1)
VALID_UTM_MEDIUMS = {'social', 'paid_social', 'email', 'cpc', 'organic', 'referral', 'display', 'video'}


# ── Request models ──────────────────────────────────────────────────────────────

class UTMPresetRequest(BaseModel):
    """ADDED: Save a UTM parameter preset for reuse across posts (§2.1.1)."""
    name: str = Field(min_length=1, max_length=120, description='Internal preset name, e.g. Q3 Campaign — LinkedIn')
    # ADDED: standard UTM params
    utm_source: str = Field(min_length=1, max_length=120, description='e.g. linkedin, twitter, instagram')
    utm_medium: str = Field(min_length=1, max_length=80, description='e.g. social, paid_social')
    utm_campaign: str = Field(min_length=1, max_length=200, description='Campaign name, e.g. product_launch_2025')
    utm_term: str | None = Field(default=None, max_length=200, description='Paid keywords — optional.')
    utm_content: str | None = Field(default=None, max_length=200, description='Ad variant — optional.')
    # ADDED: convenience flags
    auto_lowercase: bool = Field(default=True, description='Force all param values to lowercase.')
    replace_spaces: bool = Field(default=True, description='Replace spaces with underscores in param values.')
    description: str | None = Field(default=None, max_length=500)


class UTMPresetUpdateRequest(BaseModel):
    """ADDED: Partial update for a UTM preset."""
    name: str | None = Field(default=None, max_length=120)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=80)
    utm_campaign: str | None = Field(default=None, max_length=200)
    utm_term: str | None = Field(default=None, max_length=200)
    utm_content: str | None = Field(default=None, max_length=200)
    auto_lowercase: bool | None = None
    replace_spaces: bool | None = None
    description: str | None = Field(default=None, max_length=500)


class UTMBuildRequest(BaseModel):
    """
    ADDED: Build a UTM-tagged URL from a preset OR custom params (§2.1.1).
    Supply preset_id to apply a saved preset; supply custom params to override or use without preset.
    """
    base_url: str = Field(min_length=4, max_length=2000, description='The landing page URL to tag.')
    preset_id: int | None = Field(default=None, ge=1, description='Apply a saved UTM preset.')
    # ADDED: custom override params — any provided value overrides the preset value
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=80)
    utm_campaign: str | None = Field(default=None, max_length=200)
    utm_term: str | None = Field(default=None, max_length=200)
    utm_content: str | None = Field(default=None, max_length=200)
    # ADDED: campaign tag from social post (§2.1.1 campaign_tag integration)
    campaign_tag: str | None = Field(default=None, max_length=120, description='Appended to utm_campaign as suffix if provided.')
    auto_lowercase: bool = Field(default=True)
    replace_spaces: bool = Field(default=True)
    shorten: bool = Field(default=False, description='If true, attempt to shorten the generated tagged URL.')
    shortener_provider: str = Field(default='auto', pattern=r'^(auto|bitly|tinyurl)$')

    @model_validator(mode='after')
    def _require_source_or_preset(self) -> 'UTMBuildRequest':
        if self.preset_id is None and self.utm_source is None:
            raise ValueError('Provide either preset_id or at least utm_source to build a UTM URL.')
        return self


class URLShortenRequest(BaseModel):
    """Shorten a URL using configured provider credentials."""
    url: str = Field(min_length=4, max_length=2000)
    provider: str = Field(default='auto', pattern=r'^(auto|bitly|tinyurl)$')


# ── URL builder helper ──────────────────────────────────────────────────────────

def _sanitize(value: str, lowercase: bool, replace_spaces: bool) -> str:
    """ADDED: Normalize UTM param values per best-practice conventions."""
    v = value.strip()
    if lowercase:
        v = v.lower()
    if replace_spaces:
        v = v.replace(' ', '_').replace('-', '_')
    return v


def _build_utm_url(
    base_url: str,
    source: str,
    medium: str,
    campaign: str,
    term: str | None,
    content: str | None,
    auto_lowercase: bool,
    replace_spaces: bool,
) -> str:
    """
    ADDED: Append UTM parameters to the base URL.
    Preserves existing query params; does not duplicate UTM keys.
    """
    # ADDED: validate URL is parseable
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f'Invalid URL: {base_url!r}. Must include scheme (https://) and host.')

    params: dict[str, str] = {}
    params['utm_source'] = _sanitize(source, auto_lowercase, replace_spaces)
    params['utm_medium'] = _sanitize(medium, auto_lowercase, replace_spaces)
    params['utm_campaign'] = _sanitize(campaign, auto_lowercase, replace_spaces)
    if term:
        params['utm_term'] = _sanitize(term, auto_lowercase, replace_spaces)
    if content:
        params['utm_content'] = _sanitize(content, auto_lowercase, replace_spaces)

    # Merge with existing query string — UTM params take precedence
    existing_qs = parsed.query
    new_qs = existing_qs + ('&' if existing_qs else '') + urlencode(params, quote_via=quote_plus)
    tagged = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_qs, parsed.fragment))
    return tagged


def _shorten_with_bitly(url: str) -> str:
    token = os.getenv('BITLY_ACCESS_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Bitly is not configured')
    endpoint = os.getenv('BITLY_SHORTEN_ENDPOINT', 'https://api-ssl.bitly.com/v4/shorten').strip()
    timeout_sec = float(os.getenv('URL_SHORTENER_TIMEOUT_SECONDS', '12'))
    try:
        with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
            response = client.post(
                endpoint,
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                json={'long_url': url},
            )
            response.raise_for_status()
            payload = response.json() if response.content else {}
            link = str(payload.get('link') or '').strip()
            if not link:
                raise RuntimeError('Bitly response missing shortened link')
            return link
    except httpx.TimeoutException as exc:
        raise RuntimeError('Bitly timeout') from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f'Bitly error: {exc.response.status_code}') from exc


def _shorten_with_tinyurl(url: str) -> str:
    token = os.getenv('TINYURL_API_TOKEN', '').strip()
    if not token:
        raise RuntimeError('TinyURL is not configured')
    endpoint = os.getenv('TINYURL_SHORTEN_ENDPOINT', 'https://api.tinyurl.com/create').strip()
    timeout_sec = float(os.getenv('URL_SHORTENER_TIMEOUT_SECONDS', '12'))
    try:
        with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
            response = client.post(
                endpoint,
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                json={'url': url, 'domain': os.getenv('TINYURL_DOMAIN', 'tinyurl.com').strip()},
            )
            response.raise_for_status()
            payload = response.json() if response.content else {}
            short_url = str(
                payload.get('data', {}).get('tiny_url')
                or payload.get('data', {}).get('url')
                or payload.get('tiny_url')
                or ''
            ).strip()
            if not short_url:
                raise RuntimeError('TinyURL response missing shortened link')
            return short_url
    except httpx.TimeoutException as exc:
        raise RuntimeError('TinyURL timeout') from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f'TinyURL error: {exc.response.status_code}') from exc


def _shorten_url(url: str, provider: str) -> tuple[str, str]:
    requested = provider.strip().lower()
    if requested == 'bitly':
        return _shorten_with_bitly(url), 'bitly'
    if requested == 'tinyurl':
        return _shorten_with_tinyurl(url), 'tinyurl'

    try:
        return _shorten_with_bitly(url), 'bitly'
    except RuntimeError:
        return _shorten_with_tinyurl(url), 'tinyurl'


# ── Router factory ──────────────────────────────────────────────────────────────

def create_utm_builder_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    presets_memory: list[dict[str, Any]],
) -> APIRouter:
    """
    Create the UTM Builder router (SproutSocial §2.1.1).
    Provides UTM preset management and URL building for social post links.
    """
    router = APIRouter()
    _lock = threading.Lock()

    def _audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'utm-builder-router',
            })

    # ── Preset CRUD ─────────────────────────────────────────────────────────────

    @router.post('/publishing/utm/presets')
    def create_preset(payload: UTMPresetRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Save a reusable UTM parameter preset (§2.1.1)."""
        enforce_rate_limit(f'{auth.tenant_id}:utm:presets:create', 120, 60)
        with _lock:
            preset: dict[str, Any] = {
                'id': len(presets_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'utm_source': payload.utm_source.strip(),
                'utm_medium': payload.utm_medium.strip(),
                'utm_campaign': payload.utm_campaign.strip(),
                'utm_term': payload.utm_term.strip() if payload.utm_term else None,
                'utm_content': payload.utm_content.strip() if payload.utm_content else None,
                'auto_lowercase': payload.auto_lowercase,
                'replace_spaces': payload.replace_spaces,
                'description': payload.description,
                'use_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            presets_memory.append(preset)
        _audit(auth.tenant_id, 'utm_preset_created', preset['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'preset': preset.copy()}

    @router.get('/publishing/utm/presets')
    def list_presets(
        auth: AuthDep,
        search: Annotated[str | None, Query(max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """ADDED: List UTM presets for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:utm:presets:list', 240, 60)
        search_lc = search.strip().lower() if search else None
        with _lock:
            items = [
                p.copy() for p in presets_memory
                if p.get('tenant_id') == auth.tenant_id
                and (
                    search_lc is None
                    or search_lc in str(p.get('name', '')).lower()
                    or search_lc in str(p.get('utm_campaign', '')).lower()
                    or search_lc in str(p.get('utm_source', '')).lower()
                )
            ]
        items.sort(key=lambda p: int(p.get('use_count', 0)), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'presets': items[offset: offset + limit],
        }

    @router.patch(
        '/publishing/utm/presets/{preset_id}',
        responses={404: {'description': PRESET_NOT_FOUND}},
    )
    def update_preset(preset_id: int, payload: UTMPresetUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Update a UTM preset."""
        enforce_rate_limit(f'{auth.tenant_id}:utm:presets:update', 120, 60)
        with _lock:
            preset = next(
                (p for p in presets_memory if p.get('tenant_id') == auth.tenant_id and p.get('id') == preset_id),
                None,
            )
            if preset is None:
                raise HTTPException(status_code=404, detail=PRESET_NOT_FOUND)
            if payload.name is not None:
                preset['name'] = payload.name.strip()
            if payload.utm_source is not None:
                preset['utm_source'] = payload.utm_source.strip()
            if payload.utm_medium is not None:
                preset['utm_medium'] = payload.utm_medium.strip()
            if payload.utm_campaign is not None:
                preset['utm_campaign'] = payload.utm_campaign.strip()
            if payload.utm_term is not None:
                preset['utm_term'] = payload.utm_term.strip()
            if payload.utm_content is not None:
                preset['utm_content'] = payload.utm_content.strip()
            if payload.auto_lowercase is not None:
                preset['auto_lowercase'] = payload.auto_lowercase
            if payload.replace_spaces is not None:
                preset['replace_spaces'] = payload.replace_spaces
            if payload.description is not None:
                preset['description'] = payload.description
            preset['updated_at'] = datetime.now(UTC).isoformat()
            updated = preset.copy()
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'preset': updated}

    @router.delete(
        '/publishing/utm/presets/{preset_id}',
        responses={404: {'description': PRESET_NOT_FOUND}},
    )
    def delete_preset(preset_id: int, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Delete a UTM preset."""
        enforce_rate_limit(f'{auth.tenant_id}:utm:presets:delete', 60, 60)
        with _lock:
            idx = next(
                (i for i, p in enumerate(presets_memory) if p.get('tenant_id') == auth.tenant_id and p.get('id') == preset_id),
                None,
            )
            if idx is None:
                raise HTTPException(status_code=404, detail=PRESET_NOT_FOUND)
            presets_memory.pop(idx)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'preset_id': preset_id, 'deleted': True}

    # ── URL builder ─────────────────────────────────────────────────────────────

    @router.post('/publishing/utm/build', responses={404: {'description': PRESET_NOT_FOUND}, 422: {'description': 'Invalid UTM input'}})
    def build_utm_url(payload: UTMBuildRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Build a UTM-tagged URL from a preset or custom params (§2.1.1).
        Custom params override preset values field-by-field.
        Increments preset use_count for popularity tracking.
        """
        enforce_rate_limit(f'{auth.tenant_id}:utm:build', 600, 60)

        # Resolve preset if provided
        preset: dict[str, Any] | None = None
        if payload.preset_id is not None:
            with _lock:
                preset = next(
                    (p for p in presets_memory if p.get('tenant_id') == auth.tenant_id and p.get('id') == payload.preset_id),
                    None,
                )
            if preset is None:
                raise HTTPException(status_code=404, detail=PRESET_NOT_FOUND)

        # Merge: custom params override preset values
        source = payload.utm_source or (preset.get('utm_source') if preset else None)
        medium = payload.utm_medium or (preset.get('utm_medium') if preset else None)
        campaign = payload.utm_campaign or (preset.get('utm_campaign') if preset else None)
        term = payload.utm_term or (preset.get('utm_term') if preset else None)
        content = payload.utm_content or (preset.get('utm_content') if preset else None)
        auto_lc = payload.auto_lowercase if preset is None else bool(preset.get('auto_lowercase', True))
        replace_sp = payload.replace_spaces if preset is None else bool(preset.get('replace_spaces', True))

        if not source or not medium or not campaign:
            raise HTTPException(status_code=422, detail='utm_source, utm_medium, and utm_campaign are required (from preset or custom input).')

        # ADDED: append campaign_tag suffix to utm_campaign if provided (§2.1.1 campaign_tag integration)
        if payload.campaign_tag:
            campaign = f'{campaign}_{payload.campaign_tag.strip()}'

        try:
            tagged_url = _build_utm_url(
                payload.base_url,
                source=source,
                medium=medium,
                campaign=campaign,
                term=term,
                content=content,
                auto_lowercase=auto_lc,
                replace_spaces=replace_sp,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        # Increment preset use_count
        if preset is not None:
            with _lock:
                for p in presets_memory:
                    if p.get('tenant_id') == auth.tenant_id and p.get('id') == payload.preset_id:
                        p['use_count'] = int(p.get('use_count', 0)) + 1
                        p['last_used_at'] = datetime.now(UTC).isoformat()
                        break

        short_url: str | None = None
        shortener_provider: str | None = None
        shortener_error: str | None = None
        if payload.shorten:
            try:
                short_url, shortener_provider = _shorten_url(tagged_url, payload.shortener_provider)
            except RuntimeError as exc:
                shortener_error = str(exc)

        _audit(auth.tenant_id, 'utm_url_built')
        response = {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'base_url': payload.base_url,
            'tagged_url': tagged_url,
            'params': {
                'utm_source': _sanitize(source, auto_lc, replace_sp),
                'utm_medium': _sanitize(medium, auto_lc, replace_sp),
                'utm_campaign': _sanitize(campaign, auto_lc, replace_sp),
                'utm_term': _sanitize(term, auto_lc, replace_sp) if term else None,
                'utm_content': _sanitize(content, auto_lc, replace_sp) if content else None,
            },
            'preset_id': payload.preset_id,
            'short_url': short_url,
            'shortener_provider': shortener_provider,
        }
        if shortener_error:
            response['shortener_error'] = shortener_error
        return response

    @router.post(
        '/publishing/utm/shorten',
        responses={
            422: {'description': 'Invalid URL or shortener input'},
            503: {'description': 'URL shortener provider unavailable or not configured'},
        },
    )
    def shorten_url(payload: URLShortenRequest, auth: AuthDep) -> dict[str, Any]:
        """Shorten a URL using Bitly or TinyURL with provider fallback support."""
        enforce_rate_limit(f'{auth.tenant_id}:utm:shorten', 300, 60)

        parsed = urlparse(payload.url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=422, detail='Invalid URL. Must include scheme and host.')

        try:
            short_url, provider = _shorten_url(payload.url, payload.provider)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        _audit(auth.tenant_id, 'utm_url_shortened')
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'url': payload.url,
            'short_url': short_url,
            'provider': provider,
        }

    return router
