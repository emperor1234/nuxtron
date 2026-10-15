"""Explicit capability gates for production Workforce execution."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel


class WorkforceExecutionUnavailableDetail(BaseModel):
    code: Literal["NOT_IMPLEMENTED"]
    message: str


class WorkforceExecutionUnavailableResponse(BaseModel):
    detail: WorkforceExecutionUnavailableDetail


WORKFORCE_EXECUTION_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Autonomous Workforce execution is disabled in production until provider credentials are resolved from "
        "tenant-scoped durable secrets and job/outcome persistence is transactional and restart-safe."
    ),
}
WORKFORCE_EXECUTION_UNAVAILABLE_RESPONSES = {
    501: {
        "model": WorkforceExecutionUnavailableResponse,
        "description": "Durable tenant-scoped mission execution is not configured.",
    }
}
WORKFORCE_API_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Autonomous Workforce APIs are disabled in production until their data uses the canonical tenant-isolated "
        "PostgreSQL schema, migrations, and durable repository instead of process-local or legacy storage."
    ),
}
WORKFORCE_API_UNAVAILABLE_RESPONSES = {
    501: {
        "model": WorkforceExecutionUnavailableResponse,
        "description": "The Workforce production persistence and tenant-isolation boundary is not implemented.",
    }
}


def require_workforce_execution_available() -> None:
    """Prevent production mission actions from using in-memory state or queueing raw credentials."""
    if os.getenv("ENVIRONMENT", "development").strip().lower() in {"prod", "production"}:
        raise HTTPException(status_code=501, detail=WORKFORCE_EXECUTION_UNAVAILABLE_DETAIL)


def require_workforce_api_available() -> None:
    """Reject every Workforce API call until production persistence is tenant-isolated and durable."""
    if os.getenv("ENVIRONMENT", "development").strip().lower() in {"prod", "production"}:
        raise HTTPException(status_code=501, detail=WORKFORCE_API_UNAVAILABLE_DETAIL)
