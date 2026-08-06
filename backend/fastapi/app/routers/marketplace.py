# NEW MODULE — Marketplace (Part 4 Section 20, API Platform)
# Implements plugin/theme registry, install, publish per spec.
# Memory-backed, same router factory pattern.

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

# Type alias for dependency injection
AuthDep = Annotated[AuthContext, Depends(require_auth)]

# Error message constants
MARKETPLACE_ITEM_NOT_FOUND = 'Marketplace item not found.'


# ── Seed catalogue: sample plugins and themes ─────────────────────────────────

_SEED_PLUGINS: list[dict[str, Any]] = [
    {
        'id': 'plugin-001', 'type': 'plugin', 'name': 'CRM Enrichment Pro',
        'description': 'Auto-enrich CRM contacts from LinkedIn, Clearbit, and Apollo.',
        'category': 'crm', 'version': '2.1.0', 'author': 'Nuxtron Labs',
        'price': 0.0, 'currency': 'USD', 'installs': 4820,
        'rating': 4.7, 'compatible_plans': ['studio', 'enterprise', 'agency'],
    },
    {
        'id': 'plugin-002', 'type': 'plugin', 'name': 'Advanced SEO Auditor',
        'description': 'Deep technical SEO audit with Core Web Vitals and GEO scoring.',
        'category': 'seo', 'version': '3.0.1', 'author': 'Nuxtron Labs',
        'price': 0.0, 'currency': 'USD', 'installs': 9100,
        'rating': 4.9, 'compatible_plans': ['pro', 'studio', 'enterprise', 'agency'],
    },
    {
        'id': 'plugin-003', 'type': 'plugin', 'name': 'Influencer Fraud Detector',
        'description': 'ML-based fake follower and engagement pod detection.',
        'category': 'influencer', 'version': '1.5.3', 'author': 'Community',
        'price': 29.0, 'currency': 'USD', 'installs': 2310,
        'rating': 4.5, 'compatible_plans': ['studio', 'enterprise', 'agency'],
    },
]

_SEED_THEMES: list[dict[str, Any]] = [
    {
        'id': 'theme-001', 'type': 'theme', 'name': 'Midnight Pro',
        'description': 'Dark mode first dashboard theme with glassmorphism panels.',
        'category': 'dashboard', 'version': '1.2.0', 'author': 'Nuxtron Design',
        'price': 0.0, 'currency': 'USD', 'installs': 12400,
        'rating': 4.8, 'preview_url': 'https://themes.nuxtron.io/midnight-pro',
    },
    {
        'id': 'theme-002', 'type': 'theme', 'name': 'Clean Minimal',
        'description': 'Light, clean interface inspired by Linear and Notion.',
        'category': 'dashboard', 'version': '2.0.0', 'author': 'Nuxtron Design',
        'price': 0.0, 'currency': 'USD', 'installs': 19800,
        'rating': 4.9, 'preview_url': 'https://themes.nuxtron.io/clean-minimal',
    },
]


# ── Request models ────────────────────────────────────────────────────────────

class MarketplaceInstallRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=80)


class MarketplacePublishRequest(BaseModel):
    type: str = Field(pattern=r'^(plugin|theme)$')
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=10, max_length=2000)
    category: str = Field(min_length=1, max_length=80)
    version: str = Field(default='1.0.0', max_length=20)
    price: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default='USD', max_length=8)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_marketplace_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    marketplace_catalogue_memory: list[dict[str, Any]],
    marketplace_installs_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter()
    lock = threading.Lock()

    # Pre-seed on first factory call.
    with lock:
        if not marketplace_catalogue_memory:
            marketplace_catalogue_memory.extend(_SEED_PLUGINS + _SEED_THEMES)

    def _audit(tenant_id: str, action: str) -> None:
        with lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'marketplace-router',
            })

    @router.get('/marketplace/plugins')
    def list_plugins(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:marketplace:plugins', 120, 60)
        with lock:
            items = [i.copy() for i in marketplace_catalogue_memory if i.get('type') == 'plugin']
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'plugins': items}

    @router.get('/marketplace/themes')
    def list_themes(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:marketplace:themes', 120, 60)
        with lock:
            items = [i.copy() for i in marketplace_catalogue_memory if i.get('type') == 'theme']
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'themes': items}

    @router.post('/marketplace/install', responses={404: {'description': MARKETPLACE_ITEM_NOT_FOUND}})
    def install_item(payload: MarketplaceInstallRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:marketplace:install', 30, 60)
        with lock:
            item = next((i.copy() for i in marketplace_catalogue_memory if i.get('id') == payload.item_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail=MARKETPLACE_ITEM_NOT_FOUND)

        with lock:
            # Idempotent — return existing install if already installed.
            existing = next(
                (i.copy() for i in marketplace_installs_memory
                 if i.get('tenant_id') == auth.tenant_id and i.get('item_id') == payload.item_id),
                None,
            )
            if existing:
                return {'status': 'ok', 'tenant_id': auth.tenant_id, 'install': existing, 'already_installed': True}

            install: dict[str, Any] = {
                'id': len(marketplace_installs_memory) + 1,
                'tenant_id': auth.tenant_id,
                'item_id': payload.item_id,
                'item_type': item.get('type'),
                'item_name': item.get('name'),
                'version': item.get('version'),
                'installed_at': datetime.now(UTC).isoformat(),
            }
            marketplace_installs_memory.append(install)

        _audit(auth.tenant_id, f'marketplace_install_{payload.item_id}')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'install': install}

    @router.post('/marketplace/publish')
    def publish_item(payload: MarketplacePublishRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:marketplace:publish', 10, 60)
        with lock:
            item: dict[str, Any] = {
                'id': f'user-{auth.tenant_id}-{len(marketplace_catalogue_memory) + 1}',
                'type': payload.type,
                'name': payload.name,
                'description': payload.description,
                'category': payload.category,
                'version': payload.version,
                'author': auth.tenant_id,
                'price': payload.price,
                'currency': payload.currency,
                'installs': 0,
                'rating': 0.0,
                'status': 'pending_review',
                'published_at': datetime.now(UTC).isoformat(),
            }
            marketplace_catalogue_memory.append(item)

        _audit(auth.tenant_id, 'marketplace_item_published')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'item': item}

    return router
