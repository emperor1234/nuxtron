"""Tests for pure helper functions in viralpost.py and smart_inbox.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from datetime import UTC

from backend.fastapi.app.routers.smart_inbox import (
    _ai_classify,
    _priority_score,
    _suggested_replies,
)
from backend.fastapi.app.routers.viralpost import (
    _compute_optimal_times,
    _next_optimal_datetime,
)

# ─── viralpost: _compute_optimal_times ───────────────────────────────────────

class TestComputeOptimalTimes:
    def test_insufficient_history_uses_benchmark(self):
        result = _compute_optimal_times([], "instagram", "image", 0)
        assert isinstance(result, list)
        assert all(r.get("source") == "industry_benchmark" for r in result)

    def test_insufficient_history_returns_low_confidence(self):
        result = _compute_optimal_times([{"some": "data"}] * 5, "instagram", "image", 0)
        assert all(r.get("confidence") == "low" for r in result)

    def test_with_sufficient_history(self):
        from datetime import datetime, timedelta
        history = []
        for i in range(20):
            dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC) + timedelta(days=i % 7)
            history.append({
                "published_at": dt.isoformat(),
                "impressions": 1000,
                "engagements": 50 + i,
            })
        result = _compute_optimal_times(history, "instagram", "image", 0)
        assert isinstance(result, list)
        assert len(result) <= 3

    def test_returns_at_most_3_windows(self):
        from datetime import datetime
        history = []
        for i in range(30):
            dt = datetime(2024, 1, 15 + (i % 7), 10 + (i % 5), 0, 0, tzinfo=UTC)
            history.append({
                "published_at": dt.isoformat(),
                "impressions": 1000,
                "engagements": 50,
            })
        result = _compute_optimal_times(history, "twitter", "video", 0)
        assert len(result) <= 3

    def test_video_content_type(self):
        result = _compute_optimal_times([], "instagram", "video", 0)
        assert isinstance(result, list)


# ─── viralpost: _next_optimal_datetime ───────────────────────────────────────

class TestNextOptimalDatetime:
    def test_empty_windows_returns_24h_from_now(self):
        result = _next_optimal_datetime([])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_with_valid_window(self):
        windows = [{"day": "Monday", "hour": 10, "minute": 0}]
        result = _next_optimal_datetime(windows)
        assert isinstance(result, str)

    def test_returns_isoformat_string(self):
        windows = [{"day": "Tuesday", "hour": 14, "minute": 30}]
        result = _next_optimal_datetime(windows)
        # Should be parseable as a datetime string
        # Just ensure it's non-empty and looks like a datetime
        assert "T" in result or "-" in result


# ─── smart_inbox: _ai_classify ───────────────────────────────────────────────

class TestAiClassify:
    def test_spam_detection(self):
        msg_type, sentiment, conf = _ai_classify("Click here for free money winner!")
        assert msg_type == "spam"
        assert conf > 0.5

    def test_crisis_detection(self):
        msg_type, sentiment, conf = _ai_classify("This product is dangerous and there's a lawsuit!")
        assert msg_type == "crisis"
        assert sentiment == "negative"

    def test_question_detection(self):
        msg_type, sentiment, conf = _ai_classify("How do I reset my password?")
        assert msg_type == "question"

    def test_complaint_detection(self):
        msg_type, sentiment, conf = _ai_classify("This is terrible and awful, I hate it!")
        assert msg_type == "complaint"
        assert sentiment == "negative"

    def test_compliment_detection(self):
        msg_type, sentiment, conf = _ai_classify("This is amazing and perfect, I love it!")
        assert msg_type == "compliment"
        assert sentiment == "positive"

    def test_neutral_conversation(self):
        msg_type, sentiment, conf = _ai_classify("Hello, just checking in.")
        assert msg_type == "conversation"
        assert sentiment == "neutral"

    def test_returns_tuple_of_three(self):
        result = _ai_classify("Test message")
        assert len(result) == 3


# ─── smart_inbox: _priority_score ────────────────────────────────────────────

class TestPriorityScore:
    def test_crisis_highest_priority(self):
        score = _priority_score("crisis", "negative", 0)
        assert score >= 100

    def test_complaint_medium_priority(self):
        score = _priority_score("complaint", "negative", 0)
        assert 50 <= score <= 100

    def test_compliment_low_priority(self):
        score = _priority_score("compliment", "positive", 0)
        assert score < 50

    def test_high_follower_count_boosts_score(self):
        low_follow = _priority_score("question", "neutral", 100)
        high_follow = _priority_score("question", "neutral", 100_000)
        assert high_follow > low_follow

    def test_negative_sentiment_boosts_score(self):
        neutral = _priority_score("conversation", "neutral", 0)
        negative = _priority_score("conversation", "negative", 0)
        assert negative > neutral

    def test_returns_int(self):
        score = _priority_score("question", "neutral", 1000)
        assert isinstance(score, int)


# ─── smart_inbox: _suggested_replies ─────────────────────────────────────────

class TestSuggestedReplies:
    def test_question_returns_3_replies(self):
        replies = _suggested_replies("question")
        assert len(replies) == 3

    def test_complaint_returns_3_replies(self):
        replies = _suggested_replies("complaint")
        assert len(replies) == 3

    def test_compliment_returns_3_replies(self):
        replies = _suggested_replies("compliment")
        assert len(replies) == 3

    def test_crisis_returns_3_replies(self):
        replies = _suggested_replies("crisis")
        assert len(replies) == 3

    def test_unknown_type_returns_fallback(self):
        replies = _suggested_replies("unknown_type")
        assert len(replies) == 3

    def test_replies_are_strings(self):
        replies = _suggested_replies("question")
        assert all(isinstance(r, str) for r in replies)
