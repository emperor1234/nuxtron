"""Search/Visibility HTTP adapters beginning with swarm status."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.momentum_start import execute_content_generate
from ..operations.momentum_start import execute_content_generate_variants
from ..operations.momentum_start import execute_content_hooks
from ..operations.momentum_start import execute_momentum_inject
from ..operations.momentum_start import execute_momentum_start
from ..operations.optimal_triggers import execute_momentum_get
from ..operations.optimal_triggers import execute_swarm_database_stats
from ..operations.optimal_triggers import execute_swarm_status
from ..runtime import ContextRuntime
from ..schemas import HooksRequest
from ..schemas import MomentumInjectRequest
from ..schemas import MomentumStartRequest
from ..schemas import ViralContentRequest
from ..schemas import ViralContentVariantsRequest
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/swarm/{swarm_id}/status", responses={404: {"description": "Swarm not found."}})
    def swarm_status(swarm_id: str, auth: AuthDep) -> dict:
        return execute_swarm_status(runtime, swarm_id, auth)

    @router.get("/swarm/database/stats")
    def swarm_database_stats(auth: AuthDep) -> dict:
        return execute_swarm_database_stats(runtime, auth)

    @router.post("/momentum/start")
    def momentum_start(payload: MomentumStartRequest, auth: AuthDep) -> dict:
        return execute_momentum_start(runtime, payload, auth)

    @router.get("/momentum/{event_id}", responses={404: {"description": "Momentum event not found."}})
    def momentum_get(event_id: str, auth: AuthDep) -> dict:
        return execute_momentum_get(runtime, event_id, auth)

    @router.post("/momentum/{event_id}/inject", responses={404: {"description": "Momentum event not found."}})
    def momentum_inject(event_id: str, payload: MomentumInjectRequest, auth: AuthDep) -> dict:
        return execute_momentum_inject(runtime, event_id, payload, auth)

    @router.post(
        "/content/generate",
        responses={422: {"description": "Generated content did not meet minimum viral score threshold."}},
    )
    def content_generate(payload: ViralContentRequest, auth: AuthDep) -> dict:
        return execute_content_generate(runtime, payload, auth)

    @router.post(
        "/content/generate-variants",
        responses={422: {"description": "At least one generated variant did not meet minimum viral score threshold."}},
    )
    def content_generate_variants(payload: ViralContentVariantsRequest, auth: AuthDep) -> dict:
        return execute_content_generate_variants(runtime, payload, auth)

    @router.post("/content/hooks")
    def content_hooks(payload: HooksRequest, auth: AuthDep) -> dict:
        return execute_content_hooks(runtime, payload, auth)
