"""Search/Visibility HTTP adapters beginning with paid amplify."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.momentum_start import execute_paid_events_list
from ..operations.trends_live import execute_dark_social_attribution
from ..operations.trends_live import execute_dark_social_measurement
from ..operations.trends_live import execute_dark_social_seed
from ..operations.trends_live import execute_immortal_assets
from ..operations.trends_live import execute_immortalise
from ..operations.trends_live import execute_paid_amplify
from ..operations.trends_live import execute_viral_vault
from ..runtime import ContextRuntime
from ..schemas import DarkSocialAttributionRequest
from ..schemas import DarkSocialSeedRequest
from ..schemas import ImmortaliseRequest
from ..schemas import PaidAmplifyRequest
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/paid/amplify")
    def paid_amplify(payload: PaidAmplifyRequest, auth: AuthDep) -> dict:
        return execute_paid_amplify(runtime, payload, auth)

    @router.get("/paid/events")
    def paid_events_list(auth: AuthDep) -> dict:
        return execute_paid_events_list(runtime, auth)

    @router.post("/dark-social/seed")
    def dark_social_seed(payload: DarkSocialSeedRequest, auth: AuthDep) -> dict:
        return execute_dark_social_seed(runtime, payload, auth)

    @router.get("/dark-social/measurement")
    def dark_social_measurement(auth: AuthDep) -> dict:
        return execute_dark_social_measurement(runtime, auth)

    @router.post("/dark-social/attribution", responses={422: {"description": "Invalid attribution payload."}})
    def dark_social_attribution(payload: DarkSocialAttributionRequest, auth: AuthDep) -> dict:
        return execute_dark_social_attribution(runtime, payload, auth)

    @router.post("/immortalise")
    def immortalise(payload: ImmortaliseRequest, auth: AuthDep) -> dict:
        return execute_immortalise(runtime, payload, auth)

    @router.get("/immortalise/vault")
    def viral_vault(auth: AuthDep) -> dict:
        return execute_viral_vault(runtime, auth)

    @router.get(
        "/immortalise/{immortal_id}/assets", responses={404: {"description": "Immortalisation record not found."}}
    )
    def immortal_assets(immortal_id: str, auth: AuthDep) -> dict:
        return execute_immortal_assets(runtime, immortal_id, auth)
