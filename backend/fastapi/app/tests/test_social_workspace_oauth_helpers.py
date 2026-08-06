"""Tests for social_workspace.py oauth and URL parsing helpers."""
import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.routers.social_workspace import (
    _build_authorization_url,
    _default_redirect_uri,
    _normalize_avatar_profile,
    _normalize_voiceover_engine,
    _normalized_text,
    _oauth_mode,
    _parse_website_host,
    _provider_is_configured,
)


class TestOauthMode:
    def test_default_is_mock_in_development(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ["ENVIRONMENT"] = "development"
            os.environ.pop("SOCIAL_OAUTH_MODE", None)
            assert _oauth_mode() == "mock"

    def test_default_is_live_in_production(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ["ENVIRONMENT"] = "production"
            os.environ.pop("SOCIAL_OAUTH_MODE", None)
            assert _oauth_mode() == "live"

    def test_from_env(self):
        with patch.dict(os.environ, {"SOCIAL_OAUTH_MODE": "live"}, clear=False):
            assert _oauth_mode() == "live"

    def test_strips_and_lowercases(self):
        with patch.dict(os.environ, {"SOCIAL_OAUTH_MODE": "  LIVE  "}, clear=False):
            assert _oauth_mode() == "live"


class TestDefaultRedirectUri:
    def test_default_base(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SOCIAL_OAUTH_BASE_REDIRECT_URI", None)
            uri = _default_redirect_uri("instagram")
            assert uri.endswith("/oauth/instagram/callback")

    def test_custom_base(self):
        with patch.dict(os.environ, {"SOCIAL_OAUTH_BASE_REDIRECT_URI": "https://myapp.com"}, clear=False):
            uri = _default_redirect_uri("facebook")
            assert uri == "https://myapp.com/oauth/facebook/callback"

    def test_trailing_slash_stripped_from_base(self):
        with patch.dict(os.environ, {"SOCIAL_OAUTH_BASE_REDIRECT_URI": "https://myapp.com/"}, clear=False):
            uri = _default_redirect_uri("x")
            assert uri == "https://myapp.com/oauth/x/callback"


class TestProviderIsConfigured:
    def test_configured_when_env_set(self):
        with patch.dict(os.environ, {"SOCIAL_OAUTH_INSTAGRAM_CLIENT_ID": "some-id"}, clear=False):
            assert _provider_is_configured("instagram") is True

    def test_not_configured_when_env_empty(self):
        with patch.dict(os.environ, {"SOCIAL_OAUTH_INSTAGRAM_CLIENT_ID": ""}, clear=False):
            assert _provider_is_configured("instagram") is False

    def test_unknown_provider_returns_false(self):
        assert _provider_is_configured("nonexistent_network") is False


class TestBuildAuthorizationUrl:
    def test_builds_url_for_instagram(self):
        with patch.dict(os.environ, {"SOCIAL_OAUTH_INSTAGRAM_CLIENT_ID": "test-client"}, clear=False):
            url = _build_authorization_url("instagram", "state123", "https://redirect.com/callback")
            assert "client_id=test-client" in url
            assert "state=state123" in url
            assert "response_type=code" in url

    def test_mock_client_id_when_unset(self):
        with patch.dict(os.environ, {"SOCIAL_OAUTH_INSTAGRAM_CLIENT_ID": ""}, clear=False):
            url = _build_authorization_url("instagram", "s1", "https://r.com")
            assert "client_id=mock-instagram-client" in url

    def test_contains_scope(self):
        url = _build_authorization_url("linkedin", "s2", "https://r.com")
        assert "scope=" in url


class TestParseWebsiteHost:
    def test_basic_domain(self):
        clean_host, brand_name, handle, normalized_url = _parse_website_host("example.com")
        assert clean_host == "example.com"
        assert brand_name == "Example"
        assert handle == "example"
        assert normalized_url == "https://example.com"

    def test_www_stripped(self):
        clean_host, _, _, _ = _parse_website_host("www.example.com")
        assert clean_host == "example.com"

    def test_https_url(self):
        clean_host, brand_name, _, _ = _parse_website_host("https://my-brand.io")
        assert clean_host == "my-brand.io"
        assert brand_name == "My Brand"

    def test_invalid_no_dot_raises(self):
        with pytest.raises(HTTPException):
            _parse_website_host("localhost")

    def test_empty_raises(self):
        with pytest.raises(HTTPException):
            _parse_website_host("")


class TestNormalizeAvatarProfile:
    def test_none_source_returns_defaults(self):
        result = _normalize_avatar_profile(None)
        assert isinstance(result, dict)

    def test_passes_keys(self):
        src = {"name": "MyCreator", "ethnicity": "diverse"}
        result = _normalize_avatar_profile(src)
        assert result.get("name") == "MyCreator"
        assert result.get("ethnicity") == "diverse"


class TestNormalizeVoiceoverEngine:
    def test_none_returns_defaults(self):
        result = _normalize_voiceover_engine(None)
        assert isinstance(result, dict)

    def test_passes_values(self):
        src = {"voice_name": "bella", "language": "Spanish"}
        result = _normalize_voiceover_engine(src)
        assert result.get("voice_name") == "bella"
        assert result.get("language") == "Spanish"


class TestNormalizedText:
    def test_returns_value(self):
        payload = {"name": "My Brand"}
        assert _normalized_text(payload, "name", "default") == "My Brand"

    def test_uses_default_when_missing(self):
        payload = {}
        assert _normalized_text(payload, "name", "fallback") == "fallback"

    def test_strips_whitespace(self):
        payload = {"name": "  hello  "}
        assert _normalized_text(payload, "name", "") == "hello"
