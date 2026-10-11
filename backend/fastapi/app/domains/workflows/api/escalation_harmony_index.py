"""Workflow HTTP operations: escalation harmony index."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.escalation_harmony_index import execute_get_postmortem_action_item_escalation_harmony_index
from ..operations.escalation_harmony_index import execute_get_postmortem_action_item_remediation_rhythm_forecast
from ..operations.escalation_harmony_index import execute_get_postmortem_action_item_escalation_rhythm_index
from ..operations.escalation_harmony_index import execute_get_postmortem_action_item_remediation_tempo_forecast
from ..operations.escalation_harmony_index import execute_get_postmortem_action_item_escalation_tempo_index


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-harmony-index",
        summary="Escalation harmony index for owner workload cohesion",
    )
    def get_postmortem_action_item_escalation_harmony_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_harmony_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-rhythm-forecast",
        summary="Remediation rhythm forecast for owner execution cadence",
    )
    def get_postmortem_action_item_remediation_rhythm_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_rhythm_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-rhythm-index",
        summary="Escalation rhythm index for owner execution cadence",
    )
    def get_postmortem_action_item_escalation_rhythm_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_rhythm_index(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-tempo-forecast",
        summary="Remediation tempo forecast for owner execution pacing",
    )
    def get_postmortem_action_item_remediation_tempo_forecast(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_tempo_forecast(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalation-tempo-index",
        summary="Escalation tempo index for owner execution pacing",
    )
    def get_postmortem_action_item_escalation_tempo_index(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_escalation_tempo_index(runtime, auth, max_open_items_per_owner)
