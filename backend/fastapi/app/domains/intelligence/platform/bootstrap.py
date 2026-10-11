"""Intelligence/Platform HTTP composition and legacy import exports."""

from __future__ import annotations
from .runtime import ContextRuntime
from fastapi import APIRouter
from typing import Any
from .api import (
    ai_safety_validate,
    recovery_status,
    get_agent_config,
)
from .services.observability import _agent_db_dsn as _agent_db_dsn
from .services.observability import _try_agent_db_query as _try_agent_db_query
from .services.observability import _try_agent_db_scalar as _try_agent_db_scalar
from .services.observability import _now as _now
from .services.observability import _sha256 as _sha256
from .services.observability import _uptime_seconds as _uptime_seconds
from .services.observability import _detect_hallucination_indicators as _detect_hallucination_indicators
from .services.observability import _validate_json_keys as _validate_json_keys
from .services.observability import _get_env_model_registry as _get_env_model_registry
from .services.observability import _record_lineage as _record_lineage
from .services.observability import _get_sla_metrics as _get_sla_metrics
from .schemas import AIValidateRequest as AIValidateRequest
from .schemas import AgentConfigUpdateRequest as AgentConfigUpdateRequest
from .schemas import RetryRequest as RetryRequest
from .schemas import PromptVersionCreateRequest as PromptVersionCreateRequest
from .schemas import AgentToolRegisterRequest as AgentToolRegisterRequest
from .constants import _agent_tool_calls as _agent_tool_calls
from .constants import _agent_config as _agent_config
from .constants import _agent_sessions as _agent_sessions
from .constants import _retry_counts as _retry_counts
from .constants import _PLATFORM_START_TS as _PLATFORM_START_TS
from .constants import _lineage_events as _lineage_events
from .constants import _prompt_versions as _prompt_versions
from .constants import AuthDep as AuthDep
from .constants import _DEFAULT_AGENT_TOOLS as _DEFAULT_AGENT_TOOLS
from .constants import _recovery_queue as _recovery_queue
import hashlib
import os
import time
from collections import defaultdict
from datetime import UTC
from datetime import datetime
from typing import Annotated
import psycopg
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from .... import memory_stores
from ....deps import AuthContext
from ....deps import require_auth
from ....production_middleware import get_request_latency_snapshot


def create_platform_intelligence_router(
    enforce_rate_limit: Any, audit_log_memory: list[dict[str, Any]], seo_jobs_fn: Any | None = None
) -> APIRouter:
    """
    Factory that creates the Platform Intelligence router.
    seo_jobs_fn: optional callable returning the _seo_jobs dict from seo_platform router.
    """
    router = APIRouter(prefix="/platform", tags=["Platform Intelligence"])
    runtime = ContextRuntime(
        audit_log_memory=audit_log_memory, enforce_rate_limit=enforce_rate_limit, seo_jobs_fn=seo_jobs_fn
    )
    ai_safety_validate.register(router, runtime)
    recovery_status.register(router, runtime)
    get_agent_config.register(router, runtime)
    return router
