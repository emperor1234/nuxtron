"""Notifications/Delivery request contracts."""

from __future__ import annotations
from pydantic import BaseModel
from pydantic import Field


class NotificationCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=4000)
    category: str = Field(default="general", min_length=1, max_length=40)
    priority: str = Field(default="info", min_length=1, max_length=20)


class NotificationPreferencesRequest(BaseModel):
    muted_categories: list[str] = Field(default_factory=list, max_length=50)
    email_enabled: bool = True
    sms_enabled: bool = False
    slack_enabled: bool = False
    realtime_enabled: bool = True
    digest_frequency: str = Field(default="realtime", max_length=20)
