"""Assistant constants and configuration vocabulary."""

from ...deps import AuthContext
from ...deps import require_auth
from fastapi import Depends
from typing import Annotated
import re

AuthDep = Annotated[AuthContext, Depends(require_auth)]

HIGH_IMPACT_TARGETS = {"admin", "billing", "credits", "payouts", "security"}

DEFAULT_BLOCKED_ACTIONS = ["billing_change", "credit_spend", "external_transfer"]

CONNECTOR_CHANNELS: tuple[str, ...] = ("chat", "email", "ticket", "webhook", "admin", "customer_support")

EXPLICIT_APPROVAL_COMMAND_MARKERS = ("billing_change", "credit_spend", "external_transfer", "refund_force")

HUMAN_VALIDATION_COMMAND_MARKERS = ("compliance", "bulk", "ticket", "campaign", "broadcast")

TOKEN_PATTERN = re.compile("\\w{2,}")

LOCAL_EMBEDDING_DIMENSIONS = 64

APPLICATION_JSON = "application/json"

CRM_FEATURE_KEYS: tuple[str, ...] = (
    "multi_tenancy",
    "low_code_objects",
    "sales_pipeline_and_erp_adjacent",
    "cross_platform_workflow_orchestration",
    "ecosystem_modules",
)

CRM_DEFAULT_OWNERSHIP: dict[str, str] = {
    "multi_tenancy": "corteza",
    "low_code_objects": "corteza",
    "sales_pipeline_and_erp_adjacent": "odoo",
    "cross_platform_workflow_orchestration": "corteza",
    "ecosystem_modules": "odoo",
}

AUTONOMY_DISABLED_DETAIL = "IRA autonomy is disabled for this tenant."

IRA_PLAYBOOK_DECISION_TREE: tuple[dict[str, str], ...] = (
    {
        "question": "Do you have paying users?",
        "if_yes": "Optimize retention and expansion; do not pause shipping.",
        "if_no": "Refine positioning and run customer interviews before adding scope.",
    },
    {
        "question": "Do users reach value in first 7 days?",
        "if_yes": "Scale acquisition channels and agency partner activation.",
        "if_no": "Improve onboarding and guided first outcomes in the control center.",
    },
    {
        "question": "Is autonomy healthy (risk + finance + connectors)?",
        "if_yes": "Expand automation depth safely with guarded approvals.",
        "if_no": "Stabilize protections and connector reliability before expansion.",
    },
    {
        "question": "Have key channels remained available?",
        "if_yes": "Increase cadence and campaign throughput.",
        "if_no": "Use fallback channels and activate resilience playbooks.",
    },
)
