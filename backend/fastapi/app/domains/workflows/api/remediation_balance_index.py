"""Workflow HTTP operations: remediation balance index."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.remediation_balance_index import execute_get_postmortem_action_item_remediation_balance_index
from ..operations.remediation_balance_index import execute_get_postmortem_action_item_escalation_pressure_forecast
from ..operations.remediation_balance_index import execute_get_postmortem_action_item_remediation_concentration_forecast
from ..operations.remediation_balance_index import execute_get_postmortem_action_item_escalation_containment_index
from ..operations.remediation_balance_index import execute_get_postmortem_action_item_remediation_readiness_balance
from ..operations.remediation_balance_index import execute_get_postmortem_action_item_escalation_load_shedding_forecast


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-balance-index",
        summary="Remediation balance index across active owners and action-item backlog",
    )
    def get_postmortem_action_item_remediation_balance_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_balance_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-pressure-forecast",
        summary="Escalation pressure forecast for near-term action-item execution load",
    )
    def get_postmortem_action_item_escalation_pressure_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_pressure_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-concentration-forecast",
        summary="Remediation concentration forecast for active owner distribution",
    )
    def get_postmortem_action_item_remediation_concentration_forecast(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_concentration_forecast(
            runtime, auth, max_open_items_per_owner
        )

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-containment-index",
        summary="Escalation containment index for short-horizon remediation stability",
    )
    def get_postmortem_action_item_escalation_containment_index(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_containment_index(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-readiness-balance",
        summary="Remediation readiness balance across active action-item owners",
    )
    def get_postmortem_action_item_remediation_readiness_balance(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_readiness_balance(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-load-shedding-forecast",
        summary="Escalation load shedding forecast for short-horizon backlog control",
    )
    def get_postmortem_action_item_escalation_load_shedding_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_load_shedding_forecast(runtime, auth, days_horizon)
