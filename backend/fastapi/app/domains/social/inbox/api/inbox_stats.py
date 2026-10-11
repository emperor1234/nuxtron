"""Social/Inbox HTTP adapters beginning with inbox stats."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.delivery_failure_metrics import execute_delivery_failure_metrics
from ..operations.delivery_failure_metrics import execute_replay_pending_delivery_failures
from ..operations.list_messages import execute_inbox_stats
from ..operations.list_messages import execute_list_delivery_failures
from ..operations.list_messages import execute_mention_alerts
from ..operations.list_messages import execute_pending_approvals
from ..operations.replay_delivery_failure import execute_replay_delivery_failure
from ..operations.replay_delivery_failures_bulk import execute_replay_delivery_failures_bulk
from ..runtime import ContextRuntime
from ..schemas import DeliveryFailureBulkReplayRequest
from ..schemas import DeliveryFailureReplayPendingRequest
from ..schemas import ResponseReplayRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/inbox/stats")
    def inbox_stats(auth: AuthDep) -> dict[str, Any]:
        return execute_inbox_stats(runtime, auth)

    @router.get("/inbox/mentions/alerts")
    def mention_alerts(
        auth: AuthDep,
        severity: Annotated[str | None, Query(max_length=20)] = None,
        unresolved_only: Annotated[bool, Query()] = True,
    ) -> dict[str, Any]:
        return execute_mention_alerts(runtime, auth, severity, unresolved_only)

    @router.get("/inbox/approvals/pending")
    def pending_approvals(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_pending_approvals(runtime, auth, network, limit, offset)

    @router.get("/inbox/delivery-failures")
    def list_delivery_failures(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_delivery_failures(runtime, auth, status, limit, offset)

    @router.get("/inbox/delivery-failures/metrics")
    def delivery_failure_metrics(
        auth: AuthDep, network: Annotated[str | None, Query(max_length=40)] = None
    ) -> dict[str, Any]:
        return execute_delivery_failure_metrics(runtime, auth, network)

    @router.post(
        "/inbox/delivery-failures/{failure_id}/replay", responses={404: {"description": "Delivery failure not found"}}
    )
    async def replay_delivery_failure(failure_id: int, payload: ResponseReplayRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_replay_delivery_failure(runtime, failure_id, payload, auth)

    @router.post("/inbox/delivery-failures/replay-bulk")
    async def replay_delivery_failures_bulk(payload: DeliveryFailureBulkReplayRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_replay_delivery_failures_bulk(runtime, payload, auth)

    @router.post("/inbox/delivery-failures/replay-pending")
    async def replay_pending_delivery_failures(
        payload: DeliveryFailureReplayPendingRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return await execute_replay_pending_delivery_failures(runtime, payload, auth)
