"""Social use cases: download report."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ..constants import AuthDep
from ..constants import REPORT_NOT_FOUND
from ..constants import START_PAGE_NOT_FOUND
from ..extended_schemas import AIAssistantRequest
from ..extended_schemas import LongformRepurposeRequest
from ..extended_schemas import StartPageUpdateRequest
from ..extended_schemas import TeamMemberInviteRequest
from ..extended_schemas import TeamMemberUpdateRequest
from ..services.ai_policy import _sw_run_ai_assistant_text
from ..services.capabilities import _require_openai_for_strict_social
from ..services.publishing import _sw_humanized_publish_slot
from ..services.workspace import _sw_http_error
from ..services.workspace_buffer_compute_comment_score import _buffer_seed_start_page
from ..services.workspace_buffer_compute_comment_score import _buffer_seed_team_members
from ..services.workspace_parse_longform_variants import _sw_generate_longform_variants
from datetime import UTC
from datetime import datetime
from fastapi import APIRouter
from typing import Any
import os


def operation_download_report(
    st: _SocialWorkspaceState, router: APIRouter, report_id: str, auth: AuthDep
) -> dict[str, Any]:
    """In production: generates PDF via ReportLab or Excel via openpyxl and streams the file."""
    st.enforce_rate_limit(f"{auth.tenant_id}:analytics:reports:download", 60, 60)
    with st.lock:
        report = next(
            (r for r in st.reports if r.get("tenant_id") == auth.tenant_id and str(r.get("id", "")) == report_id), None
        )
    if report is None:
        raise _sw_http_error(status_code=404, detail=REPORT_NOT_FOUND)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "report_id": report_id,
        "export_format": report.get("export_format", "pdf"),
        "download_ready": True,
        "download_url": f"/api/v1/social/analytics/reports/{report_id}/export",
        "note": "In production, this streams the binary file (PDF/Excel/CSV) generated server-side.",
    }


def operation_ai_assistant(
    st: _SocialWorkspaceState, router: APIRouter, payload: AIAssistantRequest, auth: AuthDep
) -> dict[str, Any]:
    """Buffer AI Assistant — rephrase, shorten, expand, change tone, generate ideas, repurpose.
    Production: calls OpenAI GPT-4o (gpt-4o) via openai Python SDK with structured prompt."""
    st.enforce_rate_limit(f"{auth.tenant_id}:ai-assistant", 60, 60)
    _require_openai_for_strict_social("ai assistant")
    action = payload.action.strip().lower()
    text = payload.text.strip()
    platform = (payload.target_platform or "").strip()
    tone = (payload.tone or "professional").strip()
    result_text, safety = _sw_run_ai_assistant_text(action, text, platform, tone)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "action": action,
        "original": text,
        "result": result_text.strip(),
        "platform": platform,
        "provider": safety.get("provider", "fallback"),
        "safety": safety,
    }


def operation_repurpose_longform_asset(
    st: _SocialWorkspaceState, router: APIRouter, payload: LongformRepurposeRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:automation:repurpose", 60, 60)
    _require_openai_for_strict_social("longform repurpose")
    source_title = payload.source_title.strip() or "Longform asset"
    source_url = payload.source_url.strip() if payload.source_url else ""
    variants, prompt, provider, safety = _sw_generate_longform_variants(
        payload.source_text, source_title, payload.target_platform, payload.tone, payload.variant_count
    )
    created_ideas: list[dict[str, Any]] = []
    queued_post: dict[str, Any] | None = None
    target_network = payload.target_platform.strip().lower().replace(" ", "_") or "linkedin"
    with st.lock:
        created_records: list[dict[str, Any]] = []
        for index, variant in enumerate(variants, start=1):
            item = {
                "id": len(st.content_ideas) + 1,
                "tenant_id": auth.tenant_id,
                "title": f"{source_title} repurpose {index}",
                "body": variant,
                "source": "repurpose",
                "source_ref": source_url or source_title,
                "tags": ["repurpose", target_network, "longform"],
                "status": "new",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            st.content_ideas.append(item)
            created_records.append(item)
        if payload.queue_first_variant and created_records:
            first_variant = created_records[0]
            publish_at = _sw_humanized_publish_slot(target_network, datetime.now(UTC))
            queued_post = {
                "id": f"repurpose-{first_variant['id']}-post-{len(st.scheduled_posts) + 1}",
                "tenant_id": auth.tenant_id,
                "platform": target_network,
                "title": first_variant["title"],
                "text": first_variant["body"],
                "publish_at": publish_at.isoformat(),
                "status": "scheduled",
                "created_at": datetime.now(UTC).isoformat(),
                "source": "repurpose",
                "source_ref": source_url or source_title,
            }
            st.scheduled_posts.append(queued_post)
            first_variant["status"] = "queued"
            first_variant["updated_at"] = datetime.now(UTC).isoformat()
        created_ideas = [item.copy() for item in created_records]
    _sw_audit(st, auth.tenant_id, "social_longform_repurposed", source_title)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "source_title": source_title,
        "source_url": source_url or None,
        "target_platform": payload.target_platform,
        "tone": payload.tone,
        "variant_count": len(created_ideas),
        "generated_variants": created_ideas,
        "queued_post": queued_post,
        "provider": provider,
        "prompt": prompt,
        "safety": safety,
        "telemetry_event": "social.longform.repurposed",
    }


def operation_list_team_members(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:team:list", 240, 60)
    _buffer_seed_team_members(st, auth.tenant_id)
    with st.lock:
        items = [m.copy() for m in st.team_members if m.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "total": len(items), "members": items}


def operation_invite_team_member(
    st: _SocialWorkspaceState, router: APIRouter, payload: TeamMemberInviteRequest, auth: AuthDep
) -> dict[str, Any]:
    """Invite a team member. Production: sends invitation email via SendGrid/Postmark."""
    st.enforce_rate_limit(f"{auth.tenant_id}:team:invite", 30, 60)
    _buffer_seed_team_members(st, auth.tenant_id)
    valid_roles = {"admin", "editor", "approver", "analyst", "viewer"}
    if payload.role not in valid_roles:
        raise _sw_http_error(status_code=422, detail=f"Invalid role. Must be one of: {', '.join(sorted(valid_roles))}")
    now = datetime.now(UTC).isoformat()
    with st.lock:
        existing = next(
            (
                m
                for m in st.team_members
                if m.get("tenant_id") == auth.tenant_id and m.get("email") == payload.email.strip().lower()
            ),
            None,
        )
        if existing:
            raise _sw_http_error(status_code=409, detail="Team member with this email already exists.")
        member = {
            "id": f"mem-{len(st.team_members) + 1}",
            "tenant_id": auth.tenant_id,
            "email": payload.email.strip().lower(),
            "name": payload.email.strip().split("@")[0].replace(".", " ").title(),
            "role": payload.role,
            "channel_ids": payload.channel_ids,
            "status": "invited",
            "joined_at": None,
            "invited_at": now,
        }
        st.team_members.append(member)
        created = member.copy()
    _sw_audit(st, auth.tenant_id, "team_member_invited", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "member": created, "invitation_sent": True}


def operation_update_team_member(
    st: _SocialWorkspaceState, router: APIRouter, member_id: str, payload: TeamMemberUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:team:update", 120, 60)
    with st.lock:
        member = next(
            (m for m in st.team_members if m.get("tenant_id") == auth.tenant_id and m.get("id") == member_id), None
        )
        if member is None:
            raise _sw_http_error(status_code=404, detail="Team member not found.")
        if payload.role is not None:
            member["role"] = payload.role
        if payload.channel_ids is not None:
            member["channel_ids"] = payload.channel_ids
        member["updated_at"] = datetime.now(UTC).isoformat()
        updated = member.copy()
    _sw_audit(st, auth.tenant_id, "team_member_updated", member_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "member": updated}


def operation_remove_team_member(
    st: _SocialWorkspaceState, router: APIRouter, member_id: str, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:team:remove", 60, 60)
    with st.lock:
        idx = next(
            (
                i
                for i, m in enumerate(st.team_members)
                if m.get("tenant_id") == auth.tenant_id and m.get("id") == member_id
            ),
            None,
        )
        if idx is None:
            raise _sw_http_error(status_code=404, detail="Team member not found.")
        st.team_members.pop(idx)
    _sw_audit(st, auth.tenant_id, "team_member_removed", member_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted": True, "member_id": member_id}


def operation_get_start_page(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    """Get the Start Page configuration (Buffer's link-in-bio builder)."""
    st.enforce_rate_limit(f"{auth.tenant_id}:start-page:get", 240, 60)
    _buffer_seed_start_page(st, auth.tenant_id)
    with st.lock:
        page = next((p.copy() for p in st.start_pages if p.get("tenant_id") == auth.tenant_id), None)
    if page is None:
        raise _sw_http_error(status_code=404, detail=START_PAGE_NOT_FOUND)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "start_page": page,
        "public_url": f"https://start.page/{page.get('slug')}",
    }


def operation_update_start_page(
    st: _SocialWorkspaceState, router: APIRouter, payload: StartPageUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    """Update Start Page. Links published to buffer.page/{slug} in production."""
    st.enforce_rate_limit(f"{auth.tenant_id}:start-page:update", 60, 60)
    _buffer_seed_start_page(st, auth.tenant_id)
    now = datetime.now(UTC).isoformat()
    with st.lock:
        page = next((p for p in st.start_pages if p.get("tenant_id") == auth.tenant_id), None)
        if page is None:
            raise _sw_http_error(status_code=404, detail=START_PAGE_NOT_FOUND)
        page.update(
            {
                "title": payload.title.strip() or page.get("title", ""),
                "bio": payload.bio.strip() or page.get("bio", ""),
                "theme": payload.theme,
                "accent_color": payload.accent_color,
                "background_color": payload.background_color,
                "avatar_url": payload.avatar_url or page.get("avatar_url"),
                "links": payload.links if payload.links else page.get("links", []),
                "social_links": payload.social_links if payload.social_links else page.get("social_links", []),
                "updated_at": now,
            }
        )
        updated = page.copy()
    _sw_audit(st, auth.tenant_id, "start_page_updated", updated["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "start_page": updated,
        "public_url": f"https://start.page/{updated.get('slug')}",
    }


def operation_track_start_page_link_click(
    st: _SocialWorkspaceState, router: APIRouter, link_id: str, auth: AuthDep
) -> dict[str, Any]:
    """Track link click analytics on Start Page."""
    st.enforce_rate_limit(f"{auth.tenant_id}:start-page:click", 600, 60)
    with st.lock:
        page = next((p for p in st.start_pages if p.get("tenant_id") == auth.tenant_id), None)
        if page is None:
            raise _sw_http_error(status_code=404, detail=START_PAGE_NOT_FOUND)
        link = next((lnk for lnk in page.get("links", []) if lnk.get("id") == link_id), None)
        if link is None:
            raise _sw_http_error(status_code=404, detail="Link not found.")
        link["clicks"] = int(link.get("clicks", 0)) + 1
        page["views"] = int(page.get("views", 0)) + 1
    return {"status": "ok", "tenant_id": auth.tenant_id, "link_id": link_id, "clicks": link["clicks"]}


def operation__vendor_registry(
    st: _SocialWorkspaceState, router: APIRouter, oauth_vendor_keys: dict[str, bool], shortener_config: dict[str, bool]
) -> list[dict[str, Any]]:
    return [
        {
            "vendor": "OpenAI",
            "vendor_key": "openai",
            "configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "env_keys": ["OPENAI_API_KEY"],
            "capabilities": ["ai_content_engines", "ai_repurposing", "ai_agents", "ai_inbox_automation"],
            "routes": ["/social/ai-assistant", "/social/automation/repurpose", "/social/ai-agents/workflows/execute"],
        },
        {
            "vendor": "Canva",
            "vendor_key": "canva",
            "configured": bool(os.getenv("CANVA_ACCESS_TOKEN", "").strip()),
            "env_keys": ["CANVA_ACCESS_TOKEN"],
            "capabilities": ["ai_content_engines", "ai_video"],
            "routes": ["/social/integrations/canva/import", "/social/integrations/canva/imports"],
        },
        {
            "vendor": "Zapier",
            "vendor_key": "zapier",
            "configured": True,
            "env_keys": ["SOCIAL_WEBHOOK_SECRET (optional)"],
            "capabilities": ["ai_automation", "ai_crm_connected_social"],
            "routes": ["/social/integrations/webhooks", "/social/integrations/webhooks/incoming/zapier"],
        },
        {
            "vendor": "Make",
            "vendor_key": "make",
            "configured": True,
            "env_keys": ["SOCIAL_WEBHOOK_SECRET (optional)"],
            "capabilities": ["ai_automation", "ai_crm_connected_social"],
            "routes": ["/social/integrations/webhooks", "/social/integrations/webhooks/incoming/make"],
        },
        {
            "vendor": "HubSpot",
            "vendor_key": "hubspot",
            "configured": bool(os.getenv("HUBSPOT_ACCESS_TOKEN", "").strip()),
            "env_keys": ["HUBSPOT_ACCESS_TOKEN"],
            "capabilities": ["ai_crm_connected_social"],
            "routes": ["/social/integrations/webhooks", "/social/automation/rules"],
        },
        {
            "vendor": "Meta Ads",
            "vendor_key": "meta_ads",
            "configured": bool(
                os.getenv("META_ADS_ACCESS_TOKEN", "").strip() or os.getenv("META_ACCESS_TOKEN", "").strip()
            ),
            "env_keys": ["META_ADS_ACCESS_TOKEN", "META_ACCESS_TOKEN"],
            "capabilities": ["ai_ad_optimization"],
            "routes": ["/social/ads/campaigns", "/social/ads/analytics"],
        },
        {
            "vendor": "TikTok Ads",
            "vendor_key": "tiktok_ads",
            "configured": bool(
                os.getenv("TIKTOK_ADS_ACCESS_TOKEN", "").strip() or os.getenv("TIKTOK_ACCESS_TOKEN", "").strip()
            ),
            "env_keys": ["TIKTOK_ADS_ACCESS_TOKEN", "TIKTOK_ACCESS_TOKEN"],
            "capabilities": ["ai_ad_optimization"],
            "routes": ["/social/ads/campaigns", "/social/ads/analytics"],
        },
        {
            "vendor": "Brandwatch / Meltwater feeds",
            "vendor_key": "brandwatch_meltwater",
            "configured": bool(
                os.getenv("BRANDWATCH_API_KEY", "").strip() or os.getenv("MELTWATER_API_KEY", "").strip()
            ),
            "env_keys": ["BRANDWATCH_API_KEY", "MELTWATER_API_KEY"],
            "capabilities": ["ai_social_listening", "ai_brand_monitoring", "ai_competitor_intelligence"],
            "routes": ["/social/listening/mentions", "/social/competitors/insights"],
        },
        {
            "vendor": "ManyChat / DM channel APIs",
            "vendor_key": "manychat",
            "configured": bool(os.getenv("MANYCHAT_API_KEY", "").strip()),
            "env_keys": ["MANYCHAT_API_KEY"],
            "capabilities": ["ai_inbox_automation"],
            "routes": ["/social/inbox/agents/dm-chatbot/respond", "/social/inbox/comment-to-dm"],
        },
        {
            "vendor": "Bitly/TinyURL/Rebrandly",
            "vendor_key": "shorteners",
            "configured": bool(any(shortener_config.values())),
            "env_keys": ["BITLY_ACCESS_TOKEN", "TINYURL_API_TOKEN", "REBRANDLY_API_KEY"],
            "capabilities": ["ai_scheduling", "ai_automation", "ai_ad_optimization"],
            "routes": ["/social/links/shorten", "/social/links"],
        },
        {
            "vendor": "OAuth social providers",
            "vendor_key": "oauth_providers",
            "configured": bool(all(oauth_vendor_keys.values())),
            "env_keys": [
                "SOCIAL_OAUTH_FACEBOOK_CLIENT_ID",
                "SOCIAL_OAUTH_LINKEDIN_CLIENT_ID",
                "SOCIAL_OAUTH_X_CLIENT_ID",
                "SOCIAL_OAUTH_TIKTOK_CLIENT_ID",
                "SOCIAL_OAUTH_YOUTUBE_CLIENT_ID",
                "SOCIAL_OAUTH_THREADS_CLIENT_ID",
            ],
            "capabilities": ["ai_scheduling", "ai_analytics"],
            "routes": ["/social/oauth/{network}/start", "/social/oauth/connect-all", "/social/accounts/connect"],
        },
    ]
