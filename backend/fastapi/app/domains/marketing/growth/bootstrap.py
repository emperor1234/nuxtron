"""Marketing/Growth HTTP composition and legacy import exports."""

from __future__ import annotations
from .runtime import ContextRuntime
from .schemas import GrowthSuiteContext
from fastapi import APIRouter
import threading
from .api import (
    growth_suite_summary,
    create_agency_workspace,
    geo_analyze,
    list_ab_tests,
)
from .services.now_iso import _now_iso as _now_iso
from .services.now_iso import _tokenize as _tokenize
from .services.now_iso import _sentence_lengths as _sentence_lengths
from .services.now_iso import _pick_top_words as _pick_top_words
from .services.now_iso import _analyze_brand_voice as _analyze_brand_voice
from .services.now_iso import _ab_variants as _ab_variants
from .services.now_iso import _roi_forecast as _roi_forecast
from .services.now_iso import _calendar_slots as _calendar_slots
from .services.now_iso import _audience_segments as _audience_segments
from .services.now_iso import _ads_matrix as _ads_matrix
from .services.now_iso import _repurpose_content as _repurpose_content
from .services.now_iso import _geo_seo as _geo_seo
from .services.now_iso import _email_pack as _email_pack
from .services.now_iso import _scheduler_plan as _scheduler_plan
from .services.now_iso import _podcast_episode as _podcast_episode
from .services.now_iso import _video_script as _video_script
from .schemas import AgencyWorkspaceRequest as AgencyWorkspaceRequest
from .schemas import CounterStrikeRequest as CounterStrikeRequest
from .schemas import KeywordTrackRequest as KeywordTrackRequest
from .schemas import IraBrainRequest as IraBrainRequest
from .schemas import AgencyMemberRequest as AgencyMemberRequest
from .schemas import ABTestRequest as ABTestRequest
from .schemas import BrandVoiceFeedbackRequest as BrandVoiceFeedbackRequest
from .schemas import AdvancedReportRequest as AdvancedReportRequest
from .schemas import PodcastRequest as PodcastRequest
from .schemas import BrandHierarchyRequest as BrandHierarchyRequest
from .schemas import GeoSeoRequest as GeoSeoRequest
from .schemas import AdsDraftRequest as AdsDraftRequest
from .schemas import VideoScriptRequest as VideoScriptRequest
from .schemas import ContentCalendarRequest as ContentCalendarRequest
from .schemas import BrandVoiceRequest as BrandVoiceRequest
from .schemas import SmartSchedulerRequest as SmartSchedulerRequest
from .schemas import GrowthSuiteContext as GrowthSuiteContext
from .schemas import AudienceDnaRequest as AudienceDnaRequest
from .schemas import AgencyMrrRequest as AgencyMrrRequest
from .schemas import RepurposeRequest as RepurposeRequest
from .schemas import EmailMarketingRequest as EmailMarketingRequest
from .schemas import RoiForecastRequest as RoiForecastRequest
from .schemas import ABTestEvaluationRequest as ABTestEvaluationRequest
from .constants import _STOP_WORDS as _STOP_WORDS
from .constants import AuthDep as AuthDep
from .constants import _FEATURE_ORDER as _FEATURE_ORDER
from .constants import _SLUG_PATTERN as _SLUG_PATTERN
import json
import re
import statistics
import uuid
from collections import Counter
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Annotated
from typing import Any
from typing import Literal
import psycopg
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from ....deps import AuthContext
from ....deps import require_auth


def create_growth_suite_router(*, ctx: GrowthSuiteContext) -> APIRouter:
    router = APIRouter()
    lock = threading.Lock()
    db_init_lock = threading.Lock()
    db_initialized = {"done": False}
    enforce_rate_limit = ctx.enforce_rate_limit
    growth_suite_memory = ctx.growth_suite_memory
    scheduled_posts_memory = ctx.scheduled_posts_memory
    email_campaigns_memory = ctx.email_campaigns_memory
    chatbots_memory = ctx.chatbots_memory
    chatbot_leads_memory = ctx.chatbot_leads_memory
    linkinbio_pages_memory = ctx.linkinbio_pages_memory
    linkinbio_links_memory = ctx.linkinbio_links_memory
    analytics_reports_memory = ctx.analytics_reports_memory
    crm_contacts_memory = ctx.crm_contacts_memory
    crm_deals_memory = ctx.crm_deals_memory
    revenue_touchpoints_memory = ctx.revenue_touchpoints_memory
    revenue_conversions_memory = ctx.revenue_conversions_memory
    db_ready_fn = ctx.db_ready_fn
    db_dsn_fn = ctx.db_dsn_fn
    runtime = ContextRuntime(
        analytics_reports_memory=analytics_reports_memory,
        chatbot_leads_memory=chatbot_leads_memory,
        chatbots_memory=chatbots_memory,
        crm_contacts_memory=crm_contacts_memory,
        crm_deals_memory=crm_deals_memory,
        db_dsn_fn=db_dsn_fn,
        db_init_lock=db_init_lock,
        db_initialized=db_initialized,
        db_ready_fn=db_ready_fn,
        email_campaigns_memory=email_campaigns_memory,
        enforce_rate_limit=enforce_rate_limit,
        growth_suite_memory=growth_suite_memory,
        linkinbio_links_memory=linkinbio_links_memory,
        linkinbio_pages_memory=linkinbio_pages_memory,
        lock=lock,
        revenue_conversions_memory=revenue_conversions_memory,
        revenue_touchpoints_memory=revenue_touchpoints_memory,
        scheduled_posts_memory=scheduled_posts_memory,
    )
    growth_suite_summary.register(router, runtime)
    create_agency_workspace.register(router, runtime)
    geo_analyze.register(router, runtime)
    list_ab_tests.register(router, runtime)
    return router
