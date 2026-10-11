"""Durable, redacted security audit events."""

from __future__ import annotations


import hashlib
import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy import JSON, bindparam, text

from ...database import organization_scoped_session


def durable_audit_enabled() -> bool:
    return os.getenv("SECURITY_AUDIT_DURABLE", "false").strip().lower() in {"1", "true", "yes"}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:64] if value else ""


def record_security_event(
    *,
    tenant_id: str,
    event_type: str,
    principal_id: str,
    auth_mode: str,
    method: str,
    path: str,
    request_id: str,
    client_ip: str,
    user_agent: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write one organization-scoped, non-secret audit record."""
    try:
        with organization_scoped_session(tenant_id) as session:
            session.execute(
                text(
                    """
                    INSERT INTO security_audit_events
                        (tenant_id, event_type, principal_id, auth_mode, method,
                         path, request_id, ip_hash, user_agent_hash, metadata)
                    VALUES
                        (:tenant_id, :event_type, :principal_id, :auth_mode, :method,
                         :path, :request_id, :ip_hash, :user_agent_hash, :metadata)
                    """
                ).bindparams(bindparam("metadata", type_=JSON)),
                {
                    "tenant_id": tenant_id,
                    "event_type": event_type,
                    "principal_id": principal_id[:255],
                    "auth_mode": auth_mode[:40],
                    "method": method[:12],
                    "path": path[:512],
                    "request_id": request_id[:160],
                    "ip_hash": _hash(client_ip),
                    "user_agent_hash": _hash(user_agent),
                    "metadata": metadata or {},
                },
            )
    except Exception as exc:
        if os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
            raise HTTPException(status_code=503, detail="Security audit service unavailable.") from exc
        raise
