"""Search/Visibility HTTP adapters beginning with network superconnectors."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.db_available import execute_list_detonations
from ..operations.optimal_triggers import execute_cascade_simulate
from ..operations.optimal_triggers import execute_detonation_execute
from ..operations.optimal_triggers import execute_detonation_history
from ..operations.optimal_triggers import execute_detonation_plan
from ..operations.optimal_triggers import execute_network_superconnectors
from ..operations.optimal_triggers import execute_swarm_activate
from ..operations.optimal_triggers import execute_swarm_compose
from ..runtime import ContextRuntime
from ..schemas import CascadeSimulateRequest
from ..schemas import DetonationPlanRequest
from ..schemas import SwarmActivateRequest
from ..schemas import SwarmComposeRequest
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get(
        "/network/superconnectors",
        responses={404: {"description": "No network map found. Run POST /vse/network/map first."}},
    )
    def network_superconnectors(auth: AuthDep) -> dict:
        return execute_network_superconnectors(runtime, auth)

    @router.post("/network/cascade-simulate")
    def cascade_simulate(payload: CascadeSimulateRequest, auth: AuthDep) -> dict:
        return execute_cascade_simulate(runtime, payload, auth)

    @router.post("/detonation/plan")
    def detonation_plan(payload: DetonationPlanRequest, auth: AuthDep) -> dict:
        return execute_detonation_plan(runtime, payload, auth)

    @router.post(
        "/detonation/{detonation_id}/execute",
        responses={
            404: {"description": "Detonation plan not found."},
            422: {"description": "Detonation already executed."},
        },
    )
    def detonation_execute(detonation_id: str, auth: AuthDep) -> dict:
        return execute_detonation_execute(runtime, detonation_id, auth)

    @router.get("/detonation")
    def list_detonations(auth: AuthDep) -> dict:
        return execute_list_detonations(runtime, auth)

    @router.get("/detonation/history")
    def detonation_history(auth: AuthDep) -> dict:
        return execute_detonation_history(runtime, auth)

    @router.post("/swarm/compose")
    def swarm_compose(payload: SwarmComposeRequest, auth: AuthDep) -> dict:
        return execute_swarm_compose(runtime, payload, auth)

    @router.post(
        "/swarm/activate",
        responses={404: {"description": "Swarm not found."}, 422: {"description": "Swarm already active."}},
    )
    def swarm_activate(payload: SwarmActivateRequest, auth: AuthDep) -> dict:
        return execute_swarm_activate(runtime, payload, auth)
