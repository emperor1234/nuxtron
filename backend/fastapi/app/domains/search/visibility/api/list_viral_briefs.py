"""Search/Visibility HTTP adapters beginning with list viral briefs."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.db_available import execute_analyze_triggers
from ..operations.db_available import execute_list_viral_briefs
from ..operations.db_available import execute_triggers_library
from ..operations.optimal_triggers import execute_algorithm_models
from ..operations.optimal_triggers import execute_algorithm_optimize
from ..operations.optimal_triggers import execute_algorithm_updates
from ..operations.optimal_triggers import execute_network_map
from ..operations.optimal_triggers import execute_optimal_triggers
from ..runtime import ContextRuntime
from ..schemas import AlgorithmOptimizeRequest
from ..schemas import NetworkMapRequest
from ..schemas import TriggerAnalyzeRequest
from ..schemas import ViralBriefRequest
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/brief")
    def list_viral_briefs(auth: AuthDep) -> dict:
        return execute_list_viral_briefs(runtime, auth)

    @router.get("/triggers/library")
    def triggers_library(auth: AuthDep) -> dict:
        return execute_triggers_library(runtime, auth)

    @router.post("/triggers/analyze")
    def analyze_triggers(payload: TriggerAnalyzeRequest, auth: AuthDep) -> dict:
        return execute_analyze_triggers(runtime, payload, auth)

    @router.post("/triggers/optimal")
    def optimal_triggers(payload: ViralBriefRequest, auth: AuthDep) -> dict:
        return execute_optimal_triggers(runtime, payload, auth)

    @router.get("/algorithm/models")
    def algorithm_models(auth: AuthDep) -> dict:
        return execute_algorithm_models(runtime, auth)

    @router.post("/algorithm/optimize")
    def algorithm_optimize(payload: AlgorithmOptimizeRequest, auth: AuthDep) -> dict:
        return execute_algorithm_optimize(runtime, payload, auth)

    @router.get("/algorithm/updates")
    def algorithm_updates(auth: AuthDep) -> dict:
        return execute_algorithm_updates(runtime, auth)

    @router.post("/network/map")
    def network_map(payload: NetworkMapRequest, auth: AuthDep) -> dict:
        return execute_network_map(runtime, payload, auth)
