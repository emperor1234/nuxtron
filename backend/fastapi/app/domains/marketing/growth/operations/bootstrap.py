"""Marketing/Growth use cases: bootstrap."""

from __future__ import annotations
from ..runtime import ContextRuntime
from ..schemas import RoiForecastRequest
from ..services.now_iso import _ab_variants
from ..services.now_iso import _ads_matrix
from ..services.now_iso import _analyze_brand_voice
from ..services.now_iso import _audience_segments
from ..services.now_iso import _calendar_slots
from ..services.now_iso import _email_pack
from ..services.now_iso import _geo_seo
from ..services.now_iso import _podcast_episode
from ..services.now_iso import _repurpose_content
from ..services.now_iso import _roi_forecast
from ..services.now_iso import _scheduler_plan
from ..services.now_iso import _video_script
from .ensure_tables import helper_store_record
from .ensure_tables import helper_summary
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
import uuid


def helper_bootstrap(runtime: ContextRuntime, tenant_id: str) -> dict[str, Any]:
    brand_voice = _analyze_brand_voice(
        [
            "We publish proof-heavy growth content with sharp hooks and direct outcomes.",
            "If a post cannot drive pipeline, it should not take up the slot.",
            "Clarity wins. Specificity wins. Revenue wins.",
        ],
        "This is a generic AI post about growth and content performance.",
    )
    helper_store_record(
        runtime,
        tenant_id,
        "brand_voice_dna",
        "profile",
        "primary",
        {
            "status": "ready",
            "headline": f"Voice score {brand_voice['voice_score']}/100 with a reusable fingerprint.",
            "metrics": [
                {"label": "Voice score", "value": brand_voice["voice_score"]},
                {"label": "Signature words", "value": len(brand_voice["fingerprint"]["signature_words"])},
            ],
            "brand_voice": brand_voice,
        },
    )
    variants = _ab_variants("Turn audience attention into attributed revenue with one publishing engine.")
    test_key = f"ab_{uuid.uuid4().hex[:10]}"
    scores = [0.24, 0.31, 0.28, 0.37, 0.34]
    winning_index = max(range(len(scores)), key=lambda index: scores[index])
    runtime.scheduled_posts_memory.append(
        {
            "id": len(runtime.scheduled_posts_memory) + 1,
            "tenant_id": tenant_id,
            "platform": "linkedin",
            "content": variants[winning_index]["content"],
            "status": "scheduled",
            "scheduled_for": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "source": "growth-suite",
        }
    )
    helper_store_record(
        runtime,
        tenant_id,
        "auto_ab_testing",
        "test",
        test_key,
        {
            "status": "ready",
            "headline": "Five variants generated, winner selected, republish queued.",
            "metrics": [{"label": "Variants", "value": 5}, {"label": "Winner score", "value": scores[winning_index]}],
            "variants": variants,
            "winner": variants[winning_index],
        },
    )
    forecast = _roi_forecast(RoiForecastRequest(content_title="Pipeline post", platform="linkedin"))
    helper_store_record(
        runtime,
        tenant_id,
        "roi_forecaster",
        "forecast",
        "latest",
        {
            "status": "ready",
            "headline": f"Predicted revenue ${forecast['projected_revenue']:.2f} before publishing.",
            "metrics": [
                {"label": "Projected revenue", "value": forecast["projected_revenue"]},
                {"label": "Projected engagement", "value": forecast["projected_engagement"]},
            ],
            "forecast": forecast,
        },
    )
    helper_store_record(
        runtime,
        tenant_id,
        "counter_strike",
        "event",
        "latest",
        {
            "status": "ready",
            "headline": "Competitor watch is active with a 60-second response window.",
            "metrics": [{"label": "Response window sec", "value": 60}, {"label": "Queued counters", "value": 1}],
            "generated_post": "Their angle is broad. Our counter narrows to proof, timing, and a clearer CTA.",
        },
    )
    calendar = _calendar_slots(["revenue attribution", "brand voice", "ai search"], 90, "linkedin")
    helper_store_record(
        runtime,
        tenant_id,
        "ai_content_calendar",
        "calendar",
        "90_day",
        {
            "status": "ready",
            "headline": "A 90-day calendar has been generated from revenue and trend signals.",
            "metrics": [{"label": "Days planned", "value": 90}, {"label": "Topics", "value": 3}],
            "calendar": calendar,
        },
    )
    helper_store_record(
        runtime,
        tenant_id,
        "agency_portal",
        "workspace",
        "agency_primary",
        {
            "status": "ready",
            "headline": "Agency workspace, client roles, approval controls, and MRR tracking are active.",
            "metrics": [{"label": "Clients", "value": 2}, {"label": "MRR", "value": 12450.0}],
            "members": [
                {"email": "owner@nuxtron.io", "role": "Owner"},
                {"email": "editor@nuxtron.io", "role": "Editor"},
                {"email": "client@example.com", "role": "Client"},
            ],
            "approval_flow": ["Editor", "Client"],
        },
    )
    audience = _audience_segments([], 99)
    helper_store_record(
        runtime,
        tenant_id,
        "audience_dna",
        "analysis",
        "latest",
        {
            "status": "ready",
            "headline": "Audience clusters and buyer scores are ready for targeting.",
            "metrics": [
                {"label": "Super fans", "value": audience["super_fans"]},
                {"label": "Avg buyer score", "value": audience["avg_buyer_score"]},
            ],
            "audience": audience,
        },
    )
    helper_store_record(
        runtime,
        tenant_id,
        "ira_autonomous_brain",
        "run",
        "daily",
        {
            "status": "ready",
            "headline": "Daily health checks and evergreen recycling are scheduled.",
            "metrics": [{"label": "Health score", "value": 92}, {"label": "Recycled assets", "value": 3}],
            "actions": [
                "Recycle the top carousel into email and video.",
                "Boost the forecasted winner with paid support.",
            ],
        },
    )
    ads = _ads_matrix(
        "Launch Engine", "Free strategy audit", "One brief turns into multi-platform ad drafts that stay on-brand."
    )
    helper_store_record(
        runtime,
        tenant_id,
        "auto_ads_manager",
        "campaign",
        "launch_engine",
        {
            "status": "ready",
            "headline": "Draft campaigns were generated across 13 ad specs.",
            "metrics": [{"label": "Ad specs", "value": ads["spec_count"]}, {"label": "Draft status", "value": "draft"}],
            "ads": ads,
        },
    )
    repurpose = _repurpose_content("Revenue attribution lets you prove which posts create pipeline, not just reach.")
    helper_store_record(
        runtime,
        tenant_id,
        "content_repurpose_engine",
        "batch",
        "latest",
        {
            "status": "ready",
            "headline": "One source asset was repurposed into 20 publishable formats.",
            "metrics": [
                {"label": "Formats", "value": len(repurpose["outputs"])},
                {"label": "Hours saved", "value": repurpose["hours_saved"]},
            ],
            "repurpose": repurpose,
        },
    )
    geo = _geo_seo(
        "Structure content for citation, proof, and answer-style retrieval.", ["competitor-a", "competitor-b"]
    )
    helper_store_record(
        runtime,
        tenant_id,
        "geo_seo_engine",
        "analysis",
        "latest",
        {
            "status": "ready",
            "headline": "AI search visibility and share-of-voice metrics are available.",
            "metrics": [
                {"label": "AI share of voice", "value": geo["ai_share_of_voice"]},
                {"label": "Citation score", "value": geo["citation_score"]},
            ],
            "geo_seo": geo,
        },
    )
    chatbot_id = len(runtime.chatbots_memory) + 1
    runtime.chatbots_memory.append(
        {
            "id": chatbot_id,
            "tenant_id": tenant_id,
            "name": "Growth Concierge",
            "status": "deployed",
            "trained": True,
            "deployed": True,
        }
    )
    runtime.chatbot_leads_memory.append(
        {
            "id": len(runtime.chatbot_leads_memory) + 1,
            "tenant_id": tenant_id,
            "chatbot_id": chatbot_id,
            "lead_score": 87,
            "email": "lead@example.com",
        }
    )
    helper_store_record(
        runtime,
        tenant_id,
        "ai_lead_chatbot",
        "deployment",
        "growth_concierge",
        {
            "status": "ready",
            "headline": "Website chatbot is deployed and capturing qualified leads.",
            "metrics": [{"label": "Lead score", "value": 87}, {"label": "Active bots", "value": 1}],
        },
    )
    email = _email_pack("Weekly brief on the highest-leverage revenue moves.", "warm leads", "Book a strategy call")
    runtime.email_campaigns_memory.append(
        {
            "id": len(runtime.email_campaigns_memory) + 1,
            "tenant_id": tenant_id,
            "name": email["newsletter_subject"],
            "status": "draft",
            "sequence_length": len(email["drip_sequence"]),
        }
    )
    helper_store_record(
        runtime,
        tenant_id,
        "email_marketing",
        "campaign",
        "latest",
        {
            "status": "ready",
            "headline": "Newsletter and 5-email drip sequence are ready to launch.",
            "metrics": [
                {"label": "Drip emails", "value": len(email["drip_sequence"])},
                {"label": "Campaign status", "value": "draft"},
            ],
            "email": email,
        },
    )
    scheduler = _scheduler_plan(["Launch post", "Proof post", "CTA post"], "linkedin", 7)
    for item in scheduler["scheduled_items"]:
        runtime.scheduled_posts_memory.append(
            {
                "id": len(runtime.scheduled_posts_memory) + 1,
                "tenant_id": tenant_id,
                "platform": item["platform"],
                "content": item["draft"],
                "status": "scheduled",
                "scheduled_for": item["scheduled_for"],
                "source": "smart-scheduler",
            }
        )
    helper_store_record(
        runtime,
        tenant_id,
        "smart_scheduler",
        "plan",
        "weekly_fill",
        {
            "status": "ready",
            "headline": "Best-time posting windows have been applied to queued drafts.",
            "metrics": [
                {"label": "Scheduled items", "value": len(scheduler["scheduled_items"])},
                {"label": "Best windows", "value": len(scheduler["best_windows"])},
            ],
            "scheduler": scheduler,
        },
    )
    page_id = len(runtime.linkinbio_pages_memory) + 1
    runtime.linkinbio_pages_memory.append(
        {"id": page_id, "tenant_id": tenant_id, "title": "Creator Storefront", "status": "published"}
    )
    runtime.linkinbio_links_memory.append(
        {
            "id": len(runtime.linkinbio_links_memory) + 1,
            "tenant_id": tenant_id,
            "page_id": page_id,
            "title": "Featured offer",
        }
    )
    helper_store_record(
        runtime,
        tenant_id,
        "link_in_bio_builder",
        "page",
        "creator_storefront",
        {
            "status": "ready",
            "headline": "Shoppable bio page and analytics-ready links are published.",
            "metrics": [{"label": "Pages", "value": 1}, {"label": "Links", "value": 1}],
        },
    )
    podcast = _podcast_episode(
        "Revenue Systems Weekly", "Today we break down how content should map to pipeline, not vanity reach."
    )
    helper_store_record(
        runtime,
        tenant_id,
        "podcast_generator",
        "episode",
        "weekly_show",
        {
            "status": "ready",
            "headline": "Podcast episode script, clips, and RSS metadata have been generated.",
            "metrics": [
                {"label": "Chapters", "value": len(podcast["chapters"])},
                {"label": "Social clips", "value": podcast["social_clips"]},
            ],
            "podcast": podcast,
        },
    )
    video = _video_script("Revenue attribution", "founders", "more qualified pipeline")
    helper_store_record(
        runtime,
        tenant_id,
        "video_script_generator",
        "script",
        "latest",
        {
            "status": "ready",
            "headline": "Video script, storyboard, b-roll, and SRT preview are prepared.",
            "metrics": [
                {"label": "Scenes", "value": len(video["scenes"])},
                {"label": "B-roll shots", "value": len(video["b_roll"])},
            ],
            "video": video,
        },
    )
    runtime.analytics_reports_memory.append(
        {
            "id": len(runtime.analytics_reports_memory) + 1,
            "tenant_id": tenant_id,
            "name": "Executive Revenue Report",
            "status": "ready",
        }
    )
    helper_store_record(
        runtime,
        tenant_id,
        "advanced_reports",
        "report",
        "executive",
        {
            "status": "ready",
            "headline": "White-label executive reporting is generated with platform and revenue breakdowns.",
            "metrics": [{"label": "CSV export", "value": "ready"}, {"label": "Executive summary", "value": "included"}],
            "csv_export_path": "/analytics/export",
        },
    )
    return helper_summary(runtime, tenant_id)
