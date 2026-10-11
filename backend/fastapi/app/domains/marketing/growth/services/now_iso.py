"""Marketing/Growth service: now iso."""

from __future__ import annotations
from ..constants import _SLUG_PATTERN
from ..constants import _STOP_WORDS
from ..schemas import RoiForecastRequest
from collections import Counter
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
import re
import statistics


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tokenize(text: str) -> list[str]:
    return re.findall("[a-zA-Z']+", text.lower())


def _sentence_lengths(posts: list[str]) -> list[int]:
    values: list[int] = []
    for post in posts:
        segments = [segment.strip() for segment in re.split("[.!?]+", post) if segment.strip()]
        for segment in segments:
            values.append(max(1, len(_tokenize(segment))))
    return values or [1]


def _pick_top_words(posts: list[str]) -> list[str]:
    words = [word for post in posts for word in _tokenize(post) if len(word) > 3 and word not in _STOP_WORDS]
    counts = Counter(words)
    return [word for word, _ in counts.most_common(6)]


def _analyze_brand_voice(posts: list[str], ai_output: str) -> dict[str, Any]:
    sentence_lengths = _sentence_lengths(posts)
    avg_sentence_length = round(statistics.mean(sentence_lengths), 1)
    signature_words = _pick_top_words(posts)
    source_words = set(signature_words)
    ai_words = set(_tokenize(ai_output)) if ai_output else set()
    match_ratio = len(source_words & ai_words) / max(1, len(source_words)) if ai_output else 0.0
    punctuation_intensity = round(sum((post.count("!") + post.count("?") for post in posts)) / max(1, len(posts)), 2)
    line_break_ratio = round(sum((post.count("\n") for post in posts)) / max(1, len(posts)), 2)
    score = int(min(98, 62 + match_ratio * 28 + min(8, punctuation_intensity * 2)))
    rewrite = ai_output.strip() or "No source AI output supplied."
    if ai_output.strip():
        lead = signature_words[0].capitalize() if signature_words else "Here"
        tail = ", ".join(signature_words[:3]) if signature_words else "clarity, proof, momentum"
        rewrite = f"{lead} matters when the market is crowded. {ai_output.strip()} Keep the cadence tight, make the proof concrete, and land the point around {tail}."
    return {
        "fingerprint": {
            "avg_sentence_length": avg_sentence_length,
            "signature_words": signature_words,
            "punctuation_intensity": punctuation_intensity,
            "line_break_ratio": line_break_ratio,
        },
        "voice_score": score,
        "rewrite": rewrite,
    }


def _ab_variants(base_content: str) -> list[dict[str, str]]:
    stems = [
        ("control", base_content),
        ("proof", f"Proof first: {base_content}"),
        ("urgency", f"Before your competitors do, {base_content[0].lower() + base_content[1:]}"),
        ("contrarian", f"Most teams get this wrong. {base_content}"),
        ("roi", f"This is what turns content into pipeline: {base_content}"),
    ]
    return [
        {"variant_key": f"variant_{index + 1}", "name": name, "content": content}
        for index, (name, content) in enumerate(stems)
    ]


def _roi_forecast(payload: RoiForecastRequest) -> dict[str, Any]:
    avg_revenue = statistics.mean(payload.historical_revenue)
    avg_engagement = statistics.mean(payload.historical_engagement_rate)
    projected_engagement = round(payload.expected_impressions * avg_engagement, 0)
    clicks = round(projected_engagement * 0.31, 0)
    conversions = max(1, round(clicks * 0.065, 0))
    projected_revenue = round(avg_revenue * (0.88 + min(0.35, avg_engagement * 3.2)), 2)
    return {
        "projected_engagement": int(projected_engagement),
        "projected_clicks": int(clicks),
        "projected_conversions": int(conversions),
        "projected_revenue": projected_revenue,
        "confidence": round(min(0.94, 0.66 + len(payload.historical_revenue) * 0.03), 2),
        "recommended_slot": "Tue 09:30",
    }


def _calendar_slots(topics: list[str], days: int, channel: str) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    base_date = datetime.now(UTC).date()
    for index in range(days):
        topic = topics[index % len(topics)]
        post_date = base_date + timedelta(days=index)
        slot_hour = [9, 11, 14, 16][index % 4]
        predicted_revenue = round(120 + index % 7 * 19.5 + len(topic) * 1.7, 2)
        slots.append(
            {
                "day": post_date.isoformat(),
                "topic": topic,
                "channel": channel,
                "slot": f"{slot_hour:02d}:00",
                "predicted_revenue": predicted_revenue,
                "content_type": ["thought leadership", "case study", "offer", "social proof"][index % 4],
            }
        )
    return slots


def _audience_segments(handles: list[str], product_price: float) -> dict[str, Any]:
    size = max(12, len(handles) or 24)
    super_fans = max(3, round(size * 0.18))
    high_intent = max(4, round(size * 0.27))
    advocates = max(2, round(size * 0.11))
    avg_buyer_score = round(min(94, 52 + product_price / 4), 1)
    return {
        "super_fans": super_fans,
        "high_intent_buyers": high_intent,
        "rising_advocates": advocates,
        "avg_buyer_score": avg_buyer_score,
        "targeting_recommendations": [
            "Offer proof-heavy posts to high-intent buyers.",
            "Give super fans early-access content and referrals.",
            "Feed advocates quote cards and customer win snippets.",
        ],
    }


def _ads_matrix(campaign_name: str, offer: str, primary_message: str) -> dict[str, Any]:
    specs = [
        "meta_feed",
        "meta_story",
        "meta_reel",
        "instagram_feed",
        "instagram_story",
        "tiktok_infeed",
        "linkedin_single_image",
        "linkedin_document",
        "google_responsive_search",
        "google_display",
        "youtube_short",
        "youtube_instream",
        "x_promoted",
    ]
    drafts = [
        {
            "spec": spec,
            "headline": f"{campaign_name} | {offer[:55]}",
            "primary_text": primary_message[:180],
            "cta": "Learn more",
            "status": "draft",
        }
        for spec in specs
    ]
    return {"spec_count": len(drafts), "drafts": drafts}


def _repurpose_content(source_content: str) -> dict[str, Any]:
    formats = [
        "thread",
        "carousel",
        "newsletter",
        "podcast_script",
        "faq",
        "press_release",
        "video_script",
        "reddit_post",
        "quote_cards",
        "case_study",
        "landing_page",
        "sales_email",
        "drip_email",
        "webinar_outline",
        "community_post",
        "founder_note",
        "ad_copy",
        "lead_magnet",
        "sms_teaser",
        "comment_replies",
    ]
    outputs = [
        {"format": fmt, "title": f"{fmt.replace('_', ' ').title()} version", "summary": f"{source_content[:120]}..."}
        for fmt in formats
    ]
    return {"outputs": outputs, "hours_saved": 12}


def _geo_seo(content: str, competitors: list[str]) -> dict[str, Any]:
    keywords = _pick_top_words([content])
    citation_score = min(96, 58 + len(keywords) * 4)
    competitor_pressure = len(competitors) * 6
    ai_share_of_voice = round(max(12, citation_score - competitor_pressure / 2), 1)
    return {
        "citation_score": citation_score,
        "ai_share_of_voice": ai_share_of_voice,
        "priority_keywords": keywords[:5],
        "recommendations": [
            "Add a concise definition paragraph near the top.",
            "Publish original data points and citeable stats.",
            "Mirror question-style subheads used in AI overviews.",
        ],
    }


def _email_pack(source_content: str, audience: str, cta: str) -> dict[str, Any]:
    drip = [{"step": step + 1, "subject": f"{audience.title()} email {step + 1}", "cta": cta} for step in range(5)]
    return {
        "newsletter_subject": f"{audience.title()} weekly brief",
        "newsletter_body": source_content[:400],
        "drip_sequence": drip,
    }


def _scheduler_plan(drafts: list[str], platform: str, fill_days: int) -> dict[str, Any]:
    slots = ["08:30", "10:00", "12:30", "15:00", "18:00"]
    items = []
    start = datetime.now(UTC).date()
    for index, draft in enumerate(drafts):
        schedule_day = start + timedelta(days=index % fill_days)
        items.append(
            {
                "draft": draft[:120],
                "platform": platform,
                "scheduled_for": f"{schedule_day.isoformat()}T{slots[index % len(slots)]}:00Z",
                "expected_reach_lift_pct": 18 + index % 5 * 4,
            }
        )
    return {"scheduled_items": items, "best_windows": slots[: min(fill_days, len(slots))]}


def _podcast_episode(title: str, source_text: str) -> dict[str, Any]:
    chapters = [
        {"title": "Hook", "timestamp": "00:00"},
        {"title": "Core insight", "timestamp": "02:30"},
        {"title": "Case study", "timestamp": "06:00"},
        {"title": "CTA", "timestamp": "09:30"},
    ]
    return {
        "episode_title": title,
        "script": source_text[:1200],
        "chapters": chapters,
        "rss_slug": _SLUG_PATTERN.sub("-", title.lower()).strip("-"),
        "social_clips": 3,
    }


def _video_script(topic: str, audience: str, objective: str) -> dict[str, Any]:
    scenes = [
        {"scene": 1, "purpose": "Hook", "script": f"Open with the painful cost of ignoring {topic}."},
        {"scene": 2, "purpose": "Problem", "script": f"Show why {audience} keep missing leverage."},
        {"scene": 3, "purpose": "Solution", "script": f"Introduce the system that fixes it and drives {objective}."},
        {"scene": 4, "purpose": "CTA", "script": "End with one concrete next step and a deadline."},
    ]
    return {
        "scenes": scenes,
        "b_roll": ["dashboard close-ups", "customer proof", "workflow animation"],
        "thumbnail_concepts": ["Before/After metric split", "Bold promise with face crop"],
        "srt_preview": "1\n00:00:00,000 --> 00:00:03,000\nStop publishing content that cannot convert.\n",
    }
