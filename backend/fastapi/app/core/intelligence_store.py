"""Thread-safe in-memory store used by intelligence routes and tests."""

from __future__ import annotations

import copy
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class StoreResult:
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
    return [copy.deepcopy(row) for row in rows]


def _ensure_defaults(row: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(row)
    now = datetime.now(UTC).isoformat()
    payload.setdefault("id", str(uuid.uuid4()))
    payload.setdefault("created_at", now)
    payload.setdefault("updated_at", now)
    return payload


class StoreQuery:
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

    def select(self, selected: str) -> StoreQuery:
        self._selected = selected
        return self

    def eq(self, key: str, value: Any) -> StoreQuery:
        self._eq_filters.append((key, value))
        return self

    def gte(self, key: str, value: Any) -> StoreQuery:
        self._gte_filters.append((key, value))
        return self

    def limit(self, value: int) -> StoreQuery:
        self._limit = value
        return self

    def order(self, key: str, desc: bool = False) -> StoreQuery:
        self._order_by = key
        self._order_desc = desc
        return self

    def single(self) -> StoreQuery:
        self._single = True
        return self

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> StoreQuery:
        self._pending_insert = payload if isinstance(payload, list) else [payload]
        return self

    def upsert(
        self,
        payload: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
    ) -> StoreQuery:
        rows = payload if isinstance(payload, list) else [payload]
        self._pending_upsert = (rows, on_conflict)
        return self

    def update(self, payload: dict[str, Any]) -> StoreQuery:
        self._pending_update = payload
        return self

    def execute(self) -> StoreResult:
        with _STORE_LOCK:
            rows = _STORE.setdefault(self.table_name, [])

            if self._pending_insert is not None:
                created = []
                for row in self._pending_insert:
                    normalized = _ensure_defaults(row)
                    rows.append(normalized)
                    created.append(copy.deepcopy(normalized))
                return StoreResult(data=created)

            if self._pending_upsert is not None:
                payload_rows, on_conflict = self._pending_upsert
                conflict_keys = [
                    key.strip()
                    for key in (on_conflict or "id").split(",")
                    if key.strip()
                ]
                updated = []
                for row in payload_rows:
                    normalized = _ensure_defaults(row)
                    found_index = next(
                        (
                            index
                            for index, existing in enumerate(rows)
                            if all(
                                existing.get(key) == normalized.get(key)
                                for key in conflict_keys
                            )
                        ),
                        None,
                    )
                    if found_index is None:
                        rows.append(normalized)
                        updated.append(copy.deepcopy(normalized))
                    else:
                        merged = {
                            **rows[found_index],
                            **normalized,
                            "updated_at": datetime.now(UTC).isoformat(),
                        }
                        rows[found_index] = merged
                        updated.append(copy.deepcopy(merged))
                return StoreResult(data=updated)

            if self._pending_update is not None:
                updated = []
                for index, existing in enumerate(rows):
                    if self._matches(existing):
                        merged = {
                            **existing,
                            **self._pending_update,
                            "updated_at": datetime.now(UTC).isoformat(),
                        }
                        rows[index] = merged
                        updated.append(copy.deepcopy(merged))
                return StoreResult(data=updated)

            filtered = [row for row in rows if self._matches(row)]

            if self._order_by:
                filtered.sort(
                    key=lambda row: row.get(self._order_by),
                    reverse=self._order_desc,
                )

            if self._limit is not None:
                filtered = filtered[: self._limit]

            if "intel_targets(" in self._selected and self.table_name in {
                "intel_social_posts",
                "intel_ads",
            }:
                targets_by_id = {
                    target.get("id"): target
                    for target in _STORE.get("intel_targets", [])
                }
                for row in filtered:
                    target = targets_by_id.get(row.get("target_id"), {})
                    row["intel_targets"] = {
                        "name": target.get("name"),
                        "domain": target.get("domain"),
                        "category": target.get("category"),
                    }

            if self._single:
                return StoreResult(
                    data=copy.deepcopy(filtered[0]) if filtered else None
                )

            return StoreResult(data=_deepcopy_rows(filtered))

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


class IntelligenceStore:
    def table(self, table_name: str) -> StoreQuery:
        return StoreQuery(table_name)


_STORE_SINGLETON = IntelligenceStore()


def get_intelligence_store() -> IntelligenceStore:
    return _STORE_SINGLETON
