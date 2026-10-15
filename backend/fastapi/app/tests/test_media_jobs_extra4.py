"""Regression tests for media output URLs when durable artifacts are unavailable."""

from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from fastapi.testclient import TestClient
import pytest


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestMediaOutputUrlCapability:
    def test_completed_memory_row_never_produces_a_signed_url(self, client: TestClient) -> None:
        """No process-local row may authorize a synthetic or non-durable output URL."""
        from backend.fastapi.app import memory_stores

        tenant_id = "media-output-capability-test"
        job_id = len(memory_stores.media_jobs) + 9000
        memory_stores.media_jobs.append(
            {
                "id": job_id,
                "tenant_id": tenant_id,
                "storage_key": f"raw-input/{tenant_id}/source.png",
                "output_bucket": "processed-output",
                "output_key": f"processed/{tenant_id}/{job_id}/source.png",
                "media_type": "image",
                "status": "complete",
                "progress_pct": 100,
            }
        )
        response = client.post(
            f"/media/jobs/{job_id}/output-url",
            headers={"X-API-Key": "test-api-key", "X-Tenant-Id": tenant_id},
            json={"expires_seconds": 900},
        )

        assert response.status_code == 501
        assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
        assert "signed_url" not in response.json()

    def test_expiry_bounds_are_still_schema_validated(self, client: TestClient) -> None:
        response = client.post(
            "/media/jobs/1/output-url",
            headers={"X-API-Key": "test-api-key", "X-Tenant-Id": "media-output-capability-test"},
            json={"expires_seconds": 5},
        )
        assert response.status_code == 422
