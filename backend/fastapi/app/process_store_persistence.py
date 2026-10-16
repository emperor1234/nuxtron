"""Durable snapshots for the process-local stores.

Many routers keep their records in plain dicts and lists (``memory_stores``
and per-router ``_store`` dicts). Those objects are shared by identity, so
this module keeps them where they are and makes them survive a restart:

* at startup every registered store is refilled in place from its last snapshot;
* a background thread writes any store whose contents changed;
* shutdown writes a final snapshot.

Snapshots go to the ``process_store_snapshots`` table when a database is
configured, otherwise to a JSON file (``NUXTRON_STATE_PATH``). Stores that hold
secrets are never written. This is one writer per deployment: with more than
one worker process each keeps its own copy, so run a single worker
(``WEB_CONCURRENCY=1``) until these records move to dedicated tables.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger('nuxtron.process_store_persistence')

TABLE = 'process_store_snapshots'
FLUSH_INTERVAL_SECONDS = 3.0

# Stores that hold credentials, tokens or short-lived state are never persisted.
_EXCLUDED_NAME = re.compile(r'token|credential|secret|oauth|session|provider_config|cache|api_key|password|rate', re.I)

# (module, attribute) pairs declared outside memory_stores that hold user records.
EXTRA_STORES: tuple[tuple[str, str], ...] = (
    ('routers.brandkit', '_kits'),
    ('routers.brandkit', '_knowledge_bases'),
    ('routers.brandkit', '_analytics'),
    ('routers.social_media_router', '_parity_content_store'),
    ('routers.social_media_router', '_parity_dm_templates_store'),
    ('routers.social_media_router', '_parity_listening_keywords_store'),
    ('routers.social_media_router', '_parity_team_invites_store'),
    ('routers.social_media_router', '_parity_review_replies_store'),
    ('routers.social_media_router', '_parity_owly_generations_store'),
    ('routers.social_media_router', '_parity_mentions_store'),
    ('routers.social_media_router', '_parity_comments_store'),
    ('routers.social_media_router', '_parity_reviews_store'),
    ('routers.social_media_router', '_parity_dm_events_store'),
    ('routers.competitor_analysis', '_competitors'),
    ('routers.competitor_analysis', '_competitor_ads'),
    ('routers.backlink_intelligence', '_domains'),
    ('routers.backlink_intelligence', '_backlinks'),
    ('routers.backlink_intelligence', '_audits'),
    ('routers.backlink_intelligence', '_prospects'),
    ('routers.rank_tracker', '_projects'),
    ('routers.rank_tracker', '_tracked_keywords'),
    ('routers.rank_tracker', '_competitors'),
    ('routers.rank_tracker', '_position_history'),
    ('routers.rank_tracker', '_alerts'),
    ('routers.social_posting', '_scheduled_posts'),
    ('routers.social_posting', '_post_analytics'),
    ('routers.social_posting', '_auto_post_jobs'),
    ('routers.contentshake_ai', '_drafts'),
    ('routers.ad_generation', '_ads'),
    ('routers.ad_generation', '_campaigns'),
    ('routers.ad_generation', '_avatars'),
    ('routers.ad_generation', '_analytics'),
    ('routers.pla_research', '_tracked_domains'),
    ('routers.predis_features', '_brand_kits_store'),
    ('routers.predis_features', '_calendar_events_store'),
    ('routers.predis_features', '_template_store'),
    ('routers.predis_features', '_auto_post_config_store'),
    ('routers.predis_features', '_asset_library'),
)

Store = dict | list


class SnapshotBackend(Protocol):
    def load_all(self) -> dict[str, str]: ...
    def save(self, name: str, payload: str) -> None: ...


class FileBackend:
    """One JSON file holding every snapshot; used when no database is configured."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def load_all(self) -> dict[str, str]:
        with self._lock:
            if not self.path.exists():
                return {}
            raw = json.loads(self.path.read_text(encoding='utf-8') or '{}')
        return {str(k): str(v) for k, v in raw.items()}

    def save(self, name: str, payload: str) -> None:
        with self._lock:
            current: dict[str, str] = {}
            if self.path.exists():
                current = json.loads(self.path.read_text(encoding='utf-8') or '{}')
            current[name] = payload
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(current), encoding='utf-8')
            os.replace(tmp, self.path)


class DbBackend:
    """Snapshots in the ``process_store_snapshots`` table (Postgres or SQLite)."""

    def __init__(self) -> None:
        from sqlalchemy import text

        from .database import get_db_session

        self._text = text
        self._session = get_db_session
        with self._session() as session:
            session.execute(
                text(
                    f'CREATE TABLE IF NOT EXISTS {TABLE} ('
                    'store_name VARCHAR(160) PRIMARY KEY, '
                    'payload TEXT NOT NULL, '
                    'updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)'
                )
            )

    def load_all(self) -> dict[str, str]:
        with self._session() as session:
            rows = session.execute(self._text(f'SELECT store_name, payload FROM {TABLE}')).all()
        return {str(name): str(payload) for name, payload in rows}

    def save(self, name: str, payload: str) -> None:
        text = self._text
        with self._session() as session:
            updated = session.execute(
                text(f'UPDATE {TABLE} SET payload = :p, updated_at = CURRENT_TIMESTAMP WHERE store_name = :n'),
                {'p': payload, 'n': name},
            ).rowcount
            if not updated:
                session.execute(text(f'INSERT INTO {TABLE} (store_name, payload) VALUES (:n, :p)'), {'n': name, 'p': payload})


def _default_backend() -> SnapshotBackend:
    from .database import _get_database_url

    if _get_database_url():
        try:
            return DbBackend()
        except Exception:
            logger.exception('Snapshot table unavailable; falling back to a state file.')
    default = Path(__file__).resolve().parent.parent / '.nuxtron-state' / 'process_stores.json'
    return FileBackend(Path(os.getenv('NUXTRON_STATE_PATH', '').strip() or default))


def is_persistable(name: str) -> bool:
    return not _EXCLUDED_NAME.search(name)


def discover_stores() -> dict[str, Store]:
    """Name every store that may be snapshotted. Names are stable across restarts."""
    from . import memory_stores

    found: dict[str, Store] = {}
    seen: set[int] = set()
    for attr, value in vars(memory_stores).items():
        if isinstance(value, dict | list) and not attr.startswith('_') and attr == attr.lower() and id(value) not in seen:
            found[f'memory_stores.{attr}'] = value
            seen.add(id(value))
    package = __package__ or 'backend.fastapi.app'
    for module_name, attr in EXTRA_STORES:
        full = f'{package}.{module_name}'
        module = sys.modules.get(full)
        if module is None:
            try:
                module = importlib.import_module(full)
            except Exception:
                continue
        value = getattr(module, attr, None)
        if isinstance(value, dict | list) and id(value) not in seen:
            found[f'{module_name}.{attr}'] = value
            seen.add(id(value))
    return {name: store for name, store in found.items() if is_persistable(name.rsplit('.', 1)[-1])}


def _reject(value: object) -> object:
    # Only plain JSON data round-trips. Objects, datetimes and sets would come back
    # as strings and break the code that reads them, so such stores stay in memory.
    raise TypeError(f'{type(value).__name__} is not plain JSON data')


def _brand_codec() -> tuple[Any, Any]:
    from .contexts.brand_management.public import Brand

    def encode(store: Any) -> Any:
        return {key: brand.model_dump(mode='json') for key, brand in dict(store).items()}

    def decode(data: Any) -> Any:
        return {key: Brand.model_validate(value) for key, value in data.items()}

    return encode, decode


# Stores that hold validated models instead of plain data rebuild them on restore.
_CODECS: dict[str, Any] = {'memory_stores.brand_hub_brands': _brand_codec}


def _encode(store: Store, name: str = '') -> str:
    if name in _CODECS:
        store = _CODECS[name]()[0](store)
    return json.dumps(store, default=_reject, separators=(',', ':'), sort_keys=False)


def _fill(store: Store, data: Any) -> None:
    """Replace the contents in place so every holder of the reference sees them."""
    if isinstance(store, list) and isinstance(data, list):
        store[:] = data
    elif isinstance(store, dict) and isinstance(data, dict):
        store.clear()
        store.update(data)


class ProcessStorePersistence:
    def __init__(self, backend: SnapshotBackend | None = None, stores: dict[str, Store] | None = None) -> None:
        self._backend = backend
        self._stores = stores
        self._digests: dict[str, str] = {}
        self._unsupported: set[str] = set()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def backend(self) -> SnapshotBackend:
        if self._backend is None:
            self._backend = _default_backend()
        return self._backend

    @property
    def stores(self) -> dict[str, Store]:
        if self._stores is None:
            self._stores = discover_stores()
        return self._stores

    def restore(self) -> int:
        """Refill stores from their snapshots. A bad snapshot is skipped, never fatal."""
        restored = 0
        try:
            snapshots = self.backend.load_all()
        except Exception:
            logger.exception('Could not read store snapshots; starting empty.')
            return 0
        for name, store in self.stores.items():
            payload = snapshots.get(name)
            if payload is None:
                continue
            try:
                data = json.loads(payload)
                if name in _CODECS:
                    data = _CODECS[name]()[1](data)
                _fill(store, data)
                self._digests[name] = hashlib.sha256(payload.encode()).hexdigest()
                restored += 1
            except Exception:
                logger.exception('Skipping unreadable snapshot for %s', name)
        return restored

    def flush(self) -> int:
        """Write every store whose contents changed since the last write."""
        written = 0
        for name, store in self.stores.items():
            try:
                payload = _encode(store, name)
            except RuntimeError:
                continue  # mutated while encoding; the next tick retries
            except Exception as exc:
                if name not in self._unsupported:
                    self._unsupported.add(name)
                    logger.warning('%s stays in memory only: %s', name, exc)
                continue
            digest = hashlib.sha256(payload.encode()).hexdigest()
            if self._digests.get(name) == digest or (name not in self._digests and payload in ('{}', '[]')):
                continue
            try:
                self.backend.save(name, payload)
                self._digests[name] = digest
                written += 1
            except Exception:
                logger.exception('Could not save snapshot for %s', name)
        return written

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if int(os.getenv('WEB_CONCURRENCY', '1') or '1') > 1:
            logger.warning('WEB_CONCURRENCY > 1: store snapshots are per process and will overwrite each other.')
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='process-store-flush', daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(FLUSH_INTERVAL_SECONDS):
            try:
                self.flush()
            except Exception:
                logger.exception('Store snapshot flush failed')

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        try:
            self.flush()
        except Exception:
            logger.exception('Final store snapshot failed')


_instance: ProcessStorePersistence | None = None


def get_persistence() -> ProcessStorePersistence:
    global _instance
    if _instance is None:
        _instance = ProcessStorePersistence()
    return _instance


def enabled() -> bool:
    """Snapshots are on by default; tests and one-off scripts opt out."""
    if os.getenv('PYTEST_CURRENT_TEST') or 'pytest' in sys.modules:
        return os.getenv('NUXTRON_PERSIST_STORES', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    return os.getenv('NUXTRON_PERSIST_STORES', '1').strip().lower() not in {'0', 'false', 'no', 'off'}
