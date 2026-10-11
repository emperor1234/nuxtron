"""Crm constants and configuration vocabulary."""

from ...deps import AuthContext
from ...deps import require_auth
from .schemas import _PipelineStage
from fastapi import Depends
from typing import Annotated

AuthDep = Annotated[AuthContext, Depends(require_auth)]

CONTACT_NOT_FOUND = "Contact not found."

DEAL_NOT_FOUND = "Deal not found."

LEAD_NOT_FOUND = "Lead not found."

TICKET_NOT_FOUND = "Ticket not found."

TASK_NOT_FOUND = "Task not found."

CAMPAIGN_NOT_FOUND = "Campaign not found."

QUOTE_NOT_FOUND = "Quote not found."

INVOICE_NOT_FOUND = "CRM invoice not found."

SEQUENCE_NOT_FOUND = "Email sequence not found."

WORKFLOW_NOT_FOUND = "Workflow rule not found."

SEGMENT_NOT_FOUND = "Segment not found."

PROJECT_NOT_FOUND = "Project not found."

ENTITY_TYPE_NOT_FOUND = "Custom entity type not found."

AUTOMATION_RECIPE_NOT_FOUND = "Automation recipe not found."

PIPELINE_STAGES: list[_PipelineStage] = [
    {"stage": "prospect", "display": "Prospect", "probability": 10},
    {"stage": "qualified", "display": "Qualified", "probability": 25},
    {"stage": "proposal", "display": "Proposal", "probability": 50},
    {"stage": "negotiation", "display": "Negotiation", "probability": 75},
    {"stage": "closed_won", "display": "Closed Won", "probability": 100},
    {"stage": "closed_lost", "display": "Closed Lost", "probability": 0},
]
