"""Tests for pure helper functions in media_jobs.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import json

from backend.fastapi.app.routers.media_jobs import (
    MediaJobCreateRequest,
    _build_job_record,
    _detect_magic_mime,
    _issue_validation_token,
    _sse_message,
    _validate_magic_bytes,
)

# ─── _sse_message ─────────────────────────────────────────────────────────────

class TestSseMessage:
    def test_format(self):
        result = _sse_message("job_update", {"id": 1, "status": "done"})
        assert result.startswith("event: job_update\n")
        assert "data: " in result
        assert result.endswith("\n\n")

    def test_json_payload(self):
        payload = {"key": "value", "num": 42}
        result = _sse_message("test", payload)
        data_line = [line for line in result.split("\n") if line.startswith("data:")][0]
        parsed = json.loads(data_line[6:])
        assert parsed == payload


# ─── _detect_magic_mime ───────────────────────────────────────────────────────

class TestDetectMagicMime:
    def test_jpeg_magic_bytes(self):
        raw = b'\xff\xd8\xff' + b'\x00' * 20
        result = _detect_magic_mime(raw)
        assert result == "image/jpeg"

    def test_png_magic_bytes(self):
        raw = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20
        result = _detect_magic_mime(raw)
        assert result == "image/png"

    def test_pdf_magic_bytes(self):
        raw = b'%PDF' + b'-1.4 %' + b'\x00' * 20
        result = _detect_magic_mime(raw)
        assert result == "application/pdf"

    def test_unknown_returns_none(self):
        raw = b'\x00\x01\x02\x03' * 10
        result = _detect_magic_mime(raw)
        assert result is None

    def test_mp3_magic_bytes(self):
        raw = b'ID3' + b'\x00' * 20
        result = _detect_magic_mime(raw)
        assert result == "audio/mpeg"


# ─── _validate_magic_bytes ───────────────────────────────────────────────────

class TestValidateMagicBytes:
    def test_valid_jpeg(self):
        raw = b'\xff\xd8\xff' + b'\x00' * 20
        ok, mime = _validate_magic_bytes(raw, "image/jpeg")
        assert ok is True
        assert mime == "image/jpeg"

    def test_mismatch_returns_false(self):
        raw = b'\xff\xd8\xff' + b'\x00' * 20  # jpeg bytes
        ok, reason = _validate_magic_bytes(raw, "image/png")  # but claim png
        assert ok is False

    def test_unknown_claimed_mime(self):
        raw = b'\x00' * 20
        ok, reason = _validate_magic_bytes(raw, "text/html")
        assert ok is False

    def test_no_magic_match_for_claimed_mime(self):
        raw = b'\x00' * 20  # no magic bytes
        ok, reason = _validate_magic_bytes(raw, "image/jpeg")
        assert ok is False


# ─── _issue_validation_token ──────────────────────────────────────────────────

class TestIssueValidationToken:
    def test_returns_hex_string(self):
        token = _issue_validation_token("tenant1", "bucket/file.jpg", "image/jpeg")
        assert isinstance(token, str)
        assert len(token) == 64  # sha256 hex = 64 chars

    def test_deterministic_within_time_window(self):
        t1 = _issue_validation_token("tenant1", "key1", "image/jpeg")
        t2 = _issue_validation_token("tenant1", "key1", "image/jpeg")
        assert t1 == t2

    def test_different_tenants_different_tokens(self):
        t1 = _issue_validation_token("tenant1", "key1", "image/jpeg")
        t2 = _issue_validation_token("tenant2", "key1", "image/jpeg")
        assert t1 != t2


# ─── _build_job_record ────────────────────────────────────────────────────────

class TestBuildJobRecord:
    def get_payload(self):
        return MediaJobCreateRequest(
            storage_key="uploads/test.mp4",
            media_type="video",
            output_bucket="processed",
            processing_options={"quality": "high"},
            validation_token="some_token"
        )

    def test_basic_structure(self):
        payload = self.get_payload()
        result = _build_job_record(42, "tenant1", payload, "2024-01-01T00:00:00")
        assert result["id"] == 42
        assert result["tenant_id"] == "tenant1"
        assert result["status"] == "queued"
        assert result["progress_pct"] == 0

    def test_validation_token_presence(self):
        payload = self.get_payload()
        result = _build_job_record(1, "t1", payload, "2024-01-01")
        assert result["validation_token_provided"] is True

    def test_no_validation_token(self):
        payload = MediaJobCreateRequest(
            storage_key="uploads/test.jpg",
            media_type="image",
        )
        result = _build_job_record(1, "t1", payload, "2024-01-01")
        assert result["validation_token_provided"] is False

    def test_has_timestamps(self):
        payload = self.get_payload()
        result = _build_job_record(1, "t1", payload, "2024-01-01T00:00:00Z")
        assert result["created_at"] == "2024-01-01T00:00:00Z"
        assert result["updated_at"] == "2024-01-01T00:00:00Z"
        assert result["completed_at"] is None
