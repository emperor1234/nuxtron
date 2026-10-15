"""Audience-insight endpoints fail closed until a verified workspace provider is connected."""

from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

router = APIRouter(prefix="/one2target", tags=["Audience insights"])


class CompareRequest(BaseModel):
    domains: list[str] = Field(min_length=2, max_length=3)


_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "A verified, permissioned audience-data connection for this workspace is not configured. "
        "Demographics, interests, audience sizes, behavior summaries, and ad-targeting estimates are disabled; "
        "domain-derived sample records are not returned."
    ),
}


def _audience_data_unavailable() -> NoReturn:
    raise HTTPException(status_code=501, detail=_UNAVAILABLE_DETAIL)


@router.get("/demographics")
def get_demographics(
    domain: str = Query(min_length=3, max_length=253),
    auth: AuthContext = Depends(require_auth),
):
    _audience_data_unavailable()


@router.get("/interests")
def get_interests(
    domain: str = Query(min_length=3, max_length=253),
    auth: AuthContext = Depends(require_auth),
):
    _audience_data_unavailable()


@router.get("/behaviour")
def get_behaviour(
    domain: str = Query(min_length=3, max_length=253),
    auth: AuthContext = Depends(require_auth),
):
    _audience_data_unavailable()


@router.get("/socioeconomics")
def get_socioeconomics(
    domain: str = Query(min_length=3, max_length=253),
    auth: AuthContext = Depends(require_auth),
):
    _audience_data_unavailable()


@router.get("/audience-size")
def get_audience_size(
    domain: str = Query(min_length=3, max_length=253),
    auth: AuthContext = Depends(require_auth),
):
    _audience_data_unavailable()


@router.get("/ad-targeting")
def get_ad_targeting(
    domain: str = Query(min_length=3, max_length=253),
    auth: AuthContext = Depends(require_auth),
):
    _audience_data_unavailable()


@router.post("/compare")
def compare_audiences(
    payload: CompareRequest,
    auth: AuthContext = Depends(require_auth),
):
    _audience_data_unavailable()
