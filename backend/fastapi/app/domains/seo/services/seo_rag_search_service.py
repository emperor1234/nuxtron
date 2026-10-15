"""Fail-closed boundary for server-backed semantic site retrieval."""

from typing import NoReturn

from fastapi import HTTPException

RAG_SEARCH_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Connected site crawling, document indexing, semantic retrieval, and source citations are not configured. "
        "This request did not access or save site content. Use Corpus Search Preview for browser-local matches "
        "against text you supply."
    ),
}


def raise_rag_search_unavailable() -> NoReturn:
    """Stop synthetic answers until a tenant-scoped retrieval source is connected."""
    raise HTTPException(status_code=501, detail=RAG_SEARCH_UNAVAILABLE)
