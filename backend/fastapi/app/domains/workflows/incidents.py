"""Workflow incidents implementation with explicit dependencies."""

from .graph import parse_iso
from .runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from typing import Any


def record_sla_alert(
    runtime: WorkflowRuntime, tenant_id: str, connector: dict[str, Any], reliability: dict[str, Any]
) -> None:
    if not (bool(reliability.get("availability_breached")) or bool(reliability.get("latency_breached"))):
        return
    alert_type = "availability" if bool(reliability.get("availability_breached")) else "latency"
    with runtime.lock:
        existing_open = next(
            (
                a
                for a in runtime.connector_sla_alerts
                if a.get("tenant_id") == tenant_id
                and a.get("connector_id") == connector.get("id")
                and (a.get("type") == alert_type)
                and (a.get("status") == "open")
            ),
            None,
        )
        if existing_open is not None:
            existing_open["last_seen_at"] = datetime.now(UTC).isoformat()
            existing_open["snapshot"] = reliability
            existing_open["breach_count"] = int(existing_open.get("breach_count", 1)) + 1
            evaluate_alert_escalation(runtime, existing_open)
            return
        runtime.connector_sla_alerts.append(
            {
                "id": len(runtime.connector_sla_alerts) + 1,
                "tenant_id": tenant_id,
                "connector_id": connector.get("id"),
                "connector_name": connector.get("name"),
                "type": alert_type,
                "status": "open",
                "message": "SLA target breached for connector reliability.",
                "snapshot": reliability,
                "breach_count": 1,
                "escalated_rule_ids": [],
                "created_at": datetime.now(UTC).isoformat(),
                "last_seen_at": datetime.now(UTC).isoformat(),
            }
        )
        evaluate_alert_escalation(runtime, runtime.connector_sla_alerts[-1])


def evaluate_alert_escalation(runtime: WorkflowRuntime, alert: dict[str, Any]) -> None:
    tenant_id = str(alert.get("tenant_id", ""))
    connector_id = int(alert.get("connector_id", 0))
    breach_count = int(alert.get("breach_count", 1))
    already_escalated = set(alert.get("escalated_rule_ids") or [])
    for rule in runtime.connector_escalation_rules:
        if rule.get("tenant_id") != tenant_id or not bool(rule.get("enabled", True)):
            continue
        min_breach = int(rule.get("min_breach_count", 1))
        rule_id = int(rule.get("id", 0))
        if breach_count < min_breach or rule_id in already_escalated:
            continue
        runtime.connector_escalation_events.append(
            {
                "id": len(runtime.connector_escalation_events) + 1,
                "tenant_id": tenant_id,
                "connector_id": connector_id,
                "alert_id": alert.get("id"),
                "rule_id": rule_id,
                "rule_name": rule.get("name"),
                "channels": rule.get("channels", []),
                "notify_recipients": rule.get("notify_recipients", []),
                "status": "triggered",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        escalated_ids = alert.setdefault("escalated_rule_ids", [])
        escalated_ids.append(rule_id)


def close_sla_alerts_if_recovered(
    runtime: WorkflowRuntime, tenant_id: str, connector_id: int, reliability: dict[str, Any]
) -> None:
    recovered = not bool(reliability.get("availability_breached")) and (not bool(reliability.get("latency_breached")))
    if not recovered:
        return
    with runtime.lock:
        for alert in runtime.connector_sla_alerts:
            if (
                alert.get("tenant_id") == tenant_id
                and int(alert.get("connector_id", 0)) == connector_id
                and (alert.get("status") == "open")
            ):
                alert["status"] = "resolved"
                alert["resolved_at"] = datetime.now(UTC).isoformat()


def build_incident_timeline(
    runtime: WorkflowRuntime, *, tenant_id: str, connector_id: int, limit: int
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for alert in runtime.connector_sla_alerts:
        if alert.get("tenant_id") != tenant_id or int(alert.get("connector_id", 0)) != connector_id:
            continue
        timeline.append(
            {
                "type": "sla_alert",
                "ref_id": int(alert.get("id", 0)),
                "status": alert.get("status", "unknown"),
                "occurred_at": alert.get("last_seen_at") or alert.get("created_at"),
                "details": {"alert_type": alert.get("type"), "breach_count": int(alert.get("breach_count", 1))},
            }
        )
    for event in runtime.connector_escalation_events:
        if event.get("tenant_id") != tenant_id or int(event.get("connector_id", 0)) != connector_id:
            continue
        timeline.append(
            {
                "type": "escalation_event",
                "ref_id": int(event.get("id", 0)),
                "status": event.get("status", "unknown"),
                "occurred_at": event.get("resolved_at") or event.get("acknowledged_at") or event.get("created_at"),
                "details": {"rule_name": event.get("rule_name"), "channels": event.get("channels", [])},
            }
        )
    for replay_item in runtime.connector_replay_queue:
        if replay_item.get("tenant_id") != tenant_id or int(replay_item.get("connector_id", 0)) != connector_id:
            continue
        timeline.append(
            {
                "type": "replay_attempt",
                "ref_id": int(replay_item.get("id", 0)),
                "status": replay_item.get("status", "unknown"),
                "occurred_at": replay_item.get("updated_at") or replay_item.get("created_at"),
                "details": {
                    "failure_type": replay_item.get("failure_type"),
                    "attempts": int(replay_item.get("attempts", 0)),
                },
            }
        )
    timeline.sort(key=lambda item: parse_iso(item.get("occurred_at")), reverse=True)
    return timeline[:limit]
