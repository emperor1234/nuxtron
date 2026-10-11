"""Workflow use cases: list connector postmortems."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..graph import coerce_int as _coerce_int
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorPostmortemActionItemRequest
from ..schemas import WorkflowConnectorPostmortemActionItemUpdateRequest
from ..schemas import WorkflowConnectorPostmortemCloseRequest
from ..schemas import WorkflowConnectorPostmortemClosurePolicyRequest
from ..service import append_audit
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from typing import Any


def execute_list_connector_postmortems(runtime: WorkflowRuntime, connector_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:list", 120, 60)
    with runtime.lock:
        connector = next(
            (
                c
                for c in runtime.connectors
                if int(c.get("id", 0)) == connector_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        postmortems = [
            postmortem.copy()
            for postmortem in runtime.connector_postmortems
            if postmortem.get("tenant_id") == auth.tenant_id and int(postmortem.get("connector_id", 0)) == connector_id
        ]
    postmortems.sort(key=lambda item: parse_iso(item.get("created_at")), reverse=True)
    return {"status": "ok", "connector_id": connector_id, "postmortems": postmortems, "total": len(postmortems)}


def execute_create_postmortem_action_item(
    runtime: WorkflowRuntime,
    connector_id: int,
    postmortem_id: int,
    payload: WorkflowConnectorPostmortemActionItemRequest,
    auth: AuthDep,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:create", 120, 60)
    now = datetime.now(UTC)
    with runtime.lock:
        postmortem = next(
            (
                p
                for p in runtime.connector_postmortems
                if int(p.get("id", 0)) == postmortem_id
                and int(p.get("connector_id", 0)) == connector_id
                and (p.get("tenant_id") == auth.tenant_id)
            ),
            None,
        )
        if postmortem is None:
            raise HTTPException(status_code=404, detail="Postmortem not found.")
        action_items = postmortem.setdefault("action_items_detailed", [])
        action_item = {
            "id": len(action_items) + 1,
            "title": payload.title,
            "owner": payload.owner,
            "status": "open",
            "note": "",
            "due_at": (now + timedelta(hours=payload.due_in_hours)).isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        action_items.append(action_item)
        postmortem["updated_at"] = now.isoformat()
    append_audit(
        runtime, auth.tenant_id, "workflow_connector_postmortem_action_item_created", _coerce_int(action_item.get("id"))
    )
    return {"status": "ok", "action_item": action_item}


def execute_list_postmortem_action_items(
    runtime: WorkflowRuntime, connector_id: int, postmortem_id: int, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:list", 120, 60)
    with runtime.lock:
        postmortem = next(
            (
                p
                for p in runtime.connector_postmortems
                if int(p.get("id", 0)) == postmortem_id
                and int(p.get("connector_id", 0)) == connector_id
                and (p.get("tenant_id") == auth.tenant_id)
            ),
            None,
        )
        if postmortem is None:
            raise HTTPException(status_code=404, detail="Postmortem not found.")
        action_items = [item.copy() for item in postmortem.get("action_items_detailed") or []]
    return {
        "status": "ok",
        "connector_id": connector_id,
        "postmortem_id": postmortem_id,
        "action_items": action_items,
        "total": len(action_items),
    }


def execute_update_postmortem_action_item(
    runtime: WorkflowRuntime,
    connector_id: int,
    postmortem_id: int,
    action_item_id: int,
    payload: WorkflowConnectorPostmortemActionItemUpdateRequest,
    auth: AuthDep,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:update", 120, 60)
    normalized_status = payload.status.strip().lower()
    if normalized_status not in {"open", "in_progress", "done", "blocked"}:
        raise HTTPException(status_code=422, detail="Invalid action item status.")
    with runtime.lock:
        postmortem = next(
            (
                p
                for p in runtime.connector_postmortems
                if int(p.get("id", 0)) == postmortem_id
                and int(p.get("connector_id", 0)) == connector_id
                and (p.get("tenant_id") == auth.tenant_id)
            ),
            None,
        )
        if postmortem is None:
            raise HTTPException(status_code=404, detail="Postmortem not found.")
        action_item = next(
            (
                item
                for item in postmortem.get("action_items_detailed") or []
                if int(item.get("id", 0)) == action_item_id
            ),
            None,
        )
        if action_item is None:
            raise HTTPException(status_code=404, detail="Action item not found.")
        action_item["status"] = normalized_status
        action_item["note"] = payload.note
        action_item["updated_at"] = datetime.now(UTC).isoformat()
        postmortem["updated_at"] = datetime.now(UTC).isoformat()
    append_audit(runtime, auth.tenant_id, "workflow_connector_postmortem_action_item_updated", action_item_id)
    return {"status": "ok", "action_item": action_item}


def execute_close_postmortem(
    runtime: WorkflowRuntime,
    connector_id: int,
    postmortem_id: int,
    payload: WorkflowConnectorPostmortemCloseRequest,
    auth: AuthDep,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:close", 60, 60)
    with runtime.lock:
        postmortem = next(
            (
                p
                for p in runtime.connector_postmortems
                if int(p.get("id", 0)) == postmortem_id
                and int(p.get("connector_id", 0)) == connector_id
                and (p.get("tenant_id") == auth.tenant_id)
            ),
            None,
        )
        if postmortem is None:
            raise HTTPException(status_code=404, detail="Postmortem not found.")
        action_items = list(postmortem.get("action_items_detailed") or [])
        open_items = [item for item in action_items if str(item.get("status", "")).lower() != "done"]
        if payload.require_action_items_resolved and open_items:
            raise HTTPException(status_code=409, detail="Action items must be completed before closure.")
        policy = next(
            (
                p
                for p in runtime.connector_postmortem_closure_policies
                if p.get("tenant_id") == auth.tenant_id and bool(p.get("enabled", False))
            ),
            None,
        )
        if policy is not None:
            enforce_for_breached_only = bool(policy.get("enforce_for_breached_sla_only", False))
            needs_approval = True
            if enforce_for_breached_only:
                needs_approval = str(postmortem.get("closure_sla_status", "")).lower() == "breached"
            if needs_approval:
                required_approvals = int(policy.get("required_approvals", 1))
                approved_request = next(
                    (
                        r
                        for r in runtime.connector_postmortem_closure_requests
                        if r.get("tenant_id") == auth.tenant_id
                        and int(r.get("postmortem_id", 0)) == postmortem_id
                        and (r.get("status") == "approved")
                        and (len(r.get("approved_by") or []) >= required_approvals)
                    ),
                    None,
                )
                if approved_request is None:
                    raise HTTPException(
                        status_code=409, detail="Approved postmortem closure request required by policy."
                    )
        now = datetime.now(UTC)
        target_close_by = parse_iso(postmortem.get("target_close_by"))
        postmortem["status"] = "closed"
        postmortem["closed_at"] = now.isoformat()
        postmortem["closed_by"] = payload.closed_by
        postmortem["closure_note"] = payload.note
        postmortem["closure_sla_status"] = "met" if now <= target_close_by else "breached"
        postmortem["updated_at"] = now.isoformat()
    append_audit(runtime, auth.tenant_id, "workflow_connector_postmortem_closed", postmortem_id)
    return {"status": "ok", "postmortem": postmortem}


def execute_upsert_postmortem_closure_policy(
    runtime: WorkflowRuntime, payload: WorkflowConnectorPostmortemClosurePolicyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:closure-policy:upsert", 60, 60)
    with runtime.lock:
        policy = next(
            (p for p in runtime.connector_postmortem_closure_policies if p.get("tenant_id") == auth.tenant_id), None
        )
        if policy is None:
            policy = {
                "id": len(runtime.connector_postmortem_closure_policies) + 1,
                "tenant_id": auth.tenant_id,
                "enabled": payload.enabled,
                "required_approvals": payload.required_approvals,
                "approver_roles": payload.approver_roles,
                "enforce_for_breached_sla_only": payload.enforce_for_breached_sla_only,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            runtime.connector_postmortem_closure_policies.append(policy)
        else:
            policy["enabled"] = payload.enabled
            policy["required_approvals"] = payload.required_approvals
            policy["approver_roles"] = payload.approver_roles
            policy["enforce_for_breached_sla_only"] = payload.enforce_for_breached_sla_only
            policy["updated_at"] = datetime.now(UTC).isoformat()
    append_audit(runtime, auth.tenant_id, "workflow_connector_postmortem_closure_policy_upserted", int(policy["id"]))
    return {"status": "ok", "policy": policy}


def execute_get_postmortem_closure_policy(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:closure-policy:get", 120, 60)
    with runtime.lock:
        policy = next(
            (p.copy() for p in runtime.connector_postmortem_closure_policies if p.get("tenant_id") == auth.tenant_id),
            None,
        )
    if policy is None:
        return {
            "status": "ok",
            "policy": {
                "enabled": False,
                "required_approvals": 1,
                "approver_roles": [],
                "enforce_for_breached_sla_only": False,
            },
        }
    return {"status": "ok", "policy": policy}


def execute_create_postmortem_closure_request(
    runtime: WorkflowRuntime, connector_id: int, postmortem_id: int, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:closure-requests:create", 90, 60)
    with runtime.lock:
        postmortem = next(
            (
                p
                for p in runtime.connector_postmortems
                if int(p.get("id", 0)) == postmortem_id
                and int(p.get("connector_id", 0)) == connector_id
                and (p.get("tenant_id") == auth.tenant_id)
            ),
            None,
        )
        if postmortem is None:
            raise HTTPException(status_code=404, detail="Postmortem not found.")
        existing = next(
            (
                r
                for r in runtime.connector_postmortem_closure_requests
                if r.get("tenant_id") == auth.tenant_id
                and int(r.get("postmortem_id", 0)) == postmortem_id
                and (r.get("status") == "pending")
            ),
            None,
        )
        if existing is not None:
            return {"status": "ok", "closure_request": existing, "reused": True}
        policy = next(
            (p for p in runtime.connector_postmortem_closure_policies if p.get("tenant_id") == auth.tenant_id), None
        )
        required_approvals = int((policy or {}).get("required_approvals", 1))
        closure_request = {
            "id": len(runtime.connector_postmortem_closure_requests) + 1,
            "tenant_id": auth.tenant_id,
            "connector_id": connector_id,
            "postmortem_id": postmortem_id,
            "status": "pending",
            "required_approvals": required_approvals,
            "approved_by": [],
            "rejected_by": [],
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.connector_postmortem_closure_requests.append(closure_request)
    append_audit(
        runtime,
        auth.tenant_id,
        "workflow_connector_postmortem_closure_request_created",
        _coerce_int(closure_request.get("id")),
    )
    return {"status": "ok", "closure_request": closure_request, "reused": False}
