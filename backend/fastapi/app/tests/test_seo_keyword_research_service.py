"""Unit tests for the server-side keyword research availability contract."""

from __future__ import annotations

import pytest
from backend.fastapi.app.domains.seo.services.seo_keyword_research_service import (
    KEYWORD_RESEARCH_UNAVAILABLE_DETAIL,
    raise_keyword_research_unavailable,
)
from fastapi import HTTPException


def test_keyword_research_fails_closed_without_verified_provider_data() -> None:
    with pytest.raises(HTTPException) as error:
        raise_keyword_research_unavailable()

    assert error.value.status_code == 501
    assert error.value.detail == KEYWORD_RESEARCH_UNAVAILABLE_DETAIL
