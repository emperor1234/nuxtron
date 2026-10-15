"""Fail-closed contract for performance measurement and remediation."""

from typing import NoReturn

from fastapi import HTTPException

PERFORMANCE_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Verified lab measurements, field-vitals sources, and tenant-scoped monitoring are not configured. "
        "Performance scoring, history, monitors, report sharing, and auto-fix are disabled."
    ),
}

PERFORMANCE_UNAVAILABLE_501_RESPONSE = {
    501: {
        "description": "Performance measurement is unavailable until verified providers and tenant-scoped storage are configured.",
        "content": {"application/json": {"example": {"detail": PERFORMANCE_UNAVAILABLE_DETAIL}}},
    }
}


def raise_performance_unavailable() -> NoReturn:
    """Reject performance operations before network, persistence, or synthetic fallback work."""
    raise HTTPException(status_code=501, detail=PERFORMANCE_UNAVAILABLE_DETAIL)
