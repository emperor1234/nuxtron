"""Workflow HTTP operations: escalation alignment index."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.escalation_alignment_index import execute_get_postmortem_action_item_escalation_alignment_index
from ..operations.escalation_alignment_index import execute_get_postmortem_action_item_remediation_clarity_forecast
from ..operations.escalation_alignment_index import execute_get_postmortem_action_item_escalation_clarity_index
from ..operations.escalation_alignment_index import execute_get_postmortem_action_item_remediation_composure_forecast
from ..operations.escalation_alignment_index import execute_get_postmortem_action_item_escalation_composure_index
from ..operations.escalation_alignment_index import execute_get_postmortem_action_item_remediation_focus_forecast


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-alignment-index",
        summary="Escalation alignment index for active owner workload",
    )
    def get_postmortem_action_item_escalation_alignment_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_alignment_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-clarity-forecast",
        summary="Remediation clarity forecast for active owner workload",
    )
    def get_postmortem_action_item_remediation_clarity_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_clarity_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-clarity-index",
        summary="Escalation clarity index for active owner workload",
    )
    def get_postmortem_action_item_escalation_clarity_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_clarity_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-composure-forecast",
        summary="Remediation composure forecast for active owner workload",
    )
    def get_postmortem_action_item_remediation_composure_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_composure_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-composure-index",
        summary="Escalation composure index for active owner workload",
    )
    def get_postmortem_action_item_escalation_composure_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_composure_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-focus-forecast",
        summary="Remediation focus forecast for active owner workload",
    )
    def get_postmortem_action_item_remediation_focus_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_focus_forecast(runtime, auth, days_horizon)
