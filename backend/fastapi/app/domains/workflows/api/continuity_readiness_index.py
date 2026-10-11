"""Workflow HTTP operations: continuity readiness index."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.continuity_readiness_index import execute_get_postmortem_action_item_continuity_readiness_index
from ..operations.continuity_readiness_index import execute_get_postmortem_action_item_escalation_drain_forecast
from ..operations.continuity_readiness_index import execute_get_postmortem_action_item_remediation_confidence_forecast
from ..operations.continuity_readiness_index import execute_get_postmortem_action_item_escalation_stabilization_index
from ..operations.continuity_readiness_index import execute_get_postmortem_action_item_remediation_posture_score
from ..operations.continuity_readiness_index import execute_get_postmortem_action_item_escalation_runway_forecast


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/continuity-readiness-index",
        summary="Continuity readiness index for ongoing remediation ownership",
    )
    def get_postmortem_action_item_continuity_readiness_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_continuity_readiness_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-drain-forecast",
        summary="Escalation drain forecast for short-horizon backlog reduction",
    )
    def get_postmortem_action_item_escalation_drain_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_drain_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-confidence-forecast",
        summary="Remediation confidence forecast for short-horizon backlog execution",
    )
    def get_postmortem_action_item_remediation_confidence_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_confidence_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-stabilization-index",
        summary="Escalation stabilization index for active remediation backlog",
    )
    def get_postmortem_action_item_escalation_stabilization_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_stabilization_index(
            runtime, auth, max_open_items_per_owner
        )

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-posture-score",
        summary="Remediation posture score for active action-item backlog",
    )
    def get_postmortem_action_item_remediation_posture_score(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_posture_score(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-runway-forecast",
        summary="Escalation runway forecast for near-term backlog stability",
    )
    def get_postmortem_action_item_escalation_runway_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_runway_forecast(runtime, auth, days_horizon)
