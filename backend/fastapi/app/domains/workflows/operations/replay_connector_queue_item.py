"""Workflow use cases: replay connector queue item."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..incidents import close_sla_alerts_if_recovered
from ..incidents import record_sla_alert
from ..reliability import ensure_reliability_fields
from ..reliability import process_replay_item_locked
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorReplayRequest
from ..service import append_audit
from fastapi import HTTPException
from typing import Any


def execute_replay_connector_queue_item(
    runtime: WorkflowRuntime, connector_id: int, item_id: int, payload: WorkflowConnectorReplayRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:replay:run", 90, 60)
    with runtime.lock:
        connector = next(
            (c for c in runtime.connectors if c.get("id") == connector_id and c.get("tenant_id") == auth.tenant_id),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        ensure_reliability_fields(connector)
        item = next(
            (
                i
                for i in runtime.connector_replay_queue
                if i.get("id") == item_id
                and i.get("tenant_id") == auth.tenant_id
                and (i.get("connector_id") == connector_id)
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        if item.get("status") != "pending":
            raise HTTPException(status_code=409, detail="Replay item already processed.")
        result = process_replay_item_locked(connector=connector, item=item, force_success=payload.force_success)
        reliability = result["slo"]
        record_sla_alert(runtime, auth.tenant_id, connector, reliability)
        close_sla_alerts_if_recovered(runtime, auth.tenant_id, connector_id, reliability)
    append_audit(runtime, auth.tenant_id, "workflow_connector_replay_processed", item_id)
    return {"status": "ok", "item": item, "connector": connector, "slo": reliability}
