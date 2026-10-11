"""Workflow HTTP operations: list connector postmortems."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorPostmortemActionItemRequest
from ..schemas import WorkflowConnectorPostmortemActionItemUpdateRequest
from ..schemas import WorkflowConnectorPostmortemCloseRequest
from ..schemas import WorkflowConnectorPostmortemClosurePolicyRequest
from fastapi import APIRouter
from typing import Any
from ..operations.list_connector_postmortems import execute_list_connector_postmortems
from ..operations.list_connector_postmortems import execute_create_postmortem_action_item
from ..operations.list_connector_postmortems import execute_list_postmortem_action_items
from ..operations.list_connector_postmortems import execute_update_postmortem_action_item
from ..operations.list_connector_postmortems import execute_close_postmortem
from ..operations.list_connector_postmortems import execute_upsert_postmortem_closure_policy
from ..operations.list_connector_postmortems import execute_get_postmortem_closure_policy
from ..operations.list_connector_postmortems import execute_create_postmortem_closure_request


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get(
        "/workflow-connectors/{connector_id}/postmortems", responses={404: {"description": EXECUTION_NOT_FOUND}}
    )
    def list_connector_postmortems(connector_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_list_connector_postmortems(runtime, connector_id, auth)

    @router.post(
        "/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items",
        responses={404: {"description": EXECUTION_NOT_FOUND}},
    )
    def create_postmortem_action_item(
        connector_id: int, postmortem_id: int, payload: WorkflowConnectorPostmortemActionItemRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_create_postmortem_action_item(runtime, connector_id, postmortem_id, payload, auth)

    @router.get(
        "/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items",
        responses={404: {"description": EXECUTION_NOT_FOUND}},
    )
    def list_postmortem_action_items(connector_id: int, postmortem_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_list_postmortem_action_items(runtime, connector_id, postmortem_id, auth)

    @router.patch(
        "/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items/{action_item_id}",
        responses={404: {"description": EXECUTION_NOT_FOUND}},
    )
    def update_postmortem_action_item(
        connector_id: int,
        postmortem_id: int,
        action_item_id: int,
        payload: WorkflowConnectorPostmortemActionItemUpdateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        return execute_update_postmortem_action_item(
            runtime, connector_id, postmortem_id, action_item_id, payload, auth
        )

    @router.post(
        "/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/close",
        responses={404: {"description": EXECUTION_NOT_FOUND}},
    )
    def close_postmortem(
        connector_id: int, postmortem_id: int, payload: WorkflowConnectorPostmortemCloseRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_close_postmortem(runtime, connector_id, postmortem_id, payload, auth)

    @router.post("/workflow-connectors/postmortems/closure-policy", summary="Upsert postmortem closure approval policy")
    def upsert_postmortem_closure_policy(
        payload: WorkflowConnectorPostmortemClosurePolicyRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_upsert_postmortem_closure_policy(runtime, payload, auth)

    @router.get("/workflow-connectors/postmortems/closure-policy", summary="Get postmortem closure approval policy")
    def get_postmortem_closure_policy(auth: AuthDep) -> dict[str, Any]:
        return execute_get_postmortem_closure_policy(runtime, auth)

    @router.post(
        "/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/closure-requests",
        responses={404: {"description": EXECUTION_NOT_FOUND}},
    )
    def create_postmortem_closure_request(connector_id: int, postmortem_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_create_postmortem_closure_request(runtime, connector_id, postmortem_id, auth)
