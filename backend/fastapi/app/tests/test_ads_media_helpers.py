"""Tests for the media-library asset tagging helper."""
from __future__ import annotations

import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.routers.media_library import _ai_tag_asset


class TestAiTagAsset:
    def test_always_includes_type_tag(self) -> None:
        tags = _ai_tag_asset("hero-banner.jpg", "image")
        assert "auto:image" in tags

    def test_extracts_words_from_filename(self) -> None:
        tags = _ai_tag_asset("summer-sale-banner.jpg", "image")
        assert "auto:summer" in tags
        assert "auto:sale" in tags
        assert "auto:banner" in tags

    def test_ignores_short_words(self) -> None:
        tags = _ai_tag_asset("a-b-longword.png", "image")
        assert "auto:a" not in tags
        assert "auto:b" not in tags

    def test_caps_at_8_tags(self) -> None:
        tags = _ai_tag_asset("very-long-summer-sale-banner-hero-image-test.jpg", "image")
        assert len(tags) <= 8

    def test_underscore_replaced(self) -> None:
        tags = _ai_tag_asset("brand_hero_shot.jpg", "image")
        assert "auto:brand" in tags
        assert "auto:hero" in tags

    def test_video_type_tag(self) -> None:
        tags = _ai_tag_asset("promo-video.mp4", "video")
        assert "auto:video" in tags

    def test_returns_list(self) -> None:
        result = _ai_tag_asset("test.jpg", "image")
        assert isinstance(result, list)
