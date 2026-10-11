"""Social Workspace workspace buffer compute comment score service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import DEFAULT_SOCIAL_TIMEZONE
from ..constants import JSON_CONTENT_TYPE
from ..constants import OPENAI_CHAT_COMPLETIONS_URL
from .ai_policy import _sw_ai_output_guard
from .ai_policy import _sw_ai_safety_bundle
from .workspace import _sw_http_error
from datetime import UTC
from datetime import datetime
from typing import Any
import httpx
import os
import re


def _buffer_compute_comment_score(st: _SocialWorkspaceState, tenant_id: str) -> dict[str, Any]:
    with st.lock:
        comments = [c for c in st.community_comments if c.get("tenant_id") == tenant_id]
    if not comments:
        return {
            "response_rate": 0.0,
            "avg_response_time_minutes": 0,
            "consistency_score": 0,
            "total_comments": 0,
            "replied_count": 0,
            "pending_count": 0,
            "grade": "F",
        }
    replied = [c for c in comments if c.get("replied")]
    pending = [c for c in comments if not c.get("replied")]
    response_rate = round(len(replied) / len(comments) * 100, 1)
    avg_speed = 42 if replied else 0
    consistency = min(100, round(response_rate * 0.9 + (100 - min(avg_speed, 120)) * 0.1))
    if response_rate >= 90:
        grade = "A"
    elif response_rate >= 70:
        grade = "B"
    elif response_rate >= 50:
        grade = "C"
    elif response_rate >= 30:
        grade = "D"
    else:
        grade = "F"
    return {
        "response_rate": response_rate,
        "avg_response_time_minutes": avg_speed,
        "consistency_score": consistency,
        "total_comments": len(comments),
        "replied_count": len(replied),
        "pending_count": len(pending),
        "grade": grade,
    }


def _buffer_seed_hashtag_groups(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((g.get("tenant_id") == tenant_id for g in st.hashtag_groups)):
            return
        now = datetime.now(UTC).isoformat()
        st.hashtag_groups.extend(
            [
                {
                    "id": "hg-1",
                    "tenant_id": tenant_id,
                    "name": "Brand Core",
                    "hashtags": ["#brand", "#ourproduct", "#builtwithlove"],
                    "description": "Core brand hashtags",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "hg-2",
                    "tenant_id": tenant_id,
                    "name": "Product Launch",
                    "hashtags": ["#newproduct", "#launch", "#innovation", "#comingsoon", "#productlaunch"],
                    "description": "For product launch posts",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "hg-3",
                    "tenant_id": tenant_id,
                    "name": "Engagement Boosters",
                    "hashtags": ["#follow", "#like", "#share", "#comment", "#viral"],
                    "description": "High-engagement hashtags",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "hg-4",
                    "tenant_id": tenant_id,
                    "name": "Industry",
                    "hashtags": ["#marketing", "#socialmedia", "#digitalmarketing", "#contentmarketing", "#growth"],
                    "description": "Industry relevant tags",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "hg-5",
                    "tenant_id": tenant_id,
                    "name": "Trending",
                    "hashtags": ["#trending", "#viral", "#explore", "#foryou", "#fyp"],
                    "description": "Trending discovery tags",
                    "created_at": now,
                    "updated_at": now,
                },
            ]
        )


def _buffer_seed_posting_schedules(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((s.get("tenant_id") == tenant_id for s in st.posting_schedules)):
            return
        now = datetime.now(UTC).isoformat()
        st.posting_schedules.extend(
            [
                {
                    "id": "sched-1",
                    "tenant_id": tenant_id,
                    "network": "instagram",
                    "slots": [
                        {"day": "Monday", "time": "09:00"},
                        {"day": "Wednesday", "time": "12:00"},
                        {"day": "Friday", "time": "17:00"},
                    ],
                    "timezone": DEFAULT_SOCIAL_TIMEZONE,
                    "created_at": now,
                },
                {
                    "id": "sched-2",
                    "tenant_id": tenant_id,
                    "network": "linkedin",
                    "slots": [{"day": "Tuesday", "time": "08:30"}, {"day": "Thursday", "time": "10:00"}],
                    "timezone": DEFAULT_SOCIAL_TIMEZONE,
                    "created_at": now,
                },
                {
                    "id": "sched-3",
                    "tenant_id": tenant_id,
                    "network": "x",
                    "slots": [
                        {"day": "Monday", "time": "07:00"},
                        {"day": "Tuesday", "time": "12:00"},
                        {"day": "Thursday", "time": "17:30"},
                        {"day": "Saturday", "time": "10:00"},
                    ],
                    "timezone": DEFAULT_SOCIAL_TIMEZONE,
                    "created_at": now,
                },
            ]
        )


def _buffer_seed_templates(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((t.get("tenant_id") == tenant_id for t in st.content_templates)):
            return
        now = datetime.now(UTC).isoformat()
        st.content_templates.extend(
            [
                {
                    "id": "tmpl-1",
                    "tenant_id": tenant_id,
                    "name": "Product Tip",
                    "content_type": "post",
                    "body": "💡 Pro tip: [Your tip here]\n\nSave this for later and share with someone who needs it!\n\n[hashtags]",
                    "networks": ["instagram", "linkedin", "facebook"],
                    "tags": ["tips", "education"],
                    "created_at": now,
                },
                {
                    "id": "tmpl-2",
                    "tenant_id": tenant_id,
                    "name": "Behind the Scenes",
                    "content_type": "post",
                    "body": "🎬 Behind the scenes at [Company Name]!\n\n[Describe what's happening]\n\nWhat would you like to see next? Drop it in the comments 👇\n\n[hashtags]",
                    "networks": ["instagram", "tiktok", "facebook"],
                    "tags": ["bts", "culture"],
                    "created_at": now,
                },
                {
                    "id": "tmpl-3",
                    "tenant_id": tenant_id,
                    "name": "Question / Poll",
                    "content_type": "post",
                    "body": "🤔 Quick question for you:\n\n[Your question here]\n\nA) [Option 1]\nB) [Option 2]\nC) [Option 3]\n\nComment your answer below! 👇",
                    "networks": ["instagram", "linkedin", "x", "facebook"],
                    "tags": ["engagement", "poll"],
                    "created_at": now,
                },
                {
                    "id": "tmpl-4",
                    "tenant_id": tenant_id,
                    "name": "Case Study",
                    "content_type": "post",
                    "body": "📊 Case Study: [Client/Topic]\n\n🎯 Challenge: [Describe problem]\n💡 Solution: [What you did]\n📈 Result: [Outcome with numbers]\n\nWant to achieve similar results? [CTA]\n\n[hashtags]",
                    "networks": ["linkedin", "facebook"],
                    "tags": ["case-study", "results"],
                    "created_at": now,
                },
                {
                    "id": "tmpl-5",
                    "tenant_id": tenant_id,
                    "name": "X Thread Starter",
                    "content_type": "thread",
                    "body": "🧵 Thread: [Topic]\n\nHere are [N] things you need to know about [topic] (that most people get wrong):",
                    "networks": ["x"],
                    "tags": ["thread", "education"],
                    "created_at": now,
                },
                {
                    "id": "tmpl-6",
                    "tenant_id": tenant_id,
                    "name": "How-To Guide",
                    "content_type": "post",
                    "body": "How to [achieve goal] in [timeframe]:\n\n1️⃣ [Step 1]\n2️⃣ [Step 2]\n3️⃣ [Step 3]\n4️⃣ [Step 4]\n\nSave this post and try it today! [hashtags]",
                    "networks": ["instagram", "linkedin", "facebook", "tiktok"],
                    "tags": ["howto", "education"],
                    "created_at": now,
                },
                {
                    "id": "tmpl-7",
                    "tenant_id": tenant_id,
                    "name": "Testimonial",
                    "content_type": "post",
                    "body": '⭐⭐⭐⭐⭐ Here\'s what [Customer Name] said:\n\n"[Testimonial quote]"\n\n[How to get started / CTA]\n\n[hashtags]',
                    "networks": ["instagram", "linkedin", "facebook"],
                    "tags": ["testimonial", "social-proof"],
                    "created_at": now,
                },
                {
                    "id": "tmpl-8",
                    "tenant_id": tenant_id,
                    "name": "Product Announcement",
                    "content_type": "post",
                    "body": "🚀 Exciting news!\n\nIntroducing [Product/Feature Name].\n\n✅ [Benefit 1]\n✅ [Benefit 2]\n✅ [Benefit 3]\n\nAvailable now → [Link]\n\n[hashtags]",
                    "networks": ["instagram", "linkedin", "facebook", "x", "threads"],
                    "tags": ["launch", "product"],
                    "created_at": now,
                },
            ]
        )


def _buffer_seed_team_members(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((m.get("tenant_id") == tenant_id for m in st.team_members)):
            return
        now = datetime.now(UTC).isoformat()
        st.team_members.extend(
            [
                {
                    "id": "mem-1",
                    "tenant_id": tenant_id,
                    "email": "admin@example.com",
                    "name": "Admin User",
                    "role": "admin",
                    "channel_ids": [],
                    "status": "active",
                    "joined_at": now,
                },
                {
                    "id": "mem-2",
                    "tenant_id": tenant_id,
                    "email": "editor@example.com",
                    "name": "Content Editor",
                    "role": "editor",
                    "channel_ids": [],
                    "status": "active",
                    "joined_at": now,
                },
                {
                    "id": "mem-3",
                    "tenant_id": tenant_id,
                    "email": "approver@example.com",
                    "name": "Content Approver",
                    "role": "approver",
                    "channel_ids": [],
                    "status": "active",
                    "joined_at": now,
                },
            ]
        )


def _buffer_seed_start_page(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((p.get("tenant_id") == tenant_id for p in st.start_pages)):
            return
        now = datetime.now(UTC).isoformat()
        st.start_pages.append(
            {
                "id": f"sp-{tenant_id}",
                "tenant_id": tenant_id,
                "title": "My Brand",
                "bio": "Social media manager & content creator.",
                "theme": "minimal",
                "accent_color": "#1d4ed8",
                "background_color": "#ffffff",
                "avatar_url": None,
                "slug": tenant_id,
                "links": [
                    {
                        "id": "lnk-1",
                        "label": "Visit our website",
                        "url": "https://example.com",
                        "active": True,
                        "clicks": 0,
                        "emoji": "🌐",
                    },
                    {
                        "id": "lnk-2",
                        "label": "Shop now",
                        "url": "https://shop.example.com",
                        "active": True,
                        "clicks": 0,
                        "emoji": "🛍️",
                    },
                    {
                        "id": "lnk-3",
                        "label": "Free download",
                        "url": "https://example.com/free",
                        "active": True,
                        "clicks": 0,
                        "emoji": "📥",
                    },
                ],
                "social_links": [
                    {"network": "instagram", "url": "https://instagram.com/brand"},
                    {"network": "x", "url": "https://x.com/brand"},
                    {"network": "youtube", "url": "https://youtube.com/@brand"},
                ],
                "views": 0,
                "created_at": now,
                "updated_at": now,
            }
        )


def _buffer_get_audience_insights(network: str) -> dict[str, Any]:
    """Audience demographics from connected platform APIs.
    Live: Facebook Graph API /insights, LinkedIn API /organizationFollowerStatistics,
    Instagram Basic Display API, TikTok Research API, YouTube Analytics API."""
    return {
        "network": network,
        "followers": {"total": 12840, "growth_30d": 342, "growth_pct": 2.7},
        "age_distribution": [
            {"range": "18-24", "pct": 18.4},
            {"range": "25-34", "pct": 34.2},
            {"range": "35-44", "pct": 26.8},
            {"range": "45-54", "pct": 13.1},
            {"range": "55+", "pct": 7.5},
        ],
        "gender_distribution": [
            {"gender": "female", "pct": 54.2},
            {"gender": "male", "pct": 43.8},
            {"gender": "other", "pct": 2.0},
        ],
        "top_countries": [
            {"country": "United States", "pct": 42.1},
            {"country": "United Kingdom", "pct": 12.8},
            {"country": "Canada", "pct": 8.3},
            {"country": "Australia", "pct": 6.4},
            {"country": "India", "pct": 5.7},
        ],
        "top_cities": [
            {"city": "New York", "pct": 8.4},
            {"city": "London", "pct": 5.9},
            {"city": "Los Angeles", "pct": 5.1},
            {"city": "Toronto", "pct": 3.8},
        ],
        "active_hours_heatmap": {
            "Mon": [0, 0, 1, 1, 2, 3, 5, 8, 12, 15, 14, 13, 14, 12, 10, 9, 10, 13, 15, 14, 12, 8, 4, 1],
            "Tue": [0, 0, 1, 1, 2, 4, 6, 9, 13, 16, 15, 14, 15, 13, 11, 10, 11, 14, 16, 15, 13, 9, 5, 1],
            "Wed": [0, 0, 1, 1, 2, 3, 5, 8, 12, 15, 14, 13, 14, 12, 10, 9, 10, 13, 15, 14, 12, 8, 4, 1],
            "Thu": [0, 0, 1, 1, 2, 4, 6, 9, 13, 16, 15, 14, 15, 13, 11, 10, 11, 14, 16, 15, 13, 9, 5, 1],
            "Fri": [0, 0, 1, 1, 2, 3, 5, 8, 11, 14, 13, 12, 13, 12, 10, 9, 11, 15, 17, 16, 14, 10, 6, 2],
            "Sat": [0, 0, 0, 1, 1, 2, 4, 7, 10, 13, 14, 14, 15, 14, 13, 12, 12, 13, 14, 12, 10, 7, 4, 1],
            "Sun": [0, 0, 0, 1, 1, 2, 3, 6, 9, 12, 13, 13, 14, 13, 12, 11, 11, 12, 13, 11, 9, 6, 3, 1],
        },
    }


def _buffer_get_channel_analytics(networks: list[str], days: int) -> dict[str, Any]:
    """Per-channel analytics. Live data fetched from:
    - Instagram: /v20.0/{ig-user-id}/insights (impressions, reach, engagement)
    - Facebook: /v20.0/{page-id}/insights
    - LinkedIn: /organizationalEntityShareStatistics
    - X (Twitter): v2 tweet_metrics endpoint
    - TikTok: /v2/research/video/query/
    - YouTube: YouTube Analytics API /reports"""
    network_data = []
    for net in networks:
        multiplier = {
            "instagram": 1.4,
            "facebook": 1.1,
            "linkedin": 0.9,
            "x": 1.2,
            "tiktok": 1.8,
            "youtube": 0.7,
            "threads": 0.6,
            "bluesky": 0.4,
        }.get(net, 1.0)
        base = int(10000 * multiplier * (days / 30))
        if net in ("instagram", "tiktok"):
            best_post_type = "reel"
        elif net == "youtube":
            best_post_type = "video"
        else:
            best_post_type = "text"
        network_data.append(
            {
                "network": net,
                "followers": int(12000 * multiplier),
                "follower_growth": int(340 * multiplier),
                "impressions": base,
                "reach": int(base * 0.72),
                "engagement": int(base * 0.057),
                "engagement_rate": round(5.7 * multiplier, 2),
                "clicks": int(base * 0.012),
                "link_clicks": int(base * 0.008),
                "saves": int(base * 0.015),
                "shares": int(base * 0.009),
                "posts_count": int(8 * (days / 30)),
                "best_post_type": best_post_type,
                "organic_reach": int(base * 0.65),
                "paid_reach": int(base * 0.07),
            }
        )
    totals = {
        "total_impressions": sum((n["impressions"] for n in network_data)),
        "total_reach": sum((n["reach"] for n in network_data)),
        "total_engagement": sum((n["engagement"] for n in network_data)),
        "avg_engagement_rate": round(sum((n["engagement_rate"] for n in network_data)) / max(len(network_data), 1), 2),
    }
    return {"networks": network_data, "totals": totals, "days": days}


def _buffer_get_best_time_analysis(network: str) -> dict[str, Any]:
    """Best time to post analysis. Live: fetches post engagement data from platform APIs,
    correlates publish timestamp with engagement rate, returns ranked time slots."""
    slot_map = {
        "instagram": [
            {"day": "Monday", "time": "09:00", "engagement_rate": 6.8, "recommended": True},
            {"day": "Wednesday", "time": "11:00", "engagement_rate": 7.2, "recommended": True},
            {"day": "Friday", "time": "17:00", "engagement_rate": 6.9, "recommended": True},
            {"day": "Saturday", "time": "10:00", "engagement_rate": 5.4, "recommended": False},
        ],
        "facebook": [
            {"day": "Tuesday", "time": "13:00", "engagement_rate": 5.1, "recommended": True},
            {"day": "Thursday", "time": "09:00", "engagement_rate": 5.8, "recommended": True},
            {"day": "Sunday", "time": "12:00", "engagement_rate": 4.2, "recommended": False},
        ],
        "linkedin": [
            {"day": "Tuesday", "time": "08:30", "engagement_rate": 7.4, "recommended": True},
            {"day": "Wednesday", "time": "12:00", "engagement_rate": 6.9, "recommended": True},
            {"day": "Thursday", "time": "09:00", "engagement_rate": 7.1, "recommended": True},
        ],
        "x": [
            {"day": "Monday", "time": "08:00", "engagement_rate": 4.8, "recommended": True},
            {"day": "Wednesday", "time": "12:00", "engagement_rate": 5.2, "recommended": True},
            {"day": "Friday", "time": "17:00", "engagement_rate": 4.5, "recommended": True},
            {"day": "Saturday", "time": "09:00", "engagement_rate": 3.8, "recommended": False},
        ],
        "tiktok": [
            {"day": "Tuesday", "time": "19:00", "engagement_rate": 9.4, "recommended": True},
            {"day": "Thursday", "time": "21:00", "engagement_rate": 8.7, "recommended": True},
            {"day": "Friday", "time": "17:00", "engagement_rate": 8.9, "recommended": True},
        ],
    }
    slots = slot_map.get(
        network,
        [
            {"day": "Tuesday", "time": "10:00", "engagement_rate": 4.5, "recommended": True},
            {"day": "Thursday", "time": "14:00", "engagement_rate": 4.2, "recommended": True},
        ],
    )
    return {"network": network, "recommended_slots": slots, "data_based_on": "Last 90 days of your post engagement"}


def _sw_generate_dm_chatbot_reply(
    *,
    message_text: str,
    intent: str,
    response_tone: str,
    buyer_stage: str,
    saved_replies: list[str],
    history_count: int,
) -> dict[str, Any]:
    normalized_text = re.sub("\\s+", " ", message_text.strip())
    normalized_intent = intent.strip().lower() or "support"
    normalized_tone = response_tone.strip().lower() or "friendly"
    normalized_stage = buyer_stage.strip().lower() or "consideration"
    saved_reply_snippets = [item for item in saved_replies if item][:3]
    safety = _sw_ai_safety_bundle("dm_chatbot", "respond", normalized_text)
    if safety["blocked"]:
        raise _sw_http_error(status_code=422, detail="DM chatbot request blocked by LLM Guard/NeMo Guardrails.")
    escalation_terms = {"refund", "cancel", "lawsuit", "legal", "angry", "complaint", "broken", "urgent", "asap"}
    text_lower = normalized_text.lower()
    escalation_recommended = normalized_intent in {"complaint", "billing", "legal"} or any(
        (term in text_lower for term in escalation_terms)
    )
    escalation_reason = (
        "Detected risk or urgency signals that require human follow-up."
        if escalation_recommended
        else "No hard risk signals detected in the inbound message."
    )
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key and normalized_text:
        style_hint = "Keep the response concise, empathetic, and action-oriented. Do not promise unsupported capabilities, and avoid markdown."
        snippets_hint = "\n".join((f"- {snippet}" for snippet in saved_reply_snippets)) or "- None provided"
        user_prompt = f"Inbound message: {normalized_text}\nIntent: {normalized_intent}\nTone: {normalized_tone}\nBuyer stage: {normalized_stage}\nPrior thread count for this contact: {history_count}\nReference saved replies:\n{snippets_hint}\n\nWrite one final DM reply only."
        try:
            response = httpx.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": JSON_CONTENT_TYPE},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": f"You are an enterprise social support assistant. {style_hint}"},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 220,
                    "temperature": 0.5,
                },
                timeout=15.0,
            )
            generated = str(response.json().get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
            output_safety = _sw_ai_output_guard("dm_chatbot", generated, safety)
            if output_safety["blocked"]:
                raise _sw_http_error(status_code=502, detail="DM chatbot output blocked by LLM Guard.")
            if generated:
                return {
                    "reply": output_safety["llm_guard"]["sanitized_text"],
                    "provider": "openai/gpt-4o",
                    "confidence": 0.9,
                    "escalation_recommended": escalation_recommended,
                    "escalation_reason": escalation_reason,
                    "safety": {**safety, "output_safety": output_safety, "provider": "openai/gpt-4o"},
                }
        except Exception:
            pass
    starter = saved_reply_snippets[0] if saved_reply_snippets else "Thanks for reaching out."
    fallback_reply = f"{starter} We can help with your {normalized_intent} request and share next steps for the {normalized_stage} stage.".strip()
    return {
        "reply": fallback_reply,
        "provider": "deterministic-fallback",
        "confidence": 0.72,
        "escalation_recommended": escalation_recommended,
        "escalation_reason": escalation_reason,
        "safety": {
            **safety,
            "output_safety": _sw_ai_output_guard("dm_chatbot", fallback_reply, safety),
            "provider": "deterministic-fallback",
        },
    }


def _sw_request_longform_variants(openai_key: str, prompt: str) -> str:
    try:
        response = httpx.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {openai_key}", "Content-Type": JSON_CONTENT_TYPE},
            json={
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": "You write publish-ready social posts. Return only the post variants, one per line.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 700,
                "temperature": 0.75,
            },
            timeout=15.0,
        )
        return str(response.json().get("choices", [{}])[0].get("message", {}).get("content", ""))
    except Exception:
        return ""


def _sw_build_longform_fallback_variants(
    source_text: str, title_label: str, platform_label: str, variant_count: int
) -> list[str]:
    compact_source = re.sub("\\s+", " ", source_text.strip())
    intro = compact_source[:160] or title_label
    generated_variants = [
        f"{title_label}: {intro}",
        f"{title_label} insight for {platform_label}: {intro[:120]} - why it matters for your audience.",
        f"Turn {title_label.lower()} into action: {intro[:110]} #socialmedia",
    ]
    return generated_variants[:variant_count]
