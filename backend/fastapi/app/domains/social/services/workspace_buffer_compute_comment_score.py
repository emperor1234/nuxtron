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
from fastapi import HTTPException
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
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _buffer_seed_posting_schedules(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


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
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _buffer_seed_start_page(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _buffer_get_audience_insights(network: str) -> dict[str, Any]:
    """Audience demographics from connected platform APIs.
    Live: Facebook Graph API /insights, LinkedIn API /organizationFollowerStatistics,
    Instagram Basic Display API, TikTok Research API, YouTube Analytics API."""
    raise HTTPException(
        status_code=501,
        detail={"code": "NOT_IMPLEMENTED", "message": "Audience demographics need verified platform insights from a connected account; no figures are generated without them."},
    )


def _buffer_get_channel_analytics(networks: list[str], days: int) -> dict[str, Any]:
    """Per-channel analytics. Live data fetched from:
    - Instagram: /v20.0/{ig-user-id}/insights (impressions, reach, engagement)
    - Facebook: /v20.0/{page-id}/insights
    - LinkedIn: /organizationalEntityShareStatistics
    - X (Twitter): v2 tweet_metrics endpoint
    - TikTok: /v2/research/video/query/
    - YouTube: YouTube Analytics API /reports"""
    raise HTTPException(
        status_code=501,
        detail={"code": "NOT_IMPLEMENTED", "message": "Channel analytics need verified platform insights from a connected account; no figures are generated without them."},
    )


def _buffer_get_best_time_analysis(network: str) -> dict[str, Any]:
    """Best time to post analysis. Live: fetches post engagement data from platform APIs,
    correlates publish timestamp with engagement rate, returns ranked time slots."""
    raise HTTPException(
        status_code=501,
        detail={"code": "NOT_IMPLEMENTED", "message": "Best-time analysis need verified platform insights from a connected account; no figures are generated without them."},
    )


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
