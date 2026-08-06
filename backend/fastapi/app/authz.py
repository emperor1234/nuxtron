"""Role-based authorization built on top of ``deps.require_auth``.

Tenant scoping (``AuthContext.tenant_id``) answers "which tenant is this
request for". This module answers the separate question "is this caller
allowed to do this within that tenant" — a distinction the codebase did not
previously make: every authenticated caller in a tenant had equal access to
every route in that tenant's namespace.

Roles live ONLY on the verified JWT ``roles`` claim (``AuthContext.roles``,
populated in ``deps.py``). Never read a role off a request body or query
param — a client can put anything there. API-key auth carries no user
identity, so it never carries roles either; API-key callers can only pass
``require_role`` checks if ``ALLOW_API_KEY_ROLE_BYPASS`` is explicitly enabled
for a given call, which no current caller does.

Roles are intentionally a flat set of strings rather than a hierarchy class,
matching how they are already issued in routers/auth.py (``roles: ['user']``,
``roles: ['saml_user']``) and requested in JwtIssueRequest. ``super_admin``
and ``admin`` are treated as satisfying any narrower role check via
``_PRIVILEGED_ROLES`` below, since they are the only two roles currently
issued with elevated intent anywhere in the codebase (see
``routers/auth.py``'s self-issue guard and ``routers/ira.py``'s RBAC map).
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from .deps import AuthContext

# Roles that implicitly satisfy ANY require_role(...) check, highest first.
# Keep this list short and explicit — do not add a role here unless it is
# meant to be a universal escalation, not a domain-specific one.
_PRIVILEGED_ROLES: tuple[str, ...] = ('super_admin', 'admin')


def has_any_role(auth: AuthContext, *roles: str) -> bool:
    """True if ``auth`` carries any of ``roles``, or a role in _PRIVILEGED_ROLES."""
    if not roles:
        return True
    caller_roles = set(auth.roles)
    if caller_roles.intersection(_PRIVILEGED_ROLES):
        return True
    return bool(caller_roles.intersection(roles))


def require_role(*roles: str) -> Callable[[AuthContext], AuthContext]:
    """FastAPI dependency factory: 403s unless the caller holds one of ``roles``.

    Usage (alongside, not instead of, ``require_auth``)::

        from ..deps import require_auth
        from ..authz import require_role

        AuthDep = Annotated[AuthContext, Depends(require_auth)]

        @router.post('/billing/refund')
        def refund(auth: AuthDep, _role: Annotated[AuthContext, Depends(require_role('admin'))]) -> ...:
            ...

    ``require_role`` re-resolves ``AuthContext`` via ``require_auth`` itself
    (FastAPI dependency caching means this does not re-run the auth check), so
    it can be composed as its own dependency rather than needing every route
    to manually call a helper function.
    """
    if not roles:
        raise ValueError('require_role() needs at least one role name.')

    from fastapi import Depends

    from .deps import require_auth

    def _resolver(auth: AuthContext = Depends(require_auth)) -> AuthContext:
        if not has_any_role(auth, *roles):
            raise HTTPException(
                status_code=403,
                detail=f'This action requires one of the following roles: {", ".join(roles)}.',
            )
        return auth

    return _resolver
