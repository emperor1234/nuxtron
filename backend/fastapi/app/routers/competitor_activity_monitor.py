"""Authenticated API contracts for competitor activity monitoring."""

from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Durable tenant-scoped monitor storage, an authorized competitor-data source, and scheduled acquisition are not "
        "configured. Monitor creation, alerts, and activity feeds are disabled; no sample events are generated."
    ),
}

router = APIRouter(
    prefix="/eyeon",
    tags=["Competitor Activity Monitor"],
    responses={501: {"description": "Verified competitor monitoring sources and durable storage are unavailable."}},
)


class MonitorAddRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)
    label: str = Field(default="", max_length=100)
    track_content: bool = True
    track_ads: bool = True
    track_keywords: bool = True
    track_backlinks: bool = True
    track_social: bool = True


class AlertConfigRequest(BaseModel):
    monitor_id: str | None = None
    event_types: list[str] = Field(default_factory=list)
    severity: str = Field(default="warning", description="info | warning | critical")
    email: str = Field(default="", max_length=320)
    webhook_url: str = Field(default="", max_length=2000)
    active: bool = True


def _raise_unavailable() -> NoReturn:
    raise HTTPException(status_code=501, detail=_UNAVAILABLE)


@router.post("/monitors")
def add_monitor(payload: MonitorAddRequest, auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.get("/monitors")
def list_monitors(auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.delete("/monitors/{monitor_id}")
def delete_monitor(monitor_id: str, auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.get("/feed")
def get_feed(
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    auth: AuthContext = Depends(require_auth),
):
    _raise_unavailable()


@router.get("/feed/{monitor_id}")
def get_monitor_feed(
    monitor_id: str,
    limit: int = Query(default=30, ge=1, le=100),
    auth: AuthContext = Depends(require_auth),
):
    _raise_unavailable()


@router.get("/content-changes")
def get_content_changes(auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.get("/ad-changes")
def get_ad_changes(auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.get("/keyword-changes")
def get_keyword_changes(auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.get("/backlink-changes")
def get_backlink_changes(auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.post("/alerts")
def configure_alert(payload: AlertConfigRequest, auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.get("/alerts")
def list_alerts(auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()


@router.get("/summary")
def get_summary(auth: AuthContext = Depends(require_auth)):
    _raise_unavailable()
