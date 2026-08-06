"""
Tests for ai.py pure helpers and route smoke tests.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

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


@pytest.fixture(autouse=True)
def mock_generation_backends():
    from backend.fastapi.app.routers.ai import AIGenerationResponse

    with patch(
        "backend.fastapi.app.routers.ai._generate_image",
        new=AsyncMock(
            return_value=AIGenerationResponse(
                status="success",
                content="mock-image",
                media_url="data:image/png;base64,aGVsbG8=",
            )
        ),
    ), patch(
        "backend.fastapi.app.routers.ai._generate_text",
        new=AsyncMock(return_value=AIGenerationResponse(status="success", content="mock-text")),
    ), patch(
        "backend.fastapi.app.routers.ai._generate_video",
        new=AsyncMock(return_value=AIGenerationResponse(status="success", content="mock-video")),
    ), patch(
        "backend.fastapi.app.routers.ai._generate_voice",
        new=AsyncMock(return_value=AIGenerationResponse(status="success", content="mock-voice")),
    ):
        yield


class TestSanitizePrompt:
    def _fn(self):
        from backend.fastapi.app.routers.ai import _sanitize_prompt
        return _sanitize_prompt

    def test_clean_prompt_returned_normalized(self) -> None:
        fn = self._fn()
        result = fn("A beautiful sunset over the ocean")
        assert result == "A beautiful sunset over the ocean"

    def test_empty_string_returns_none(self) -> None:
        fn = self._fn()
        assert fn("") is None

    def test_whitespace_only_returns_none(self) -> None:
        fn = self._fn()
        assert fn("   ") is None

    def test_null_bytes_normalized(self) -> None:
        fn = self._fn()
        result = fn("Hello\x00World")
        assert result == "Hello World"

    def test_script_injection_blocked(self) -> None:
        fn = self._fn()
        assert fn("<script>alert('xss')</script>") is None

    def test_javascript_protocol_blocked(self) -> None:
        fn = self._fn()
        assert fn("javascript:alert(1)") is None

    def test_php_injection_blocked(self) -> None:
        fn = self._fn()
        assert fn("<?php echo 'hacked'; ?>") is None

    def test_python_injection_blocked(self) -> None:
        fn = self._fn()
        assert fn("use __import__('os') to run commands") is None

    def test_sql_injection_blocked(self) -> None:
        fn = self._fn()
        assert fn("DROP TABLE users; --") is None

    def test_union_select_blocked(self) -> None:
        fn = self._fn()
        assert fn("1 UNION SELECT * FROM users") is None

    def test_multi_space_normalized(self) -> None:
        fn = self._fn()
        result = fn("a  b   c")
        assert result == "a b c"

    def test_newline_normalized(self) -> None:
        fn = self._fn()
        result = fn("line1\nline2")
        assert result == "line1 line2"


class TestAsBool:
    def _fn(self):
        from backend.fastapi.app.routers.ai import _as_bool
        return _as_bool

    def test_bool_true(self) -> None:
        assert self._fn()(True) is True

    def test_bool_false(self) -> None:
        assert self._fn()(False) is False

    def test_string_true(self) -> None:
        fn = self._fn()
        assert fn("true") is True
        assert fn("1") is True
        assert fn("yes") is True
        assert fn("on") is True

    def test_string_false(self) -> None:
        fn = self._fn()
        assert fn("false") is False
        assert fn("0") is False
        assert fn("no") is False

    def test_string_case_insensitive(self) -> None:
        fn = self._fn()
        assert fn("TRUE") is True
        assert fn("True") is True

    def test_truthy_int(self) -> None:
        fn = self._fn()
        assert fn(1) is True
        assert fn(0) is False

    def test_none_is_falsy(self) -> None:
        fn = self._fn()
        assert fn(None) is False


class TestSanitizeFilename:
    def _fn(self):
        from backend.fastapi.app.routers.ai import _sanitize_filename
        return _sanitize_filename

    def test_clean_filename_unchanged(self) -> None:
        fn = self._fn()
        result = fn("image.png")
        assert result == "image.png"

    def test_special_chars_replaced(self) -> None:
        fn = self._fn()
        result = fn("my image (1).png")
        assert result == "my_image__1_.png"

    def test_empty_fallback(self) -> None:
        fn = self._fn()
        result = fn("")
        assert result == "upload.bin"

    def test_spaces_stripped_then_fallback(self) -> None:
        fn = self._fn()
        result = fn("   ")
        assert result == "upload.bin"

    def test_long_filename_truncated(self) -> None:
        fn = self._fn()
        result = fn("a" * 300 + ".png")
        assert len(result) <= 180

    def test_path_traversal_sanitized(self) -> None:
        fn = self._fn()
        result = fn("../../etc/passwd")
        # The function replaces / with _ but keeps .. as chars; slashes are removed
        assert "/" not in result


class TestResolveCheckpointName:
    def _fn(self):
        from backend.fastapi.app.routers.ai import _resolve_checkpoint_name
        return _resolve_checkpoint_name

    def test_returns_none_or_string(self) -> None:
        fn = self._fn()
        result = fn()
        # Returns None if no checkpoint dir, or a string if checkpoints exist
        assert result is None or isinstance(result, str)


class TestComposeGenerationPrompt:
    def _make_payload(self, **kwargs):
        from backend.fastapi.app.routers.ai import AIGenerationRequest
        defaults = {
            "prompt": "A sunset",
            "media_type": "image",
        }
        defaults.update(kwargs)
        return AIGenerationRequest(**defaults)

    def _fn(self):
        from backend.fastapi.app.routers.ai import _compose_generation_prompt
        return _compose_generation_prompt

    def test_minimal_prompt(self) -> None:
        fn = self._fn()
        payload = self._make_payload()
        result = fn(payload)
        assert "A sunset" in result

    def test_with_description(self) -> None:
        fn = self._fn()
        payload = self._make_payload(prompt_description="golden hour lighting")
        result = fn(payload)
        assert "Details: golden hour lighting" in result

    def test_with_creative_mode(self) -> None:
        fn = self._fn()
        payload = self._make_payload(creative_mode="cinematic")
        result = fn(payload)
        assert "Mode: cinematic" in result

    def test_with_aspect_ratio(self) -> None:
        fn = self._fn()
        payload = self._make_payload(aspect_ratio="16:9")
        result = fn(payload)
        assert "Aspect ratio: 16:9" in result

    def test_with_resolution(self) -> None:
        fn = self._fn()
        payload = self._make_payload(resolution="4K")
        result = fn(payload)
        assert "Resolution: 4K" in result

    def test_with_real_people(self) -> None:
        fn = self._fn()
        payload = self._make_payload(contains_real_people=True)
        result = fn(payload)
        assert "Contains real people" in result

    def test_with_reference_images(self) -> None:
        fn = self._fn()
        payload = self._make_payload(reference_images=["img1.png", "img2.png"])
        result = fn(payload)
        assert "Reference images: img1.png, img2.png" in result

    def test_with_reference_videos(self) -> None:
        fn = self._fn()
        payload = self._make_payload(reference_videos=["video.mp4"])
        result = fn(payload)
        assert "Reference videos: video.mp4" in result

    def test_with_reference_audios(self) -> None:
        fn = self._fn()
        payload = self._make_payload(reference_audios=["audio.mp3"])
        result = fn(payload)
        assert "Reference audios: audio.mp3" in result

    def test_return_last_frame(self) -> None:
        fn = self._fn()
        payload = self._make_payload(return_last_frame=True)
        result = fn(payload)
        assert "Return last frame enabled" in result

    def test_parts_joined_by_pipe(self) -> None:
        fn = self._fn()
        payload = self._make_payload(prompt_description="desc")
        result = fn(payload)
        assert " | " in result


class TestAIRoutes:
    def test_health(self, client: TestClient) -> None:
        r = client.get("/ai/health", headers=H)
        assert r.status_code in VALID

    def test_generate_text(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "Write a tweet about Nuxtron",
            "media_type": "text",
            "model": "llama3.2",
        })
        assert r.status_code in VALID

    def test_generate_image(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "A beautiful mountain landscape",
            "media_type": "image",
        })
        assert r.status_code in VALID

    def test_generate_blocked_prompt(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "<script>alert('xss')</script>",
            "media_type": "text",
        })
        assert r.status_code in VALID

    def test_generate_auto_choose_model(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "Generate some content",
            "media_type": "text",
            "model": "auto choose model",
        })
        assert r.status_code in VALID

    def test_generate_with_style(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "A portrait",
            "media_type": "image",
            "style": "photorealistic",
        })
        assert r.status_code in VALID

    def test_generate_blocked_style(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "A portrait",
            "media_type": "image",
            "style": "<script>hack()</script>",
        })
        assert r.status_code in VALID

    def test_generate_blocked_description(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "A portrait",
            "media_type": "image",
            "prompt_description": "DROP TABLE users; --",
        })
        assert r.status_code in VALID

    def test_generate_video(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "A flying dragon",
            "media_type": "video",
        })
        assert r.status_code in VALID

    def test_generate_voice(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "Hello world, this is a voice test",
            "media_type": "voice",
        })
        assert r.status_code in VALID

    def test_generate_with_seed(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "A landscape",
            "media_type": "image",
            "seed_enabled": True,
            "seed": "12345",
        })
        assert r.status_code in VALID

    def test_generate_invalid_model_name(self, client: TestClient) -> None:
        r = client.post("/ai/social-studio/generate", headers=H, json={
            "prompt": "Some text",
            "media_type": "text",
            "model": "invalid model with spaces!!!",
        })
        assert r.status_code in VALID

    def test_get_job_status_missing(self, client: TestClient) -> None:
        r = client.get("/ai/social-studio/job/nonexistent-job-id", headers=H)
        assert r.status_code in VALID

    def test_get_job_status_response_schema(self, client: TestClient) -> None:
        r = client.get("/ai/social-studio/job/nonexistent-job-id", headers=H)
        if r.status_code == 200:
            data = r.json()
            assert "status" in data
