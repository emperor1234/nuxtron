"""Social Workspace workspace service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import CanvaImportRequest
from ..constants import JSON_CONTENT_TYPE
from ..constants import SUPPORTED_NETWORKS
from ...identity.secure_egress import outbound_request
from ...identity.secure_egress import resolve_outbound_target
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from operator import eq
from operator import ge
from operator import gt
from operator import le
from operator import lt
from operator import ne
from typing import Any
from typing import cast
import httpx
import os
import re


def _sw_http_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _normalized_text(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key)
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return default


def _sw_extract_urls(text: str) -> list[str]:
    return [match.group(0) for match in re.finditer("https?://[^\\s)\\]>]+", text)]


def _sw_conditional_metrics(st: "_SocialWorkspaceState", tenant_id: str) -> dict[str, float]:
    with st.lock:
        queued_posts = sum(
            (
                1
                for post in st.scheduled_posts
                if post.get("tenant_id") == tenant_id and post.get("status") == "scheduled"
            )
        )
        draft_posts = sum(
            (1 for post in st.scheduled_posts if post.get("tenant_id") == tenant_id and post.get("status") == "draft")
        )
        inbox_unread = sum(
            (
                1
                for item in st.inbox_messages
                if item.get("tenant_id") == tenant_id and item.get("status") not in {"responded", "complete"}
            )
        )
        connected_accounts = sum((1 for account in st.social_accounts if account.get("tenant_id") == tenant_id))
    return {
        "queued_posts": float(queued_posts),
        "draft_posts": float(draft_posts),
        "inbox_unread": float(inbox_unread),
        "connected_accounts": float(connected_accounts),
    }


def _sw_evaluate_conditions(st: "_SocialWorkspaceState", tenant_id: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
    if not rules:
        return {"passed": True, "results": [], "metrics": _sw_conditional_metrics(st, tenant_id)}
    metrics = _sw_conditional_metrics(st, tenant_id)
    operators: dict[str, Callable[[float, float], bool]] = {
        "gt": gt,
        "gte": ge,
        "lt": lt,
        "lte": le,
        "eq": eq,
        "neq": ne,
    }
    comparisons: list[dict[str, Any]] = []
    passed = True
    for rule in rules:
        metric = str(rule.get("metric") or "").strip().lower()
        operator = str(rule.get("operator") or "gte").strip().lower()
        try:
            expected = float(rule.get("value"))
        except (TypeError, ValueError):
            expected = 0.0
        actual = float(metrics.get(metric, 0.0))
        comparator = operators.get(operator)
        ok = metric in metrics and comparator is not None and comparator(actual, expected)
        if not ok:
            passed = False
        comparisons.append(
            {"metric": metric, "operator": operator, "expected": expected, "actual": actual, "passed": ok}
        )
    return {"passed": passed, "results": comparisons, "metrics": metrics}


def _sw_deliver_webhook(
    url: str, event_type: str, payload: dict[str, Any], secret: str | None = None
) -> dict[str, Any]:
    headers = {"Content-Type": JSON_CONTENT_TYPE, "User-Agent": "NuxtronSocial/1.0"}
    if secret and secret.strip():
        headers["X-Nuxtron-Webhook-Secret"] = secret.strip()
    body = {"event_type": event_type, "occurred_at": datetime.now(UTC).isoformat(), "payload": payload}
    try:
        target = resolve_outbound_target(url)
        response = outbound_request(
            "POST",
            target,
            headers=headers,
            json=body,
            timeout=12.0,
            max_response_bytes=64_000,
        )
        return {"ok": response.status_code < 300, "status_code": response.status_code}
    except Exception as exc:
        return {"ok": False, "status_code": 0, "error": f"Webhook delivery failed ({type(exc).__name__})."}


def _sw_resolve_canva_asset_url(payload: CanvaImportRequest) -> str:
    if payload.design_url and payload.design_url.strip():
        return payload.design_url.strip()
    if not payload.design_id or not payload.design_id.strip():
        raise _sw_http_error(status_code=422, detail="Provide either design_url or design_id for Canva import.")
    api_base = os.getenv("CANVA_API_BASE_URL", "https://api.canva.com/rest/v1").strip().rstrip("/")
    token = os.getenv("CANVA_ACCESS_TOKEN", "").strip()
    if not token:
        raise _sw_http_error(status_code=503, detail="CANVA_ACCESS_TOKEN is not configured.")
    design_id = payload.design_id.strip()
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{api_base}/designs/{design_id}/exports",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
        if resp.status_code >= 400:
            raise _sw_http_error(status_code=502, detail=f"Canva export fetch failed with status {resp.status_code}.")
        body = resp.json()
        exports = cast(list[dict[str, Any]], body.get("items") or body.get("exports") or [])
        export_url = ""
        if exports:
            export_url = str(exports[0].get("url") or exports[0].get("download_url") or "").strip()
        if not export_url:
            export_url = str(body.get("url") or body.get("download_url") or "").strip()
        if not export_url:
            raise _sw_http_error(status_code=502, detail="Canva API did not return an export URL.")
        return export_url
    except HTTPException:
        raise
    except Exception as exc:
        raise _sw_http_error(status_code=502, detail=f"Canva import failed: {str(exc)}")


def _sw_seed_notifications(st: _SocialWorkspaceState, tenant_id: str, network: str, account_name: str) -> None:
    st.notifications.append(
        {
            "id": len(st.notifications) + 1,
            "tenant_id": tenant_id,
            "title": f"{SUPPORTED_NETWORKS.get(network, {}).get('label', network.title())} connected",
            "message": f"{account_name} is now connected and ready for publishing plus inbox sync.",
            "category": "social",
            "priority": "info",
            "read": False,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )


def _sw_seed_inbox_messages(st: _SocialWorkspaceState, tenant_id: str, network: str, handle: str) -> None:
    starter_messages = [
        ("comment", f"Love the latest post from @{handle}. Can you share pricing?"),
        ("dm", f"Hi @{handle}, interested in a demo for our team."),
        ("mention", f"Comparing @{handle} with competitors this week. Strong creative work."),
    ]
    for source_type, text in starter_messages:
        st.inbox_messages.append(
            {
                "id": len(st.inbox_messages) + 1,
                "tenant_id": tenant_id,
                "network": network,
                "source_type": source_type,
                "external_message_id": f"{network}-{len(st.inbox_messages) + 1}",
                "parent_message_id": None,
                "author_handle": f"{source_type}_fan_{len(st.inbox_messages) + 1}",
                "author_display_name": source_type.title(),
                "author_follower_count": 1800 + len(st.inbox_messages) * 120,
                "crm_contact_id": None,
                "text": text,
                "message_type": "question" if source_type != "mention" else "conversation",
                "sentiment": "positive",
                "classification_confidence": 0.92,
                "priority_score": 74,
                "suggested_replies": [
                    "Thanks for reaching out. We can help you get started right away.",
                    "Happy to share details. Sending the next step here.",
                ],
                "status": "pending",
                "assigned_to": None,
                "due_at": None,
                "tags": [network],
                "replied": False,
                "replied_at": None,
                "read": False,
                "read_at": None,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )


def _sw_seed_post_history(st: _SocialWorkspaceState, tenant_id: str, network: str, account_id: int) -> None:
    for index in range(6):
        published_at = datetime.now(UTC) - timedelta(days=index + 1)
        engagements = 140 + index * 18
        impressions = 2200 + index * 190
        st.viralpost_history.append(
            {
                "id": len(st.viralpost_history) + 1,
                "tenant_id": tenant_id,
                "network": network,
                "profile_id": str(account_id),
                "content_type": "image",
                "published_at": published_at.isoformat(),
                "impressions": impressions,
                "reach": impressions - 220,
                "engagements": engagements,
                "likes": int(engagements * 0.62),
                "comments": int(engagements * 0.14),
                "shares": int(engagements * 0.1),
                "link_clicks": int(engagements * 0.21),
                "engagement_rate": round(engagements / max(impressions, 1), 6),
                "dedup_key": f"{tenant_id}-{network}-{account_id}-{index}",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )


def _sw_seed_listening(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((item.get("tenant_id") == tenant_id for item in st.listening_keywords)):
            return
        now = datetime.now(UTC).isoformat()
        st.listening_keywords.extend(
            [
                {
                    "id": 1,
                    "tenant_id": tenant_id,
                    "keyword": f"@{tenant_id}",
                    "networks": ["instagram", "x", "facebook", "linkedin", "reddit"],
                    "alert_threshold": 500,
                    "alert_on_crisis": True,
                    "created_at": now,
                },
                {
                    "id": 2,
                    "tenant_id": tenant_id,
                    "keyword": "#BrandName",
                    "networks": ["instagram", "x", "tiktok"],
                    "alert_threshold": 200,
                    "alert_on_crisis": True,
                    "created_at": now,
                },
                {
                    "id": 3,
                    "tenant_id": tenant_id,
                    "keyword": "competitor OR rival",
                    "networks": ["x", "reddit", "linkedin"],
                    "alert_threshold": 1000,
                    "alert_on_crisis": False,
                    "created_at": now,
                },
            ]
        )
        st.listening_mentions.extend(
            [
                {
                    "id": 1,
                    "tenant_id": tenant_id,
                    "keyword_id": 1,
                    "network": "x",
                    "author": "@customer_a",
                    "text": "Great experience with the platform!",
                    "sentiment": "positive",
                    "reach": 4200,
                    "engagement": 312,
                    "is_crisis": False,
                    "alert_dismissed": False,
                    "created_at": now,
                },
                {
                    "id": 2,
                    "tenant_id": tenant_id,
                    "keyword_id": 1,
                    "network": "facebook",
                    "author": "ReviewUser",
                    "text": "Had a billing issue that was never resolved.",
                    "sentiment": "negative",
                    "reach": 1800,
                    "engagement": 89,
                    "is_crisis": True,
                    "alert_dismissed": False,
                    "created_at": now,
                },
                {
                    "id": 3,
                    "tenant_id": tenant_id,
                    "keyword_id": 2,
                    "network": "instagram",
                    "author": "@influencer_x",
                    "text": "Loving the new campaign features!",
                    "sentiment": "positive",
                    "reach": 28000,
                    "engagement": 2100,
                    "is_crisis": False,
                    "alert_dismissed": False,
                    "created_at": now,
                },
                {
                    "id": 4,
                    "tenant_id": tenant_id,
                    "keyword_id": 1,
                    "network": "reddit",
                    "author": "u/anon_reviewer",
                    "text": "The platform crashed during our live stream.",
                    "sentiment": "negative",
                    "reach": 6700,
                    "engagement": 520,
                    "is_crisis": True,
                    "alert_dismissed": False,
                    "created_at": now,
                },
            ]
        )


def _sw_seed_monitoring_streams(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((item.get("tenant_id") == tenant_id for item in st.monitoring_streams)):
            return
        now = datetime.now(UTC).isoformat()
        st.monitoring_streams.extend(
            [
                {
                    "id": 1,
                    "tenant_id": tenant_id,
                    "name": "Brand Mentions",
                    "stream_type": "keyword",
                    "query": f"@{tenant_id}",
                    "networks": ["x", "instagram", "facebook"],
                    "column_index": 0,
                    "created_at": now,
                    "feed": [
                        {
                            "id": "f1",
                            "author": "@user_alpha",
                            "network": "x",
                            "text": "Really impressed by the automation tools!",
                            "engagement": 88,
                            "sentiment": "positive",
                            "posted_at": now,
                        },
                        {
                            "id": "f2",
                            "author": "@brand_watcher",
                            "network": "instagram",
                            "text": "Coverage of the new product launch 🚀",
                            "engagement": 340,
                            "sentiment": "positive",
                            "posted_at": now,
                        },
                    ],
                },
                {
                    "id": 2,
                    "tenant_id": tenant_id,
                    "name": "Competitor Watch",
                    "stream_type": "keyword",
                    "query": "competitor1 OR competitor2",
                    "networks": ["x", "linkedin", "reddit"],
                    "column_index": 1,
                    "created_at": now,
                    "feed": [
                        {
                            "id": "f3",
                            "author": "u/industry_analyst",
                            "network": "reddit",
                            "text": "Competitor just dropped pricing 20%.",
                            "engagement": 210,
                            "sentiment": "neutral",
                            "posted_at": now,
                        }
                    ],
                },
                {
                    "id": 3,
                    "tenant_id": tenant_id,
                    "name": "Industry Trends",
                    "stream_type": "hashtag",
                    "query": "#SocialMediaMarketing",
                    "networks": ["instagram", "x", "linkedin", "tiktok"],
                    "column_index": 2,
                    "created_at": now,
                    "feed": [
                        {
                            "id": "f4",
                            "author": "@marketing_guru",
                            "network": "linkedin",
                            "text": "AI is transforming how brands engage audiences in 2026.",
                            "engagement": 1450,
                            "sentiment": "positive",
                            "posted_at": now,
                        },
                        {
                            "id": "f5",
                            "author": "@social_pro",
                            "network": "x",
                            "text": "Short-form video continues dominating organic reach.",
                            "engagement": 890,
                            "sentiment": "positive",
                            "posted_at": now,
                        },
                    ],
                },
            ]
        )


def _sw_seed_ad_campaigns(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((item.get("tenant_id") == tenant_id for item in st.social_ad_campaigns)):
            return
        now = datetime.now(UTC).isoformat()
        st.social_ad_campaigns.extend(
            [
                {
                    "id": 1,
                    "tenant_id": tenant_id,
                    "name": "Q2 Brand Awareness",
                    "objective": "awareness",
                    "network": "facebook",
                    "status": "active",
                    "budget_daily": 150.0,
                    "budget_total": 3000.0,
                    "spent": 1240.5,
                    "impressions": 485000,
                    "reach": 312000,
                    "clicks": 8900,
                    "conversions": 420,
                    "ctr": 1.84,
                    "cpc": 0.14,
                    "roas": 4.2,
                    "start_date": "2026-04-01",
                    "end_date": "2026-06-30",
                    "audience_targeting": {"age": "25-44", "interests": ["marketing", "technology"]},
                    "creative_ids": [],
                    "created_at": now,
                },
                {
                    "id": 2,
                    "tenant_id": tenant_id,
                    "name": "Product Launch Retargeting",
                    "objective": "conversions",
                    "network": "instagram",
                    "status": "active",
                    "budget_daily": 80.0,
                    "budget_total": 1600.0,
                    "spent": 640.0,
                    "impressions": 128000,
                    "reach": 89000,
                    "clicks": 4200,
                    "conversions": 280,
                    "ctr": 3.28,
                    "cpc": 0.15,
                    "roas": 6.8,
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-31",
                    "audience_targeting": {"custom_audience": "website_visitors_30d"},
                    "creative_ids": [],
                    "created_at": now,
                },
                {
                    "id": 3,
                    "tenant_id": tenant_id,
                    "name": "LinkedIn Lead Gen",
                    "objective": "lead_generation",
                    "network": "linkedin",
                    "status": "paused",
                    "budget_daily": 200.0,
                    "budget_total": 4000.0,
                    "spent": 920.0,
                    "impressions": 42000,
                    "reach": 28000,
                    "clicks": 1800,
                    "conversions": 95,
                    "ctr": 4.29,
                    "cpc": 0.51,
                    "roas": 3.1,
                    "start_date": "2026-03-15",
                    "end_date": "2026-06-15",
                    "audience_targeting": {"job_titles": ["Marketing Manager", "CMO", "VP Marketing"]},
                    "creative_ids": [],
                    "created_at": now,
                },
            ]
        )


def _sw_seed_reports(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        if any((item.get("tenant_id") == tenant_id for item in st.reports)):
            return
        now = datetime.now(UTC).isoformat()
        st.reports.extend(
            [
                {
                    "id": 1,
                    "tenant_id": tenant_id,
                    "name": "Monthly Overview — May 2026",
                    "report_type": "overview",
                    "networks": ["instagram", "x", "facebook", "linkedin"],
                    "date_range_days": 30,
                    "metrics": ["impressions", "reach", "engagement", "clicks", "conversions"],
                    "export_format": "pdf",
                    "schedule": "monthly",
                    "status": "ready",
                    "data": {
                        "total_impressions": 840000,
                        "total_reach": 620000,
                        "total_engagement": 48000,
                        "total_clicks": 12400,
                        "total_conversions": 980,
                        "engagement_rate": 5.7,
                        "top_network": "instagram",
                        "top_post_id": "p_001",
                    },
                    "created_at": now,
                    "generated_at": now,
                },
                {
                    "id": 2,
                    "tenant_id": tenant_id,
                    "name": "Competitor Benchmark Q2",
                    "report_type": "benchmark",
                    "networks": ["x", "linkedin"],
                    "date_range_days": 90,
                    "metrics": ["engagement_rate", "follower_growth", "posting_frequency"],
                    "export_format": "excel",
                    "schedule": "quarterly",
                    "status": "ready",
                    "data": {
                        "your_engagement_rate": 5.7,
                        "industry_avg_engagement": 3.2,
                        "top_competitor_engagement": 6.1,
                        "percentile": 78,
                    },
                    "created_at": now,
                    "generated_at": now,
                },
            ]
        )


def _sw_seed_competitors(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        existing = [item for item in st.competitor_profiles if item.get("tenant_id") == tenant_id]
        if existing:
            return
        now = datetime.now(UTC).isoformat()
        seeded_profiles = [
            {
                "id": len(st.competitor_profiles) + 1,
                "tenant_id": tenant_id,
                "handle": "@sproutsocial",
                "competitor": "Sprout Social",
                "network": "linkedin",
                "followers": 148000,
                "engagement_rate": 4.8,
                "average_likes": 910,
                "average_comments": 64,
                "posting_frequency": "2 posts/day",
                "best_posting_time": "Tue 10:00 AM",
                "created_at": now,
            },
            {
                "id": len(st.competitor_profiles) + 2,
                "tenant_id": tenant_id,
                "handle": "@hootsuite",
                "competitor": "Hootsuite",
                "network": "x",
                "followers": 326000,
                "engagement_rate": 3.9,
                "average_likes": 580,
                "average_comments": 41,
                "posting_frequency": "3 posts/day",
                "best_posting_time": "Wed 12:00 PM",
                "created_at": now,
            },
        ]
        st.competitor_profiles.extend(seeded_profiles)
        for profile in seeded_profiles:
            st.competitor_snapshots.append(
                {
                    "id": len(st.competitor_snapshots) + 1,
                    "tenant_id": tenant_id,
                    "competitor_profile_id": profile["id"],
                    "followers": profile["followers"],
                    "engagement_rate": profile["engagement_rate"],
                    "average_likes": profile["average_likes"],
                    "average_comments": profile["average_comments"],
                    "captured_at": now,
                }
            )


def _sw_seed_reviews(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        existing = [item for item in st.reviews if item.get("tenant_id") == tenant_id]
        if existing:
            return
        st.reviews.extend(
            [
                {
                    "id": len(st.reviews) + 1,
                    "tenant_id": tenant_id,
                    "platform": "google",
                    "author": "A. Patel",
                    "rating": 2,
                    "text": "Support took too long to respond to our campaign issue.",
                    "status": "open",
                    "sentiment": "negative",
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
                {
                    "id": len(st.reviews) + 2,
                    "tenant_id": tenant_id,
                    "platform": "facebook",
                    "author": "J. Kim",
                    "rating": 5,
                    "text": "Excellent campaign outcomes and quick turnaround.",
                    "status": "responded",
                    "sentiment": "positive",
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            ]
        )


def _sw_seed_influencers(st: _SocialWorkspaceState) -> None:
    with st.lock:
        if st.influencer_profiles:
            return
        st.influencer_profiles.extend(
            [
                {
                    "id": "inf-001",
                    "name": "Nora Reed",
                    "handle": "@nora.creates",
                    "platform": "instagram",
                    "followers": 68500,
                    "engagement_rate": 4.7,
                    "category": "saas",
                    "fit_score": 91,
                },
                {
                    "id": "inf-002",
                    "name": "Leo Martin",
                    "handle": "@leogrowth",
                    "platform": "linkedin",
                    "followers": 42300,
                    "engagement_rate": 5.2,
                    "category": "b2b",
                    "fit_score": 88,
                },
                {
                    "id": "inf-003",
                    "name": "Mina Park",
                    "handle": "@mina.ai",
                    "platform": "youtube",
                    "followers": 112000,
                    "engagement_rate": 3.6,
                    "category": "automation",
                    "fit_score": 86,
                },
            ]
        )


def _sw_seed_saved_replies(st: _SocialWorkspaceState, tenant_id: str) -> None:
    with st.lock:
        existing = [item for item in st.saved_replies if item.get("tenant_id") == tenant_id]
        if existing:
            return
        st.saved_replies.extend(
            [
                {
                    "id": len(st.saved_replies) + 1,
                    "tenant_id": tenant_id,
                    "title": "Demo request",
                    "body": "Thanks for reaching out. We would be happy to schedule a tailored demo for your team.",
                    "category": "sales",
                    "created_at": datetime.now(UTC).isoformat(),
                },
                {
                    "id": len(st.saved_replies) + 2,
                    "tenant_id": tenant_id,
                    "title": "Support follow-up",
                    "body": "We have logged this with our support team and will share an update shortly.",
                    "category": "support",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            ]
        )
