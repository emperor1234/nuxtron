"""Synchronized process-local generated asset store."""

from __future__ import annotations

import threading
from collections.abc import Callable

from . import memory_stores

JsonObject = dict[str, object]

ai_generated_assets = memory_stores.ai_generated_assets
ai_generated_assets_lock = threading.Lock()
_next_asset_id = 1
_MAX_ASSETS = 2000
_TRIM_COUNT = 500


def append_generated_asset(build_record: Callable[[int], JsonObject]) -> JsonObject:
    """Allocate a monotonic ID and append one record atomically."""
    global _next_asset_id
    with ai_generated_assets_lock:
        asset_id = _next_asset_id
        _next_asset_id += 1
        # File persistence intentionally runs under this owner lock: a record
        # must never become visible to readers before its referenced file exists.
        record = build_record(asset_id)
        record['id'] = asset_id
        ai_generated_assets.append(record)
        if len(ai_generated_assets) > _MAX_ASSETS:
            del ai_generated_assets[:_TRIM_COUNT]
        return record


def find_generated_asset(asset_id: int, tenant_id: str) -> JsonObject | None:
    """Return a detached asset record visible to one tenant."""
    with ai_generated_assets_lock:
        for record in ai_generated_assets:
            if record.get('id') == asset_id and str(record.get('tenant_id', '')) == tenant_id:
                return dict(record)
    return None


def reset_generated_assets_for_tests() -> None:
    """Clear records and safely restart the test-only ID sequence."""
    global _next_asset_id
    with ai_generated_assets_lock:
        ai_generated_assets.clear()
        _next_asset_id = 1
