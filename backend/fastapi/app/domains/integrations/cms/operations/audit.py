"""Integrations/Cms use cases: audit."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import CMS_CONNECTION_NOT_FOUND
from ..constants import SUPPORTED_CMS
from ..runtime import ContextRuntime
from ..schemas import CmsAttributionLinkRequest
from ..schemas import CmsConnectionRequest
from ..schemas import CmsPublishRequest
from ..schemas import CmsSchemaInjectRequest
from ..schemas import CmsSyncRequest
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def helper_audit(runtime: ContextRuntime, tenant_id: str, action: str, resource_id: int | None = None) -> None:
    with runtime.lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "resource_id": resource_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "cms-router",
            }
        )


def helper_enroll_contact_in_sequence(
    runtime: ContextRuntime, tenant_id: str, seq_id: int, contact_id: int
) -> tuple[bool, dict[str, Any] | None]:
    with runtime.lock:
        seq = next(
            (
                s
                for s in runtime.email_sequences_memory
                if int(s.get("id", 0)) == seq_id and s.get("tenant_id") == tenant_id
            ),
            None,
        )
        if seq is None:
            return (False, None)
        enrolled_ids_raw = seq.get("enrolled_contact_ids", [])
        enrolled_ids = [int(v) for v in enrolled_ids_raw if str(v).strip().isdigit()]
        if contact_id in enrolled_ids:
            return (False, seq.copy())
        enrolled_ids.append(contact_id)
        seq["enrolled_contact_ids"] = sorted(set(enrolled_ids))
        seq["enrollments"] = len(seq["enrolled_contact_ids"])
        seq["updated_at"] = datetime.now(UTC).isoformat()
        return (True, seq.copy())


def helper_cms_vendor_matrix(connection: dict[str, Any]) -> list[dict[str, Any]]:
    cms_type = str(connection.get("cms_type") or "custom")
    api_configured = bool(connection.get("api_key_configured"))
    api_url = str(connection.get("api_url") or "").strip()
    return [
        {
            "vendor": f"{cms_type}_api",
            "purpose": "CMS content API publish and sync",
            "integration": "cms_api",
            "configured": api_configured,
            "runtime_dependency": True,
        },
        {
            "vendor": "cdn_edge_cache",
            "purpose": "Content delivery and invalidation",
            "integration": "cdn_cache",
            "configured": bool(api_url),
            "runtime_dependency": False,
        },
        {
            "vendor": "crawler_analytics",
            "purpose": "AI crawler visibility tracking",
            "integration": "analytics_events",
            "configured": True,
            "runtime_dependency": False,
        },
        {
            "vendor": "crm_bridge",
            "purpose": "Attribution sync to CRM contacts/deals/tasks",
            "integration": "crm_attribution_bridge",
            "configured": True,
            "runtime_dependency": False,
        },
    ]


def helper_cms_vendor_chart(connections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    chart_map: dict[str, dict[str, Any]] = {}
    total_integrations = 0
    configured_integrations = 0
    for conn in connections:
        vendors = helper_cms_vendor_matrix(conn)
        for vendor in vendors:
            total_integrations += 1
            if bool(vendor.get("configured")):
                configured_integrations += 1
            key = str(vendor.get("vendor") or "unknown")
            row = chart_map.get(key)
            if row is None:
                row = {
                    "vendor": key,
                    "purpose": str(vendor.get("purpose") or ""),
                    "integration": str(vendor.get("integration") or ""),
                    "runtime_dependency": bool(vendor.get("runtime_dependency")),
                    "connections_using": 0,
                    "connections_configured": 0,
                }
                chart_map[key] = row
            row["connections_using"] = int(row.get("connections_using", 0)) + 1
            if bool(vendor.get("configured")):
                row["connections_configured"] = int(row.get("connections_configured", 0)) + 1
    chart = sorted(chart_map.values(), key=lambda r: str(r.get("vendor", "")))
    summary = {
        "connections": len(connections),
        "vendors": len(chart),
        "total_integrations": total_integrations,
        "configured_integrations": configured_integrations,
    }
    return (chart, summary)


def execute_add_connection(runtime: ContextRuntime, payload: CmsConnectionRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:connections:create", 30, 60)
    if payload.cms_type not in SUPPORTED_CMS:
        raise HTTPException(status_code=422, detail=f"Unsupported CMS type. Supported: {', '.join(SUPPORTED_CMS)}")
    with runtime.lock:
        conn: dict[str, Any] = {
            "id": len(runtime.cms_connections_memory) + 1,
            "tenant_id": auth.tenant_id,
            "cms_type": payload.cms_type,
            "display_name": payload.display_name,
            "api_url": payload.api_url,
            "api_key_configured": bool(payload.api_key),
            "site_id": payload.site_id,
            "status": "connected",
            "last_synced_at": None,
            "pages_synced": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "source": "api",
        }
        runtime.cms_connections_memory.append(conn)
    helper_audit(runtime, auth.tenant_id, "cms_connection_added", conn["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "connection": conn}


def execute_list_connections(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:connections:list", 120, 60)
    with runtime.lock:
        items = [c.copy() for c in runtime.cms_connections_memory if c.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "connections": items}


def execute_list_cms_vendors(
    runtime: ContextRuntime, auth: AuthDep, connection_id: Annotated[int | None, Query(ge=1)] = None
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:vendors:list", 120, 60)
    with runtime.lock:
        connections = [c.copy() for c in runtime.cms_connections_memory if c.get("tenant_id") == auth.tenant_id]
    if connection_id is not None:
        connection = next((c for c in connections if int(c.get("id", 0)) == int(connection_id)), None)
        if connection is None:
            raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)
        vendors = helper_cms_vendor_matrix(connection)
        chart, summary = helper_cms_vendor_chart([connection])
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "connection_id": int(connection_id),
            "cms_type": connection.get("cms_type", ""),
            "vendors": vendors,
            "vendor_chart": chart,
            "summary": summary,
        }
    chart, summary = helper_cms_vendor_chart(connections)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "connections": [
            {
                "connection_id": int(c.get("id", 0)),
                "cms_type": c.get("cms_type", ""),
                "display_name": c.get("display_name", ""),
                "vendors": helper_cms_vendor_matrix(c),
            }
            for c in connections
        ],
        "vendor_chart": chart,
        "summary": summary,
    }


def execute_publish_content(runtime: ContextRuntime, payload: CmsPublishRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:publish", 60, 60)
    with runtime.lock:
        conn = next(
            (
                c
                for c in runtime.cms_connections_memory
                if c.get("id") == payload.connection_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if conn is None:
            raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)
        slug = payload.slug or payload.title.lower().replace(" ", "-")[:120]
        page: dict[str, Any] = {
            "id": len(runtime.cms_pages_memory) + 1,
            "tenant_id": auth.tenant_id,
            "connection_id": payload.connection_id,
            "cms_type": conn.get("cms_type"),
            "title": payload.title,
            "slug": slug,
            "content_preview": payload.content[:200],
            "tags": payload.tags,
            "schema_injected": payload.inject_schema,
            "status": payload.status,
            "published_at": datetime.now(UTC).isoformat(),
            "source": "api",
        }
        runtime.cms_pages_memory.append(page)
        conn["pages_synced"] = conn.get("pages_synced", 0) + 1
        conn["last_synced_at"] = page["published_at"]
    helper_audit(runtime, auth.tenant_id, "cms_content_published", page["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "page": page}


def execute_sync_content(runtime: ContextRuntime, payload: CmsSyncRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:sync", 30, 60)
    with runtime.lock:
        conn = next(
            (
                c
                for c in runtime.cms_connections_memory
                if c.get("id") == payload.connection_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if conn is None:
            raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)
        sync_record: dict[str, Any] = {
            "id": len(runtime.cms_sync_log_memory) + 1,
            "tenant_id": auth.tenant_id,
            "connection_id": payload.connection_id,
            "cms_type": conn.get("cms_type"),
            "direction": payload.direction,
            "items_synced": 0,
            "status": "queued",
            "started_at": datetime.now(UTC).isoformat(),
        }
        runtime.cms_sync_log_memory.append(sync_record)
        conn["last_synced_at"] = sync_record["started_at"]
    helper_audit(runtime, auth.tenant_id, "cms_sync_triggered", sync_record["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "sync": sync_record,
        "message": f"Sync job queued for {conn.get('cms_type')} ({payload.direction}).",
    }


def execute_list_pages(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:pages:list", 120, 60)
    with runtime.lock:
        items = [p.copy() for p in runtime.cms_pages_memory if p.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda p: str(p.get("published_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "pages": items}


def execute_schema_inject(runtime: ContextRuntime, payload: CmsSchemaInjectRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:schema-inject", 60, 60)
    with runtime.lock:
        conn = next(
            (
                c
                for c in runtime.cms_connections_memory
                if c.get("id") == payload.connection_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if conn is None:
            raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)
    schema_payload = {"@context": "https://schema.org", "@type": payload.schema_type, "identifier": payload.page_id}
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "connection_id": payload.connection_id,
        "page_id": payload.page_id,
        "schema_type": payload.schema_type,
        "injected_at": datetime.now(UTC).isoformat(),
        "schema_preview": schema_payload,
    }


def execute_crawler_analytics(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:crawler-analytics", 120, 60)
    with runtime.lock:
        conns = [c.copy() for c in runtime.cms_connections_memory if c.get("tenant_id") == auth.tenant_id]
        pages = [p.copy() for p in runtime.cms_pages_memory if p.get("tenant_id") == auth.tenant_id]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "analytics": {
            "total_connections": len(conns),
            "total_pages_published": len(pages),
            "schema_injected_pages": sum((1 for p in pages if p.get("schema_injected"))),
            "cms_types_connected": list({c.get("cms_type") for c in conns}),
        },
    }


def execute_create_attribution_link(
    runtime: ContextRuntime, payload: CmsAttributionLinkRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:attribution:links:create", 90, 60)
    with runtime.lock:
        conn = next(
            (
                c
                for c in runtime.cms_connections_memory
                if c.get("id") == payload.connection_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if conn is None:
            raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)
        linked_page = next(
            (
                p
                for p in runtime.cms_pages_memory
                if p.get("tenant_id") == auth.tenant_id
                and p.get("connection_id") == payload.connection_id
                and (
                    payload.page_id is not None
                    and p.get("id") == payload.page_id
                    or (payload.page_slug is not None and p.get("slug") == payload.page_slug)
                )
            ),
            None,
        )
        attribution_link: dict[str, Any] = {
            "id": len(runtime.cms_attribution_links_memory) + 1,
            "tenant_id": auth.tenant_id,
            "connection_id": payload.connection_id,
            "cms_type": conn.get("cms_type"),
            "page_id": linked_page.get("id") if linked_page else payload.page_id,
            "page_slug": linked_page.get("slug") if linked_page else payload.page_slug or "",
            "campaign": payload.campaign,
            "utm": {
                "source": payload.source,
                "medium": payload.medium,
                "term": payload.term,
                "content": payload.content,
            },
            "landing_page_slug": payload.landing_page_slug,
            "form_template_name": payload.form_template_name,
            "created_at": datetime.now(UTC).isoformat(),
        }
        runtime.cms_attribution_links_memory.append(attribution_link)
    helper_audit(runtime, auth.tenant_id, "cms_attribution_link_created", attribution_link["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "attribution_link": attribution_link}


def execute_list_attribution_links(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:attribution:links:list", 180, 60)
    with runtime.lock:
        links = [l.copy() for l in runtime.cms_attribution_links_memory if l.get("tenant_id") == auth.tenant_id]
    links.sort(key=lambda l: str(l.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(links), "links": links}


def execute_list_attribution_automation_rules(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:attribution:automation-rules:list", 180, 60)
    with runtime.lock:
        rules = [r.copy() for r in runtime.cms_attribution_rules_memory if r.get("tenant_id") == auth.tenant_id]
    rules.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(rules), "rules": rules}
