"""Social use cases: create social automation rule."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.schemas import AutomationRuleCreateRequest
from ....domains.social.schemas import AutomationRuleStatusRequest
from ....domains.social.schemas import CommentToDmRequest
from ....domains.social.schemas import ContactView
from ....domains.social.schemas import DmChatbotReplyRequest
from ....domains.social.schemas import MessageClaimRequest
from ....domains.social.schemas import PauseAllRequest
from ....domains.social.schemas import SavedReplyCreateRequest
from ....domains.social.schemas import SavedReplyUpdateRequest
from ....domains.social.schemas import SocialInboxRespondRequest
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..constants import SAVED_REPLY_NOT_FOUND
from ..services.capabilities import _require_openai_for_strict_social
from ..services.workspace import _sw_http_error
from ..services.workspace import _sw_seed_saved_replies
from ..services.workspace_buffer_compute_comment_score import _sw_generate_dm_chatbot_reply
from ..services.workspace_connect_account import _sw_seed_inbox_for_tenant
from datetime import UTC
from datetime import datetime
from fastapi import APIRouter
from typing import Any
from typing import cast


def operation_create_social_automation_rule(
    st: _SocialWorkspaceState, router: APIRouter, payload: AutomationRuleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:automation:rules:create", 120, 60)
    with st.lock:
        rule = {
            "id": len(st.automation_rules) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name.strip(),
            "trigger_type": payload.trigger_type.strip(),
            "trigger_value": payload.trigger_value.strip(),
            "action_type": payload.action_type.strip(),
            "action_payload": payload.action_payload,
            "enabled": payload.enabled,
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.automation_rules.append(rule)
        created = rule.copy()
    _sw_audit(st, auth.tenant_id, "social_automation_rule_created", created["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "rule": created,
        "telemetry_event": "social.automation.rule_created",
    }


def operation_update_social_automation_rule(
    st: _SocialWorkspaceState, router: APIRouter, rule_id: int, payload: AutomationRuleStatusRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:automation:rules:update", 180, 60)
    with st.lock:
        rule = next(
            (
                item
                for item in st.automation_rules
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == rule_id
            ),
            None,
        )
        if rule is None:
            raise _sw_http_error(status_code=404, detail="Automation rule not found.")
        rule["enabled"] = payload.enabled
        rule["updated_at"] = datetime.now(UTC).isoformat()
        updated = rule.copy()
    _sw_audit(st, auth.tenant_id, "social_automation_rule_updated", rule_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "rule": updated,
        "telemetry_event": "social.automation.rule_updated",
    }


def operation_get_social_automation_queue(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:automation:queue", 240, 60)
    pause_state = st.pause_all_state.get(auth.tenant_id, {"paused": False, "reason": "", "updated_at": None})
    with st.lock:
        queued = [
            item.copy()
            for item in st.scheduled_posts
            if item.get("tenant_id") == auth.tenant_id and item.get("status") == "scheduled"
        ]
        drafts = [
            item.copy()
            for item in st.scheduled_posts
            if item.get("tenant_id") == auth.tenant_id and item.get("status") == "draft"
        ]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "pause_all": pause_state,
        "summary": {"scheduled": len(queued), "drafts": len(drafts)},
        "items": queued[:50],
    }


def operation_set_social_pause_all(
    st: _SocialWorkspaceState, router: APIRouter, payload: PauseAllRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:automation:pause-all", 60, 60)
    state = {"paused": payload.paused, "reason": payload.reason.strip(), "updated_at": datetime.now(UTC).isoformat()}
    st.pause_all_state[auth.tenant_id] = state
    _sw_audit(st, auth.tenant_id, "social_pause_all_updated", None)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "pause_all": state,
        "telemetry_event": "social.automation.pause_all_updated",
    }


def operation_list_social_inbox(
    st: _SocialWorkspaceState, router: APIRouter, unread_only: bool = False, *, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:list", 240, 60)
    _sw_seed_inbox_for_tenant(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.inbox_messages if item.get("tenant_id") == auth.tenant_id]
    if unread_only:
        items = [item for item in items if item.get("status") not in {"responded", "complete"}]
    normalized = [
        {
            "id": str(item.get("id")),
            "network": item.get("network") or "linkedin",
            "source": f"@{item.get('author_handle')}",
            "type": item.get("source_type") or "comment",
            "content": item.get("text") or item.get("message") or "",
            "sentiment": item.get("sentiment") or "neutral",
            "engagement": item.get("author_follower_count") or 0,
            "createdAt": item.get("created_at"),
            "responded": item.get("status") in {"responded", "complete"},
            "assignedTo": item.get("assigned_to"),
            "state": item.get("collision_state") or item.get("status") or "open",
        }
        for item in items
    ]
    return {"status": "ok", "tenant_id": auth.tenant_id, "items": normalized}


def operation_get_social_inbox_stats(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:stats", 240, 60)
    _sw_seed_inbox_for_tenant(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.inbox_messages if item.get("tenant_id") == auth.tenant_id]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "total": len(items),
        "unread": sum((1 for item in items if item.get("status") not in {"responded", "complete"})),
        "pending_responses": sum((1 for item in items if item.get("status") == "open")),
    }


def operation_mark_social_inbox_read(
    st: _SocialWorkspaceState, router: APIRouter, message_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:read", 180, 60)
    _sw_seed_inbox_for_tenant(st, auth.tenant_id)
    with st.lock:
        message = next(
            (
                item
                for item in st.inbox_messages
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == message_id
            ),
            None,
        )
        if message is None:
            raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
        message["read_at"] = datetime.now(UTC).isoformat()
        updated = message.copy()
    return {"status": "ok", "tenant_id": auth.tenant_id, "message": updated}


def operation_respond_social_inbox(
    st: _SocialWorkspaceState, router: APIRouter, message_id: int, payload: SocialInboxRespondRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:respond", 180, 60)
    _sw_seed_inbox_for_tenant(st, auth.tenant_id)
    with st.lock:
        message = next(
            (
                item
                for item in st.inbox_messages
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == message_id
            ),
            None,
        )
        if message is None:
            raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
        message["reply_text"] = payload.response_text.strip()
        message["status"] = "responded"
        message["updated_at"] = datetime.now(UTC).isoformat()
        updated = message.copy()
    _sw_audit(st, auth.tenant_id, "social_inbox_replied", message_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "message": updated}


def operation_respond_with_dm_chatbot(
    st: _SocialWorkspaceState, router: APIRouter, payload: DmChatbotReplyRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:dm-chatbot:respond", 180, 60)
    _require_openai_for_strict_social("dm chatbot responses")
    _sw_seed_inbox_for_tenant(st, auth.tenant_id)
    with st.lock:
        message = next(
            (
                item
                for item in st.inbox_messages
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == payload.message_id
            ),
            None,
        )
        if message is None:
            raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
        author_handle = str(message.get("author_handle") or "")
        history = [
            item
            for item in st.inbox_messages
            if item.get("tenant_id") == auth.tenant_id and item.get("author_handle") == author_handle
        ]
        saved_replies = [
            str(item.get("body") or "").strip()
            for item in st.saved_replies
            if item.get("tenant_id") == auth.tenant_id and str(item.get("body") or "").strip()
        ]
        chatbot_result = _sw_generate_dm_chatbot_reply(
            message_text=str(message.get("text") or ""),
            intent=payload.intent,
            response_tone=payload.response_tone,
            buyer_stage=str(payload.context.get("buyer_stage") or "consideration"),
            saved_replies=saved_replies,
            history_count=len(history),
        )
        reply = chatbot_result["reply"]
        message["reply_text"] = reply
        message["status"] = "responded"
        message["assigned_to"] = "dm-chatbot"
        message["chatbot_provider"] = chatbot_result["provider"]
        message["chatbot_confidence"] = chatbot_result["confidence"]
        message["chatbot_escalation_recommended"] = chatbot_result["escalation_recommended"]
        message["chatbot_escalation_reason"] = chatbot_result["escalation_reason"]
        message["chatbot_safety"] = chatbot_result.get("safety")
        message["updated_at"] = datetime.now(UTC).isoformat()
        updated = message.copy()
    _sw_audit(st, auth.tenant_id, "social_dm_chatbot_replied", payload.message_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "message": updated,
        "provider": chatbot_result["provider"],
        "confidence": chatbot_result["confidence"],
        "escalation_recommended": chatbot_result["escalation_recommended"],
        "escalation_reason": chatbot_result["escalation_reason"],
        "safety": chatbot_result.get("safety"),
        "telemetry_event": "social.inbox.dm_chatbot_responded",
    }


def operation_run_comment_to_dm(
    st: _SocialWorkspaceState, router: APIRouter, payload: CommentToDmRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:comment-to-dm", 120, 60)
    _sw_seed_inbox_for_tenant(st, auth.tenant_id)
    with st.lock:
        source = next(
            (
                item
                for item in st.inbox_messages
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == payload.message_id
            ),
            None,
        )
        if source is None:
            raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
        source_text = str(source.get("text") or "").lower()
        keyword = payload.keyword.strip().lower()
        if keyword not in source_text:
            raise _sw_http_error(status_code=409, detail="Keyword did not match source comment.")
        dm_text = payload.dm_text.strip() if payload.dm_text else ""
        offer_link = (payload.offer_link or "https://nuxtron.local/offers/social-growth").strip()
        if not dm_text:
            dm_text = f"Thanks for commenting. Here is your private offer link: {offer_link}"
        outbound_dm = {
            "id": len(st.inbox_messages) + 1,
            "tenant_id": auth.tenant_id,
            "network": source.get("network") or "instagram",
            "source_type": "dm",
            "external_message_id": f"comment-dm-{len(st.inbox_messages) + 1}",
            "parent_message_id": source.get("id"),
            "author_handle": "brand_bot",
            "author_display_name": "Brand Bot",
            "author_follower_count": 0,
            "crm_contact_id": None,
            "text": dm_text,
            "message_type": "promo",
            "sentiment": "positive",
            "classification_confidence": 0.97,
            "priority_score": 65,
            "suggested_replies": [],
            "status": "responded",
            "assigned_to": "comment-to-dm",
            "due_at": None,
            "tags": ["comment-to-dm", keyword],
            "replied": True,
            "replied_at": datetime.now(UTC).isoformat(),
            "read": True,
            "read_at": datetime.now(UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        st.inbox_messages.append(outbound_dm)
        source["status"] = "responded"
        source["updated_at"] = datetime.now(UTC).isoformat()
        source_snapshot = source.copy()
    _sw_audit(st, auth.tenant_id, "social_comment_to_dm_sent", payload.message_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "source_message": source_snapshot,
        "outbound_dm": outbound_dm,
        "telemetry_event": "social.inbox.comment_to_dm_sent",
    }


def operation_list_social_saved_replies(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:saved-replies:list", 240, 60)
    _sw_seed_saved_replies(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.saved_replies if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "items": items}


def operation_create_social_saved_reply(
    st: _SocialWorkspaceState, router: APIRouter, payload: SavedReplyCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:saved-replies:create", 120, 60)
    with st.lock:
        item = {
            "id": len(st.saved_replies) + 1,
            "tenant_id": auth.tenant_id,
            "title": payload.title.strip(),
            "body": payload.body.strip(),
            "category": payload.category.strip(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.saved_replies.append(item)
        created = item.copy()
    _sw_audit(st, auth.tenant_id, "social_saved_reply_created", created["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "item": created,
        "telemetry_event": "social.inbox.saved_reply_created",
    }


def operation_update_social_saved_reply(
    st: _SocialWorkspaceState, router: APIRouter, reply_id: int, payload: SavedReplyUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:saved-replies:update", 120, 60)
    with st.lock:
        item = next(
            (
                entry
                for entry in st.saved_replies
                if entry.get("tenant_id") == auth.tenant_id and entry.get("id") == reply_id
            ),
            None,
        )
        if item is None:
            raise _sw_http_error(status_code=404, detail=SAVED_REPLY_NOT_FOUND)
        item["title"] = payload.title.strip()
        item["body"] = payload.body.strip()
        item["category"] = payload.category.strip()
        item["updated_at"] = datetime.now(UTC).isoformat()
        updated = item.copy()
    _sw_audit(st, auth.tenant_id, "social_saved_reply_updated", updated["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "item": updated,
        "telemetry_event": "social.inbox.saved_reply_updated",
    }


def operation_delete_social_saved_reply(
    st: _SocialWorkspaceState, router: APIRouter, reply_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:saved-replies:delete", 120, 60)
    with st.lock:
        idx = next(
            (
                i
                for i, entry in enumerate(st.saved_replies)
                if entry.get("tenant_id") == auth.tenant_id and entry.get("id") == reply_id
            ),
            None,
        )
        if idx is None:
            raise _sw_http_error(status_code=404, detail=SAVED_REPLY_NOT_FOUND)
        st.saved_replies.pop(idx)
    _sw_audit(st, auth.tenant_id, "social_saved_reply_deleted", reply_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "deleted": True,
        "reply_id": reply_id,
        "telemetry_event": "social.inbox.saved_reply_deleted",
    }


def operation_list_social_contact_views(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:contacts", 240, 60)
    with st.lock:
        inbox = [item.copy() for item in st.inbox_messages if item.get("tenant_id") == auth.tenant_id]
    contacts: dict[str, ContactView] = {}
    for item in inbox:
        key = str(item.get("author_handle") or "unknown")
        contact = contacts.setdefault(
            key,
            {
                "handle": key,
                "display_name": item.get("author_display_name") or key,
                "message_count": 0,
                "last_message_at": item.get("created_at"),
                "sentiment": item.get("sentiment", "neutral"),
                "networks": set(),
            },
        )
        contact["message_count"] += 1
        contact["last_message_at"] = max(str(contact["last_message_at"]), str(item.get("created_at")))
        cast(set[str], contact["networks"]).add(str(item.get("network") or ""))
    items = [{**item, "networks": sorted(cast(set[str], item["networks"]))} for item in contacts.values()]
    items.sort(key=lambda x: str(x.get("last_message_at")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "items": items}


def operation_get_social_message_history(
    st: _SocialWorkspaceState, router: APIRouter, message_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:history", 240, 60)
    with st.lock:
        message = next(
            (
                item
                for item in st.inbox_messages
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == message_id
            ),
            None,
        )
        if message is None:
            raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
        author = message.get("author_handle")
        history = [
            item.copy()
            for item in st.inbox_messages
            if item.get("tenant_id") == auth.tenant_id and item.get("author_handle") == author
        ]
    history.sort(key=lambda item: str(item.get("created_at")))
    return {"status": "ok", "tenant_id": auth.tenant_id, "message": message, "history": history}


def operation_claim_social_message(
    st: _SocialWorkspaceState, router: APIRouter, message_id: int, payload: MessageClaimRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:claim", 180, 60)
    with st.lock:
        message = next(
            (
                item
                for item in st.inbox_messages
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == message_id
            ),
            None,
        )
        if message is None:
            raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
        message["assigned_to"] = payload.agent_name.strip()
        message["collision_state"] = "claimed"
        message["updated_at"] = datetime.now(UTC).isoformat()
        updated = message.copy()
    _sw_audit(st, auth.tenant_id, "social_inbox_message_claimed", message_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "message": updated,
        "telemetry_event": "social.inbox.message_claimed",
    }


def operation_complete_social_message(
    st: _SocialWorkspaceState, router: APIRouter, message_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:complete", 180, 60)
    with st.lock:
        message = next(
            (
                item
                for item in st.inbox_messages
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == message_id
            ),
            None,
        )
        if message is None:
            raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
        message["status"] = "complete"
        message["completed_at"] = datetime.now(UTC).isoformat()
        message["updated_at"] = datetime.now(UTC).isoformat()
        updated = message.copy()
    _sw_audit(st, auth.tenant_id, "social_inbox_message_completed", message_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "message": updated,
        "telemetry_event": "social.inbox.message_completed",
    }
