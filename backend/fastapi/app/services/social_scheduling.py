"""Social Scheduling Service

Extracted from legacy_main.py: Schedule, list, move, delete social posts.
"""

from __future__ import annotations

import os
from fastapi import Depends
from datetime import UTC, datetime
from typing import Annotated, TYPE_CHECKING, Literal

import psycopg

if TYPE_CHECKING:
    from ..deps import AuthContext

JsonObject = dict[str, object]
from ..deps import AuthContext, require_auth
AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Memory Store References (set by legacy_main.py) ──────────
_scheduled_posts_memory = []
_social_accounts_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores
_db_ready = False
_db_dsn_fn = None
_te_encrypt = None
_te_decrypt = None


def set_memory_stores(
    scheduled_posts_memory=None,
    social_accounts_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
    db_ready=None,
    db_dsn_fn=None,
    te_encrypt=None,
    te_decrypt=None,
) -> None:
    global _scheduled_posts_memory, _social_accounts_memory
    global _rate_buckets, _rate_lock, _enforce_rate_limit
    global _db_ready, _db_dsn_fn, _te_encrypt, _te_decrypt
    if scheduled_posts_memory is not None:
        _scheduled_posts_memory = scheduled_posts_memory
    if social_accounts_memory is not None:
        _social_accounts_memory = social_accounts_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit
    if db_ready is not None:
        _db_ready = db_ready
    if db_dsn_fn is not None:
        _db_dsn_fn = db_dsn_fn
    if te_encrypt is not None:
        _te_encrypt = te_encrypt
    if te_decrypt is not None:
        _te_decrypt = te_decrypt


# ── Social Scheduling ─────────────────────────────────────────


def schedule_social_post(payload: SocialScheduleRequest, auth: AuthDep) -> JsonObject:
    publish_at = payload.publish_at
    if publish_at.tzinfo is None:
        publish_at = publish_at.replace(tzinfo=UTC)

    if publish_at <= datetime.now(UTC):
        raise Exception('publish_at must be in the future.')

    media = [str(url) for url in payload.media_urls]
    text_cipher = _te_encrypt(payload.text)
    text_preview = payload.text[:50] + ('...' if len(payload.text) > 50 else '')

    if _db_ready:
        with psycopg.connect(_db_dsn_fn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO social_scheduled_posts (tenant_id, platform, text_cipher, text_preview, publish_at, media_urls)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (auth.tenant_id, payload.platform, text_cipher, text_preview, publish_at, media),
                )
                row = cur.fetchone()
                new_id = row[0] if row else len(_scheduled_posts_memory) + 1
            conn.commit()
    else:
        new_id = len(_scheduled_posts_memory) + 1

    item: JsonObject = {
        'id': new_id,
        'tenant_id': auth.tenant_id,
        'platform': payload.platform,
        'text': payload.text,
        'text_cipher': text_cipher,
        'text_preview': text_preview,
        'publish_at': publish_at.isoformat(),
        'media_urls': media,
        'status': 'scheduled',
        'created_at': datetime.now(UTC).isoformat(),
        'persistence': 'postgres' if _db_ready else 'memory-fallback',
        'encryption': 'application-level',
    }
    _scheduled_posts_memory.append(item)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'post': item}


def list_scheduled_posts(auth: AuthDep) -> JsonObject:
    items: list[JsonObject] = [
        p for p in _scheduled_posts_memory if p.get('tenant_id') == auth.tenant_id
    ]
    for p in items:
        p['text'] = _te_decrypt(p.get('text_cipher', '')) or p.get('text_preview', '***')
    items.sort(key=lambda x: x.get('publish_at', ''))
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'posts': items}


def move_scheduled_post(post_id: int, payload: SocialMoveRequest, auth: AuthDep) -> JsonObject:
    new_publish_at = payload.new_publish_at
    if new_publish_at.tzinfo is None:
        new_publish_at = new_publish_at.replace(tzinfo=UTC)

    if new_publish_at <= datetime.now(UTC):
        raise Exception('new_publish_at must be in the future.')

    if _db_ready:
        with psycopg.connect(_db_dsn_fn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE social_scheduled_posts
                    SET publish_at = %s, updated_at = NOW()
                    WHERE id = %s AND tenant_id = %s
                    RETURNING id
                    """,
                    (new_publish_at, post_id, auth.tenant_id),
                )
                row = cur.fetchone()
                if not row:
                    raise Exception('Scheduled post not found.')
            conn.commit()

    updated = False
    for p in _scheduled_posts_memory:
        if p.get('id') == post_id and p.get('tenant_id') == auth.tenant_id:
            p['publish_at'] = new_publish_at.isoformat()
            p['updated_at'] = datetime.now(UTC).isoformat()
            updated = True
            break

    if not updated:
        raise Exception('Scheduled post not found.')

    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'post_id': post_id, 'new_publish_at': new_publish_at.isoformat()}


def delete_scheduled_post(post_id: int, auth: AuthDep) -> JsonObject:
    if _db_ready:
        with psycopg.connect(_db_dsn_fn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM social_scheduled_posts WHERE id = %s AND tenant_id = %s",
                    (post_id, auth.tenant_id),
                )
                if cur.rowcount == 0:
                    raise Exception('Scheduled post not found.')
            conn.commit()

    before = len(_scheduled_posts_memory)
    _scheduled_posts_memory[:] = [
        p for p in _scheduled_posts_memory
        if not (p.get('id') == post_id and p.get('tenant_id') == auth.tenant_id)
    ]
    if len(_scheduled_posts_memory) == before:
        raise Exception('Scheduled post not found.')

    return {'status': 'ok', 'deleted_id': post_id}


# ── Request Models ────────────────────────────────────────────

from pydantic import BaseModel, Field, HttpUrl


class SocialScheduleRequest(BaseModel):
    platform: Literal['linkedin', 'x', 'instagram', 'facebook']
    text: str = Field(min_length=3, max_length=2200)
    publish_at: datetime
    media_urls: list[HttpUrl] = Field(default_factory=list, max_length=10)


class SocialMoveRequest(BaseModel):
    new_publish_at: datetime
