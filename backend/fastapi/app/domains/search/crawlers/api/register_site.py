"""Search/Crawlers HTTP adapters beginning with register site."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.deploy_snippets_bulk import execute_deploy_snippets_bulk
from ..operations.deploy_snippets_bulk import execute_detect_crawler
from ..operations.deploy_snippets_bulk import execute_list_crawlers
from ..operations.deploy_snippets_bulk import execute_verify_snippet
from ..operations.now_iso import execute_get_snippet
from ..operations.now_iso import execute_list_sites
from ..operations.now_iso import execute_register_site
from ..operations.now_iso import execute_unregister_site
from ..runtime import ContextRuntime
from ..schemas import BulkSnippetDeployRequest
from ..schemas import CrawlerDetectRequest
from ..schemas import SiteRegisterRequest
from ..schemas import SnippetVerifyRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/sites", status_code=201)
    def register_site(payload: SiteRegisterRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_register_site(runtime, payload, auth)

    @router.get("/sites")
    def list_sites(auth: AuthDep) -> dict[str, Any]:
        return execute_list_sites(runtime, auth)

    @router.delete("/sites/{site_id}", status_code=200)
    def unregister_site(site_id: str, auth: AuthDep) -> dict[str, Any]:
        return execute_unregister_site(runtime, site_id, auth)

    @router.get("/sites/{site_id}/snippet")
    def get_snippet(site_id: str, auth: AuthDep) -> dict[str, Any]:
        return execute_get_snippet(runtime, site_id, auth)

    @router.post("/snippets/deploy-bulk")
    def deploy_snippets_bulk(payload: BulkSnippetDeployRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_deploy_snippets_bulk(runtime, payload, auth)

    @router.post("/sites/{site_id}/snippet/verify")
    def verify_snippet(site_id: str, payload: SnippetVerifyRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_verify_snippet(runtime, site_id, payload, auth)

    @router.get("/crawlers")
    def list_crawlers(
        auth: AuthDep, category: str | None = Query(default=None), enabled_only: bool = Query(default=False)
    ) -> dict[str, Any]:
        return execute_list_crawlers(runtime, auth, category, enabled_only)

    @router.post("/crawlers/detect")
    def detect_crawler(payload: CrawlerDetectRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_detect_crawler(runtime, payload, auth)
