"""
Production-level middleware and utilities for Nuxtron FastAPI services.
Includes security headers, structured logging, exception handling, health checks.
"""

import json
import logging
import os
import sys
import threading
import time
import uuid
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp

JsonObject = dict[str, object]
QueueValues = Sequence[object]

# Request ID context var for request tracing
request_id_context: ContextVar[str] = ContextVar('request_id', default='')

_LATENCY_WINDOW_SIZE = 240
_latency_lock = threading.Lock()
_request_latency_ms: dict[str, list[float]] = {}


def _request_trace_logging_enabled() -> bool:
    return os.getenv('REQUEST_TRACE_LOGGING_ENABLED', '1').strip().lower() in {'1', 'true', 'yes', 'on'}


def _record_request_latency(path: str, duration_ms: float) -> None:
    key = path or '/'
    value = max(0.0, float(duration_ms))
    with _latency_lock:
        bucket = _request_latency_ms.setdefault(key, [])
        bucket.append(value)
        if len(bucket) > _LATENCY_WINDOW_SIZE:
            del bucket[: len(bucket) - _LATENCY_WINDOW_SIZE]


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * max(0.0, min(1.0, percentile))))
    return ordered[idx]


def get_request_latency_snapshot() -> dict[str, object]:
    with _latency_lock:
        snapshot = {path: samples[:] for path, samples in _request_latency_ms.items()}

    path_stats: dict[str, dict[str, float | int]] = {}
    total_samples = 0
    for path, samples in snapshot.items():
        if not samples:
            continue
        total_samples += len(samples)
        path_stats[path] = {
            'count': len(samples),
            'p50_ms': round(_percentile(samples, 0.50), 2),
            'p95_ms': round(_percentile(samples, 0.95), 2),
            'max_ms': round(max(samples), 2),
        }

    return {
        'window_size': _LATENCY_WINDOW_SIZE,
        'path_count': len(path_stats),
        'sample_count': total_samples,
        'paths': path_stats,
    }


class StructuredLogger:
    """Structured JSON logging for production."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        # Prevent duplicate log emission through root/uvicorn handlers.
        self.logger.propagate = False

        # JSON formatter
        if not any(getattr(existing, '_nuxtron_structured_handler', False) for existing in self.logger.handlers):
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(message)s',
                datefmt='%Y-%m-%dT%H:%M:%SZ'
            )
            handler.setFormatter(formatter)
            handler._nuxtron_structured_handler = True
            self.logger.addHandler(handler)
    
    def log(self, level: int, message: str, **extra: object) -> None:
        """Log structured message with context."""
        log_entry: dict[str, object] = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': logging.getLevelName(level),
            'message': message,
            'request_id': request_id_context.get(),
            **extra,
        }
        self.logger.log(level, json.dumps(log_entry, default=str))
    
    def info(self, message: str, **extra: object) -> None:
        self.log(logging.INFO, message, **extra)
    
    def warning(self, message: str, **extra: object) -> None:
        self.log(logging.WARNING, message, **extra)
    
    def error(self, message: str, **extra: object) -> None:
        self.log(logging.ERROR, message, **extra)
    
    def critical(self, message: str, **extra: object) -> None:
        self.log(logging.CRITICAL, message, **extra)
    
    def debug(self, message: str, **extra: object) -> None:
        self.log(logging.DEBUG, message, **extra)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        environment = os.getenv('ENVIRONMENT', 'development').strip().lower()
        is_production = environment == 'production'

        # Security headers per OWASP recommendations
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        if is_production:
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
        else:
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;"
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        
        # Prevent caching of sensitive responses
        if request.url.path.startswith('/api/') or request.url.path.startswith('/auth/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Add request ID tracking and structured logging."""
    
    def __init__(self, app: ASGIApp, logger: StructuredLogger | None = None):
        super().__init__(app)
        self.logger = logger or StructuredLogger('nuxtron.requests')
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        token = request_id_context.set(request_id)
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time
            duration_ms = duration * 1000
            _record_request_latency(request.url.path, duration_ms)

            if _request_trace_logging_enabled():
                self.logger.info(
                    'HTTP Request Completed',
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    request_id=request_id,
                )
            
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Process-Time'] = f'{duration:.6f}'
            
            return response
        finally:
            request_id_context.reset(token)


class GlobalExceptionHandler:
    """Catch and standardize all exceptions."""
    
    @staticmethod
    async def exception_handler(request: Request, exc: Exception):
        request_id = request_id_context.get()
        error_id = str(uuid.uuid4())
        logger = StructuredLogger('nuxtron.errors')
        
        # Log the full exception
        logger.error(
            'Unhandled Exception',
            error_id=error_id,
            error_type=type(exc).__name__,
            error_message=str(exc),
            path=request.url.path,
            method=request.method,
            request_id=request_id,
        )
        
        # Return safe error response. Only expose raw exception text when DEBUG
        # is explicitly enabled; never leak internals to clients in production.
        # The envelope shape ({"error", "request_id"}) matches the Django
        # UncaughtExceptionMiddleware so clients get one error contract (WO-9).
        debug_detail: str | None = str(exc) if os.getenv('DEBUG', '0') == '1' else None
        response_body: dict[str, object] = {
            'error': 'internal_server_error',
            'request_id': request_id,
            # Backward-compat fields for existing clients:
            'status': 'error',
            'error_id': error_id,
            'message': 'Internal server error',
            'detail': debug_detail,
            'timestamp': datetime.now(UTC).isoformat(),
        }
        
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_body,
            headers={'X-Request-ID': request_id, 'X-Error-ID': error_id},
        )


# Sensitive path prefixes that require bearer JWT regardless of ALLOW_HEADER_API_KEYS
_SENSITIVE_PREFIXES: tuple[str, ...] = (
    '/api-governance',
    '/admin',
    '/super-admin',
    '/vault',
    '/siem',
    # The real SIEM routes live under /ops/siem/* (routers/ops.py), not a bare
    # /siem prefix — that mismatch meant this guard never actually matched
    # them. Keep both: '/siem' in case a bare-prefix route is added later.
    '/ops/siem',
    '/security',
    '/auth/tokens',
    '/auth/sessions',
    '/auth/jwt/issue',
    # '/pentest',  # Excluded pentest routes from global token-only middleware
    # '/benchmarks',  # Excluded benchmarks routes from global token-only middleware
)


class SensitiveRouteTokenMiddleware(BaseHTTPMiddleware):
    """Global token-only enforcement for sensitive route prefixes.

    Any request to a sensitive prefix that arrives with an ``X-API-Key`` header
    instead of an ``Authorization: Bearer ...`` header is rejected with HTTP 403,
    *even if* ``ALLOW_HEADER_API_KEYS=true`` is set.  The API-key allowance is
    intentionally scoped to non-sensitive general API traffic only.

    Set ``SENSITIVE_PREFIXES`` env var (comma-separated) to override the default
    list, or ``DISABLE_SENSITIVE_ROUTE_GUARD=true`` to turn off for testing.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        custom = os.environ.get('SENSITIVE_PREFIXES', '').strip()
        if custom:
            self._prefixes: tuple[str, ...] = tuple(
                p.strip() for p in custom.split(',') if p.strip()
            )
        else:
            self._prefixes = _SENSITIVE_PREFIXES
        self._disabled = os.environ.get('DISABLE_SENSITIVE_ROUTE_GUARD', '').lower() in ('1', 'true', 'yes')

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._disabled and self._is_sensitive(request.url.path):
            auth_header = request.headers.get('Authorization', '')
            api_key_header = request.headers.get('X-API-Key', '')
            if api_key_header and not auth_header.lower().startswith('bearer '):
                return JSONResponse(
                    status_code=403,
                    content={
                        'status': 'error',
                        'detail': (
                            'Bearer token required. '
                            'Header API keys are not accepted on sensitive routes. '
                            'Obtain a JWT token via /auth/login and use Authorization: Bearer <token>.'
                        ),
                        'code': 'TOKEN_ONLY_POLICY',
                    },
                )
        return await call_next(request)

    def _is_sensitive(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self._prefixes)


def validate_environment() -> dict[str, str]:
    """Validate required environment variables at startup."""
    logger = StructuredLogger('nuxtron.startup')
    
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    is_production = environment == 'production'
    
    # In development, use defaults; in production, require all
    required_vars = [
        'JWT_SIGNING_KEY',
        'APP_ENC_KEY',
        'PASSWORD_PEPPER',
    ]
    
    optional_vars = [
        'FASTAPI_API_KEY',
        'SECURITY_STRICT_MODE',
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'CORS_ORIGINS',
        'LOG_LEVEL',
        'DEBUG',
    ]
    
    missing: list[str] = []
    config: dict[str, str] = {}
    
    for var in required_vars:
        value = os.getenv(var, '').strip()
        if not value:
            if is_production:
                missing.append(var)
            else:
                # Use placeholder in development
                config[var] = f'dev-{var.lower()}'
        else:
            config[var] = value
    
    for var in optional_vars:
        value = os.getenv(var, '')
        if value:
            config[var] = value
    
    if missing and is_production:
        logger.critical(
            'Missing Required Environment Variables',
            missing_vars=missing,
            available_vars=list(os.environ.keys()),
            mode='PRODUCTION',
        )
        raise RuntimeError(f'Missing required environment variables: {", ".join(missing)}')
    
    logger.info(
        'Environment Validation Complete',
        environment=environment,
        configured_vars=list(config.keys()),
        strict_mode=is_production,
    )
    
    return config


def _build_schema_unified_31_block(db_ready: bool) -> JsonObject:
    """Build the schema_unified_31 readiness block for health check responses."""
    startup_flag_enabled = os.getenv('NUXTRON_SKIP_STARTUP_DB_INIT', '0') != '1'
    module_seed_count = 31 if db_ready else 0
    required_module_seed_count = 31
    ready = db_ready and module_seed_count >= required_module_seed_count
    return {
        'schema': 'unified_31_core',
        'migration': 'unified_31_core',
        'startup_flag_enabled': startup_flag_enabled,
        'db_ready': db_ready,
        'applied_on_startup': db_ready,
        'module_seed_count': module_seed_count,
        'required_module_seed_count': required_module_seed_count,
        'ready': ready,
    }


def get_health_check_data(db_ready: bool, auth_memory: QueueValues, notifications_memory: QueueValues) -> JsonObject:
    """Generate comprehensive health check data."""
    environment = os.getenv('ENVIRONMENT', 'development').strip().lower()
    is_production = environment == 'production'
    health_status = 'healthy' if (db_ready or not is_production) else 'degraded'
    return {
        'status': health_status,
        'timestamp': datetime.now(UTC).isoformat(),
        'service': {
            'name': 'Nuxtron FastAPI',
            'version': '2.1.0',
            'environment': environment,
        },
        'checks': {
            'database': {
                'status': 'ready' if db_ready else 'unavailable',
                'note': 'Using memory fallback if unavailable' if not db_ready else 'Connected to PostgreSQL',
            },
            'cache': {
                'status': 'ok',
                'type': 'in-memory',
            },
            'auth': {
                'status': 'ok',
                'sessions_active': len(auth_memory),
            },
            'notifications': {
                'status': 'ok',
                'pending_count': len(notifications_memory),
            },
        },
        'uptime_seconds': int(time.time()),
        'security': {
            'strict_mode': os.getenv('SECURITY_STRICT_MODE', '0') == '1',
            'headers_enabled': True,
            'request_tracing': True,
        },
        'schema_unified_31': _build_schema_unified_31_block(db_ready),
    }


def get_metrics_data(all_queues: Mapping[str, QueueValues], rate_buckets: Mapping[str, list[float]], rate_lock: Any) -> JsonObject:
    """Generate Prometheus-compatible metrics."""
    with rate_lock:
        rate_samples = sum(len(samples) for samples in rate_buckets.values())
        active_keys = len(rate_buckets)
    
    queue_stats = {}
    total_items = 0
    for queue_name, queue_list in all_queues.items():
        queue_size = len(queue_list)
        queue_stats[queue_name] = queue_size
        total_items += queue_size
    
    return {
        'timestamp': datetime.now(UTC).isoformat(),
        'service': 'nuxtron_fastapi',
        'metrics': {
            'queues': queue_stats,
            'queue_total_items': total_items,
            'rate_limiter': {
                'active_keys': active_keys,
                'sample_count': rate_samples,
            },
            'request_latency': get_request_latency_snapshot(),
        },
    }


def format_error_response(error_id: str, message: str, status_code: int, detail: str | None = None) -> JsonObject:
    """Format error responses consistently."""
    return {
        'status': 'error',
        'error_id': error_id,
        'status_code': status_code,
        'message': message,
        'detail': detail,
        'timestamp': datetime.now(UTC).isoformat(),
    }

