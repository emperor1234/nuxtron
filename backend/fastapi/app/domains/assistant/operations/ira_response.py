"""Assistant use cases: ira response."""

from .... import ira_connector_integration as port_dispatch_via_ira_connector
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..services.reasoning_support import _now_iso
from .db_dsn import helper_probe_crm_connectors
from .frontier_stack_catalog import helper_frontier_stack_catalog
from .ml_capabilities import helper_frontier_env_template
from .ml_capabilities import helper_frontier_readiness_summary
from ...identity.secure_egress import outbound_request
from ...identity.secure_egress import resolve_outbound_target
from typing import Any
import httpx
import os


def helper_ira_response(
    role: str,
    channel: str,
    message: str,
    *,
    knowledge_hits: list[dict[str, Any]] | None = None,
    recent_history: list[dict[str, Any]] | None = None,
) -> tuple[str, float]:
    """Return (response_text, confidence: 0.0-1.0)"""
    role_prefix = {"customer": "IRA Customer Care", "admin": "IRA Platform Ops", "operator": "IRA Control Tower"}.get(
        role, "IRA"
    )
    channel_hint = {
        "chat": "chat response",
        "email": "email draft",
        "ticket": "ticket resolution update",
        "webhook": "automation callback response",
    }.get(channel, "response")
    message_text = message.strip()
    lower_message = message_text.lower()

    def _contains(*tokens: str) -> bool:
        return any((token in lower_message for token in tokens))

    confidence = 0.4
    _short_confirms = {
        "yes",
        "no",
        "ok",
        "okay",
        "sure",
        "do it",
        "go",
        "proceed",
        "confirm",
        "start",
        "run",
        "execute",
        "do",
        "do this",
        "sounds good",
        "great",
        "perfect",
        "please",
    }
    is_short_confirm = lower_message in _short_confirms or len(message_text.split()) <= 3
    if is_short_confirm and recent_history:
        history_text = " ".join((str(m.get("content", "")) for m in recent_history[-6:])).lower()

        def _hist_contains(*tokens: str) -> bool:
            return any((token in history_text for token in tokens))

        if _hist_contains("seo", "ranking", "keyword", "backlink", "technical audit", "core web"):
            lower_message = lower_message + " seo"
            confidence += 0.2
        elif _hist_contains("ads", "campaign", "cac", "roas", "creative", "paid"):
            lower_message = lower_message + " ads"
            confidence += 0.2
        elif _hist_contains("social", "instagram", "tiktok", "linkedin", "content calendar", "post"):
            lower_message = lower_message + " social"
            confidence += 0.2
        elif _hist_contains("billing", "invoice", "payment", "refund", "dispute", "credit"):
            lower_message = lower_message + " billing"
            confidence += 0.2
        elif _hist_contains("security", "breach", "siem", "threat", "incident", "risk"):
            lower_message = lower_message + " security"
            confidence += 0.2
        elif _hist_contains("support", "customer", "onboarding", "help", "issue", "ticket"):
            lower_message = lower_message + " support"
            confidence += 0.2
    if _contains("seo", "ranking", "keyword", "backlink", "core web vitals", "technical audit"):
        task_brief = "SEO workflow selected: I can run technical crawl checks, cluster target keywords, and queue a backlink + internal-linking plan with weekly rank delta tracking."
        confidence += 0.1
    elif _contains("ads", "campaign", "cac", "roas", "creative", "paid"):
        task_brief = "Ads workflow selected: I can propose creatives, launch audience split tests, and rebalance budget toward best CAC/ROAS performers on a 48-hour cadence."
        confidence += 0.1
    elif _contains("social", "content calendar", "post", "instagram", "linkedin", "tiktok", "youtube"):
        task_brief = "Social workflow selected: I can generate a 30-day content calendar, create multi-format variants, and schedule per-platform peak windows."
        confidence += 0.1
    elif _contains("billing", "invoice", "payment", "refund", "dispute", "credit"):
        task_brief = "Billing workflow selected: I can investigate ledger and invoice context, then prepare a compliant action path with approvals for refund/dispute steps."
        confidence += 0.1
    elif _contains("security", "incident", "breach", "siem", "threat", "risk"):
        task_brief = "Security workflow selected: I can assemble risk signals, correlate events, and generate a guarded incident-response sequence with audit checkpoints."
        confidence += 0.1
    elif _contains("support", "customer", "onboarding", "help", "issue", "ticket"):
        task_brief = "Support workflow selected: I can draft a customer-safe resolution plan, route handoffs to the right queue, and keep full conversation audit trace."
        confidence += 0.1
    else:
        task_brief = "General workflow selected: I can break this into safe executable steps, request approvals where required, and keep full operational audit logging."
    base_response = f'{role_prefix}: {channel_hint} ready for "{message_text[:220]}". {task_brief}'
    if knowledge_hits:
        confidence += min(len(knowledge_hits) * 0.15, 0.3)
        grounded_points = [
            f"{str(hit.get('title', 'Knowledge'))}: {str(hit.get('content', ''))[:160]}" for hit in knowledge_hits[:2]
        ]
        response_text = f"{base_response} Grounded knowledge highlights: {' '.join(grounded_points)}"
    else:
        response_text = base_response
    confidence = min(confidence, 1.0)
    return (response_text, confidence)


def helper_deliver_slack(
    context_runtime: ContextRuntime, *, tenant_id: str, connector: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    """Send Slack message via configured connector using integration layer."""
    text = (
        str(payload.get("message", payload.get("body", payload.get("subject", "IRA action")))).strip() or "IRA action"
    )
    title = str(payload.get("title", "")).strip()
    result = port_dispatch_via_ira_connector.dispatch_via_ira_connector(
        channel="slack", ira_connector=connector, message=text, title=title
    )
    if result["delivery_status"] in ("queued", "failed"):
        queued: dict[str, Any] = {
            "id": len(context_runtime.slack_messages_memory) + 1,
            "tenant_id": tenant_id,
            "provider": result.get("provider", "unknown"),
            "channel": result.get("channel", "#general"),
            "text_preview": text[:120],
            "status": "queued",
            "created_at": _now_iso(),
        }
        context_runtime.slack_messages_memory.append(queued)
        return {**result, "message_id": queued["id"]}
    return result


def helper_deliver_whatsapp(
    context_runtime: ContextRuntime, *, tenant_id: str, connector: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    """Send WhatsApp message via Twilio connector using integration layer."""
    body = (
        str(payload.get("message", payload.get("body", payload.get("subject", "IRA customer support update")))).strip()
        or "IRA customer support update"
    )
    recipient = str(payload.get("to", payload.get("recipient", ""))).strip()
    result = port_dispatch_via_ira_connector.dispatch_via_ira_connector(
        channel="whatsapp", ira_connector=connector, recipient=recipient, body=body
    )
    if result["delivery_status"] in ("queued", "failed"):
        queued: dict[str, Any] = {
            "id": len(context_runtime.twilio_messages_memory) + 1,
            "tenant_id": tenant_id,
            "provider": result.get("provider", "unknown"),
            "to": recipient,
            "body": body,
            "status": "queued",
            "created_at": _now_iso(),
        }
        context_runtime.twilio_messages_memory.append(queued)
        return {**result, "message_id": queued["id"]}
    return result


def helper_record_cost(
    context_runtime: ContextRuntime,
    tenant_id: str,
    action_type: str,
    units: int = 1,
    unit_cost_pence: float = 0.5,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record cost per IRA decision/action for cost tracking."""
    total_cost_pence = round(units * unit_cost_pence, 4)
    entry: dict[str, Any] = {
        "id": len(context_runtime.ira_cost_ledger_memory) + 1,
        "tenant_id": tenant_id,
        "action_type": action_type,
        "units": units,
        "unit_cost_pence": unit_cost_pence,
        "total_cost_pence": total_cost_pence,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }
    context_runtime.ira_cost_ledger_memory.append(entry)
    return entry


def helper_notify_ops_email(
    context_runtime: ContextRuntime,
    *,
    tenant_id: str,
    subject: str,
    body: str,
    priority: str = "normal",
    event_type: str = "ira_notification",
) -> None:
    """Send an ops notification email via resend/email connector, with fallback to memory queue."""
    resend_api_key = os.getenv("RESEND_API_KEY", "").strip()
    ops_email = os.getenv("OPS_NOTIFICATION_EMAIL", "").strip()
    if not ops_email:
        ops_email = "ops@nuxtron.local"
    queued: dict[str, Any] = {
        "id": len(context_runtime.resend_messages_memory) + 1,
        "tenant_id": tenant_id,
        "provider": "resend" if resend_api_key else "internal_queue",
        "to": ops_email,
        "subject": f"[IRA-{priority.upper()}] {subject}",
        "html": f"<p>{body}</p><p><small>Tenant: {tenant_id} | Event: {event_type}</small></p>",
        "status": "queued",
        "created_at": _now_iso(),
    }
    context_runtime.resend_messages_memory.append(queued)
    if resend_api_key:
        try:
            httpx.post(
                "https://api.resend.com/emails",
                json={
                    "from": "IRA Notifications <noreply@nuxtron.local>",
                    "to": [ops_email],
                    "subject": queued["subject"],
                    "html": queued["html"],
                },
                headers={"Authorization": f"Bearer {resend_api_key}"},
                timeout=4,
            )
            queued["status"] = "sent"
        except Exception:
            queued["status"] = "queued"


def helper_notify_ops_slack(
    context_runtime: ContextRuntime,
    *,
    tenant_id: str,
    text: str,
    title: str = "IRA Alert",
    priority: str = "normal",
    event_type: str = "ira_notification",
) -> None:
    """Post an ops alert to Slack via webhook, with fallback to memory queue."""
    webhook_url = os.getenv("SLACK_OPS_WEBHOOK_URL", "").strip()
    queued: dict[str, Any] = {
        "id": len(context_runtime.slack_messages_memory) + 1,
        "tenant_id": tenant_id,
        "provider": "slack_webhook",
        "channel": "#ira-alerts",
        "text_preview": text[:240],
        "event_type": event_type,
        "status": "queued",
        "created_at": _now_iso(),
    }
    context_runtime.slack_messages_memory.append(queued)
    if not webhook_url:
        return
    payload_body: dict[str, Any] = {
        "text": f"*[IRA-{priority.upper()}] {title}*\n{text}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*[IRA-{priority.upper()}] {title}*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text[:2000]}},
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Tenant: `{tenant_id}` | Event: `{event_type}`"}],
            },
        ],
    }
    try:
        target = resolve_outbound_target(webhook_url)
        response = outbound_request("POST", target, json=payload_body, timeout=4, max_response_bytes=64_000)
        queued["status"] = "sent" if response.is_success else "queued"
    except Exception:
        queued["status"] = "queued"


def helper_record_performance(
    context_runtime: ContextRuntime,
    tenant_id: str,
    action_type: str,
    *,
    latency_ms: float = 0.0,
    confidence: float = 0.5,
    outcome: str = "success",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record a performance data point for analytics."""
    context_runtime.ira_performance_log_memory.append(
        {
            "id": len(context_runtime.ira_performance_log_memory) + 1,
            "tenant_id": tenant_id,
            "action_type": action_type,
            "latency_ms": round(latency_ms, 2),
            "confidence": round(confidence, 3),
            "outcome": outcome,
            "metadata": metadata or {},
            "created_at": _now_iso(),
        }
    )


def execute_ira_frontier_stack(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:frontier:stack", 120, 60)
    stack = helper_frontier_stack_catalog()
    readiness = helper_frontier_readiness_summary(stack)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "frontier": stack,
        "readiness": readiness,
        "env_template": helper_frontier_env_template(readiness),
        "god_stack_example": {
            "brain": "OpenAI / Anthropic",
            "agents": "CrewAI + LangGraph",
            "memory": "Pinecone + Neo4j + Redis",
            "rag": "LlamaIndex (hybrid retrieval)",
            "workflows": "Temporal + n8n",
            "observability": "LangSmith + Weights & Biases",
        },
    }


def execute_ira_frontier_env_template(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:frontier:env-template", 120, 60)
    stack = helper_frontier_stack_catalog()
    readiness = helper_frontier_readiness_summary(stack)
    template = helper_frontier_env_template(readiness)
    return {"status": "ok", "tenant_id": auth.tenant_id, "readiness": readiness, "env_template": template}


def execute_ira_memory_overview(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:memory:overview", 120, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "memory": context_runtime.memory_system.overview(auth.tenant_id),
    }


def execute_ira_crm_connectors_status(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:crm:connectors:status", 60, 60)
    return {"status": "ok", "tenant_id": auth.tenant_id, "connectors": helper_probe_crm_connectors()}
