"""Workflow graph implementation with explicit dependencies."""

from .constants import ACTION_TYPES
from .constants import HIGH_RISK_ACTIONS
from .schemas import WorkflowStepModel
from datetime import UTC
from datetime import datetime
from typing import Any


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def is_high_risk(workflow: dict[str, Any]) -> bool:
    steps = workflow.get("steps", [])
    return any((str(step.get("action_type", "")).strip().lower() in HIGH_RISK_ACTIONS for step in steps))


def count_approvals(request: dict[str, Any]) -> int:
    return len(request.get("approved_by") or [])


def parse_iso(value: Any) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return datetime.fromtimestamp(0, tz=UTC)


def normalized_steps(steps: list[WorkflowStepModel]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for s in steps:
        normalized.append(
            {
                "step_id": s.step_id,
                "action_type": s.action_type.strip().lower(),
                "config": s.config,
                "next_step_id": s.next_step_id,
                "branch_yes": s.branch_yes,
                "branch_no": s.branch_no,
                "delay_hours": s.delay_hours,
            }
        )
    return normalized


def validate_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    step_ids = [str(step.get("step_id", "")).strip() for step in steps]
    if len(step_ids) != len(set(step_ids)):
        errors.append("Duplicate step_id values are not allowed.")
    step_id_set = set(step_ids)
    for step in steps:
        step_id = str(step.get("step_id", "")).strip()
        action = str(step.get("action_type", "")).strip().lower()
        if action not in ACTION_TYPES:
            errors.append(f"Unsupported action_type for step {step_id}: {action}")
        next_step = str(step.get("next_step_id", "")).strip()
        if next_step and next_step not in step_id_set:
            errors.append(f"next_step_id not found for step {step_id}: {next_step}")
        if action == "branch_condition":
            branch_yes = str(step.get("branch_yes", "")).strip()
            branch_no = str(step.get("branch_no", "")).strip()
            if not branch_yes or not branch_no:
                errors.append(f"branch_condition requires branch_yes and branch_no for step {step_id}")
            if branch_yes and branch_yes not in step_id_set:
                errors.append(f"branch_yes target not found for step {step_id}: {branch_yes}")
            if branch_no and branch_no not in step_id_set:
                errors.append(f"branch_no target not found for step {step_id}: {branch_no}")
        if action == "delay" and int(step.get("delay_hours", 0)) == 0:
            warnings.append(f"delay step {step_id} has delay_hours=0 and behaves like a passthrough step.")
    return {"errors": errors, "warnings": warnings}


def preview_graph_path(steps: list[dict[str, Any]], start_step_id: str, max_steps: int = 100) -> dict[str, Any]:
    if not steps:
        return {"visited": [], "halt_reason": "empty"}
    step_map = {str(step.get("step_id", "")): step for step in steps}
    current = start_step_id or str(steps[0].get("step_id", ""))
    visited: list[str] = []
    seen_count: dict[str, int] = {}
    while current:
        if current not in step_map:
            return {"visited": visited, "halt_reason": f"unknown_step:{current}"}
        if len(visited) >= max_steps:
            return {"visited": visited, "halt_reason": "max_steps_exceeded"}
        visited.append(current)
        seen_count[current] = seen_count.get(current, 0) + 1
        if seen_count[current] > 2:
            return {"visited": visited, "halt_reason": f"cycle_detected:{current}"}
        step = step_map[current]
        action = str(step.get("action_type", "")).strip().lower()
        if action == "branch_condition":
            current = str(step.get("branch_yes", "")).strip()
        else:
            current = str(step.get("next_step_id", "")).strip()
    return {"visited": visited, "halt_reason": "terminal"}
