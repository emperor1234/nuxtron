"""Fail-closed Map Rank Tracker API contracts.

No verified local-pack provider or durable location-history store is configured.
These routes deliberately return a typed 501 instead of generating synthetic grids.
"""

from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
router = APIRouter(prefix="/map-rank-tracker", tags=["Map Rank Tracker"])

_MAP_RANK_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": "Verified local-pack observations and durable location history are not configured. No map scan is generated.",
}
_MAP_RANK_UNAVAILABLE_RESPONSE = {
    "description": "Verified local-pack rank observations are unavailable.",
    "content": {"application/json": {"example": {"detail": _MAP_RANK_UNAVAILABLE_DETAIL}}},
}


def _raise_map_rank_unavailable() -> NoReturn:
    raise HTTPException(status_code=501, detail=_MAP_RANK_UNAVAILABLE_DETAIL)


class ProjectCreateRequest(BaseModel):
    name: str = Field(max_length=100)
    business_name: str = Field(max_length=200, description="Google Business Profile name")
    address: str = Field(max_length=500)
    lat: float = Field(description="Center latitude for grid tracking")
    lng: float = Field(description="Center longitude for grid tracking")
    location_name: str = Field(default="United States", max_length=100)
    grid_size: int = Field(default=5, ge=3, le=9, description="Grid size: 3x3 to 9x9")


class KeywordAddRequest(BaseModel):
    project_id: str
    keywords: list[str] = Field(min_length=1, max_length=50)


class RankCheckRequest(BaseModel):
    project_id: str
    keyword_ids: list[str] = Field(default_factory=list, description="Empty = check all")


@router.post("/projects", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def create_project(payload: ProjectCreateRequest, auth: AuthDep) -> NoReturn:
    _ = (payload, auth)
    _raise_map_rank_unavailable()


@router.get("/projects", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def list_projects(auth: AuthDep) -> NoReturn:
    _ = auth
    _raise_map_rank_unavailable()


@router.delete("/projects/{project_id}", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def delete_project(project_id: str, auth: AuthDep) -> NoReturn:
    _ = (project_id, auth)
    _raise_map_rank_unavailable()


@router.post("/keywords", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def add_keywords(payload: KeywordAddRequest, auth: AuthDep) -> NoReturn:
    _ = (payload, auth)
    _raise_map_rank_unavailable()


@router.get("/keywords/{project_id}", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def list_keywords(project_id: str, auth: AuthDep) -> NoReturn:
    _ = (project_id, auth)
    _raise_map_rank_unavailable()


@router.post("/check", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def run_rank_check(payload: RankCheckRequest, auth: AuthDep) -> NoReturn:
    _ = (payload, auth)
    _raise_map_rank_unavailable()


@router.get("/results/{project_id}", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def get_results(project_id: str, auth: AuthDep) -> NoReturn:
    _ = (project_id, auth)
    _raise_map_rank_unavailable()


@router.get("/history/{keyword_id}", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def get_history(keyword_id: str, days: int = Query(default=30, ge=7, le=365), auth: AuthDep = None) -> NoReturn:
    _ = (keyword_id, days, auth)
    _raise_map_rank_unavailable()


@router.get("/grid", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def get_grid(
    keyword: str = Query(min_length=1, max_length=200),
    lat: float = Query(description="Center latitude"),
    lng: float = Query(description="Center longitude"),
    grid_size: int = Query(default=5, ge=3, le=9),
    auth: AuthDep = None,
) -> NoReturn:
    _ = (keyword, lat, lng, grid_size, auth)
    _raise_map_rank_unavailable()


@router.get("/heatmap/{keyword_id}", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def get_heatmap(keyword_id: str, auth: AuthDep) -> NoReturn:
    _ = (keyword_id, auth)
    _raise_map_rank_unavailable()


@router.get("/competitors", status_code=501, response_model=None, responses={501: _MAP_RANK_UNAVAILABLE_RESPONSE})
def get_local_competitors(
    keyword: str = Query(min_length=1, max_length=200),
    lat: float = Query(description="Center latitude"),
    lng: float = Query(description="Center longitude"),
    auth: AuthDep = None,
) -> NoReturn:
    _ = (keyword, lat, lng, auth)
    _raise_map_rank_unavailable()
