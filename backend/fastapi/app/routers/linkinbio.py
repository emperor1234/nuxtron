# NEW MODULE — Link-in-Bio Engine (Part 3 Section 8.35, Buffer Start Page-class)
# Implements shoppable link pages, A/B testing, analytics, custom domains.
# Memory-backed, same router factory pattern.

import threading
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

# Type alias for dependency injection
AuthDep = Annotated[AuthContext, Depends(require_auth)]

# Error message constants
PAGE_NOT_FOUND = 'Page not found.'
LINK_NOT_FOUND = 'Link not found.'


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


# ── Request models ────────────────────────────────────────────────────────────

class LinkinbioPageCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    bio: str = Field(default='', max_length=320)
    theme: str = Field(default='minimal', max_length=40)
    custom_domain: str = Field(default='', max_length=240)
    profile_image_url: str = Field(default='', max_length=500)


class LinkinbioLinkAddRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=5, max_length=2000)
    emoji: str = Field(default='', max_length=10)
    is_product: bool = False
    product_price: float = Field(default=0.0, ge=0.0)
    product_currency: str = Field(default='USD', max_length=8)
    active: bool = True


class LinkinbioPageUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=320)
    theme: str | None = Field(default=None, max_length=40)
    custom_domain: str | None = Field(default=None, max_length=240)


class LinkinbioLinkUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    url: str | None = Field(default=None, min_length=5, max_length=2000)
    emoji: str | None = Field(default=None, max_length=10)
    is_product: bool | None = None
    product_price: float | None = Field(default=None, ge=0.0)
    product_currency: str | None = Field(default=None, max_length=8)
    active: bool | None = None


# ── Factory ───────────────────────────────────────────────────────────────────

def create_linkinbio_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    linkinbio_pages_memory: list[dict[str, Any]],
    linkinbio_links_memory: list[dict[str, Any]],
    linkinbio_analytics_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter()
    lock = threading.Lock()

    def _audit(tenant_id: str, action: str, resource_id: int | None = None) -> None:
        with lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'resource_id': resource_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'linkinbio-router',
            })

    def _record_analytics_event(
        *,
        tenant_id: str,
        page_id: int,
        event_type: str,
        link_id: int | None = None,
        count: int = 1,
    ) -> None:
        now = datetime.now(UTC)
        with lock:
            linkinbio_analytics_memory.append({
                'id': len(linkinbio_analytics_memory) + 1,
                'tenant_id': tenant_id,
                'page_id': page_id,
                'link_id': link_id,
                'event_type': event_type,
                'count': count,
                'bucket_date': now.date().isoformat(),
                'created_at': now.isoformat(),
            })

    # Keep analytics memory wired for compatibility with app router factory composition.
    _ = linkinbio_analytics_memory

    @router.post('/linkinbio/pages')
    def create_page(payload: LinkinbioPageCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:pages:create', 30, 60)
        with lock:
            page: dict[str, Any] = {
                'id': len(linkinbio_pages_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title,
                'bio': payload.bio,
                'theme': payload.theme,
                'custom_domain': payload.custom_domain,
                'profile_image_url': payload.profile_image_url,
                'slug': f'{auth.tenant_id}-{len(linkinbio_pages_memory) + 1}',
                'published': True,
                'total_views': 0,
                'total_clicks': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
                'source': 'api',
            }
            linkinbio_pages_memory.append(page)

        _audit(auth.tenant_id, 'linkinbio_page_created', page['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'page': page}

    @router.get('/linkinbio/pages')
    def list_pages(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:pages:list', 120, 60)
        with lock:
            pages = [p.copy() for p in linkinbio_pages_memory if p.get('tenant_id') == auth.tenant_id]
        pages.sort(key=lambda p: str(p.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(pages), 'pages': pages}

    @router.patch('/linkinbio/pages/{page_id}', responses={404: {'description': PAGE_NOT_FOUND}})
    def update_page(page_id: int, payload: LinkinbioPageUpdateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:pages:update', 60, 60)
        with lock:
            page = next(
                (p for p in linkinbio_pages_memory
                 if p.get('id') == page_id and p.get('tenant_id') == auth.tenant_id),
                None,
            )
            if page is None:
                raise HTTPException(status_code=404, detail=PAGE_NOT_FOUND)
            if payload.title is not None:
                page['title'] = payload.title
            if payload.bio is not None:
                page['bio'] = payload.bio
            if payload.theme is not None:
                page['theme'] = payload.theme
            if payload.custom_domain is not None:
                page['custom_domain'] = payload.custom_domain
            page['updated_at'] = datetime.now(UTC).isoformat()
            snapshot = page.copy()

        _audit(auth.tenant_id, 'linkinbio_page_updated', page_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'page': snapshot}

    @router.post('/linkinbio/pages/{page_id}/links', responses={404: {'description': PAGE_NOT_FOUND}})
    def add_link(page_id: int, payload: LinkinbioLinkAddRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:links:add', 60, 60)
        with lock:
            page = next(
                (p for p in linkinbio_pages_memory
                 if p.get('id') == page_id and p.get('tenant_id') == auth.tenant_id),
                None,
            )
            if page is None:
                raise HTTPException(status_code=404, detail=PAGE_NOT_FOUND)

            link: dict[str, Any] = {
                'id': len(linkinbio_links_memory) + 1,
                'tenant_id': auth.tenant_id,
                'page_id': page_id,
                'label': payload.label,
                'url': payload.url,
                'emoji': payload.emoji,
                'is_product': payload.is_product,
                'product_price': payload.product_price,
                'product_currency': payload.product_currency,
                'active': payload.active,
                'clicks': 0,
                'created_at': datetime.now(UTC).isoformat(),
            }
            linkinbio_links_memory.append(link)

        _audit(auth.tenant_id, 'linkinbio_link_added', link['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'link': link}

    @router.get('/linkinbio/pages/{page_id}/links', responses={404: {'description': PAGE_NOT_FOUND}})
    def list_links(page_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:links:list', 120, 60)
        with lock:
            page_exists = any(
                p.get('id') == page_id and p.get('tenant_id') == auth.tenant_id
                for p in linkinbio_pages_memory
            )
            if not page_exists:
                raise HTTPException(status_code=404, detail=PAGE_NOT_FOUND)
            links = [
                l.copy() for l in linkinbio_links_memory
                if l.get('page_id') == page_id and l.get('tenant_id') == auth.tenant_id
            ]
        links.sort(key=lambda item: int(item.get('id', 0)))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(links), 'links': links}

    @router.patch(
        '/linkinbio/pages/{page_id}/links/{link_id}',
        responses={404: {'description': LINK_NOT_FOUND}},
    )
    def update_link(
        page_id: int,
        link_id: int,
        payload: LinkinbioLinkUpdateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:links:update', 120, 60)
        with lock:
            link = next(
                (
                    item for item in linkinbio_links_memory
                    if item.get('id') == link_id
                    and item.get('page_id') == page_id
                    and item.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if link is None:
                raise HTTPException(status_code=404, detail=LINK_NOT_FOUND)

            if payload.label is not None:
                link['label'] = payload.label
            if payload.url is not None:
                link['url'] = payload.url
            if payload.emoji is not None:
                link['emoji'] = payload.emoji
            if payload.is_product is not None:
                link['is_product'] = payload.is_product
            if payload.product_price is not None:
                link['product_price'] = payload.product_price
            if payload.product_currency is not None:
                link['product_currency'] = payload.product_currency
            if payload.active is not None:
                link['active'] = payload.active

            snapshot = link.copy()

        _audit(auth.tenant_id, 'linkinbio_link_updated', link_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'link': snapshot}

    @router.delete(
        '/linkinbio/pages/{page_id}/links/{link_id}',
        responses={404: {'description': LINK_NOT_FOUND}},
    )
    def delete_link(page_id: int, link_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:links:delete', 120, 60)
        with lock:
            idx = next(
                (
                    i for i, item in enumerate(linkinbio_links_memory)
                    if item.get('id') == link_id
                    and item.get('page_id') == page_id
                    and item.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if idx is None:
                raise HTTPException(status_code=404, detail=LINK_NOT_FOUND)
            removed = linkinbio_links_memory.pop(idx)

        _audit(auth.tenant_id, 'linkinbio_link_deleted', link_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'deleted': removed}

    @router.post(
        '/linkinbio/pages/{page_id}/links/{link_id}/click',
        responses={404: {'description': LINK_NOT_FOUND}},
    )
    def record_link_click(page_id: int, link_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:links:click', 240, 60)
        with lock:
            page = next(
                (
                    p for p in linkinbio_pages_memory
                    if p.get('id') == page_id and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            link = next(
                (
                    item for item in linkinbio_links_memory
                    if item.get('id') == link_id
                    and item.get('page_id') == page_id
                    and item.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if page is None or link is None:
                raise HTTPException(status_code=404, detail=LINK_NOT_FOUND)

            page['total_views'] = int(page.get('total_views', 0)) + 1
            page['total_clicks'] = int(page.get('total_clicks', 0)) + 1
            link['clicks'] = int(link.get('clicks', 0)) + 1
            link_snapshot = link.copy()

        _record_analytics_event(tenant_id=auth.tenant_id, page_id=page_id, link_id=link_id, event_type='view')
        _record_analytics_event(tenant_id=auth.tenant_id, page_id=page_id, link_id=link_id, event_type='click')

        _audit(auth.tenant_id, 'linkinbio_link_clicked', link_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'link': link_snapshot}

    @router.post('/linkinbio/pages/{page_id}/view', responses={404: {'description': PAGE_NOT_FOUND}})
    def record_page_view(page_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:page:view', 300, 60)
        with lock:
            page = next(
                (
                    p for p in linkinbio_pages_memory
                    if p.get('id') == page_id and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if page is None:
                raise HTTPException(status_code=404, detail=PAGE_NOT_FOUND)
            page['total_views'] = int(page.get('total_views', 0)) + 1
            page_snapshot = page.copy()

        _record_analytics_event(tenant_id=auth.tenant_id, page_id=page_id, event_type='view')
        _audit(auth.tenant_id, 'linkinbio_page_viewed', page_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'page': page_snapshot}

    @router.get('/linkinbio/pages/{page_id}/analytics', responses={404: {'description': PAGE_NOT_FOUND}})
    def page_analytics(page_id: int, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:analytics', 120, 60)
        with lock:
            page = next(
                (p.copy() for p in linkinbio_pages_memory
                 if p.get('id') == page_id and p.get('tenant_id') == auth.tenant_id),
                None,
            )
            if page is None:
                raise HTTPException(status_code=404, detail=PAGE_NOT_FOUND)
            links = [
                l.copy() for l in linkinbio_links_memory
                if l.get('page_id') == page_id and l.get('tenant_id') == auth.tenant_id
            ]

        total_clicks = sum(int(l.get('clicks', 0)) for l in links)
        top_links = sorted(links, key=lambda l: int(l.get('clicks', 0)), reverse=True)[:5]

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'analytics': {
                'page_id': page_id,
                'total_views': page.get('total_views', 0),
                'total_clicks': total_clicks,
                'click_through_rate': 0.0 if page.get('total_views', 0) == 0 else round(total_clicks / max(1, page['total_views']), 4),
                'top_links': top_links,
                'total_links': len(links),
                'active_links': sum(1 for l in links if l.get('active')),
            },
        }

    @router.get('/linkinbio/pages/{page_id}/analytics/timeseries', responses={404: {'description': PAGE_NOT_FOUND}})
    def page_analytics_timeseries(
        page_id: int,
        auth: AuthDep,
        days: int = 30,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:linkinbio:analytics:timeseries', 120, 60)
        window_days = min(max(days, 1), 90)

        with lock:
            page_exists = any(
                p.get('id') == page_id and p.get('tenant_id') == auth.tenant_id
                for p in linkinbio_pages_memory
            )
            if not page_exists:
                raise HTTPException(status_code=404, detail=PAGE_NOT_FOUND)

            page_links = [
                item.copy() for item in linkinbio_links_memory
                if item.get('tenant_id') == auth.tenant_id and item.get('page_id') == page_id
            ]

            events = [
                event.copy() for event in linkinbio_analytics_memory
                if event.get('tenant_id') == auth.tenant_id and event.get('page_id') == page_id
            ]

        start_day = date.today() - timedelta(days=window_days - 1)
        buckets: dict[str, dict[str, int]] = {}

        for day_offset in range(window_days):
            day = (start_day + timedelta(days=day_offset)).isoformat()
            buckets[day] = {'views': 0, 'clicks': 0}

        link_meta = {
            int(item.get('id', 0)): {
                'link_id': int(item.get('id', 0)),
                'label': str(item.get('label', '')),
            }
            for item in page_links
            if int(item.get('id', 0)) > 0
        }
        link_buckets: dict[int, dict[str, int]] = {
            link_id: dict.fromkeys(buckets, 0)
            for link_id in link_meta
        }

        for event in events:
            bucket_date = str(event.get('bucket_date', ''))
            if bucket_date not in buckets:
                continue
            event_type = str(event.get('event_type', '')).lower()
            count = int(event.get('count', 1) or 1)
            if event_type == 'view':
                buckets[bucket_date]['views'] += count
            elif event_type == 'click':
                buckets[bucket_date]['clicks'] += count
                link_id = int(event.get('link_id') or 0)
                if link_id in link_buckets:
                    link_buckets[link_id][bucket_date] += count

        series = [
            {
                'date': bucket_date,
                'views': values['views'],
                'clicks': values['clicks'],
                'ctr': 0.0 if values['views'] == 0 else round(values['clicks'] / max(1, values['views']), 4),
            }
            for bucket_date, values in buckets.items()
        ]

        per_link = []
        for link_id, bucket_map in link_buckets.items():
            link_series = [{'date': d, 'clicks': c} for d, c in bucket_map.items()]
            per_link.append({
                'link_id': link_id,
                'label': link_meta[link_id]['label'],
                'total_clicks': sum(item['clicks'] for item in link_series),
                'series': link_series,
            })
        per_link.sort(key=lambda item: _coerce_int(item.get('total_clicks', 0)), reverse=True)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'timeseries': {
                'page_id': page_id,
                'days': window_days,
                'series': series,
                'per_link': per_link,
                'totals': {
                    'views': sum(point['views'] for point in series),
                    'clicks': sum(point['clicks'] for point in series),
                },
            },
        }

    return router
