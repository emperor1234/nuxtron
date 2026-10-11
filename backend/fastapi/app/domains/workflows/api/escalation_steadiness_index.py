"""Workflow HTTP operations: escalation steadiness index."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.escalation_steadiness_index import execute_get_postmortem_action_item_escalation_steadiness_index
from ..operations.escalation_steadiness_index import execute_get_postmortem_action_item_remediation_durability_forecast
from ..operations.escalation_steadiness_index import execute_get_postmortem_action_item_escalation_durability_index
from ..operations.escalation_steadiness_index import execute_get_postmortem_action_item_remediation_consistency_forecast
from ..operations.escalation_steadiness_index import execute_get_postmortem_action_item_escalation_consistency_index
from ..operations.escalation_steadiness_index import execute_get_postmortem_action_item_remediation_alignment_forecast


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-steadiness-index",
        summary="Escalation steadiness index for active owner workload",
    )
    def get_postmortem_action_item_escalation_steadiness_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_steadiness_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-durability-forecast",
        summary="Remediation durability forecast for active owner workload",
    )
    def get_postmortem_action_item_remediation_durability_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_durability_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-durability-index",
        summary="Escalation durability index for active owner workload",
    )
    def get_postmortem_action_item_escalation_durability_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_durability_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-consistency-forecast",
        summary="Remediation consistency forecast for active owner workload",
    )
    def get_postmortem_action_item_remediation_consistency_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_consistency_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-consistency-index",
        summary="Escalation consistency index for active owner workload",
    )
    def get_postmortem_action_item_escalation_consistency_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_consistency_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-alignment-forecast",
        summary="Remediation alignment forecast for active owner workload",
    )
    def get_postmortem_action_item_remediation_alignment_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_alignment_forecast(runtime, auth, days_horizon)
