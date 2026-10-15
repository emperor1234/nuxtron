"""Fail-closed contract for server-backed RAG search."""

from __future__ import annotations

import pytest
from backend.fastapi.app.seo_rag_search_service import raise_rag_search_unavailable
from fastapi import HTTPException

pytestmark = pytest.mark.no_legacy


def test_server_search_is_explicitly_unavailable_without_retrieval_sources() -> None:
    with pytest.raises(HTTPException) as error:
        raise_rag_search_unavailable()

    assert error.value.status_code == 501
    assert error.value.detail["code"] == "NOT_IMPLEMENTED"
    assert "source citations" in error.value.detail["message"]
