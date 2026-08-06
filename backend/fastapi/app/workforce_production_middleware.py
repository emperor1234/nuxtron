"""
Autonomous Workforce Production Middleware

Provides production-grade logging, request tracking, error context, and security controls.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Production logger with structured JSON output
_logger = logging.getLogger("workforce")


class WorkforceLogger:
    """Structured logging for production deployment."""

    @staticmethod
    def configure_json_logging(
        log_level: str = "INFO",
        log_file: str | None = None,
    ) -> None:
        """Configure JSON structured logging."""
        _logger.setLevel(log_level.upper())

        # JSON handler for structured output
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)

        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            _logger.addHandler(file_handler)

    @staticmethod
    def log_external_api_call(
        request_id: str,
        provider: str,
        method: str,
        url: str,
        status_code: int,
        latency_seconds: float,
        error: str | None = None,
    ) -> None:
        """Log external API call with full context."""
        context = {
            "event": "external_api_call",
            "request_id": request_id,
            "provider": provider,
            "method": method,
            "url": url[:100],  # Truncate URL for safety
            "status_code": status_code,
            "latency_seconds": round(latency_seconds, 3),
            "error": error,
        }
        _logger.info(json.dumps(context))

    @staticmethod
    def log_mission_event(
        request_id: str,
        mission_id: str,
        event: str,
        role: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log mission state transitions."""
        context = {
            "event": "mission_event",
            "request_id": request_id,
            "mission_id": mission_id,
            "mission_event": event,
            "role": role,
            "status": status,
            "details": details or {},
        }
        _logger.info(json.dumps(context))

    @staticmethod
    def log_error(
        request_id: str,
        error_type: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log error with full context."""
        error_context = {
            "event": "error",
            "request_id": request_id,
            "error_type": error_type,
            "message": message,
            "context": context or {},
        }
        _logger.error(json.dumps(error_context))

    @staticmethod
    def log_provider_action(
        request_id: str,
        provider: str,
        action: str,
        success: bool,
        latency_seconds: float,
        error: str | None = None,
    ) -> None:
        """Log provider-specific action execution."""
        context = {
            "event": "provider_action",
            "request_id": request_id,
            "provider": provider,
            "action": action,
            "success": success,
            "latency_seconds": round(latency_seconds, 3),
            "error": error,
        }
        _logger.info(json.dumps(context))

    @staticmethod
    def log_retry_attempt(
        request_id: str,
        retry_id: str,
        provider: str,
        retry_count: int,
        max_retries: int,
        next_retry_at: str,
        reason: str | None = None,
    ) -> None:
        """Log retry queue actions."""
        context = {
            "event": "retry_attempt",
            "request_id": request_id,
            "retry_id": retry_id,
            "provider": provider,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "next_retry_at": next_retry_at,
            "reason": reason,
        }
        _logger.info(json.dumps(context))


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests for distributed tracing."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Store in state for downstream handlers
        request.state.request_id = request_id
        
        # Measure latency
        start_time = time.time()
        response = await call_next(request)
        latency = time.time() - start_time
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = str(round(latency, 3))
        
        # Log request completion
        level = "INFO" if response.status_code < 400 else "WARNING"
        context = {
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_seconds": round(latency, 3),
            "level": level,
        }
        getattr(_logger, level.lower())(json.dumps(context))
        
        return response


class CircuitBreaker:
    """Circuit breaker for external API calls to prevent cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.is_open = False

    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function through circuit breaker."""
        if self.is_open:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.is_open = False
                self.failure_count = 0
            else:
                raise RuntimeError("Circuit breaker is OPEN - service unavailable")

        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except self.expected_exception:
            self.on_failure()
            raise

    def on_success(self) -> None:
        """Reset failure counter on success."""
        self.failure_count = 0
        self.is_open = False

    def on_failure(self) -> None:
        """Increment failure counter and open circuit if threshold exceeded."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            _logger.warning(
                json.dumps({
                    "event": "circuit_breaker_opened",
                    "failure_count": self.failure_count,
                    "threshold": self.failure_threshold,
                })
            )


class ExponentialBackoff:
    """Exponential backoff with jitter for retry logic."""

    def __init__(
        self,
        base_seconds: int = 2,
        max_seconds: int = 300,
        multiplier: float = 2.0,
        jitter: bool = True,
    ):
        self.base_seconds = base_seconds
        self.max_seconds = max_seconds
        self.multiplier = multiplier
        self.jitter = jitter

    def get_wait_time(self, retry_count: int) -> int:
        """Calculate wait time in seconds for given retry count."""
        wait = min(
            int(self.base_seconds * (self.multiplier ** retry_count)),
            self.max_seconds,
        )
        
        if self.jitter:
            import random
            jitter_amount = random.randint(0, wait // 2)
            wait += jitter_amount
        
        return wait


class HealthCheck:
    """System health check for liveness/readiness probes."""

    def __init__(self):
        self.is_healthy = True
        self.checks: dict[str, Callable[[], bool]] = {}

    def register_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Register a health check function."""
        self.checks[name] = check_func

    async def run_all_checks(self) -> tuple[bool, dict[str, Any]]:
        """Run all registered checks and return overall status."""
        results: dict[str, dict[str, Any]] = {}
        all_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                is_ok = check_func()
                results[name] = {"ok": is_ok, "error": None}
                if not is_ok:
                    all_healthy = False
            except Exception as exc:
                results[name] = {"ok": False, "error": str(exc)[:200]}
                all_healthy = False
        
        return all_healthy, results

    def get_status(self) -> dict[str, Any]:
        """Get current health status."""
        return {
            "status": "healthy" if self.is_healthy else "unhealthy",
            "timestamp": time.time(),
        }


# Singleton instances
_request_id_middleware = RequestIDMiddleware.__name__
_logger_instance = WorkforceLogger()
_health_check = HealthCheck()  # type: ignore[no-untyped-call]
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create circuit breaker for provider."""
    if provider not in _circuit_breakers:
        _circuit_breakers[provider] = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
        )
    return _circuit_breakers[provider]


def get_logger() -> WorkforceLogger:
    """Get logger instance."""
    return _logger_instance


def get_health_check() -> HealthCheck:
    """Get health check instance."""
    return _health_check
