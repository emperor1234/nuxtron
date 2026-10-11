"""Workflow HTTP operations: owner workload."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorActionItemRebalanceRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.owner_workload import execute_get_postmortem_action_item_owner_workload
from ..operations.owner_workload import execute_get_postmortem_action_item_rebalance_suggestions
from ..operations.owner_workload import execute_get_postmortem_action_item_workload_hotspots
from ..operations.owner_workload import execute_get_postmortem_action_item_surge_alerts
from ..operations.owner_workload import execute_get_postmortem_action_item_balance_index


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/owner-workload",
        summary="Owner workload dashboard for action-item governance",
    )
    def get_postmortem_action_item_owner_workload(auth: AuthDep, include_done: bool = False) -> dict[str, Any]:
        return execute_get_postmortem_action_item_owner_workload(runtime, auth, include_done)

    @router.post(
        "/workflow-connectors/postmortems/action-items/rebalance-suggestions",
        summary="Recommend owner rebalance suggestions for open action items",
    )
    def get_postmortem_action_item_rebalance_suggestions(
        payload: WorkflowConnectorActionItemRebalanceRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_rebalance_suggestions(runtime, payload, auth)

    @router.get(
        "/workflow-connectors/postmortems/action-items/workload-hotspots", summary="Owner workload hotspots dashboard"
    )
    def get_postmortem_action_item_workload_hotspots(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        max_overdue_items_per_owner: Annotated[int, Query(ge=0, le=100)] = 1,
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_workload_hotspots(
            runtime, auth, max_open_items_per_owner, max_overdue_items_per_owner
        )

    @router.get(
        "/workflow-connectors/postmortems/action-items/surge-alerts",
        summary="Owner surge alerts for escalating workload",
    )
    def get_postmortem_action_item_surge_alerts(
        auth: AuthDep,
        lookback_hours: Annotated[int, Query(ge=1, le=720)] = 24,
        min_new_open_escalations: Annotated[int, Query(ge=1, le=50)] = 1,
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_surge_alerts(runtime, auth, lookback_hours, min_new_open_escalations)

    @router.get(
        "/workflow-connectors/postmortems/action-items/balance-index",
        summary="Balance index for owner action-item distribution",
    )
    def get_postmortem_action_item_balance_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_balance_index(runtime, auth, max_open_items_per_owner)
