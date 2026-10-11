"""Search/Visibility HTTP adapters beginning with list engines."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.db_available import execute_analytics_cascade_map
from ..operations.db_available import execute_analytics_k_factor
from ..operations.db_available import execute_analytics_roi_report
from ..operations.db_available import execute_command_centre
from ..operations.db_available import execute_dashboard_summary
from ..operations.db_available import execute_generate_viral_brief
from ..operations.db_available import execute_list_engines
from ..operations.db_available import execute_list_subsystems
from ..runtime import ContextRuntime
from ..schemas import ViralBriefRequest
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/engines")
    def list_engines(auth: AuthDep) -> dict:
        return execute_list_engines(runtime, auth)

    @router.get("/subsystems")
    def list_subsystems(auth: AuthDep) -> dict:
        return execute_list_subsystems(runtime, auth)

    @router.get("/command-centre")
    def command_centre(auth: AuthDep) -> dict:
        return execute_command_centre(runtime, auth)

    @router.get("/dashboard/summary")
    def dashboard_summary(auth: AuthDep) -> dict:
        return execute_dashboard_summary(runtime, auth)

    @router.get("/analytics/k-factor")
    def analytics_k_factor(auth: AuthDep) -> dict:
        return execute_analytics_k_factor(runtime, auth)

    @router.get("/analytics/cascade-map")
    def analytics_cascade_map(auth: AuthDep) -> dict:
        return execute_analytics_cascade_map(runtime, auth)

    @router.get("/analytics/roi-report")
    def analytics_roi_report(auth: AuthDep) -> dict:
        return execute_analytics_roi_report(runtime, auth)

    @router.post("/brief")
    def generate_viral_brief(payload: ViralBriefRequest, auth: AuthDep) -> dict:
        return execute_generate_viral_brief(runtime, payload, auth)
