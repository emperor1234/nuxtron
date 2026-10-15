"""Automation/Workforce HTTP composition and legacy import exports."""

from __future__ import annotations
from ....workforce_observability import MetricsCollector
from ....workforce_persistence import WorkforceDB
from .runtime import ContextRuntime
from .capabilities import WORKFORCE_API_UNAVAILABLE_RESPONSES
from .capabilities import require_workforce_api_available
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import os
import threading
from .api import (
    list_capabilities,
    list_missions,
    list_knowledge,
    search_knowledge,
)
from .services.mission_execution import _now_iso as _now_iso
from .services.mission_execution import _parse_iso_utc as _parse_iso_utc
from .services.mission_execution import _verify_provider_live_standalone as _verify_provider_live_standalone
from .services.mission_execution import _ai_gateway_url as _ai_gateway_url
from .services.mission_execution import _mission_system_prompt as _mission_system_prompt
from .services.mission_execution import _extract_ai_text as _extract_ai_text
from .services.mission_execution import _generate_mission_artifact as _generate_mission_artifact
from .services.mission_execution import _dispatch_provider_action as _dispatch_provider_action
from .services.run_autonomous_workforce_watchdog import (
    run_autonomous_workforce_watchdog as run_autonomous_workforce_watchdog,
)
from .schemas import MissionDecisionRequest as MissionDecisionRequest
from .schemas import WebhookTriggerRequest as WebhookTriggerRequest
from .schemas import MetricsQueryRequest as MetricsQueryRequest
from .schemas import ScheduleRequest as ScheduleRequest
from .schemas import IntegrationConnectRequest as IntegrationConnectRequest
from .schemas import MissionCreateRequest as MissionCreateRequest
from .schemas import RetryQueueItemResponse as RetryQueueItemResponse
from .schemas import WorkforceProfileRequest as WorkforceProfileRequest
from .schemas import KnowledgeDocRequest as KnowledgeDocRequest
from .constants import MissionStatus as MissionStatus
from .constants import PROVIDER_CATALOG as PROVIDER_CATALOG
from .constants import JSON_CONTENT_TYPE as JSON_CONTENT_TYPE
from .constants import DEFAULT_AI_GATEWAY_PATH as DEFAULT_AI_GATEWAY_PATH
from .constants import _META_ME_URL as _META_ME_URL
from .constants import AuthDep as AuthDep
from .constants import RoleType as RoleType
import asyncio
import hashlib
import time
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Annotated
from typing import Literal
import httpx
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from pydantic import BaseModel
from pydantic import Field
from ....deps import AuthContext
from ....deps import require_auth
from ....provider_executors import get_executor


def create_autonomous_workforce_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    profiles_memory: list[dict[str, Any]],
    integrations_memory: list[dict[str, Any]],
    missions_memory: list[dict[str, Any]],
    feed_memory: list[dict[str, Any]],
    schedules_memory: list[dict[str, Any]],
    knowledge_memory: list[dict[str, Any]],
    outcomes_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter(
        prefix="/autonomous-workforce",
        tags=["Autonomous Workforce"],
        dependencies=[Depends(require_workforce_api_available)],
        responses=WORKFORCE_API_UNAVAILABLE_RESPONSES,
    )
    _lock = threading.Lock()
    _metrics = MetricsCollector()
    _retry_queue: list[dict[str, Any]] = []
    _db_dsn_raw = str(os.getenv("WORKFORCE_DB_DSN", "") or os.getenv("DATABASE_URL", "")).strip()
    _db_dsn = _db_dsn_raw if _db_dsn_raw.startswith("postgresql") else ""
    _db: WorkforceDB | None = WorkforceDB(_db_dsn) if _db_dsn else None
    runtime = ContextRuntime(
        _db=_db,
        _lock=_lock,
        _metrics=_metrics,
        _retry_queue=_retry_queue,
        audit_log_memory=audit_log_memory,
        enforce_rate_limit=enforce_rate_limit,
        feed_memory=feed_memory,
        integrations_memory=integrations_memory,
        knowledge_memory=knowledge_memory,
        missions_memory=missions_memory,
        outcomes_memory=outcomes_memory,
        profiles_memory=profiles_memory,
        schedules_memory=schedules_memory,
    )
    list_capabilities.register(router, runtime)
    list_missions.register(router, runtime)
    list_knowledge.register(router, runtime)
    search_knowledge.register(router, runtime)
    return router
