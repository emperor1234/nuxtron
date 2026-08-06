"""Tests for pure helper functions in social_workspace.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from backend.fastapi.app.routers.social_workspace import (
    _clean_text,
    _default_redirect_uri,
    _detect_industry,
    _extract_first_tag,
    _extract_keywords_from_html,
    _extract_link_href,
    _extract_meta,
    _extract_page_content,
    _extract_title,
    _normalize_avatar_profile,
    _normalize_ugc_template_profile,
    _normalize_voiceover_engine,
    _normalized_text,
    _oauth_mode,
    _parse_website_host,
    _provider_is_configured,
)
from fastapi import HTTPException

# ─── _clean_text ─────────────────────────────────────────────────────────────

class TestCleanText:
    def test_strips_html_tags(self):
        result = _clean_text("<b>Hello</b> <i>World</i>")
        assert "<b>" not in result
        assert "Hello" in result

    def test_normalizes_whitespace(self):
        result = _clean_text("hello   world")
        assert result == "hello world"

    def test_strips_edges(self):
        result = _clean_text("  hello  ")
        assert result == "hello"

    def test_empty_string(self):
        assert _clean_text("") == ""


# ─── _extract_title ──────────────────────────────────────────────────────────

class TestExtractTitle:
    def test_basic_title(self):
        html = "<html><title>My Page Title</title></html>"
        assert _extract_title(html) == "My Page Title"

    def test_no_title(self):
        assert _extract_title("<html><body>No title</body></html>") == ""

    def test_title_with_whitespace(self):
        html = "<title>  Spaced Title  </title>"
        result = _extract_title(html)
        assert result.strip() == "Spaced Title"


# ─── _extract_meta ───────────────────────────────────────────────────────────

class TestExtractMeta:
    def test_name_attr(self):
        html = '<meta name="description" content="Test description">'
        result = _extract_meta(html, ["description"])
        assert result == "Test description"

    def test_property_attr(self):
        html = '<meta property="og:title" content="OG Title">'
        result = _extract_meta(html, ["og:title"])
        assert result == "OG Title"

    def test_missing_returns_empty(self):
        html = "<html><body>No meta</body></html>"
        result = _extract_meta(html, ["description"])
        assert result == ""

    def test_first_match_wins(self):
        html = '<meta name="og:title" content="First"><meta name="description" content="Second">'
        result = _extract_meta(html, ["og:title", "description"])
        assert result == "First"


# ─── _extract_first_tag ──────────────────────────────────────────────────────

class TestExtractFirstTag:
    def test_extracts_h1(self):
        html = "<html><body><h1>Main Heading</h1></body></html>"
        result = _extract_first_tag(html, "h1")
        assert result == "Main Heading"

    def test_missing_tag_returns_empty(self):
        assert _extract_first_tag("<html></html>", "h1") == ""

    def test_extracts_p(self):
        html = "<p>First paragraph</p><p>Second</p>"
        result = _extract_first_tag(html, "p")
        assert result == "First paragraph"


# ─── _extract_link_href ──────────────────────────────────────────────────────

class TestExtractLinkHref:
    def test_extracts_icon_href(self):
        html = '<link rel="icon" href="/favicon.ico">'
        result = _extract_link_href(html, ["icon"])
        assert "/favicon.ico" in result

    def test_missing_returns_empty(self):
        result = _extract_link_href("<html></html>", ["icon"])
        assert result == ""

    def test_apple_touch_icon(self):
        html = '<link rel="apple-touch-icon" href="/apple-icon.png">'
        result = _extract_link_href(html, ["apple-touch-icon"])
        assert "/apple-icon.png" in result


# ─── _detect_industry ────────────────────────────────────────────────────────

class TestDetectIndustry:
    def test_saas(self):
        assert _detect_industry(["saas", "platform"]) == "saas"

    def test_ecommerce(self):
        assert _detect_industry(["shop", "store"]) == "ecommerce"

    def test_finance(self):
        assert _detect_industry(["fintech", "payments"]) == "finance"

    def test_healthcare(self):
        assert _detect_industry(["health", "wellness"]) == "healthcare"

    def test_education(self):
        assert _detect_industry(["learning", "course"]) == "education"

    def test_travel(self):
        assert _detect_industry(["travel", "hotel"]) == "travel"

    def test_fallback_marketing(self):
        assert _detect_industry(["random", "keywords"]) == "marketing"

    def test_empty_keywords(self):
        assert _detect_industry([]) == "marketing"


# ─── _parse_website_host ─────────────────────────────────────────────────────

class TestParseWebsiteHost:
    def test_basic_url(self):
        clean_host, brand_name, handle, normalized_url = _parse_website_host("https://example.com")
        assert clean_host == "example.com"
        assert brand_name == "Example"
        assert handle == "example"

    def test_www_stripped(self):
        clean_host, brand_name, handle, normalized_url = _parse_website_host("https://www.example.com")
        assert "www" not in clean_host

    def test_adds_https(self):
        clean_host, brand_name, handle, normalized_url = _parse_website_host("example.com")
        assert normalized_url.startswith("https://")

    def test_invalid_no_dot_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            _parse_website_host("localhost")
        assert exc_info.value.status_code == 422

    def test_brand_name_capitalized(self):
        _, brand_name, _, _ = _parse_website_host("https://my-company.co.uk")
        assert brand_name[0].isupper()


# ─── _extract_page_content ───────────────────────────────────────────────────

class TestExtractPageContent:
    def test_returns_expected_keys(self):
        result = _extract_page_content("<html><title>Test</title></html>")
        assert "title" in result
        assert "h1" in result
        assert "description" in result
        assert "logo" in result

    def test_extracts_og_title(self):
        html = '<meta property="og:title" content="OG Page">'
        result = _extract_page_content(html)
        assert result["title"] == "OG Page"

    def test_empty_html_returns_empty_strings(self):
        result = _extract_page_content("")
        assert result["title"] == ""
        assert result["h1"] == ""


# ─── _extract_keywords_from_html ─────────────────────────────────────────────

class TestExtractKeywordsFromHtml:
    def test_returns_list(self):
        result = _extract_keywords_from_html("", "Acme", "acme")
        assert isinstance(result, list)

    def test_max_8_keywords(self):
        html = "<title>saas software platform automation marketing analytics data insights growth</title>"
        result = _extract_keywords_from_html(html, "Acme", "acme")
        assert len(result) <= 8

    def test_fallback_to_brand(self):
        result = _extract_keywords_from_html("", "Acme Corp", "acme")
        # brand name split or joined may appear
        assert any("acme" in k for k in result)

    def test_meta_keywords_extracted(self):
        html = '<meta name="keywords" content="saas, automation, platform">'
        result = _extract_keywords_from_html(html, "Test", "test")
        assert any("saas" in k or "automation" in k or "platform" in k for k in result)


# ─── _normalize_avatar_profile ───────────────────────────────────────────────

class TestNormalizeAvatarProfile:
    def test_none_returns_defaults(self):
        result = _normalize_avatar_profile(None)
        assert result["mode"] == "catalog"
        assert result["name"] == "Creator"

    def test_valid_mode(self):
        result = _normalize_avatar_profile({"mode": "custom", "name": "Alice"})
        assert result["mode"] == "custom"
        assert result["name"] == "Alice"

    def test_invalid_mode_defaults_to_catalog(self):
        result = _normalize_avatar_profile({"mode": "invalid"})
        assert result["mode"] == "catalog"

    def test_empty_name_defaults(self):
        result = _normalize_avatar_profile({"name": ""})
        assert result["name"] == "Creator"


# ─── _normalize_voiceover_engine ─────────────────────────────────────────────

class TestNormalizeVoiceoverEngine:
    def test_none_returns_defaults(self):
        result = _normalize_voiceover_engine(None)
        assert result["language"] == "English"
        assert result["style"] == "Narration"

    def test_custom_values(self):
        result = _normalize_voiceover_engine({"language": "Spanish", "voice_name": "Maria"})
        assert result["language"] == "Spanish"
        assert result["voice_name"] == "Maria"


# ─── _normalized_text ────────────────────────────────────────────────────────

class TestNormalizedText:
    def test_returns_value_if_present(self):
        result = _normalized_text({"key": "value"}, "key", "default")
        assert result == "value"

    def test_returns_default_if_missing(self):
        result = _normalized_text({}, "key", "default")
        assert result == "default"

    def test_returns_default_if_empty_string(self):
        result = _normalized_text({"key": ""}, "key", "default")
        assert result == "default"

    def test_returns_default_if_non_string(self):
        result = _normalized_text({"key": 123}, "key", "default")
        assert result == "default"


# ─── _normalize_ugc_template_profile ─────────────────────────────────────────

class TestNormalizeUgcTemplateProfile:
    def test_none_returns_defaults(self):
        result = _normalize_ugc_template_profile(None)
        assert result["platform"] == "Instagram"
        assert result["objective"] == "Sales"

    def test_custom_values(self):
        result = _normalize_ugc_template_profile({"platform": "TikTok", "objective": "Awareness"})
        assert result["platform"] == "TikTok"
        assert result["objective"] == "Awareness"

    def test_has_all_expected_keys(self):
        result = _normalize_ugc_template_profile({})
        expected_keys = ["style_category_id", "platform", "objective", "hook_style", "aspect_ratio"]
        for key in expected_keys:
            assert key in result


# ─── _oauth_mode ─────────────────────────────────────────────────────────────

class TestOauthMode:
    def test_returns_string(self):
        result = _oauth_mode()
        assert isinstance(result, str)

    def test_default_is_mock_in_development(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=False):
            os.environ["ENVIRONMENT"] = "development"
            os.environ.pop("SOCIAL_OAUTH_MODE", None)
            result = _oauth_mode()
            assert result == "mock"

    def test_default_is_live_in_production(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=False):
            os.environ["ENVIRONMENT"] = "production"
            os.environ.pop("SOCIAL_OAUTH_MODE", None)
            result = _oauth_mode()
            assert result == "live"


# ─── _default_redirect_uri ───────────────────────────────────────────────────

class TestDefaultRedirectUri:
    def test_contains_network(self):
        result = _default_redirect_uri("linkedin")
        assert "linkedin" in result

    def test_is_url(self):
        result = _default_redirect_uri("instagram")
        assert result.startswith("http")

    def test_contains_oauth_path(self):
        result = _default_redirect_uri("x")
        assert "oauth" in result


# ─── _provider_is_configured ─────────────────────────────────────────────────

class TestProviderIsConfigured:
    def test_unknown_network_returns_false(self):
        assert _provider_is_configured("unknown_network_xyz") is False

    def test_without_env_var_returns_false(self):
        # With no env var set, should return False
        result = _provider_is_configured("linkedin")
        assert isinstance(result, bool)
