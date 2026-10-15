"""Fail-closed boundary for provider-backed rank tracking."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, NoReturn

from fastapi import HTTPException

RANK_TRACKING_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Verified rank-position provider data and durable tracking are not configured. "
        "Use Rank Position Review for a user-supplied export."
    ),
}

RANK_TRACKING_501_RESPONSE = {
    "description": "Verified rank-position data and durable tracking are unavailable.",
    "content": {"application/json": {"example": {"detail": RANK_TRACKING_UNAVAILABLE_DETAIL}}},
}


def raise_rank_tracking_unavailable() -> NoReturn:
    raise HTTPException(status_code=501, detail=RANK_TRACKING_UNAVAILABLE_DETAIL)


async def analyze_rank_tracking(
    *,
    domain: str,
    tracked_keywords: list[str],
    historical_lookback_days: int,
    include_competitor_tracking: bool,
    competitor_domains: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
    llm_timeout_seconds: float | None = None,
) -> NoReturn:
    """Retain the compatibility signature but never fabricate measured positions."""
    _ = (
        domain,
        tracked_keywords,
        historical_lookback_days,
        include_competitor_tracking,
        competitor_domains,
        notes,
        ollama_json_fn,
        system_prompt,
        clean_text_fn,
        llm_timeout_seconds,
    )
    raise_rank_tracking_unavailable()
