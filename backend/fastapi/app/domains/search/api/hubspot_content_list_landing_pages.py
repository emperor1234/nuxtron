"""Search HTTP operations beginning with hubspot content list landing pages."""

from ..constants import AuthDep
from ..operations.hubspot_route_coverage_chart import operation_hubspot_content_list_blog_posts
from ..operations.hubspot_route_coverage_chart import operation_hubspot_content_list_landing_pages
from ..operations.hubspot_route_coverage_chart import operation_hubspot_content_list_podcasts
from ..operations.hubspot_route_coverage_chart import operation_hubspot_data_list_sync_jobs
from ..operations.hubspot_wiring_required_keys import operation_hubspot_content_create_blog_post
from ..operations.hubspot_wiring_required_keys import operation_hubspot_content_create_podcast
from ..operations.hubspot_wiring_required_keys import operation_hubspot_data_create_quality_rule
from ..operations.hubspot_wiring_required_keys import operation_hubspot_data_create_sync_job
from ..runtime import SearchRuntime
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hubspot/content/landing-pages")
    def hubspot_content_list_landing_pages(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_content_list_landing_pages(runtime, auth)

    @router.post("/hubspot/content/blog-posts")
    def hubspot_content_create_blog_post(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_content_create_blog_post(runtime, payload, auth)

    @router.get("/hubspot/content/blog-posts")
    def hubspot_content_list_blog_posts(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_content_list_blog_posts(runtime, auth)

    @router.post("/hubspot/content/podcasts")
    def hubspot_content_create_podcast(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_content_create_podcast(runtime, payload, auth)

    @router.get("/hubspot/content/podcasts")
    def hubspot_content_list_podcasts(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_content_list_podcasts(runtime, auth)

    @router.post("/hubspot/data/sync-jobs")
    def hubspot_data_create_sync_job(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_data_create_sync_job(runtime, payload, auth)

    @router.get("/hubspot/data/sync-jobs")
    def hubspot_data_list_sync_jobs(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_data_list_sync_jobs(runtime, auth)

    @router.post("/hubspot/data/quality-rules")
    def hubspot_data_create_quality_rule(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_data_create_quality_rule(runtime, payload, auth)
