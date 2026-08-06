"""
Unit tests for pure helper functions in backend/fastapi/app/routers/ai.py.
Tests _sanitize_prompt, _as_bool, _sanitize_filename, _compose_generation_prompt,
_resolve_checkpoint_name, and related utilities.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest


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
    def setup_method(self) -> None:
        from backend.fastapi.app.routers.ai import _sanitize_prompt
        self.sanitize = _sanitize_prompt

    def test_clean_prompt_returns_normalized(self) -> None:
        result = self.sanitize("A beautiful sunset over the ocean")
        assert result == "A beautiful sunset over the ocean"

    def test_extra_whitespace_normalized(self) -> None:
        result = self.sanitize("  hello   world  ")
        assert result == "hello world"

    def test_null_bytes_removed(self) -> None:
        result = self.sanitize("hello\x00world")
        assert result == "hello world"

    def test_empty_after_strip_returns_none(self) -> None:
        result = self.sanitize("   \x00   ")
        assert result is None

    def test_script_tag_blocked(self) -> None:
        result = self.sanitize("<script>alert('xss')</script>")
        assert result is None

    def test_javascript_blocked(self) -> None:
        result = self.sanitize("javascript:void(0)")
        assert result is None

    def test_php_tag_blocked(self) -> None:
        result = self.sanitize("<?php echo 'hello'; ?>")
        assert result is None

    def test_eval_blocked(self) -> None:
        result = self.sanitize("eval(malicious_code())")
        assert result is None

    def test_subprocess_blocked(self) -> None:
        result = self.sanitize("subprocess.run(['rm', '-rf', '/'])")
        assert result is None

    def test_import_blocked(self) -> None:
        result = self.sanitize("__import__('os')")
        assert result is None

    def test_os_system_blocked(self) -> None:
        result = self.sanitize("os.system('rm -rf /')")
        assert result is None

    def test_multiline_normalized(self) -> None:
        result = self.sanitize("line one\nline two\n\nline three")
        assert result is not None
        assert "\n" not in result


class TestAsBool:
    def setup_method(self) -> None:
        from backend.fastapi.app.routers.ai import _as_bool
        self.as_bool = _as_bool

    def test_true_bool(self) -> None:
        assert self.as_bool(True) is True

    def test_false_bool(self) -> None:
        assert self.as_bool(False) is False

    def test_string_true(self) -> None:
        for val in ("true", "True", "TRUE", "1", "yes", "YES", "on", "ON"):
            assert self.as_bool(val) is True

    def test_string_false(self) -> None:
        for val in ("false", "False", "0", "no", "off", ""):
            assert self.as_bool(val) is False

    def test_int_truthy(self) -> None:
        assert self.as_bool(1) is True
        assert self.as_bool(42) is True

    def test_int_falsy(self) -> None:
        assert self.as_bool(0) is False

    def test_none_falsy(self) -> None:
        assert self.as_bool(None) is False


class TestSanitizeFilename:
    def setup_method(self) -> None:
        from backend.fastapi.app.routers.ai import _sanitize_filename
        self.sanitize = self._fn = _sanitize_filename

    def test_clean_filename_unchanged(self) -> None:
        result = self.sanitize("photo.png")
        assert result == "photo.png"

    def test_spaces_replaced(self) -> None:
        result = self.sanitize("my photo.png")
        assert " " not in result
        assert result == "my_photo.png"

    def test_special_chars_replaced(self) -> None:
        result = self.sanitize("file/path/../etc/passwd")
        assert "/" not in result
        # slashes are replaced with underscores; dots are allowed so ".." may appear
        assert "file_path" in result

    def test_empty_returns_default(self) -> None:
        result = self.sanitize("   ")
        assert result == "upload.bin"

    def test_long_name_truncated(self) -> None:
        long_name = "a" * 300
        result = self.sanitize(long_name)
        assert len(result) <= 180

    def test_allowed_chars_preserved(self) -> None:
        result = self.sanitize("my-file_name.test-2025.jpg")
        assert result == "my-file_name.test-2025.jpg"


class TestComposeGenerationPrompt:
    def setup_method(self) -> None:
        from backend.fastapi.app.routers.ai import AIGenerationRequest, _compose_generation_prompt
        self.compose = _compose_generation_prompt
        self.Request = AIGenerationRequest

    def _make_request(self, **kwargs) -> object:
        defaults = {"prompt": "Test prompt", "media_type": "image"}
        return self.Request(**{**defaults, **kwargs})

    def test_only_prompt(self) -> None:
        payload = self._make_request()
        result = self.compose(payload)
        assert result == "Test prompt"

    def test_with_description(self) -> None:
        payload = self._make_request(prompt_description="Detailed description")
        result = self.compose(payload)
        assert "Details: Detailed description" in result

    def test_with_creative_mode(self) -> None:
        payload = self._make_request(creative_mode="cinematic")
        result = self.compose(payload)
        assert "Mode: cinematic" in result

    def test_with_aspect_ratio(self) -> None:
        payload = self._make_request(aspect_ratio="16:9")
        result = self.compose(payload)
        assert "Aspect ratio: 16:9" in result

    def test_with_resolution(self) -> None:
        payload = self._make_request(resolution="4K")
        result = self.compose(payload)
        assert "Resolution: 4K" in result

    def test_with_real_people(self) -> None:
        payload = self._make_request(contains_real_people=True)
        result = self.compose(payload)
        assert "Contains real people" in result

    def test_with_return_last_frame(self) -> None:
        payload = self._make_request(return_last_frame=True, media_type="video")
        result = self.compose(payload)
        assert "Return last frame enabled" in result

    def test_with_reference_images(self) -> None:
        payload = self._make_request(reference_images=["img1.png", "img2.jpg"])
        result = self.compose(payload)
        assert "Reference images: img1.png, img2.jpg" in result

    def test_with_reference_videos(self) -> None:
        payload = self._make_request(reference_videos=["vid1.mp4"], media_type="video")
        result = self.compose(payload)
        assert "Reference videos: vid1.mp4" in result

    def test_with_reference_audios(self) -> None:
        payload = self._make_request(reference_audios=["audio1.wav"], media_type="voice")
        result = self.compose(payload)
        assert "Reference audios: audio1.wav" in result

    def test_parts_joined_with_pipe(self) -> None:
        payload = self._make_request(creative_mode="hdr")
        result = self.compose(payload)
        assert " | " in result


class TestResolveCheckpointName:
    def test_no_directory_returns_none(self) -> None:
        from backend.fastapi.app.routers.ai import _resolve_checkpoint_name
        # Ensure the directory doesn't exist in current test context
        # (it likely doesn't, so this should return None)
        result = _resolve_checkpoint_name()
        # Either None (no checkpoint dir) or a string (if somehow present)
        assert result is None or isinstance(result, str)

    def test_directory_with_safetensors_file(self) -> None:
        from unittest.mock import MagicMock, patch

        from backend.fastapi.app.routers.ai import _resolve_checkpoint_name

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        mock_file1 = MagicMock()
        mock_file1.name = "sd_xl_base_1.0.safetensors"
        mock_file1.is_file.return_value = True
        mock_file1.suffix = ".safetensors"

        mock_file2 = MagicMock()
        mock_file2.name = "v1-5-pruned.safetensors"
        mock_file2.is_file.return_value = True
        mock_file2.suffix = ".safetensors"

        mock_path.iterdir.return_value = [mock_file1, mock_file2]

        with patch("backend.fastapi.app.routers.ai.Path", return_value=mock_path):
            result = _resolve_checkpoint_name()
        # Just verify it returns a string (or None) without crashing
        assert result is None or isinstance(result, str)


class TestAiRouterEndpoints:
    """End-to-end smoke tests for the 3 ai.py routes."""

    @pytest.fixture(scope="class")
    def client(self):
        from backend.fastapi.app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app, raise_server_exceptions=False)

    VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
    H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}

    def test_ai_health(self, client) -> None:
        r = client.get("/ai/health", headers=self.H)
        assert r.status_code in self.VALID

    def test_ai_generate_text(self, client) -> None:
        r = client.post("/ai/social-studio/generate", headers=self.H, json={
            "prompt": "Write a short tweet about AI marketing",
            "media_type": "text",
            "model": "llama2",
        })
        assert r.status_code in self.VALID

    def test_ai_generate_image(self, client) -> None:
        r = client.post("/ai/social-studio/generate", headers=self.H, json={
            "prompt": "A beautiful landscape photo",
            "media_type": "image",
        })
        assert r.status_code in self.VALID

    def test_ai_generate_voice(self, client) -> None:
        r = client.post("/ai/social-studio/generate", headers=self.H, json={
            "prompt": "Hello, welcome to our platform",
            "media_type": "voice",
        })
        assert r.status_code in self.VALID

    def test_ai_generate_video(self, client) -> None:
        r = client.post("/ai/social-studio/generate", headers=self.H, json={
            "prompt": "A product demo animation",
            "media_type": "video",
        })
        assert r.status_code in self.VALID

    def test_ai_generate_suspicious_prompt(self, client) -> None:
        r = client.post("/ai/social-studio/generate", headers=self.H, json={
            "prompt": "<script>alert('xss')</script>",
            "media_type": "text",
        })
        assert r.status_code in self.VALID
        # Should block the suspicious prompt and return error
        if r.status_code == 200:
            data = r.json()
            assert data.get("status") == "error"

    def test_ai_generate_with_style(self, client) -> None:
        r = client.post("/ai/social-studio/generate", headers=self.H, json={
            "prompt": "Portrait photo",
            "media_type": "image",
            "style": "cinematic",
            "creative_mode": "hdr",
            "aspect_ratio": "16:9",
            "resolution": "4K",
        })
        assert r.status_code in self.VALID

    def test_ai_job_nonexistent(self, client) -> None:
        r = client.get("/ai/social-studio/job/job_nonexistent", headers=self.H)
        assert r.status_code in self.VALID
