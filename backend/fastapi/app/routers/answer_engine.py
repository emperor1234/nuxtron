"""Answer Engine Insights API Routes.

Durable, tenant-scoped APIs for AI visibility monitoring.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from ..answer_engine.insights import (
    AnswerEngineInsight,
    BrandMention,
    compute_insights,
    sync_brand_mentions,
)
from ..deps import AuthContext, require_auth
from ..persistence.ai_visibility_store import get_ai_visibility_store

router = APIRouter(prefix='/api/v1/answer-engine', tags=['Answer Engine Insights'])
logger = logging.getLogger(__name__)


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_brand_mentions(rows: list[dict]) -> list[BrandMention]:
    mentions: list[BrandMention] = []
    for row in rows:
        try:
            mentions.append(
                BrandMention(
                    id=str(row.get('id') or ''),
                    tenant_id=str(row.get('tenant_id') or ''),
                    brand_name=str(row.get('brand_name') or ''),
                    search_engine=str(row.get('search_engine') or 'chatgpt'),
                    query=str(row.get('query') or ''),
                    answer_text=str(row.get('answer_text') or ''),
                    source_url=row.get('source_url'),
                    sentiment=str(row.get('sentiment') or 'neutral'),
                    confidence=float(row.get('confidence') or 0.0),
                    timestamp=str(row.get('timestamp_iso') or ''),
                )
            )
        except Exception:
            continue
    return mentions

@router.post('/sync/{brand_name}')
async def trigger_sync(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
    background_tasks: BackgroundTasks,
) -> dict:
    """Trigger Answer Engine data sync for a brand in background."""

    try:
        tenant_id = auth.tenant_id
        store = get_ai_visibility_store()

        def sync_task() -> None:
            try:
                import asyncio

                mentions = asyncio.run(sync_brand_mentions(brand_name, tenant_id))
                persisted = store.replace_brand_mentions(
                    tenant_id,
                    brand_name,
                    [
                        {
                            'id': mention.id,
                            'search_engine': mention.search_engine.value,
                            'query': mention.query,
                            'answer_text': mention.answer_text,
                            'source_url': mention.source_url,
                            'sentiment': mention.sentiment.value,
                            'confidence': mention.confidence,
                            'timestamp': mention.timestamp.isoformat(),
                        }
                        for mention in mentions
                    ],
                )
                logger.info('Answer Engine sync completed for %s: %d mentions', brand_name, persisted)
            except Exception:
                logger.exception('Answer Engine sync task failed for %s', brand_name)

        background_tasks.add_task(sync_task)
        return {
            'status': 'sync_started',
            'brand_name': brand_name,
            'message': 'Answer Engine sync started. Check back in 30-60 seconds for results.',
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to start Answer Engine sync.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/insights/{brand_name}', response_model=AnswerEngineInsight)
async def get_insights(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> AnswerEngineInsight:
    """Get aggregated Answer Engine insights for a brand."""

    try:
        tenant_id = auth.tenant_id
        store = get_ai_visibility_store()
        mentions = _to_brand_mentions(store.get_all_mentions_for_brand(tenant_id=tenant_id, brand_name=brand_name))
        if not mentions:
            return AnswerEngineInsight(
                tenant_id=tenant_id,
                brand_name=brand_name,
            )
        return compute_insights(mentions, brand_name, tenant_id)

    except Exception as exc:
        logger.exception('Failed to get Answer Engine insights.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/insights/{brand_name}/mentions', response_model=list[dict])
async def list_mentions(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
    sentiment: Annotated[str | None, Query()] = None,
    engine: Annotated[str | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict]:
    """List brand mentions with optional filters."""

    try:
        store = get_ai_visibility_store()
        paginated = store.get_mentions(
            tenant_id=auth.tenant_id,
            brand_name=brand_name,
            sentiment=sentiment,
            engine=engine,
            skip=skip,
            limit=limit,
        )

        return [
            {
                'id': m.get('id'),
                'brand_name': m.get('brand_name'),
                'search_engine': m.get('search_engine'),
                'query': m.get('query'),
                'answer_text': m.get('answer_text'),
                'source_url': m.get('source_url'),
                'sentiment': m.get('sentiment'),
                'confidence': m.get('confidence'),
                'timestamp': m.get('timestamp_iso'),
            }
            for m in paginated
        ]

    except Exception as exc:
        logger.exception('Failed to list Answer Engine mentions.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/status/{brand_name}')
async def get_sync_status(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Get last sync status for a brand."""

    try:
        store = get_ai_visibility_store()
        mentions = _to_brand_mentions(store.get_all_mentions_for_brand(tenant_id=auth.tenant_id, brand_name=brand_name))
        if not mentions:
            return {
                'brand_name': brand_name,
                'status': 'never_synced',
                'last_updated': None,
                'total_mentions': 0,
            }
        insight = compute_insights(mentions, brand_name, auth.tenant_id)
        return {
            'brand_name': brand_name,
            'status': 'synced',
            'last_updated': insight.updated_at.isoformat(),
            'total_mentions_7d': insight.total_mentions_7d,
            'total_mentions_30d': insight.total_mentions_30d,
            'trending': insight.trending_direction,
            'visibility_score': insight.visibility_score,
        }

    except Exception as exc:
        logger.exception('Failed to get Answer Engine sync status.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/analytics/{brand_name}/timeline')
async def get_timeline(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Get mention timeline for charting."""

    try:
        store = get_ai_visibility_store()
        mentions = store.get_all_mentions_for_brand(tenant_id=auth.tenant_id, brand_name=brand_name)
        timeline: dict[str, int] = {}
        for mention in mentions:
            timestamp = str(mention.get('timestamp_iso') or '')
            date_key = timestamp[:10] if len(timestamp) >= 10 else 'unknown'
            timeline[date_key] = timeline.get(date_key, 0) + 1
        sorted_timeline = sorted(timeline.items())
        return {
            'brand_name': brand_name,
            'timeline': [{'date': date, 'count': count} for date, count in sorted_timeline],
        }

    except Exception as exc:
        logger.exception('Failed to get Answer Engine timeline.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/analytics/{brand_name}/by-engine')
async def get_by_engine(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Get breakdown by search engine."""

    try:
        store = get_ai_visibility_store()
        mentions = _to_brand_mentions(store.get_all_mentions_for_brand(tenant_id=auth.tenant_id, brand_name=brand_name))
        if not mentions:
            return {'brand_name': brand_name, 'by_engine': {}}
        insight = compute_insights(mentions, brand_name, auth.tenant_id)
        return {
            'brand_name': brand_name,
            'by_engine': [{'engine': engine.value, 'count': count} for engine, count in insight.mentions_by_engine.items()],
        }

    except Exception as exc:
        logger.exception('Failed to get Answer Engine by-engine data.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/analytics/{brand_name}/sentiment')
async def get_sentiment_breakdown(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Get sentiment breakdown."""

    try:
        store = get_ai_visibility_store()
        mentions = _to_brand_mentions(store.get_all_mentions_for_brand(tenant_id=auth.tenant_id, brand_name=brand_name))
        if not mentions:
            return {'brand_name': brand_name, 'sentiment': {}}
        insight = compute_insights(mentions, brand_name, auth.tenant_id)
        return {
            'brand_name': brand_name,
            'sentiment': [{'sentiment': sentiment, 'count': count} for sentiment, count in insight.sentiment_breakdown.items()],
        }

    except Exception as exc:
        logger.exception('Failed to get Answer Engine sentiment data.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/analytics/{brand_name}/citations')
async def get_citation_domains(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Get citation/source domains most used across AI answers."""
    try:
        store = get_ai_visibility_store()
        mentions = store.get_all_mentions_for_brand(tenant_id=auth.tenant_id, brand_name=brand_name)
        counter: Counter[str] = Counter()
        for mention in mentions:
            source_url = str(mention.get('source_url') or '').strip()
            if not source_url:
                continue
            host = urlparse(source_url).netloc.lower().strip()
            if host:
                counter[host] += 1
        return {
            'brand_name': brand_name,
            'citation_domains': [{'domain': domain, 'count': count} for domain, count in counter.most_common(50)],
            'total_domains': len(counter),
        }
    except Exception as exc:
        logger.exception('Failed to get citation domains.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/analytics/{brand_name}/share-of-voice')
async def get_share_of_voice(
    brand_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
    competitors: Annotated[list[str] | None, Query()] = None,
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> dict:
    """Compute mention-based share of voice against competitor brands."""
    if competitors is None:
        competitors = []
    try:
        store = get_ai_visibility_store()
        own_mentions = store.get_mentions_for_window(tenant_id=auth.tenant_id, brand_name=brand_name, days=days)
        rows = [{'brand': brand_name, 'mentions': len(own_mentions)}]
        for competitor in competitors:
            name = competitor.strip()
            if not name:
                continue
            comp_mentions = store.get_mentions_for_window(tenant_id=auth.tenant_id, brand_name=name, days=days)
            rows.append({'brand': name, 'mentions': len(comp_mentions)})

        total = sum(_coerce_int(item.get('mentions', 0)) for item in rows)
        rows_with_share = []
        for item in rows:
            mentions = _coerce_int(item.get('mentions', 0))
            share = round((mentions / max(total, 1)) * 100.0, 2)
            rows_with_share.append({'brand': item['brand'], 'mentions': mentions, 'share_pct': share})

        rows_with_share.sort(key=lambda item: item['mentions'], reverse=True)
        return {
            'brand_name': brand_name,
            'window_days': days,
            'total_mentions': total,
            'share_of_voice': rows_with_share,
        }
    except Exception as exc:
        logger.exception('Failed to compute share of voice.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc
