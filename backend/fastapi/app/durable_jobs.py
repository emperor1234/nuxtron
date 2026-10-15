"""Durable, tenant-scoped job persistence and signed worker references.

The API stores the complete request in ``job_executions.job_params`` and creates
an outbox record in the same transaction. Celery receives only a signed opaque
reference; workers reload the request under the tenant's RLS context.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from .database import get_db_session_sync, organization_scoped_session
from .models import JobExecution, JobOutbox, Tenant


def _signing_key() -> bytes:
    value = os.getenv("AI_JOB_SIGNING_SECRET", "").strip() or os.getenv("APP_ENC_KEY", "").strip()
    if not value:
        if os.getenv("ENVIRONMENT", "").strip().lower() == "production":
            raise RuntimeError("AI_JOB_SIGNING_SECRET must be configured in production")
        value = "development-only-ai-job-signing-secret"
    return value.encode("utf-8")


def sign_job_reference(job_id: str, tenant_id: str) -> str:
    """Return an authenticated reference containing no job payload."""
    body = f"{job_id}.{tenant_id}".encode()
    digest = hmac.new(_signing_key(), body, hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{job_id}.{tenant_id}.{signature}"


def verify_job_reference(reference: str) -> tuple[str, str]:
    parts = reference.split(".")
    if len(parts) != 3 or not all(parts):
        raise ValueError("Invalid job reference")
    job_id, tenant_id, supplied = parts
    expected = sign_job_reference(job_id, tenant_id).rsplit(".", 1)[1]
    if not hmac.compare_digest(supplied, expected):
        raise ValueError("Invalid job reference signature")
    return job_id, tenant_id


def create_job(
    *,
    tenant_id: str,
    job_id: str,
    job_type: str,
    payload: dict[str, Any],
    task_name: str,
    queue: str,
    max_retries: int,
    expires_seconds: int,
) -> str:
    """Create execution and outbox rows atomically and return a signed ref."""
    now = datetime.now(UTC)
    reference = sign_job_reference(job_id, tenant_id)
    params = dict(payload)
    params["job_reference"] = reference
    with organization_scoped_session(tenant_id) as session:
        existing = session.scalar(
            select(JobExecution).where(
                JobExecution.tenant_id == tenant_id,
                JobExecution.job_id == job_id,
            )
        )
        if existing is None:
            session.add(
                JobExecution(
                    tenant_id=tenant_id,
                    job_id=job_id,
                    job_type=job_type,
                    status="queued",
                    job_params=params,
                    queued_at=now,
                    max_retries=max_retries,
                    data={"queue": queue, "expires_seconds": expires_seconds},
                )
            )
            session.add(
                JobOutbox(
                    tenant_id=tenant_id,
                    job_id=job_id,
                    task_name=task_name,
                    queue=queue,
                    payload={"job_reference": reference},
                    status="pending",
                    available_at=now,
                )
            )
    return reference


def load_job(reference: str) -> tuple[JobExecution, str]:
    job_id, tenant_id = verify_job_reference(reference)
    with organization_scoped_session(tenant_id) as session:
        job = session.scalar(
            select(JobExecution).where(
                JobExecution.tenant_id == tenant_id,
                JobExecution.job_id == job_id,
            )
        )
        if job is None:
            raise LookupError("Job not found")
        session.expunge(job)
        return job, tenant_id


def update_job(
    reference: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
    celery_task_id: str | None = None,
) -> None:
    job_id, tenant_id = verify_job_reference(reference)
    now = datetime.now(UTC)
    with organization_scoped_session(tenant_id) as session:
        job = session.scalar(
            select(JobExecution).where(
                JobExecution.tenant_id == tenant_id,
                JobExecution.job_id == job_id,
            )
        )
        if job is None:
            raise LookupError("Job not found")
        if status == "running" and job.started_at is None:
            job.started_at = now
        if status in {"completed", "failed"}:
            job.completed_at = now
            if job.started_at:
                job.duration_seconds = max(0.0, (now - job.started_at).total_seconds())
        job.status = status
        if result is not None:
            job.result = result
        if error_message is not None:
            job.error_message = error_message
        if celery_task_id:
            job.data = {**(job.data or {}), "celery_task_id": celery_task_id}


def mark_outbox_published(reference: str, celery_task_id: str) -> None:
    job_id, tenant_id = verify_job_reference(reference)
    with organization_scoped_session(tenant_id) as session:
        row = session.scalar(
            select(JobOutbox).where(
                JobOutbox.tenant_id == tenant_id,
                JobOutbox.job_id == job_id,
                JobOutbox.status.in_(("pending", "publishing")),
            )
        )
        if row is not None:
            row.status = "published"
            row.published_at = datetime.now(UTC)
            row.attempts += 1
            row.last_error = None
            row.payload = {**(row.payload or {}), "celery_task_id": celery_task_id}


def claim_pending_outbox(limit: int = 100) -> list[dict[str, str]]:
    """Claim ready messages tenant-by-tenant so PostgreSQL RLS stays enabled."""
    now = datetime.now(UTC)
    tenant_session = get_db_session_sync()
    try:
        tenant_ids = [row[0] for row in tenant_session.execute(select(Tenant.tenant_id)).all()]
    finally:
        tenant_session.close()
    claimed: list[dict[str, str]] = []
    for tenant_id in tenant_ids:
        if len(claimed) >= limit:
            break
        with organization_scoped_session(tenant_id) as session:
            rows = session.scalars(
                select(JobOutbox)
                .where(JobOutbox.tenant_id == tenant_id, JobOutbox.status == "pending", JobOutbox.available_at <= now)
                .order_by(JobOutbox.available_at, JobOutbox.id)
                .limit(limit - len(claimed))
                .with_for_update(skip_locked=True)
            ).all()
            for row in rows:
                row.status = "publishing"
                reference = str((row.payload or {}).get("job_reference") or "")
                if reference:
                    claimed.append({"reference": reference, "task_name": row.task_name, "queue": row.queue})
    return claimed


def mark_outbox_failed(reference: str, error: str) -> None:
    job_id, tenant_id = verify_job_reference(reference)
    with organization_scoped_session(tenant_id) as session:
        row = session.scalar(
            select(JobOutbox).where(
                JobOutbox.tenant_id == tenant_id,
                JobOutbox.job_id == job_id,
            )
        )
        if row is not None:
            row.status = "pending"
            row.attempts += 1
            row.last_error = error[:2000]
            row.available_at = datetime.now(UTC) + timedelta(seconds=min(300, 2 ** min(row.attempts, 8)))


def new_job_id() -> str:
    return secrets.token_urlsafe(24)
