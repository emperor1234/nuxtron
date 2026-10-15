"""Fail-closed Local Heatmap API contracts.

No verified geogrid provider or durable scan-history store is configured.
These routes deliberately return a typed 501 instead of generating synthetic heatmaps.
"""

from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
router = APIRouter(prefix="/local-heatmap", tags=["Local Heatmap"])

_LOCAL_HEATMAP_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": "Verified local rank-grid observations and durable scan history are not configured. No heatmap is generated.",
}
_LOCAL_HEATMAP_UNAVAILABLE_RESPONSE = {
    "description": "Verified geogrid rank observations are unavailable.",
    "content": {"application/json": {"example": {"detail": _LOCAL_HEATMAP_UNAVAILABLE_DETAIL}}},
}


def _raise_local_heatmap_unavailable() -> NoReturn:
    raise HTTPException(status_code=501, detail=_LOCAL_HEATMAP_UNAVAILABLE_DETAIL)


class ScanCreateRequest(BaseModel):
    business_name: str = Field(max_length=300)
    keyword: str = Field(max_length=200)
    center_lat: float
    center_lng: float
    grid_size: int = Field(default=5, ge=3, le=9)
    radius_km: float = Field(default=5.0, ge=0.5, le=50.0)
    label: str = Field(default="", max_length=100)


class BusinessProfileRequest(BaseModel):
    business_name: str = Field(max_length=300)
    address: str = Field(max_length=500)
    lat: float
    lng: float
    category: str = Field(default="", max_length=100)
    website: str = Field(default="", max_length=2000)
    phone: str = Field(default="", max_length=30)


@router.post("/business-profile", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def set_business_profile(payload: BusinessProfileRequest, auth: AuthDep) -> NoReturn:
    _ = (payload, auth)
    _raise_local_heatmap_unavailable()


@router.get("/business-profile", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def get_business_profile(auth: AuthDep) -> NoReturn:
    _ = auth
    _raise_local_heatmap_unavailable()


@router.post("/scans", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def create_scan(payload: ScanCreateRequest, auth: AuthDep) -> NoReturn:
    _ = (payload, auth)
    _raise_local_heatmap_unavailable()


@router.get("/scans", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def list_scans(auth: AuthDep) -> NoReturn:
    _ = auth
    _raise_local_heatmap_unavailable()


@router.get("/scans/{scan_id}", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def get_scan(scan_id: str, auth: AuthDep) -> NoReturn:
    _ = (scan_id, auth)
    _raise_local_heatmap_unavailable()


@router.delete("/scans/{scan_id}", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def delete_scan(scan_id: str, auth: AuthDep) -> NoReturn:
    _ = (scan_id, auth)
    _raise_local_heatmap_unavailable()


@router.get("/results/{scan_id}", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def get_results(scan_id: str, auth: AuthDep) -> NoReturn:
    _ = (scan_id, auth)
    _raise_local_heatmap_unavailable()


@router.get("/history", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def get_history(auth: AuthDep) -> NoReturn:
    _ = auth
    _raise_local_heatmap_unavailable()


@router.get("/comparison", status_code=501, response_model=None, responses={501: _LOCAL_HEATMAP_UNAVAILABLE_RESPONSE})
def compare_scans(
    scan_id_a: str = Query(description="First scan ID"),
    scan_id_b: str = Query(description="Second scan ID"),
    auth: AuthDep = None,
) -> NoReturn:
    _ = (scan_id_a, scan_id_b, auth)
    _raise_local_heatmap_unavailable()
