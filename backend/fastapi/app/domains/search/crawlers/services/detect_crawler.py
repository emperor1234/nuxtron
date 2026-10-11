"""Search/Crawlers service: detect crawler."""

from __future__ import annotations
from ..constants import _CRAWLER_COMPILED
from typing import Any


def _detect_crawler(user_agent: str) -> dict[str, Any] | None:
    """Return first matching crawler record or None if no match."""
    for crawler in _CRAWLER_COMPILED:
        if crawler["_re"].search(user_agent):
            return {k: v for k, v in crawler.items() if k != "_re"}
    return None
