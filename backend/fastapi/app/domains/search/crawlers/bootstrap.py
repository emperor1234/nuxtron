"""Search/Crawlers HTTP composition and legacy import exports."""

from __future__ import annotations
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    register_site,
    ingest_crawler_event,
    cloudflare_status,
    list_automation_schedules,
)
from .services.detect_crawler import _detect_crawler as _detect_crawler
from .schemas import CloudflareSyncRequest as CloudflareSyncRequest
from .schemas import CrawlerRuleRequest as CrawlerRuleRequest
from .schemas import BulkSnippetDeployRequest as BulkSnippetDeployRequest
from .schemas import AutomationSchedulesExecuteRequest as AutomationSchedulesExecuteRequest
from .schemas import AutomationRunRequest as AutomationRunRequest
from .schemas import SiteRegisterRequest as SiteRegisterRequest
from .schemas import AutomationScheduleUpdateRequest as AutomationScheduleUpdateRequest
from .schemas import CrawlerDetectRequest as CrawlerDetectRequest
from .schemas import CrawlerEventIngestRequest as CrawlerEventIngestRequest
from .schemas import CloudflareAutoSyncRequest as CloudflareAutoSyncRequest
from .schemas import VisibilityAuditRequest as VisibilityAuditRequest
from .schemas import AutomationScheduleCreateRequest as AutomationScheduleCreateRequest
from .schemas import SsrRenderRequest as SsrRenderRequest
from .schemas import SnippetVerifyRequest as SnippetVerifyRequest
from .constants import AuthDep as AuthDep
import hashlib
import os
import re
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
from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from ....deps import AuthContext
from ....deps import require_auth


def create_ai_crawler_enablement_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    sites_memory: list[dict[str, Any]],
    crawler_events_memory: list[dict[str, Any]],
    ssr_cache_memory: list[dict[str, Any]],
    crawler_rules_memory: list[dict[str, Any]],
    audit_results_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter(prefix="/ai-crawler", tags=["AI Crawler Enablement"])
    _lock = threading.Lock()
    automation_schedules_memory: list[dict[str, Any]] = []
    automation_runs_memory: list[dict[str, Any]] = []
    runtime = ContextRuntime(
        _lock=_lock,
        audit_log_memory=audit_log_memory,
        audit_results_memory=audit_results_memory,
        automation_runs_memory=automation_runs_memory,
        automation_schedules_memory=automation_schedules_memory,
        crawler_events_memory=crawler_events_memory,
        crawler_rules_memory=crawler_rules_memory,
        enforce_rate_limit=enforce_rate_limit,
        sites_memory=sites_memory,
        ssr_cache_memory=ssr_cache_memory,
    )
    register_site.register(router, runtime)
    ingest_crawler_event.register(router, runtime)
    cloudflare_status.register(router, runtime)
    list_automation_schedules.register(router, runtime)
    return router
