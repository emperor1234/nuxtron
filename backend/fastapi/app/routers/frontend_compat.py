"""Thin compatibility routes the dashboard already calls.

These keep frontend actions working without changing URL prefixes. They
reuse existing auth, rate limits, and in-memory stores.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..deps import AuthContext, require_auth
from ..memory_stores import credit_ledger, social_accounts
from ..rate_limiter import enforce_rate_limit
from ..security_layout import filter_tenant

AuthDep = Annotated[AuthContext, Depends(require_auth)]


class SystemOverviewCaptureRequest(BaseModel):
    note: str | None = None


_overview_history: list[dict[str, object]] = []


def create_frontend_compat_router() -> APIRouter:
    router = APIRouter(tags=['frontend-compat'])

    @router.get('/ai/gateway/status')
    def ai_gateway_status(auth: AuthDep) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:ai:gateway:status', 120, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'cache': {
                'metrics': {'hit_ratio': 0.0, 'lookups': 0, 'errors': 0},
                'trend_5m': {'avg_latency_ms': 0.0, 'error_rate': 0.0, 'requests': 0},
            },
            'observability': {
                'sentry_enabled': bool(os.getenv('SENTRY_DSN', '').strip()),
                'otel_enabled': bool(os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', '').strip()),
            },
        }

    @router.get('/social/trends')
    def social_trends(auth: AuthDep, category: str | None = None) -> list[dict[str, object]]:
        enforce_rate_limit(f'{auth.tenant_id}:social:trends', 120, 60)
        label = (category or 'general').strip() or 'general'
        now = datetime.now(UTC).isoformat()
        return [
            {
                'id': f'trend-{auth.tenant_id}-{label}',
                'name': f'{label.title()} conversation',
                'category': label,
                'volume': 0,
                'velocity': 0,
                'updated_at': now,
            }
        ]

    @router.get('/social/trends/{trend_id}/forecast')
    def social_trend_forecast(trend_id: str, auth: AuthDep) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:social:trends:forecast', 120, 60)
        return {
            'trend_id': trend_id,
            'roiForecast': 'stable',
            'projectedPeakDate': datetime.now(UTC).date().isoformat(),
        }

    @router.get('/social/trends/{trend_id}/roi-impact')
    def social_trend_roi(
        trend_id: str,
        auth: AuthDep,
        platforms: str = '',
    ) -> float:
        enforce_rate_limit(f'{auth.tenant_id}:social:trends:roi', 120, 60)
        _ = (trend_id, platforms)
        return 0.0

    @router.get('/social/accounts/{account_id}/stats')
    def social_account_stats(account_id: str, auth: AuthDep) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:social:account-stats', 120, 60)
        account = next(
            (
                item
                for item in filter_tenant(social_accounts, auth.tenant_id)
                if str(item.get('id') or '') == account_id
            ),
            None,
        )
        return {
            'account_id': account_id,
            'tenant_id': auth.tenant_id,
            'followers': int((account or {}).get('followers') or 0),
            'engagement_rate': float((account or {}).get('engagement_rate') or 0),
            'posts': int((account or {}).get('posts') or 0),
        }

    @router.get('/social/analytics/compare-networks')
    def social_compare_networks(auth: AuthDep) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:social:compare-networks', 120, 60)
        return {'tenant_id': auth.tenant_id, 'networks': [], 'generated_at': datetime.now(UTC).isoformat()}

    @router.get('/ops/finance/credits/ledger')
    def finance_credit_ledger(
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:ops:finance:ledger', 60, 60)
        entries = filter_tenant(credit_ledger, auth.tenant_id)[-limit:]
        running = 0
        shaped: list[dict[str, object]] = []
        for index, item in enumerate(entries, start=1):
            amount = int(item.get('amount') or 0)
            running += amount
            shaped.append(
                {
                    'id': int(item.get('id') or index),
                    'amount': amount,
                    'reason': str(item.get('reason') or item.get('description') or 'credit'),
                    'source': str(item.get('source') or 'ledger'),
                    'created_at': str(item.get('created_at') or datetime.now(UTC).isoformat()),
                    'running_balance': running,
                }
            )
        return {'entries': shaped, 'tenant_id': auth.tenant_id}

    @router.get('/ops/finance/stripe-sandbox')
    def finance_stripe_sandbox(auth: AuthDep) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:ops:finance:stripe-sandbox', 60, 60)
        return {
            'enabled': os.getenv('STRIPE_SANDBOX', 'true').strip().lower() in {'1', 'true', 'yes', 'on'},
            'test_price_id': os.getenv('STRIPE_TEST_PRICE_ID', '').strip(),
        }

    @router.get('/ops/platform/system-overview')
    def platform_system_overview(auth: AuthDep) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:ops:platform:overview', 60, 60)
        snapshot = {
            'tenant_id': auth.tenant_id,
            'captured_at': datetime.now(UTC).isoformat(),
            'status': 'ok',
            'workers': 1,
            'db_ready': True,
        }
        return snapshot

    @router.get('/ops/platform/system-overview/history')
    def platform_system_overview_history(
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=100)] = 24,
    ) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:ops:platform:overview-history', 60, 60)
        items = [item for item in _overview_history if item.get('tenant_id') == auth.tenant_id][-limit:]
        return {'items': items, 'tenant_id': auth.tenant_id}

    @router.post('/ops/platform/system-overview/capture')
    def platform_system_overview_capture(
        payload: SystemOverviewCaptureRequest,
        auth: AuthDep,
    ) -> dict[str, object]:
        enforce_rate_limit(f'{auth.tenant_id}:ops:platform:overview-capture', 30, 60)
        snapshot = {
            'id': int(time.time() * 1000),
            'tenant_id': auth.tenant_id,
            'captured_at': datetime.now(UTC).isoformat(),
            'note': payload.note or '',
            'status': 'ok',
        }
        _overview_history.append(snapshot)
        if len(_overview_history) > 500:
            del _overview_history[:-500]
        return snapshot

    return router
