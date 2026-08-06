"""Agent Analytics API Routes.

REST endpoints for viewing AI bot traffic analytics:
- Dashboard metrics
- Bot-specific breakdowns
- Trend analysis
- Geographic distribution
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..agent_analytics.core import (
    AgentLogEvent,
    AIBot,
    BotSignature,
    agent_analytics_collector,
)
from ..deps import AuthContext, require_auth

router = APIRouter(prefix='/api/v1/agent-analytics', tags=['Agent Analytics'])
logger = logging.getLogger(__name__)

MEMORY_STORE_UNAVAILABLE = 'Agent Analytics persistence is not configured for production. Configure a durable backend before enabling logging.'


def _is_production() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _ensure_agent_analytics_store_writable() -> None:
    if _is_production():
        raise HTTPException(status_code=503, detail=MEMORY_STORE_UNAVAILABLE)


def get_tenant_id() -> str:
    """Placeholder for tenant extraction"""
    return "default_tenant"

@router.post('/log-event')
async def log_bot_event(
    event_data: dict[str, Any],
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Log an AI bot visit (called from Cloudflare Worker or CDN)."""

    try:
        _ensure_agent_analytics_store_writable()
        tenant_id = auth.tenant_id

        user_agent = event_data.get('user_agent', '')
        bot_name = BotSignature.identify(user_agent)

        if not bot_name:
            logger.debug('Non-bot user-agent: %s', user_agent)
            return {'status': 'ignored', 'reason': 'not_a_bot'}

        event = AgentLogEvent(
            tenant_id=tenant_id,
            timestamp=datetime.fromisoformat(
                event_data.get('timestamp', datetime.utcnow().isoformat()).replace('Z', '+00:00')
            ),
            method=event_data.get('method', 'GET'),
            path=event_data.get('path', '/'),
            query_string=event_data.get('query_string'),
            bot_name=bot_name,
            user_agent=user_agent,
            ip_hash=event_data.get('ip_hash', ''),
            country=event_data.get('country'),
            asn=event_data.get('asn'),
            is_datacenter=event_data.get('is_datacenter', False),
            status_code=event_data.get('status_code', 200),
            response_time_ms=event_data.get('response_time_ms', 0),
            response_size_bytes=event_data.get('response_size_bytes', 0),
        )

        agent_analytics_collector.add_log(event)
        return {'status': 'logged', 'bot': bot_name.value}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to log event.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/dashboard')
async def get_dashboard(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> dict:
    """Get summary dashboard metrics."""

    try:
        tenant_id = auth.tenant_id
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        analytics = agent_analytics_collector.get_analytics(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        return {
            'period_days': days,
            'total_requests': analytics.total_requests,
            'unique_bots': analytics.unique_bots,
            'total_crawled_pages': analytics.total_crawled_pages,
            'requests_by_bot': [{'bot': bot.value, 'count': count} for bot, count in analytics.requests_by_bot.items()],
            'avg_response_time_ms': analytics.avg_response_time_ms,
            'total_bandwidth_gb': round(analytics.total_bandwidth_gb, 2),
            'top_pages': analytics.top_pages[:10],
            'status_codes': [{'code': code, 'count': count} for code, count in sorted(analytics.requests_by_status.items())],
        }

    except Exception as exc:
        logger.exception('Failed to get dashboard.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/bots/{bot_name}')
async def get_bot_details(
    bot_name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> dict:
    """Get detailed analytics for a specific bot."""

    try:
        tenant_id = auth.tenant_id
        try:
            bot = AIBot(bot_name)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f'Invalid bot: {bot_name}. Must be one of: {", ".join([b.value for b in AIBot])}',
            )

        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        details = agent_analytics_collector.get_bot_details(
            tenant_id=tenant_id,
            bot_name=bot,
            period_start=period_start,
            period_end=period_end,
        )

        return details

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to get bot details.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/bots')
async def list_bots(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: Annotated[int, Query()] = 7,
) -> dict:
    """List all bots detected."""

    try:
        tenant_id = auth.tenant_id
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        analytics = agent_analytics_collector.get_analytics(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        return {
            'bots_detected': [{'name': bot.value, 'requests': count} for bot, count in analytics.requests_by_bot.items()],
            'total_unique_bots': analytics.unique_bots,
        }

    except Exception as exc:
        logger.exception('Failed to list bots.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/pages')
async def get_top_pages(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: Annotated[int, Query()] = 7,
    limit: Annotated[int, Query(le=100)] = 20,
) -> dict:
    """Get most crawled pages by AI bots."""

    try:
        tenant_id = auth.tenant_id
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        analytics = agent_analytics_collector.get_analytics(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        return {
            'top_pages': analytics.top_pages[:limit],
            'total_crawled_pages': analytics.total_crawled_pages,
        }

    except Exception as exc:
        logger.exception('Failed to get pages.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/geographic')
async def get_geographic_distribution(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: Annotated[int, Query()] = 7,
) -> dict:
    """Get geographic distribution of bot traffic."""

    try:
        tenant_id = auth.tenant_id
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        analytics = agent_analytics_collector.get_analytics(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        countries = [
            {'country': country, 'requests': count}
            for country, count in sorted(analytics.requests_by_country.items(), key=lambda x: x[1], reverse=True)[:20]
        ]

        return {
            'countries': countries,
            'top_country': countries[0] if countries else None,
        }

    except Exception as exc:
        logger.exception('Failed to get geographic data.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/status-codes')
async def get_status_code_breakdown(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: Annotated[int, Query()] = 7,
) -> dict:
    """Get HTTP status code breakdown."""

    try:
        tenant_id = auth.tenant_id
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        analytics = agent_analytics_collector.get_analytics(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        success_rate: float = 0.0
        if analytics.total_requests > 0:
            success_rate = sum(count for code, count in analytics.requests_by_status.items() if code < 400) / analytics.total_requests * 100

        return {
            'status_codes': [{'code': code, 'count': count} for code, count in sorted(analytics.requests_by_status.items())],
            'total_requests': analytics.total_requests,
            'success_rate': success_rate,
        }

    except Exception as exc:
        logger.exception('Failed to get status codes.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get('/comparison')
async def compare_periods(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: Annotated[int, Query()] = 7,
) -> dict:
    """Compare traffic between current period and previous period."""

    try:
        tenant_id = auth.tenant_id
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)
        previous_period_end = period_start
        previous_period_start = previous_period_end - timedelta(days=days)

        current = agent_analytics_collector.get_analytics(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        previous = agent_analytics_collector.get_analytics(
            tenant_id=tenant_id,
            period_start=previous_period_start,
            period_end=previous_period_end,
        )

        change_requests = current.total_requests - previous.total_requests
        change_percent = (change_requests / previous.total_requests * 100) if previous.total_requests > 0 else (100 if change_requests > 0 else 0)

        return {
            'period': f'last_{days}_days',
            'current_period': {
                'requests': current.total_requests,
                'unique_bots': current.unique_bots,
                'crawled_pages': current.total_crawled_pages,
            },
            'previous_period': {
                'requests': previous.total_requests,
                'unique_bots': previous.unique_bots,
                'crawled_pages': previous.total_crawled_pages,
            },
            'change': {
                'requests_absolute': change_requests,
                'requests_percent': round(change_percent, 1),
                'trend': 'up' if change_requests > 0 else 'down' if change_requests < 0 else 'stable',
            },
        }

    except Exception as exc:
        logger.exception('Failed to compare periods.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc
