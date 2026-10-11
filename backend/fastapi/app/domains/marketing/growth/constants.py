"""Marketing/Growth constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from fastapi import Depends
from typing import Annotated
import re

AuthDep = Annotated[AuthContext, Depends(require_auth)]

_FEATURE_ORDER = [
    ("brand_voice_dna", "Brand Voice DNA"),
    ("auto_ab_testing", "Auto A/B Testing"),
    ("roi_forecaster", "ROI Forecaster"),
    ("counter_strike", "Counter-Strike"),
    ("ai_content_calendar", "AI Content Calendar"),
    ("agency_portal", "Agency Portal"),
    ("audience_dna", "Audience DNA"),
    ("ira_autonomous_brain", "IRA Autonomous Brain"),
    ("auto_ads_manager", "Auto Ads Manager"),
    ("content_repurpose_engine", "Content Repurpose Engine"),
    ("geo_seo_engine", "GEO / SEO Engine"),
    ("ai_lead_chatbot", "AI Lead Chatbot"),
    ("email_marketing", "Email Marketing"),
    ("smart_scheduler", "Smart Scheduler"),
    ("link_in_bio_builder", "Link-in-Bio Builder"),
    ("podcast_generator", "Podcast Generator"),
    ("video_script_generator", "Video Script Generator"),
    ("advanced_reports", "Advanced Reports"),
]

_SLUG_PATTERN = re.compile("[^a-z0-9]+")

_STOP_WORDS = {
    "the",
    "and",
    "that",
    "with",
    "your",
    "from",
    "this",
    "have",
    "about",
    "into",
    "will",
    "they",
    "them",
    "their",
    "there",
    "what",
    "when",
    "where",
    "which",
    "while",
    "were",
    "been",
    "being",
    "just",
    "than",
    "then",
    "also",
    "because",
    "across",
    "after",
    "before",
    "should",
    "would",
    "could",
    "over",
    "under",
    "more",
}
