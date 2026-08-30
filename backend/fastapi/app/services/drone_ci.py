"""Drone CI Integration Service

Extracted from legacy_main.py: Drone CI build triggering.
"""

from __future__ import annotations

import os
from fastapi import Depends
from datetime import UTC, datetime
from typing import Annotated, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ..deps import AuthContext

JsonObject = dict[str, object]
from ..deps import AuthContext, require_auth
AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Memory Store References (set by legacy_main.py) ──────────
_drone_builds_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores


def set_memory_stores(
    drone_builds_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
) -> None:
    global _drone_builds_memory, _rate_buckets, _rate_lock, _enforce_rate_limit
    if drone_builds_memory is not None:
        _drone_builds_memory = drone_builds_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit


# ── Drone CI ──────────────────────────────────────────────────


def drone_trigger_build(payload: DroneBuildTriggerRequest, auth: AuthDep) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:drone:trigger', limit=60, window_seconds=60)

    server = os.getenv('DRONE_SERVER', '').rstrip('/')
    token = os.getenv('DRONE_TOKEN', '').strip()

    if not server or not token:
        item: JsonObject = {
            'id': len(_drone_builds_memory) + 1,
            'tenant_id': auth.tenant_id,
            'repo': f'{payload.repo_owner}/{payload.repo_name}',
            'branch': payload.branch,
            'status': 'queued',
            'reason': 'Drone not configured',
            'params': payload.params,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _drone_builds_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    build_params = {k: str(v) for k, v in payload.params.items()}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{server}/api/repos/{payload.repo_owner}/{payload.repo_name}/builds',
                headers=headers,
                json={'branch': payload.branch, 'params': build_params},
            )
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'repo': f'{payload.repo_owner}/{payload.repo_name}',
                        'branch': payload.branch,
                        'build_number': data.get('number'),
                        'status': data.get('status'),
                        'delivery_status': 'triggered',
                    },
                }
    except Exception as ex:
        message = f'Drone request failed: {ex}'
        item: JsonObject = {
            'id': len(_drone_builds_memory) + 1,
            'tenant_id': auth.tenant_id,
            'repo': f'{payload.repo_owner}/{payload.repo_name}',
            'branch': payload.branch,
            'status': 'queued',
            'reason': message,
            'params': payload.params,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _drone_builds_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_drone_builds_memory) + 1,
        'tenant_id': auth.tenant_id,
        'repo': f'{payload.repo_owner}/{payload.repo_name}',
        'branch': payload.branch,
        'status': 'queued',
        'reason': 'Drone responded with non-success status',
        'params': payload.params,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _drone_builds_memory.append(item)
    return {'status': 'ok', 'result': item}


# ── Request Models ────────────────────────────────────────────

from pydantic import BaseModel, Field


class DroneBuildTriggerRequest(BaseModel):
    repo_owner: str = Field(min_length=1, max_length=120)
    repo_name: str = Field(min_length=1, max_length=120)
    branch: str = Field(default='main', min_length=1, max_length=120)
    params: dict[str, object] = Field(default_factory=dict)
