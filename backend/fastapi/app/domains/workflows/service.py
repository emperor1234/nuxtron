"""Workflow service implementation with explicit dependencies."""

from .runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from typing import Any


def get_policy(runtime: WorkflowRuntime, workflow_id: int, tenant_id: str) -> dict[str, Any] | None:
    with runtime.lock:
        return next(
            (
                p
                for p in runtime.approval_policies
                if p.get("workflow_id") == workflow_id and p.get("tenant_id") == tenant_id and p.get("enabled")
            ),
            None,
        )


def append_audit(runtime: WorkflowRuntime, tenant_id: str, action: str, ref_id: int | None = None) -> None:
    with runtime.lock:
        runtime.audit_log.append(
            {
                "id": len(runtime.audit_log) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "ref_id": ref_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "workflows-router",
            }
        )


def simulate_execution(
    runtime: WorkflowRuntime, workflow: dict[str, Any], contact_id: str, contact_email: str, tenant_id: str
) -> dict[str, Any]:
    """Simulate executing a workflow — logs each step."""
    steps = workflow.get("steps", [])
    step_logs = []
    for step in steps:
        action_type = str(step.get("action_type", "unknown"))
        log = {
            "id": len(runtime.workflow_step_logs) + 1,
            "tenant_id": tenant_id,
            "step_id": step.get("step_id"),
            "action_type": action_type,
            "contact_id": contact_id,
            "status": "completed",
            "result": f"Action {action_type} executed for {contact_email or contact_id}",
            "executed_at": datetime.now(UTC).isoformat(),
        }
        step_logs.append(log)
        with runtime.lock:
            runtime.workflow_step_logs.append(log)
    return {"steps_executed": len(step_logs), "step_logs": step_logs}


def workflow_platform_readiness_payload(runtime: WorkflowRuntime, tenant_id: str) -> dict[str, Any]:
    with runtime.lock:
        tenant_workflows = [w for w in runtime.workflows if w.get("tenant_id") == tenant_id]
        tenant_templates = [t for t in runtime.workflow_templates if t.get("tenant_id") == tenant_id]
        tenant_connectors = [c for c in runtime.connectors if c.get("tenant_id") == tenant_id]
        tenant_executions = [e for e in runtime.workflow_executions if e.get("tenant_id") == tenant_id]
        tenant_webhook_events = [e for e in runtime.workflow_webhook_events if e.get("tenant_id") == tenant_id]
    matrix = [
        {"feature": "workflow_crud", "implemented": True},
        {"feature": "graph_validation", "implemented": True},
        {"feature": "template_library", "implemented": True},
        {"feature": "template_instantiation", "implemented": True},
        {"feature": "manual_enrollment", "implemented": True},
        {"feature": "webhook_trigger_ingestion", "implemented": True},
        {"feature": "execution_history", "implemented": True},
        {"feature": "approval_gates", "implemented": True},
        {"feature": "connector_reliability", "implemented": True},
        {"feature": "incident_escalation", "implemented": True},
        {"feature": "postmortem_governance", "implemented": True},
    ]
    implemented_count = sum((1 for item in matrix if bool(item.get("implemented"))))
    total_count = len(matrix)
    completion_pct = round(implemented_count / total_count * 100, 1) if total_count else 0.0
    return {
        "status": "ok",
        "completion_pct": completion_pct,
        "implemented_count": implemented_count,
        "total_count": total_count,
        "matrix": matrix,
        "tenant_stats": {
            "workflows": len(tenant_workflows),
            "templates": len(tenant_templates),
            "connectors": len(tenant_connectors),
            "executions": len(tenant_executions),
            "webhook_events": len(tenant_webhook_events),
        },
        "vendors": [
            {"name": "OpenAI", "usage": "LLM reasoning and generation", "integration": "AI gateway / provider SDK"},
            {"name": "Anthropic", "usage": "LLM reasoning fallback", "integration": "AI gateway / provider SDK"},
            {"name": "Slack", "usage": "Notifications and human approvals", "integration": "Slack Web API"},
            {
                "name": "Google Analytics",
                "usage": "Attribution and analytics",
                "integration": "Google Analytics Data API",
            },
            {"name": "Google Search Console", "usage": "SEO signals", "integration": "Search Console API"},
            {"name": "X (Twitter)", "usage": "Social publishing", "integration": "X API v2"},
            {"name": "Meta Graph", "usage": "Facebook/Instagram/Threads publishing", "integration": "Graph API"},
            {"name": "TikTok", "usage": "Video publishing", "integration": "TikTok API"},
            {"name": "YouTube", "usage": "Video distribution", "integration": "YouTube Data API v3"},
            {"name": "Prometheus + Grafana", "usage": "Metrics and dashboards", "integration": "Observability stack"},
        ],
    }
