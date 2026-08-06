import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]


class CommerceProductRequest(BaseModel):
    name: str = Field(min_length=2, max_length=240)
    description: str = Field(default='', max_length=1000)
    price_usd: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default='USD', max_length=8)
    category: str = Field(default='general', max_length=80)
    inventory: int = Field(default=0, ge=0)
    digital: bool = Field(default=False)


class CommerceOrderRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=9999)
    buyer_email: str = Field(min_length=5, max_length=320)
    note: str = Field(default='', max_length=500)


@dataclass
class CommerceContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    commerce_products_memory: list[dict[str, Any]]
    commerce_orders_memory: list[dict[str, Any]]
    product_not_found: str


def register_commerce_routes(*, router: APIRouter, context: CommerceContext) -> None:
    commerce_product_counter: list[int] = [0]
    commerce_order_counter: list[int] = [0]

    def _commerce_order_status(quantity: int, inventory: int) -> str:
        if inventory == 0:
            return 'backorder'
        return 'confirmed' if quantity <= inventory else 'partial'

    @router.get('/money-printers/commerce-pro/catalog')
    def commerce_catalog(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:commerce:catalog', 240, 60)
        with context.lock:
            products = [p.copy() for p in context.commerce_products_memory if p.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(products), 'products': products}

    @router.post('/money-printers/commerce-pro/products')
    def commerce_create_product(payload: CommerceProductRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:commerce:products', 120, 60)
        with context.lock:
            commerce_product_counter[0] += 1
            product: dict[str, Any] = {
                'id': commerce_product_counter[0],
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'price_usd': round(payload.price_usd, 2),
                'currency': payload.currency.upper(),
                'category': payload.category,
                'inventory': payload.inventory,
                'digital': payload.digital,
                'status': 'active',
                'created_at': datetime.now(UTC).isoformat(),
            }
            context.commerce_products_memory.append(product)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'product': product.copy()}

    @router.get('/money-printers/commerce-pro/storefront')
    def commerce_storefront(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:commerce:storefront', 240, 60)
        with context.lock:
            products = [
                p.copy()
                for p in context.commerce_products_memory
                if p.get('tenant_id') == auth.tenant_id and p.get('status') == 'active'
            ]
            orders = [o.copy() for o in context.commerce_orders_memory if o.get('tenant_id') == auth.tenant_id]
        revenue = round(sum(float(o.get('total_usd', 0)) for o in orders if o.get('order_status') == 'confirmed'), 2)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'storefront': {
                'active_products': len(products),
                'total_orders': len(orders),
                'confirmed_revenue_usd': revenue,
                'currency': 'USD',
            },
        }

    @router.post('/money-printers/commerce-pro/orders', responses={404: {'description': 'Product not found'}})
    def commerce_create_order(payload: CommerceOrderRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:commerce:orders', 120, 60)
        with context.lock:
            product = next(
                (
                    p
                    for p in context.commerce_products_memory
                    if p.get('id') == payload.product_id and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if product is None:
                raise HTTPException(status_code=404, detail=context.product_not_found)
            commerce_order_counter[0] += 1
            total_usd = round(float(product.get('price_usd', 0)) * payload.quantity, 2)
            order: dict[str, Any] = {
                'id': commerce_order_counter[0],
                'tenant_id': auth.tenant_id,
                'product_id': payload.product_id,
                'product_name': product.get('name', ''),
                'quantity': payload.quantity,
                'total_usd': total_usd,
                'currency': product.get('currency', 'USD'),
                'buyer_email': payload.buyer_email,
                'note': payload.note,
                'order_status': _commerce_order_status(payload.quantity, int(product.get('inventory', 0))),
                'created_at': datetime.now(UTC).isoformat(),
            }
            context.commerce_orders_memory.append(order)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'order': order.copy()}

    @router.get('/money-printers/commerce-pro/orders')
    def commerce_list_orders(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:commerce:orders:list', 240, 60)
        with context.lock:
            orders = [o.copy() for o in context.commerce_orders_memory if o.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(orders), 'orders': orders}

    @router.get('/money-printers/commerce-pro/overview')
    def commerce_overview(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        context.enforce_rate_limit(f'{auth.tenant_id}:commerce:overview', 240, 60)
        with context.lock:
            products = [p.copy() for p in context.commerce_products_memory if p.get('tenant_id') == auth.tenant_id]
            orders = [o.copy() for o in context.commerce_orders_memory if o.get('tenant_id') == auth.tenant_id]
        confirmed = [o for o in orders if o.get('order_status') == 'confirmed']
        revenue = round(sum(float(o.get('total_usd', 0)) for o in confirmed), 2)
        backorders = sum(1 for o in orders if o.get('order_status') == 'backorder')
        digital_products = sum(1 for p in products if p.get('digital'))
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'commerce': {
                'total_products': len(products),
                'digital_products': digital_products,
                'total_orders': len(orders),
                'confirmed_orders': len(confirmed),
                'backorders': backorders,
                'confirmed_revenue_usd': revenue,
            },
        }
