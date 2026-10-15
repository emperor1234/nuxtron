"""Focused media validation and disabled-job capability regression tests."""

from __future__ import annotations

import base64
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient


TENANT_ID = "media-job-capability-test"
HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": TENANT_ID}
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
PNG_BASE64 = base64.b64encode(PNG_BYTES).decode()


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestMagicByteHelpers:
    def test_supported_signatures_match_claimed_mime(self) -> None:
        from backend.fastapi.app.domains.content.media.services.processing import _validate_magic_bytes

        assert _validate_magic_bytes(PNG_BYTES, "image/png") == (True, "image/png")
        assert _validate_magic_bytes(b"%PDF" + b"\x00" * 12, "application/pdf") == (True, "application/pdf")

    def test_mime_mismatch_is_rejected(self) -> None:
        from backend.fastapi.app.domains.content.media.services.processing import _validate_magic_bytes

        valid, reason = _validate_magic_bytes(PNG_BYTES, "image/jpeg")
        assert valid is False
        assert "image/png" in reason or "Magic bytes match" in reason

    def test_unknown_bytes_and_mime_are_rejected(self) -> None:
        from backend.fastapi.app.domains.content.media.services.processing import _validate_magic_bytes

        valid, reason = _validate_magic_bytes(b"unrecognized bytes", "text/plain")
        assert valid is False
        assert "Unknown MIME type" in reason or "text/plain" in reason


class TestFileValidationEndpoint:
    def test_valid_png_returns_object_bound_token(self, client: TestClient) -> None:
        response = client.post(
            "/media/validate-file",
            headers=HEADERS,
            json={
                "first_bytes_b64": PNG_BASE64,
                "expected_mime": "image/png",
                "storage_key": f"raw-input/{TENANT_ID}/image.png",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["validation_token"]

    def test_mismatched_magic_bytes_are_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/media/validate-file",
            headers=HEADERS,
            json={"first_bytes_b64": PNG_BASE64, "expected_mime": "image/jpeg"},
        )
        assert response.status_code == 422

    def test_invalid_base64_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/media/validate-file",
            headers=HEADERS,
            json={"first_bytes_b64": "!!!not-base64!!!", "expected_mime": "image/png"},
        )
        assert response.status_code == 422


_JOB_ENDPOINTS = [
    ("post", "/media/jobs", {"storage_key": f"raw-input/{TENANT_ID}/image.png", "media_type": "image"}),
    ("get", "/media/jobs", None),
    ("get", "/media/jobs/123", None),
    ("delete", "/media/jobs/123", None),
    ("post", "/media/jobs/123/retry", None),
    ("post", "/media/jobs/123/output-url", {"expires_seconds": 300}),
    ("get", "/media/jobs/123/audit", None),
    ("get", "/media/jobs/dlq", None),
    ("get", "/media/jobs/stats", None),
    ("get", "/media/jobs/123/stream?api_key=test-api-key&tenant_id=" + TENANT_ID, None),
    (
        "post",
        "/media/sandbox/dispatch",
        {
            "storage_key": f"raw-input/{TENANT_ID}/video.mp4",
            "media_type": "video",
            "provider": "mux",
            "operation": "transcode",
        },
    ),
]


@pytest.mark.parametrize(("method", "path", "payload"), _JOB_ENDPOINTS)
def test_media_job_endpoints_fail_closed_without_durable_adapters(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    """No job API may return success or mutate process-local media state."""
    from backend.fastapi.app import memory_stores

    jobs_before = len(memory_stores.media_jobs)
    request = getattr(client, method)
    kwargs: dict[str, object] = {"headers": HEADERS}
    if payload is not None:
        kwargs["json"] = payload
    response = request(path, **kwargs)

    assert response.status_code == 501, response.text
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
    assert len(memory_stores.media_jobs) == jobs_before
