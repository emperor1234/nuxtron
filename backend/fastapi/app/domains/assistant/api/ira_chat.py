"""Assistant HTTP adapters beginning with ira chat."""

from ..constants import AuthDep
from ..operations.ira_chat import execute_ira_batch_actions
from ..operations.ira_chat import execute_ira_chat
from ..operations.ira_chat import execute_ira_monitor
from ..operations.ira_execute_action import execute_ira_create_ab_test
from ..operations.ira_execute_action import execute_ira_execute_action
from ..operations.ira_execute_action import execute_ira_performance_analytics
from ..operations.ira_ml_retrieval_query import execute_ira_cost_summary
from ..operations.ira_ml_retrieval_query import execute_ira_rollback_action
from ..runtime import ContextRuntime
from ..schemas import IRAAbTestCreateRequest
from ..schemas import IRAActionRequest
from ..schemas import IRABatchActionsRequest
from ..schemas import IRAMessageRequest
from fastapi import APIRouter
from fastapi import Header
from typing import Annotated
from typing import Any


def register(router: APIRouter, context_runtime: ContextRuntime):

    @router.post("/chat", responses={422: {"description": "IRA autonomy or connector is disabled"}})
    def ira_chat(payload: IRAMessageRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_chat(context_runtime, payload, auth)

    @router.post(
        "/actions",
        responses={
            403: {"description": "High-impact actions blocked by policy"},
            422: {"description": "IRA autonomy/connector disabled"},
            423: {"description": "Protection mode active"},
        },
    )
    def ira_execute_action(
        payload: IRAActionRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_ira_execute_action(context_runtime, payload, auth, x_super_admin_key)

    @router.post(
        "/actions/{action_snapshot_id}/rollback",
        responses={
            403: {"description": "Super admin required"},
            404: {"description": "Snapshot not found"},
            422: {"description": "Rollback not possible"},
        },
    )
    def ira_rollback_action(
        action_snapshot_id: int,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_ira_rollback_action(context_runtime, action_snapshot_id, auth, x_super_admin_key)

    @router.get("/monitor")
    def ira_monitor(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_monitor(context_runtime, auth)

    @router.post("/actions/batch", responses={422: {"description": "IRA autonomy disabled or validation failed"}})
    def ira_batch_actions(
        payload: IRABatchActionsRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_ira_batch_actions(context_runtime, payload, auth, x_super_admin_key)

    @router.get("/costs")
    def ira_cost_summary(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_cost_summary(context_runtime, auth)

    @router.get("/performance")
    def ira_performance_analytics(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_performance_analytics(context_runtime, auth)

    @router.post("/ab-tests", responses={422: {"description": "Traffic split must sum to 1.0 and match variant count"}})
    def ira_create_ab_test(payload: IRAAbTestCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_create_ab_test(context_runtime, payload, auth)
