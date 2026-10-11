"""Marketing/Growth HTTP adapters beginning with growth suite summary."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.ensure_tables import execute_brand_voice_profile
from ..operations.ensure_tables import execute_create_ab_test
from ..operations.ensure_tables import execute_evaluate_ab_test
from ..operations.ensure_tables import execute_forecast_roi
from ..operations.ensure_tables import execute_growth_suite_summary
from ..operations.ensure_tables import execute_trigger_counter_strike
from ..operations.growth_suite_bootstrap import execute_generate_content_calendar
from ..operations.growth_suite_bootstrap import execute_growth_suite_bootstrap
from ..runtime import ContextRuntime
from ..schemas import ABTestEvaluationRequest
from ..schemas import ABTestRequest
from ..schemas import BrandVoiceRequest
from ..schemas import ContentCalendarRequest
from ..schemas import CounterStrikeRequest
from ..schemas import RoiForecastRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/ops/platform/growth-suite")
    def growth_suite_summary(auth: AuthDep) -> dict[str, Any]:
        return execute_growth_suite_summary(runtime, auth)

    @router.post("/ops/platform/growth-suite/bootstrap")
    def growth_suite_bootstrap(auth: AuthDep) -> dict[str, Any]:
        return execute_growth_suite_bootstrap(runtime, auth)

    @router.post("/ai/brand-voice/profile")
    def brand_voice_profile(payload: BrandVoiceRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_brand_voice_profile(runtime, payload, auth)

    @router.post("/experiments/ab-tests")
    def create_ab_test(payload: ABTestRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_ab_test(runtime, payload, auth)

    @router.post(
        "/experiments/ab-tests/{test_key}/evaluate",
        responses={
            404: {"description": "A/B test not found."},
            422: {"description": "No variants available for evaluation."},
        },
    )
    def evaluate_ab_test(test_key: str, payload: ABTestEvaluationRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_evaluate_ab_test(runtime, test_key, payload, auth)

    @router.post("/forecast/roi")
    def forecast_roi(payload: RoiForecastRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_forecast_roi(runtime, payload, auth)

    @router.post("/features/counter-strike/trigger")
    def trigger_counter_strike(payload: CounterStrikeRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_trigger_counter_strike(runtime, payload, auth)

    @router.post("/calendar/content-plan")
    def generate_content_calendar(payload: ContentCalendarRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_generate_content_calendar(runtime, payload, auth)
