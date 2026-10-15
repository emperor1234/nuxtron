"""Fail-closed boundary for provider-verified review analysis."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, NoReturn

from fastapi import HTTPException

REVIEW_REPUTATION_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": "Connected review-provider data and durable reputation history are unavailable. No review counts, ratings, or themes are generated.",
}

REVIEW_REPUTATION_501_RESPONSE = {
    "description": "Verified review-provider data are unavailable.",
    "content": {"application/json": {"example": {"detail": REVIEW_REPUTATION_UNAVAILABLE_DETAIL}}},
}


def raise_review_reputation_unavailable() -> NoReturn:
    raise HTTPException(status_code=501, detail=REVIEW_REPUTATION_UNAVAILABLE_DETAIL)


async def analyze_review_reputation(
    *,
    brand: str,
    reviews_text: str,
    platforms: list[str],
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> NoReturn:
    """Keep the legacy signature while refusing unsupported provider claims."""
    _ = (brand, reviews_text, platforms, notes, ollama_json_fn, system_prompt, clean_text_fn)
    raise_review_reputation_unavailable()
