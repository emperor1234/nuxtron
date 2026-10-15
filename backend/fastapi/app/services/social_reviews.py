"""Social Listening & Reviews Service

Extracted from legacy_main.py: Social listening mention ingestion, summary,
alert rules, clusters, and reviews ingestion, listing, responding, summary.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, NoReturn

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from .. import memory_stores
from ..deps import AuthContext, require_auth
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit

JsonObject = dict[str, object]

REVIEW_DATA_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": "Connected review-provider data and durable reputation storage are not configured. Review operations do not use synthetic records.",
}
REVIEW_DATA_UNAVAILABLE_RESPONSE = {
    "description": "Connected review-provider data are unavailable.",
    "content": {"application/json": {"example": {"detail": REVIEW_DATA_UNAVAILABLE_DETAIL}}},
}


def raise_review_data_unavailable() -> NoReturn:
    raise HTTPException(status_code=501, detail=REVIEW_DATA_UNAVAILABLE_DETAIL)


AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Memory Store References (set by legacy_main.py) ──────────
_social_listening_memory = memory_stores.social_listening
_social_listening_alert_rules_memory = memory_stores.social_listening_alert_rules
_social_listening_alerts_memory = memory_stores.social_listening_alerts
_reviews_memory = memory_stores.reviews

_coerce_int = int


def set_memory_stores(
    social_listening_memory=None,
    social_listening_alert_rules_memory=None,
    social_listening_alerts_memory=None,
    reviews_memory=None,
    enforce_rate_limit=None,
    coerce_int=None,
) -> None:
    """Inject memory store references from legacy_main.py."""
    global _social_listening_memory, _social_listening_alert_rules_memory
    global _social_listening_alerts_memory, _reviews_memory
    global _enforce_rate_limit, _coerce_int
    if social_listening_memory is not None:
        _social_listening_memory = social_listening_memory
    if social_listening_alert_rules_memory is not None:
        _social_listening_alert_rules_memory = social_listening_alert_rules_memory
    if social_listening_alerts_memory is not None:
        _social_listening_alerts_memory = social_listening_alerts_memory
    if reviews_memory is not None:
        _reviews_memory = reviews_memory
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit
    if coerce_int is not None:
        _coerce_int = coerce_int


# ── Social Listening ──────────────────────────────────────────


def ingest_social_listening_mention(
    payload: SocialListeningIngestRequest,
    auth: AuthDep,
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:social:listening:ingest', limit=180, window_seconds=60)
    mention: JsonObject = {
        'id': len(_social_listening_memory) + 1,
        'tenant_id': auth.tenant_id,
        'platform': payload.platform,
        'query': payload.query,
        'author_handle': payload.author_handle,
        'text': payload.text,
        'sentiment': payload.sentiment,
        'engagement_count': payload.engagement_count,
        'created_at': datetime.now(UTC).isoformat(),
        'source': 'api',
        'persistence': 'memory-fallback',
    }
    _social_listening_memory.append(mention)
    for rule in [
        item for item in _social_listening_alert_rules_memory
        if item.get('tenant_id') == auth.tenant_id and item.get('enabled', True)
    ]:
        matches_query = not rule.get('query') or str(rule.get('query')).lower() in payload.query.lower()
        matches_platform = not rule.get('platform') or rule.get('platform') == payload.platform
        matches_sentiment = (not rule.get('negative_only', True)) or payload.sentiment == 'negative'
        matches_engagement = payload.engagement_count >= _coerce_int(rule.get('min_engagement', 0), 0)
        if not (matches_query and matches_platform and matches_sentiment and matches_engagement):
            continue

        _social_listening_alerts_memory.append({
            'id': len(_social_listening_alerts_memory) + 1,
            'tenant_id': auth.tenant_id,
            'rule_id': rule.get('id'),
            'rule_name': rule.get('name'),
            'mention_id': mention['id'],
            'severity': 'high' if payload.engagement_count >= 100 else 'medium',
            'status': 'open',
            'created_at': datetime.now(UTC).isoformat(),
        })
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'mention': mention}


def list_social_listening_mentions(auth: AuthDep) -> JsonObject:
    items: list[JsonObject] = [
        e for e in _social_listening_memory if e.get('tenant_id') == auth.tenant_id
    ]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'mentions': items}


def get_social_listening_summary(auth: AuthDep) -> JsonObject:
    mentions = [e for e in _social_listening_memory if e.get('tenant_id') == auth.tenant_id]
    alerts = [e for e in _social_listening_alerts_memory if e.get('tenant_id') == auth.tenant_id]
    rules = [e for e in _social_listening_alert_rules_memory if e.get('tenant_id') == auth.tenant_id]

    sentiment_counts: dict[str, int] = {}
    platform_counts: dict[str, int] = {}
    query_counts: dict[str, int] = {}

    for m in mentions:
        sentiment = m.get('sentiment', 'neutral')
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        platform = m.get('platform', 'unknown')
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
        query = m.get('query', 'unknown')
        query_counts[query] = query_counts.get(query, 0) + 1

    top_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    clusters: dict[tuple[str, str, str], int] = {}
    for m in mentions:
        key = (m.get('query', 'unknown'), m.get('platform', 'unknown'), m.get('sentiment', 'neutral'))
        clusters[key] = clusters.get(key, 0) + 1

    cluster_list = [
        {'query': q, 'platform': p, 'sentiment': s, 'count': c}
        for (q, p, s), c in clusters.items()
    ]
    cluster_list.sort(key=lambda x: x['count'], reverse=True)

    open_alerts = [a for a in alerts if a.get('status') == 'open']
    crisis_level = 'normal'
    if len(open_alerts) >= 10:
        crisis_level = 'high'
    elif len(open_alerts) >= 5:
        crisis_level = 'medium'
    elif len(open_alerts) >= 1:
        crisis_level = 'low'

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'totals': {
            'mentions': len(mentions),
            'alerts': len(alerts),
            'open_alerts': len(open_alerts),
            'rules': len(rules),
        },
        'sentiment_breakdown': sentiment_counts,
        'platform_distribution': platform_counts,
        'top_queries': [{'query': q, 'count': c} for q, c in top_queries],
        'clusters': cluster_list[:20],
        'crisis_level': crisis_level,
    }


def create_social_listening_alert_rule(
    payload: SocialListeningAlertRuleRequest,
    auth: AuthDep,
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:social:listening:rules:create', limit=60, window_seconds=60)
    rule: JsonObject = {
        'id': len(_social_listening_alert_rules_memory) + 1,
        'tenant_id': auth.tenant_id,
        'name': payload.name,
        'query': payload.query,
        'platform': payload.platform,
        'min_engagement': payload.min_engagement,
        'negative_only': payload.negative_only,
        'enabled': True,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _social_listening_alert_rules_memory.append(rule)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'persistence': 'memory-fallback', 'rule': rule}


def list_social_listening_alert_rules(auth: AuthDep) -> JsonObject:
    items: list[JsonObject] = [
        item.copy() for item in _social_listening_alert_rules_memory if item.get('tenant_id') == auth.tenant_id
    ]
    items.sort(key=lambda item: str(item.get('created_at') or ''), reverse=True)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'persistence': 'memory-fallback',
        'count': len(items),
        'rules': items,
    }


def list_social_listening_alerts(auth: AuthDep) -> JsonObject:
    items: list[JsonObject] = [
        e for e in _social_listening_alerts_memory if e.get('tenant_id') == auth.tenant_id
    ]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'alerts': items}


def get_social_listening_clusters(auth: AuthDep) -> JsonObject:
    mentions = [e for e in _social_listening_memory if e.get('tenant_id') == auth.tenant_id]
    clusters: dict[tuple[str, str, str], int] = {}
    for m in mentions:
        key = (m.get('query', 'unknown'), m.get('platform', 'unknown'), m.get('sentiment', 'neutral'))
        clusters[key] = clusters.get(key, 0) + 1
    cluster_list = [
        {'query': q, 'platform': p, 'sentiment': s, 'count': c}
        for (q, p, s), c in clusters.items()
    ]
    cluster_list.sort(key=lambda x: x['count'], reverse=True)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'clusters': cluster_list}


# ── Reviews ───────────────────────────────────────────────────


def ingest_review(payload: ReviewIngestRequest, auth: AuthDep) -> JsonObject:
    raise_review_data_unavailable()


def list_reviews(auth: AuthDep) -> JsonObject:
    raise_review_data_unavailable()


def respond_to_review(review_id: int, payload: ReviewResponseRequest, auth: AuthDep) -> JsonObject:
    raise_review_data_unavailable()


def get_reviews_summary(auth: AuthDep) -> JsonObject:
    raise_review_data_unavailable()


# ── Request Models ────────────────────────────────────────────

class SocialListeningIngestRequest(BaseModel):
    platform: Literal['linkedin', 'x', 'instagram', 'facebook', 'reddit', 'youtube', 'news']
    query: str = Field(min_length=2, max_length=120)
    author_handle: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=3, max_length=4000)
    sentiment: Literal['positive', 'neutral', 'negative'] = 'neutral'
    engagement_count: int = Field(default=0, ge=0, le=1_000_000)


class SocialListeningAlertRuleRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    query: str | None = Field(default=None, max_length=120)
    platform: Literal['linkedin', 'x', 'instagram', 'facebook', 'reddit', 'youtube', 'news'] | None = None
    min_engagement: int = Field(default=20, ge=0, le=1_000_000)
    negative_only: bool = True


class ReviewIngestRequest(BaseModel):
    platform: Literal['google', 'trustpilot', 'g2', 'capterra', 'yelp', 'app_store', 'play_store', 'custom']
    reviewer: str = Field(min_length=1, max_length=120)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=3, max_length=4000)
    category: str = Field(default='general', min_length=1, max_length=80)


class ReviewResponseRequest(BaseModel):
    response: str = Field(min_length=3, max_length=4000)
