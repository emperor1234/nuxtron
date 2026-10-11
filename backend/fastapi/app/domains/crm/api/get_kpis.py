"""Crm HTTP adapters beginning with get kpis."""

from ..constants import AuthDep
from ..operations.create_api_token import execute_get_backup_ops
from ..operations.create_api_token import execute_get_executive_analytics
from ..operations.create_api_token import execute_get_kpis
from ..operations.create_api_token import execute_toggle_live_sync
from ..operations.create_api_token import execute_update_backup_config
from ..operations.create_segment import execute_get_live_sync_status
from ..operations.run_backup import execute_run_backup
from ..operations.run_backup import execute_run_live_sync
from ..runtime import ContextRuntime
from ..schemas import CRMBackupConfigRequest
from ..schemas import CRMLiveSyncToggleRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/crm/reports/kpis")
    def get_kpis(auth: AuthDep, days: Annotated[int, Query(ge=7, le=365)] = 30) -> dict[str, Any]:
        return execute_get_kpis(runtime, auth, days)

    @router.get("/crm/reports/executive-analytics")
    def get_executive_analytics(auth: AuthDep, days: Annotated[int, Query(ge=7, le=365)] = 30) -> dict[str, Any]:
        return execute_get_executive_analytics(runtime, auth, days)

    @router.get("/crm/ops/backup")
    def get_backup_ops(auth: AuthDep) -> dict[str, Any]:
        return execute_get_backup_ops(runtime, auth)

    @router.post("/crm/ops/backup/config")
    def update_backup_config(payload: CRMBackupConfigRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_backup_config(runtime, payload, auth)

    @router.post("/crm/ops/backup/run")
    def run_backup(
        auth: AuthDep,
        mode: Annotated[str, Query(pattern="^(incremental|full)$")] = "incremental",
        source: Annotated[str, Query(max_length=80)] = "manual",
    ) -> dict[str, Any]:
        return execute_run_backup(runtime, auth, mode, source)

    @router.get("/crm/ops/live-sync")
    def get_live_sync_status(auth: AuthDep) -> dict[str, Any]:
        return execute_get_live_sync_status(runtime, auth)

    @router.post("/crm/ops/live-sync/toggle")
    def toggle_live_sync(payload: CRMLiveSyncToggleRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_toggle_live_sync(runtime, payload, auth)

    @router.post("/crm/ops/live-sync/run")
    def run_live_sync(auth: AuthDep) -> dict[str, Any]:
        return execute_run_live_sync(runtime, auth)
