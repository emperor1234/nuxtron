"""Search/Visibility HTTP adapters beginning with content score."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.momentum_start import execute_content_score
from ..operations.momentum_start import execute_emotion_analyze
from ..operations.momentum_start import execute_emotion_audience_state
from ..operations.momentum_start import execute_emotion_engineer
from ..operations.trends_live import execute_paid_assess
from ..operations.trends_live import execute_trends_alerts
from ..operations.trends_live import execute_trends_hijack
from ..operations.trends_live import execute_trends_live
from ..runtime import ContextRuntime
from ..schemas import ContentScoreRequest
from ..schemas import EmotionAnalyzeRequest
from ..schemas import EmotionEngineerRequest
from ..schemas import PaidAssessRequest
from ..schemas import TrendHijackRequest
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/content/score")
    def content_score(payload: ContentScoreRequest, auth: AuthDep) -> dict:
        return execute_content_score(runtime, payload, auth)

    @router.post("/emotion/analyze")
    def emotion_analyze(payload: EmotionAnalyzeRequest, auth: AuthDep) -> dict:
        return execute_emotion_analyze(runtime, payload, auth)

    @router.post("/emotion/engineer")
    def emotion_engineer(payload: EmotionEngineerRequest, auth: AuthDep) -> dict:
        return execute_emotion_engineer(runtime, payload, auth)

    @router.get("/emotion/audience-state")
    def emotion_audience_state(auth: AuthDep) -> dict:
        return execute_emotion_audience_state(runtime, auth)

    @router.get("/trends/live")
    def trends_live(auth: AuthDep) -> dict:
        return execute_trends_live(runtime, auth)

    @router.post(
        "/trends/hijack",
        responses={
            404: {"description": "Trend ID not found. Check GET /vse/trends/live"},
            422: {"description": "Trend authenticity score below required threshold."},
        },
    )
    def trends_hijack(payload: TrendHijackRequest, auth: AuthDep) -> dict:
        return execute_trends_hijack(runtime, payload, auth)

    @router.get("/trends/alerts")
    def trends_alerts(auth: AuthDep) -> dict:
        return execute_trends_alerts(runtime, auth)

    @router.post("/paid/assess")
    def paid_assess(payload: PaidAssessRequest, auth: AuthDep) -> dict:
        return execute_paid_assess(runtime, payload, auth)
