"""Truthful boundary for UGC features without verified consent and publishing evidence."""

from typing import Any, NoReturn

from fastapi import HTTPException

UGC_UNAVAILABLE_DETAIL: dict[str, str] = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "UGC workflows are unavailable until verified discovery, creator-sourced rights consent, "
        "durable tenant-scoped asset storage, and an authorized publishing connection are implemented."
    ),
}

UGC_UNAVAILABLE_RESPONSES: dict[int, dict[str, Any]] = {
    501: {
        "description": "UGC provider evidence, creator consent, and durable publishing are unavailable.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "detail": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string", "enum": ["NOT_IMPLEMENTED"]},
                                "message": {"type": "string"},
                            },
                            "required": ["code", "message"],
                        }
                    },
                    "required": ["detail"],
                }
            }
        },
    }
}


def raise_ugc_unavailable() -> NoReturn:
    """Fail before any provider call, state mutation, rate-limit, or audit write."""
    raise HTTPException(
        status_code=501,
        detail=UGC_UNAVAILABLE_DETAIL,
        headers={"Cache-Control": "no-store"},
    )
