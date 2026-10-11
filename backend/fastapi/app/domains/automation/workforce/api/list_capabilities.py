"""Automation/Workforce HTTP adapters beginning with list capabilities."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.list_capabilities import execute_connect_integration
from ..operations.list_capabilities import execute_create_mission
from ..operations.list_capabilities import execute_get_profile
from ..operations.list_capabilities import execute_integration_catalog
from ..operations.list_capabilities import execute_list_capabilities
from ..operations.list_capabilities import execute_list_integrations
from ..operations.list_capabilities import execute_list_vendors
from ..operations.list_capabilities import execute_upsert_profile
from ..runtime import ContextRuntime
from ..schemas import IntegrationConnectRequest
from ..schemas import MissionCreateRequest
from ..schemas import WorkforceProfileRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/capabilities")
    def list_capabilities(auth: AuthDep) -> dict[str, Any]:
        return execute_list_capabilities(runtime, auth)

    @router.get("/vendors")
    def list_vendors(auth: AuthDep) -> dict[str, Any]:
        return execute_list_vendors(runtime, auth)

    @router.post("/profile", status_code=201)
    def upsert_profile(payload: WorkforceProfileRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_upsert_profile(runtime, payload, auth)

    @router.get("/profile", responses={404: {"description": "Workforce profile not found."}})
    def get_profile(auth: AuthDep) -> dict[str, Any]:
        return execute_get_profile(runtime, auth)

    @router.get("/integrations/catalog")
    def integration_catalog(auth: AuthDep) -> dict[str, Any]:
        return execute_integration_catalog(runtime, auth)

    @router.post(
        "/integrations/connect",
        status_code=201,
        responses={422: {"description": "Unsupported provider, missing credentials, or provider verification failed."}},
    )
    async def connect_integration(payload: IntegrationConnectRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_connect_integration(runtime, payload, auth)

    @router.get("/integrations")
    def list_integrations(auth: AuthDep) -> dict[str, Any]:
        return execute_list_integrations(runtime, auth)

    @router.post("/missions", status_code=201)
    def create_mission(payload: MissionCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_mission(runtime, payload, auth)
