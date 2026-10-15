"""Fail-closed contract for server-side Programmatic SEO generation."""

from typing import NoReturn

from fastapi import HTTPException

_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Server-side Programmatic SEO generation is unavailable until tenant-scoped content evidence, "
        "unique-value and URL-collision checks, and a reviewable publishing workflow are connected. "
        "Use the browser-local draft preview for template expansion."
    ),
}


def raise_programmatic_seo_unavailable() -> NoReturn:
    """Reject unsupported server-side generation without invoking a model or persisting a result."""
    raise HTTPException(status_code=501, detail=dict(_UNAVAILABLE_DETAIL))
