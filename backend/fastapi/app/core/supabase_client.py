"""In-memory Supabase-like client used by intelligence routes and tests."""

from __future__ import annotations

import copy
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class _Result:
    data: list[dict[str, Any]] | dict[str, Any] | None


_STORE_LOCK = threading.Lock()
_STORE: dict[str, list[dict[str, Any]]] = {
    "intel_targets": [],
    "intel_social_posts": [],
    "intel_ads": [],
    "intel_trends": [],
    "intel_reports": [],
    "intel_content_context": [],
    "intel_roi_predictions": [],
    "organizations": [],
}


def _deepcopy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [copy.deepcopy(r) for r in rows]


def _ensure_defaults(table: str, row: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(row)
    payload.setdefault("id", str(uuid.uuid4()))
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    payload.setdefault("updated_at", datetime.utcnow().isoformat())
    return payload


class _Query:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self._selected = "*"
        self._eq_filters: list[tuple[str, Any]] = []
        self._gte_filters: list[tuple[str, Any]] = []
        self._limit: int | None = None
        self._order_by: str | None = None
        self._order_desc = False
        self._single = False
        self._pending_insert: list[dict[str, Any]] | None = None
        self._pending_upsert: tuple[list[dict[str, Any]], str | None] | None = None
        self._pending_update: dict[str, Any] | None = None

    def select(self, selected: str) -> _Query:
        self._selected = selected
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def gte(self, key: str, value: Any) -> _Query:
        self._gte_filters.append((key, value))
        return self

    def limit(self, value: int) -> _Query:
        self._limit = value
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self._order_by = key
        self._order_desc = desc
        return self

    def single(self) -> _Query:
        self._single = True
        return self

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> _Query:
        if isinstance(payload, list):
            self._pending_insert = payload
        else:
            self._pending_insert = [payload]
        return self

    def upsert(self, payload: dict[str, Any] | list[dict[str, Any]], on_conflict: str | None = None) -> _Query:
        rows = payload if isinstance(payload, list) else [payload]
        self._pending_upsert = (rows, on_conflict)
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._pending_update = payload
        return self

    def execute(self) -> _Result:
        with _STORE_LOCK:
            rows = _STORE.setdefault(self.table_name, [])

            if self._pending_insert is not None:
                created: list[dict[str, Any]] = []
                for row in self._pending_insert:
                    normalized = _ensure_defaults(self.table_name, row)
                    rows.append(normalized)
                    created.append(copy.deepcopy(normalized))
                return _Result(data=created)

            if self._pending_upsert is not None:
                payload_rows, on_conflict = self._pending_upsert
                conflict_keys = [k.strip() for k in (on_conflict or "id").split(",") if k.strip()]
                updated: list[dict[str, Any]] = []
                for row in payload_rows:
                    normalized = _ensure_defaults(self.table_name, row)
                    found_index = None
                    for i, existing in enumerate(rows):
                        if all(existing.get(k) == normalized.get(k) for k in conflict_keys):
                            found_index = i
                            break
                    if found_index is None:
                        rows.append(normalized)
                        updated.append(copy.deepcopy(normalized))
                    else:
                        merged = {**rows[found_index], **normalized, "updated_at": datetime.utcnow().isoformat()}
                        rows[found_index] = merged
                        updated.append(copy.deepcopy(merged))
                return _Result(data=updated)

            if self._pending_update is not None:
                count = 0
                out: list[dict[str, Any]] = []
                for i, existing in enumerate(rows):
                    if self._matches(existing):
                        merged = {**existing, **self._pending_update, "updated_at": datetime.utcnow().isoformat()}
                        rows[i] = merged
                        out.append(copy.deepcopy(merged))
                        count += 1
                return _Result(data=out if count else [])

            filtered = [r for r in rows if self._matches(r)]

            if self._order_by:
                filtered.sort(key=lambda x: x.get(self._order_by), reverse=self._order_desc)

            if self._limit is not None:
                filtered = filtered[: self._limit]

            if "intel_targets(" in self._selected and self.table_name in {"intel_social_posts", "intel_ads"}:
                targets_by_id = {t.get("id"): t for t in _STORE.get("intel_targets", [])}
                for row in filtered:
                    target = targets_by_id.get(row.get("target_id"), {})
                    row["intel_targets"] = {
                        "name": target.get("name"),
                        "domain": target.get("domain"),
                        "category": target.get("category"),
                    }

            if self._single:
                return _Result(data=copy.deepcopy(filtered[0]) if filtered else None)

            return _Result(data=_deepcopy_rows(filtered))

    def _matches(self, row: dict[str, Any]) -> bool:
        for key, value in self._eq_filters:
            if row.get(key) != value:
                return False
        for key, value in self._gte_filters:
            current = row.get(key, 0)
            try:
                if current < value:
                    return False
            except TypeError:
                return False
        return True


class _SupabaseCompat:
    def table(self, table_name: str) -> _Query:
        return _Query(table_name)


_SUPABASE_SINGLETON = _SupabaseCompat()


def get_supabase() -> _SupabaseCompat:
    return _SUPABASE_SINGLETON
