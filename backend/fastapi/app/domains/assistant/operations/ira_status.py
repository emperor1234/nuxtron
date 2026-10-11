"""Assistant use cases: ira status."""

from ..constants import AuthDep
from ..constants import CONNECTOR_CHANNELS
from ..constants import DEFAULT_BLOCKED_ACTIONS
from ..constants import IRA_PLAYBOOK_DECISION_TREE
from ..runtime import ContextRuntime
from ..schemas import IRAFrontierEnvTemplateApplyRequest
from ..schemas import IRAFrontierPlanRequest
from ..services.reasoning_support import _now_iso
from .copilot_env_template import helper_copilot_env_template
from .copilot_env_template import helper_copilot_health_check
from .db_dsn import helper_append_ira_event
from .db_dsn import helper_audit
from .db_dsn import helper_get_or_create_connector
from .db_dsn import helper_get_or_create_control
from .db_dsn import helper_tenant_revenue_snapshot
from .db_dsn import helper_validate_env_target_filename
from .frontier_stack_catalog import helper_frontier_stack_catalog
from .frontier_stack_catalog import helper_merge_env_file_non_destructive
from .frontier_stack_catalog import helper_tenant_suspicious_signal
from .ml_capabilities import helper_copilot_catalog
from .ml_capabilities import helper_copilot_readiness
from .ml_capabilities import helper_frontier_env_template
from .ml_capabilities import helper_frontier_readiness_summary
from .ml_capabilities import helper_frontier_recommended_stack
from .ml_capabilities import helper_ml_summary
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any
from typing import cast
import os
import uuid


def execute_ira_status(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:status", 120, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id).copy()
        recent_events = [
            item.copy() for item in context_runtime.ira_events_memory if item.get("tenant_id") == auth.tenant_id
        ][-20:]
        connectors = [
            helper_get_or_create_connector(context_runtime, auth.tenant_id, channel).copy()
            for channel in CONNECTOR_CHANNELS
        ]
    brain_capabilities = cast(dict[str, Any], context_runtime.ai_brain.capabilities())
    brain_providers = cast(dict[str, Any], brain_capabilities.get("providers", {}) or {})

    def _provider_readiness(key: str, fallback_label: str, fallback_model: str) -> dict[str, Any]:
        provider = cast(dict[str, Any], brain_providers.get(key, {}) or {})
        configured = bool(provider.get("configured", False))
        reason = str(
            provider.get("reason")
            or provider.get("status_reason")
            or provider.get("unavailable_reason")
            or provider.get("error")
            or provider.get("error_detail")
            or ""
        ).strip()
        if not reason:
            reason = "Configured and available" if configured else "Missing provider credentials/configuration"
        return {
            "key": key,
            "label": str(provider.get("label", fallback_label) or fallback_label),
            "configured": configured,
            "model": str(provider.get("model", fallback_model) or fallback_model),
            "route": key,
            "reason": reason,
        }

    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "ira_name": "IRA",
        "always_on": True,
        "autonomy": control,
        "connectors": connectors,
        "finance_health": helper_tenant_revenue_snapshot(context_runtime, auth.tenant_id),
        "risk_signal": helper_tenant_suspicious_signal(context_runtime, auth.tenant_id),
        "recent_events": recent_events,
        "provider_readiness": {
            "internal": {
                "key": "internal",
                "label": "Internal IRA",
                "configured": True,
                "model": "rule_based",
                "route": "internal",
                "reason": "Built-in guarded fallback route",
            },
            "openai": _provider_readiness("openai", "OpenAI", "gpt-4.1-mini"),
            "anthropic": _provider_readiness("anthropic", "Anthropic", "claude-3-5-sonnet-latest"),
        },
        "capabilities": {
            "customer_support": True,
            "admin_assist": True,
            "email_handling": True,
            "chat_handling": True,
            "credit_monitoring": True,
            "payment_monitoring": True,
            "damage_containment": True,
            "provider_connectors": True,
            "feature_adoption_guidance": True,
            "lead_conversion_assist": True,
            "human_validation_gate": True,
            "rbac_enforced": True,
            "abac_enforced": True,
            "provider_routing": True,
            "training_layer": True,
            "rag_retrieval": True,
            "fine_tuning_orchestration": True,
        },
        "ml_training_layer": helper_ml_summary(context_runtime, auth.tenant_id),
        "policy": {
            "requires_super_admin_for_autonomy": bool(control.get("require_super_admin", True)),
            "dashboard_scope": "super_admin_dashboard",
            "compliance_requires_human_validation": True,
            "bulk_messages_require_human_validation": True,
            "tickets_require_human_validation": True,
            "all_disputes_require_human_validation": True,
            "strict_policy_lock": bool(control.get("strict_policy_lock", True)),
            "max_dispute_auto_resolution_gbp": float(control.get("max_dispute_auto_resolution_gbp", 50.0)),
            "blocked_autonomous_actions": list(DEFAULT_BLOCKED_ACTIONS),
        },
    }


def execute_ira_playbook(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:playbook", 120, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id).copy()
        sessions_count = len(
            [item for item in context_runtime.ira_sessions_memory if item.get("tenant_id") == auth.tenant_id]
        )
        events_count = len(
            [item for item in context_runtime.ira_events_memory if item.get("tenant_id") == auth.tenant_id]
        )
        connectors = [
            helper_get_or_create_connector(context_runtime, auth.tenant_id, channel).copy()
            for channel in CONNECTOR_CHANNELS
        ]
    finance = helper_tenant_revenue_snapshot(context_runtime, auth.tenant_id)
    risk_signal = helper_tenant_suspicious_signal(context_runtime, auth.tenant_id)
    min_margin = float(control.get("min_profit_margin_pct", 70.0))
    current_margin = float(finance.get("profit_margin_pct", 0.0))
    suspicious_score = float(risk_signal.get("score", 0.0))
    milestones: list[dict[str, Any]] = [
        {
            "key": "first_session",
            "label": "First IRA session",
            "target": "Week 1",
            "achieved": sessions_count >= 1,
            "detail": f"Sessions observed: {sessions_count}",
        },
        {
            "key": "first_event",
            "label": "First automation event",
            "target": "Week 1",
            "achieved": events_count >= 1,
            "detail": f"Events observed: {events_count}",
        },
        {
            "key": "autonomy_enabled",
            "label": "Autonomy enabled",
            "target": "Week 2",
            "achieved": bool(control.get("autonomy_enabled", True)),
            "detail": f"Autonomy state: {('enabled' if bool(control.get('autonomy_enabled', True)) else 'disabled')}",
        },
        {
            "key": "connectors_online",
            "label": "Core connectors online",
            "target": "Week 2",
            "achieved": all(
                (
                    bool(item.get("enabled", False))
                    for item in connectors
                    if str(item.get("channel", "")) in {"chat", "email", "ticket"}
                )
            ),
            "detail": "Chat, email, and ticket connector readiness",
        },
        {
            "key": "profit_guard",
            "label": "Profit margin target met",
            "target": "Week 4",
            "achieved": current_margin >= min_margin,
            "detail": f"Margin {current_margin:.2f}% vs target {min_margin:.2f}%",
        },
        {
            "key": "risk_guard",
            "label": "Risk signal within threshold",
            "target": "Week 4",
            "achieved": suspicious_score <= float(control.get("suspicious_signal_threshold", 0.75)),
            "detail": f"Risk score {suspicious_score:.3f} vs threshold {float(control.get('suspicious_signal_threshold', 0.75)):.3f}",
        },
    ]
    achieved_count = len([item for item in milestones if bool(item.get("achieved", False))])
    total_count = len(milestones)
    completion_pct = 0.0 if total_count <= 0 else round(achieved_count / total_count * 100.0, 2)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "generated_at": _now_iso(),
        "completion_chart": {"achieved": achieved_count, "total": total_count, "percentage": completion_pct},
        "milestones": milestones,
        "decision_tree": list(IRA_PLAYBOOK_DECISION_TREE),
    }


def execute_ira_frontier_plan(
    context_runtime: ContextRuntime, payload: IRAFrontierPlanRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:frontier:plan", 60, 60)
    stack = helper_frontier_recommended_stack(payload)
    readiness = helper_frontier_readiness_summary(helper_frontier_stack_catalog())
    phases: list[dict[str, Any]] = [
        {
            "phase": 1,
            "name": "Reliability Foundation",
            "deliverables": ["guardrails", "approval gates", "budget controls", "failure telemetry"],
        },
        {
            "phase": 2,
            "name": "Memory + RAG Intelligence",
            "deliverables": ["vector_memory", "graph_memory", "hybrid_retrieval", "context_compression"],
        },
        {
            "phase": 3,
            "name": "Multi-Agent Workforce",
            "deliverables": ["planner_executor_critic_roles", "durable_workflow_state", "tool_retry_policy"],
        },
        {
            "phase": 4,
            "name": "Multimodal + Enterprise Ops",
            "deliverables": ["audio_video_ui_analysis", "slack_notion_salesforce_workspace_actions"],
        },
    ]
    execution_jobs: list[dict[str, Any]] = []
    if payload.create_execution_tasks:
        for phase in phases:
            phase_number = int(phase.get("phase", 0) or 0)
            job: dict[str, Any] = {
                "id": len(context_runtime.ira_ml_jobs_memory) + 1,
                "tenant_id": auth.tenant_id,
                "job_type": "frontier_execution_phase",
                "name": f"frontier_phase_{phase_number}",
                "objective": payload.objective,
                "framework": ",".join(cast(list[str], stack.get("agents", []))),
                "priority": payload.priority,
                "phase": phase_number,
                "phase_name": str(phase.get("name", "")),
                "deliverables": phase.get("deliverables", []),
                "status": "planned",
                "dry_run": True,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }
            context_runtime.ira_ml_jobs_memory.append(job)
            execution_jobs.append(job)
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "frontier_plan_generated",
        {
            "priority": payload.priority,
            "objective_preview": payload.objective[:140],
            "open_source_only": payload.include_free_open_source_only,
            "create_execution_tasks": payload.create_execution_tasks,
        },
    )
    helper_audit(context_runtime, auth.tenant_id, "ira_frontier_plan_generated", {"event_id": event["id"]})
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "objective": payload.objective,
        "priority": payload.priority,
        "recommended_stack": stack,
        "current_readiness": readiness,
        "implementation_phases": phases,
        "execution_jobs": execution_jobs,
        "event_id": event["id"],
    }


def execute_ira_frontier_env_template_apply_draft(
    context_runtime: ContextRuntime, payload: IRAFrontierEnvTemplateApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:frontier:env-template:apply", 30, 60)
    is_valid_target, validated_target_or_error = helper_validate_env_target_filename(payload.target_file)
    if not is_valid_target:
        raise HTTPException(status_code=422, detail=validated_target_or_error)
    target_file = validated_target_or_error
    stack = helper_frontier_stack_catalog()
    readiness = helper_frontier_readiness_summary(stack)
    env_template = helper_frontier_env_template(readiness)
    rendered_template = str(env_template.get("template", "")).strip()
    if not rendered_template:
        raise HTTPException(status_code=422, detail="Unable to render environment template from readiness state.")
    generated_lines: list[str] = []
    for entry in cast(list[Any], env_template.get("required_env", [])):
        if isinstance(entry, str) and entry.strip():
            generated_lines.append(entry.strip())
    for entry in cast(list[Any], env_template.get("recommended_defaults", [])):
        if isinstance(entry, str) and entry.strip():
            generated_lines.append(entry.strip())
    mode = payload.mode
    file_content = f"# Generated by IRA Frontier Stack\n# tenant: {auth.tenant_id}\n# generated_at: {_now_iso()}\n\n{rendered_template}\n"
    target_path = os.path.abspath(target_file)
    should_merge_non_destructive = mode in {"merge_non_destructive", "merge_and_backup"}
    should_create_backup = mode == "merge_and_backup"
    existing_content = ""
    if should_merge_non_destructive and os.path.exists(target_path):
        try:
            with open(target_path, encoding="utf-8") as handle:
                existing_content = handle.read()
        except Exception as ex:
            raise HTTPException(status_code=500, detail=f"Failed reading existing env file: {ex}") from ex
    merge_stats: dict[str, int] = {"updated_existing_empty": 0, "kept_existing_non_empty": 0, "appended_missing": 0}
    if should_merge_non_destructive:
        file_content, merge_stats = helper_merge_env_file_non_destructive(existing_content, generated_lines)
    backup_path = ""
    if should_create_backup and os.path.exists(target_path):
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = f"{target_path}.bak-{timestamp}-{uuid.uuid4().hex[:8]}"
        try:
            with open(backup_path, "w", encoding="utf-8", newline="\n") as backup_handle:
                backup_handle.write(existing_content)
        except Exception as ex:
            raise HTTPException(status_code=500, detail=f"Failed writing backup env file: {ex}") from ex
    try:
        with open(target_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(file_content)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Failed writing draft env file: {ex}") from ex
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "frontier_env_template_draft_applied",
        {"target_file": target_file, "readiness_score": readiness.get("score_pct", 0), "mode": mode},
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_frontier_env_template_draft_applied",
        {"event_id": event["id"], "target_file": target_file},
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "target_file": target_file,
        "target_path": target_path,
        "mode": mode,
        "backup_path": backup_path,
        "bytes_written": len(file_content.encode("utf-8")),
        "merge_stats": merge_stats,
        "readiness": readiness,
        "event_id": event["id"],
    }


def execute_ira_copilot_catalog(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:copilot:catalog", 120, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "copilot": helper_copilot_catalog(),
        "readiness": helper_copilot_readiness(),
        "env_template": helper_copilot_env_template(),
    }


def execute_ira_copilot_health(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:copilot:health", 120, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "health": helper_copilot_health_check(),
        "readiness": helper_copilot_readiness(),
    }


def execute_ira_copilot_env_template(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:copilot:env-template", 120, 60)
    return {"status": "ok", "tenant_id": auth.tenant_id, "env_template": helper_copilot_env_template()}
