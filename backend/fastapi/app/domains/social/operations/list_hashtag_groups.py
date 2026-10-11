"""Social use cases: list hashtag groups."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.schemas import ApprovalCreateRequest
from ....domains.social.schemas import ApprovalRejectRequest
from ....domains.social.schemas import ConditionalRuleEvaluationRequest
from ....domains.social.schemas import LinkShortenRequest
from ..constants import AuthDep
from ..constants import SCHEDULED_POST_NOT_FOUND
from ..extended_schemas import CalendarAutoPostRequest
from ..extended_schemas import CalendarMoveRequest
from ..extended_schemas import FirstCommentRequest
from ..extended_schemas import HashtagGroupCreateRequest
from ..extended_schemas import HashtagGroupUpdateRequest
from ..extended_schemas import QueueReorderRequest
from ..extended_schemas import ThreadPostRequest
from ..services.publishing import _sw_shorten_url
from ..services.workspace import _sw_evaluate_conditions
from ..services.workspace import _sw_http_error
from ..services.workspace_buffer_compute_comment_score import _buffer_seed_hashtag_groups
from datetime import UTC
from datetime import datetime
from fastapi import APIRouter
from typing import Any
from urllib.parse import urlparse


def operation_list_hashtag_groups(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:hashtag:list", 240, 60)
    _buffer_seed_hashtag_groups(st, auth.tenant_id)
    with st.lock:
        items = [g.copy() for g in st.hashtag_groups if g.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "hashtag_groups": items}


def operation_create_hashtag_group(
    st: _SocialWorkspaceState, router: APIRouter, payload: HashtagGroupCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:hashtag:create", 120, 60)
    now = datetime.now(UTC).isoformat()
    with st.lock:
        group = {
            "id": f"hg-{len(st.hashtag_groups) + 1}",
            "tenant_id": auth.tenant_id,
            "name": payload.name.strip(),
            "hashtags": [h.strip().lstrip("#") for h in payload.hashtags if h.strip()],
            "description": payload.description.strip(),
            "created_at": now,
            "updated_at": now,
        }
        st.hashtag_groups.append(group)
        created = group.copy()
    _sw_audit(st, auth.tenant_id, "hashtag_group_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "hashtag_group": created}


def operation_update_hashtag_group(
    st: _SocialWorkspaceState, router: APIRouter, group_id: str, payload: HashtagGroupUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:hashtag:update", 180, 60)
    with st.lock:
        group = next(
            (g for g in st.hashtag_groups if g.get("tenant_id") == auth.tenant_id and g.get("id") == group_id), None
        )
        if group is None:
            raise _sw_http_error(status_code=404, detail="Hashtag group not found.")
        if payload.name is not None:
            group["name"] = payload.name.strip()
        if payload.hashtags is not None:
            group["hashtags"] = [h.strip().lstrip("#") for h in payload.hashtags if h.strip()]
        if payload.description is not None:
            group["description"] = payload.description.strip()
        group["updated_at"] = datetime.now(UTC).isoformat()
        updated = group.copy()
    _sw_audit(st, auth.tenant_id, "hashtag_group_updated", group_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "hashtag_group": updated}


def operation_delete_hashtag_group(
    st: _SocialWorkspaceState, router: APIRouter, group_id: str, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:hashtag:delete", 120, 60)
    with st.lock:
        idx = next(
            (
                i
                for i, g in enumerate(st.hashtag_groups)
                if g.get("tenant_id") == auth.tenant_id and g.get("id") == group_id
            ),
            None,
        )
        if idx is None:
            raise _sw_http_error(status_code=404, detail="Hashtag group not found.")
        st.hashtag_groups.pop(idx)
    _sw_audit(st, auth.tenant_id, "hashtag_group_deleted", group_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted": True, "group_id": group_id}


def operation_set_first_comment(
    st: _SocialWorkspaceState, router: APIRouter, payload: FirstCommentRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:firstcomment:set", 120, 60)
    with st.lock:
        post = next(
            (
                p
                for p in st.scheduled_posts
                if p.get("tenant_id") == auth.tenant_id and str(p.get("id", "")) == payload.post_id
            ),
            None,
        )
        if post is None:
            raise _sw_http_error(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)
        post["first_comment"] = payload.comment.strip()
        post["first_comment_status"] = "scheduled"
        post["updated_at"] = datetime.now(UTC).isoformat()
        updated = post.copy()
    _sw_audit(st, auth.tenant_id, "first_comment_set", payload.post_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "post_id": payload.post_id,
        "first_comment": updated["first_comment"],
    }


def operation_get_first_comment(
    st: _SocialWorkspaceState, router: APIRouter, post_id: str, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:firstcomment:get", 240, 60)
    with st.lock:
        post = next(
            (p for p in st.scheduled_posts if p.get("tenant_id") == auth.tenant_id and str(p.get("id", "")) == post_id),
            None,
        )
    if post is None:
        raise _sw_http_error(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "post_id": post_id,
        "first_comment": post.get("first_comment"),
        "first_comment_status": post.get("first_comment_status"),
    }


def operation_create_thread_post(
    st: _SocialWorkspaceState, router: APIRouter, payload: ThreadPostRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:thread:create", 60, 60)
    if len(payload.threads) > 25:
        raise _sw_http_error(status_code=422, detail="Maximum 25 tweets per thread.")
    with st.lock:
        post = next(
            (
                p
                for p in st.scheduled_posts
                if p.get("tenant_id") == auth.tenant_id and str(p.get("id", "")) == payload.post_id
            ),
            None,
        )
        if post is None:
            raise _sw_http_error(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)
        post["thread_tweets"] = payload.threads
        post["content_type"] = "thread"
        post["thread_count"] = len(payload.threads)
        post["updated_at"] = datetime.now(UTC).isoformat()
    _sw_audit(st, auth.tenant_id, "thread_post_created", payload.post_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "post_id": payload.post_id,
        "thread_count": len(payload.threads),
        "thread_tweets": payload.threads,
    }


def operation_get_thread_post(
    st: _SocialWorkspaceState, router: APIRouter, post_id: str, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:thread:get", 240, 60)
    with st.lock:
        post = next(
            (p for p in st.scheduled_posts if p.get("tenant_id") == auth.tenant_id and str(p.get("id", "")) == post_id),
            None,
        )
    if post is None:
        raise _sw_http_error(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "post_id": post_id,
        "thread_tweets": post.get("thread_tweets", []),
        "thread_count": post.get("thread_count", 0),
    }


def operation_get_publishing_queue(
    st: _SocialWorkspaceState,
    router: APIRouter,
    auth: AuthDep,
    status: str = "scheduled",
    network: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:queue:list", 240, 60)
    with st.lock:
        posts = [
            p.copy()
            for p in st.scheduled_posts
            if p.get("tenant_id") == auth.tenant_id
            and (status == "all" or p.get("status", "").lower() == status)
            and (not network or str(p.get("network", "")).lower() == network.lower())
        ]
    posts.sort(key=lambda p: str(p.get("scheduled_for") or p.get("created_at") or ""))
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(posts[:limit]), "queue": posts[:limit]}


def operation_reorder_queue(
    st: _SocialWorkspaceState, router: APIRouter, payload: QueueReorderRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:queue:reorder", 60, 60)
    with st.lock:
        existing = {str(p.get("id", "")): p for p in st.scheduled_posts if p.get("tenant_id") == auth.tenant_id}
        missing = [pid for pid in payload.post_ids if pid not in existing]
        if missing:
            raise _sw_http_error(status_code=404, detail=f"Posts not found: {missing}")
        base_posts = [existing[pid] for pid in payload.post_ids]
        times = sorted([str(p.get("scheduled_for") or "") for p in base_posts])
        for i, pid in enumerate(payload.post_ids):
            if i < len(times):
                existing[pid]["scheduled_for"] = times[i]
    _sw_audit(st, auth.tenant_id, "queue_reordered", None)
    return {"status": "ok", "tenant_id": auth.tenant_id, "reordered": len(payload.post_ids)}


def operation_list_calendar_events(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep, month: int | None = None, year: int | None = None
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:calendar:list", 240, 60)
    with st.lock:
        posts = [item.copy() for item in st.scheduled_posts if item.get("tenant_id") == auth.tenant_id]

    def _parse_when(value: Any) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        normalized = raw.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None

    items: list[dict[str, Any]] = []
    for post in posts:
        when = _parse_when(post.get("scheduled_for") or post.get("publish_at") or post.get("created_at"))
        if month is not None and year is not None:
            if when is None or when.month != month or when.year != year:
                continue
        network = str(post.get("platform") or post.get("network") or "").strip().lower()
        items.append(
            {
                "id": str(post.get("id", "")),
                "platforms": [network] if network else [],
                "title": str(post.get("headline") or post.get("title") or post.get("text") or "")[:180],
                "scheduled_for": when.isoformat() if when is not None else "",
                "status": str(post.get("status") or "scheduled"),
                "auto_post": bool(post.get("auto_post", True)),
            }
        )
    items.sort(key=lambda item: str(item.get("scheduled_for") or ""))
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "items": items}


def operation_move_calendar_event(
    st: _SocialWorkspaceState, router: APIRouter, item_id: str, payload: CalendarMoveRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:calendar:move", 120, 60)
    raw = payload.new_scheduled_time.strip().replace("Z", "+00:00")
    try:
        moved_to = datetime.fromisoformat(raw)
        if moved_to.tzinfo is None:
            moved_to = moved_to.replace(tzinfo=UTC)
    except ValueError as exc:
        raise _sw_http_error(status_code=422, detail="new_scheduled_time must be a valid ISO-8601 datetime.") from exc
    with st.lock:
        post = next(
            (p for p in st.scheduled_posts if p.get("tenant_id") == auth.tenant_id and str(p.get("id", "")) == item_id),
            None,
        )
        if post is None:
            raise _sw_http_error(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)
        post["publish_at"] = moved_to.isoformat()
        post["scheduled_for"] = moved_to.isoformat()
        post["updated_at"] = datetime.now(UTC).isoformat()
        updated = post.copy()
    _sw_audit(st, auth.tenant_id, "calendar_event_moved", item_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "id": str(updated.get("id", "")),
        "scheduled_for": str(updated.get("scheduled_for") or updated.get("publish_at") or ""),
        "auto_post": bool(updated.get("auto_post", True)),
        "status_value": str(updated.get("status") or "scheduled"),
    }


def operation_set_calendar_event_auto_post(
    st: _SocialWorkspaceState, router: APIRouter, item_id: str, payload: CalendarAutoPostRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:calendar:auto-post", 120, 60)
    with st.lock:
        post = next(
            (p for p in st.scheduled_posts if p.get("tenant_id") == auth.tenant_id and str(p.get("id", "")) == item_id),
            None,
        )
        if post is None:
            raise _sw_http_error(status_code=404, detail=SCHEDULED_POST_NOT_FOUND)
        post["auto_post"] = payload.auto_post
        post["updated_at"] = datetime.now(UTC).isoformat()
        updated = post.copy()
    _sw_audit(st, auth.tenant_id, "calendar_event_auto_post_updated", item_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "id": str(updated.get("id", "")),
        "auto_post": bool(updated.get("auto_post")),
        "scheduled_for": str(updated.get("scheduled_for") or updated.get("publish_at") or ""),
        "status_value": str(updated.get("status") or "scheduled"),
    }


def operation_shorten_social_link(
    st: _SocialWorkspaceState, router: APIRouter, payload: LinkShortenRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:links:shorten", 120, 60)
    parsed = urlparse(payload.url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise _sw_http_error(status_code=422, detail="URL must be a valid HTTP(S) URL.")
    shortened = _sw_shorten_url(payload.url.strip(), payload.provider, payload.domain)
    short_url = str(shortened.get("short_url") or "").strip()
    if not short_url:
        raise _sw_http_error(status_code=502, detail="Shortener provider returned an empty URL.")
    with st.lock:
        item = {
            "id": len(st.short_links) + 1,
            "tenant_id": auth.tenant_id,
            "provider": shortened.get("provider"),
            "source_url": payload.url.strip(),
            "short_url": short_url,
            "domain": payload.domain,
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.short_links.append(item)
        created = item.copy()
    _sw_audit(st, auth.tenant_id, "social_link_shortened", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "link": created}


def operation_list_short_links(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep, limit: int = 100
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:links:list", 240, 60)
    clamped_limit = max(1, min(limit, 500))
    with st.lock:
        items = [item.copy() for item in st.short_links if item.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[:clamped_limit]),
        "links": items[:clamped_limit],
    }


def operation_evaluate_conditional_rules(
    st: _SocialWorkspaceState, router: APIRouter, payload: ConditionalRuleEvaluationRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:automation:conditions:evaluate", 120, 60)
    evaluation = _sw_evaluate_conditions(st, auth.tenant_id, payload.rules)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "passed": evaluation["passed"],
        "results": evaluation["results"],
        "metrics": evaluation["metrics"],
    }


def operation_create_approval_request(
    st: _SocialWorkspaceState, router: APIRouter, payload: ApprovalCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:approvals:create", 120, 60)
    with st.lock:
        post = next(
            (
                item
                for item in st.scheduled_posts
                if item.get("tenant_id") == auth.tenant_id and str(item.get("id")) == payload.post_id
            ),
            None,
        )
        if post is None:
            raise _sw_http_error(status_code=404, detail="Post not found for approval request.")
        approval_levels = [lvl.strip().lower() for lvl in payload.approval_levels if lvl.strip()]
        approvers = [approver.strip().lower() for approver in payload.approvers if approver.strip()]
        request_obj = {
            "id": f"appr-{len(st.approval_requests) + 1}",
            "tenant_id": auth.tenant_id,
            "post_id": payload.post_id,
            "platform": post.get("platform"),
            "content_preview": str(post.get("headline") or post.get("text") or "")[:120],
            "requested_by": "manual",
            "approvers": approvers,
            "approval_levels": approval_levels or approvers,
            "approvals_received": [],
            "auto_publish_on_approve": payload.auto_publish_on_approve,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.approval_requests.append(request_obj)
        post["status"] = "pending_approval"
        post["approval_status"] = "pending"
        post["approval_levels"] = request_obj["approval_levels"]
        post["updated_at"] = datetime.now(UTC).isoformat()
        created = request_obj.copy()
    _sw_audit(st, auth.tenant_id, "social_approval_requested", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "request": created}


def operation_list_pending_approvals(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:approvals:list", 240, 60)
    with st.lock:
        items = [
            item.copy()
            for item in st.approval_requests
            if item.get("tenant_id") == auth.tenant_id and item.get("status") == "pending"
        ]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "requests": items}


def operation_approve_request(
    st: _SocialWorkspaceState, router: APIRouter, request_id: str, auth: AuthDep, approver: str = "approver"
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:approvals:approve", 180, 60)
    approver_value = approver.strip().lower() or "approver"
    with st.lock:
        req = next(
            (
                item
                for item in st.approval_requests
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == request_id
            ),
            None,
        )
        if req is None:
            raise _sw_http_error(status_code=404, detail="Approval request not found.")
        if req.get("status") != "pending":
            return {
                "success": True,
                "tenant_id": auth.tenant_id,
                "postId": str(req.get("post_id")),
                "status": req.get("status"),
            }
        approvals = [str(v).lower() for v in req.get("approvals_received", [])]
        if approver_value not in approvals:
            approvals.append(approver_value)
        req["approvals_received"] = approvals
        required = [str(v).lower() for v in req.get("approval_levels") or req.get("approvers") or []]
        all_approved = all((level in approvals for level in required)) if required else bool(approvals)
        post = next(
            (
                item
                for item in st.scheduled_posts
                if item.get("tenant_id") == auth.tenant_id and str(item.get("id")) == str(req.get("post_id"))
            ),
            None,
        )
        if all_approved:
            req["status"] = "approved"
            req["approved_at"] = datetime.now(UTC).isoformat()
            if post is not None:
                publish_at_raw = str(post.get("publish_at") or "")
                publish_now = False
                try:
                    publish_now = bool(publish_at_raw) and datetime.fromisoformat(publish_at_raw) <= datetime.now(UTC)
                except Exception:
                    publish_now = False
                if req.get("auto_publish_on_approve"):
                    post["status"] = "published" if publish_now else "scheduled"
                else:
                    post["status"] = "approved"
                post["approval_status"] = "approved"
                post["updated_at"] = datetime.now(UTC).isoformat()
        else:
            req["status"] = "pending"
            if post is not None:
                post["status"] = "pending_approval"
                post["approval_status"] = "pending"
                post["updated_at"] = datetime.now(UTC).isoformat()
        post_id = str(req.get("post_id"))
        req_status = str(req.get("status") or "pending")
    _sw_audit(st, auth.tenant_id, "social_approval_approved", request_id)
    return {"success": True, "tenant_id": auth.tenant_id, "postId": post_id, "status": req_status}


def operation_reject_request(
    st: _SocialWorkspaceState, router: APIRouter, request_id: str, payload: ApprovalRejectRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:approvals:reject", 180, 60)
    with st.lock:
        req = next(
            (
                item
                for item in st.approval_requests
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == request_id
            ),
            None,
        )
        if req is None:
            raise _sw_http_error(status_code=404, detail="Approval request not found.")
        req["status"] = "rejected"
        req["rejection_reason"] = payload.reason.strip()
        req["rejected_at"] = datetime.now(UTC).isoformat()
        post = next(
            (
                item
                for item in st.scheduled_posts
                if item.get("tenant_id") == auth.tenant_id and str(item.get("id")) == str(req.get("post_id"))
            ),
            None,
        )
        if post is not None:
            post["status"] = "rejected"
            post["approval_status"] = "rejected"
            post["rejection_reason"] = payload.reason.strip()
            post["updated_at"] = datetime.now(UTC).isoformat()
    _sw_audit(st, auth.tenant_id, "social_approval_rejected", request_id)
    return {"success": True, "tenant_id": auth.tenant_id, "request_id": request_id}


def operation_list_integration_webhooks(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:integrations:webhooks:list", 240, 60)
    with st.lock:
        items = [item.copy() for item in st.integration_webhooks if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "webhooks": items}
