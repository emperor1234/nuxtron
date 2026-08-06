"""Validation helpers used by Lindy routers."""

from fastapi import HTTPException


def validate_email_list(emails: list[str]) -> None:
    """Validate a list of email-like strings for basic router input checks."""
    invalid = [email for email in emails if "@" not in email or email.startswith("@") or email.endswith("@")]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid attendee email(s): {', '.join(invalid)}")
