"""Single owner of the HTTP edge configuration for the FastAPI application.

This module decides the environment-driven edge policy — which middleware is
installed and in which order, which hosts and origins are trusted, and whether
the interactive API docs are exposed. ``legacy_main`` re-exports the policy
helpers under their historical private names so existing callers keep working,
but the stack itself is configured here and nowhere else.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..production_middleware import (
    GlobalExceptionHandler,
    RequestTracingMiddleware,
    SecurityHeadersMiddleware,
    SensitiveRouteTokenMiddleware,
    StructuredLogger,
)
from ..rate_limiter import RateLimitExceededError

CORS_ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
CORS_ALLOWED_HEADERS = ['Authorization', 'Content-Type', 'X-API-Key', 'X-Tenant-Id', 'X-Request-ID']
TRUTHY_ENVIRONMENT_VALUES = {'1', 'true', 'yes', 'on'}


def is_production_environment() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def allow_api_docs() -> bool:
    if is_production_environment():
        return os.getenv('ENABLE_API_DOCS', '0').strip().lower() in TRUTHY_ENVIRONMENT_VALUES
    return True


def allowed_hosts() -> list[str]:
    raw = os.getenv('ALLOWED_HOSTS', '').strip()
    if raw:
        hosts = [item.strip() for item in raw.split(',') if item.strip()]
        # Container-local healthchecks (Docker HEALTHCHECK, Coolify's internal
        # probe) hit /healthz over loopback with Host: 127.0.0.1, which never
        # matches a real public ALLOWED_HOSTS domain. Always allow loopback
        # so those checks succeed without weakening the public-facing check.
        for local_host in ('localhost', '127.0.0.1'):
            if local_host not in hosts:
                hosts.append(local_host)
        return hosts
    if is_production_environment():
        raise RuntimeError('ALLOWED_HOSTS must be configured in production mode.')
    return ['*']


def cors_origins() -> list[str]:
    raw = os.getenv('CORS_ORIGINS', '').strip()
    if raw:
        return [item.strip() for item in raw.split(',') if item.strip()]
    if is_production_environment():
        raise RuntimeError('CORS_ORIGINS must be configured in production mode.')
    return ['*']


def configure_middleware(app: FastAPI) -> None:
    """Install the production middleware stack on *app* (order matters!)."""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SensitiveRouteTokenMiddleware)  # token-only on sensitive prefixes
    app.add_middleware(RequestTracingMiddleware, logger=StructuredLogger('nuxtron.requests'))
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())

    allowed_origins = cors_origins()
    wildcard_origin = len(allowed_origins) == 1 and allowed_origins[0] == '*'
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=not wildcard_origin,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
    )


def configure_exception_handlers(app: FastAPI) -> None:
    """Install the application-wide error responses on *app*."""

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
        return JSONResponse(status_code=429, content={'detail': exc.detail})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return await GlobalExceptionHandler.exception_handler(request, exc)
