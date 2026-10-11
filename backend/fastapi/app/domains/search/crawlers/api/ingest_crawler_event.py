"""Search/Crawlers HTTP adapters beginning with ingest crawler event."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.cloudflare_sync import execute_cloudflare_auto_sync
from ..operations.cloudflare_sync import execute_cloudflare_sync
from ..operations.cloudflare_sync import execute_readiness
from ..operations.deploy_snippets_bulk import execute_crawler_dashboard
from ..operations.deploy_snippets_bulk import execute_get_crawler_events
from ..operations.deploy_snippets_bulk import execute_ingest_crawler_event
from ..operations.deploy_snippets_bulk import execute_list_ssr_cache
from ..operations.deploy_snippets_bulk import execute_request_ssr_render
from ..runtime import ContextRuntime
from ..schemas import CloudflareAutoSyncRequest
from ..schemas import CloudflareSyncRequest
from ..schemas import CrawlerEventIngestRequest
from ..schemas import SsrRenderRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/events", status_code=201)
    def ingest_crawler_event(payload: CrawlerEventIngestRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ingest_crawler_event(runtime, payload, auth)

    @router.get("/events")
    def get_crawler_events(
        auth: AuthDep,
        site_id: str | None = Query(default=None),
        crawler_name: str | None = Query(default=None),
        ai_only: bool = Query(default=False),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> dict[str, Any]:
        return execute_get_crawler_events(runtime, auth, site_id, crawler_name, ai_only, limit)

    @router.get("/dashboard")
    def crawler_dashboard(
        auth: AuthDep, site_id: str | None = Query(default=None), window_hours: int = Query(default=24, ge=1, le=168)
    ) -> dict[str, Any]:
        return execute_crawler_dashboard(runtime, auth, site_id, window_hours)

    @router.post("/ssr/render")
    def request_ssr_render(payload: SsrRenderRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_request_ssr_render(runtime, payload, auth)

    @router.get("/ssr/cache")
    def list_ssr_cache(
        auth: AuthDep, site_id: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=500)
    ) -> dict[str, Any]:
        return execute_list_ssr_cache(runtime, auth, site_id, limit)

    @router.post("/cloudflare/sync")
    def cloudflare_sync(payload: CloudflareSyncRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_cloudflare_sync(runtime, payload, auth)

    @router.post("/cloudflare/auto-sync")
    def cloudflare_auto_sync(payload: CloudflareAutoSyncRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_cloudflare_auto_sync(runtime, payload, auth)

    @router.get("/readiness")
    def readiness(auth: AuthDep) -> dict[str, Any]:
        return execute_readiness(runtime, auth)
