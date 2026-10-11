"""Automation/Workforce request contracts."""

from __future__ import annotations
from .constants import RoleType
from pydantic import BaseModel
from pydantic import Field
from typing import Any


class WorkforceProfileRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=160)
    website: str = Field(min_length=3, max_length=300)
    target_markets: list[str] = Field(default_factory=list, max_length=30)
    preferred_channels: list[str] = Field(default_factory=list, max_length=30)
    brand_tone: str = Field(default="", max_length=400)
    goals: list[str] = Field(default_factory=list, max_length=20)


class IntegrationConnectRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    access_token: str | None = Field(default=None, max_length=4096)
    secret_ref: str | None = Field(
        default=None,
        max_length=200,
        description="External secret reference (vault key, KMS key id, secret manager path)",
    )
    account_id: str | None = Field(default=None, max_length=160)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MissionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=2000)
    role: RoleType
    objective: str = Field(min_length=1, max_length=800)
    requires_approval: bool = True
    providers: list[str] = Field(default_factory=list, max_length=12)
    input_context: dict[str, Any] = Field(default_factory=dict)


class MissionDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ScheduleRequest(BaseModel):
    mission_template_id: str | None = Field(default=None, max_length=64)
    role: RoleType
    title: str = Field(min_length=1, max_length=180)
    objective: str = Field(min_length=1, max_length=800)
    frequency_minutes: int = Field(default=60, ge=5, le=1440)
    providers: list[str] = Field(default_factory=list, max_length=12)
    enabled: bool = True


class KnowledgeDocRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=20000)
    source: str = Field(default="manual", max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=30)


class WebhookTriggerRequest(BaseModel):
    """External webhook to trigger mission creation."""

    role: RoleType
    trigger_source: str = Field(max_length=120)
    objective: str = Field(min_length=1, max_length=800)
    providers: list[str] = Field(default_factory=list, max_length=12)
    event_data: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = True


class RetryQueueItemResponse(BaseModel):
    """Retry queue item for display/management."""

    id: str
    mission_id: str
    provider: str
    retry_count: int
    max_retries: int
    status: str
    next_retry_at: str
    last_error: str | None = None
    backoff_seconds: int = 60


class MetricsQueryRequest(BaseModel):
    """Query parameters for metrics."""

    time_window_minutes: int = Field(default=60, ge=5, le=1440)
    provider: str | None = None
