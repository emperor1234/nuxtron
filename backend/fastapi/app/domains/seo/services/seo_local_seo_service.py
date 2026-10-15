"""Fail-closed boundary for provider-backed Local SEO analysis."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, NoReturn

from fastapi import HTTPException

LOCAL_SEO_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": "Verified business-profile, citation, review, and local-demand sources are not connected. No local score or search volume is generated.",
}

LOCAL_SEO_501_RESPONSE = {
    "description": "Verified Local SEO provider data are unavailable.",
    "content": {"application/json": {"example": {"detail": LOCAL_SEO_UNAVAILABLE_DETAIL}}},
}


def raise_local_seo_unavailable() -> NoReturn:
    raise HTTPException(status_code=501, detail=LOCAL_SEO_UNAVAILABLE_DETAIL)


async def optimize_local_seo(
    *,
    business_name: str,
    category: str,
    location: str,
    website: str,
    description: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> NoReturn:
    """Keep the compatibility signature without inventing local SEO evidence."""
    _ = (business_name, category, location, website, description, ollama_json_fn, system_prompt, clean_text_fn)
    raise_local_seo_unavailable()
