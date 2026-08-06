"""Tests for pure helper functions in smart_inbox.py, viralpost.py, and crm.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")


from backend.fastapi.app.routers.crm import _apply_segment_filters
from backend.fastapi.app.routers.smart_inbox import (
    _ai_classify,
    _priority_score,
    _suggested_replies,
)
from backend.fastapi.app.routers.viralpost import (
    _compute_optimal_times,
    _next_optimal_datetime,
)

# ─── _ai_classify ────────────────────────────────────────────────────────────

class TestAiClassify:
    def test_spam_detection(self):
        msg_type, sentiment, confidence = _ai_classify("click here for free money now!")
        assert msg_type == "spam"
        assert confidence > 0.5

    def test_crisis_detection(self):
        msg_type, sentiment, confidence = _ai_classify("safety recall lawsuit filed today")
        assert msg_type == "crisis"
        assert sentiment == "negative"

    def test_question_detection(self):
        msg_type, sentiment, confidence = _ai_classify("When does it ship?")
        assert msg_type == "question"

    def test_complaint_detection(self):
        msg_type, sentiment, confidence = _ai_classify("This is terrible and broken and bad")
        assert msg_type == "complaint"
        assert sentiment == "negative"

    def test_compliment_detection(self):
        msg_type, sentiment, confidence = _ai_classify("This is amazing and awesome and fantastic")
        assert msg_type == "compliment"
        assert sentiment == "positive"

    def test_neutral_conversation(self):
        msg_type, sentiment, confidence = _ai_classify("Hello there")
        assert msg_type == "conversation"

    def test_returns_tuple(self):
        result = _ai_classify("test message")
        assert isinstance(result, tuple)
        assert len(result) == 3


# ─── _priority_score ─────────────────────────────────────────────────────────

class TestPriorityScore:
    def test_crisis_is_highest(self):
        assert _priority_score("crisis", "neutral", 0) == 100

    def test_complaint_plus_negative(self):
        score = _priority_score("complaint", "negative", 0)
        assert score == 70  # 50 + 20

    def test_question_score(self):
        score = _priority_score("question", "neutral", 0)
        assert score == 30

    def test_compliment_score(self):
        score = _priority_score("compliment", "positive", 0)
        assert score == 10

    def test_high_follower_boost(self):
        base = _priority_score("question", "neutral", 0)
        boosted = _priority_score("question", "neutral", 100_000)
        assert boosted == base + 40

    def test_medium_follower_boost(self):
        base = _priority_score("question", "neutral", 0)
        boosted = _priority_score("question", "neutral", 10_000)
        assert boosted == base + 20

    def test_small_follower_boost(self):
        base = _priority_score("question", "neutral", 0)
        boosted = _priority_score("question", "neutral", 1_000)
        assert boosted == base + 10

    def test_unknown_type(self):
        score = _priority_score("other", "neutral", 0)
        assert score == 0


# ─── _suggested_replies ──────────────────────────────────────────────────────

class TestSuggestedReplies:
    def test_question_replies(self):
        replies = _suggested_replies("question")
        assert len(replies) == 3

    def test_complaint_replies(self):
        replies = _suggested_replies("complaint")
        assert len(replies) == 3

    def test_compliment_replies(self):
        replies = _suggested_replies("compliment")
        assert len(replies) == 3

    def test_crisis_replies(self):
        replies = _suggested_replies("crisis")
        assert len(replies) == 3

    def test_unknown_type_returns_generic(self):
        replies = _suggested_replies("conversation")
        assert len(replies) == 3

    def test_all_strings(self):
        for msg_type in ["question", "complaint", "compliment", "crisis", "spam"]:
            for reply in _suggested_replies(msg_type):
                assert isinstance(reply, str)


# ─── _compute_optimal_times ──────────────────────────────────────────────────

class TestComputeOptimalTimes:
    def test_insufficient_data_uses_benchmark(self):
        result = _compute_optimal_times(
            history=[],
            network="instagram",
            content_type="image",
            tz_offset=0,
        )
        assert len(result) > 0
        assert result[0]["source"] == "industry_benchmark"
        assert result[0]["confidence"] == "low"

    def test_unknown_network_falls_back_to_instagram(self):
        result = _compute_optimal_times(
            history=[],
            network="unknown_network",
            content_type="image",
            tz_offset=0,
        )
        assert len(result) > 0

    def test_sufficient_history_computes_windows(self):
        history = []
        for i in range(15):
            history.append({
                "published_at": "2024-01-15T10:00:00+00:00",
                "impressions": 100,
                "engagements": 10 + i,
            })
        result = _compute_optimal_times(
            history=history,
            network="linkedin",
            content_type="image",
            tz_offset=0,
        )
        assert len(result) <= 3
        for window in result:
            assert "engagement_index" in window

    def test_video_content_weight_applied(self):
        history = []
        for _i in range(12):
            history.append({
                "published_at": "2024-01-15T10:00:00+00:00",
                "impressions": 100,
                "engagements": 10,
            })
        result_image = _compute_optimal_times(
            history=history,
            network="instagram",
            content_type="image",
            tz_offset=0,
        )
        result_video = _compute_optimal_times(
            history=history,
            network="instagram",
            content_type="video",
            tz_offset=0,
        )
        # Video should have same or higher engagement_index due to 1.2x weight
        assert result_video[0]["engagement_index"] >= result_image[0]["engagement_index"]

    def test_history_with_invalid_dates_handled(self):
        history = [{"published_at": "not-a-date", "impressions": 100, "engagements": 10}] * 15
        result = _compute_optimal_times(
            history=history,
            network="instagram",
            content_type="image",
            tz_offset=0,
        )
        # Falls back to benchmark when invalid dates result in empty buckets
        assert len(result) > 0

    def test_tz_offset_applied(self):
        history = []
        for _i in range(15):
            history.append({
                "published_at": "2024-01-15T10:00:00+00:00",
                "impressions": 100,
                "engagements": 10,
            })
        result = _compute_optimal_times(
            history=history,
            network="instagram",
            content_type="image",
            tz_offset=5,
        )
        assert len(result) > 0


# ─── _next_optimal_datetime ──────────────────────────────────────────────────

class TestNextOptimalDatetime:
    def test_empty_windows_returns_future(self):
        result = _next_optimal_datetime([], tz_offset=0)
        assert isinstance(result, str)
        assert len(result) > 10

    def test_returns_iso_string(self):
        windows = [{"day": "Monday", "hour": 10, "minute": 0}]
        result = _next_optimal_datetime(windows)
        # Should be parseable as ISO datetime
        assert "T" in result or "-" in result

    def test_with_tz_offset(self):
        windows = [{"day": "Tuesday", "hour": 14, "minute": 30}]
        result = _next_optimal_datetime(windows, tz_offset=3)
        assert isinstance(result, str)

    def test_unknown_day_name(self):
        windows = [{"day": "Funday", "hour": 10, "minute": 0}]
        result = _next_optimal_datetime(windows)
        assert isinstance(result, str)


# ─── _apply_segment_filters ──────────────────────────────────────────────────

class TestApplySegmentFilters:
    def _contacts(self):
        return [
            {"tenant_id": "t1", "lifecycle_stage": "lead", "lead_score": 50, "tags": ["vip"], "company": "Acme Corp"},
            {"tenant_id": "t1", "lifecycle_stage": "customer", "lead_score": 80, "tags": ["premium"], "company": "Beta Inc"},
            {"tenant_id": "t2", "lifecycle_stage": "lead", "lead_score": 90, "tags": [], "company": "Other"},
        ]

    def test_no_filters_returns_all_tenant_contacts(self):
        result = _apply_segment_filters("t1", {}, self._contacts())
        assert len(result) == 2

    def test_excludes_other_tenants(self):
        result = _apply_segment_filters("t1", {}, self._contacts())
        for c in result:
            assert c["tenant_id"] == "t1"

    def test_lifecycle_stage_filter(self):
        result = _apply_segment_filters("t1", {"lifecycle_stage": "lead"}, self._contacts())
        assert len(result) == 1
        assert result[0]["lifecycle_stage"] == "lead"

    def test_min_lead_score_filter(self):
        result = _apply_segment_filters("t1", {"min_lead_score": 70}, self._contacts())
        assert len(result) == 1
        assert result[0]["lead_score"] == 80

    def test_tag_filter(self):
        result = _apply_segment_filters("t1", {"tag": "vip"}, self._contacts())
        assert len(result) == 1
        assert "vip" in result[0]["tags"]

    def test_company_filter_case_insensitive(self):
        result = _apply_segment_filters("t1", {"company": "acme"}, self._contacts())
        assert len(result) == 1
        assert "acme" in result[0]["company"].lower()

    def test_empty_contacts(self):
        result = _apply_segment_filters("t1", {}, [])
        assert result == []

    def test_combined_filters(self):
        result = _apply_segment_filters(
            "t1",
            {"lifecycle_stage": "lead", "min_lead_score": 30},
            self._contacts(),
        )
        assert len(result) == 1
