"""Workflow action vocabulary and HTTP authorization annotation."""

from ...deps import AuthContext
from ...deps import require_auth
from fastapi import Depends
from typing import Annotated

AuthDep = Annotated[AuthContext, Depends(require_auth)]

WORKFLOW_NOT_FOUND = "Workflow not found."

EXECUTION_NOT_FOUND = "Workflow execution not found."

TRIGGER_TYPES = {
    "contact_created",
    "deal_stage_changed",
    "form_submitted",
    "ticket_created",
    "survey_response",
    "date_based",
    "manual",
    "tag_added",
    "property_changed",
    "webhook",
    "api_event",
}

ACTION_TYPES = {
    "send_email",
    "update_property",
    "add_tag",
    "remove_tag",
    "notify_rep",
    "create_task",
    "send_webhook",
    "delay",
    "branch_condition",
    "enroll_sequence",
    "create_ticket",
    "add_to_list",
}

HIGH_RISK_ACTIONS = {"send_webhook", "update_property", "create_ticket"}
