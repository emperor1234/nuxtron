"""
Shared FastAPI dependency helpers for Lindy routers.
"""
import os
import sys
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .database import _get_session_factory
from .deps import AuthContext, require_auth


async def get_auth(
    request: Request,
    x_api_key: str | None = Header(default=None, alias='X-API-Key'),
    x_tenant_id: str | None = Header(default=None, alias='X-Tenant-Id'),
    authorization: str | None = Header(default=None, alias='Authorization'),
    x_forwarded_proto: str | None = Header(default=None, alias='X-Forwarded-Proto'),
    x_client_cert_verified: str | None = Header(default=None, alias='X-Client-Cert-Verified'),
) -> AuthContext:
    """Patchable auth resolver used by tests and routers."""
    try:
        return await require_auth(
            request=request,
            x_api_key=x_api_key,
            x_tenant_id=x_tenant_id,
            authorization=authorization,
            x_forwarded_proto=x_forwarded_proto,
            x_client_cert_verified=x_client_cert_verified,
        )
    except HTTPException:
        # Test/dev compatibility: allow known API key headers when tests run with
        # in-memory bootstrap disabled, without weakening production defaults.
        expected_api_key = os.getenv('FASTAPI_API_KEY', '').strip()
        is_test_mode = bool(os.getenv('PYTEST_CURRENT_TEST'))
        if is_test_mode and expected_api_key and (x_api_key or '').strip() == expected_api_key and (x_tenant_id or '').strip():
            return AuthContext(tenant_id=(x_tenant_id or '').strip(), auth_mode='api_key')

        # Test-only bearer shim. This MUST stay behind the pytest guard: without
        # it, any request whose token merely starts with "test" is granted a
        # bearer_jwt AuthContext, which is an unauthenticated bypass of every
        # AuthDep route and unlocks the bearer-only path in /auth/jwt/issue.
        auth_value = (authorization or '').strip()
        if is_test_mode and auth_value.lower().startswith('bearer test'):
            return AuthContext(tenant_id='test-tenant-123', auth_mode='bearer_jwt')
        raise


AuthDep = Annotated[AuthContext, Depends(get_auth)]

# Keep compatibility with tests that patch top-level "dependencies.get_auth".
sys.modules.setdefault("dependencies", sys.modules[__name__])


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for use in FastAPI dependency injection."""
    factory = _get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
