"""Structured logging filters & a JSON formatter.

Wires the per-request correlation id into every log record so that logs can be
filtered by request across all services. In production we emit JSON so that the
log aggregator (Loki / Datadog / CloudWatch) can parse fields without regex.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from django.http import HttpRequest

from .middleware import get_request_id


class RequestIDFilter(logging.Filter):
    """Inject `request_id` into every record (empty string when unavailable)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'request_id'):
            record.request_id = '-'
        return True


class JsonFormatter(logging.Formatter):
    """Single-line JSON log formatter compatible with container log collectors."""

    _RESERVED = {
        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
        'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
        'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
        'processName', 'process', 'message', 'asctime', 'taskName',
    }

    def format(self, record: logging.LogRecord) -> str:
        # Base fields.
        payload: dict[str, Any] = {
            'ts': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', '-'),
        }
        # Caller / exception context.
        if record.exc_info:
            payload['exc'] = self.formatException(record.exc_info)
        # Extra fields from logger.X(..., extra={...}).
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith('_'):
                payload[key] = value
        return json.dumps(payload, default=str)


def bind_request(request: HttpRequest) -> None:
    """Attach request context to logging's extra for the current call frame.

    Convenience used by views; the middleware already set request_id on the
    request object. We use LogAdapter-style local scoping via LoggerAdapter at
    call sites instead of thread-local globals to keep state explicit.
    """
    # Intentionally a no-op placeholder: we expose `request_logger()` below for
    # explicit adapter use. Kept for future contextvar-based binding.
    _ = request


class _RequestLogger(logging.LoggerAdapter):
    """LoggerAdapter that stamps `request_id` onto every emitted record."""

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        extra = dict(self.extra or {})
        extra.setdefault('request_id', '-')
        kwargs.setdefault('extra', {}).update(extra)
        return msg, kwargs


def request_logger(request: HttpRequest, name: str = 'platform_api') -> logging.LoggerAdapter:
    """Return a logger adapter bound to the request's correlation id."""
    return _RequestLogger(logging.getLogger(name), {'request_id': get_request_id(request) or '-'})


# Ensure stderr is line-buffered so container runtimes see logs promptly.
try:
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    pass
