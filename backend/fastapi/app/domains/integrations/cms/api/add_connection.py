"""Integrations/Cms HTTP adapters beginning with add connection."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import CMS_CONNECTION_NOT_FOUND
from ..operations.audit import execute_add_connection
from ..operations.audit import execute_crawler_analytics
from ..operations.audit import execute_list_cms_vendors
from ..operations.audit import execute_list_connections
from ..operations.audit import execute_list_pages
from ..operations.audit import execute_publish_content
from ..operations.audit import execute_schema_inject
from ..operations.audit import execute_sync_content
from ..runtime import ContextRuntime
from ..schemas import CmsConnectionRequest
from ..schemas import CmsPublishRequest
from ..schemas import CmsSchemaInjectRequest
from ..schemas import CmsSyncRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/cms/connections", responses={422: {"description": "Unsupported CMS type"}})
    def add_connection(payload: CmsConnectionRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_add_connection(runtime, payload, auth)

    @router.get("/cms/connections")
    def list_connections(auth: AuthDep) -> dict[str, Any]:
        return execute_list_connections(runtime, auth)

    @router.get("/cms/vendors")
    def list_cms_vendors(auth: AuthDep, connection_id: Annotated[int | None, Query(ge=1)] = None) -> dict[str, Any]:
        return execute_list_cms_vendors(runtime, auth, connection_id)

    @router.post("/cms/publish", responses={404: {"description": CMS_CONNECTION_NOT_FOUND}})
    def publish_content(payload: CmsPublishRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_publish_content(runtime, payload, auth)

    @router.post("/cms/sync", responses={404: {"description": CMS_CONNECTION_NOT_FOUND}})
    def sync_content(payload: CmsSyncRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_sync_content(runtime, payload, auth)

    @router.get("/cms/pages")
    def list_pages(auth: AuthDep) -> dict[str, Any]:
        return execute_list_pages(runtime, auth)

    @router.post("/cms/schema-inject", responses={404: {"description": CMS_CONNECTION_NOT_FOUND}})
    def schema_inject(payload: CmsSchemaInjectRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_schema_inject(runtime, payload, auth)

    @router.get("/cms/crawler-analytics")
    def crawler_analytics(auth: AuthDep) -> dict[str, Any]:
        return execute_crawler_analytics(runtime, auth)
