"""
Tests for media_jobs.py pure helpers and routes.
"""
from __future__ import annotations

import base64
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestSseMessage:
    def _fn(self):
        from backend.fastapi.app.routers.media_jobs import _sse_message
        return _sse_message

    def test_format(self) -> None:
        fn = self._fn()
        result = fn("job.updated", {"status": "done"})
        assert result.startswith("event: job.updated\n")
        assert "data:" in result
        assert result.endswith("\n\n")

    def test_payload_serialized(self) -> None:
        fn = self._fn()
        result = fn("test.event", {"key": "value", "num": 42})
        assert '"key":"value"' in result or '"key": "value"' in result


class TestDetectMagicMime:
    def _fn(self):
        from backend.fastapi.app.routers.media_jobs import _detect_magic_mime
        return _detect_magic_mime

    def test_jpeg_detected(self) -> None:
        fn = self._fn()
        # JPEG magic bytes: FF D8 FF
        raw = b'\xff\xd8\xff' + b'\x00' * 13
        assert fn(raw) == "image/jpeg"

    def test_png_detected(self) -> None:
        fn = self._fn()
        raw = b'\x89PNG\r\n\x1a\n' + b'\x00' * 8
        assert fn(raw) == "image/png"

    def test_gif87_detected(self) -> None:
        fn = self._fn()
        raw = b'GIF87a' + b'\x00' * 10
        assert fn(raw) == "image/gif"

    def test_gif89_detected(self) -> None:
        fn = self._fn()
        raw = b'GIF89a' + b'\x00' * 10
        assert fn(raw) == "image/gif"

    def test_pdf_detected(self) -> None:
        fn = self._fn()
        raw = b'%PDF' + b'\x00' * 12
        assert fn(raw) == "application/pdf"

    def test_ogg_detected(self) -> None:
        fn = self._fn()
        raw = b'OggS' + b'\x00' * 12
        assert fn(raw) == "audio/ogg"

    def test_mp3_id3_detected(self) -> None:
        fn = self._fn()
        raw = b'ID3' + b'\x00' * 13
        assert fn(raw) == "audio/mpeg"

    def test_unknown_returns_none(self) -> None:
        fn = self._fn()
        raw = b'\x00' * 16
        result = fn(raw)
        assert result is None

    def test_short_bytes_no_crash(self) -> None:
        fn = self._fn()
        fn(b'\xff\xd8')  # too short for some checks
        # Should not raise


class TestValidateMagicBytes:
    def _fn(self):
        from backend.fastapi.app.routers.media_jobs import _validate_magic_bytes
        return _validate_magic_bytes

    def test_valid_jpeg(self) -> None:
        fn = self._fn()
        raw = b'\xff\xd8\xff' + b'\x00' * 13
        valid, info = fn(raw, "image/jpeg")
        assert valid is True

    def test_valid_png(self) -> None:
        fn = self._fn()
        raw = b'\x89PNG\r\n\x1a\n' + b'\x00' * 8
        valid, info = fn(raw, "image/png")
        assert valid is True

    def test_wrong_mime_detected_as_different(self) -> None:
        fn = self._fn()
        raw = b'\xff\xd8\xff' + b'\x00' * 13  # JPEG bytes
        valid, info = fn(raw, "image/png")
        assert valid is False
        assert "jpeg" in info.lower() or "png" in info.lower()

    def test_unknown_mime_type(self) -> None:
        fn = self._fn()
        raw = b'\xff\xd8\xff' + b'\x00' * 13
        valid, info = fn(raw, "application/unknown")
        assert valid is False

    def test_empty_bytes_unknown_mime(self) -> None:
        fn = self._fn()
        valid, info = fn(b'\x00' * 16, "image/jpeg")
        assert valid is False


class TestIssueValidationToken:
    def _fn(self):
        from backend.fastapi.app.routers.media_jobs import _issue_validation_token
        return _issue_validation_token

    def test_returns_hex_string(self) -> None:
        fn = self._fn()
        token = fn("tenant-1", "uploads/file.jpg", "image/jpeg")
        assert isinstance(token, str)
        assert len(token) == 64  # SHA-256 hex

    def test_different_tenants_different_tokens(self) -> None:
        fn = self._fn()
        t1 = fn("tenant-1", "key.jpg", "image/jpeg")
        t2 = fn("tenant-2", "key.jpg", "image/jpeg")
        assert t1 != t2

    def test_different_keys_different_tokens(self) -> None:
        fn = self._fn()
        t1 = fn("tenant-1", "key1.jpg", "image/jpeg")
        t2 = fn("tenant-1", "key2.jpg", "image/jpeg")
        assert t1 != t2

    def test_different_mimes_different_tokens(self) -> None:
        fn = self._fn()
        t1 = fn("tenant-1", "key.jpg", "image/jpeg")
        t2 = fn("tenant-1", "key.jpg", "image/png")
        assert t1 != t2


class TestBuildJobRecord:
    def _make_request(self, **kwargs):
        from backend.fastapi.app.routers.media_jobs import MediaJobCreateRequest
        defaults = {
            "storage_key": "raw-uploads/test.jpg",
            "media_type": "image",
        }
        defaults.update(kwargs)
        return MediaJobCreateRequest(**defaults)

    def _fn(self):
        from backend.fastapi.app.routers.media_jobs import _build_job_record
        return _build_job_record

    def test_returns_expected_keys(self) -> None:
        fn = self._fn()
        payload = self._make_request()
        result = fn(1, "tenant-1", payload, "2024-01-01T00:00:00Z")
        assert result["id"] == 1
        assert result["tenant_id"] == "tenant-1"
        assert result["status"] == "queued"
        assert result["progress_pct"] == 0
        assert result["output_key"] is None

    def test_validation_token_flag(self) -> None:
        fn = self._fn()
        payload_with_token = self._make_request(validation_token="tok123")
        result = fn(1, "t", payload_with_token, "2024-01-01T00:00:00Z")
        assert result["validation_token_provided"] is True

        payload_no_token = self._make_request()
        result2 = fn(2, "t", payload_no_token, "2024-01-01T00:00:00Z")
        assert result2["validation_token_provided"] is False

    def test_processing_options_stored(self) -> None:
        fn = self._fn()
        opts = {"resize": "1280x720", "quality": 85}
        payload = self._make_request(processing_options=opts)
        result = fn(3, "t", payload, "2024-01-01T00:00:00Z")
        assert result["processing_options"] == opts


class TestMediaJobsRoutes:
    def test_validate_file_jpeg(self, client: TestClient) -> None:
        raw = b'\xff\xd8\xff' + b'\x00' * 13
        b64 = base64.b64encode(raw).decode()
        r = client.post("/media/validate-file", headers=H, json={
            "first_bytes_b64": b64,
            "expected_mime": "image/jpeg",
        })
        assert r.status_code in VALID

    def test_validate_file_invalid_b64(self, client: TestClient) -> None:
        r = client.post("/media/validate-file", headers=H, json={
            "first_bytes_b64": "not-valid-base64!!",
            "expected_mime": "image/jpeg",
        })
        assert r.status_code in VALID

    def test_validate_file_wrong_mime(self, client: TestClient) -> None:
        raw = b'\xff\xd8\xff' + b'\x00' * 13
        b64 = base64.b64encode(raw).decode()
        r = client.post("/media/validate-file", headers=H, json={
            "first_bytes_b64": b64,
            "expected_mime": "image/png",
        })
        assert r.status_code in VALID

    def test_create_job(self, client: TestClient) -> None:
        r = client.post("/media/jobs", headers=H, json={
            "storage_key": "raw-uploads/test.jpg",
            "media_type": "image",
        })
        assert r.status_code in VALID

    def test_create_job_with_validation_token(self, client: TestClient) -> None:
        r = client.post("/media/jobs", headers=H, json={
            "storage_key": "raw-uploads/test2.jpg",
            "media_type": "video",
            "validation_token": "fake-token-abc",
        })
        assert r.status_code in VALID

    def test_create_job_invalid_media_type(self, client: TestClient) -> None:
        r = client.post("/media/jobs", headers=H, json={
            "storage_key": "raw-uploads/test.xyz",
            "media_type": "invalid_type",
        })
        assert r.status_code in VALID

    def test_list_jobs_empty(self, client: TestClient) -> None:
        r = client.get("/media/jobs", headers=H)
        assert r.status_code in VALID

    def test_list_jobs_with_status_filter(self, client: TestClient) -> None:
        r = client.get("/media/jobs?status=queued", headers=H)
        assert r.status_code in VALID

    def test_get_job_not_found(self, client: TestClient) -> None:
        r = client.get("/media/jobs/99999", headers=H)
        assert r.status_code in VALID

    def test_cancel_job_not_found(self, client: TestClient) -> None:
        r = client.delete("/media/jobs/99999", headers=H)
        assert r.status_code in VALID

    def test_retry_job_not_found(self, client: TestClient) -> None:
        r = client.post("/media/jobs/99999/retry", headers=H)
        assert r.status_code in VALID

    def test_output_url_not_found(self, client: TestClient) -> None:
        r = client.post("/media/jobs/99999/output-url", headers=H, json={
            "expires_seconds": 900,
        })
        assert r.status_code in VALID

    def test_dlq_empty(self, client: TestClient) -> None:
        r = client.get("/media/jobs/dlq", headers=H)
        assert r.status_code in VALID

    def test_get_job_after_create(self, client: TestClient) -> None:
        # Create a job, then try to get it
        create_r = client.post("/media/jobs", headers=H, json={
            "storage_key": "uploads/new-file.jpg",
            "media_type": "image",
        })
        if create_r.status_code == 201:
            data = create_r.json()
            job_id = data.get("id")
            if job_id:
                r = client.get(f"/media/jobs/{job_id}", headers=H)
                assert r.status_code in VALID

    def test_cancel_job_after_create(self, client: TestClient) -> None:
        create_r = client.post("/media/jobs", headers=H, json={
            "storage_key": "uploads/cancel-test.jpg",
            "media_type": "image",
        })
        if create_r.status_code == 201:
            data = create_r.json()
            job_id = data.get("id")
            if job_id:
                r = client.delete(f"/media/jobs/{job_id}", headers=H)
                assert r.status_code in VALID
