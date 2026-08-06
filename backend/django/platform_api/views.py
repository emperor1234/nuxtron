"""DRF endpoints: liveness, readiness, metrics, and authenticated profile.

These are the operational backbone. `/health/` is a cheap liveness probe (the
process answers). `/readiness/` verifies downstream dependencies and is what
the orchestrator should gate traffic on. `/metrics/` exposes Prometheus text.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.conf import settings
from django.http import HttpResponse
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from .health_checks import CHECKS, CheckResult
from .logging_filters import request_logger

log = logging.getLogger(__name__)

# Track process start for uptime; module import == first worker boot for gunicorn
# preload mode, which is close enough for liveness semantics.
_START_MONOTONIC = time.monotonic()


@extend_schema(
    summary='Liveness probe',
    description='Returns 200 if the process can answer requests. Does not check dependencies.',
    responses=OpenApiTypes.OBJECT,
)
@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def health_view(_request: Any) -> Response:
    """Liveness probe. Always 200 if the process can answer."""
    uptime_s = time.monotonic() - _START_MONOTONIC
    return Response(
        {
            'status': 'ok',
            'service': 'django-api',
            'uptime_s': round(uptime_s, 1),
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary='Readiness probe',
    description=(
        'Verifies downstream dependencies (database, cache, vault). '
        'Returns 200 when healthy, 503 when any critical dependency is unreachable. '
        'Gate ingress traffic on this endpoint.'
    ),
    responses=OpenApiTypes.OBJECT,
)
@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def readiness_view(request: Any) -> Response:
    """Readiness probe. 503 if any critical dependency is unreachable."""
    rl = request_logger(request, 'platform_api.readiness')
    results: dict[str, dict[str, Any]] = {}
    overall_ok = True
    for name, check_fn in CHECKS:
        result: CheckResult = check_fn()  # never raises
        results[name] = {'ok': result.ok, 'detail': result.detail}
        if not result.ok:
            overall_ok = False
            rl.warning('dependency check failed: %s -> %s', name, result.detail)

    http_status = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    body = {
        'status': 'ok' if overall_ok else 'degraded',
        'service': 'django-api',
        'checks': results,
        'version': getattr(settings, 'APP_VERSION', 'unknown'),
    }
    return Response(body, status=http_status)


@extend_schema(
    summary='Prometheus metrics',
    description='Container/process metrics in Prometheus text exposition format.',
    responses={(200, 'text/plain'): OpenApiTypes.NONE},
)
@ratelimit(key='ip', rate='60/m', block=True)
def metrics_view(_request: Any) -> HttpResponse:
    """Prometheus-format metrics. Expose under /metrics (see urls.py).

    Unauthenticated by design (scrapers don't carry bearer tokens), so this is
    locked down two other ways instead: AdminIPAllowlistMiddleware restricts
    it to ADMIN_IP_ALLOWLIST networks when configured (config/middleware/
    admin_allowlist.py), and the rate limit below caps scrape/probe volume
    from any single peer.

    We keep this intentionally lightweight and dependency-free: a real rollout
    would swap the body for django-prometheus counters/histograms. The shape
    below is valid Prometheus text that a scrape can ingest immediately.
    """
    probe_ok = CHECKS[0][1]().ok  # database check
    content = (
        '# HELP nuxtron_up 1 if the process is up.\n'
        '# TYPE nuxtron_up gauge\n'
        'nuxtron_up 1\n'
        '# HELP nuxtron_db_ready 1 if the database probe succeeded.\n'
        '# TYPE nuxtron_db_ready gauge\n'
        f'nuxtron_db_ready {1 if probe_ok else 0}\n'
    )
    return HttpResponse(content, content_type='text/plain; version=0.0.4; charset=utf-8')


@extend_schema(
    summary='Current user profile',
    description='Returns identity fields for the authenticated principal (JWT or session).',
    responses=OpenApiTypes.OBJECT,
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request: Any) -> Response:
    """Return the authenticated user's identity. Requires a valid JWT/session."""
    user = request.user
    return Response(
        {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': getattr(user, 'is_staff', False),
            'is_superuser': getattr(user, 'is_superuser', False),
            'date_joined': getattr(user, 'date_joined', None),
        }
    )


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """TokenObtainPairView scoped to the 'login' throttle rate (THROTTLE_LOGIN).

    The stock view only inherits the generic anon/user throttle rates, so
    brute-force login attempts were only bounded by THROTTLE_ANON (30/minute
    by default) rather than the stricter, purpose-built THROTTLE_LOGIN rate
    already defined in DEFAULT_THROTTLE_RATES.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'
