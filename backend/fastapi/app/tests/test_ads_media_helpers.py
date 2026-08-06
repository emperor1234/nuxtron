"""Tests for pure helper functions in ads_control_tower.py and media_library.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.routers.ads_control_tower import (
    _platform_oauth_url,
    _seed_connector,
)
from backend.fastapi.app.routers.media_library import _ai_tag_asset

# ─── ads_control_tower: _platform_oauth_url ──────────────────────────────────

class TestPlatformOauthUrl:
    def test_known_platform_google_ads(self):
        url = _platform_oauth_url("google_ads")
        assert "google" in url.lower()
        assert url.startswith("https://")

    def test_known_platform_microsoft(self):
        url = _platform_oauth_url("microsoft_ads")
        assert "microsoft" in url.lower()

    def test_known_platform_amazon(self):
        url = _platform_oauth_url("amazon_ads")
        assert "amazon" in url.lower()

    def test_unknown_platform_returns_fallback(self):
        url = _platform_oauth_url("unknown_platform_xyz")
        assert url == "https://example.com/oauth"

    def test_returns_string(self):
        result = _platform_oauth_url("youtube_ads")
        assert isinstance(result, str)


# ─── ads_control_tower: _seed_connector ──────────────────────────────────────

class TestSeedConnector:
    def test_basic_structure(self):
        result = _seed_connector("tenant-1", "google_ads")
        assert result["tenant_id"] == "tenant-1"
        assert result["platform"] == "google_ads"
        assert result["status"] == "disconnected"
        assert result["connected"] is False

    def test_has_uuid_id(self):
        import uuid
        result = _seed_connector("t1", "meta_ads")
        try:
            uuid.UUID(result["id"])
            valid = True
        except ValueError:
            valid = False
        assert valid

    def test_financial_fields_zero(self):
        result = _seed_connector("t1", "google_ads")
        assert result["credit_total"] == 0.0
        assert result["credit_remaining"] == 0.0

    def test_has_timestamps(self):
        result = _seed_connector("t1", "google_ads")
        assert "created_at" in result
        assert "updated_at" in result

    def test_unique_ids_per_call(self):
        r1 = _seed_connector("t1", "google_ads")
        r2 = _seed_connector("t1", "google_ads")
        assert r1["id"] != r2["id"]


# ─── media_library: _ai_tag_asset ────────────────────────────────────────────

class TestAiTagAsset:
    def test_always_includes_type_tag(self):
        tags = _ai_tag_asset("hero-banner.jpg", "image")
        assert "auto:image" in tags

    def test_extracts_words_from_filename(self):
        tags = _ai_tag_asset("summer-sale-banner.jpg", "image")
        assert "auto:summer" in tags
        assert "auto:sale" in tags
        assert "auto:banner" in tags

    def test_ignores_short_words(self):
        tags = _ai_tag_asset("a-b-longword.png", "image")
        # 'a' and 'b' are too short (< 3 chars)
        assert "auto:a" not in tags
        assert "auto:b" not in tags

    def test_caps_at_8_tags(self):
        # Long filename with many words
        tags = _ai_tag_asset("very-long-summer-sale-banner-hero-image-test.jpg", "image")
        assert len(tags) <= 8

    def test_underscore_replaced(self):
        tags = _ai_tag_asset("brand_hero_shot.jpg", "image")
        assert "auto:brand" in tags
        assert "auto:hero" in tags

    def test_video_type_tag(self):
        tags = _ai_tag_asset("promo-video.mp4", "video")
        assert "auto:video" in tags

    def test_returns_list(self):
        result = _ai_tag_asset("test.jpg", "image")
        assert isinstance(result, list)
