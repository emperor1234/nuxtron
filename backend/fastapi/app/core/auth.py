"""Auth helpers for intelligence routes.

SECURITY NOTE (2026-07): The previous implementation of ``get_current_user`` /
``get_current_org`` returned the raw ``Authorization: Bearer`` payload and the
raw ``X-Org-ID`` header verbatim — with *no* signature verification and a
``"test-user"`` / ``"test-org-001"`` fallback when the headers were absent. That
meant any caller (including unauthenticated ones) was treated as an
authenticated user of any tenant they named. It was a full authentication and
tenant-isolation bypass.

These helpers now delegate to the central :func:`app.deps.require_auth`
enforcer, which validates JWT signatures (or API keys when explicitly enabled)
and resolves a trustworthy ``tenant_id``. We keep the original signatures so the
25+ existing call sites in ``intelligence/routes.py`` are unaffected.

Returned identity contract
--------------------------
* ``get_current_org``   -> the authenticated tenant id (string)
* ``get_current_user``  -> a stable user identifier derived from the verified
  JWT ``sub``/``user_id`` claim, or the API-key fingerprint for key auth.
"""

from __future__ import annotations

import hashlib

from fastapi import Depends

from ..deps import AuthContext, require_auth


def _user_identifier(ctx: AuthContext, *, api_key_raw: str | None = None) -> str:
    """Derive a stable, non-sensitive user identifier from the auth context.

    For bearer auth we use the verified JWT ``sub`` claim propagated on
    ``AuthContext.subject``. For API-key auth there is no user claim, so we emit
    a short fingerprint of the key — never the key itself.
    """
    if ctx.subject:
        return ctx.subject
    if api_key_raw:
        return f'apikey:{hashlib.sha256(api_key_raw.encode("utf-8")).hexdigest()[:12]}'
    # Fallback: identify by tenant so audit trails are never empty, but never
    # impersonate a concrete user.
    return f'tenant:{ctx.tenant_id}'


async def get_current_org(ctx: AuthContext = Depends(require_auth)) -> str:
    """Return the authenticated tenant id.

    The tenant id is resolved by ``require_auth`` from the verified JWT claim
    (preferred) or the validated ``X-Tenant-Id`` header when API-key auth is
    explicitly enabled. Callers must not trust a client-supplied value directly.
    """
    return ctx.tenant_id


async def get_current_user(ctx: AuthContext = Depends(require_auth)) -> str:
    """Return a stable identifier for the authenticated principal."""
    return _user_identifier(ctx)
