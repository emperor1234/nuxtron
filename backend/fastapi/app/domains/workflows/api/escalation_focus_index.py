"""Workflow HTTP operations: escalation focus index."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.escalation_focus_index import execute_get_postmortem_action_item_escalation_focus_index
from ..operations.escalation_focus_index import execute_get_postmortem_action_item_remediation_attention_forecast
from ..operations.escalation_focus_index import execute_get_postmortem_action_item_escalation_attention_index
from ..operations.escalation_focus_index import execute_get_postmortem_action_item_remediation_coordination_forecast
from ..operations.escalation_focus_index import execute_get_postmortem_action_item_escalation_coordination_index


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-focus-index",
        summary="Escalation focus index for active owner workload",
    )
    def get_postmortem_action_item_escalation_focus_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_focus_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-attention-forecast",
        summary="Remediation attention forecast for action item ownership discipline",
    )
    def get_postmortem_action_item_remediation_attention_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_attention_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-attention-index",
        summary="Escalation attention index for action item ownership discipline",
    )
    def get_postmortem_action_item_escalation_attention_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_attention_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-coordination-forecast",
        summary="Remediation coordination forecast for action item workload alignment",
    )
    def get_postmortem_action_item_remediation_coordination_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_coordination_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-coordination-index",
        summary="Escalation coordination index for action item workload alignment",
    )
    def get_postmortem_action_item_escalation_coordination_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_coordination_index(runtime, auth, max_open_items_per_owner)
