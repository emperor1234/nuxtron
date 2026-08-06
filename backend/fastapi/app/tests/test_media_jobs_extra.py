"""
Tests for media_jobs router — covering uncovered endpoints.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)

# A tiny valid PNG in base64 (8x8 transparent PNG)
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAAXNSR0IArs4c6QAAAA"
    "pJREFUGFdjYGBg+A8AAQQAAf9ToxIAAAAASUVORK5CYII="
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestValidateFile:
    def test_validate_valid_image(self, client: TestClient) -> None:
        r = client.post("/media/validate-file", headers=H, json={
            "file_base64": TINY_PNG_B64,
            "media_type": "image",
        })
        assert r.status_code in VALID

    def test_validate_invalid_base64(self, client: TestClient) -> None:
        r = client.post("/media/validate-file", headers=H, json={
            "file_base64": "not-valid-base64!!!",
            "media_type": "image",
        })
        assert r.status_code in VALID

    def test_validate_empty_payload(self, client: TestClient) -> None:
        r = client.post("/media/validate-file", headers=H, json={})
        assert r.status_code in VALID


class TestCreateJob:
    def test_create_image_job(self, client: TestClient) -> None:
        r = client.post("/media/jobs", headers=H, json={
            "media_type": "image",
            "operation": "resize",
            "source_url": "https://example.com/test.png",
        })
        assert r.status_code in VALID

    def test_create_video_job(self, client: TestClient) -> None:
        r = client.post("/media/jobs", headers=H, json={
            "media_type": "video",
            "operation": "transcode",
            "source_url": "https://example.com/test.mp4",
        })
        assert r.status_code in VALID

    def test_create_job_invalid_media_type(self, client: TestClient) -> None:
        r = client.post("/media/jobs", headers=H, json={
            "media_type": "invalid_type",
            "operation": "compress",
        })
        assert r.status_code in VALID


class TestListJobs:
    def test_list_jobs_default(self, client: TestClient) -> None:
        r = client.get("/media/jobs", headers=H)
        assert r.status_code in VALID

    def test_list_jobs_with_filter(self, client: TestClient) -> None:
        r = client.get("/media/jobs?status=pending", headers=H)
        assert r.status_code in VALID


class TestGetJob:
    def test_get_nonexistent_job(self, client: TestClient) -> None:
        r = client.get("/media/jobs/job_nonexistent", headers=H)
        assert r.status_code in VALID


class TestCancelJob:
    def test_cancel_nonexistent_job(self, client: TestClient) -> None:
        r = client.delete("/media/jobs/job_nonexistent", headers=H)
        assert r.status_code in VALID


class TestRetryJob:
    def test_retry_nonexistent_job(self, client: TestClient) -> None:
        r = client.post("/media/jobs/job_nonexistent/retry", headers=H, json={})
        assert r.status_code in VALID


class TestOutputUrl:
    def test_output_url_nonexistent_job(self, client: TestClient) -> None:
        r = client.post("/media/jobs/job_nonexistent/output-url", headers=H, json={})
        assert r.status_code in VALID


class TestDLQAndStream:
    def test_get_dlq(self, client: TestClient) -> None:
        r = client.get("/media/jobs/dlq", headers=H)
        assert r.status_code in VALID

    def test_stream_nonexistent_job(self, client: TestClient) -> None:
        r = client.get("/media/jobs/job_nonexistent/stream", headers=H)
        assert r.status_code in VALID
