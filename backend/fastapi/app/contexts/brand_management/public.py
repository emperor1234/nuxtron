"""Public brand-management types safe for other contexts to import."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now_naive() -> datetime:
    """Return legacy-compatible naive UTC without deprecated ``utcnow()``."""
    return datetime.now(UTC).replace(tzinfo=None)


class BrandStatus(StrEnum):
    """Lifecycle states accepted by the historical brand API."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class BrandGuidelines(BaseModel):
    """Visual, voice, content, and compliance rules for one brand."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    primary_color: str = "#000000"
    secondary_color: str = "#FFFFFF"
    logo_url: str | None = None
    brand_font: str = "Arial"
    tone: str = "professional"
    voice_description: str = ""
    content_policy: str = ""
    restricted_topics: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    restricted_keywords: list[str] = Field(default_factory=list)
    compliance_rules: list[str] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now_naive)
    updated_at: datetime = Field(default_factory=utc_now_naive)


class BrandAsset(BaseModel):
    """An asset held in a tenant-owned brand library."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    asset_type: str
    url: str
    category: str
    tags: list[str] = Field(default_factory=list)
    rights_holder: str
    usage_rights: str
    expiration_date: datetime | None = None
    usage_count: int = 0
    engagement_rate: float | None = None
    uploaded_at: datetime = Field(default_factory=utc_now_naive)
    last_used_at: datetime | None = None


class Brand(BaseModel):
    """Tenant-owned brand aggregate.

    ``tenant_id`` is immutable from API updates. Repository lookups require it,
    so a caller cannot discover or mutate an aggregate by guessing its ID.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    description: str = ""
    website: str | None = None
    status: BrandStatus = BrandStatus.ACTIVE
    guidelines: BrandGuidelines = Field(default_factory=BrandGuidelines)
    assets: list[BrandAsset] = Field(default_factory=list)
    primary_audience: str = ""
    primary_channels: list[str] = Field(default_factory=list)
    monthly_reach: int = 0
    monthly_engagement: float = 0.0
    owners: list[str] = Field(default_factory=list)
    contributors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now_naive)
    updated_at: datetime = Field(default_factory=utc_now_naive)
