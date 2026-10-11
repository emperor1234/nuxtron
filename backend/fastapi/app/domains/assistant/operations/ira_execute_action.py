"""Assistant use cases: ira execute action."""

from ..constants import AUTONOMY_DISABLED_DETAIL
from ..constants import AuthDep
from ..constants import HIGH_IMPACT_TARGETS
from ..runtime import ContextRuntime
from ..schemas import IRAAbTestCreateRequest
from ..schemas import IRAAbTestRecordRequest
from ..schemas import IRAActionRequest
from ..services.reasoning_support import _now_iso
from .copilot_env_template import helper_deliver_email
from .db_dsn import helper_append_ira_event
from .db_dsn import helper_audit
from .db_dsn import helper_connector_enabled
from .db_dsn import helper_get_or_create_connector
from .db_dsn import helper_get_or_create_control
from .db_dsn import helper_is_super_admin
from .db_dsn import helper_require_super_admin_for_control
from .db_dsn import helper_requires_explicit_approval
from .db_dsn import helper_requires_human_validation
from .db_dsn import helper_validate_rbac_abac
from .ira_response import helper_deliver_slack
from .ira_response import helper_deliver_whatsapp
from .ira_response import helper_notify_ops_email
from .ira_response import helper_notify_ops_slack
from .ira_response import helper_record_cost
from .ira_response import helper_record_performance
from fastapi import HTTPException
from fastapi import Header
from typing import Annotated
from typing import Any


def execute_ira_execute_action(
    context_runtime: ContextRuntime,
    payload: IRAActionRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:action", 120, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        helper_require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail="IRA autonomous execution is restricted to super admin sessions.",
        )
        if not bool(control.get("autonomy_enabled", True)):
            raise HTTPException(status_code=422, detail=AUTONOMY_DISABLED_DETAIL)
        helper_validate_rbac_abac(
            context_runtime, payload=payload, auth=auth, verified_super_admin=helper_is_super_admin(x_super_admin_key)
        )
        if payload.target in HIGH_IMPACT_TARGETS and (not bool(control.get("allow_high_impact_actions", False))):
            raise HTTPException(
                status_code=403, detail="IRA high-impact actions require explicit allow_high_impact_actions=true."
            )
        if bool(control.get("protection_mode", False)) and payload.target in HIGH_IMPACT_TARGETS:
            raise HTTPException(
                status_code=423, detail="IRA protection mode is active. High-impact actions are temporarily blocked."
            )
        if not payload.dry_run and (not payload.user_consent):
            raise HTTPException(status_code=422, detail="IRA action requires explicit user consent for execution.")
        if not payload.dry_run and (not payload.consent_reference.strip()):
            raise HTTPException(status_code=422, detail="IRA action requires consent_reference for auditability.")
        if not payload.dry_run and (not payload.risk_analysis_approved):
            raise HTTPException(
                status_code=422, detail="IRA action requires approved risk analysis before consented execution."
            )
        if helper_requires_explicit_approval(payload) and (not payload.explicit_approval):
            raise HTTPException(
                status_code=403, detail="This command is blocked for autonomous mode without explicit approval."
            )
        requires_human_validation = helper_requires_human_validation(payload)
        if payload.target in HIGH_IMPACT_TARGETS and (not payload.human_validation_approved) and (not payload.dry_run):
            raise HTTPException(
                status_code=422, detail="High-impact financial/security operations require human validation approval."
            )
        if requires_human_validation and (not payload.human_validation_approved) and (not payload.dry_run):
            raise HTTPException(status_code=422, detail="This action requires human validation before execution.")
        dispute_amount = float(payload.payload.get("dispute_amount_gbp", 0.0) or 0.0)
        dispute_mode = bool(payload.payload.get("is_dispute", False)) or "dispute" in payload.command.strip().lower()
        max_dispute = float(control.get("max_dispute_auto_resolution_gbp", 50.0))
        if dispute_mode and (not payload.human_validation_approved) and (not payload.dry_run):
            raise HTTPException(status_code=422, detail="All dispute operations require human validation approval.")
        if payload.target in {"admin", "billing", "credits", "security"}:
            connector_channel = "admin"
        elif payload.target == "email":
            connector_channel = "email"
        elif payload.target == "customer_support":
            connector_channel = "customer_support"
        else:
            connector_channel = "chat"
        if not payload.dry_run and (not helper_connector_enabled(context_runtime, auth.tenant_id, connector_channel)):
            raise HTTPException(status_code=422, detail=f"IRA connector for channel {connector_channel} is disabled.")
        connector = helper_get_or_create_connector(context_runtime, auth.tenant_id, connector_channel)
        result: dict[str, Any] = {
            "target": payload.target,
            "command": payload.command,
            "dry_run": payload.dry_run,
            "executed": not payload.dry_run,
            "consent_reference": payload.consent_reference,
            "human_validation_required": requires_human_validation,
            "dashboard_scope": payload.dashboard_scope,
        }
        if payload.target in {"customers", "chats"} and (not payload.dry_run):
            context_runtime.chatbot_conversations_memory.append(
                {
                    "id": len(context_runtime.chatbot_conversations_memory) + 1,
                    "tenant_id": auth.tenant_id,
                    "chatbot_id": 0,
                    "session_id": f"ira-{len(context_runtime.chatbot_conversations_memory) + 1}",
                    "user_message": str(payload.payload.get("message", payload.command)),
                    "assistant_message": "Handled by IRA autonomous operations.",
                    "created_at": _now_iso(),
                }
            )
            result["channel"] = "chat"
            if str(connector.get("provider", "internal")).strip().lower() == "slack":
                result["provider_result"] = helper_deliver_slack(
                    context_runtime, tenant_id=auth.tenant_id, connector=connector, payload=payload.payload
                )
        if payload.target == "email" and (not payload.dry_run):
            ticket_id = len(context_runtime.tickets_memory) + 1
            context_runtime.tickets_memory.append(
                {
                    "id": ticket_id,
                    "tenant_id": auth.tenant_id,
                    "subject": str(payload.payload.get("subject", "IRA automated email action")),
                    "description": str(payload.payload.get("body", payload.command)),
                    "status": "queued_for_human_validation" if requires_human_validation else "resolved",
                    "priority": "normal",
                    "channel": "email",
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                }
            )
            result["ticket_id"] = ticket_id
            result["provider_result"] = helper_deliver_email(
                context_runtime, tenant_id=auth.tenant_id, connector=connector, payload=payload.payload
            )
        if payload.target in {"admin", "billing", "credits", "security"} and (not payload.dry_run):
            result["provider_result"] = helper_deliver_slack(
                context_runtime, tenant_id=auth.tenant_id, connector=connector, payload=payload.payload
            )
            result["requires_review"] = True
        if payload.target == "customer_support" and (not payload.dry_run):
            provider = str(connector.get("provider", "internal")).strip().lower()
            if provider == "twilio_whatsapp":
                result["provider_result"] = helper_deliver_whatsapp(
                    context_runtime, tenant_id=auth.tenant_id, connector=connector, payload=payload.payload
                )
            else:
                ticket_id = len(context_runtime.tickets_memory) + 1
                context_runtime.tickets_memory.append(
                    {
                        "id": ticket_id,
                        "tenant_id": auth.tenant_id,
                        "subject": str(payload.payload.get("subject", "IRA customer support case")),
                        "description": str(payload.payload.get("body", payload.command)),
                        "status": "queued_for_human_validation" if requires_human_validation else "open",
                        "priority": "high",
                        "channel": "api",
                        "created_at": _now_iso(),
                        "updated_at": _now_iso(),
                    }
                )
                result["ticket_id"] = ticket_id
                result["provider_result"] = {"provider": provider or "ticket", "delivery_status": "ticket_opened"}
        if dispute_mode and (not payload.dry_run):
            result["dispute_policy"] = {
                "auto_resolution_cap_gbp": max_dispute,
                "amount_gbp": dispute_amount,
                "human_validation_required": True,
            }
            if dispute_amount <= max_dispute:
                result["retention_guidance"] = (
                    "Offer credit-first resolution, empathy, and value recap before refund path."
                )
        if payload.target == "customers":
            result["lead_support"] = {
                "lead_capture_enabled": True,
                "recommended_next_step": "Collect intent, budget, timeline, and preferred channel before handoff.",
            }
        result["feature_adoption_help"] = {
            "enabled": True,
            "message": "IRA can guide users through all platform features with role-aware recommendations.",
        }
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "action_executed",
        {
            "target": payload.target,
            "command": payload.command,
            "dry_run": payload.dry_run,
            "high_impact": payload.target in HIGH_IMPACT_TARGETS,
            "consent_reference": payload.consent_reference,
            "human_validation_required": requires_human_validation,
            "explicit_approval": payload.explicit_approval,
        },
    )
    action_confidence = 0.5
    if requires_human_validation:
        action_confidence += 0.2
    if payload.human_validation_approved and (not payload.dry_run):
        action_confidence += 0.15
    if payload.dry_run:
        action_confidence -= 0.1
    action_confidence = min(max(action_confidence, 0.0), 1.0)
    if not payload.dry_run:
        snapshot: dict[str, Any] = {
            "id": len(context_runtime.ira_action_snapshots_memory) + 1,
            "tenant_id": auth.tenant_id,
            "event_id": event["id"],
            "target": payload.target,
            "command": payload.command,
            "before_state": payload.payload.get("before_state", {}),
            "after_state": payload.payload.get("after_state", result),
            "confidence": round(action_confidence, 3),
            "rollback_enabled": payload.target not in {"admin", "security"},
            "created_at": _now_iso(),
        }
        context_runtime.ira_action_snapshots_memory.append(snapshot)
        result["action_snapshot_id"] = snapshot["id"]
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_action_executed",
        {
            "event_id": event["id"],
            "target": payload.target,
            "dry_run": payload.dry_run,
            "confidence": round(action_confidence, 3),
            "snapshot_id": result.get("action_snapshot_id"),
        },
    )
    if not payload.dry_run:
        unit_cost = 2.0 if payload.target in HIGH_IMPACT_TARGETS else 1.0
        helper_record_cost(
            context_runtime,
            auth.tenant_id,
            f"ira_action_{payload.target}",
            units=1,
            unit_cost_pence=unit_cost,
            metadata={"event_id": event["id"], "target": payload.target},
        )
    if not payload.dry_run and payload.target in HIGH_IMPACT_TARGETS:
        helper_notify_ops_email(
            context_runtime,
            tenant_id=auth.tenant_id,
            subject=f"IRA executed {payload.target} action",
            body=f"IRA executed a high-impact action on target <b>{payload.target}</b>.<br>Command: {payload.command}<br>Confidence: {round(action_confidence * 100, 1)}%<br>Consent reference: {payload.consent_reference}<br>Event ID: {event['id']}",
            priority="high",
            event_type="ira_high_impact_action",
        )
        helper_notify_ops_slack(
            context_runtime,
            tenant_id=auth.tenant_id,
            title=f"IRA High-Impact Action: {payload.target}",
            text=f"Target: `{payload.target}` | Command: `{payload.command}`\nConfidence: *{round(action_confidence * 100, 1)}%* | Event: `{event['id']}`\nConsent ref: `{payload.consent_reference}`",
            priority="high",
            event_type="ira_high_impact_action",
        )
    if not payload.dry_run:
        helper_record_performance(
            context_runtime,
            auth.tenant_id,
            f"action_{payload.target}",
            confidence=action_confidence,
            outcome="success",
            metadata={"event_id": event["id"], "target": payload.target},
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "result": result,
        "confidence": round(action_confidence, 3),
        "event_id": event["id"],
    }


def execute_ira_performance_analytics(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Performance analytics — latency, confidence trends, outcome rates per action type."""
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:performance", 120, 60)
    logs = [p for p in context_runtime.ira_performance_log_memory if p.get("tenant_id") == auth.tenant_id]
    by_type: dict[str, dict[str, Any]] = {}
    for entry in logs:
        atype = str(entry.get("action_type", "unknown"))
        if atype not in by_type:
            by_type[atype] = {"count": 0, "success": 0, "failure": 0, "total_confidence": 0.0, "total_latency_ms": 0.0}
        by_type[atype]["count"] += 1
        outcome = str(entry.get("outcome", "success"))
        if outcome == "success":
            by_type[atype]["success"] += 1
        elif outcome == "failure":
            by_type[atype]["failure"] += 1
        by_type[atype]["total_confidence"] += float(entry.get("confidence", 0.5))
        by_type[atype]["total_latency_ms"] += float(entry.get("latency_ms", 0.0))
    summary: dict[str, Any] = {}
    for atype, stats in by_type.items():
        count = stats["count"]
        summary[atype] = {
            "count": count,
            "success_rate": round(stats["success"] / count, 3) if count else 0.0,
            "failure_rate": round(stats["failure"] / count, 3) if count else 0.0,
            "avg_confidence": round(stats["total_confidence"] / count, 3) if count else 0.0,
            "avg_latency_ms": round(stats["total_latency_ms"] / count, 2) if count else 0.0,
        }
    overall_success = sum((1 for p in logs if p.get("outcome") == "success"))
    overall_confidence = sum((float(p.get("confidence", 0.5)) for p in logs))
    total = len(logs)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "total_data_points": total,
        "overall_success_rate": round(overall_success / total, 3) if total else 0.0,
        "overall_avg_confidence": round(overall_confidence / total, 3) if total else 0.0,
        "by_action_type": summary,
        "recent": sorted(logs, key=lambda p: p.get("created_at", ""), reverse=True)[:20],
    }


def execute_ira_create_ab_test(
    context_runtime: ContextRuntime, payload: IRAAbTestCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    """Create a new A/B test to compare IRA decision variants."""
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:abtest", 60, 60)
    if payload.traffic_split and len(payload.traffic_split) != len(payload.variants):
        raise HTTPException(status_code=422, detail="traffic_split length must match variants length.")
    if payload.traffic_split:
        total_split = sum(payload.traffic_split)
        if abs(total_split - 1.0) > 0.01:
            raise HTTPException(status_code=422, detail=f"traffic_split must sum to 1.0, got {round(total_split, 4)}.")
    split = (
        payload.traffic_split
        if payload.traffic_split
        else [round(1.0 / len(payload.variants), 4)] * len(payload.variants)
    )
    test: dict[str, Any] = {
        "id": len(context_runtime.ira_ab_tests_memory) + 1,
        "tenant_id": auth.tenant_id,
        "name": payload.name,
        "description": payload.description,
        "variants": payload.variants,
        "traffic_split": split,
        "metric": payload.metric,
        "target_scope": payload.target_scope,
        "status": "running",
        "results": {v: {"impressions": 0, "successes": 0, "failures": 0, "total_value": 0.0} for v in payload.variants},
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    context_runtime.ira_ab_tests_memory.append(test)
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_ab_test_created",
        {"test_id": test["id"], "name": payload.name, "variants": payload.variants},
    )
    helper_record_performance(
        context_runtime, auth.tenant_id, "ab_test_created", confidence=0.5, metadata={"test_id": test["id"]}
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "test": test}


def execute_ira_record_ab_result(
    context_runtime: ContextRuntime, payload: IRAAbTestRecordRequest, auth: AuthDep
) -> dict[str, Any]:
    """Record an outcome for a variant in a running A/B test."""
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:abtest:record", 600, 60)
    test = next(
        (
            t
            for t in context_runtime.ira_ab_tests_memory
            if t.get("id") == payload.test_id and t.get("tenant_id") == auth.tenant_id
        ),
        None,
    )
    if test is None:
        raise HTTPException(status_code=404, detail=f"A/B test {payload.test_id} not found.")
    if test.get("status") != "running":
        raise HTTPException(status_code=422, detail="A/B test is not in running state.")
    if payload.variant not in test.get("variants", []):
        raise HTTPException(
            status_code=422, detail=f"Variant '{payload.variant}' not in test variants {test['variants']}."
        )
    variant_stats = test["results"][payload.variant]
    variant_stats["impressions"] += 1
    variant_stats["total_value"] = round(variant_stats["total_value"] + payload.value, 4)
    if payload.outcome == "success":
        variant_stats["successes"] += 1
    elif payload.outcome == "failure":
        variant_stats["failures"] += 1
    test["updated_at"] = _now_iso()
    return {"status": "ok", "test_id": payload.test_id, "variant": payload.variant, "variant_stats": variant_stats}
