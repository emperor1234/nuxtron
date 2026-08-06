# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportMissingTypeArgument=false, reportUnusedFunction=false

import base64
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, HttpUrl

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
CONTENT_TYPE_JSON = 'application/json'
StoreItem = dict[str, object]
StoreList = list[StoreItem]


class MeilisearchIndexRequest(BaseModel):
    index: str = Field(min_length=1, max_length=80)
    document_id: str = Field(min_length=1, max_length=120)
    document: dict[str, object] = Field(default_factory=dict)


class MeilisearchQueryRequest(BaseModel):
    index: str = Field(min_length=1, max_length=80)
    query: str = Field(min_length=1, max_length=400)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    filter: str | None = Field(default=None, max_length=400)


class RedisCacheSetRequest(BaseModel):
    key: str = Field(min_length=1, max_length=512)
    value: str = Field(min_length=0, max_length=65536)
    ttl_seconds: int = Field(default=3600, ge=1, le=2592000)


class RedisCacheGetRequest(BaseModel):
    key: str = Field(min_length=1, max_length=512)


class RedisCacheDeleteRequest(BaseModel):
    key: str = Field(min_length=1, max_length=512)


class RedisCacheFlushPrefixRequest(BaseModel):
    prefix: str = Field(min_length=1, max_length=256)


class TwilioSendSmsRequest(BaseModel):
    to: str = Field(min_length=7, max_length=20)
    body: str = Field(min_length=1, max_length=1600)
    from_number: str | None = Field(default=None, max_length=20)


class TwilioMakeCallRequest(BaseModel):
    to: str = Field(min_length=7, max_length=20)
    twiml_url: HttpUrl
    from_number: str | None = Field(default=None, max_length=20)


class SlackSendMessageRequest(BaseModel):
    channel: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)
    username: str = Field(default='Nuxtron', max_length=80)
    icon_emoji: str = Field(default=':robot_face:', max_length=40)
    blocks: list[dict[str, object]] = Field(default_factory=list)


class SlackWebhookMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    blocks: list[dict[str, object]] = Field(default_factory=list)


class ResendSendEmailRequest(BaseModel):
    to_email: str = Field(min_length=5, max_length=320)
    subject: str = Field(min_length=1, max_length=300)
    html: str | None = Field(default=None, max_length=25000)
    text: str | None = Field(default=None, max_length=10000)
    from_email: str | None = Field(default=None, max_length=320)


class AlgoliaIndexObjectRequest(BaseModel):
    index_name: str = Field(min_length=1, max_length=128)
    object_id: str = Field(min_length=1, max_length=256)
    document: dict[str, object]


class AlgoliaQueryRequest(BaseModel):
    index_name: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=0, max_length=200)
    page: int = Field(default=0, ge=0, le=100)
    hits_per_page: int = Field(default=20, ge=1, le=100)


def _handle_search_index_document(
    *,
    payload: MeilisearchIndexRequest,
    auth: AuthContext,
    meilisearch_index_memory: list[dict[str, object]],
    append_bounded: Callable[[list[dict[str, object]], dict[str, object]], None],
) -> dict[str, object]:
    host = os.getenv('MEILISEARCH_HOST', '').rstrip('/')
    api_key = os.getenv('MEILISEARCH_API_KEY', '').strip()
    tenant_index = f'{auth.tenant_id}__{payload.index}'
    doc: dict[str, object] = {**payload.document, 'id': payload.document_id, '_tenant_id': auth.tenant_id}

    if not host:
        record: dict[str, object] = {
            'id': len(meilisearch_index_memory) + 1,
            'tenant_id': auth.tenant_id,
            'index': tenant_index,
            'document_id': payload.document_id,
            'document': doc,
            'status': 'queued',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(meilisearch_index_memory, record)
        return {'status': 'ok', 'result': record}

    headers: dict[str, str] = {'Content-Type': CONTENT_TYPE_JSON}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f'{host}/indexes/{tenant_index}/documents',
                headers=headers,
                json=[doc],
            )
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'index': tenant_index,
                        'document_id': payload.document_id,
                        'delivery_status': 'indexed',
                        'response_status': response.status_code,
                    },
                }
    except Exception:
        record: dict[str, object] = {
            'id': len(meilisearch_index_memory) + 1,
            'tenant_id': auth.tenant_id,
            'index': tenant_index,
            'document_id': payload.document_id,
            'document': doc,
            'status': 'queued-after-error',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(meilisearch_index_memory, record)
        return {'status': 'ok', 'result': record}

    record: dict[str, object] = {
        'id': len(meilisearch_index_memory) + 1,
        'tenant_id': auth.tenant_id,
        'index': tenant_index,
        'document_id': payload.document_id,
        'document': doc,
        'status': 'queued-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    append_bounded(meilisearch_index_memory, record)
    return {'status': 'ok', 'result': record}


def _handle_search_query(
    *,
    payload: MeilisearchQueryRequest,
    auth: AuthContext,
    meilisearch_index_memory: list[dict],
) -> dict:
    host = os.getenv('MEILISEARCH_HOST', '').rstrip('/')
    api_key = os.getenv('MEILISEARCH_API_KEY', '').strip()
    tenant_index = f'{auth.tenant_id}__{payload.index}'

    if not host:
        q = payload.query.lower()
        hits = [
            r['document']
            for r in meilisearch_index_memory
            if r.get('tenant_id') == auth.tenant_id
            and r.get('index') == tenant_index
            and q in str(r.get('document', '')).lower()
        ]
        page = hits[payload.offset: payload.offset + payload.limit]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'index': tenant_index,
            'query': payload.query,
            'hits': page,
            'total_hits': len(hits),
            'source': 'memory-fallback',
        }

    headers: dict[str, str] = {'Content-Type': CONTENT_TYPE_JSON}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    request_body: dict = {'q': payload.query, 'limit': payload.limit, 'offset': payload.offset}
    if payload.filter:
        request_body['filter'] = payload.filter

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f'{host}/indexes/{tenant_index}/search',
                headers=headers,
                json=request_body,
            )
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'index': tenant_index,
                    'query': payload.query,
                    'hits': data.get('hits', []),
                    'total_hits': data.get('estimatedTotalHits', 0),
                    'source': 'meilisearch',
                }
    except Exception:
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'index': tenant_index,
            'query': payload.query,
            'hits': [],
            'total_hits': 0,
            'source': 'error',
        }

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'index': tenant_index,
        'query': payload.query,
        'hits': [],
        'total_hits': 0,
        'source': 'meilisearch-non-success',
    }


def _register_meilisearch_routes(
    *,
    router: APIRouter,
    enforce_rate_limit: Callable[[str, int, int], None],
    meilisearch_index_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
) -> None:
    @router.post('/search/index-document')
    def search_index_document(payload: MeilisearchIndexRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:search:index', 120, 60)
        return _handle_search_index_document(
            payload=payload,
            auth=auth,
            meilisearch_index_memory=meilisearch_index_memory,
            append_bounded=append_bounded,
        )

    @router.post('/search/query')
    def search_query(payload: MeilisearchQueryRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:search:query', 180, 60)
        return _handle_search_query(
            payload=payload,
            auth=auth,
            meilisearch_index_memory=meilisearch_index_memory,
        )


def _handle_cache_set(
    *,
    payload: RedisCacheSetRequest,
    auth: AuthContext,
    redis_ops_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
    redis_key: Callable[[str, str], str],
    redis_client: Callable[[], object | None],
) -> dict:
    namespaced = redis_key(auth.tenant_id, payload.key)
    r = redis_client()
    if r is not None:
        try:
            r.setex(namespaced, payload.ttl_seconds, payload.value)
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'key': namespaced,
                'ttl_seconds': payload.ttl_seconds,
                'source': 'redis',
            }
        except Exception:
            pass

    record = {
        'id': len(redis_ops_memory) + 1,
        'tenant_id': auth.tenant_id,
        'op': 'set',
        'key': namespaced,
        'value': payload.value,
        'ttl_seconds': payload.ttl_seconds,
        'expires_at': datetime.fromtimestamp(time.time() + payload.ttl_seconds, tz=UTC).isoformat(),
        'created_at': datetime.now(UTC).isoformat(),
    }
    redis_ops_memory[:] = [
        e for e in redis_ops_memory
        if not (e.get('key') == namespaced and e.get('op') == 'set')
    ]
    append_bounded(redis_ops_memory, record)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'key': namespaced,
        'ttl_seconds': payload.ttl_seconds,
        'source': 'memory-fallback',
    }


def _handle_cache_get(
    *,
    payload: RedisCacheGetRequest,
    auth: AuthContext,
    redis_ops_memory: list[dict],
    redis_key: Callable[[str, str], str],
    redis_client: Callable[[], object | None],
) -> dict:
    namespaced = redis_key(auth.tenant_id, payload.key)
    r = redis_client()
    if r is not None:
        try:
            value = r.get(namespaced)
            ttl = r.ttl(namespaced)
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'key': namespaced,
                'value': value,
                'ttl_remaining': ttl,
                'found': value is not None,
                'source': 'redis',
            }
        except Exception:
            pass

    now = time.time()
    entry = next(
        (
            e for e in reversed(redis_ops_memory)
            if e.get('key') == namespaced
            and e.get('op') == 'set'
            and datetime.fromisoformat(e['expires_at']).timestamp() > now
        ),
        None,
    )
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'key': namespaced,
        'value': entry['value'] if entry else None,
        'found': entry is not None,
        'source': 'memory-fallback',
    }


def _handle_cache_delete(
    *,
    payload: RedisCacheDeleteRequest,
    auth: AuthContext,
    redis_ops_memory: list[dict],
    redis_key: Callable[[str, str], str],
    redis_client: Callable[[], object | None],
) -> dict:
    namespaced = redis_key(auth.tenant_id, payload.key)
    r = redis_client()
    if r is not None:
        try:
            deleted = r.delete(namespaced)
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'key': namespaced,
                'deleted': bool(deleted),
                'source': 'redis',
            }
        except Exception:
            pass

    before = len(redis_ops_memory)
    redis_ops_memory[:] = [e for e in redis_ops_memory if e.get('key') != namespaced]
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'key': namespaced,
        'deleted': len(redis_ops_memory) < before,
        'source': 'memory-fallback',
    }


def _handle_cache_flush_prefix(
    *,
    payload: RedisCacheFlushPrefixRequest,
    auth: AuthContext,
    redis_ops_memory: list[dict],
    redis_key: Callable[[str, str], str],
    redis_client: Callable[[], object | None],
) -> dict:
    namespaced_prefix = redis_key(auth.tenant_id, payload.prefix)
    r = redis_client()
    if r is not None:
        try:
            keys = list(r.scan_iter(f'{namespaced_prefix}*'))
            if keys:
                r.delete(*keys)
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'prefix': namespaced_prefix,
                'keys_deleted': len(keys),
                'source': 'redis',
            }
        except Exception:
            pass

    before = len(redis_ops_memory)
    redis_ops_memory[:] = [e for e in redis_ops_memory if not e.get('key', '').startswith(namespaced_prefix)]
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'prefix': namespaced_prefix,
        'keys_deleted': before - len(redis_ops_memory),
        'source': 'memory-fallback',
    }


def _register_cache_routes(
    *,
    router: APIRouter,
    enforce_rate_limit: Callable[[str, int, int], None],
    redis_ops_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
    redis_key: Callable[[str, str], str],
    redis_client: Callable[[], object | None],
) -> None:
    @router.post('/cache/set')
    def cache_set(payload: RedisCacheSetRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:cache:set', 300, 60)
        return _handle_cache_set(
            payload=payload,
            auth=auth,
            redis_ops_memory=redis_ops_memory,
            append_bounded=append_bounded,
            redis_key=redis_key,
            redis_client=redis_client,
        )

    @router.post('/cache/get')
    def cache_get(payload: RedisCacheGetRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:cache:get', 600, 60)
        return _handle_cache_get(
            payload=payload,
            auth=auth,
            redis_ops_memory=redis_ops_memory,
            redis_key=redis_key,
            redis_client=redis_client,
        )

    @router.post('/cache/delete')
    def cache_delete(payload: RedisCacheDeleteRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:cache:delete', 300, 60)
        return _handle_cache_delete(
            payload=payload,
            auth=auth,
            redis_ops_memory=redis_ops_memory,
            redis_key=redis_key,
            redis_client=redis_client,
        )

    @router.post('/cache/flush-prefix')
    def cache_flush_prefix(payload: RedisCacheFlushPrefixRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:cache:flush', 30, 60)
        return _handle_cache_flush_prefix(
            payload=payload,
            auth=auth,
            redis_ops_memory=redis_ops_memory,
            redis_key=redis_key,
            redis_client=redis_client,
        )


def _handle_twilio_send_sms(
    *,
    payload: TwilioSendSmsRequest,
    auth: AuthContext,
    twilio_messages_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
) -> dict:
    account_sid = os.getenv('TWILIO_ACCOUNT_SID', '').strip()
    auth_token = os.getenv('TWILIO_AUTH_TOKEN', '').strip()
    default_from = os.getenv('TWILIO_FROM_NUMBER', '').strip()
    api_base_url = os.getenv('TWILIO_API_BASE_URL', 'https://api.twilio.com').rstrip('/')
    from_number = (payload.from_number or default_from).strip()

    if not account_sid or not auth_token or not from_number:
        item = {
            'id': len(twilio_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'sms',
            'to': payload.to,
            'body_preview': payload.body[:60],
            'status': 'queued',
            'reason': 'Twilio not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(twilio_messages_memory, item)
        return {'status': 'ok', 'result': item}

    credentials = base64.b64encode(f'{account_sid}:{auth_token}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {credentials}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {'From': from_number, 'To': payload.to, 'Body': payload.body}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{api_base_url}/2010-04-01/Accounts/{account_sid}/Messages.json',
                headers=headers,
                data=data,
            )
            if response.is_success:
                rdata = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'type': 'sms',
                        'sid': rdata.get('sid'),
                        'to': payload.to,
                        'delivery_status': rdata.get('status', 'sent'),
                        'provider': 'twilio',
                    },
                }
            return {
                'status': 'ok',
                'result': {
                    'tenant_id': auth.tenant_id,
                    'type': 'sms',
                    'delivery_status': 'twilio-error',
                    'twilio_status': response.status_code,
                    'detail': response.text[:200],
                },
            }
    except Exception:
        item = {
            'id': len(twilio_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'sms',
            'to': payload.to,
            'status': 'queued-after-error',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(twilio_messages_memory, item)
        return {'status': 'ok', 'result': item}


def _handle_twilio_make_call(
    *,
    payload: TwilioMakeCallRequest,
    auth: AuthContext,
    twilio_messages_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
) -> dict:
    account_sid = os.getenv('TWILIO_ACCOUNT_SID', '').strip()
    auth_token = os.getenv('TWILIO_AUTH_TOKEN', '').strip()
    default_from = os.getenv('TWILIO_FROM_NUMBER', '').strip()
    api_base_url = os.getenv('TWILIO_API_BASE_URL', 'https://api.twilio.com').rstrip('/')
    from_number = (payload.from_number or default_from).strip()

    if not account_sid or not auth_token or not from_number:
        item = {
            'id': len(twilio_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'call',
            'to': payload.to,
            'status': 'queued',
            'reason': 'Twilio not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(twilio_messages_memory, item)
        return {'status': 'ok', 'result': item}

    credentials = base64.b64encode(f'{account_sid}:{auth_token}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {credentials}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {'From': from_number, 'To': payload.to, 'Url': str(payload.twiml_url)}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{api_base_url}/2010-04-01/Accounts/{account_sid}/Calls.json',
                headers=headers,
                data=data,
            )
            if response.is_success:
                rdata = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'type': 'call',
                        'sid': rdata.get('sid'),
                        'to': payload.to,
                        'delivery_status': rdata.get('status', 'initiated'),
                        'provider': 'twilio',
                    },
                }
    except Exception:
        item = {
            'id': len(twilio_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'call',
            'to': payload.to,
            'status': 'queued-after-error',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(twilio_messages_memory, item)
        return {'status': 'ok', 'result': item}

    item = {
        'id': len(twilio_messages_memory) + 1,
        'tenant_id': auth.tenant_id,
        'type': 'call',
        'to': payload.to,
        'status': 'queued-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    append_bounded(twilio_messages_memory, item)
    return {'status': 'ok', 'result': item}


def _register_twilio_routes(
    *,
    router: APIRouter,
    enforce_rate_limit: Callable[[str, int, int], None],
    twilio_messages_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
) -> None:
    @router.post('/notifications/twilio/send-sms')
    def twilio_send_sms(payload: TwilioSendSmsRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:twilio:sms', 60, 60)
        return _handle_twilio_send_sms(
            payload=payload,
            auth=auth,
            twilio_messages_memory=twilio_messages_memory,
            append_bounded=append_bounded,
        )

    @router.post('/notifications/twilio/make-call')
    def twilio_make_call(payload: TwilioMakeCallRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:twilio:call', 20, 60)
        return _handle_twilio_make_call(
            payload=payload,
            auth=auth,
            twilio_messages_memory=twilio_messages_memory,
            append_bounded=append_bounded,
        )


def _handle_slack_send_message(
    *,
    payload: SlackSendMessageRequest,
    auth: AuthContext,
    slack_messages_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
) -> dict:
    bot_token = os.getenv('SLACK_BOT_TOKEN', '').strip()
    api_base_url = os.getenv('SLACK_API_BASE_URL', 'https://slack.com/api').rstrip('/')

    if not bot_token:
        item = {
            'id': len(slack_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'channel': payload.channel,
            'text_preview': payload.text[:80],
            'status': 'queued',
            'reason': 'Slack not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(slack_messages_memory, item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Authorization': f'Bearer {bot_token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }
    body: dict = {
        'channel': payload.channel,
        'text': payload.text,
        'username': payload.username,
        'icon_emoji': payload.icon_emoji,
    }
    if payload.blocks:
        body['blocks'] = payload.blocks

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{api_base_url}/chat.postMessage', headers=headers, json=body)
            if response.is_success:
                rdata = response.json()
                ok = rdata.get('ok', response.is_success)
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'channel': payload.channel,
                        'ts': rdata.get('ts'),
                        'delivery_status': 'sent' if ok else 'slack-api-error',
                        'slack_error': rdata.get('error') if not ok else None,
                        'provider': 'slack-web-api',
                    },
                }
    except Exception:
        item = {
            'id': len(slack_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'channel': payload.channel,
            'status': 'queued-after-error',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(slack_messages_memory, item)
        return {'status': 'ok', 'result': item}

    item = {
        'id': len(slack_messages_memory) + 1,
        'tenant_id': auth.tenant_id,
        'channel': payload.channel,
        'status': 'queued-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    append_bounded(slack_messages_memory, item)
    return {'status': 'ok', 'result': item}


def _handle_slack_webhook_message(
    *,
    payload: SlackWebhookMessageRequest,
    auth: AuthContext,
    slack_messages_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
) -> dict:
    webhook_url = os.getenv('SLACK_WEBHOOK_URL', '').strip()

    if not webhook_url:
        item = {
            'id': len(slack_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'webhook',
            'text_preview': payload.text[:80],
            'status': 'queued',
            'reason': 'Slack webhook not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(slack_messages_memory, item)
        return {'status': 'ok', 'result': item}

    body: dict = {'text': payload.text}
    if payload.blocks:
        body['blocks'] = payload.blocks

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(webhook_url, json=body)
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'delivery_status': 'sent',
                        'provider': 'slack-incoming-webhook',
                    },
                }
    except Exception:
        item = {
            'id': len(slack_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'webhook',
            'status': 'queued-after-error',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(slack_messages_memory, item)
        return {'status': 'ok', 'result': item}

    item = {
        'id': len(slack_messages_memory) + 1,
        'tenant_id': auth.tenant_id,
        'type': 'webhook',
        'status': 'queued-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    append_bounded(slack_messages_memory, item)
    return {'status': 'ok', 'result': item}


def _register_slack_routes(
    *,
    router: APIRouter,
    enforce_rate_limit: Callable[[str, int, int], None],
    slack_messages_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
) -> None:
    @router.post('/notifications/slack/send-message')
    def slack_send_message(payload: SlackSendMessageRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:slack:message', 60, 60)
        return _handle_slack_send_message(
            payload=payload,
            auth=auth,
            slack_messages_memory=slack_messages_memory,
            append_bounded=append_bounded,
        )

    @router.post('/notifications/slack/webhook')
    def slack_webhook_message(payload: SlackWebhookMessageRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:slack:webhook', 60, 60)
        return _handle_slack_webhook_message(
            payload=payload,
            auth=auth,
            slack_messages_memory=slack_messages_memory,
            append_bounded=append_bounded,
        )


def _register_resend_routes(
    *,
    router: APIRouter,
    enforce_rate_limit: Callable[[str, int, int], None],
    resend_messages_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
) -> None:
    @router.post('/notifications/resend/send-email')
    def resend_send_email(payload: ResendSendEmailRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:resend:send-email', 120, 60)

        api_key = os.getenv('RESEND_API_KEY', '').strip()
        default_from = os.getenv('RESEND_FROM_EMAIL', 'onboarding@nuxtron.local').strip()
        api_base_url = os.getenv('RESEND_API_BASE_URL', 'https://api.resend.com').rstrip('/')
        from_email = (payload.from_email or default_from).strip()

        if not api_key:
            item = {
                'id': len(resend_messages_memory) + 1,
                'tenant_id': auth.tenant_id,
                'to_email': payload.to_email,
                'subject': payload.subject,
                'status': 'queued',
                'reason': 'Resend not configured',
                'created_at': datetime.now(UTC).isoformat(),
            }
            append_bounded(resend_messages_memory, item)
            return {'status': 'ok', 'result': item}

        body = {
            'from': from_email,
            'to': [payload.to_email],
            'subject': payload.subject,
        }
        if payload.html:
            body['html'] = payload.html
        if payload.text:
            body['text'] = payload.text
        if not payload.html and not payload.text:
            body['text'] = 'Generated by Nuxtron platform bridge.'

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(
                    f'{api_base_url}/emails',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': CONTENT_TYPE_JSON,
                    },
                    json=body,
                )
                if response.is_success:
                    data = response.json()
                    return {
                        'status': 'ok',
                        'result': {
                            'tenant_id': auth.tenant_id,
                            'provider': 'resend',
                            'message_id': data.get('id'),
                            'to_email': payload.to_email,
                            'delivery_status': 'sent',
                        },
                    }
        except Exception:
            item = {
                'id': len(resend_messages_memory) + 1,
                'tenant_id': auth.tenant_id,
                'to_email': payload.to_email,
                'subject': payload.subject,
                'status': 'queued-after-error',
                'created_at': datetime.now(UTC).isoformat(),
            }
            append_bounded(resend_messages_memory, item)
            return {'status': 'ok', 'result': item}

        item = {
            'id': len(resend_messages_memory) + 1,
            'tenant_id': auth.tenant_id,
            'to_email': payload.to_email,
            'subject': payload.subject,
            'status': 'queued-after-non-success',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(resend_messages_memory, item)
        return {'status': 'ok', 'result': item}


def _handle_algolia_index_object(
    *,
    payload: AlgoliaIndexObjectRequest,
    auth: AuthContext,
    algolia_sync_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
    algolia_tenant_index: Callable[[str, str], str],
) -> dict:
    app_id = os.getenv('ALGOLIA_APP_ID', '').strip()
    api_key = os.getenv('ALGOLIA_API_KEY', '').strip()
    tenant_index_name = algolia_tenant_index(auth.tenant_id, payload.index_name)

    if not app_id or not api_key:
        item = {
            'id': len(algolia_sync_memory) + 1,
            'tenant_id': auth.tenant_id,
            'index_name': tenant_index_name,
            'object_id': payload.object_id,
            'document': payload.document,
            'status': 'queued',
            'reason': 'Algolia not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        algolia_sync_memory[:] = [
            e for e in algolia_sync_memory
            if not (
                e.get('tenant_id') == auth.tenant_id
                and e.get('index_name') == tenant_index_name
                and e.get('object_id') == payload.object_id
            )
        ]
        append_bounded(algolia_sync_memory, item)
        return {'status': 'ok', 'result': item}

    headers = {
        'X-Algolia-Application-Id': app_id,
        'X-Algolia-API-Key': api_key,
        'Content-Type': CONTENT_TYPE_JSON,
    }
    body = dict(payload.document)
    body['objectID'] = payload.object_id

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.put(
                f'https://{app_id}.algolia.net/1/indexes/{tenant_index_name}/{payload.object_id}',
                headers=headers,
                json=body,
            )
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'index_name': tenant_index_name,
                        'object_id': payload.object_id,
                        'task_id': data.get('taskID'),
                        'provider': 'algolia',
                    },
                }
    except Exception:
        item = {
            'id': len(algolia_sync_memory) + 1,
            'tenant_id': auth.tenant_id,
            'index_name': tenant_index_name,
            'object_id': payload.object_id,
            'document': payload.document,
            'status': 'queued-after-error',
            'created_at': datetime.now(UTC).isoformat(),
        }
        append_bounded(algolia_sync_memory, item)
        return {'status': 'ok', 'result': item}

    item = {
        'id': len(algolia_sync_memory) + 1,
        'tenant_id': auth.tenant_id,
        'index_name': tenant_index_name,
        'object_id': payload.object_id,
        'document': payload.document,
        'status': 'queued-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    append_bounded(algolia_sync_memory, item)
    return {'status': 'ok', 'result': item}


def _handle_algolia_query(
    *,
    payload: AlgoliaQueryRequest,
    auth: AuthContext,
    algolia_sync_memory: list[dict],
    algolia_tenant_index: Callable[[str, str], str],
) -> dict:
    app_id = os.getenv('ALGOLIA_APP_ID', '').strip()
    api_key = os.getenv('ALGOLIA_API_KEY', '').strip()
    tenant_index_name = algolia_tenant_index(auth.tenant_id, payload.index_name)

    if not app_id or not api_key:
        hits = [
            {
                'objectID': e.get('object_id'),
                **(e.get('document') or {}),
            }
            for e in algolia_sync_memory
            if e.get('tenant_id') == auth.tenant_id and e.get('index_name') == tenant_index_name
        ]
        if payload.query.strip():
            needle = payload.query.strip().lower()
            hits = [h for h in hits if needle in str(h).lower()]

        start = payload.page * payload.hits_per_page
        end = start + payload.hits_per_page
        page_hits = hits[start:end]
        return {
            'status': 'ok',
            'result': {
                'tenant_id': auth.tenant_id,
                'index_name': tenant_index_name,
                'query': payload.query,
                'hits': page_hits,
                'total_hits': len(hits),
                'page': payload.page,
                'hits_per_page': payload.hits_per_page,
                'source': 'memory-fallback',
            },
        }

    headers = {
        'X-Algolia-Application-Id': app_id,
        'X-Algolia-API-Key': api_key,
        'Content-Type': CONTENT_TYPE_JSON,
    }
    body = {
        'query': payload.query,
        'page': payload.page,
        'hitsPerPage': payload.hits_per_page,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f'https://{app_id}.algolia.net/1/indexes/{tenant_index_name}/query',
                headers=headers,
                json=body,
            )
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'index_name': tenant_index_name,
                        'query': payload.query,
                        'hits': data.get('hits', []),
                        'total_hits': data.get('nbHits', 0),
                        'page': data.get('page', payload.page),
                        'hits_per_page': data.get('hitsPerPage', payload.hits_per_page),
                        'source': 'algolia',
                    },
                }
    except Exception:
        return {
            'status': 'ok',
            'result': {
                'tenant_id': auth.tenant_id,
                'index_name': tenant_index_name,
                'query': payload.query,
                'hits': [],
                'total_hits': 0,
                'source': 'error',
            },
        }

    return {
        'status': 'ok',
        'result': {
            'tenant_id': auth.tenant_id,
            'index_name': tenant_index_name,
            'query': payload.query,
            'hits': [],
            'total_hits': 0,
            'source': 'non-success',
        },
    }


def _register_algolia_routes(
    *,
    router: APIRouter,
    enforce_rate_limit: Callable[[str, int, int], None],
    algolia_sync_memory: list[dict],
    append_bounded: Callable[[list[dict], dict], None],
    algolia_tenant_index: Callable[[str, str], str],
) -> None:
    @router.post('/search/algolia/index-object')
    def algolia_index_object(payload: AlgoliaIndexObjectRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:algolia:index', 300, 60)
        return _handle_algolia_index_object(
            payload=payload,
            auth=auth,
            algolia_sync_memory=algolia_sync_memory,
            append_bounded=append_bounded,
            algolia_tenant_index=algolia_tenant_index,
        )

    @router.post('/search/algolia/query')
    def algolia_query(payload: AlgoliaQueryRequest, auth: AuthDep) -> dict:
        enforce_rate_limit(f'{auth.tenant_id}:algolia:query', 300, 60)
        return _handle_algolia_query(
            payload=payload,
            auth=auth,
            algolia_sync_memory=algolia_sync_memory,
            algolia_tenant_index=algolia_tenant_index,
        )


def create_bridges_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    meilisearch_index_memory: StoreList,
    redis_ops_memory: StoreList,
    twilio_messages_memory: StoreList,
    slack_messages_memory: StoreList,
    resend_messages_memory: StoreList,
    algolia_sync_memory: StoreList,
) -> APIRouter:
    router = APIRouter()
    try:
        # Prefer canonical memory cap, but keep legacy fallback for older deployments.
        memory_cap_raw = os.getenv('BRIDGES_MEMORY_CAP') or os.getenv('BRIDGES_MEMORY_MAX_ITEMS') or '5000'
        memory_max_items = max(1, int(memory_cap_raw))
    except ValueError:
        memory_max_items = 5000

    def redis_key(tenant_id: str, key: str) -> str:
        return f'nuxtron:{tenant_id}:{key}'

    def algolia_tenant_index(tenant_id: str, index_name: str) -> str:
        return f'{tenant_id}__{index_name}'

    def append_bounded(buffer: StoreList, item: StoreItem) -> None:
        buffer.append(item)
        overflow = len(buffer) - memory_max_items
        if overflow > 0:
            del buffer[:overflow]

    def redis_client():
        try:
            import redis  # type: ignore

            host = os.getenv('REDIS_HOST', '').strip()
            if not host:
                return None
            port = int(os.getenv('REDIS_PORT', '6379'))
            password = os.getenv('REDIS_PASSWORD', '') or None
            db = int(os.getenv('REDIS_DB', '0'))
            return redis.Redis(host=host, port=port, password=password, db=db, decode_responses=True, socket_timeout=5)
        except Exception:
            return None

    _register_meilisearch_routes(
        router=router,
        enforce_rate_limit=enforce_rate_limit,
        meilisearch_index_memory=meilisearch_index_memory,
        append_bounded=append_bounded,
    )
    _register_cache_routes(
        router=router,
        enforce_rate_limit=enforce_rate_limit,
        redis_ops_memory=redis_ops_memory,
        append_bounded=append_bounded,
        redis_key=redis_key,
        redis_client=redis_client,
    )
    _register_twilio_routes(
        router=router,
        enforce_rate_limit=enforce_rate_limit,
        twilio_messages_memory=twilio_messages_memory,
        append_bounded=append_bounded,
    )
    _register_slack_routes(
        router=router,
        enforce_rate_limit=enforce_rate_limit,
        slack_messages_memory=slack_messages_memory,
        append_bounded=append_bounded,
    )
    _register_resend_routes(
        router=router,
        enforce_rate_limit=enforce_rate_limit,
        resend_messages_memory=resend_messages_memory,
        append_bounded=append_bounded,
    )
    _register_algolia_routes(
        router=router,
        enforce_rate_limit=enforce_rate_limit,
        algolia_sync_memory=algolia_sync_memory,
        append_bounded=append_bounded,
        algolia_tenant_index=algolia_tenant_index,
    )

    return router