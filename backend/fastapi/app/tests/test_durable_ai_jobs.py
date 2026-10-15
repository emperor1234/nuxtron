from __future__ import annotations

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

from backend.fastapi.app.database import SessionLocal, get_db_session_sync
from backend.fastapi.app.durable_jobs import create_job, load_job, verify_job_reference
from backend.fastapi.app.models import JobOutbox


def setup_function() -> None:
    session = SessionLocal()
    session.close()


def test_create_job_writes_execution_and_outbox_atomically() -> None:
    reference = create_job(
        tenant_id="tenant-a",
        job_id="job-a",
        job_type="ai_generation:text",
        payload={"prompt": "private prompt", "media_type": "text"},
        task_name="nuxtron.tasks.ai.process_text",
        queue="ai-text",
        max_retries=1,
        expires_seconds=600,
    )
    job, tenant_id = load_job(reference)
    assert tenant_id == "tenant-a"
    assert job.status == "queued"
    assert job.job_params["prompt"] == "private prompt"
    assert verify_job_reference(reference) == ("job-a", "tenant-a")

    with pytest.raises(ValueError):
        verify_job_reference(reference[:-1] + ("x" if reference[-1] != "x" else "y"))


def test_outbox_is_tenant_scoped() -> None:
    create_job(
        tenant_id="tenant-a",
        job_id="job-a",
        job_type="ai_generation:text",
        payload={"prompt": "private prompt", "media_type": "text"},
        task_name="nuxtron.tasks.ai.process_text",
        queue="ai-text",
        max_retries=1,
        expires_seconds=600,
    )
    session = get_db_session_sync()
    try:
        rows = session.query(JobOutbox).filter_by(tenant_id="tenant-a", job_id="job-a").all()
        assert len(rows) == 1
        assert ".tenant-a." in rows[0].payload["job_reference"]
        assert session.query(JobOutbox).filter_by(tenant_id="tenant-b", job_id="job-a").count() == 0
    finally:
        session.close()
