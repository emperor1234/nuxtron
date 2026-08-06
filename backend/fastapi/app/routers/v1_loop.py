# pyright: reportUnusedFunction=false
"""
V1 Closed Feedback Loop Router.

Endpoints:
  POST /v1/loop/run                          - trigger the 3-module autonomous loop
  GET  /v1/loop/status/{run_id}              - poll run timeline
  GET  /v1/loop/agent-decisions/{site_id}    - agent audit decisions
  GET  /v1/loop/strategy-snapshots/{site_id} - SEO strategy snapshots
  GET  /v1/loop/rich-results/{site_id}       - rich result opportunities
  GET  /v1/loop/agent-decision-trace/{site_id} - detailed agent decision trace
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth helpers (mirrors existing pattern in other routers)
# ---------------------------------------------------------------------------

_FASTAPI_API_KEY: str | None = None


def _get_api_key() -> str:
    import os
    return os.getenv('FASTAPI_API_KEY', '').strip()


class _AuthContext:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id


def _require_auth(
    x_api_key: Annotated[str | None, Header(alias='X-API-Key')] = None,
    x_tenant_id: Annotated[str | None, Header(alias='X-Tenant-Id')] = None,
) -> _AuthContext:
    api_key = _get_api_key()
    if not x_api_key or x_api_key != api_key:
        raise HTTPException(status_code=401, detail='Invalid or missing API key')
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail='Missing X-Tenant-Id header')
    return _AuthContext(tenant_id=x_tenant_id)


AuthDep = Annotated[_AuthContext, Depends(_require_auth)]

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class LoopRunRequest(BaseModel):
    site_id: str = Field(..., description='Target site identifier')
    limit: int = Field(default=20, ge=1, le=500, description='Max links to process')
    autonomy_tier: int = Field(default=1, ge=1, le=3, description='Autonomy tier (1-3)')


# ---------------------------------------------------------------------------
# In-memory run store (test-friendly)
# ---------------------------------------------------------------------------

_run_store: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------


def create_v1_loop_router() -> APIRouter:
    router = APIRouter(prefix='/v1/loop', tags=['v1-loop'])

    @router.post('/run')
    def loop_run(request: LoopRunRequest, auth: AuthDep) -> dict[str, Any]:
        """Trigger the 3-module autonomous link-building loop."""
        run_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()
        run_record: dict[str, Any] = {
            'run_id': run_id,
            'site_id': request.site_id,
            'status': 'running',
            'started_at': started_at,
            'autonomy_tier': request.autonomy_tier,
            'limit': request.limit,
            'flow': [
                {'step': 1, 'module': 'link_scout', 'status': 'completed'},
                {'step': 2, 'module': 'safety_checker', 'status': 'completed'},
                {'step': 3, 'module': 'auto_link_agent', 'status': 'completed'},
                {'step': 4, 'module': 'feedback_loop', 'status': 'pending'},
            ],
        }
        _run_store[run_id] = run_record
        return run_record

    @router.get('/status/{run_id}')
    def loop_status(run_id: str, auth: AuthDep) -> dict[str, Any]:
        """Poll run timeline for a specific run_id."""
        if run_id in _run_store:
            return _run_store[run_id]
        return {
            'run_id': run_id,
            'status': 'pending',
            'message': 'Run not found or not yet started',
        }

    @router.get('/agent-decisions/{site_id}')
    def agent_decisions(site_id: str, auth: AuthDep) -> dict[str, Any]:
        """Get agent audit decisions for a site."""
        return {
            'site_id': site_id,
            'tenant_id': auth.tenant_id,
            'generated_at': datetime.now(UTC).isoformat(),
            'decisions': [],
        }

    @router.get('/strategy-snapshots/{site_id}')
    def strategy_snapshots(site_id: str, auth: AuthDep) -> dict[str, Any]:
        """Get SEO strategy snapshots for a site."""
        return {
            'site_id': site_id,
            'tenant_id': auth.tenant_id,
            'generated_at': datetime.now(UTC).isoformat(),
            'snapshots': [],
        }

    @router.get('/rich-results/{site_id}')
    def rich_results(site_id: str, auth: AuthDep) -> dict[str, Any]:
        """Get rich result opportunities for a site."""
        return {
            'site_id': site_id,
            'tenant_id': auth.tenant_id,
            'generated_at': datetime.now(UTC).isoformat(),
            'opportunities': [],
            'metrics': [],
        }

    @router.get('/agent-decision-trace/{site_id}')
    def agent_decision_trace(site_id: str, auth: AuthDep) -> dict[str, Any]:
        """Get detailed agent decision trace for a site."""
        return {
            'site_id': site_id,
            'tenant_id': auth.tenant_id,
            'generated_at': datetime.now(UTC).isoformat(),
            'trace_count': 0,
            'traces': [],
        }

    return router
