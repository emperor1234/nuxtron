"""Workflow HTTP operations: ownership stability forecast."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.ownership_stability_forecast import execute_get_postmortem_action_item_ownership_stability_forecast
from ..operations.ownership_stability_forecast import execute_get_postmortem_action_item_escalation_burn_rate
from ..operations.ownership_stability_forecast import execute_get_postmortem_action_item_handoff_resilience_forecast
from ..operations.ownership_stability_forecast import execute_get_postmortem_action_item_backlog_clearance_confidence
from ..operations.ownership_stability_forecast import execute_get_postmortem_action_item_remediation_velocity_forecast
from ..operations.ownership_stability_forecast import execute_get_postmortem_action_item_escalation_recovery_readiness


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/ownership-stability-forecast",
        summary="Ownership stability forecast for active remediation continuity",
    )
    def get_postmortem_action_item_ownership_stability_forecast(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_ownership_stability_forecast(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-burn-rate",
        summary="Escalation burn-rate guidance for short-horizon backlog reduction",
    )
    def get_postmortem_action_item_escalation_burn_rate(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_burn_rate(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/handoff-resilience-forecast",
        summary="Handoff resilience forecast for open remediation ownership",
    )
    def get_postmortem_action_item_handoff_resilience_forecast(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_handoff_resilience_forecast(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/backlog-clearance-confidence",
        summary="Backlog clearance confidence over the selected horizon",
    )
    def get_postmortem_action_item_backlog_clearance_confidence(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_backlog_clearance_confidence(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-velocity-forecast",
        summary="Remediation velocity forecast for open action-item backlog",
    )
    def get_postmortem_action_item_remediation_velocity_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_velocity_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-recovery-readiness",
        summary="Escalation recovery readiness for near-term stabilization",
    )
    def get_postmortem_action_item_escalation_recovery_readiness(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_recovery_readiness(runtime, auth, max_open_items_per_owner)
