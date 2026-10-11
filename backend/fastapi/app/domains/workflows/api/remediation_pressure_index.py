"""Workflow HTTP operations: remediation pressure index."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.remediation_pressure_index import execute_get_postmortem_action_item_remediation_pressure_index
from ..operations.remediation_pressure_index import execute_get_postmortem_action_item_escalation_relief_forecast
from ..operations.remediation_pressure_index import execute_get_postmortem_action_item_remediation_recovery_index
from ..operations.remediation_pressure_index import execute_get_postmortem_action_item_escalation_recovery_index
from ..operations.remediation_pressure_index import execute_get_postmortem_action_item_remediation_resilience_forecast
from ..operations.remediation_pressure_index import execute_get_postmortem_action_item_remediation_steadiness_forecast


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-pressure-index",
        summary="Remediation pressure index for active owner workload",
    )
    def get_postmortem_action_item_remediation_pressure_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_pressure_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-relief-forecast",
        summary="Escalation relief forecast for short-horizon backlog recovery",
    )
    def get_postmortem_action_item_escalation_relief_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_relief_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-recovery-index",
        summary="Remediation recovery index for active owner workload",
    )
    def get_postmortem_action_item_remediation_recovery_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_recovery_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-recovery-index",
        summary="Escalation recovery index for short-horizon backlog recovery",
    )
    def get_postmortem_action_item_escalation_recovery_index(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_recovery_index(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-resilience-forecast",
        summary="Remediation resilience forecast for active owner workload",
    )
    def get_postmortem_action_item_remediation_resilience_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_resilience_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-steadiness-forecast",
        summary="Remediation steadiness forecast for active owner workload",
    )
    def get_postmortem_action_item_remediation_steadiness_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_steadiness_forecast(runtime, auth, days_horizon)
