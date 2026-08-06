import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..authz import require_role
from ..deps import AuthContext, require_auth

# Type alias for dependency injection
AuthDep = Annotated[AuthContext, Depends(require_auth)]
AdminDep = Annotated[AuthContext, Depends(require_role('admin'))]
JsonObject = dict[str, object]


class TenantProfileCreateRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=180)
    plan: Literal['starter', 'growth', 'pro', 'enterprise'] = 'starter'
    status: Literal['active', 'suspended'] = 'active'
    settings: dict[str, object] = Field(default_factory=dict)


class TenantProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=180)
    plan: Literal['starter', 'growth', 'pro', 'enterprise'] | None = None
    status: Literal['active', 'suspended'] | None = None
    settings: dict[str, object] | None = None


def create_tenant_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    get_db_ready: Callable[[], bool],
    db_dsn: Callable[[], str],
    encrypt_value: Callable[[str], str],
    decrypt_value: Callable[[str], str | None],
    tenant_profiles_memory: list[dict[str, object]],
) -> APIRouter:
    router = APIRouter()

    @router.post('/tenants', responses={500: {'description': 'Failed to create tenant profile'}})
    def create_tenant_profile(payload: TenantProfileCreateRequest, auth: AuthDep) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:tenants:create', 30, 60)
        display_name_cipher = encrypt_value(payload.display_name)
        display_name_preview = payload.display_name[:64]

        if get_db_ready():
            with psycopg.connect(db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO tenant_profiles (tenant_id, display_name_cipher, display_name_preview, plan, status, settings_json)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (tenant_id)
                        DO UPDATE SET
                            display_name_cipher = EXCLUDED.display_name_cipher,
                            display_name_preview = EXCLUDED.display_name_preview,
                            plan = EXCLUDED.plan,
                            status = EXCLUDED.status,
                            settings_json = EXCLUDED.settings_json,
                            updated_at = NOW()
                        RETURNING tenant_id, display_name_cipher, display_name_preview, plan, status, settings_json, created_at, updated_at
                        """,
                        (
                            auth.tenant_id,
                            display_name_cipher,
                            display_name_preview,
                            payload.plan,
                            payload.status,
                            json.dumps(payload.settings),
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()

            if not row:
                raise HTTPException(status_code=500, detail='Failed to create tenant profile.')

            return {
                'status': 'ok',
                'tenant': {
                    'tenant_id': row[0],
                    'display_name': decrypt_value(row[1] or '') or row[2],
                    'plan': row[3],
                    'status': row[4],
                    'settings': row[5],
                    'created_at': row[6].isoformat(),
                    'updated_at': row[7].isoformat(),
                    'persistence': 'postgres',
                    'encryption': 'application-level',
                },
            }

        tenant_profiles_memory[:] = [e for e in tenant_profiles_memory if e.get('tenant_id') != auth.tenant_id]
        item: dict[str, object] = {
            'id': len(tenant_profiles_memory) + 1,
            'tenant_id': auth.tenant_id,
            'display_name': payload.display_name,
            'display_name_cipher': display_name_cipher,
            'plan': payload.plan,
            'status': payload.status,
            'settings': payload.settings,
            'created_at': datetime.now(UTC).isoformat(),
            'updated_at': datetime.now(UTC).isoformat(),
            'persistence': 'memory-fallback',
            'encryption': 'application-level',
        }
        tenant_profiles_memory.append(item)
        return {'status': 'ok', 'tenant': item}

    @router.get('/tenants')
    def list_tenant_profiles(auth: AuthDep) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        if get_db_ready():
            with psycopg.connect(db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT tenant_id, display_name_cipher, display_name_preview, plan, status, settings_json, created_at, updated_at
                        FROM tenant_profiles
                        WHERE tenant_id = %s
                        ORDER BY created_at DESC
                        """,
                        (auth.tenant_id,),
                    )
                    rows = cur.fetchall()

            db_items: list[dict[str, object]] = [
                {
                    'tenant_id': row[0],
                    'display_name': decrypt_value(row[1] or '') or row[2],
                    'plan': row[3],
                    'status': row[4],
                    'settings': row[5],
                    'created_at': row[6].isoformat(),
                    'updated_at': row[7].isoformat(),
                    'persistence': 'postgres',
                    'encryption': 'application-level',
                }
                for row in rows
            ]
            return {'status': 'ok', 'count': len(db_items), 'items': db_items}

        memory_items: list[dict[str, object]] = [e for e in tenant_profiles_memory if e.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'count': len(memory_items), 'items': memory_items}

    @router.patch('/tenants/{tenant_id}', responses={403: {'description': 'Cross-tenant update is not allowed, or caller lacks the admin role'}, 404: {'description': 'Tenant profile not found'}, 500: {'description': 'Failed to update tenant profile'}})
    def update_tenant_profile(  # pyright: ignore[reportUnusedFunction]
        tenant_id: str, payload: TenantProfileUpdateRequest, auth: AuthDep, _role: AdminDep
    ) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:tenants:update', 60, 60)
        if tenant_id != auth.tenant_id:
            raise HTTPException(status_code=403, detail='Cross-tenant update is not allowed.')

        if get_db_ready():
            with psycopg.connect(db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT display_name_cipher, display_name_preview, plan, status, settings_json
                        FROM tenant_profiles WHERE tenant_id = %s
                        """,
                        (tenant_id,),
                    )
                    existing = cur.fetchone()

                    if not existing:
                        raise HTTPException(status_code=404, detail='Tenant profile not found.')

                    display_name_cipher = existing[0]
                    display_name_preview = existing[1]
                    if payload.display_name is not None:
                        display_name_cipher = encrypt_value(payload.display_name)
                        display_name_preview = payload.display_name[:64]

                    plan = payload.plan or existing[2]
                    status = payload.status or existing[3]
                    settings = payload.settings if payload.settings is not None else existing[4]

                    cur.execute(
                        """
                        UPDATE tenant_profiles
                        SET display_name_cipher = %s,
                            display_name_preview = %s,
                            plan = %s,
                            status = %s,
                            settings_json = %s::jsonb,
                            updated_at = NOW()
                        WHERE tenant_id = %s
                        RETURNING tenant_id, display_name_cipher, display_name_preview, plan, status, settings_json, created_at, updated_at
                        """,
                        (
                            display_name_cipher,
                            display_name_preview,
                            plan,
                            status,
                            json.dumps(settings),
                            tenant_id,
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()

            if not row:
                raise HTTPException(status_code=500, detail='Failed to update tenant profile.')

            return {
                'status': 'ok',
                'tenant': {
                    'tenant_id': row[0],
                    'display_name': decrypt_value(row[1] or '') or row[2],
                    'plan': row[3],
                    'status': row[4],
                    'settings': row[5],
                    'created_at': row[6].isoformat(),
                    'updated_at': row[7].isoformat(),
                    'persistence': 'postgres',
                    'encryption': 'application-level',
                },
            }

        entry = next((e for e in tenant_profiles_memory if e.get('tenant_id') == tenant_id), None)
        if not entry:
            raise HTTPException(status_code=404, detail='Tenant profile not found.')

        if payload.display_name is not None:
            entry['display_name'] = payload.display_name
            entry['display_name_cipher'] = encrypt_value(payload.display_name)
        if payload.plan is not None:
            entry['plan'] = payload.plan
        if payload.status is not None:
            entry['status'] = payload.status
        if payload.settings is not None:
            entry['settings'] = payload.settings
        entry['updated_at'] = datetime.now(UTC).isoformat()
        return {'status': 'ok', 'tenant': entry}

    @router.delete(
        '/tenants/{tenant_id}',
        responses={403: {'description': 'Cross-tenant delete is not allowed, or caller lacks the admin role'}},
    )
    def delete_tenant_profile(tenant_id: str, auth: AuthDep, _role: AdminDep) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:tenants:delete', 20, 60)
        if tenant_id != auth.tenant_id:
            raise HTTPException(status_code=403, detail='Cross-tenant delete is not allowed.')

        if get_db_ready():
            with psycopg.connect(db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM tenant_profiles WHERE tenant_id = %s', (tenant_id,))
                    deleted = cur.rowcount > 0
                conn.commit()
            return {'status': 'ok', 'tenant_id': tenant_id, 'deleted': deleted, 'persistence': 'postgres'}

        before = len(tenant_profiles_memory)
        tenant_profiles_memory[:] = [e for e in tenant_profiles_memory if e.get('tenant_id') != tenant_id]
        return {
            'status': 'ok',
            'tenant_id': tenant_id,
            'deleted': len(tenant_profiles_memory) < before,
            'persistence': 'memory-fallback',
        }

    return router
