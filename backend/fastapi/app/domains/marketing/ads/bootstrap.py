"""Marketing/Ads HTTP composition and legacy import exports."""

from __future__ import annotations
from ....integrations.vendor_manager import get_vendor_manager
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    list_connectors,
    get_campaign,
    get_kpis,
    audience_insights,
)
from .services.now_iso import _now_iso as _now_iso
from .services.now_iso import _platform_oauth_url as _platform_oauth_url
from .services.now_iso import _platform_vendor_id as _platform_vendor_id
from .services.now_iso import _seed_connector as _seed_connector
from .schemas import CampaignSchedule as CampaignSchedule
from .schemas import ApprovalRequestModel as ApprovalRequestModel
from .schemas import KeywordConfig as KeywordConfig
from .schemas import CampaignDuplicateRequest as CampaignDuplicateRequest
from .schemas import CampaignCreative as CampaignCreative
from .schemas import ConnectorCallbackRequest as ConnectorCallbackRequest
from .schemas import ApprovalDecisionModel as ApprovalDecisionModel
from .schemas import CampaignCreateRequest as CampaignCreateRequest
from .schemas import CampaignUpdateRequest as CampaignUpdateRequest
from .schemas import CampaignMetricsPatchRequest as CampaignMetricsPatchRequest
from .schemas import CampaignPublishRequest as CampaignPublishRequest
from .schemas import ConnectorStartResponse as ConnectorStartResponse
from .schemas import CalendarRescheduleRequest as CalendarRescheduleRequest
from .schemas import AssetAutoResizeRequest as AssetAutoResizeRequest
from .schemas import ForecastResponse as ForecastResponse
from .schemas import ConnectorListResponse as ConnectorListResponse
from .constants import _DEFAULT_BEST_TIME as _DEFAULT_BEST_TIME
from .constants import SUPPORTED_PLATFORMS as SUPPORTED_PLATFORMS
from .constants import PLATFORM_META as PLATFORM_META
from .constants import AuthDep as AuthDep
from .constants import _BEST_TIME_TABLE as _BEST_TIME_TABLE
import hashlib
import secrets
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Annotated
from typing import Literal
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from ....deps import AuthContext
from ....deps import require_auth
from ....integrations.vendor_manager import VendorCredentials
from ....integrations.vendor_manager import VendorType


def create_ads_control_tower_router(
    *,
    enforce_rate_limit: Callable[..., None],
    notifications_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    connectors_memory: list[dict[str, Any]] | None = None,
    campaigns_memory: list[dict[str, Any]] | None = None,
    scheduler_memory: list[dict[str, Any]] | None = None,
    forecast_memory: list[dict[str, Any]] | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/ads-control-tower", tags=["ads-control-tower"])
    lock = threading.Lock()
    vendor_manager = get_vendor_manager()
    _connectors = connectors_memory if connectors_memory is not None else []
    _campaigns = campaigns_memory if campaigns_memory is not None else []
    _scheduler = scheduler_memory if scheduler_memory is not None else []
    _forecasts = forecast_memory if forecast_memory is not None else []
    runtime = ContextRuntime(
        _campaigns=_campaigns,
        _connectors=_connectors,
        _forecasts=_forecasts,
        _scheduler=_scheduler,
        audit_log_memory=audit_log_memory,
        enforce_rate_limit=enforce_rate_limit,
        lock=lock,
        notifications_memory=notifications_memory,
        vendor_manager=vendor_manager,
    )
    list_connectors.register(router, runtime)
    get_campaign.register(router, runtime)
    get_kpis.register(router, runtime)
    audience_insights.register(router, runtime)
    return router
