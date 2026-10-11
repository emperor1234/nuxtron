"""Workflow HTTP operations: remediation cadence forecast."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorUpsertRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.remediation_cadence_forecast import execute_get_postmortem_action_item_remediation_cadence_forecast
from ..operations.remediation_cadence_forecast import execute_get_postmortem_action_item_escalation_cadence_index
from ..operations.remediation_cadence_forecast import execute_get_postmortem_action_item_remediation_stability_forecast
from ..operations.remediation_cadence_forecast import execute_get_postmortem_action_item_escalation_stability_index
from ..operations.remediation_cadence_forecast import execute_get_postmortem_compliance_rollups
from ..operations.remediation_cadence_forecast import execute_upsert_connector
from ..operations.remediation_cadence_forecast import execute_list_connectors


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-cadence-forecast",
        summary="Remediation cadence forecast for owner execution flow",
    )
    def get_postmortem_action_item_remediation_cadence_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_cadence_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-cadence-index",
        summary="Escalation cadence index for owner execution flow",
    )
    def get_postmortem_action_item_escalation_cadence_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_cadence_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-stability-forecast",
        summary="Remediation stability forecast for owner execution consistency",
    )
    def get_postmortem_action_item_remediation_stability_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_stability_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-stability-index",
        summary="Escalation stability index for owner execution consistency",
    )
    def get_postmortem_action_item_escalation_stability_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_stability_index(runtime, auth, max_open_items_per_owner)

    @router.get("/workflow-connectors/postmortems/compliance-rollups", summary="Weekly postmortem compliance rollups")
    def get_postmortem_compliance_rollups(
        auth: AuthDep, weeks: Annotated[int, Query(ge=1, le=26)] = 4
    ) -> dict[str, Any]:
        return execute_get_postmortem_compliance_rollups(runtime, auth, weeks)

    @router.post("/workflow-connectors", summary="Register or update workflow connector")
    def upsert_connector(payload: WorkflowConnectorUpsertRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_upsert_connector(runtime, payload, auth)

    @router.get("/workflow-connectors", summary="List connectors for workflows")
    def list_connectors(auth: AuthDep) -> dict[str, Any]:
        return execute_list_connectors(runtime, auth)
