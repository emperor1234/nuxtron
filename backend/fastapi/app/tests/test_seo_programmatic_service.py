"""Fail-closed contract for server-side Programmatic SEO generation."""

import pytest
from backend.fastapi.app.domains.seo.services.seo_programmatic_service import raise_programmatic_seo_unavailable
from fastapi import HTTPException


def test_server_generation_is_typed_unavailable() -> None:
    with pytest.raises(HTTPException) as error:
        raise_programmatic_seo_unavailable()

    assert error.value.status_code == 501
    assert error.value.detail["code"] == "NOT_IMPLEMENTED"
    assert "browser-local draft preview" in error.value.detail["message"]
