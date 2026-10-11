"""Workflow HTTP operations: coverage gaps."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.coverage_gaps import execute_get_postmortem_action_item_coverage_gaps
from ..operations.coverage_gaps import execute_get_postmortem_action_item_handoff_readiness
from ..operations.coverage_gaps import execute_get_postmortem_action_item_continuity_risks
from ..operations.coverage_gaps import execute_get_postmortem_action_item_ownership_churn


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/coverage-gaps",
        summary="Coverage gaps in action-item ownership and capacity",
    )
    def get_postmortem_action_item_coverage_gaps(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_coverage_gaps(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/handoff-readiness",
        summary="Owner handoff readiness for active incident action items",
    )
    def get_postmortem_action_item_handoff_readiness(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        critical_open_escalations_threshold: Annotated[int, Query(ge=1, le=20)] = 1,
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_handoff_readiness(
            runtime, auth, max_open_items_per_owner, critical_open_escalations_threshold
        )

    @router.get(
        "/workflow-connectors/postmortems/action-items/continuity-risks",
        summary="Continuity risks for owner concentration on active incident work",
    )
    def get_postmortem_action_item_continuity_risks(
        auth: AuthDep, min_single_owner_items: Annotated[int, Query(ge=1, le=100)] = 2
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_continuity_risks(runtime, auth, min_single_owner_items)

    @router.get(
        "/workflow-connectors/postmortems/action-items/ownership-churn",
        summary="Ownership churn indicators for active connector incident work",
    )
    def get_postmortem_action_item_ownership_churn(
        auth: AuthDep, min_owner_switch_risk_items: Annotated[int, Query(ge=1, le=100)] = 2
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_ownership_churn(runtime, auth, min_owner_switch_risk_items)
