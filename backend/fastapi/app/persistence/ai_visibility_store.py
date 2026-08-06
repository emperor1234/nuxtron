from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return datetime.now(UTC)


def _default_db_path() -> Path:
    explicit = os.getenv("AI_VISIBILITY_DB_PATH", "").strip()
    if explicit:
        return Path(explicit)

    data_dir = os.getenv("NUXTRON_DATA_DIR", "").strip()
    if data_dir:
        return Path(data_dir) / "ai_visibility.db"

    # Fallback to repository-local storage for developer environments.
    return Path.cwd() / "storage" / "ai_visibility.db"


class AiVisibilityStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _default_db_path()
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS answer_engine_mentions (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    brand_name TEXT NOT NULL,
                    search_engine TEXT NOT NULL,
                    query TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    source_url TEXT,
                    sentiment TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp_iso TEXT NOT NULL,
                    created_at_iso TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS ix_ae_mentions_tenant_brand_ts
                    ON answer_engine_mentions (tenant_id, brand_name, timestamp_iso DESC);

                CREATE TABLE IF NOT EXISTS prompt_volume_events (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    keyword_type TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    brand_name TEXT,
                    context TEXT,
                    relevance_score REAL NOT NULL,
                    observed_at_iso TEXT NOT NULL,
                    created_at_iso TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS ix_prompt_events_tenant_ts
                    ON prompt_volume_events (tenant_id, observed_at_iso DESC);
                """
            )

    def replace_brand_mentions(self, tenant_id: str, brand_name: str, mentions: Iterable[dict[str, Any]]) -> int:
        rows = list(mentions)
        now_iso = _utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                "DELETE FROM answer_engine_mentions WHERE tenant_id = ? AND brand_name = ?",
                (tenant_id, brand_name),
            )
            for row in rows:
                mention_id = str(row.get("id") or "").strip() or os.urandom(8).hex()
                ts = _parse_iso(str(row.get("timestamp") or now_iso)).isoformat()
                conn.execute(
                    """
                    INSERT INTO answer_engine_mentions (
                        id, tenant_id, brand_name, search_engine, query, answer_text, source_url,
                        sentiment, confidence, timestamp_iso, created_at_iso
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mention_id,
                        tenant_id,
                        brand_name,
                        str(row.get("search_engine") or "unknown"),
                        str(row.get("query") or ""),
                        str(row.get("answer_text") or ""),
                        str(row.get("source_url") or "") or None,
                        str(row.get("sentiment") or "neutral"),
                        float(row.get("confidence") or 0.0),
                        ts,
                        now_iso,
                    ),
                )
            return len(rows)

    def get_mentions(
        self,
        *,
        tenant_id: str,
        brand_name: str,
        sentiment: str | None = None,
        engine: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT id, tenant_id, brand_name, search_engine, query, answer_text, source_url,
                   sentiment, confidence, timestamp_iso
            FROM answer_engine_mentions
            WHERE tenant_id = ? AND brand_name = ?
        """
        params: list[Any] = [tenant_id, brand_name]
        if sentiment:
            query += " AND sentiment = ?"
            params.append(sentiment)
        if engine:
            query += " AND search_engine = ?"
            params.append(engine)
        query += " ORDER BY timestamp_iso DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        with self._lock, self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def get_mentions_for_window(self, *, tenant_id: str, brand_name: str, days: int) -> list[dict[str, Any]]:
        cutoff = (datetime.now(UTC) - timedelta(days=max(days, 1))).isoformat()
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, tenant_id, brand_name, search_engine, query, answer_text, source_url,
                       sentiment, confidence, timestamp_iso
                FROM answer_engine_mentions
                WHERE tenant_id = ? AND brand_name = ? AND timestamp_iso >= ?
                ORDER BY timestamp_iso DESC
                """,
                (tenant_id, brand_name, cutoff),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_all_mentions_for_brand(self, *, tenant_id: str, brand_name: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, tenant_id, brand_name, search_engine, query, answer_text, source_url,
                       sentiment, confidence, timestamp_iso
                FROM answer_engine_mentions
                WHERE tenant_id = ? AND brand_name = ?
                ORDER BY timestamp_iso DESC
                """,
                (tenant_id, brand_name),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_prompt_event(
        self,
        *,
        tenant_id: str,
        keyword: str,
        keyword_type: str,
        sources: list[str],
        brand_name: str,
        context: str | None,
        relevance_score: float,
        observed_at_iso: str,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO prompt_volume_events (
                    id, tenant_id, keyword, keyword_type, sources_json, brand_name, context,
                    relevance_score, observed_at_iso, created_at_iso
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    os.urandom(8).hex(),
                    tenant_id,
                    keyword,
                    keyword_type,
                    json.dumps(sources),
                    brand_name,
                    context,
                    relevance_score,
                    observed_at_iso,
                    _utc_now_iso(),
                ),
            )

    def get_prompt_events(
        self,
        *,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
        brand_name: str | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT keyword, keyword_type, sources_json, brand_name, context, relevance_score, observed_at_iso
            FROM prompt_volume_events
            WHERE tenant_id = ? AND observed_at_iso >= ? AND observed_at_iso <= ?
        """
        params: list[Any] = [tenant_id, period_start.astimezone(UTC).isoformat(), period_end.astimezone(UTC).isoformat()]
        if brand_name:
            query += " AND brand_name = ?"
            params.append(brand_name)
        query += " ORDER BY observed_at_iso DESC"

        with self._lock, self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        output: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            try:
                payload["sources"] = [str(item) for item in json.loads(str(payload.pop("sources_json", "[]")))]
            except json.JSONDecodeError:
                payload["sources"] = []
            output.append(payload)
        return output

_store: AiVisibilityStore | None = None
_store_lock = threading.Lock()


def get_ai_visibility_store() -> AiVisibilityStore:
    global _store
    if _store is not None:
        return _store
    with _store_lock:
        if _store is None:
            _store = AiVisibilityStore()
        return _store
