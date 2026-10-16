"""Social use cases: create mobile quick post."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.persistence import _sw_get_account
from ....domains.social.schemas import AutoPostRequest
from ....domains.social.schemas import MobileOfflineSyncRequest
from ....domains.social.schemas import MobileQuickPostRequest
from ..constants import ACCOUNT_NOT_FOUND
from ..constants import AuthDep
from ..constants import SAVED_REPLY_NOT_FOUND
from ..extended_schemas import CommunityCommentReplyRequest
from ..extended_schemas import ContentTemplateCreateRequest
from ..extended_schemas import CustomReportRequest
from ..extended_schemas import PostingScheduleRequest
from ..extended_schemas import SavedCommentReplyCreateRequest
from ..services.publishing import _sw_humanized_publish_slot
from ..services.publishing import _sw_publish_mode_to_status
from ..services.publishing import _sw_resolve_publish_at
from ..services.workspace import _sw_http_error
from ..services.workspace import _sw_seed_reports
from ..services.workspace_buffer_compute_comment_score import _buffer_compute_comment_score
from ..services.workspace_buffer_compute_comment_score import _buffer_get_audience_insights
from ..services.workspace_buffer_compute_comment_score import _buffer_get_best_time_analysis
from ..services.workspace_buffer_compute_comment_score import _buffer_get_channel_analytics
from ..services.workspace_buffer_compute_comment_score import _buffer_seed_posting_schedules
from ..services.workspace_buffer_compute_comment_score import _buffer_seed_templates
from ..services.workspace_connect_account import _buffer_seed_community_comments
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import APIRouter
from typing import Any
from typing import cast


def operation_create_mobile_quick_post(
    st: _SocialWorkspaceState, router: APIRouter, payload: MobileQuickPostRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:mobile:quick-post", 180, 60)
    account = _sw_get_account(st, auth.tenant_id, payload.account_id)
    if account is None:
        raise _sw_http_error(status_code=404, detail=ACCOUNT_NOT_FOUND)
    publish_at = _sw_resolve_publish_at(
        AutoPostRequest(
            account_id=payload.account_id,
            content_type="image",
            headline="Mobile quick post",
            caption=payload.text,
            media_urls=payload.media_urls,
            publish_mode=payload.publish_mode,
            publish_at=payload.publish_at,
        ),
        _sw_humanized_publish_slot(payload.network.strip().lower(), datetime.now(UTC)),
    )
    with st.lock:
        post = {
            "id": len(st.scheduled_posts) + 1,
            "tenant_id": auth.tenant_id,
            "platform": payload.network.strip().lower(),
            "headline": "Mobile quick post",
            "text": payload.text.strip(),
            "media_urls": payload.media_urls,
            "publish_at": publish_at.isoformat(),
            "status": _sw_publish_mode_to_status(payload.publish_mode),
            "created_at": datetime.now(UTC).isoformat(),
            "source": "mobile",
        }
        st.scheduled_posts.append(post)
        st.notifications.append(
            {
                "id": len(st.notifications) + 1,
                "tenant_id": auth.tenant_id,
                "title": "Mobile quick post queued",
                "message": f"Mobile post prepared for {payload.network.strip().lower()}.",
                "category": "social",
                "priority": "info",
                "read": False,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        created = post.copy()
    _sw_audit(st, auth.tenant_id, "social_mobile_quick_post_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "post": created}


def operation_sync_mobile_offline_events(
    st: _SocialWorkspaceState, router: APIRouter, payload: MobileOfflineSyncRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:mobile:sync", 240, 60)
    applied: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    with st.lock:
        device = next(
            (
                item
                for item in st.mobile_devices
                if item.get("tenant_id") == auth.tenant_id and item.get("device_id") == payload.device_id.strip()
            ),
            None,
        )
        if device is None:
            raise _sw_http_error(status_code=404, detail="Mobile device not registered.")
        device["last_seen_at"] = datetime.now(UTC).isoformat()
        for idx, event in enumerate(payload.events):
            event_type = str(event.get("type") or "").strip().lower()
            event_payload = cast(dict[str, Any], event.get("payload") or {})
            if event_type == "idea.create":
                idea = {
                    "id": len(st.content_ideas) + 1,
                    "tenant_id": auth.tenant_id,
                    "title": str(event_payload.get("title") or f"Mobile idea {idx + 1}"),
                    "body": str(event_payload.get("body") or event_payload.get("text") or ""),
                    "source": "mobile_offline",
                    "source_ref": event.get("id"),
                    "tags": cast(list[str], event_payload.get("tags") or ["mobile"]),
                    "status": "new",
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                st.content_ideas.append(idea)
                applied.append({"event_id": event.get("id"), "type": event_type, "idea_id": idea["id"]})
            elif event_type == "capture.create":
                capture = {
                    "id": len(st.extension_captures) + 1,
                    "tenant_id": auth.tenant_id,
                    "source_url": str(event_payload.get("source_url") or ""),
                    "title": str(event_payload.get("title") or f"Mobile capture {idx + 1}"),
                    "selected_text": str(event_payload.get("selected_text") or ""),
                    "note": str(event_payload.get("note") or ""),
                    "suggested_network": str(event_payload.get("suggested_network") or "linkedin").lower(),
                    "screenshot_url": event_payload.get("screenshot_url"),
                    "tags": cast(list[str], event_payload.get("tags") or ["mobile"]),
                    "status": "captured",
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                st.extension_captures.append(capture)
                applied.append({"event_id": event.get("id"), "type": event_type, "capture_id": capture["id"]})
            else:
                rejected.append(
                    {"event_id": event.get("id"), "reason": f"Unsupported event type: {event_type or 'unknown'}"}
                )
        batch = {
            "id": len(st.mobile_sync_batches) + 1,
            "tenant_id": auth.tenant_id,
            "device_id": payload.device_id.strip(),
            "received": len(payload.events),
            "applied": len(applied),
            "rejected": len(rejected),
            "applied_items": applied,
            "rejected_items": rejected,
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.mobile_sync_batches.append(batch)
        created_batch = batch.copy()
    _sw_audit(st, auth.tenant_id, "social_mobile_sync_processed", created_batch["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "batch": created_batch}


def operation_list_mobile_sync_batches(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep, limit: int = 50
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:mobile:sync:batches:list", 240, 60)
    clamped_limit = max(1, min(limit, 500))
    with st.lock:
        items = [item.copy() for item in st.mobile_sync_batches if item.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[:clamped_limit]),
        "batches": items[:clamped_limit],
    }


def operation_get_posting_schedules(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:posting-schedule:list", 240, 60)
    _buffer_seed_posting_schedules(st, auth.tenant_id)
    with st.lock:
        items = [s.copy() for s in st.posting_schedules if s.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "schedules": items}


def operation_update_posting_schedule(
    st: _SocialWorkspaceState, router: APIRouter, network: str, payload: PostingScheduleRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:posting-schedule:update", 120, 60)
    _buffer_seed_posting_schedules(st, auth.tenant_id)
    now = datetime.now(UTC).isoformat()
    with st.lock:
        existing = next(
            (s for s in st.posting_schedules if s.get("tenant_id") == auth.tenant_id and s.get("network") == network),
            None,
        )
        if existing:
            existing["slots"] = payload.slots
            existing["timezone"] = payload.timezone
            existing["updated_at"] = now
            result = existing.copy()
        else:
            schedule = {
                "id": f"sched-{len(st.posting_schedules) + 1}",
                "tenant_id": auth.tenant_id,
                "network": network,
                "slots": payload.slots,
                "timezone": payload.timezone,
                "created_at": now,
                "updated_at": now,
            }
            st.posting_schedules.append(schedule)
            result = schedule.copy()
    _sw_audit(st, auth.tenant_id, "posting_schedule_updated", network)
    return {"status": "ok", "tenant_id": auth.tenant_id, "schedule": result}


def operation_list_content_templates(
    st: _SocialWorkspaceState,
    router: APIRouter,
    auth: AuthDep,
    content_type: str | None = None,
    network: str | None = None,
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:templates:list", 240, 60)
    _buffer_seed_templates(st, auth.tenant_id)
    with st.lock:
        items = [
            t.copy()
            for t in st.content_templates
            if t.get("tenant_id") == auth.tenant_id
            and (not content_type or t.get("content_type") == content_type)
            and (not network or network in (t.get("networks") or []))
        ]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "templates": items}


def operation_create_content_template(
    st: _SocialWorkspaceState, router: APIRouter, payload: ContentTemplateCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:templates:create", 60, 60)
    now = datetime.now(UTC).isoformat()
    with st.lock:
        tmpl = {
            "id": f"tmpl-custom-{len(st.content_templates) + 1}",
            "tenant_id": auth.tenant_id,
            "name": payload.name.strip(),
            "content_type": payload.content_type.strip(),
            "body": payload.body.strip(),
            "networks": [n.strip().lower() for n in payload.networks],
            "tags": [t.strip().lower() for t in payload.tags],
            "created_at": now,
            "updated_at": now,
        }
        st.content_templates.append(tmpl)
        created = tmpl.copy()
    _sw_audit(st, auth.tenant_id, "content_template_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "template": created}


def operation_delete_content_template(
    st: _SocialWorkspaceState, router: APIRouter, template_id: str, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:templates:delete", 120, 60)
    with st.lock:
        idx = next(
            (
                i
                for i, t in enumerate(st.content_templates)
                if t.get("tenant_id") == auth.tenant_id and t.get("id") == template_id
            ),
            None,
        )
        if idx is None:
            raise _sw_http_error(status_code=404, detail="Template not found.")
        st.content_templates.pop(idx)
    _sw_audit(st, auth.tenant_id, "content_template_deleted", template_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted": True, "template_id": template_id}


def operation_list_community_comments(
    st: _SocialWorkspaceState,
    router: APIRouter,
    auth: AuthDep,
    network: str | None = None,
    status: str | None = None,
    sort: str = "newest",
    limit: int = 50,
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:community:list", 240, 60)
    _buffer_seed_community_comments(st, auth.tenant_id)
    with st.lock:
        items = [
            c.copy()
            for c in st.community_comments
            if c.get("tenant_id") == auth.tenant_id
            and (not network or c.get("network") == network)
            and (not status or c.get("status") == status)
        ]
    reverse = sort == "newest"
    items.sort(key=lambda c: str(c.get("created_at", "")), reverse=reverse)
    unanswered = [c for c in items if not c.get("replied")]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[:limit]),
        "unanswered_count": len(unanswered),
        "comments": items[:limit],
    }


def operation_reply_to_community_comment(
    st: _SocialWorkspaceState, router: APIRouter, comment_id: str, payload: CommunityCommentReplyRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:community:reply", 120, 60)
    now = datetime.now(UTC).isoformat()
    with st.lock:
        comment = next(
            (c for c in st.community_comments if c.get("tenant_id") == auth.tenant_id and c.get("id") == comment_id),
            None,
        )
        if comment is None:
            raise _sw_http_error(status_code=404, detail="Comment not found.")
        comment["replied"] = True
        comment["reply"] = payload.reply.strip()
        comment["replied_at"] = now
        comment["status"] = "replied"
        updated = comment.copy()
        st.comment_reply_log.append(
            {"tenant_id": auth.tenant_id, "comment_id": comment_id, "reply": payload.reply.strip(), "replied_at": now}
        )
    _sw_audit(st, auth.tenant_id, "community_comment_replied", comment_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "comment": updated, "platform_published": True}


def operation_create_post_from_comment(
    st: _SocialWorkspaceState, router: APIRouter, comment_id: str, auth: AuthDep
) -> dict[str, Any]:
    """Create a new scheduled post from a comment reply (Buffer 'Create post from reply' feature)."""
    st.enforce_rate_limit(f"{auth.tenant_id}:community:create-post", 60, 60)
    with st.lock:
        comment = next(
            (c for c in st.community_comments if c.get("tenant_id") == auth.tenant_id and c.get("id") == comment_id),
            None,
        )
        if comment is None:
            raise _sw_http_error(status_code=404, detail="Comment not found.")
        reply_text = comment.get("reply") or comment.get("text", "")
        now = datetime.now(UTC)
        post = {
            "id": len(st.scheduled_posts) + 1,
            "tenant_id": auth.tenant_id,
            "title": f"Repurposed from comment on {comment.get('post_title', 'post')}",
            "caption": reply_text,
            "platforms": [comment.get("network", "instagram")],
            "status": "draft",
            "content_type": "post",
            "source": "community_comment",
            "source_comment_id": comment_id,
            "scheduled_for": (now + timedelta(days=1)).isoformat(),
            "created_at": now.isoformat(),
        }
        st.scheduled_posts.append(post)
        created = post.copy()
    _sw_audit(st, auth.tenant_id, "post_created_from_comment", comment_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "post": created}


def operation_get_comment_score(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    """Community comment engagement score (response rate, speed, consistency)."""
    st.enforce_rate_limit(f"{auth.tenant_id}:community:score", 240, 60)
    _buffer_seed_community_comments(st, auth.tenant_id)
    score = _buffer_compute_comment_score(st, auth.tenant_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "comment_score": score}


def operation_list_community_saved_replies(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:community:saved-replies:list", 240, 60)
    with st.lock:
        items = [
            r.copy()
            for r in st.saved_replies
            if r.get("tenant_id") == auth.tenant_id and r.get("reply_type") == "comment"
        ]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "saved_replies": items}


def operation_create_community_saved_reply(
    st: _SocialWorkspaceState, router: APIRouter, payload: SavedCommentReplyCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:community:saved-replies:create", 60, 60)
    now = datetime.now(UTC).isoformat()
    with st.lock:
        reply = {
            "id": f"csr-{len(st.saved_replies) + 1}",
            "tenant_id": auth.tenant_id,
            "reply_type": "comment",
            "label": payload.label.strip(),
            "text": payload.text.strip(),
            "shortcut": payload.shortcut.strip() if payload.shortcut else None,
            "created_at": now,
        }
        st.saved_replies.append(reply)
        created = reply.copy()
    _sw_audit(st, auth.tenant_id, "community_saved_reply_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "saved_reply": created}


def operation_delete_community_saved_reply(
    st: _SocialWorkspaceState, router: APIRouter, reply_id: str, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:community:saved-replies:delete", 120, 60)
    with st.lock:
        idx = next(
            (
                i
                for i, r in enumerate(st.saved_replies)
                if r.get("tenant_id") == auth.tenant_id and r.get("id") == reply_id
            ),
            None,
        )
        if idx is None:
            raise _sw_http_error(status_code=404, detail=SAVED_REPLY_NOT_FOUND)
        st.saved_replies.pop(idx)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted": True, "reply_id": reply_id}


def operation_get_analytics_overview(
    st: _SocialWorkspaceState,
    router: APIRouter,
    auth: AuthDep,
    networks: str = "instagram,facebook,linkedin,x",
    days: int = 30,
) -> dict[str, Any]:
    """Cross-channel analytics overview. Fetches live from platform APIs when credentials set."""
    st.enforce_rate_limit(f"{auth.tenant_id}:analytics:overview", 120, 60)
    network_list = [n.strip() for n in networks.split(",") if n.strip()]
    data = _buffer_get_channel_analytics(network_list, days)
    return {"status": "ok", "tenant_id": auth.tenant_id, "period_days": days, **data}


def operation_get_best_time_to_post(
    st: _SocialWorkspaceState, router: APIRouter, network: str, auth: AuthDep
) -> dict[str, Any]:
    """Best time to post analysis per network, based on audience engagement data."""
    st.enforce_rate_limit(f"{auth.tenant_id}:analytics:best-time", 120, 60)
    data = _buffer_get_best_time_analysis(network.strip().lower())
    return {"status": "ok", "tenant_id": auth.tenant_id, **data}


def operation_get_audience_insights(
    st: _SocialWorkspaceState, router: APIRouter, network: str, auth: AuthDep
) -> dict[str, Any]:
    """Audience demographics. Live: pulled from platform APIs (FB Insights, LinkedIn Follower Stats, etc.)."""
    st.enforce_rate_limit(f"{auth.tenant_id}:analytics:audience", 120, 60)
    data = _buffer_get_audience_insights(network.strip().lower())
    return {"status": "ok", "tenant_id": auth.tenant_id, **data}


def operation_create_custom_report(
    st: _SocialWorkspaceState, router: APIRouter, payload: CustomReportRequest, auth: AuthDep
) -> dict[str, Any]:
    """Generate a custom branded analytics report (PDF/CSV/Excel).
    Production: uses ReportLab (PDF), openpyxl (Excel), or pandas (CSV) for export."""
    st.enforce_rate_limit(f"{auth.tenant_id}:analytics:custom-report", 30, 60)
    now = datetime.now(UTC).isoformat()
    data = _buffer_get_channel_analytics(
        payload.networks or ["instagram", "facebook", "linkedin", "x"], payload.date_range_days
    )
    report = {
        "id": f"cr-{len(st.reports) + 1}",
        "tenant_id": auth.tenant_id,
        "name": payload.name.strip(),
        "report_type": "custom",
        "networks": payload.networks,
        "metrics": payload.metrics,
        "date_range_days": payload.date_range_days,
        "include_logo": payload.include_logo,
        "accent_color": payload.accent_color,
        "export_format": payload.export_format,
        "status": "ready",
        "data": data,
        "download_url": f"/api/v1/social/analytics/reports/{len(st.reports) + 1}/download",
        "created_at": now,
        "generated_at": now,
    }
    with st.lock:
        st.reports.append(report)
        created = report.copy()
    _sw_audit(st, auth.tenant_id, "custom_report_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "report": created}


def operation_list_analytics_reports(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:analytics:reports:list", 240, 60)
    _sw_seed_reports(st, auth.tenant_id)
    with st.lock:
        items = [r.copy() for r in st.reports if r.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "reports": items}
