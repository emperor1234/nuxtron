"""Uniform exception-handling middleware (WO-9).

Catches every unhandled exception, logs it with the request correlation id,
and returns a generic 500 envelope ``{"error": "internal_server_error",
"request_id": ...}`` so that full tracebacks never reach the client. The shape
matches the FastAPI ``GlobalExceptionHandler`` envelope so clients integrating
with both services see one error contract.
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

from platform_api.middleware import get_request_id

logger = logging.getLogger('nuxtron.errors')


class UncaughtExceptionMiddleware:
    """Last-resort 500 handler; never leaks a traceback to the response body."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            response = self.get_response(request)
        except Exception:
            request_id = get_request_id(request) or str(uuid.uuid4())
            logger.exception('unhandled_exception', extra={'request_id': request_id})
            return JsonResponse(
                {'error': 'internal_server_error', 'request_id': request_id},
                status=500,
            )
        return response
