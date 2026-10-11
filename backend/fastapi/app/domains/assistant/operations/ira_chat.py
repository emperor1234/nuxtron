"""Assistant use cases: ira chat."""

from ..constants import AUTONOMY_DISABLED_DETAIL
from ..constants import AuthDep
from ..constants import HIGH_IMPACT_TARGETS
from ..runtime import ContextRuntime
from ..schemas import IRABatchActionsRequest
from ..schemas import IRAMessageRequest
from ..services.reasoning_support import _build_chat_reasoning_prompt
from ..services.reasoning_support import _extract_chat_provider_routing
from ..services.reasoning_support import _now_iso
from .copilot_env_template import helper_build_chat_action_plan
from .copilot_env_template import helper_chat_risk_assessment
from .copilot_env_template import helper_classify_chat_intent
from .copilot_env_template import helper_retrieve_knowledge_context
from .db_dsn import helper_append_ira_event
from .db_dsn import helper_audit
from .db_dsn import helper_connector_enabled
from .db_dsn import helper_get_or_create_control
from .db_dsn import helper_require_super_admin_for_control
from .ira_response import helper_ira_response
from .ira_response import helper_notify_ops_email
from .ira_response import helper_notify_ops_slack
from .ira_response import helper_record_cost
from .ira_response import helper_record_performance
from fastapi import HTTPException
from fastapi import Header
from typing import Annotated
from typing import Any
from typing import Literal
from typing import cast


def execute_ira_chat(context_runtime: ContextRuntime, payload: IRAMessageRequest, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:chat", 1000, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        if not bool(control.get("autonomy_enabled", True)):
            raise HTTPException(status_code=422, detail=AUTONOMY_DISABLED_DETAIL)
        if not helper_connector_enabled(context_runtime, auth.tenant_id, payload.channel):
            raise HTTPException(status_code=422, detail=f"IRA connector for channel {payload.channel} is disabled.")
        session: dict[str, Any] = {
            "id": len(context_runtime.ira_sessions_memory) + 1,
            "tenant_id": auth.tenant_id,
            "role": payload.role,
            "channel": payload.channel,
            "user_message": payload.message,
            "context": payload.context,
            "created_at": _now_iso(),
        }
        context_runtime.ira_sessions_memory.append(session)
    context_runtime.memory_system.append_short_term_message(
        tenant_id=auth.tenant_id,
        role=payload.role,
        channel=payload.channel,
        content=payload.message,
        context=payload.context,
    )
    knowledge_hits = helper_retrieve_knowledge_context(context_runtime, auth.tenant_id, payload.message, top_k=3)
    recent_history = context_runtime.memory_system.get_short_term_messages(auth.tenant_id, limit=6)
    intent, domain, intent_confidence = helper_classify_chat_intent(
        message=payload.message, recent_history=recent_history
    )
    risk = helper_chat_risk_assessment(payload.message)
    action_plan = helper_build_chat_action_plan(intent=intent, domain=domain, risk=risk)
    provider_routing = _extract_chat_provider_routing(payload.context)
    requested_provider = str(provider_routing["requested_provider"])
    selected_brain_provider = cast(str | None, provider_routing["brain_provider"])
    provider_catalog = cast(dict[str, Any], context_runtime.ai_brain.capabilities().get("providers", {}))
    provider_info = cast(dict[str, Any], provider_catalog.get(selected_brain_provider or "", {}) or {})
    provider_requested = requested_provider
    provider_used = "internal_rule_engine"
    provider_model = "rule_based"
    provider_status = "internal_default" if requested_provider == "auto" else "internal_forced"
    provider_reasoning = "IRA internal guarded response path"
    if selected_brain_provider and bool(provider_info.get("configured", False)):
        reasoning = context_runtime.ai_brain.reason(
            prompt=_build_chat_reasoning_prompt(
                role=payload.role,
                channel=payload.channel,
                message=payload.message,
                intent=intent,
                domain=domain,
                risk=risk,
                action_plan=action_plan,
                knowledge_hits=knowledge_hits,
                recent_history=recent_history,
            ),
            provider=cast(
                Literal["auto", "openai", "anthropic", "google_deepmind", "deepseek", "llama", "mistral"],
                selected_brain_provider,
            ),
            tools=[],
        )
        reasoning_payload = cast(dict[str, Any], reasoning.get("reasoning", {}) or {})
        output_text = str(reasoning_payload.get("output_text", "")).strip()
        provider_model = str(reasoning_payload.get("model", "")).strip() or provider_model
        if reasoning.get("status") == "ok" and output_text:
            response_text = output_text
            confidence = min(1.0, max(intent_confidence, 0.78))
            provider_used = str(reasoning_payload.get("provider", selected_brain_provider) or selected_brain_provider)
            provider_status = "external_ok"
            provider_reasoning = "IRA external reasoning path"
        else:
            response_text, confidence = helper_ira_response(
                payload.role,
                payload.channel,
                payload.message,
                knowledge_hits=knowledge_hits,
                recent_history=recent_history,
            )
            provider_status = "fell_back_to_internal"
            provider_reasoning = "Requested external provider returned no usable response"
    else:
        response_text, confidence = helper_ira_response(
            payload.role, payload.channel, payload.message, knowledge_hits=knowledge_hits, recent_history=recent_history
        )
        if selected_brain_provider:
            provider_status = "requested_provider_not_configured"
            provider_model = str(provider_info.get("model", "")).strip() or provider_model
            provider_reasoning = "Requested external provider is not configured; using internal route"
        elif requested_provider not in {"auto", "internal"}:
            provider_status = "unsupported_provider_preference"
            provider_reasoning = "Unsupported provider preference; using internal route"
    confidence = min(1.0, max(confidence, intent_confidence))
    context_runtime.memory_system.append_short_term_message(
        tenant_id=auth.tenant_id,
        role="assistant",
        channel=payload.channel,
        content=response_text,
        context={
            "knowledge_hit_count": len(knowledge_hits),
            "confidence": confidence,
            "intent": intent,
            "domain": domain,
            "provider_requested": provider_requested,
            "provider_used": provider_used,
            "provider_status": provider_status,
        },
    )
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "chat_handled",
        {
            "role": payload.role,
            "channel": payload.channel,
            "session_id": session["id"],
            "knowledge_hit_count": len(knowledge_hits),
            "confidence": round(confidence, 3),
            "intent": intent,
            "domain": domain,
            "risk_level": risk.get("risk_level", "low"),
            "knowledge_documents": [str(hit.get("document_id", "")) for hit in knowledge_hits],
            "provider_requested": provider_requested,
            "provider_used": provider_used,
            "provider_status": provider_status,
        },
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_chat_handled",
        {"session_id": session["id"], "event_id": event["id"], "confidence": round(confidence, 3)},
    )
    helper_record_cost(
        context_runtime,
        auth.tenant_id,
        "ira_chat",
        units=1,
        unit_cost_pence=0.5,
        metadata={
            "session_id": session["id"],
            "confidence": round(confidence, 3),
            "provider_requested": provider_requested,
            "provider_used": provider_used,
            "provider_status": provider_status,
        },
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "ira": {
            "name": "IRA",
            "response": response_text,
            "confidence": round(confidence, 3),
            "session_id": session["id"],
            "knowledge_hits": knowledge_hits,
            "intent": intent,
            "domain": domain,
            "risk_assessment": risk,
            "action_plan": action_plan.model_dump(),
            "provider_requested": provider_requested,
            "provider_used": provider_used,
            "provider_model": provider_model,
            "provider_status": provider_status,
            "provider_reasoning": provider_reasoning,
        },
    }


def execute_ira_monitor(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Dashboard endpoint: Real-time IRA activity summary"""
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:monitor", 300, 60)
    tenant_events = [e for e in context_runtime.ira_events_memory if e.get("tenant_id") == auth.tenant_id]
    tenant_sessions = [s for s in context_runtime.ira_sessions_memory if s.get("tenant_id") == auth.tenant_id]
    tenant_snapshots = [
        sn for sn in context_runtime.ira_action_snapshots_memory if sn.get("tenant_id") == auth.tenant_id
    ]
    tenant_costs = [c for c in context_runtime.ira_cost_ledger_memory if c.get("tenant_id") == auth.tenant_id]
    total_chats = len([e for e in tenant_events if e.get("event_type") == "chat_handled"])
    total_actions = len(
        [e for e in tenant_events if e.get("event_type") in ("action_executed", "batch_action_executed")]
    )
    failed_actions = len(
        [e for e in tenant_events if e.get("event_type") == "action_executed" and e.get("payload", {}).get("dry_run")]
    )
    confidences = [float(sn.get("confidence", 0.5)) for sn in tenant_snapshots if sn.get("confidence")]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    total_cost_pence = sum((float(c.get("total_cost_pence", 0)) for c in tenant_costs))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "recent_events": sorted(tenant_events, key=lambda e: e.get("created_at", ""), reverse=True)[:20],
        "recent_sessions": sorted(tenant_sessions, key=lambda s: s.get("created_at", ""), reverse=True)[:20],
        "recent_snapshots": sorted(tenant_snapshots, key=lambda sn: sn.get("created_at", ""), reverse=True)[:20],
        "stats": {
            "avg_confidence": round(avg_confidence, 3),
            "total_chats": total_chats,
            "total_actions": total_actions,
            "failed_actions": failed_actions,
            "total_cost_pence": round(total_cost_pence, 4),
            "total_cost_gbp": round(total_cost_pence / 100, 6),
        },
    }


def execute_ira_batch_actions(
    context_runtime: ContextRuntime,
    payload: IRABatchActionsRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    """Execute up to 100 IRA actions in a single batch request."""
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:batch", 20, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        helper_require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail="IRA batch actions are restricted to super admin sessions.",
        )
        if not bool(control.get("autonomy_enabled", True)):
            raise HTTPException(status_code=422, detail=AUTONOMY_DISABLED_DETAIL)
    results: list[dict[str, Any]] = []
    total_cost_pence = 0.0
    high_impact_count = 0
    for idx, item in enumerate(payload.actions):
        item_dry_run = payload.dry_run or item.dry_run
        is_high_impact = item.target in HIGH_IMPACT_TARGETS
        if is_high_impact and (not payload.human_validation_approved):
            results.append(
                {
                    "index": idx,
                    "target": item.target,
                    "command": item.command,
                    "status": "skipped",
                    "reason": "High-impact target requires human_validation_approved=true",
                }
            )
            continue
        item_confidence = 0.6
        if payload.human_validation_approved:
            item_confidence += 0.15
        if payload.risk_analysis_approved:
            item_confidence += 0.1
        if item_dry_run:
            item_confidence -= 0.1
        item_confidence = min(max(item_confidence, 0.0), 1.0)
        event = helper_append_ira_event(
            context_runtime,
            auth.tenant_id,
            "batch_action_executed",
            {
                "batch_index": idx,
                "target": item.target,
                "command": item.command,
                "dry_run": item_dry_run,
                "confidence": round(item_confidence, 3),
                "consent_reference": payload.consent_reference,
            },
        )
        if not item_dry_run:
            unit_cost = 2.0 if is_high_impact else 1.0
            total_cost_pence += unit_cost
            helper_record_cost(
                context_runtime,
                auth.tenant_id,
                f"ira_batch_{item.target}",
                units=1,
                unit_cost_pence=unit_cost,
                metadata={"batch_index": idx},
            )
            if is_high_impact:
                high_impact_count += 1
        if not item_dry_run:
            snap: dict[str, Any] = {
                "id": len(context_runtime.ira_action_snapshots_memory) + 1,
                "tenant_id": auth.tenant_id,
                "event_id": event["id"],
                "target": item.target,
                "command": item.command,
                "before_state": item.payload.get("before_state", {}),
                "after_state": {},
                "confidence": round(item_confidence, 3),
                "rollback_enabled": item.target not in {"admin", "security"},
                "created_at": _now_iso(),
            }
            context_runtime.ira_action_snapshots_memory.append(snap)
        results.append(
            {
                "index": idx,
                "target": item.target,
                "command": item.command,
                "status": "dry_run" if item_dry_run else "executed",
                "confidence": round(item_confidence, 3),
                "event_id": event["id"],
            }
        )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_batch_executed",
        {
            "total": len(payload.actions),
            "executed": sum((1 for r in results if r.get("status") == "executed")),
            "skipped": sum((1 for r in results if r.get("status") == "skipped")),
            "total_cost_pence": round(total_cost_pence, 4),
        },
    )
    if high_impact_count > 0:
        helper_notify_ops_email(
            context_runtime,
            tenant_id=auth.tenant_id,
            subject=f"IRA batch executed {high_impact_count} high-impact actions",
            body=f"IRA batch completed with <b>{high_impact_count} high-impact actions</b>.<br>Total actions: {len(payload.actions)}<br>Total estimated cost: {round(total_cost_pence / 100, 4)} GBP<br>Consent reference: {payload.consent_reference}",
            priority="high",
            event_type="ira_batch_high_impact",
        )
        helper_notify_ops_slack(
            context_runtime,
            tenant_id=auth.tenant_id,
            title=f"IRA Batch: {high_impact_count} High-Impact Actions",
            text=f"Batch completed: *{len(payload.actions)} total* | *{high_impact_count} high-impact*\nCost: *£{round(total_cost_pence / 100, 4)}* | Consent: `{payload.consent_reference}`",
            priority="high",
            event_type="ira_batch_high_impact",
        )
    helper_record_performance(
        context_runtime,
        auth.tenant_id,
        "batch_action",
        confidence=0.7,
        outcome="success",
        metadata={
            "total": len(payload.actions),
            "executed": sum((1 for r in results if r.get("status") == "executed")),
        },
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "total": len(payload.actions),
        "executed": sum((1 for r in results if r.get("status") == "executed")),
        "skipped": sum((1 for r in results if r.get("status") == "skipped")),
        "total_cost_pence": round(total_cost_pence, 4),
        "total_cost_gbp": round(total_cost_pence / 100, 6),
        "results": results,
    }
