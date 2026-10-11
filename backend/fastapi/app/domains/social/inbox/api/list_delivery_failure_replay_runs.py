"""Social/Inbox HTTP adapters beginning with list delivery failure replay runs."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.delivery_failure_metrics import execute_inbox_ops_config
from ..operations.inbox_ops_go_live_gate import execute_inbox_ops_go_live_gate
from ..operations.inbox_ops_go_live_gate import execute_resolve_delivery_failure
from ..operations.inbox_ops_go_live_gate import execute_resolve_delivery_failures_bulk
from ..operations.list_messages import execute_list_delivery_failure_replay_runs
from ..operations.replay_delivery_failure import execute_create_saved_reply
from ..operations.replay_delivery_failure import execute_delivery_failure_replay_run_performance
from ..operations.replay_delivery_failures_bulk import execute_inbox_ops_runbooks
from ..runtime import ContextRuntime
from ..schemas import DeliveryFailureBulkResolveRequest
from ..schemas import DeliveryFailureResolveRequest
from ..schemas import SavedReplyRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/inbox/delivery-failures/replay-runs")
    def list_delivery_failure_replay_runs(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_delivery_failure_replay_runs(runtime, auth, network, limit, offset)

    @router.get("/inbox/delivery-failures/replay-runs/performance")
    def delivery_failure_replay_run_performance(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
        operator: Annotated[str | None, Query(max_length=120)] = None,
        window_hours: Annotated[int, Query(ge=1, le=24 * 30)] = 24,
    ) -> dict[str, Any]:
        return execute_delivery_failure_replay_run_performance(runtime, auth, network, operator, window_hours)

    @router.get("/inbox/ops-config")
    def inbox_ops_config(auth: AuthDep) -> dict[str, Any]:
        return execute_inbox_ops_config(runtime, auth)

    @router.get("/inbox/ops/runbooks")
    def inbox_ops_runbooks(auth: AuthDep, code: Annotated[str | None, Query(max_length=120)] = None) -> dict[str, Any]:
        return execute_inbox_ops_runbooks(runtime, auth, code)

    @router.get("/inbox/ops/go-live-gate")
    def inbox_ops_go_live_gate(auth: AuthDep) -> dict[str, Any]:
        return execute_inbox_ops_go_live_gate(runtime, auth)

    @router.post(
        "/inbox/delivery-failures/{failure_id}/resolve", responses={404: {"description": "Delivery failure not found"}}
    )
    def resolve_delivery_failure(
        failure_id: int, payload: DeliveryFailureResolveRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_resolve_delivery_failure(runtime, failure_id, payload, auth)

    @router.post("/inbox/delivery-failures/resolve-bulk")
    def resolve_delivery_failures_bulk(payload: DeliveryFailureBulkResolveRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_resolve_delivery_failures_bulk(runtime, payload, auth)

    @router.post("/inbox/saved-replies")
    def create_saved_reply(payload: SavedReplyRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_saved_reply(runtime, payload, auth)
