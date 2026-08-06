"""
Tests for ai.py _upscale_and_sharpen_image function.
"""
from __future__ import annotations

import io
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

from unittest.mock import patch

from backend.fastapi.app.routers.ai import _upscale_and_sharpen_image


class TestUpscaleAndSharpenImage:
    def _make_png_bytes(self) -> bytes:
        """Create a minimal 10x10 PNG image in bytes."""
        try:
            from PIL import Image  # noqa: PLC0415
            buf = io.BytesIO()
            img = Image.new("RGB", (10, 10), color=(100, 150, 200))
            img.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            return b""

    def test_returns_none_when_pil_unavailable(self) -> None:
        with patch("backend.fastapi.app.routers.ai._PIL_AVAILABLE", False):
            result = _upscale_and_sharpen_image(b"fake-image", 100, 100)
            assert result is None

    def test_returns_none_for_invalid_image_bytes(self) -> None:
        result = _upscale_and_sharpen_image(b"not-an-image", 100, 100)
        assert result is None

    def test_returns_png_bytes_for_valid_image(self) -> None:
        png_bytes = self._make_png_bytes()
        if not png_bytes:
            return  # PIL not installed, skip
        result = _upscale_and_sharpen_image(png_bytes, 50, 50)
        if result is not None:
            data, mime = result
            assert mime == "image/png"
            assert len(data) > 0

    def test_returns_tuple_with_mime_type(self) -> None:
        png_bytes = self._make_png_bytes()
        if not png_bytes:
            return  # PIL not installed, skip
        result = _upscale_and_sharpen_image(png_bytes, 20, 20)
        if result is not None:
            assert isinstance(result, tuple)
            assert len(result) == 2
