"""Fail-closed contract for server-side keyword discovery."""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

KEYWORD_RESEARCH_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Verified keyword data providers are not connected. Use Keyword Data Review to inspect an export you provide; "
        "Nuxtron does not generate search-volume, difficulty, intent, or competitor-gap metrics here."
    ),
}


def raise_keyword_research_unavailable() -> NoReturn:
    """Reject server-generated keyword metrics until source-level evidence is available."""
    raise HTTPException(status_code=501, detail=KEYWORD_RESEARCH_UNAVAILABLE_DETAIL)
