"""Search/Visibility HTTP adapters beginning with simulate."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.trends_live import execute_simulate
from ..runtime import ContextRuntime
from ..schemas import CascadeSimulateRequest
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/simulate")
    def simulate(payload: CascadeSimulateRequest, auth: AuthDep) -> dict:
        return execute_simulate(runtime, payload, auth)
