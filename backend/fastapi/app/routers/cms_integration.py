# NEW MODULE — AI CMS Orchestrator (Part 3 Section 8.33)
# Implements 15+ CMS bidirectional sync, content routing, schema injection, publish.
# Memory-backed, same router factory pattern.

import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func

from ..database import get_db_session
from ..deps import AuthContext, require_auth
from ..models import Activity, Contact, Deal, Task

# Type alias for dependency injection
AuthDep = Annotated[AuthContext, Depends(require_auth)]

# Error message constants
CMS_CONNECTION_NOT_FOUND = 'CMS connection not found.'


# ── Supported CMS platforms from spec ────────────────────────────────────────

SUPPORTED_CMS = [
    'wordpress', 'webflow', 'contentful', 'sanity', 'ghost',
    'hubspot_cms', 'shopify', 'notion', 'confluence', 'wix',
    'squarespace', 'drupal', 'strapi', 'medium', 'custom',
]


# ── Request models ────────────────────────────────────────────────────────────

class CmsConnectionRequest(BaseModel):
    cms_type: str = Field(min_length=1, max_length=40)
    display_name: str = Field(min_length=1, max_length=120)
    api_url: str = Field(default='', max_length=500)
    api_key: str = Field(default='', max_length=320)
    site_id: str = Field(default='', max_length=120)


class CmsPublishRequest(BaseModel):
    connection_id: int
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=10, max_length=100_000)
    slug: str = Field(default='', max_length=240)
    tags: list[str] = Field(default_factory=list, max_length=20)
    inject_schema: bool = True
    status: str = Field(default='publish', max_length=20)


class CmsSyncRequest(BaseModel):
    connection_id: int
    direction: str = Field(default='push', pattern=r'^(push|pull|bidirectional)$')


class CmsSchemaInjectRequest(BaseModel):
    connection_id: int
    page_id: str = Field(min_length=1, max_length=120)
    schema_type: str = Field(default='Article', max_length=80)


class CmsAttributionLinkRequest(BaseModel):
    connection_id: int
    page_id: int | None = None
    page_slug: str | None = Field(default=None, max_length=240)
    campaign: str = Field(min_length=1, max_length=120)
    source: str = Field(default='direct', max_length=80)
    medium: str = Field(default='organic', max_length=80)
    term: str = Field(default='', max_length=120)
    content: str = Field(default='', max_length=120)
    landing_page_slug: str = Field(default='', max_length=240)
    form_template_name: str = Field(default='', max_length=180)


class CmsAttributionEventRequest(BaseModel):
    attribution_link_id: int
    event_type: str = Field(pattern=r'^(visit|lead|mql|sql|opportunity|customer)$')
    visitor_id: str = Field(default='', max_length=120)
    contact_email: str = Field(default='', max_length=255)
    value: float = Field(default=0.0, ge=0.0)
    sync_to_crm: bool = True
    contact_first_name: str = Field(default='', max_length=120)
    contact_last_name: str = Field(default='', max_length=120)
    company: str = Field(default='', max_length=180)
    create_deal: bool = False
    deal_title: str = Field(default='CMS Attributed Opportunity', max_length=180)
    deal_stage: str = Field(default='qualified', max_length=40)
    deal_value: float = Field(default=0.0, ge=0.0)


class CmsAttributionAutomationRuleRequest(BaseModel):
    campaign: str = Field(default='', max_length=120, description='Empty means all campaigns')
    trigger_event_type: str = Field(pattern=r'^(visit|lead|mql|sql|opportunity|customer)$')
    min_value: float = Field(default=0.0, ge=0.0)
    auto_enroll_sequence_id: int | None = None
    create_deal: bool = False
    deal_title: str = Field(default='CMS Attribution Rule Opportunity', max_length=180)
    deal_stage: str = Field(default='qualified', max_length=40)
    transition_deal_stage_to: str | None = Field(default=None, max_length=40)
    create_followup_task: bool = False
    task_title: str = Field(default='CMS Attribution Follow-up', max_length=180)
    task_priority: str = Field(default='medium', max_length=20)
    task_assigned_to: str = Field(default='', max_length=120)
    task_due_in_days: int = Field(default=2, ge=0, le=60)
    enabled: bool = True


# ── Factory ───────────────────────────────────────────────────────────────────

def create_cms_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    cms_connections_memory: list[dict[str, Any]],
    cms_pages_memory: list[dict[str, Any]],
    cms_sync_log_memory: list[dict[str, Any]],
    email_sequences_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter()
    lock = threading.Lock()
    cms_attribution_links_memory: list[dict[str, Any]] = []
    cms_attribution_events_memory: list[dict[str, Any]] = []
    cms_attribution_rules_memory: list[dict[str, Any]] = []
    cms_attribution_automation_runs_memory: list[dict[str, Any]] = []

    def _audit(tenant_id: str, action: str, resource_id: int | None = None) -> None:
        with lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'resource_id': resource_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'cms-router',
            })

    def _enroll_contact_in_sequence(tenant_id: str, seq_id: int, contact_id: int) -> tuple[bool, dict[str, Any] | None]:
        with lock:
            seq = next(
                (s for s in email_sequences_memory if int(s.get('id', 0)) == seq_id and s.get('tenant_id') == tenant_id),
                None,
            )
            if seq is None:
                return False, None
            enrolled_ids_raw = seq.get('enrolled_contact_ids', [])
            enrolled_ids = [int(v) for v in enrolled_ids_raw if str(v).strip().isdigit()]
            if contact_id in enrolled_ids:
                return False, seq.copy()
            enrolled_ids.append(contact_id)
            seq['enrolled_contact_ids'] = sorted(set(enrolled_ids))
            seq['enrollments'] = len(seq['enrolled_contact_ids'])
            seq['updated_at'] = datetime.now(UTC).isoformat()
            return True, seq.copy()

    def _cms_vendor_matrix(connection: dict[str, Any]) -> list[dict[str, Any]]:
        cms_type = str(connection.get('cms_type') or 'custom')
        api_configured = bool(connection.get('api_key_configured'))
        api_url = str(connection.get('api_url') or '').strip()
        return [
            {
                'vendor': f'{cms_type}_api',
                'purpose': 'CMS content API publish and sync',
                'integration': 'cms_api',
                'configured': api_configured,
                'runtime_dependency': True,
            },
            {
                'vendor': 'cdn_edge_cache',
                'purpose': 'Content delivery and invalidation',
                'integration': 'cdn_cache',
                'configured': bool(api_url),
                'runtime_dependency': False,
            },
            {
                'vendor': 'crawler_analytics',
                'purpose': 'AI crawler visibility tracking',
                'integration': 'analytics_events',
                'configured': True,
                'runtime_dependency': False,
            },
            {
                'vendor': 'crm_bridge',
                'purpose': 'Attribution sync to CRM contacts/deals/tasks',
                'integration': 'crm_attribution_bridge',
                'configured': True,
                'runtime_dependency': False,
            },
        ]

    def _cms_vendor_chart(connections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
        chart_map: dict[str, dict[str, Any]] = {}
        total_integrations = 0
        configured_integrations = 0

        for conn in connections:
            vendors = _cms_vendor_matrix(conn)
            for vendor in vendors:
                total_integrations += 1
                if bool(vendor.get('configured')):
                    configured_integrations += 1
                key = str(vendor.get('vendor') or 'unknown')
                row = chart_map.get(key)
                if row is None:
                    row = {
                        'vendor': key,
                        'purpose': str(vendor.get('purpose') or ''),
                        'integration': str(vendor.get('integration') or ''),
                        'runtime_dependency': bool(vendor.get('runtime_dependency')),
                        'connections_using': 0,
                        'connections_configured': 0,
                    }
                    chart_map[key] = row
                row['connections_using'] = int(row.get('connections_using', 0)) + 1
                if bool(vendor.get('configured')):
                    row['connections_configured'] = int(row.get('connections_configured', 0)) + 1

        chart = sorted(chart_map.values(), key=lambda r: str(r.get('vendor', '')))
        summary = {
            'connections': len(connections),
            'vendors': len(chart),
            'total_integrations': total_integrations,
            'configured_integrations': configured_integrations,
        }
        return chart, summary

    @router.post('/cms/connections', responses={422: {'description': 'Unsupported CMS type'}})
    def add_connection(payload: CmsConnectionRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:connections:create', 30, 60)
        if payload.cms_type not in SUPPORTED_CMS:
            raise HTTPException(
                status_code=422,
                detail=f'Unsupported CMS type. Supported: {", ".join(SUPPORTED_CMS)}',
            )
        with lock:
            conn: dict[str, Any] = {
                'id': len(cms_connections_memory) + 1,
                'tenant_id': auth.tenant_id,
                'cms_type': payload.cms_type,
                'display_name': payload.display_name,
                'api_url': payload.api_url,
                # SECURITY: never store raw API keys in memory; mark as configured only.
                'api_key_configured': bool(payload.api_key),
                'site_id': payload.site_id,
                'status': 'connected',
                'last_synced_at': None,
                'pages_synced': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'api',
            }
            cms_connections_memory.append(conn)

        _audit(auth.tenant_id, 'cms_connection_added', conn['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'connection': conn}

    @router.get('/cms/connections')
    def list_connections(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:connections:list', 120, 60)
        with lock:
            items = [c.copy() for c in cms_connections_memory if c.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'connections': items}

    @router.get('/cms/vendors')
    def list_cms_vendors(
        auth: AuthDep,
        connection_id: Annotated[int | None, Query(ge=1)] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:vendors:list', 120, 60)
        with lock:
            connections = [c.copy() for c in cms_connections_memory if c.get('tenant_id') == auth.tenant_id]

        if connection_id is not None:
            connection = next((c for c in connections if int(c.get('id', 0)) == int(connection_id)), None)
            if connection is None:
                raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)
            vendors = _cms_vendor_matrix(connection)
            chart, summary = _cms_vendor_chart([connection])
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'connection_id': int(connection_id),
                'cms_type': connection.get('cms_type', ''),
                'vendors': vendors,
                'vendor_chart': chart,
                'summary': summary,
            }

        chart, summary = _cms_vendor_chart(connections)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'connections': [
                {
                    'connection_id': int(c.get('id', 0)),
                    'cms_type': c.get('cms_type', ''),
                    'display_name': c.get('display_name', ''),
                    'vendors': _cms_vendor_matrix(c),
                }
                for c in connections
            ],
            'vendor_chart': chart,
            'summary': summary,
        }

    @router.post('/cms/publish', responses={404: {'description': CMS_CONNECTION_NOT_FOUND}})
    def publish_content(payload: CmsPublishRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:publish', 60, 60)
        with lock:
            conn = next(
                (c for c in cms_connections_memory
                 if c.get('id') == payload.connection_id and c.get('tenant_id') == auth.tenant_id),
                None,
            )
            if conn is None:
                raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)

            slug = payload.slug or payload.title.lower().replace(' ', '-')[:120]
            page: dict[str, Any] = {
                'id': len(cms_pages_memory) + 1,
                'tenant_id': auth.tenant_id,
                'connection_id': payload.connection_id,
                'cms_type': conn.get('cms_type'),
                'title': payload.title,
                'slug': slug,
                'content_preview': payload.content[:200],
                'tags': payload.tags,
                'schema_injected': payload.inject_schema,
                'status': payload.status,
                'published_at': datetime.now(UTC).isoformat(),
                'source': 'api',
            }
            cms_pages_memory.append(page)
            conn['pages_synced'] = conn.get('pages_synced', 0) + 1
            conn['last_synced_at'] = page['published_at']

        _audit(auth.tenant_id, 'cms_content_published', page['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'page': page}

    @router.post('/cms/sync', responses={404: {'description': CMS_CONNECTION_NOT_FOUND}})
    def sync_content(payload: CmsSyncRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:sync', 30, 60)
        with lock:
            conn = next(
                (c for c in cms_connections_memory
                 if c.get('id') == payload.connection_id and c.get('tenant_id') == auth.tenant_id),
                None,
            )
            if conn is None:
                raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)

            sync_record: dict[str, Any] = {
                'id': len(cms_sync_log_memory) + 1,
                'tenant_id': auth.tenant_id,
                'connection_id': payload.connection_id,
                'cms_type': conn.get('cms_type'),
                'direction': payload.direction,
                'items_synced': 0,
                'status': 'queued',
                'started_at': datetime.now(UTC).isoformat(),
            }
            cms_sync_log_memory.append(sync_record)
            conn['last_synced_at'] = sync_record['started_at']

        _audit(auth.tenant_id, 'cms_sync_triggered', sync_record['id'])
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'sync': sync_record,
            'message': f'Sync job queued for {conn.get("cms_type")} ({payload.direction}).',
        }

    @router.get('/cms/pages')
    def list_pages(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:pages:list', 120, 60)
        with lock:
            items = [p.copy() for p in cms_pages_memory if p.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda p: str(p.get('published_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'pages': items}

    @router.post('/cms/schema-inject', responses={404: {'description': CMS_CONNECTION_NOT_FOUND}})
    def schema_inject(payload: CmsSchemaInjectRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:schema-inject', 60, 60)
        with lock:
            conn = next(
                (c for c in cms_connections_memory
                 if c.get('id') == payload.connection_id and c.get('tenant_id') == auth.tenant_id),
                None,
            )
            if conn is None:
                raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)

        schema_payload = {
            '@context': 'https://schema.org',
            '@type': payload.schema_type,
            'identifier': payload.page_id,
        }
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'connection_id': payload.connection_id,
            'page_id': payload.page_id,
            'schema_type': payload.schema_type,
            'injected_at': datetime.now(UTC).isoformat(),
            'schema_preview': schema_payload,
        }

    @router.get('/cms/crawler-analytics')
    def crawler_analytics(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:crawler-analytics', 120, 60)
        with lock:
            conns = [c.copy() for c in cms_connections_memory if c.get('tenant_id') == auth.tenant_id]
            pages = [p.copy() for p in cms_pages_memory if p.get('tenant_id') == auth.tenant_id]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'analytics': {
                'total_connections': len(conns),
                'total_pages_published': len(pages),
                'schema_injected_pages': sum(1 for p in pages if p.get('schema_injected')),
                'cms_types_connected': list({c.get('cms_type') for c in conns}),
            },
        }

    @router.post('/cms/attribution/links', responses={404: {'description': CMS_CONNECTION_NOT_FOUND}})
    def create_attribution_link(payload: CmsAttributionLinkRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:attribution:links:create', 90, 60)
        with lock:
            conn = next(
                (
                    c for c in cms_connections_memory
                    if c.get('id') == payload.connection_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if conn is None:
                raise HTTPException(status_code=404, detail=CMS_CONNECTION_NOT_FOUND)

            linked_page = next(
                (
                    p for p in cms_pages_memory
                    if p.get('tenant_id') == auth.tenant_id
                    and p.get('connection_id') == payload.connection_id
                    and (
                        (payload.page_id is not None and p.get('id') == payload.page_id)
                        or (payload.page_slug is not None and p.get('slug') == payload.page_slug)
                    )
                ),
                None,
            )

            attribution_link: dict[str, Any] = {
                'id': len(cms_attribution_links_memory) + 1,
                'tenant_id': auth.tenant_id,
                'connection_id': payload.connection_id,
                'cms_type': conn.get('cms_type'),
                'page_id': linked_page.get('id') if linked_page else payload.page_id,
                'page_slug': linked_page.get('slug') if linked_page else (payload.page_slug or ''),
                'campaign': payload.campaign,
                'utm': {
                    'source': payload.source,
                    'medium': payload.medium,
                    'term': payload.term,
                    'content': payload.content,
                },
                'landing_page_slug': payload.landing_page_slug,
                'form_template_name': payload.form_template_name,
                'created_at': datetime.now(UTC).isoformat(),
            }
            cms_attribution_links_memory.append(attribution_link)

        _audit(auth.tenant_id, 'cms_attribution_link_created', attribution_link['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'attribution_link': attribution_link}

    @router.get('/cms/attribution/links')
    def list_attribution_links(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:attribution:links:list', 180, 60)
        with lock:
            links = [l.copy() for l in cms_attribution_links_memory if l.get('tenant_id') == auth.tenant_id]
        links.sort(key=lambda l: str(l.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(links), 'links': links}

    @router.post('/cms/attribution/automation-rules')
    def create_attribution_automation_rule(payload: CmsAttributionAutomationRuleRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:attribution:automation-rules:create', 90, 60)
        with lock:
            rule: dict[str, Any] = {
                'id': len(cms_attribution_rules_memory) + 1,
                'tenant_id': auth.tenant_id,
                'campaign': payload.campaign,
                'trigger_event_type': payload.trigger_event_type,
                'min_value': payload.min_value,
                'auto_enroll_sequence_id': payload.auto_enroll_sequence_id,
                'create_deal': payload.create_deal,
                'deal_title': payload.deal_title,
                'deal_stage': payload.deal_stage,
                'transition_deal_stage_to': payload.transition_deal_stage_to,
                'create_followup_task': payload.create_followup_task,
                'task_title': payload.task_title,
                'task_priority': payload.task_priority,
                'task_assigned_to': payload.task_assigned_to,
                'task_due_in_days': payload.task_due_in_days,
                'enabled': payload.enabled,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            cms_attribution_rules_memory.append(rule)
        _audit(auth.tenant_id, 'cms_attribution_automation_rule_created', rule['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'rule': rule}

    @router.get('/cms/attribution/automation-rules')
    def list_attribution_automation_rules(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:attribution:automation-rules:list', 180, 60)
        with lock:
            rules = [r.copy() for r in cms_attribution_rules_memory if r.get('tenant_id') == auth.tenant_id]
        rules.sort(key=lambda r: str(r.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(rules), 'rules': rules}

    @router.delete('/cms/attribution/automation-rules/{rule_id}', responses={404: {'description': 'Attribution automation rule not found.'}})
    def delete_attribution_automation_rule(rule_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:attribution:automation-rules:delete', 90, 60)
        with lock:
            before = len(cms_attribution_rules_memory)
            cms_attribution_rules_memory[:] = [
                r for r in cms_attribution_rules_memory
                if not (r.get('id') == rule_id and r.get('tenant_id') == auth.tenant_id)
            ]
            removed = before - len(cms_attribution_rules_memory)
        if removed == 0:
            raise HTTPException(status_code=404, detail='Attribution automation rule not found.')
        _audit(auth.tenant_id, 'cms_attribution_automation_rule_deleted', rule_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'removed': True, 'rule_id': rule_id}

    @router.get('/cms/attribution/automation-runs')
    def list_attribution_automation_runs(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:attribution:automation-runs:list', 180, 60)
        with lock:
            runs = [r.copy() for r in cms_attribution_automation_runs_memory if r.get('tenant_id') == auth.tenant_id]
        runs.sort(key=lambda r: str(r.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(runs), 'runs': runs}

    @router.post('/cms/attribution/events', responses={404: {'description': 'Attribution link not found.'}})
    def ingest_attribution_event(payload: CmsAttributionEventRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:attribution:events:create', 300, 60)
        normalized_email = payload.contact_email.strip().lower()
        with lock:
            link = next(
                (
                    l for l in cms_attribution_links_memory
                    if l.get('id') == payload.attribution_link_id and l.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if link is None:
                raise HTTPException(status_code=404, detail='Attribution link not found.')

            event: dict[str, Any] = {
                'id': len(cms_attribution_events_memory) + 1,
                'tenant_id': auth.tenant_id,
                'attribution_link_id': payload.attribution_link_id,
                'campaign': link.get('campaign', ''),
                'event_type': payload.event_type,
                'visitor_id': payload.visitor_id,
                'contact_email': normalized_email,
                'value': payload.value,
                'created_at': datetime.now(UTC).isoformat(),
            }
            cms_attribution_events_memory.append(event)

        crm_bridge: dict[str, Any] = {
            'synced': False,
            'contact_created': False,
            'contact_id': None,
            'activity_id': None,
            'deal_created': False,
            'deal_id': None,
        }

        should_sync = payload.sync_to_crm and bool(normalized_email)
        if should_sync:
            with get_db_session() as session:
                contact = session.query(Contact).filter(
                    Contact.tenant_id == auth.tenant_id,
                    func.lower(Contact.email) == normalized_email,
                ).first()
                if contact is None:
                    stage_map = {
                        'visit': 'lead',
                        'lead': 'lead',
                        'mql': 'mql',
                        'sql': 'sql',
                        'opportunity': 'opportunity',
                        'customer': 'customer',
                    }
                    contact = Contact(
                        tenant_id=auth.tenant_id,
                        email=normalized_email,
                        first_name=payload.contact_first_name,
                        last_name=payload.contact_last_name,
                        company=payload.company,
                        lifecycle_stage=stage_map.get(payload.event_type, 'lead'),
                        score=0,
                        data={
                            'source': 'cms_attribution',
                            'campaign': link.get('campaign', ''),
                            'utm': link.get('utm', {}),
                        },
                    )
                    session.add(contact)
                    session.flush()
                    crm_bridge['contact_created'] = True
                else:
                    updated_data = dict(contact.data or {})
                    updated_data['campaign'] = link.get('campaign', '')
                    updated_data['utm'] = link.get('utm', {})
                    contact.data = updated_data

                crm_bridge['contact_id'] = int(contact.id)

                activity = Activity(
                    tenant_id=auth.tenant_id,
                    type='cms_attribution',
                    contact_id=int(contact.id),
                    deal_id=None,
                    description=f"CMS attribution event: {payload.event_type}",
                    data={
                        'subject': 'CMS Attribution Event',
                        'event_type': payload.event_type,
                        'campaign': link.get('campaign', ''),
                        'attribution_link_id': payload.attribution_link_id,
                        'value': payload.value,
                        'source': 'cms-attribution',
                    },
                )
                session.add(activity)
                session.flush()
                crm_bridge['activity_id'] = int(activity.id)

                should_create_deal = payload.create_deal or (
                    payload.event_type in {'opportunity', 'customer'} and (payload.value > 0 or payload.deal_value > 0)
                )
                if should_create_deal:
                    deal_value = float(payload.deal_value if payload.deal_value > 0 else payload.value)
                    stage = payload.deal_stage.strip().lower() or 'qualified'
                    if stage not in {'prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'}:
                        stage = 'qualified'
                    deal = Deal(
                        tenant_id=auth.tenant_id,
                        title=payload.deal_title.strip() or 'CMS Attributed Opportunity',
                        value=deal_value,
                        currency='USD',
                        stage=stage,
                        contact_id=int(contact.id),
                        company_id=None,
                        close_date=None,
                        data={
                            'source': 'cms_attribution',
                            'campaign': link.get('campaign', ''),
                            'attribution_link_id': payload.attribution_link_id,
                            'probability': 25 if stage == 'qualified' else 10,
                        },
                    )
                    session.add(deal)
                    session.flush()
                    crm_bridge['deal_created'] = True
                    crm_bridge['deal_id'] = int(deal.id)

                crm_bridge['synced'] = True

        automation_executions: list[dict[str, Any]] = []
        with lock:
            rules = [
                r.copy() for r in cms_attribution_rules_memory
                if r.get('tenant_id') == auth.tenant_id and bool(r.get('enabled', True))
            ]

        for rule in rules:
            rule_campaign = str(rule.get('campaign') or '').strip().lower()
            event_campaign = str(link.get('campaign') or '').strip().lower()
            if rule_campaign and rule_campaign != event_campaign:
                continue
            if str(rule.get('trigger_event_type') or '') != payload.event_type:
                continue
            if float(payload.value) < float(rule.get('min_value', 0.0) or 0.0):
                continue

            execution: dict[str, Any] = {
                'id': 0,
                'tenant_id': auth.tenant_id,
                'rule_id': int(rule.get('id', 0) or 0),
                'event_id': int(event.get('id', 0) or 0),
                'campaign': link.get('campaign', ''),
                'event_type': payload.event_type,
                'actions': [],
                'created_at': datetime.now(UTC).isoformat(),
            }

            contact_id = crm_bridge.get('contact_id')
            sequence_id_raw = rule.get('auto_enroll_sequence_id')
            if contact_id is not None and sequence_id_raw is not None:
                try:
                    sequence_id = int(sequence_id_raw)
                except (TypeError, ValueError):
                    sequence_id = 0
                if sequence_id > 0:
                    enrolled_now, snapshot = _enroll_contact_in_sequence(auth.tenant_id, sequence_id, int(contact_id))
                    execution['actions'].append({
                        'action': 'sequence_enroll',
                        'sequence_id': sequence_id,
                        'contact_id': int(contact_id),
                        'success': snapshot is not None,
                        'enrolled_now': enrolled_now,
                    })

            if bool(rule.get('create_deal')) and contact_id is not None and not crm_bridge.get('deal_created'):
                stage = str(rule.get('deal_stage') or 'qualified').strip().lower()
                if stage not in {'prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'}:
                    stage = 'qualified'
                with get_db_session() as session:
                    deal = Deal(
                        tenant_id=auth.tenant_id,
                        title=str(rule.get('deal_title') or 'CMS Attribution Rule Opportunity'),
                        value=float(payload.value),
                        currency='USD',
                        stage=stage,
                        contact_id=int(contact_id),
                        company_id=None,
                        close_date=None,
                        data={
                            'source': 'cms_attribution_rule',
                            'campaign': link.get('campaign', ''),
                            'attribution_link_id': payload.attribution_link_id,
                            'rule_id': int(rule.get('id', 0) or 0),
                            'probability': 25 if stage == 'qualified' else 10,
                        },
                    )
                    session.add(deal)
                    session.flush()
                    execution['actions'].append({
                        'action': 'create_deal',
                        'success': True,
                        'deal_id': int(deal.id),
                        'value': float(payload.value),
                        'stage': stage,
                    })
                    crm_bridge['deal_created'] = True
                    crm_bridge['deal_id'] = int(deal.id)

            stage_target = str(rule.get('transition_deal_stage_to') or '').strip().lower()
            if contact_id is not None and stage_target:
                if stage_target not in {'prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'}:
                    stage_target = 'qualified'
                probability_map = {
                    'prospect': 10,
                    'qualified': 25,
                    'proposal': 50,
                    'negotiation': 75,
                    'closed_won': 100,
                    'closed_lost': 0,
                }
                with get_db_session() as session:
                    deal_obj: Deal | None = None
                    deal_id_raw = crm_bridge.get('deal_id')
                    deal_id = int(deal_id_raw) if str(deal_id_raw).strip().isdigit() else 0
                    if deal_id > 0:
                        deal_obj = session.query(Deal).filter(Deal.id == deal_id, Deal.tenant_id == auth.tenant_id).first()
                    if deal_obj is None:
                        deal_obj = (
                            session.query(Deal)
                            .filter(Deal.tenant_id == auth.tenant_id, Deal.contact_id == int(contact_id))
                            .order_by(Deal.id.desc())
                            .first()
                        )

                    if deal_obj is not None:
                        deal_obj.stage = stage_target
                        deal_data = dict(deal_obj.data or {})
                        deal_data['probability'] = probability_map.get(stage_target, 25)
                        deal_data['last_stage_transition_source'] = 'cms_attribution_rule'
                        deal_data['last_stage_transition_rule_id'] = int(rule.get('id', 0) or 0)
                        deal_data['last_stage_transition_event_id'] = int(event.get('id', 0) or 0)
                        deal_obj.data = deal_data
                        session.commit()
                        session.refresh(deal_obj)
                        crm_bridge['deal_id'] = int(deal_obj.id)
                        execution['actions'].append({
                            'action': 'transition_deal_stage',
                            'success': True,
                            'deal_id': int(deal_obj.id),
                            'stage': stage_target,
                        })
                    else:
                        execution['actions'].append({
                            'action': 'transition_deal_stage',
                            'success': False,
                            'reason': 'no_deal_found',
                            'stage': stage_target,
                        })

            if bool(rule.get('create_followup_task')) and contact_id is not None:
                task_priority = str(rule.get('task_priority') or 'medium').strip().lower()
                if task_priority not in {'low', 'medium', 'high'}:
                    task_priority = 'medium'
                due_days_raw = rule.get('task_due_in_days', 2)
                try:
                    due_days = int(due_days_raw)
                except (TypeError, ValueError):
                    due_days = 2
                due_days = max(0, min(due_days, 60))
                due_date = (datetime.now(UTC) + timedelta(days=due_days)).date().isoformat()
                task_title = str(rule.get('task_title') or 'CMS Attribution Follow-up').strip() or 'CMS Attribution Follow-up'
                assigned_to = str(rule.get('task_assigned_to') or '').strip()
                related_deal_id = crm_bridge.get('deal_id')
                related_deal_id_value = int(related_deal_id) if str(related_deal_id).strip().isdigit() else None
                with get_db_session() as session:
                    task = Task(
                        tenant_id=auth.tenant_id,
                        title=task_title,
                        status='open',
                        priority=task_priority,
                        assigned_to=assigned_to,
                        due_date=due_date,
                        related_contact_id=int(contact_id),
                        data={
                            'source': 'cms_attribution_rule',
                            'campaign': link.get('campaign', ''),
                            'rule_id': int(rule.get('id', 0) or 0),
                            'event_id': int(event.get('id', 0) or 0),
                            'related_deal_id': related_deal_id_value,
                        },
                    )
                    session.add(task)
                    session.flush()
                    execution['actions'].append({
                        'action': 'create_task',
                        'success': True,
                        'task_id': int(task.id),
                        'priority': task_priority,
                        'due_date': due_date,
                        'related_contact_id': int(contact_id),
                        'related_deal_id': related_deal_id_value,
                    })

            with lock:
                execution['id'] = len(cms_attribution_automation_runs_memory) + 1
                cms_attribution_automation_runs_memory.append(execution)
            automation_executions.append(execution)

        _audit(auth.tenant_id, 'cms_attribution_event_ingested', event['id'])
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'event': event,
            'crm_bridge': crm_bridge,
            'automation': {
                'matched_rules': len(automation_executions),
                'executions': automation_executions,
            },
        }

    @router.get('/cms/attribution/report')
    def attribution_report(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:cms:attribution:report', 120, 60)
        with lock:
            links = [l.copy() for l in cms_attribution_links_memory if l.get('tenant_id') == auth.tenant_id]
            events = [e.copy() for e in cms_attribution_events_memory if e.get('tenant_id') == auth.tenant_id]

        by_campaign: dict[str, dict[str, Any]] = {}
        for link in links:
            campaign = str(link.get('campaign') or 'unattributed')
            if campaign not in by_campaign:
                by_campaign[campaign] = {
                    'campaign': campaign,
                    'links': 0,
                    'visits': 0,
                    'leads': 0,
                    'customers': 0,
                    'pipeline_value': 0.0,
                    'revenue': 0.0,
                }
            by_campaign[campaign]['links'] += 1

        link_to_campaign = {int(l.get('id', 0)): str(l.get('campaign') or 'unattributed') for l in links}
        for event in events:
            campaign = link_to_campaign.get(int(event.get('attribution_link_id', 0)), 'unattributed')
            if campaign not in by_campaign:
                by_campaign[campaign] = {
                    'campaign': campaign,
                    'links': 0,
                    'visits': 0,
                    'leads': 0,
                    'customers': 0,
                    'pipeline_value': 0.0,
                    'revenue': 0.0,
                }
            event_type = str(event.get('event_type') or '')
            value = float(event.get('value') or 0.0)
            if event_type == 'visit':
                by_campaign[campaign]['visits'] += 1
            if event_type in {'lead', 'mql', 'sql', 'opportunity', 'customer'}:
                by_campaign[campaign]['leads'] += 1
                by_campaign[campaign]['pipeline_value'] = round(by_campaign[campaign]['pipeline_value'] + value, 2)
            if event_type == 'customer':
                by_campaign[campaign]['customers'] += 1
                by_campaign[campaign]['revenue'] = round(by_campaign[campaign]['revenue'] + value, 2)

        campaigns: list[dict[str, Any]] = []
        total_visits = 0
        total_leads = 0
        total_customers = 0
        total_pipeline = 0.0
        total_revenue = 0.0
        for item in by_campaign.values():
            visits = int(item['visits'])
            leads = int(item['leads'])
            customers = int(item['customers'])
            lead_conv = round((leads / visits) * 100.0, 2) if visits > 0 else 0.0
            customer_conv = round((customers / visits) * 100.0, 2) if visits > 0 else 0.0
            campaign_item = {
                **item,
                'visit_to_lead_conversion_pct': lead_conv,
                'visit_to_customer_conversion_pct': customer_conv,
            }
            campaigns.append(campaign_item)
            total_visits += visits
            total_leads += leads
            total_customers += customers
            total_pipeline = round(total_pipeline + float(item['pipeline_value']), 2)
            total_revenue = round(total_revenue + float(item['revenue']), 2)

        campaigns.sort(key=lambda c: float(c.get('revenue', 0.0)), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'summary': {
                'campaigns': len(campaigns),
                'links': len(links),
                'events': len(events),
                'visits': total_visits,
                'leads': total_leads,
                'customers': total_customers,
                'pipeline_value': total_pipeline,
                'revenue': total_revenue,
                'visit_to_lead_conversion_pct': round((total_leads / total_visits) * 100.0, 2) if total_visits > 0 else 0.0,
            },
            'campaigns': campaigns,
            'generated_at': datetime.now(UTC).isoformat(),
        }

    return router
