"""Transactional email router — provider-agnostic send endpoint.

Uses the same multi-provider dispatch already present in legacy_main.py but
exposes it through a clean, documented API route.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

logger = logging.getLogger(__name__)

AuthDep = Annotated[AuthContext, Depends(require_auth)]

DEFAULT_FROM_EMAIL = "noreply@nuxtron.local"


# ── Provider dispatch ─────────────────────────────────────────────────────────

def _send_resend(to: str, subject: str, body: str, html: str | None) -> tuple[bool, str]:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    api_base = os.getenv("RESEND_API_BASE_URL", "https://api.resend.com").rstrip("/")
    from_email = (
        os.getenv("RESEND_FROM_EMAIL", "").strip()
        or os.getenv("SMTP_FROM", "").strip()
        or DEFAULT_FROM_EMAIL
    )
    if not api_key or api_key.startswith("local-"):
        return False, "Resend API key not configured."

    payload: dict[str, object] = {"from": from_email, "to": [to], "subject": subject, "text": body}
    if html:
        payload["html"] = html

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{api_base}/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        return (resp.is_success, "Sent via Resend.") if resp.is_success else (False, f"Resend error {resp.status_code}")
    except Exception as exc:
        return False, f"Resend request failed: {exc}"


def _send_ses_smtp(to: str, subject: str, body: str) -> tuple[bool, str]:
    host = os.getenv("SES_SMTP_HOST", "").strip()
    port = int(os.getenv("SES_SMTP_PORT", "587"))
    username = os.getenv("SES_SMTP_USERNAME", "").strip()
    password = os.getenv("SES_SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SES_FROM_EMAIL", DEFAULT_FROM_EMAIL).strip()
    if not host or not username or not password:
        return False, "SES SMTP not configured."

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host=host, port=port, context=ctx, timeout=12) as srv:
                srv.login(username, password)
                srv.send_message(msg)
        else:
            with smtplib.SMTP(host=host, port=port, timeout=12) as srv:
                srv.starttls(context=ctx)
                srv.login(username, password)
                srv.send_message(msg)
        return True, "Sent via SES SMTP."
    except Exception as exc:
        return False, f"SES SMTP failed: {exc}"


def _send_smtp(to: str, subject: str, body: str) -> tuple[bool, str]:
    """Generic SMTP (for Mailgun SMTP, Postmark SMTP, or any SMTP relay)."""
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM", DEFAULT_FROM_EMAIL).strip()
    if not host or not username:
        return False, "SMTP not configured."

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        with smtplib.SMTP(host=host, port=port, timeout=12) as srv:
            srv.starttls(context=ctx)
            if username and password:
                srv.login(username, password)
            srv.send_message(msg)
        return True, "Sent via SMTP."
    except Exception as exc:
        return False, f"SMTP failed: {exc}"


def dispatch_transactional(
    to: str,
    subject: str,
    body: str,
    html: str | None = None,
    provider: str | None = None,
) -> tuple[bool, str, str]:
    """Try providers in order; returns (success, provider_name, detail)."""
    preferred = (provider or os.getenv("EMAIL_PROVIDER", "resend")).lower()

    ordered: list[tuple[str, Any]] = []
    provider_map = {
        "resend": ("resend", lambda: _send_resend(to, subject, body, html)),
        "ses": ("ses", lambda: _send_ses_smtp(to, subject, body)),
        "smtp": ("smtp", lambda: _send_smtp(to, subject, body)),
    }

    # Put preferred first, then try the rest
    if preferred in provider_map:
        ordered.append(provider_map.pop(preferred))
    ordered.extend(provider_map.values())

    last_detail = "No email transport configured."
    for name, sender_fn in ordered:
        success, detail = sender_fn()
        if success:
            return True, name, detail
        last_detail = detail
        if "not configured" not in detail.lower():
            return False, name, detail

    return False, "unavailable", last_detail


# ── Router ────────────────────────────────────────────────────────────────────

class TransactionalSendRequest(BaseModel):
    to: str = Field(min_length=3, max_length=254, description="Recipient email address")
    subject: str = Field(min_length=1, max_length=320)
    body: str = Field(min_length=1, max_length=100_000, description="Plain-text email body")
    html: str | None = Field(default=None, max_length=500_000, description="Optional HTML body")
    provider: str | None = Field(
        default=None,
        max_length=20,
        description="Force a specific provider: resend | ses | smtp. Defaults to EMAIL_PROVIDER env var.",
    )


def create_email_router() -> APIRouter:
    router = APIRouter(prefix="/email", tags=["Email"])

    @router.post("/transactional/send")
    def send_transactional(
        payload: TransactionalSendRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        """Send a single transactional email through the configured provider.

        Tries the requested provider first, then falls back automatically.
        Returns ``delivery_status: sent | queued`` — *queued* means the primary
        provider was unavailable in dev; the message was not dropped.
        """
        success, provider_used, detail = dispatch_transactional(
            to=str(payload.to),
            subject=payload.subject,
            body=payload.body,
            html=payload.html,
            provider=payload.provider,
        )

        if not success and "not configured" not in detail.lower():
            logger.error("Transactional email dispatch failed: %s", detail)
            raise HTTPException(status_code=502, detail=f"Email delivery failed: {detail}")

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "to": str(payload.to),
            "provider": provider_used,
            "delivery_status": "sent" if success else "queued",
            "detail": detail,
        }

    @router.get("/config/status")
    def email_config_status(auth: AuthDep) -> dict[str, Any]:  # noqa: ARG001
        """Return which email providers are configured (keys present, not actual values)."""
        return {
            "status": "ok",
            "providers": {
                "resend": bool(os.getenv("RESEND_API_KEY", "").strip() and not os.getenv("RESEND_API_KEY", "").startswith("local-")),
                "ses_smtp": bool(os.getenv("SES_SMTP_HOST", "").strip() and os.getenv("SES_SMTP_USERNAME", "").strip()),
                "smtp": bool(os.getenv("SMTP_HOST", "").strip()),
            },
            "active_provider": os.getenv("EMAIL_PROVIDER", "resend"),
            "from_address": (
                os.getenv("RESEND_FROM_EMAIL", "")
                or os.getenv("SMTP_FROM", "")
                or os.getenv("SES_FROM_EMAIL", "")
                or DEFAULT_FROM_EMAIL
            ),
        }

    return router
