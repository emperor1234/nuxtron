"""Workflow HTTP operations: connector health check."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorFailureSimulationRequest
from ..schemas import WorkflowConnectorReliabilityPolicyRequest
from ..schemas import WorkflowConnectorReplayProcessorRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.connector_health_check import execute_connector_health_check
from ..operations.connector_health_check import execute_update_connector_reliability_policy
from ..operations.connector_health_check import execute_get_connector_reliability
from ..operations.connector_health_check import execute_simulate_connector_failure
from ..operations.connector_health_check import execute_list_connector_replay_queue
from ..operations.connector_health_check import execute_list_connector_sla_alerts
from ..operations.connector_health_check import execute_reconcile_connector_circuits
from ..operations.connector_health_check import execute_process_connector_replay_queue


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.post(
        "/workflow-connectors/{connector_id}/health-check", responses={404: {"description": EXECUTION_NOT_FOUND}}
    )
    def connector_health_check(connector_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_connector_health_check(runtime, connector_id, auth)

    @router.patch(
        "/workflow-connectors/{connector_id}/reliability-policy", responses={404: {"description": EXECUTION_NOT_FOUND}}
    )
    def update_connector_reliability_policy(
        connector_id: int, payload: WorkflowConnectorReliabilityPolicyRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_update_connector_reliability_policy(runtime, connector_id, payload, auth)

    @router.get(
        "/workflow-connectors/{connector_id}/reliability", responses={404: {"description": EXECUTION_NOT_FOUND}}
    )
    def get_connector_reliability(connector_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_get_connector_reliability(runtime, connector_id, auth)

    @router.post(
        "/workflow-connectors/{connector_id}/simulate-failure", responses={404: {"description": EXECUTION_NOT_FOUND}}
    )
    def simulate_connector_failure(
        connector_id: int, payload: WorkflowConnectorFailureSimulationRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_simulate_connector_failure(runtime, connector_id, payload, auth)

    @router.get("/workflow-connectors/replay-queue")
    def list_connector_replay_queue(
        auth: AuthDep,
        connector_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        return execute_list_connector_replay_queue(runtime, auth, connector_id, limit)

    @router.get("/workflow-connectors/sla-alerts")
    def list_connector_sla_alerts(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> dict[str, Any]:
        return execute_list_connector_sla_alerts(runtime, auth, status, limit)

    @router.post("/workflow-connectors/reconcile-circuits")
    def reconcile_connector_circuits(auth: AuthDep) -> dict[str, Any]:
        return execute_reconcile_connector_circuits(runtime, auth)

    @router.post("/workflow-connectors/replay-queue/process")
    def process_connector_replay_queue(
        payload: WorkflowConnectorReplayProcessorRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_process_connector_replay_queue(runtime, payload, auth)
