"""Workflow HTTP operations: replay connector queue item."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorReplayRequest
from fastapi import APIRouter
from typing import Any
from ..operations.replay_connector_queue_item import execute_replay_connector_queue_item


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.post(
        "/workflow-connectors/{connector_id}/replay-queue/{item_id}/replay",
        responses={404: {"description": EXECUTION_NOT_FOUND}},
    )
    def replay_connector_queue_item(
        connector_id: int, item_id: int, payload: WorkflowConnectorReplayRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_replay_connector_queue_item(runtime, connector_id, item_id, payload, auth)
