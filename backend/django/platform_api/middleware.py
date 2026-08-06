"""Request/response infrastructure: request-id propagation middleware."""

from __future__ import annotations

import uuid
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse

# Header names. We accept inbound IDs so distributed traces stitch together.
REQUEST_ID_HEADER = 'HTTP_X_REQUEST_ID'
RESPONSE_ID_HEADER = 'X-Request-ID'

_REQUEST_ID_ATTR = 'request_id'


def get_request_id(request: HttpRequest) -> str | None:
    """Return the request id attached to this request by the middleware."""
    return getattr(request, _REQUEST_ID_ATTR, None)


class RequestIDMiddleware:
    """Assign (or accept) a per-request correlation id and echo it on responses.

    Accepting an inbound id lets us propagate a trace id from the edge (ingress,
    API gateway) through Django and onward to the FastAPI service. We *validate*
    the inbound value rather than trusting arbitrary content: only UUID-shaped or
    short ASCII tokens are honored, otherwise we mint a fresh one. This avoids
    log-injection via crafted X-Request-Id payloads.
    """

    MAX_LEN = 128

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = self._extract_or_mint(request)
        setattr(request, _REQUEST_ID_ATTR, request_id)
        try:
            response = self.get_response(request)
        except Exception:
            # Logging happens in the view layer / exception handlers; just re-raise.
            raise
        response[RESPONSE_ID_HEADER] = request_id
        return response

    def _extract_or_mint(self, request: HttpRequest) -> str:
        raw = request.META.get(REQUEST_ID_HEADER, '').strip()
        if raw and self._is_valid(raw):
            return raw
        return uuid.uuid4().hex

    @classmethod
    def _is_valid(cls, value: str) -> bool:
        # UUID hex, UUID with dashes, or a conservative ASCII token.
        if not (1 <= len(value) <= cls.MAX_LEN):
            return False
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            pass
        return value.isascii() and all(c.isalnum() or c in '-_' for c in value)
