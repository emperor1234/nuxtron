"""Shared authentication, authorization, and tenancy helpers.

Routers and extracted services should import from this module instead of
re-declaring FastAPI ``Depends`` wiring or inventing a second auth stack.
"""

from __future__ import annotations

from typing import Annotated, Any, TypeVar

from fastapi import Depends

from .authz import has_any_role, require_role
from .deps import AuthContext, require_auth
from .rate_limiter import RateLimitExceededError, enforce_rate_limit

AuthDep = Annotated[AuthContext, Depends(require_auth)]
AdminDep = Annotated[AuthContext, Depends(require_role('admin'))]
SuperAdminRoleDep = Annotated[AuthContext, Depends(require_role('super_admin'))]

T = TypeVar('T', bound=dict[str, Any])


def owned_by_tenant(item: object, tenant_id: str) -> bool:
    """True when *item* is a mapping owned by *tenant_id*."""
    if not isinstance(item, dict):
        return False
    return str(item.get('tenant_id') or '') == tenant_id


def filter_tenant(store: list[T], tenant_id: str) -> list[T]:
    """Return the subset of *store* that belongs to *tenant_id*."""
    return [item for item in store if owned_by_tenant(item, tenant_id)]


def rate_limit_or_raise(key: str, limit: int, window_seconds: int) -> None:
    """Apply the shared limiter and convert overflow into HTTP 429 at call sites."""
    enforce_rate_limit(key, limit, window_seconds)


__all__ = [
    'AdminDep',
    'AuthContext',
    'AuthDep',
    'RateLimitExceededError',
    'SuperAdminRoleDep',
    'filter_tenant',
    'has_any_role',
    'owned_by_tenant',
    'rate_limit_or_raise',
    'require_auth',
    'require_role',
]
