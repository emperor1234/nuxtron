"""Tests for pure helper functions in vse.py and ads_control_tower.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from backend.fastapi.app.routers.ads_control_tower import (
    _platform_oauth_url,
    _seed_connector,
)
from backend.fastapi.app.routers.seo_platform import get_shared_job_store
from backend.fastapi.app.routers.vse import (
    _build_content_body,
    _normalise_text,
    _token_jaccard_similarity,
    _topic_fingerprint,
    _uid,
    _viral_probability_score,
)

# ─── _uid ────────────────────────────────────────────────────────────────────

class TestUid:
    def test_default_length(self):
        result = _uid()
        assert len(result) == 8

    def test_custom_length(self):
        result = _uid(length=16)
        assert len(result) == 16

    def test_is_string(self):
        assert isinstance(_uid(), str)

    def test_unique(self):
        r1 = _uid()
        r2 = _uid()
        # Extremely unlikely to be same
        assert r1 != r2


# ─── _viral_probability_score ────────────────────────────────────────────────

class TestViralProbabilityScore:
    def test_base_score(self):
        score = _viral_probability_score(
            trigger_count=0,
            platform_optimised=False,
            hook_strength=0,
            emotional_vector="unknown",
            timing_score=0.0,
        )
        assert score == pytest.approx(44.0, abs=1.0)  # base=40 + unknown=4

    def test_platform_optimised_adds_10(self):
        base = _viral_probability_score(
            trigger_count=0, platform_optimised=False, hook_strength=0,
            emotional_vector="unknown", timing_score=0.0
        )
        optimised = _viral_probability_score(
            trigger_count=0, platform_optimised=True, hook_strength=0,
            emotional_vector="unknown", timing_score=0.0
        )
        assert optimised == pytest.approx(base + 10, abs=0.1)

    def test_awe_emotion_bonus(self):
        score = _viral_probability_score(
            trigger_count=0, platform_optimised=False, hook_strength=0,
            emotional_vector="awe", timing_score=0.0
        )
        base_unknown = _viral_probability_score(
            trigger_count=0, platform_optimised=False, hook_strength=0,
            emotional_vector="unknown", timing_score=0.0
        )
        assert score > base_unknown  # awe (8) > unknown (4)

    def test_capped_at_100(self):
        score = _viral_probability_score(
            trigger_count=100,
            platform_optimised=True,
            hook_strength=100,
            emotional_vector="awe",
            timing_score=1.0,
        )
        assert score == 100.0

    def test_trigger_count_capped_at_25(self):
        score_6 = _viral_probability_score(
            trigger_count=6, platform_optimised=False, hook_strength=0,
            emotional_vector="unknown", timing_score=0.0
        )
        score_10 = _viral_probability_score(
            trigger_count=10, platform_optimised=False, hook_strength=0,
            emotional_vector="unknown", timing_score=0.0
        )
        # Both should add 25 (capped), so same score
        assert score_6 == pytest.approx(score_10, abs=0.1)

    def test_timing_score_contributes(self):
        low = _viral_probability_score(
            trigger_count=0, platform_optimised=False, hook_strength=0,
            emotional_vector="unknown", timing_score=0.0
        )
        high = _viral_probability_score(
            trigger_count=0, platform_optimised=False, hook_strength=0,
            emotional_vector="unknown", timing_score=1.0
        )
        assert high > low

    def test_anger_emotion(self):
        score = _viral_probability_score(
            trigger_count=0, platform_optimised=False, hook_strength=0,
            emotional_vector="anger", timing_score=0.0
        )
        assert score > 40.0  # anger has 7 bonus


# ─── _normalise_text ─────────────────────────────────────────────────────────

class TestNormaliseText:
    def test_lowercases(self):
        assert _normalise_text("Hello World") == "hello world"

    def test_strips_whitespace(self):
        assert _normalise_text("  hello  ") == "hello"

    def test_normalises_spaces(self):
        assert _normalise_text("hello   world") == "hello world"

    def test_empty(self):
        assert _normalise_text("") == ""


# ─── _token_jaccard_similarity ───────────────────────────────────────────────

class TestTokenJaccardSimilarity:
    def test_identical(self):
        assert _token_jaccard_similarity("hello world", "hello world") == pytest.approx(1.0)

    def test_no_overlap(self):
        assert _token_jaccard_similarity("hello world", "foo bar") == pytest.approx(0.0)

    def test_partial_overlap(self):
        score = _token_jaccard_similarity("a b c", "a b d")
        assert 0.0 < score < 1.0

    def test_empty_both(self):
        assert _token_jaccard_similarity("", "") == pytest.approx(1.0)

    def test_empty_one(self):
        assert _token_jaccard_similarity("", "hello") == pytest.approx(0.0)


# ─── _topic_fingerprint ──────────────────────────────────────────────────────

class TestTopicFingerprint:
    def test_returns_string(self):
        result = _topic_fingerprint("AI marketing", "linkedin", "thread", "curiosity")
        assert isinstance(result, str)

    def test_correct_length(self):
        result = _topic_fingerprint("AI marketing", "linkedin", "thread", "curiosity")
        assert len(result) == 16

    def test_deterministic(self):
        r1 = _topic_fingerprint("AI", "linkedin", "thread", "awe")
        r2 = _topic_fingerprint("AI", "linkedin", "thread", "awe")
        assert r1 == r2

    def test_different_inputs_differ(self):
        r1 = _topic_fingerprint("AI", "linkedin", "thread", "awe")
        r2 = _topic_fingerprint("ML", "linkedin", "thread", "awe")
        assert r1 != r2


# ─── _build_content_body ─────────────────────────────────────────────────────

class TestBuildContentBody:
    def test_returns_string(self):
        result = _build_content_body(
            topic="AI trends",
            fmt="thread",
            emotional_vector="curiosity",
            objective="reach",
            uniqueness_angle="data-driven insights",
        )
        assert isinstance(result, str)

    def test_contains_topic(self):
        result = _build_content_body(
            topic="AI trends",
            fmt="thread",
            emotional_vector="curiosity",
            objective="reach",
            uniqueness_angle="data-driven",
        )
        assert "AI trends" in result

    def test_contains_vse_prefix(self):
        result = _build_content_body(
            topic="Test", fmt="video", emotional_vector="awe",
            objective="conversion", uniqueness_angle="unique"
        )
        assert "VSE" in result


# ─── _platform_oauth_url ─────────────────────────────────────────────────────

class TestPlatformOauthUrl:
    def test_google_ads(self):
        url = _platform_oauth_url("google_ads")
        assert "google.com" in url

    def test_microsoft_ads(self):
        url = _platform_oauth_url("microsoft_ads")
        assert "microsoft" in url

    def test_unknown_platform_fallback(self):
        url = _platform_oauth_url("unknown_platform")
        assert url == "https://example.com/oauth"

    def test_amazon_ads(self):
        url = _platform_oauth_url("amazon_ads")
        assert "amazon" in url

    def test_apple_search_ads(self):
        url = _platform_oauth_url("apple_search_ads")
        assert "apple" in url


# ─── _seed_connector ─────────────────────────────────────────────────────────

class TestSeedConnector:
    def test_returns_dict(self):
        result = _seed_connector("t1", "google_ads")
        assert isinstance(result, dict)

    def test_has_expected_keys(self):
        result = _seed_connector("t1", "google_ads")
        assert result["tenant_id"] == "t1"
        assert result["platform"] == "google_ads"
        assert result["status"] == "disconnected"
        assert result["connected"] is False

    def test_has_id(self):
        result = _seed_connector("t1", "google_ads")
        assert isinstance(result["id"], str)
        assert len(result["id"]) > 0

    def test_different_tenant(self):
        r1 = _seed_connector("t1", "google_ads")
        r2 = _seed_connector("t2", "google_ads")
        assert r1["tenant_id"] != r2["tenant_id"]


# ─── get_shared_job_store ─────────────────────────────────────────────────────

class TestGetSharedJobStore:
    def test_returns_dict(self):
        result = get_shared_job_store()
        assert isinstance(result, dict)

    def test_same_instance_returned(self):
        r1 = get_shared_job_store()
        r2 = get_shared_job_store()
        assert r1 is r2
