"""
Additional tests for seo_platform.py pure helpers.
Tests functions that can be exercised without DB or LLM.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import patch

import pytest


class TestUpstashHelpers:
    def test_upstash_rest_base_url_empty(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _upstash_rest_base_url
        with patch.dict(os.environ, {"UPSTASH_REDIS_REST_URL": ""}, clear=False):
            assert _upstash_rest_base_url() == ""

    def test_upstash_rest_base_url_strips_slash(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _upstash_rest_base_url
        with patch.dict(os.environ, {"UPSTASH_REDIS_REST_URL": "https://redis.upstash.io/"}, clear=False):
            assert _upstash_rest_base_url() == "https://redis.upstash.io"

    def test_upstash_rest_token_empty(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _upstash_rest_token
        with patch.dict(os.environ, {"UPSTASH_REDIS_REST_TOKEN": ""}, clear=False):
            assert _upstash_rest_token() == ""

    def test_upstash_rest_token_returns_value(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _upstash_rest_token
        with patch.dict(os.environ, {"UPSTASH_REDIS_REST_TOKEN": "test-token"}, clear=False):
            assert _upstash_rest_token() == "test-token"

    def test_dist_cache_disabled_without_config(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _seo_analysis_dist_cache_enabled
        with patch.dict(os.environ, {"UPSTASH_REDIS_REST_URL": "", "UPSTASH_REDIS_REST_TOKEN": ""}, clear=False):
            assert _seo_analysis_dist_cache_enabled() is False

    def test_dist_cache_enabled_with_config(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _seo_analysis_dist_cache_enabled
        with patch.dict(os.environ, {
            "UPSTASH_REDIS_REST_URL": "https://redis.upstash.io",
            "UPSTASH_REDIS_REST_TOKEN": "token123",
        }, clear=False):
            assert _seo_analysis_dist_cache_enabled() is True

    def test_upstash_command_no_config_returns_none(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _upstash_command
        with patch.dict(os.environ, {"UPSTASH_REDIS_REST_URL": "", "UPSTASH_REDIS_REST_TOKEN": ""}, clear=False):
            result = _upstash_command(["GET", "some_key"])
            assert result is None


class TestSeoCacheKey:
    def test_cache_key_format(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _seo_analysis_cache_key
        key = _seo_analysis_cache_key("tenant-1", "keyword-research", "abc123")
        assert key == "seo:analysis:v1:tenant-1:keyword-research:abc123"

    def test_cache_key_is_string(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _seo_analysis_cache_key
        key = _seo_analysis_cache_key("t", "m", "h")
        assert isinstance(key, str)


class TestClean:
    def test_clean_safe_text(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _clean
        result = _clean("A simple SEO keyword")
        assert result == "A simple SEO keyword"

    def test_clean_truncates_to_max_len(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _clean
        result = _clean("x" * 5000, max_len=4000)
        assert len(result) == 4000

    def test_clean_custom_max_len(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _clean
        result = _clean("hello world", max_len=5)
        assert result == "hello"

    def test_clean_script_raises(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _clean
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _clean("<script>alert('xss')</script>")
        assert exc.value.status_code == 400

    def test_clean_javascript_raises(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _clean
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _clean("javascript:alert(1)")

    def test_clean_sql_injection_raises(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _clean
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _clean("DROP TABLE users")

    def test_clean_union_select_raises(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _clean
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _clean("1 UNION SELECT * FROM table")

    def test_clean_php_injection_raises(self) -> None:
        from backend.fastapi.app.routers.seo_platform import _clean
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _clean("<?php echo 'hacked';")
