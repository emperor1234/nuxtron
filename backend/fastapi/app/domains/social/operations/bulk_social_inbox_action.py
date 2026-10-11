"""Social use cases: bulk social inbox action."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.schemas import AdvocacyAssetCreateRequest
from ....domains.social.schemas import InboxBulkActionRequest
from ....domains.social.schemas import InfluencerAdvocacyBridgeRequest
from ....domains.social.schemas import InfluencerSearchRequest
from ....domains.social.schemas import InfluencerShortlistRequest
from ....domains.social.schemas import ReviewCaseCreateRequest
from ....domains.social.schemas import ReviewReplyRequest
from ....domains.social.schemas import ReviewStatusRequest
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..constants import REVIEW_NOT_FOUND
from ..services.workspace import _sw_http_error
from ..services.workspace import _sw_seed_influencers
from ..services.workspace import _sw_seed_reviews
from ..services.workspace_connect_account import _sw_seed_inbox_for_tenant
from datetime import UTC
from datetime import datetime
from fastapi import APIRouter
from typing import Any


def operation_bulk_social_inbox_action(
    st: _SocialWorkspaceState, router: APIRouter, payload: InboxBulkActionRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:bulk-action", 90, 60)
    _sw_seed_inbox_for_tenant(st, auth.tenant_id)
    action = payload.action.strip().lower()
    if action not in {"claim", "complete"}:
        raise _sw_http_error(status_code=400, detail="Unsupported inbox bulk action.")
    if action == "claim" and (not payload.agent_name.strip()):
        raise _sw_http_error(status_code=400, detail="Agent name is required for claim action.")
    updated_messages: list[dict[str, Any]] = []
    missing_ids: list[int] = []
    now = datetime.now(UTC).isoformat()
    with st.lock:
        unique_message_ids = list(dict.fromkeys(payload.message_ids))
        for message_id in unique_message_ids:
            message = next(
                (
                    item
                    for item in st.inbox_messages
                    if item.get("tenant_id") == auth.tenant_id and item.get("id") == message_id
                ),
                None,
            )
            if message is None:
                missing_ids.append(message_id)
                continue
            if action == "claim":
                message["assigned_to"] = payload.agent_name.strip()
                message["collision_state"] = "claimed"
            else:
                message["status"] = "complete"
                message["completed_at"] = now
            message["read"] = True
            message["read_at"] = now
            message["updated_at"] = now
            updated_messages.append(message.copy())
    if not updated_messages:
        raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
    with st.lock:
        tenant_messages = [item for item in st.inbox_messages if item.get("tenant_id") == auth.tenant_id]
    summary = {
        "open": sum((1 for item in tenant_messages if item.get("status") not in {"responded", "complete"})),
        "responded": sum((1 for item in tenant_messages if item.get("status") == "responded")),
        "complete": sum((1 for item in tenant_messages if item.get("status") == "complete")),
        "claimed": sum((1 for item in tenant_messages if item.get("collision_state") == "claimed")),
    }
    _sw_audit(st, auth.tenant_id, f"social_inbox_bulk_{action}", updated_messages[0].get("id"))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "action": action,
        "updated_messages": updated_messages,
        "updated_count": len(updated_messages),
        "missing_ids": missing_ids,
        "summary": summary,
        "telemetry_event": f"social.inbox.bulk_{action}",
    }


def operation_list_social_reviews(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:reviews:list", 240, 60)
    _sw_seed_reviews(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.reviews if item.get("tenant_id") == auth.tenant_id]
    summary = {
        "total": len(items),
        "open": sum((1 for item in items if item.get("status") == "open")),
        "responded": sum((1 for item in items if item.get("status") == "responded")),
        "resolved": sum((1 for item in items if item.get("status") == "resolved")),
    }
    return {"status": "ok", "tenant_id": auth.tenant_id, "summary": summary, "reviews": items}


def operation_reply_social_review(
    st: _SocialWorkspaceState, router: APIRouter, review_id: int, payload: ReviewReplyRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:reviews:reply", 180, 60)
    with st.lock:
        review = next(
            (item for item in st.reviews if item.get("tenant_id") == auth.tenant_id and item.get("id") == review_id),
            None,
        )
        if review is None:
            raise _sw_http_error(status_code=404, detail=REVIEW_NOT_FOUND)
        review["status"] = "responded"
        review["reply_text"] = payload.reply_text.strip()
        review["replied_at"] = datetime.now(UTC).isoformat()
        review["updated_at"] = datetime.now(UTC).isoformat()
        updated = review.copy()
    _sw_audit(st, auth.tenant_id, "social_review_replied", review_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "review": updated, "telemetry_event": "social.review.replied"}


def operation_update_social_review_status(
    st: _SocialWorkspaceState, router: APIRouter, review_id: int, payload: ReviewStatusRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:reviews:status", 240, 60)
    with st.lock:
        review = next(
            (item for item in st.reviews if item.get("tenant_id") == auth.tenant_id and item.get("id") == review_id),
            None,
        )
        if review is None:
            raise _sw_http_error(status_code=404, detail=REVIEW_NOT_FOUND)
        review["status"] = payload.status
        review["updated_at"] = datetime.now(UTC).isoformat()
        updated = review.copy()
    _sw_audit(st, auth.tenant_id, "social_review_status_updated", review_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "review": updated,
        "telemetry_event": "social.review.status_updated",
    }


def operation_list_social_care_cases(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:care:list", 240, 60)
    with st.lock:
        items = [item.copy() for item in st.review_cases if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "cases": items}


def operation_create_social_care_case(
    st: _SocialWorkspaceState, router: APIRouter, payload: ReviewCaseCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:care:create", 120, 60)
    with st.lock:
        review = next(
            (
                item
                for item in st.reviews
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == payload.source_review_id
            ),
            None,
        )
        if review is None:
            raise _sw_http_error(status_code=404, detail=REVIEW_NOT_FOUND)
        case = {
            "id": len(st.review_cases) + 1,
            "tenant_id": auth.tenant_id,
            "source_review_id": payload.source_review_id,
            "priority": payload.priority,
            "status": "new",
            "owner": payload.owner.strip(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.review_cases.append(case)
        created = case.copy()
    _sw_audit(st, auth.tenant_id, "social_care_case_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "case": created, "telemetry_event": "social.care.case_created"}


def operation_list_social_influencers(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:influencers:list", 240, 60)
    _sw_seed_influencers(st)
    with st.lock:
        items = [item.copy() for item in st.influencer_profiles]
        shortlist_ids = set(st.influencer_shortlists.get(auth.tenant_id, []))
    for item in items:
        item["shortlisted"] = item.get("id") in shortlist_ids
    return {"status": "ok", "tenant_id": auth.tenant_id, "items": items, "shortlist_count": len(shortlist_ids)}


def operation_search_social_influencers(
    st: _SocialWorkspaceState, router: APIRouter, payload: InfluencerSearchRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:influencers:search", 180, 60)
    _sw_seed_influencers(st)
    needle = payload.query.strip().lower()
    platform = payload.platform.strip().lower()
    with st.lock:
        candidates = [item.copy() for item in st.influencer_profiles]
    items = [
        item
        for item in candidates
        if item.get("followers", 0) >= payload.min_followers
        and (not platform or str(item.get("platform", "")).lower() == platform)
        and (
            not needle
            or needle in str(item.get("name", "")).lower()
            or needle in str(item.get("handle", "")).lower()
            or (needle in str(item.get("category", "")).lower())
        )
    ]
    _sw_audit(st, auth.tenant_id, "social_influencer_search", None)
    return {"status": "ok", "tenant_id": auth.tenant_id, "items": items, "telemetry_event": "social.influencer.search"}


def operation_shortlist_social_influencer(
    st: _SocialWorkspaceState, router: APIRouter, payload: InfluencerShortlistRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:influencers:shortlist", 180, 60)
    _sw_seed_influencers(st)
    with st.lock:
        match = next((item for item in st.influencer_profiles if item.get("id") == payload.influencer_id), None)
        if match is None:
            raise _sw_http_error(status_code=404, detail="Influencer not found.")
        shortlist = st.influencer_shortlists.setdefault(auth.tenant_id, [])
        if payload.influencer_id not in shortlist:
            shortlist.append(payload.influencer_id)
        shortlisted = shortlist.copy()
        influencer = match.copy()
    _sw_audit(st, auth.tenant_id, "social_influencer_shortlisted", None)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "influencer": influencer,
        "shortlist": shortlisted,
        "telemetry_event": "social.influencer.shortlisted",
    }


def operation_bridge_influencer_to_advocacy(
    st: _SocialWorkspaceState,
    router: APIRouter,
    influencer_id: str,
    payload: InfluencerAdvocacyBridgeRequest,
    auth: AuthDep,
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:influencers:advocacy-bridge", 120, 60)
    _sw_seed_influencers(st)
    with st.lock:
        influencer = next((item for item in st.influencer_profiles if item.get("id") == influencer_id), None)
        if influencer is None:
            raise _sw_http_error(status_code=404, detail="Influencer not found.")
        shortlist = st.influencer_shortlists.setdefault(auth.tenant_id, [])
        if influencer_id not in shortlist:
            shortlist.append(influencer_id)
        asset = {
            "id": f"adv-{len(st.advocacy_assets) + 1}",
            "tenant_id": auth.tenant_id,
            "campaign": payload.campaign.strip(),
            "title": payload.title.strip(),
            "message": f"{payload.message_angle.strip()}: {influencer.get('name')} ({influencer.get('handle')}) on {influencer.get('platform')} has a {influencer.get('engagement_rate')}% engagement rate and {int(influencer.get('followers', 0)):,} followers.",
            "network": payload.network.strip().lower(),
            "status": "ready",
            "created_at": datetime.now(UTC).isoformat(),
            "source_influencer": influencer.copy(),
            "source": "social-selling-bridge",
        }
        st.advocacy_assets.append(asset)
        created = asset.copy()
        shortlist_count = len(shortlist)
    _sw_audit(st, auth.tenant_id, "social_influencer_advocacy_bridged", influencer_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "influencer": influencer,
        "asset": created,
        "shortlist_count": shortlist_count,
        "telemetry_event": "social.influencer.advocacy_bridged",
    }


def operation_list_social_advocacy_assets(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:advocacy:list", 240, 60)
    with st.lock:
        items = [item.copy() for item in st.advocacy_assets if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "items": items}


def operation_create_social_advocacy_asset(
    st: _SocialWorkspaceState, router: APIRouter, payload: AdvocacyAssetCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:advocacy:create", 120, 60)
    with st.lock:
        asset = {
            "id": f"adv-{len(st.advocacy_assets) + 1}",
            "tenant_id": auth.tenant_id,
            "campaign": payload.campaign.strip(),
            "title": payload.title.strip(),
            "message": payload.message.strip(),
            "network": payload.network.strip().lower(),
            "status": "ready",
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.advocacy_assets.append(asset)
        created = asset.copy()
    _sw_audit(st, auth.tenant_id, "social_advocacy_asset_created", None)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "asset": created,
        "telemetry_event": "social.advocacy.asset_created",
    }


def operation_publish_social_advocacy_asset(
    st: _SocialWorkspaceState, router: APIRouter, asset_id: str, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:advocacy:publish", 180, 60)
    with st.lock:
        asset = next(
            (
                item
                for item in st.advocacy_assets
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == asset_id
            ),
            None,
        )
        if asset is None:
            raise _sw_http_error(status_code=404, detail="Advocacy asset not found.")
        asset["status"] = "published"
        asset["published_at"] = datetime.now(UTC).isoformat()
        updated = asset.copy()
    _sw_audit(st, auth.tenant_id, "social_advocacy_asset_published", None)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "asset": updated,
        "telemetry_event": "social.advocacy.asset_published",
    }
