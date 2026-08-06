"""Tests for pure helpers in utm_builder.py and seo_platform.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from backend.fastapi.app.routers.seo_platform import (
    _clean,
    _seo_analysis_cache_key,
)
from backend.fastapi.app.routers.utm_builder import (
    _build_utm_url,
    _sanitize,
)
from fastapi import HTTPException

# ─── _sanitize ───────────────────────────────────────────────────────────────

class TestSanitize:
    def test_strips_whitespace(self):
        assert _sanitize("  hello  ", True, False) == "hello"

    def test_lowercase(self):
        assert _sanitize("LinkedIn", True, False) == "linkedin"

    def test_no_lowercase(self):
        assert _sanitize("LinkedIn", False, False) == "LinkedIn"

    def test_replace_spaces(self):
        assert _sanitize("my campaign", True, True) == "my_campaign"

    def test_replace_dashes(self):
        assert _sanitize("my-campaign", True, True) == "my_campaign"

    def test_no_replace_spaces(self):
        result = _sanitize("my campaign", True, False)
        assert " " in result


# ─── _build_utm_url ──────────────────────────────────────────────────────────

class TestBuildUtmUrl:
    def test_appends_utm_params(self):
        result = _build_utm_url("https://example.com", "linkedin", "social", "campaign1",
                                 None, None, True, True)
        assert "utm_source=linkedin" in result
        assert "utm_medium=social" in result
        assert "utm_campaign=campaign1" in result

    def test_with_term_and_content(self):
        result = _build_utm_url("https://example.com", "google", "cpc", "sale",
                                 "keyword1", "ad_content", True, True)
        assert "utm_term=keyword1" in result
        assert "utm_content=ad_content" in result

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            _build_utm_url("not-a-url", "linkedin", "social", "camp", None, None, True, True)

    def test_preserves_existing_params(self):
        result = _build_utm_url("https://example.com?page=1", "linkedin", "social", "camp",
                                 None, None, True, True)
        assert "page=1" in result

    def test_lowercase_applied(self):
        result = _build_utm_url("https://example.com", "LinkedIn", "Social", "Campaign",
                                 None, None, True, True)
        assert "utm_source=linkedin" in result

    def test_space_replaced(self):
        result = _build_utm_url("https://example.com", "my source", "my medium", "my campaign",
                                 None, None, True, True)
        assert "utm_source=my_source" in result


# ─── _seo_analysis_cache_key ─────────────────────────────────────────────────

class TestSeoAnalysisCacheKey:
    def test_format(self):
        key = _seo_analysis_cache_key("tenant1", "technical_audit", "abc123")
        assert key == "seo:analysis:v1:tenant1:technical_audit:abc123"

    def test_unique_per_tenant(self):
        k1 = _seo_analysis_cache_key("t1", "mod", "hash1")
        k2 = _seo_analysis_cache_key("t2", "mod", "hash1")
        assert k1 != k2

    def test_unique_per_module(self):
        k1 = _seo_analysis_cache_key("t1", "mod_a", "hash1")
        k2 = _seo_analysis_cache_key("t1", "mod_b", "hash1")
        assert k1 != k2


# ─── _clean ──────────────────────────────────────────────────────────────────

class TestSeoClean:
    def test_normal_text_passthrough(self):
        result = _clean("Hello World this is SEO content")
        assert result == "Hello World this is SEO content"

    def test_truncated_at_max_len(self):
        result = _clean("a" * 5000, max_len=100)
        assert len(result) == 100

    def test_script_tag_blocked(self):
        with pytest.raises(HTTPException) as exc:
            _clean("<script>alert('xss')</script>")
        assert exc.value.status_code == 400

    def test_javascript_uri_blocked(self):
        with pytest.raises(HTTPException) as exc:
            _clean("javascript:void(0)")
        assert exc.value.status_code == 400

    def test_sql_injection_blocked(self):
        with pytest.raises(HTTPException) as exc:
            _clean("UNION SELECT * FROM users")
        assert exc.value.status_code == 400

    def test_drop_table_blocked(self):
        with pytest.raises(HTTPException) as exc:
            _clean("DROP TABLE users")
        assert exc.value.status_code == 400

    def test_custom_max_len(self):
        result = _clean("short", max_len=100)
        assert result == "short"

    def test_empty_string_passthrough(self):
        assert _clean("") == ""
