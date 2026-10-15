"""Fail-closed tests for provider-backed review reputation analysis."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_reviews_service import (  # noqa: E402
    REVIEW_REPUTATION_UNAVAILABLE_DETAIL,
    analyze_review_reputation,
    raise_review_reputation_unavailable,
)


def test_review_reputation_unavailable_is_typed_501() -> None:
    with pytest.raises(HTTPException) as raised:
        raise_review_reputation_unavailable()

    assert raised.value.status_code == 501
    assert raised.value.detail == REVIEW_REPUTATION_UNAVAILABLE_DETAIL
    assert raised.value.detail["code"] == "NOT_IMPLEMENTED"


def test_review_reputation_does_not_call_model_or_fabricate_counts() -> None:
    model = AsyncMock(return_value={"reputation_score": 100, "review_summary": {"total_reviews": 99}})

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            analyze_review_reputation(
                brand="Example",
                reviews_text="A real review supplied by the user.",
                platforms=["google"],
                notes="",
                ollama_json_fn=model,
                system_prompt="must not be used",
                clean_text_fn=lambda text, _limit: text,
            )
        )

    assert raised.value.status_code == 501
    assert raised.value.detail["code"] == "NOT_IMPLEMENTED"
    model.assert_not_awaited()
