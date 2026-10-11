"""Workflow HTTP operations: stability score."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.stability_score import execute_get_postmortem_action_item_stability_score
from ..operations.stability_score import execute_get_postmortem_action_item_handoff_plan
from ..operations.stability_score import execute_get_postmortem_action_item_resilience_snapshot
from ..operations.stability_score import execute_get_postmortem_action_item_remediation_queue


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/stability-score",
        summary="Ownership stability score for active incident operations",
    )
    def get_postmortem_action_item_stability_score(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_stability_score(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/handoff-plan",
        summary="Handoff plan recommendations for active owner risk",
    )
    def get_postmortem_action_item_handoff_plan(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_handoff_plan(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/resilience-snapshot",
        summary="Operational resilience snapshot for active action-item governance",
    )
    def get_postmortem_action_item_resilience_snapshot(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_resilience_snapshot(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-queue",
        summary="Prioritized remediation queue for ownership resilience actions",
    )
    def get_postmortem_action_item_remediation_queue(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_queue(runtime, auth, max_open_items_per_owner, limit)
