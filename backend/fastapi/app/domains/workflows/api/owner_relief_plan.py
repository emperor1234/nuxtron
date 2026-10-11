"""Workflow HTTP operations: owner relief plan."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.owner_relief_plan import execute_get_postmortem_action_item_owner_relief_plan
from ..operations.owner_relief_plan import execute_get_postmortem_action_item_escalation_clearance_eta
from ..operations.owner_relief_plan import execute_get_postmortem_action_item_mitigation_readiness
from ..operations.owner_relief_plan import execute_get_postmortem_action_item_owner_coverage_forecast
from ..operations.owner_relief_plan import execute_get_postmortem_action_item_handoff_pressure
from ..operations.owner_relief_plan import execute_get_postmortem_action_item_remediation_momentum


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/owner-relief-plan",
        summary="Owner relief plan to reduce overloaded action-item queues",
    )
    def get_postmortem_action_item_owner_relief_plan(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_owner_relief_plan(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-clearance-eta",
        summary="Estimated days to clear current escalation backlog",
    )
    def get_postmortem_action_item_escalation_clearance_eta(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_clearance_eta(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/mitigation-readiness",
        summary="Mitigation readiness score for active action-item backlog",
    )
    def get_postmortem_action_item_mitigation_readiness(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_mitigation_readiness(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/owner-coverage-forecast",
        summary="Owner coverage forecast for near-term remediation continuity",
    )
    def get_postmortem_action_item_owner_coverage_forecast(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_owner_coverage_forecast(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/handoff-pressure",
        summary="Handoff pressure score across active action-item ownership lanes",
    )
    def get_postmortem_action_item_handoff_pressure(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_handoff_pressure(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-momentum",
        summary="Remediation momentum score for current action-item backlog dynamics",
    )
    def get_postmortem_action_item_remediation_momentum(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_momentum(runtime, auth, days_horizon)
