"""Fail-closed tests for provider-backed Rank Tracking."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_rank_tracking_service import (  # noqa: E402
    RANK_TRACKING_UNAVAILABLE_DETAIL,
    analyze_rank_tracking,
    raise_rank_tracking_unavailable,
)


def test_unavailable_error_is_typed_501() -> None:
    with pytest.raises(HTTPException) as raised:
        raise_rank_tracking_unavailable()

    assert raised.value.status_code == 501
    assert raised.value.detail == RANK_TRACKING_UNAVAILABLE_DETAIL
    assert raised.value.detail["code"] == "NOT_IMPLEMENTED"


def test_rank_analysis_fails_before_calling_model() -> None:
    model = AsyncMock(return_value={"tracking_score": 97, "ranking_history": []})

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            analyze_rank_tracking(
                domain="example.com",
                tracked_keywords=["seo tools"],
                historical_lookback_days=90,
                include_competitor_tracking=True,
                competitor_domains=["other.example"],
                notes="",
                ollama_json_fn=model,
                system_prompt="must not be used",
                clean_text_fn=lambda text, _limit: text,
            )
        )

    assert raised.value.status_code == 501
    assert raised.value.detail["code"] == "NOT_IMPLEMENTED"
    model.assert_not_awaited()
