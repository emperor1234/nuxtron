"""Marketing/Growth HTTP adapters beginning with geo analyze."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.generate_advanced_report import execute_brand_voice_feedback
from ..operations.generate_advanced_report import execute_generate_advanced_report
from ..operations.growth_suite_bootstrap import execute_generate_email_marketing
from ..operations.growth_suite_bootstrap import execute_generate_podcast
from ..operations.growth_suite_bootstrap import execute_generate_video_script
from ..operations.growth_suite_bootstrap import execute_geo_analyze
from ..operations.growth_suite_bootstrap import execute_list_brand_voice_profiles
from ..operations.growth_suite_bootstrap import execute_smart_fill
from ..runtime import ContextRuntime
from ..schemas import AdvancedReportRequest
from ..schemas import BrandVoiceFeedbackRequest
from ..schemas import EmailMarketingRequest
from ..schemas import GeoSeoRequest
from ..schemas import PodcastRequest
from ..schemas import SmartSchedulerRequest
from ..schemas import VideoScriptRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/seo/geo-analyze")
    def geo_analyze(payload: GeoSeoRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_geo_analyze(runtime, payload, auth)

    @router.post("/email/ai-generate")
    def generate_email_marketing(payload: EmailMarketingRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_generate_email_marketing(runtime, payload, auth)

    @router.post("/scheduler/smart-fill")
    def smart_fill(payload: SmartSchedulerRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_smart_fill(runtime, payload, auth)

    @router.post("/podcast/generate")
    def generate_podcast(payload: PodcastRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_generate_podcast(runtime, payload, auth)

    @router.post("/video-script/generate")
    def generate_video_script(payload: VideoScriptRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_generate_video_script(runtime, payload, auth)

    @router.post("/reports/advanced")
    def generate_advanced_report(payload: AdvancedReportRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_generate_advanced_report(runtime, payload, auth)

    @router.get("/ai/brand-voice/profiles")
    def list_brand_voice_profiles(auth: AuthDep) -> dict[str, Any]:
        return execute_list_brand_voice_profiles(runtime, auth)

    @router.post(
        "/ai/brand-voice/{profile_key}/feedback", responses={404: {"description": "Brand voice profile not found."}}
    )
    def brand_voice_feedback(profile_key: str, payload: BrandVoiceFeedbackRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_brand_voice_feedback(runtime, profile_key, payload, auth)
