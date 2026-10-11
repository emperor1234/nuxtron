"""Legacy file-backed platform persistence adapter; not a distributed repository."""
from __future__ import annotations
from ..configuration import _is_production_env
from ..constants import _inbox_messages
from ..constants import _scheduled_posts
from ..constants import logger
from fastapi import HTTPException
from pathlib import Path
from typing import Any
import json
import os

def _schedule_store_path() -> Path:
    configured = os.getenv('PLATFORM_SCHEDULE_STORE_PATH', '').strip()
    if configured:
        return Path(configured)
    return Path('storage') / 'platform' / 'scheduled_posts.json'

def _inbox_store_path() -> Path:
    configured = os.getenv('PLATFORM_INBOX_STORE_PATH', '').strip()
    if configured:
        return Path(configured)
    return Path('storage') / 'platform' / 'inbox_messages.json'

def _load_json_store(path: Path, *, warning_label: str) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        logger.warning('Unable to load %s from %s', warning_label, path)
        return {}
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    for tenant_id, records in payload.items():
        if not isinstance(tenant_id, str) or not isinstance(records, list):
            continue
        normalized[tenant_id] = [record for record in records if isinstance(record, dict)]
    return normalized

def _load_scheduled_posts_store() -> dict[str, list[dict[str, Any]]]:
    return _load_json_store(_schedule_store_path(), warning_label='platform scheduled-post store')

def _load_inbox_messages_store() -> dict[str, list[dict[str, Any]]]:
    return _load_json_store(_inbox_store_path(), warning_label='platform inbox store')

def _persist_json_store(path: Path, payload: dict[str, list[dict[str, Any]]], *, error_label: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True), encoding='utf-8')
        return True
    except Exception:
        logger.exception('Unable to persist %s to %s', error_label, path)
        return False

def _persist_scheduled_posts_store() -> bool:
    return _persist_json_store(_schedule_store_path(), _scheduled_posts, error_label='platform scheduled-post store')

def _persist_inbox_messages_store() -> bool:
    return _persist_json_store(_inbox_store_path(), _inbox_messages, error_label='platform inbox store')

def _persist_scheduled_posts_or_raise() -> None:
    if _persist_scheduled_posts_store():
        return
    if _is_production_env():
        raise HTTPException(status_code=503, detail='Scheduled post persistence is unavailable in production.')

def _persist_inbox_messages_or_raise() -> None:
    if _persist_inbox_messages_store():
        return
    if _is_production_env():
        raise HTTPException(status_code=503, detail='Inbox state persistence is unavailable in production.')
