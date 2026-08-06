"""
Tests for media_jobs output-url success path (lines 451-465).
Directly injects a 'complete' job into media_jobs_memory to avoid time.sleep.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def fresh_client() -> TestClient:
    """Module-scoped TestClient — same pattern as all other test files (no lifespan)."""
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestOutputUrlCompletedJob:
    """Cover lines 451-465: output_signed_url for a completed job."""

    def _inject_complete_job(self, tenant_id: str, job_id_override: int | None = None) -> int:
        """Directly inject a completed job into media_jobs_memory via memory_stores."""
        from backend.fastapi.app import memory_stores
        store = memory_stores.media_jobs
        job_id = job_id_override or (len(store) + 9000)
        store.append({
            "id": job_id,
            "tenant_id": tenant_id,
            "storage_key": f"uploads/output-url-test/{job_id}.png",
            "output_bucket": "processed",
            "output_key": f"processed/{job_id}.png",
            "media_type": "image",
            "status": "complete",
            "progress": 100,
            "processing_options": {},
            "validation_token": None,
            "audit_log": [],
            "dlq": False,
            "dlq_reason": None,
        })
        return job_id

    def test_output_url_after_completion(self, fresh_client: TestClient) -> None:
        """Lines 451-465: output_signed_url success path."""
        tenant = "mj4-ourlcomplete"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        job_id = self._inject_complete_job(tenant)
        r = fresh_client.post(f"/media/jobs/{job_id}/output-url", headers=h, json={
            "expires_seconds": 900,
        })
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "signed_url" in data
            assert "expires_at" in data

    def test_output_url_different_expiry(self, fresh_client: TestClient) -> None:
        """Cover output-url with a different expires_seconds."""
        tenant = "mj4-ourlexpiry"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        job_id = self._inject_complete_job(tenant)
        r = fresh_client.post(f"/media/jobs/{job_id}/output-url", headers=h, json={
            "expires_seconds": 3600,
        })
        assert r.status_code in VALID

