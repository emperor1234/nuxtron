"""Workflow HTTP operations: remediation orchestration forecast."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.remediation_orchestration_forecast import (
    execute_get_postmortem_action_item_remediation_orchestration_forecast,
)
from ..operations.remediation_orchestration_forecast import (
    execute_get_postmortem_action_item_escalation_orchestration_index,
)
from ..operations.remediation_orchestration_forecast import (
    execute_get_postmortem_action_item_remediation_synchronization_forecast,
)
from ..operations.remediation_orchestration_forecast import (
    execute_get_postmortem_action_item_escalation_synchronization_index,
)
from ..operations.remediation_orchestration_forecast import (
    execute_get_postmortem_action_item_remediation_harmony_forecast,
)


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-orchestration-forecast",
        summary="Remediation orchestration forecast for action item execution cadence",
    )
    def get_postmortem_action_item_remediation_orchestration_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_orchestration_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-orchestration-index",
        summary="Escalation orchestration index for action item execution cadence",
    )
    def get_postmortem_action_item_escalation_orchestration_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_orchestration_index(
            runtime, auth, max_open_items_per_owner
        )

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-synchronization-forecast",
        summary="Remediation synchronization forecast for owner execution alignment",
    )
    def get_postmortem_action_item_remediation_synchronization_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_synchronization_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-synchronization-index",
        summary="Escalation synchronization index for owner execution alignment",
    )
    def get_postmortem_action_item_escalation_synchronization_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_synchronization_index(
            runtime, auth, max_open_items_per_owner
        )

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-harmony-forecast",
        summary="Remediation harmony forecast for owner workload cohesion",
    )
    def get_postmortem_action_item_remediation_harmony_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_harmony_forecast(runtime, auth, days_horizon)
