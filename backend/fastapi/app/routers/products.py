# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedFunction=false
"""
Product Catalog / Library (HubSpot Commerce Hub §8.2)
NEW: Standalone product management — SKUs, pricing tiers, product variants,
categories, inventory, and deal/quote line-item linking.
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

PRODUCT_NOT_FOUND = 'Product not found.'
CATEGORY_NOT_FOUND = 'Product category not found.'
PRODUCT_STATUSES = {'active', 'draft', 'archived'}
BILLING_MODELS = {'one_time', 'recurring_monthly', 'recurring_annual', 'usage_based', 'tiered'}


class PriceTier(BaseModel):
    min_quantity: int = Field(ge=1)
    max_quantity: int | None = None
    unit_price: float = Field(ge=0)


class ProductVariant(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(default='', max_length=100)
    price_override: float | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str = Field(default='', max_length=5000)
    sku: str = Field(default='', max_length=100)
    category_id: int | None = None
    unit_price: float = Field(default=0.0, ge=0)
    currency: str = Field(default='USD', max_length=3)
    billing_model: str = Field(default='one_time', max_length=30)
    tax_pct: float = Field(default=0.0, ge=0, le=100)
    unit_of_measure: str = Field(default='unit', max_length=50)
    track_inventory: bool = False
    inventory_quantity: int = Field(default=0, ge=0)
    price_tiers: list[PriceTier] = Field(default_factory=list, max_length=10)
    variants: list[ProductVariant] = Field(default_factory=list, max_length=50)
    images: list[str] = Field(default_factory=list, max_length=10)
    tags: list[str] = Field(default_factory=list, max_length=20)
    status: str = Field(default='active', max_length=20)


class ProductCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=1000)
    parent_id: int | None = None


class ProductUpdateRequest(BaseModel):
    name: str = Field(default='', max_length=300)
    description: str = Field(default='', max_length=5000)
    unit_price: float | None = None
    status: str = Field(default='', max_length=20)
    inventory_quantity: int | None = None
    tags: list[str] | None = None
    images: list[str] | None = None


def create_products_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    products_memory: list[dict[str, Any]],
    product_categories_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """NEW: Product catalog router — HubSpot Commerce Hub §8.2."""
    router = APIRouter()
    _lock = threading.Lock()

    def _append_audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'products-router',
            })

    # ── Categories ────────────────────────────────────────────────────────────

    @router.post('/products/categories', summary='Create product category')
    def create_category(payload: ProductCategoryRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create a product category."""
        enforce_rate_limit(f'{auth.tenant_id}:products:create-category', 60, 60)
        with _lock:
            cat = {
                'id': len(product_categories_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'parent_id': payload.parent_id,
                'product_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
            }
            product_categories_memory.append(cat)
        _append_audit(auth.tenant_id, 'product_category_created', cat['id'])
        return {'status': 'ok', 'category': cat}

    @router.get('/products/categories', summary='List product categories')
    def list_categories(auth: AuthDep) -> dict[str, Any]:
        """NEW: List all product categories."""
        enforce_rate_limit(f'{auth.tenant_id}:products:list-categories', 120, 60)
        with _lock:
            cats = [c.copy() for c in product_categories_memory if c.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'categories': cats, 'total': len(cats)}

    # ── Products ──────────────────────────────────────────────────────────────

    @router.post('/products', summary='Create product', responses={409: {'description': 'SKU already exists for this tenant.'}})
    def create_product(payload: ProductCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Add a product to the catalog."""
        enforce_rate_limit(f'{auth.tenant_id}:products:create', 60, 60)
        billing_model = payload.billing_model.strip().lower()
        if billing_model not in BILLING_MODELS:
            billing_model = 'one_time'
        status = payload.status.strip().lower()
        if status not in PRODUCT_STATUSES:
            status = 'active'
        with _lock:
            # Check SKU uniqueness per tenant
            if payload.sku and any(
                p.get('sku') == payload.sku and p.get('tenant_id') == auth.tenant_id
                for p in products_memory
            ):
                raise HTTPException(status_code=409, detail='SKU already exists for this tenant.')
            product = {
                'id': len(products_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'sku': payload.sku or f'SKU-{len(products_memory) + 1:06d}',
                'category_id': payload.category_id,
                'unit_price': payload.unit_price,
                'currency': payload.currency.upper(),
                'billing_model': billing_model,
                'tax_pct': payload.tax_pct,
                'unit_of_measure': payload.unit_of_measure,
                'track_inventory': payload.track_inventory,
                'inventory_quantity': payload.inventory_quantity,
                'price_tiers': [t.model_dump() for t in payload.price_tiers],
                'variants': [v.model_dump() for v in payload.variants],
                'images': payload.images,
                'tags': payload.tags,
                'status': status,
                'deal_association_count': 0,
                'quote_association_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            products_memory.append(product)
            # Update category count
            if payload.category_id:
                for cat in product_categories_memory:
                    if cat.get('id') == payload.category_id and cat.get('tenant_id') == auth.tenant_id:
                        cat['product_count'] = cat.get('product_count', 0) + 1
                        break
        _append_audit(auth.tenant_id, 'product_created', product['id'])
        return {'status': 'ok', 'product': product}

    @router.get('/products', summary='List products')
    def list_products(
        auth: AuthDep,
        category_id: Annotated[int | None, Query(ge=1)] = None,
        status: Annotated[str | None, Query(max_length=20)] = None,
        billing_model: Annotated[str | None, Query(max_length=30)] = None,
        search: Annotated[str | None, Query(max_length=200)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List and search the product catalog."""
        enforce_rate_limit(f'{auth.tenant_id}:products:list', 120, 60)
        with _lock:
            items = [p.copy() for p in products_memory if p.get('tenant_id') == auth.tenant_id]
        if category_id is not None:
            items = [p for p in items if p.get('category_id') == category_id]
        if status:
            items = [p for p in items if p.get('status') == status]
        if billing_model:
            items = [p for p in items if p.get('billing_model') == billing_model]
        if search:
            q = search.lower()
            items = [p for p in items
                     if q in str(p.get('name', '')).lower()
                     or q in str(p.get('description', '')).lower()
                     or q in str(p.get('sku', '')).lower()
                     or any(q in str(tag).lower() for tag in p.get('tags', []))]
        return {'status': 'ok', 'products': items[offset:offset + limit], 'total': len(items)}

    @router.get('/products/{product_id}', responses={404: {'description': PRODUCT_NOT_FOUND}})
    def get_product(product_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a single product from the catalog."""
        enforce_rate_limit(f'{auth.tenant_id}:products:get', 120, 60)
        with _lock:
            product = next((p.copy() for p in products_memory
                            if p.get('id') == product_id and p.get('tenant_id') == auth.tenant_id), None)
        if product is None:
            raise HTTPException(status_code=404, detail=PRODUCT_NOT_FOUND)
        return {'status': 'ok', 'product': product}

    @router.patch('/products/{product_id}', responses={404: {'description': PRODUCT_NOT_FOUND}})
    def update_product(product_id: int, payload: ProductUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Update a product."""
        enforce_rate_limit(f'{auth.tenant_id}:products:update', 60, 60)
        with _lock:
            product = next((p for p in products_memory
                            if p.get('id') == product_id and p.get('tenant_id') == auth.tenant_id), None)
            if product is None:
                raise HTTPException(status_code=404, detail=PRODUCT_NOT_FOUND)
            if payload.name:
                product['name'] = payload.name
            if payload.description:
                product['description'] = payload.description
            if payload.unit_price is not None:
                product['unit_price'] = payload.unit_price
            if payload.status and payload.status in PRODUCT_STATUSES:
                product['status'] = payload.status
            if payload.inventory_quantity is not None:
                product['inventory_quantity'] = payload.inventory_quantity
            if payload.tags is not None:
                product['tags'] = payload.tags
            if payload.images is not None:
                product['images'] = payload.images
            product['updated_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'product_updated', product_id)
        return {'status': 'ok', 'product': product.copy()}

    @router.delete('/products/{product_id}', responses={404: {'description': PRODUCT_NOT_FOUND}})
    def delete_product(product_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Delete a product from the catalog."""
        enforce_rate_limit(f'{auth.tenant_id}:products:delete', 30, 60)
        with _lock:
            idx = next((i for i, p in enumerate(products_memory)
                        if p.get('id') == product_id and p.get('tenant_id') == auth.tenant_id), None)
            if idx is None:
                raise HTTPException(status_code=404, detail=PRODUCT_NOT_FOUND)
            removed = products_memory.pop(idx)
        _append_audit(auth.tenant_id, 'product_deleted', product_id)
        return {'status': 'ok', 'deleted': True, 'product': removed}

    @router.get('/products/catalog/stats', summary='Catalog statistics')
    def catalog_stats(auth: AuthDep) -> dict[str, Any]:
        """NEW: Product catalog statistics — by category, billing model, status."""
        enforce_rate_limit(f'{auth.tenant_id}:products:stats', 60, 60)
        with _lock:
            products = [p for p in products_memory if p.get('tenant_id') == auth.tenant_id]
        active = sum(1 for p in products if p.get('status') == 'active')
        by_billing: dict[str, int] = {}
        by_status: dict[str, int] = {}
        total_value = sum(float(p.get('unit_price', 0)) for p in products if p.get('status') == 'active')
        for p in products:
            bm = str(p.get('billing_model', 'one_time'))
            st = str(p.get('status', 'active'))
            by_billing[bm] = by_billing.get(bm, 0) + 1
            by_status[st] = by_status.get(st, 0) + 1
        return {
            'status': 'ok',
            'total_products': len(products),
            'active_products': active,
            'total_catalog_value': round(total_value, 2),
            'by_billing_model': by_billing,
            'by_status': by_status,
        }

    return router
