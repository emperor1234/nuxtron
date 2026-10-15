"""Fail-closed contract for server-side International SEO analysis."""

from typing import NoReturn

from fastapi import HTTPException

_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Server-side International SEO analysis is unavailable until authenticated, tenant-scoped page data, "
        "canonical tags, reciprocal hreflang links, and locale coverage can be verified. "
        "Use the browser-local Hreflang & Locale Review for markup you provide."
    ),
}


def raise_international_multilingual_unavailable() -> NoReturn:
    """Reject unsupported readiness estimates without invoking a model or persisting a result."""
    raise HTTPException(status_code=501, detail=dict(_UNAVAILABLE_DETAIL))
