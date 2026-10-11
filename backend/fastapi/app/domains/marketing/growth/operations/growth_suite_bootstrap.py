"""Marketing/Growth use cases: growth suite bootstrap."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import _SLUG_PATTERN
from ..runtime import ContextRuntime
from ..schemas import AdsDraftRequest
from ..schemas import AgencyMemberRequest
from ..schemas import AgencyMrrRequest
from ..schemas import AgencyWorkspaceRequest
from ..schemas import AudienceDnaRequest
from ..schemas import ContentCalendarRequest
from ..schemas import EmailMarketingRequest
from ..schemas import GeoSeoRequest
from ..schemas import IraBrainRequest
from ..schemas import PodcastRequest
from ..schemas import RepurposeRequest
from ..schemas import SmartSchedulerRequest
from ..schemas import VideoScriptRequest
from ..services.now_iso import _ads_matrix
from ..services.now_iso import _audience_segments
from ..services.now_iso import _calendar_slots
from ..services.now_iso import _email_pack
from ..services.now_iso import _geo_seo
from ..services.now_iso import _podcast_episode
from ..services.now_iso import _repurpose_content
from ..services.now_iso import _scheduler_plan
from ..services.now_iso import _video_script
from .bootstrap import helper_bootstrap
from .ensure_tables import helper_load_records
from .ensure_tables import helper_store_record
from .ensure_tables import helper_summary
from fastapi import HTTPException
from typing import Any
import uuid


def execute_growth_suite_bootstrap(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:bootstrap", 10, 60)
    return helper_bootstrap(runtime, auth.tenant_id)


def execute_generate_content_calendar(
    runtime: ContextRuntime, payload: ContentCalendarRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:calendar", 20, 60)
    calendar = _calendar_slots(payload.topics, payload.days, payload.primary_channel)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "ai_content_calendar",
        "calendar",
        f"{payload.days}_day",
        {
            "status": "ready",
            "headline": f"{payload.days}-day plan generated from topic, trend, and revenue signals.",
            "metrics": [{"label": "Days", "value": payload.days}, {"label": "Topics", "value": len(payload.topics)}],
            "calendar": calendar,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "calendar": calendar}


def execute_create_agency_workspace(
    runtime: ContextRuntime, payload: AgencyWorkspaceRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:agency:create", 20, 60)
    workspace_key = f"agency_{uuid.uuid4().hex[:10]}"
    workspace = {
        "workspace_key": workspace_key,
        "name": payload.name,
        "owner_email": payload.owner_email,
        "clients": payload.clients,
        "members": [{"email": payload.owner_email, "role": "Owner"}],
        "approval_flow": ["Editor", "Client"],
        "mrr_total": 0.0,
    }
    helper_store_record(
        runtime,
        auth.tenant_id,
        "agency_portal",
        "workspace",
        workspace_key,
        {
            "status": "ready",
            "headline": "Agency workspace created with role-based approvals.",
            "metrics": [{"label": "Clients", "value": len(payload.clients)}, {"label": "Members", "value": 1}],
            "workspace": workspace,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "workspace": workspace}


def execute_add_agency_member(
    runtime: ContextRuntime, workspace_key: str, payload: AgencyMemberRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:agency:members", 40, 60)
    latest = helper_load_records(runtime, auth.tenant_id)
    record = next(
        (
            row
            for row in latest
            if row.get("feature_key") == "agency_portal" and row.get("resource_key") == workspace_key
        ),
        None,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Agency workspace not found.")
    content = record.get("payload", {}) if isinstance(record.get("payload"), dict) else {}
    workspace = content.get("workspace", {}) if isinstance(content.get("workspace"), dict) else {}
    members = workspace.get("members", []) if isinstance(workspace.get("members"), list) else []
    members.append({"email": payload.email, "role": payload.role})
    workspace["members"] = members
    content["workspace"] = workspace
    content["headline"] = "Agency workspace members updated."
    content["metrics"] = [
        {"label": "Members", "value": len(members)},
        {"label": "Roles configured", "value": len({member["role"] for member in members})},
    ]
    helper_store_record(runtime, auth.tenant_id, "agency_portal", "workspace", workspace_key, content)
    return {"status": "ok", "tenant_id": auth.tenant_id, "members": members}


def execute_add_agency_mrr(
    runtime: ContextRuntime, workspace_key: str, payload: AgencyMrrRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:agency:mrr", 40, 60)
    latest = helper_load_records(runtime, auth.tenant_id)
    record = next(
        (
            row
            for row in latest
            if row.get("feature_key") == "agency_portal" and row.get("resource_key") == workspace_key
        ),
        None,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Agency workspace not found.")
    content = record.get("payload", {}) if isinstance(record.get("payload"), dict) else {}
    workspace = content.get("workspace", {}) if isinstance(content.get("workspace"), dict) else {}
    mrr_entries = workspace.get("mrr_entries", []) if isinstance(workspace.get("mrr_entries"), list) else []
    mrr_entries.append(
        {"client_name": payload.client_name, "monthly_recurring_revenue": payload.monthly_recurring_revenue}
    )
    total_mrr = round(sum((float(entry["monthly_recurring_revenue"]) for entry in mrr_entries)), 2)
    workspace["mrr_entries"] = mrr_entries
    workspace["mrr_total"] = total_mrr
    content["workspace"] = workspace
    content["headline"] = f"Agency MRR updated to ${total_mrr:.2f}."
    content["metrics"] = [
        {"label": "Clients on retainer", "value": len(mrr_entries)},
        {"label": "MRR", "value": total_mrr},
    ]
    helper_store_record(runtime, auth.tenant_id, "agency_portal", "workspace", workspace_key, content)
    return {"status": "ok", "tenant_id": auth.tenant_id, "mrr_total": total_mrr}


def execute_agency_overview(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:agency:overview", 120, 60)
    workspaces = [
        row for row in helper_load_records(runtime, auth.tenant_id) if row.get("feature_key") == "agency_portal"
    ]
    total_mrr = 0.0
    total_members = 0
    for row in workspaces:
        payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        workspace = payload.get("workspace", {}) if isinstance(payload.get("workspace"), dict) else {}
        total_mrr += float(workspace.get("mrr_total") or 0.0)
        members = workspace.get("members", []) if isinstance(workspace.get("members"), list) else []
        total_members += len(members)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "overview": {"workspaces": len(workspaces), "total_members": total_members, "total_mrr": round(total_mrr, 2)},
    }


def execute_analyze_audience(runtime: ContextRuntime, payload: AudienceDnaRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:audience-dna", 30, 60)
    audience = _audience_segments(payload.audience_handles, payload.product_price)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "audience_dna",
        "analysis",
        "latest",
        {
            "status": "ready",
            "headline": "Audience segments and targeting recommendations are ready.",
            "metrics": [
                {"label": "Super fans", "value": audience["super_fans"]},
                {"label": "Buyer score", "value": audience["avg_buyer_score"]},
            ],
            "audience": audience,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "audience": audience}


def execute_ira_health_check(runtime: ContextRuntime, payload: IraBrainRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:ira", 30, 60)
    latest = helper_summary(runtime, auth.tenant_id)
    active_features = latest["totals"]["configured"]
    result = {
        "health_score": min(99, 70 + active_features),
        "focus": payload.focus,
        "scheduled_jobs": ["daily health check", "evergreen recycle", "weekly strategy adaptation"],
        "recommendations": ["Double down on the top forecasted topic.", "Repurpose the winner into owned channels."],
    }
    helper_store_record(
        runtime,
        auth.tenant_id,
        "ira_autonomous_brain",
        "run",
        "latest",
        {
            "status": "ready",
            "headline": "IRA completed a health check and queued autonomous actions.",
            "metrics": [
                {"label": "Health score", "value": result["health_score"]},
                {"label": "Scheduled jobs", "value": len(result["scheduled_jobs"])},
            ],
            "ira": result,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "ira": result}


def execute_create_ads_draft(runtime: ContextRuntime, payload: AdsDraftRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:ads", 30, 60)
    ads = _ads_matrix(payload.campaign_name, payload.offer, payload.primary_message)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "auto_ads_manager",
        "campaign",
        _SLUG_PATTERN.sub("_", payload.campaign_name.lower()).strip("_") or "campaign",
        {
            "status": "ready",
            "headline": "Draft ad pack created across all supported networks.",
            "metrics": [{"label": "Specs", "value": ads["spec_count"]}, {"label": "Status", "value": "draft"}],
            "ads": ads,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "ads": ads}


def execute_repurpose_content(runtime: ContextRuntime, payload: RepurposeRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:repurpose", 30, 60)
    repurpose = _repurpose_content(payload.source_content)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "content_repurpose_engine",
        "batch",
        "latest",
        {
            "status": "ready",
            "headline": "Repurpose batch generated for downstream publishing.",
            "metrics": [
                {"label": "Formats", "value": len(repurpose["outputs"])},
                {"label": "Hours saved", "value": repurpose["hours_saved"]},
            ],
            "repurpose": repurpose,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "repurpose": repurpose}


def execute_geo_analyze(runtime: ContextRuntime, payload: GeoSeoRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:geo", 30, 60)
    geo = _geo_seo(payload.content, payload.competitors)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "geo_seo_engine",
        "analysis",
        "latest",
        {
            "status": "ready",
            "headline": "AI-search optimization report generated.",
            "metrics": [
                {"label": "AI share of voice", "value": geo["ai_share_of_voice"]},
                {"label": "Citation score", "value": geo["citation_score"]},
            ],
            "geo_seo": geo,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "geo_seo": geo}


def execute_generate_email_marketing(
    runtime: ContextRuntime, payload: EmailMarketingRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:email", 30, 60)
    email = _email_pack(payload.source_content, payload.audience, payload.cta)
    runtime.email_campaigns_memory.append(
        {
            "id": len(runtime.email_campaigns_memory) + 1,
            "tenant_id": auth.tenant_id,
            "name": email["newsletter_subject"],
            "status": "draft",
            "sequence_length": len(email["drip_sequence"]),
        }
    )
    helper_store_record(
        runtime,
        auth.tenant_id,
        "email_marketing",
        "campaign",
        "latest",
        {
            "status": "ready",
            "headline": "Newsletter plus 5-email drip generated from source content.",
            "metrics": [
                {"label": "Drip emails", "value": len(email["drip_sequence"])},
                {"label": "Audience", "value": payload.audience},
            ],
            "email": email,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "email": email}


def execute_smart_fill(runtime: ContextRuntime, payload: SmartSchedulerRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:scheduler", 30, 60)
    scheduler = _scheduler_plan(payload.drafts, payload.platform, payload.fill_days)
    for item in scheduler["scheduled_items"]:
        runtime.scheduled_posts_memory.append(
            {
                "id": len(runtime.scheduled_posts_memory) + 1,
                "tenant_id": auth.tenant_id,
                "platform": item["platform"],
                "content": item["draft"],
                "status": "scheduled",
                "scheduled_for": item["scheduled_for"],
                "source": "smart-scheduler",
            }
        )
    helper_store_record(
        runtime,
        auth.tenant_id,
        "smart_scheduler",
        "plan",
        "latest",
        {
            "status": "ready",
            "headline": "Drafts distributed into your best-performing windows.",
            "metrics": [
                {"label": "Scheduled items", "value": len(scheduler["scheduled_items"])},
                {"label": "Fill days", "value": payload.fill_days},
            ],
            "scheduler": scheduler,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "scheduler": scheduler}


def execute_generate_podcast(runtime: ContextRuntime, payload: PodcastRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:podcast", 30, 60)
    episode = _podcast_episode(payload.title, payload.source_text)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "podcast_generator",
        "episode",
        _SLUG_PATTERN.sub("_", payload.title.lower()).strip("_") or "episode",
        {
            "status": "ready",
            "headline": "Podcast package generated with RSS-ready metadata.",
            "metrics": [
                {"label": "Chapters", "value": len(episode["chapters"])},
                {"label": "Clips", "value": episode["social_clips"]},
            ],
            "podcast": episode,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "podcast": episode}


def execute_generate_video_script(
    runtime: ContextRuntime, payload: VideoScriptRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:video", 30, 60)
    video = _video_script(payload.topic, payload.audience, payload.objective)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "video_script_generator",
        "script",
        "latest",
        {
            "status": "ready",
            "headline": "Video script package generated for production handoff.",
            "metrics": [
                {"label": "Scenes", "value": len(video["scenes"])},
                {"label": "Thumbnail concepts", "value": len(video["thumbnail_concepts"])},
            ],
            "video": video,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "video": video}


def execute_list_brand_voice_profiles(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """List all brand voice profiles for the tenant, including fingerprint and score."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:brand-voice:list", 120, 60)
    records = [
        row for row in helper_load_records(runtime, auth.tenant_id) if row.get("feature_key") == "brand_voice_dna"
    ]
    profiles = []
    for row in records:
        payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        bv = payload.get("brand_voice", {}) if isinstance(payload.get("brand_voice"), dict) else {}
        profiles.append(
            {
                "profile_key": row.get("resource_key"),
                "headline": payload.get("headline", ""),
                "voice_score": bv.get("voice_score", 0),
                "fingerprint": bv.get("fingerprint", {}),
                "rewrite": bv.get("rewrite", ""),
                "updated_at": row.get("updated_at"),
                "thumbs_up": int(payload.get("thumbs_up", 0)),
                "thumbs_down": int(payload.get("thumbs_down", 0)),
            }
        )
    return {"status": "ok", "tenant_id": auth.tenant_id, "profiles": profiles, "count": len(profiles)}
