"""Contract tests for the unavailable server-side International SEO analyzer."""

import pytest
from backend.fastapi.app.domains.seo.services.seo_international_multilingual_service import (
    raise_international_multilingual_unavailable,
)
from fastapi import HTTPException


def test_server_side_international_analysis_fails_closed() -> None:
    with pytest.raises(HTTPException) as exc_info:
        raise_international_multilingual_unavailable()

    assert exc_info.value.status_code == 501
    assert exc_info.value.detail["code"] == "NOT_IMPLEMENTED"
    assert "reciprocal hreflang links" in exc_info.value.detail["message"]
    assert "browser-local Hreflang & Locale Review" in exc_info.value.detail["message"]
