"""Fail-closed tests for provider-backed Local SEO analysis."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_local_seo_service import (  # noqa: E402
    LOCAL_SEO_UNAVAILABLE_DETAIL,
    optimize_local_seo,
    raise_local_seo_unavailable,
)


def test_local_seo_unavailable_error_is_typed_501() -> None:
    with pytest.raises(HTTPException) as raised:
        raise_local_seo_unavailable()

    assert raised.value.status_code == 501
    assert raised.value.detail == LOCAL_SEO_UNAVAILABLE_DETAIL
    assert raised.value.detail["code"] == "NOT_IMPLEMENTED"


def test_local_seo_does_not_call_model_or_return_synthetic_metrics() -> None:
    model = AsyncMock(return_value={"local_seo_score": 99, "local_keywords": [{"keyword": "example", "monthly_searches": 900}]})

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            optimize_local_seo(
                business_name="Example",
                category="Services",
                location="Somewhere",
                website="https://example.com",
                description="User supplied business description",
                ollama_json_fn=model,
                system_prompt="must not be used",
                clean_text_fn=lambda text, _limit: text,
            )
        )

    assert raised.value.status_code == 501
    assert raised.value.detail["code"] == "NOT_IMPLEMENTED"
    model.assert_not_awaited()
