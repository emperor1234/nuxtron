"""Workflow HTTP operations: readiness forecast."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.readiness_forecast import execute_get_postmortem_action_item_readiness_forecast
from ..operations.readiness_forecast import execute_get_postmortem_action_item_remediation_throughput
from ..operations.readiness_forecast import execute_get_postmortem_action_item_risk_burndown
from ..operations.readiness_forecast import execute_get_postmortem_action_item_capacity_scenarios
from ..operations.readiness_forecast import execute_get_postmortem_action_item_remediation_sla


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/postmortems/action-items/readiness-forecast",
        summary="Readiness forecast based on current ownership and escalation pressure",
    )
    def get_postmortem_action_item_readiness_forecast(
        auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_readiness_forecast(runtime, auth, max_open_items_per_owner)

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-throughput",
        summary="Daily remediation throughput required to stabilize action-item risk",
    )
    def get_postmortem_action_item_remediation_throughput(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_throughput(
            runtime, auth, max_open_items_per_owner, days_horizon
        )

    @router.get(
        "/workflow-connectors/postmortems/action-items/risk-burndown",
        summary="Risk burndown targets for postmortem action-item governance",
    )
    def get_postmortem_action_item_risk_burndown(
        auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_risk_burndown(runtime, auth, days_horizon)

    @router.get(
        "/workflow-connectors/postmortems/action-items/capacity-scenarios",
        summary="Capacity planning scenarios for action-item remediation",
    )
    def get_postmortem_action_item_capacity_scenarios(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_capacity_scenarios(
            runtime, auth, max_open_items_per_owner, days_horizon
        )

    @router.get(
        "/workflow-connectors/postmortems/action-items/remediation-sla",
        summary="Remediation SLA adherence score for open action-item backlog",
    )
    def get_postmortem_action_item_remediation_sla(
        auth: AuthDep, sla_hours: Annotated[int, Query(ge=1, le=168)] = 24
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_remediation_sla(runtime, auth, sla_hours)
