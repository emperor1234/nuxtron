"""Integrations/Cms HTTP composition and legacy import exports."""

from __future__ import annotations
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    add_connection,
    create_attribution_link,
)
from .schemas import CmsAttributionLinkRequest as CmsAttributionLinkRequest
from .schemas import CmsConnectionRequest as CmsConnectionRequest
from .schemas import CmsAttributionEventRequest as CmsAttributionEventRequest
from .schemas import CmsSchemaInjectRequest as CmsSchemaInjectRequest
from .schemas import CmsPublishRequest as CmsPublishRequest
from .schemas import CmsSyncRequest as CmsSyncRequest
from .schemas import CmsAttributionAutomationRuleRequest as CmsAttributionAutomationRuleRequest
from .constants import CMS_CONNECTION_NOT_FOUND as CMS_CONNECTION_NOT_FOUND
from .constants import AuthDep as AuthDep
from .constants import SUPPORTED_CMS as SUPPORTED_CMS
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Annotated
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy import func
from ....database import get_db_session
from ....deps import AuthContext
from ....deps import require_auth
from ....models import Activity
from ....models import Contact
from ....models import Deal
from ....models import Task


def create_cms_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    cms_connections_memory: list[dict[str, Any]],
    cms_pages_memory: list[dict[str, Any]],
    cms_sync_log_memory: list[dict[str, Any]],
    email_sequences_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter()
    lock = threading.Lock()
    cms_attribution_links_memory: list[dict[str, Any]] = []
    cms_attribution_events_memory: list[dict[str, Any]] = []
    cms_attribution_rules_memory: list[dict[str, Any]] = []
    cms_attribution_automation_runs_memory: list[dict[str, Any]] = []
    runtime = ContextRuntime(
        audit_log_memory=audit_log_memory,
        cms_attribution_automation_runs_memory=cms_attribution_automation_runs_memory,
        cms_attribution_events_memory=cms_attribution_events_memory,
        cms_attribution_links_memory=cms_attribution_links_memory,
        cms_attribution_rules_memory=cms_attribution_rules_memory,
        cms_connections_memory=cms_connections_memory,
        cms_pages_memory=cms_pages_memory,
        cms_sync_log_memory=cms_sync_log_memory,
        email_sequences_memory=email_sequences_memory,
        enforce_rate_limit=enforce_rate_limit,
        lock=lock,
    )
    add_connection.register(router, runtime)
    create_attribution_link.register(router, runtime)
    return router
