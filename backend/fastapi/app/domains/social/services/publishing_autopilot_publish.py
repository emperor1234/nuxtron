"""Social Workspace publishing autopilot publish service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.persistence import _sw_get_account
from ....domains.social.schemas import AutoPostRequest
from ..constants import ACCOUNT_NOT_FOUND
from .publishing import _sw_autopilot_apply_short_links
from .publishing import _sw_autopilot_approval_state
from .publishing import _sw_autopilot_post_status
from .publishing import _sw_autopilot_preview
from .publishing import _sw_autopilot_publish_datetime
from .publishing import _sw_build_autopilot_approval_request
from .publishing import _sw_build_recurring_autopilot_posts
from .publishing import _sw_store_short_links
from .workspace import _sw_evaluate_conditions
from .workspace import _sw_http_error
from datetime import UTC
from datetime import datetime
from typing import Any


def _sw_autopilot_publish(st: _SocialWorkspaceState, payload: AutoPostRequest, tenant_id: str) -> dict[str, Any]:
    account = _sw_get_account(st, tenant_id, payload.account_id)
    if account is None:
        raise _sw_http_error(status_code=404, detail=ACCOUNT_NOT_FOUND)
    preview = _sw_autopilot_preview(st, payload, tenant_id)["preview"]
    condition_eval = _sw_evaluate_conditions(st, tenant_id, payload.conditional_rules)
    if not condition_eval["passed"]:
        return {
            "status": "skipped",
            "tenant_id": tenant_id,
            "reason": "Conditional rules were not satisfied.",
            "conditions": condition_eval,
            "telemetry_event": "social.autopilot.skipped_by_conditions",
        }
    publish_at_dt = _sw_autopilot_publish_datetime(payload, preview)
    caption, short_links = _sw_autopilot_apply_short_links(str(preview["caption"]), payload)
    needs_approval, approval_levels = _sw_autopilot_approval_state(payload)
    post_status = _sw_autopilot_post_status(payload.publish_mode, needs_approval)
    record = {
        "id": len(st.scheduled_posts) + 1,
        "tenant_id": tenant_id,
        "platform": account.get("network"),
        "text": caption,
        "publish_at": publish_at_dt.isoformat(),
        "media_urls": payload.media_urls,
        "status": post_status,
        "created_at": datetime.now(UTC).isoformat(),
        "autopilot": True,
        "headline": preview["headline"],
        "description": preview["description"],
        "hashtags": preview["hashtags"],
        "keywords": preview["keywords"],
        "aspect_ratio": preview["aspect_ratio"],
        "conditional_rules": payload.conditional_rules,
        "conditional_eval": condition_eval,
        "recurrence": payload.recurrence,
        "recurrence_count": payload.recurrence_count,
        "recurrence_until": payload.recurrence_until.isoformat() if payload.recurrence_until is not None else None,
        "approval_status": "pending" if needs_approval else "not_required",
        "approval_levels": approval_levels,
        "short_links": short_links,
    }
    recurring_posts = _sw_build_recurring_autopilot_posts(
        st, payload, tenant_id, account, preview, caption, publish_at_dt, needs_approval, approval_levels, short_links
    )
    approval_request: dict[str, Any] | None = None
    with st.lock:
        st.scheduled_posts.append(record)
        if recurring_posts:
            st.scheduled_posts.extend(recurring_posts)
        if short_links:
            _sw_store_short_links(st, tenant_id, int(record["id"]), short_links)
        if needs_approval:
            approval_request = _sw_build_autopilot_approval_request(
                st, tenant_id, record, account, preview, approval_levels, payload.auto_publish_on_approval
            )
            st.approval_requests.append(approval_request)
        st.notifications.append(
            {
                "id": len(st.notifications) + 1,
                "tenant_id": tenant_id,
                "title": "Autopost queued",
                "message": f"{payload.headline} prepared for {account.get('network_label')} with {preview['aspect_ratio']} formatting.",
                "category": "social",
                "priority": "info",
                "read": False,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
    _sw_audit(st, tenant_id, "social_autopilot_publish", record["id"])
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "post": record,
        "recurring_posts": recurring_posts,
        "preview": preview,
        "approval_request": approval_request,
        "short_links": short_links,
        "conditions": condition_eval,
    }
