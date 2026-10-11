"""Social use cases: get competitor insights."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.schemas import AdBoostRequest
from ....domains.social.schemas import AdCampaignCreateRequest
from ....domains.social.schemas import CompetitorTrackRequest
from ....domains.social.schemas import ListeningAlertDismissRequest
from ....domains.social.schemas import ListeningKeywordRequest
from ....domains.social.schemas import StreamCreateRequest
from ....domains.social.schemas import StreamUpdateRequest
from ..constants import AuthDep
from ..services.capabilities import _require_any_env_for_strict_social
from ..services.workspace import _sw_http_error
from ..services.workspace import _sw_seed_ad_campaigns
from ..services.workspace import _sw_seed_competitors
from ..services.workspace import _sw_seed_listening
from ..services.workspace import _sw_seed_monitoring_streams
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import APIRouter
from typing import Any


def operation_get_competitor_insights(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep
) -> list[dict[str, Any]]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:competitors:insights", 240, 60)
    _sw_seed_competitors(st, auth.tenant_id)
    with st.lock:
        profiles = [item.copy() for item in st.competitor_profiles if item.get("tenant_id") == auth.tenant_id]
        snapshots = [item.copy() for item in st.competitor_snapshots if item.get("tenant_id") == auth.tenant_id]
    latest_snapshot_by_profile: dict[int, dict[str, Any]] = {}
    for snapshot in sorted(snapshots, key=lambda item: str(item.get("captured_at") or "")):
        profile_id = int(snapshot.get("competitor_profile_id") or 0)
        latest_snapshot_by_profile[profile_id] = snapshot
    insights: list[dict[str, Any]] = []
    for profile in profiles:
        profile_id = int(profile.get("id") or 0)
        snapshot = latest_snapshot_by_profile.get(profile_id, {})
        insights.append(
            {
                "competitor": profile.get("competitor") or str(profile.get("handle") or "").lstrip("@") or "Competitor",
                "network": profile.get("network") or "instagram",
                "followers": int(snapshot.get("followers") or profile.get("followers") or 0),
                "engagement_rate": float(snapshot.get("engagement_rate") or profile.get("engagement_rate") or 0.0),
                "average_likes": int(snapshot.get("average_likes") or profile.get("average_likes") or 0),
                "average_comments": int(snapshot.get("average_comments") or profile.get("average_comments") or 0),
                "posting_frequency": profile.get("posting_frequency") or "Unknown",
                "best_posting_time": profile.get("best_posting_time") or "Unknown",
            }
        )
    return insights


def operation_track_competitor(
    st: _SocialWorkspaceState, router: APIRouter, payload: CompetitorTrackRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:competitors:track", 120, 60)
    _sw_seed_competitors(st, auth.tenant_id)
    clean_handle = payload.handle.strip()
    if not clean_handle.startswith("@"):
        clean_handle = f"@{clean_handle}"
    now = datetime.now(UTC).isoformat()
    competitor_name = clean_handle.lstrip("@").replace("-", " ").replace("_", " ").strip() or "Competitor"
    competitor_name = " ".join((part.capitalize() for part in competitor_name.split()))
    with st.lock:
        existing = next(
            (
                item
                for item in st.competitor_profiles
                if item.get("tenant_id") == auth.tenant_id
                and str(item.get("handle") or "").lower() == clean_handle.lower()
                and (str(item.get("network") or "").lower() == payload.network.strip().lower())
            ),
            None,
        )
        if existing is not None:
            profile = existing
        else:
            profile = {
                "id": len(st.competitor_profiles) + 1,
                "tenant_id": auth.tenant_id,
                "handle": clean_handle,
                "competitor": competitor_name,
                "network": payload.network.strip().lower(),
                "followers": 18000 + len(st.competitor_profiles) * 2750,
                "engagement_rate": round(2.8 + len(st.competitor_profiles) % 5 * 0.6, 1),
                "average_likes": 120 + len(st.competitor_profiles) * 18,
                "average_comments": 14 + len(st.competitor_profiles) * 3,
                "posting_frequency": "1 post/day",
                "best_posting_time": "Thu 11:00 AM",
                "created_at": now,
            }
            st.competitor_profiles.append(profile)
        st.competitor_snapshots.append(
            {
                "id": len(st.competitor_snapshots) + 1,
                "tenant_id": auth.tenant_id,
                "competitor_profile_id": profile["id"],
                "followers": profile["followers"],
                "engagement_rate": profile["engagement_rate"],
                "average_likes": profile["average_likes"],
                "average_comments": profile["average_comments"],
                "captured_at": now,
            }
        )
        created = profile.copy()
    _sw_audit(st, auth.tenant_id, "social_competitor_tracked", created["id"])
    return {
        "competitor": created.get("competitor"),
        "network": created.get("network"),
        "followers": int(created.get("followers") or 0),
        "engagement_rate": float(created.get("engagement_rate") or 0.0),
        "average_likes": int(created.get("average_likes") or 0),
        "average_comments": int(created.get("average_comments") or 0),
        "posting_frequency": created.get("posting_frequency") or "Unknown",
        "best_posting_time": created.get("best_posting_time") or "Unknown",
    }


def operation_list_listening_keywords(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:listening:keywords", 240, 60)
    _sw_seed_listening(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.listening_keywords if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "keywords": items}


def operation_create_listening_keyword(
    st: _SocialWorkspaceState, router: APIRouter, payload: ListeningKeywordRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:listening:keywords:create", 120, 60)
    with st.lock:
        keyword = {
            "id": len(st.listening_keywords) + 1,
            "tenant_id": auth.tenant_id,
            "keyword": payload.keyword.strip(),
            "networks": payload.networks,
            "alert_threshold": payload.alert_threshold,
            "alert_on_crisis": payload.alert_on_crisis,
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.listening_keywords.append(keyword)
        created = keyword.copy()
    _sw_audit(st, auth.tenant_id, "social_listening_keyword_created", created["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "keyword": created,
        "telemetry_event": "social.listening.keyword_created",
    }


def operation_delete_listening_keyword(
    st: _SocialWorkspaceState, router: APIRouter, keyword_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:listening:keywords:delete", 120, 60)
    with st.lock:
        idx = next(
            (
                i
                for i, item in enumerate(st.listening_keywords)
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == keyword_id
            ),
            None,
        )
        if idx is None:
            raise _sw_http_error(status_code=404, detail="Keyword not found.")
        st.listening_keywords.pop(idx)
    _sw_audit(st, auth.tenant_id, "social_listening_keyword_deleted", keyword_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted_id": keyword_id}


def operation_list_listening_mentions(
    st: _SocialWorkspaceState, router: APIRouter, crisis_only: bool = False, *, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:listening:mentions", 240, 60)
    _sw_seed_listening(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.listening_mentions if item.get("tenant_id") == auth.tenant_id]
    if crisis_only:
        items = [item for item in items if item.get("is_crisis")]
    summary = {
        "total": len(items),
        "crisis": sum((1 for item in items if item.get("is_crisis"))),
        "positive": sum((1 for item in items if item.get("sentiment") == "positive")),
        "negative": sum((1 for item in items if item.get("sentiment") == "negative")),
        "neutral": sum((1 for item in items if item.get("sentiment") == "neutral")),
        "total_reach": sum((int(item.get("reach") or 0) for item in items)),
    }
    return {"status": "ok", "tenant_id": auth.tenant_id, "summary": summary, "mentions": items}


def operation_dismiss_listening_alert(
    st: _SocialWorkspaceState, router: APIRouter, mention_id: int, payload: ListeningAlertDismissRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:listening:dismiss", 180, 60)
    with st.lock:
        mention = next(
            (
                item
                for item in st.listening_mentions
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == mention_id
            ),
            None,
        )
        if mention is None:
            raise _sw_http_error(status_code=404, detail="Mention not found.")
        mention["alert_dismissed"] = payload.dismissed
        mention["updated_at"] = datetime.now(UTC).isoformat()
        updated = mention.copy()
    _sw_audit(st, auth.tenant_id, "social_listening_alert_dismissed", mention_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "mention": updated}


def operation_get_listening_sentiment(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:listening:sentiment", 240, 60)
    _sw_seed_listening(st, auth.tenant_id)
    with st.lock:
        mentions = [item.copy() for item in st.listening_mentions if item.get("tenant_id") == auth.tenant_id]
    total = len(mentions) or 1
    positive = sum((1 for m in mentions if m.get("sentiment") == "positive"))
    negative = sum((1 for m in mentions if m.get("sentiment") == "negative"))
    neutral = total - positive - negative
    score = round((positive - negative) / total * 100, 1)
    if score > 20:
        sentiment_label = "positive"
    elif score < -20:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "sentiment_score": score,
        "label": sentiment_label,
        "breakdown": {"positive": positive, "neutral": neutral, "negative": negative, "total": total},
        "network_breakdown": {
            net: {
                "positive": sum((1 for m in mentions if m.get("network") == net and m.get("sentiment") == "positive")),
                "negative": sum((1 for m in mentions if m.get("network") == net and m.get("sentiment") == "negative")),
            }
            for net in {"instagram", "x", "facebook", "linkedin", "reddit"}
        },
    }


def operation_list_monitoring_streams(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:streams:list", 240, 60)
    _sw_seed_monitoring_streams(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.monitoring_streams if item.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda x: int(x.get("column_index") or 0))
    return {"status": "ok", "tenant_id": auth.tenant_id, "streams": items}


def operation_create_monitoring_stream(
    st: _SocialWorkspaceState, router: APIRouter, payload: StreamCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:streams:create", 120, 60)
    with st.lock:
        stream = {
            "id": len(st.monitoring_streams) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name.strip(),
            "stream_type": payload.stream_type.strip(),
            "query": payload.query.strip(),
            "networks": payload.networks,
            "column_index": payload.column_index,
            "feed": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.monitoring_streams.append(stream)
        created = stream.copy()
    _sw_audit(st, auth.tenant_id, "social_stream_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "stream": created, "telemetry_event": "social.streams.created"}


def operation_update_monitoring_stream(
    st: _SocialWorkspaceState, router: APIRouter, stream_id: int, payload: StreamUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:streams:update", 180, 60)
    with st.lock:
        stream = next(
            (
                item
                for item in st.monitoring_streams
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == stream_id
            ),
            None,
        )
        if stream is None:
            raise _sw_http_error(status_code=404, detail="Stream not found.")
        if payload.name is not None:
            stream["name"] = payload.name.strip()
        if payload.query is not None:
            stream["query"] = payload.query.strip()
        if payload.column_index is not None:
            stream["column_index"] = payload.column_index
        stream["updated_at"] = datetime.now(UTC).isoformat()
        updated = stream.copy()
    _sw_audit(st, auth.tenant_id, "social_stream_updated", stream_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "stream": updated}


def operation_delete_monitoring_stream(
    st: _SocialWorkspaceState, router: APIRouter, stream_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:streams:delete", 120, 60)
    with st.lock:
        idx = next(
            (
                i
                for i, item in enumerate(st.monitoring_streams)
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == stream_id
            ),
            None,
        )
        if idx is None:
            raise _sw_http_error(status_code=404, detail="Stream not found.")
        st.monitoring_streams.pop(idx)
    _sw_audit(st, auth.tenant_id, "social_stream_deleted", stream_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted_id": stream_id}


def operation_list_ad_campaigns(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    _require_any_env_for_strict_social(
        ["META_ADS_ACCESS_TOKEN", "META_ACCESS_TOKEN", "TIKTOK_ADS_ACCESS_TOKEN", "TIKTOK_ACCESS_TOKEN"],
        "paid social ads campaigns",
    )
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ads:campaigns:list", 240, 60)
    _sw_seed_ad_campaigns(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.social_ad_campaigns if item.get("tenant_id") == auth.tenant_id]
    summary = {
        "total_campaigns": len(items),
        "active": sum((1 for item in items if item.get("status") == "active")),
        "total_spent": round(sum((float(item.get("spent") or 0) for item in items)), 2),
        "total_impressions": sum((int(item.get("impressions") or 0) for item in items)),
        "total_conversions": sum((int(item.get("conversions") or 0) for item in items)),
        "avg_roas": round(sum((float(item.get("roas") or 0) for item in items)) / max(len(items), 1), 2),
    }
    return {"status": "ok", "tenant_id": auth.tenant_id, "summary": summary, "campaigns": items}


def operation_create_ad_campaign(
    st: _SocialWorkspaceState, router: APIRouter, payload: AdCampaignCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    _require_any_env_for_strict_social(
        ["META_ADS_ACCESS_TOKEN", "META_ACCESS_TOKEN", "TIKTOK_ADS_ACCESS_TOKEN", "TIKTOK_ACCESS_TOKEN"],
        "paid social ads campaign creation",
    )
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ads:campaigns:create", 60, 60)
    with st.lock:
        campaign = {
            "id": len(st.social_ad_campaigns) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name.strip(),
            "objective": payload.objective.strip(),
            "network": payload.network.strip(),
            "status": "pending_review",
            "budget_daily": payload.budget_daily,
            "budget_total": payload.budget_total,
            "spent": 0.0,
            "impressions": 0,
            "reach": 0,
            "clicks": 0,
            "conversions": 0,
            "ctr": 0.0,
            "cpc": 0.0,
            "roas": 0.0,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "audience_targeting": payload.audience_targeting,
            "creative_ids": payload.creative_ids,
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.social_ad_campaigns.append(campaign)
        created = campaign.copy()
    _sw_audit(st, auth.tenant_id, "social_ad_campaign_created", created["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "campaign": created,
        "telemetry_event": "social.ads.campaign_created",
    }


def operation_update_ad_campaign_status(
    st: _SocialWorkspaceState, router: APIRouter, campaign_id: int, status: str, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ads:campaigns:status", 120, 60)
    allowed = {"active", "paused", "archived", "pending_review"}
    if status not in allowed:
        raise _sw_http_error(status_code=422, detail=f"Status must be one of {sorted(allowed)}")
    with st.lock:
        campaign = next(
            (
                item
                for item in st.social_ad_campaigns
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == campaign_id
            ),
            None,
        )
        if campaign is None:
            raise _sw_http_error(status_code=404, detail="Campaign not found.")
        campaign["status"] = status
        campaign["updated_at"] = datetime.now(UTC).isoformat()
        updated = campaign.copy()
    _sw_audit(st, auth.tenant_id, "social_ad_campaign_status_updated", campaign_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": updated}


def operation_boost_organic_post(
    st: _SocialWorkspaceState, router: APIRouter, payload: AdBoostRequest, auth: AuthDep
) -> dict[str, Any]:
    _require_any_env_for_strict_social(
        ["META_ADS_ACCESS_TOKEN", "META_ACCESS_TOKEN", "TIKTOK_ADS_ACCESS_TOKEN", "TIKTOK_ACCESS_TOKEN"],
        "paid social ads boosts",
    )
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ads:boost", 60, 60)
    with st.lock:
        boost = {
            "id": len(st.social_ad_boosts) + 1,
            "tenant_id": auth.tenant_id,
            "post_id": payload.post_id.strip(),
            "network": payload.network.strip(),
            "budget_total": payload.budget_total,
            "duration_days": payload.duration_days,
            "objective": payload.objective.strip(),
            "status": "active",
            "spent": 0.0,
            "impressions": 0,
            "clicks": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(days=payload.duration_days)).isoformat(),
        }
        st.social_ad_boosts.append(boost)
        created = boost.copy()
    _sw_audit(st, auth.tenant_id, "social_ad_boost_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "boost": created, "telemetry_event": "social.ads.post_boosted"}
