"""Tests for pure helpers in growth_suite.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.routers.growth_suite import (
    _ab_variants,
    _ads_matrix,
    _analyze_brand_voice,
    _audience_segments,
    _calendar_slots,
    _email_pack,
    _geo_seo,
    _pick_top_words,
    _podcast_episode,
    _repurpose_content,
    _scheduler_plan,
    _sentence_lengths,
    _tokenize,
    _video_script,
)


class TestTokenize:
    def test_basic(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_lowercase(self):
        assert _tokenize("UPPER") == ["upper"]

    def test_punctuation_removed(self):
        tokens = _tokenize("Hello, world!")
        assert "hello" in tokens
        assert "world" in tokens

    def test_numbers_excluded(self):
        tokens = _tokenize("test123")
        assert "123" not in tokens

    def test_empty_string(self):
        assert _tokenize("") == []


class TestSentenceLengths:
    def test_single_sentence(self):
        lengths = _sentence_lengths(["Hello World"])
        assert lengths == [2]

    def test_multiple_posts(self):
        lengths = _sentence_lengths(["Hello.", "World!"])
        assert len(lengths) == 2

    def test_empty_posts(self):
        lengths = _sentence_lengths([])
        assert lengths == [1]

    def test_min_length_is_1(self):
        lengths = _sentence_lengths(["a"])
        assert all(l >= 1 for l in lengths)


class TestPickTopWords:
    def test_returns_list(self):
        result = _pick_top_words(["hello world this is test content"])
        assert isinstance(result, list)

    def test_excludes_short_words(self):
        result = _pick_top_words(["an a is it"])
        assert "an" not in result
        assert "a" not in result

    def test_max_6_words(self):
        long_text = "hello world python testing coverage quality performance scalability reliability"
        result = _pick_top_words([long_text])
        assert len(result) <= 6

    def test_empty_posts(self):
        result = _pick_top_words([])
        assert result == []


class TestAnalyzeBrandVoice:
    def test_returns_expected_keys(self):
        result = _analyze_brand_voice(["Hello world."], "ai output")
        assert "fingerprint" in result
        assert "voice_score" in result
        assert "rewrite" in result

    def test_voice_score_in_range(self):
        result = _analyze_brand_voice(["Hello world."], "test")
        assert 0 <= result["voice_score"] <= 100

    def test_no_ai_output(self):
        result = _analyze_brand_voice(["test post"], "")
        assert result["rewrite"] == "No source AI output supplied."


class TestAbVariants:
    def test_returns_5_variants(self):
        variants = _ab_variants("My content here")
        assert len(variants) == 5

    def test_first_variant_is_control(self):
        variants = _ab_variants("base content")
        assert variants[0]["name"] == "control"
        assert variants[0]["content"] == "base content"

    def test_variant_keys(self):
        variants = _ab_variants("test")
        for i, v in enumerate(variants):
            assert v["variant_key"] == f"variant_{i+1}"


class TestCalendarSlots:
    def test_returns_correct_count(self):
        slots = _calendar_slots(["topic1", "topic2"], 5, "instagram")
        assert len(slots) == 5

    def test_slot_structure(self):
        slots = _calendar_slots(["topic"], 1, "twitter")
        assert "day" in slots[0]
        assert "topic" in slots[0]
        assert "channel" in slots[0]
        assert slots[0]["channel"] == "twitter"


class TestAudienceSegments:
    def test_returns_expected_keys(self):
        result = _audience_segments(["user1", "user2"], 99.99)
        assert "super_fans" in result
        assert "high_intent_buyers" in result
        assert "avg_buyer_score" in result

    def test_positive_counts(self):
        result = _audience_segments([], 0.0)
        assert result["super_fans"] >= 3
        assert result["high_intent_buyers"] >= 4


class TestAdsMatrix:
    def test_returns_spec_count(self):
        result = _ads_matrix("Campaign", "50% off", "Great deal")
        assert result["spec_count"] > 0

    def test_drafts_count_matches_spec_count(self):
        result = _ads_matrix("Campaign", "offer", "message")
        assert len(result["drafts"]) == result["spec_count"]

    def test_draft_structure(self):
        result = _ads_matrix("MyCampaign", "Special Deal", "Buy now")
        draft = result["drafts"][0]
        assert "spec" in draft
        assert "headline" in draft
        assert "primary_text" in draft
        assert draft["status"] == "draft"


class TestGeoSeo:
    def test_returns_keys(self):
        result = _geo_seo("content about python testing", [])
        assert "citation_score" in result
        assert "ai_share_of_voice" in result
        assert "recommendations" in result

    def test_citation_score_bounded(self):
        result = _geo_seo("content", [])
        assert result["citation_score"] <= 96


class TestEmailPack:
    def test_returns_keys(self):
        result = _email_pack("source content", "marketers", "Buy Now")
        assert "newsletter_subject" in result
        assert "drip_sequence" in result

    def test_drip_has_5_steps(self):
        result = _email_pack("content", "audience", "CTA")
        assert len(result["drip_sequence"]) == 5


class TestSchedulerPlan:
    def test_returns_scheduled_items(self):
        result = _scheduler_plan(["draft1", "draft2"], "twitter", 7)
        assert "scheduled_items" in result
        assert len(result["scheduled_items"]) == 2

    def test_platform_set(self):
        result = _scheduler_plan(["draft"], "instagram", 3)
        assert result["scheduled_items"][0]["platform"] == "instagram"


class TestPodcastEpisode:
    def test_returns_expected_keys(self):
        result = _podcast_episode("My Episode", "Episode content")
        assert "episode_title" in result
        assert "chapters" in result
        assert result["episode_title"] == "My Episode"

    def test_4_chapters(self):
        result = _podcast_episode("Title", "content")
        assert len(result["chapters"]) == 4


class TestVideoScript:
    def test_returns_scenes(self):
        result = _video_script("topic", "founders", "revenue")
        assert "scenes" in result
        assert len(result["scenes"]) == 4

    def test_scene_has_keys(self):
        result = _video_script("AI", "marketers", "leads")
        scene = result["scenes"][0]
        assert "scene" in scene
        assert "purpose" in scene
        assert "script" in scene


class TestRepurposeContent:
    def test_returns_outputs(self):
        result = _repurpose_content("source content here")
        assert "outputs" in result
        assert len(result["outputs"]) > 0

    def test_hours_saved(self):
        result = _repurpose_content("content")
        assert result["hours_saved"] == 12
