# pyright: reportUnusedFunction=false

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
JsonObject = dict[str, object]
ACCOUNTING_PROVIDER_PATTERN = r'^(quickbooks|xero|hmrc)$'


class AccountingIntegrationConnectRequest(BaseModel):
    provider: str = Field(pattern=ACCOUNTING_PROVIDER_PATTERN)
    client_id: str = Field(min_length=3, max_length=200)
    account_name: str = Field(min_length=2, max_length=120)


class AccountingExportRequest(BaseModel):
    provider: str = Field(pattern=ACCOUNTING_PROVIDER_PATTERN)
    export_type: str = Field(pattern=r'^(vat_return|pnl|ledger|invoice_batch)$')
    period_label: str = Field(min_length=2, max_length=32)


class ModuleSettingUpdateRequest(BaseModel):
    key: str = Field(min_length=2, max_length=80)
    enabled: bool
    value: str = Field(default='', max_length=500)


class AccountingIntegrationDisconnectRequest(BaseModel):
    provider: str = Field(pattern=ACCOUNTING_PROVIDER_PATTERN)


def _guard_request(
    request: Request,
    auth: AuthContext,
    x_super_admin_key: str | None,
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    scope: str,
    limit: int,
    window_seconds: int,
) -> None:
    enforce_rate_limit(f'{auth.tenant_id}:{scope}', limit, window_seconds)
    require_super_admin_access(request, x_super_admin_key)


def _register_list_integrations_route(
    router: APIRouter,
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    accounting_integrations_memory: list[dict[str, Any]],
) -> None:
    @router.get('/ops/platform/super-admin/accounting/integrations')
    def list_integrations(
        request: Request,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:accounting:integrations',
            limit=120,
            window_seconds=60,
        )
        rows = [item for item in accounting_integrations_memory if str(item.get('tenant_id', '')) == auth.tenant_id]
        rows.sort(key=lambda item: str(item.get('updated_at', '') or ''), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(rows),
            'integrations': rows,
            'generated_at': datetime.now(UTC).isoformat(),
        }

def _register_connect_integration_route(
    router: APIRouter,
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    accounting_integrations_memory: list[dict[str, Any]],
    audit: Callable[[str, str, JsonObject], None],
) -> None:
    @router.post('/ops/platform/super-admin/accounting/integrations/connect')
    def connect_integration(
        request: Request,
        payload: AccountingIntegrationConnectRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:accounting:connect',
            limit=40,
            window_seconds=60,
        )
        now = datetime.now(UTC).isoformat()
        provider = payload.provider.strip().lower()
        for item in accounting_integrations_memory:
            if item.get('tenant_id') == auth.tenant_id and item.get('provider') == provider:
                item['status'] = 'connected'
                item['client_id_masked'] = payload.client_id[:3] + '***'
                item['account_name'] = payload.account_name
                item['updated_at'] = now
                audit(auth.tenant_id, 'accounting.integration.connected', {'provider': provider, 'mode': 'update'})
                return {'status': 'ok', 'integration': item}

        record: dict[str, Any] = {
            'id': len(accounting_integrations_memory) + 1,
            'tenant_id': auth.tenant_id,
            'provider': provider,
            'status': 'connected',
            'client_id_masked': payload.client_id[:3] + '***',
            'account_name': payload.account_name,
            'created_at': now,
            'updated_at': now,
        }
        accounting_integrations_memory.append(record)
        audit(auth.tenant_id, 'accounting.integration.connected', {'provider': provider, 'mode': 'create'})
        return {'status': 'ok', 'integration': record}

def _register_disconnect_integration_route(
    router: APIRouter,
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    accounting_integrations_memory: list[dict[str, Any]],
    audit: Callable[[str, str, JsonObject], None],
) -> None:
    @router.post(
        '/ops/platform/super-admin/accounting/integrations/disconnect',
        responses={404: {'description': 'Integration not found for tenant/provider.'}},
    )
    def disconnect_integration(
        request: Request,
        payload: AccountingIntegrationDisconnectRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:accounting:disconnect',
            limit=40,
            window_seconds=60,
        )
        provider = payload.provider.strip().lower()
        now = datetime.now(UTC).isoformat()
        for item in accounting_integrations_memory:
            if item.get('tenant_id') == auth.tenant_id and item.get('provider') == provider:
                item['status'] = 'disconnected'
                item['updated_at'] = now
                audit(auth.tenant_id, 'accounting.integration.disconnected', {'provider': provider})
                return {'status': 'ok', 'integration': item}
        raise HTTPException(status_code=404, detail='Integration not found for tenant/provider.')

def _register_delete_integration_route(
    router: APIRouter,
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    accounting_integrations_memory: list[dict[str, Any]],
    audit: Callable[[str, str, JsonObject], None],
) -> None:
    @router.delete(
        '/ops/platform/super-admin/accounting/integrations/{provider}',
        responses={
            404: {'description': 'Integration not found for tenant/provider.'},
            422: {'description': 'Unsupported provider for delete operation.'},
        },
    )
    def delete_integration(
        provider: str,
        request: Request,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:accounting:delete',
            limit=25,
            window_seconds=60,
        )
        normalized_provider = provider.strip().lower()
        if normalized_provider not in {'quickbooks', 'xero', 'hmrc'}:
            raise HTTPException(status_code=422, detail='Unsupported provider for delete operation.')
        for index, item in enumerate(accounting_integrations_memory):
            if item.get('tenant_id') == auth.tenant_id and item.get('provider') == normalized_provider:
                removed = accounting_integrations_memory.pop(index)
                audit(auth.tenant_id, 'accounting.integration.deleted', {'provider': normalized_provider})
                return {'status': 'ok', 'integration': removed}
        raise HTTPException(status_code=404, detail='Integration not found for tenant/provider.')


def _register_export_routes(
    router: APIRouter,
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    accounting_exports_memory: list[dict[str, Any]],
    audit: Callable[[str, str, JsonObject], None],
) -> None:
    @router.post('/ops/platform/super-admin/accounting/exports')
    def create_export(
        request: Request,
        payload: AccountingExportRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:accounting:exports',
            limit=30,
            window_seconds=60,
        )
        now = datetime.now(UTC).isoformat()
        provider = payload.provider.strip().lower()
        export_record: dict[str, Any] = {
            'id': len(accounting_exports_memory) + 1,
            'tenant_id': auth.tenant_id,
            'provider': provider,
            'export_type': payload.export_type,
            'period_label': payload.period_label,
            'status': 'submitted',
            'submitted_at': now,
            'completed_at': now,
            'detail': 'Submitted to provider gateway',
        }
        accounting_exports_memory.append(export_record)
        audit(
            auth.tenant_id,
            'accounting.export.submitted',
            {'provider': provider, 'export_type': payload.export_type, 'period_label': payload.period_label},
        )
        return {'status': 'ok', 'export': export_record}

    @router.get('/ops/platform/super-admin/accounting/exports')
    def list_exports(
        request: Request,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:accounting:exports:list',
            limit=120,
            window_seconds=60,
        )
        rows = [item for item in accounting_exports_memory if str(item.get('tenant_id', '')) == auth.tenant_id]
        rows.sort(key=lambda item: str(item.get('submitted_at', '') or ''), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(rows),
            'exports': rows,
            'generated_at': datetime.now(UTC).isoformat(),
        }

    @router.post(
        '/ops/platform/super-admin/accounting/exports/{export_id}/retry',
        responses={404: {'description': 'Export job not found for tenant.'}},
    )
    def retry_export(
        export_id: int,
        request: Request,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:accounting:exports:retry',
            limit=40,
            window_seconds=60,
        )
        now = datetime.now(UTC).isoformat()
        for item in accounting_exports_memory:
            if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == export_id:
                item['status'] = 'resubmitted'
                item['submitted_at'] = now
                item['completed_at'] = now
                item['detail'] = 'Export resubmitted to provider gateway'
                audit(auth.tenant_id, 'accounting.export.retried', {'export_id': export_id})
                return {'status': 'ok', 'export': item}
        raise HTTPException(status_code=404, detail='Export job not found for tenant.')

    @router.post(
        '/ops/platform/super-admin/accounting/exports/{export_id}/cancel',
        responses={404: {'description': 'Export job not found for tenant.'}},
    )
    def cancel_export(
        export_id: int,
        request: Request,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:accounting:exports:cancel',
            limit=40,
            window_seconds=60,
        )
        now = datetime.now(UTC).isoformat()
        for item in accounting_exports_memory:
            if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == export_id:
                item['status'] = 'cancelled'
                item['completed_at'] = now
                item['detail'] = 'Export job cancelled by super admin'
                audit(auth.tenant_id, 'accounting.export.cancelled', {'export_id': export_id})
                return {'status': 'ok', 'export': item}
        raise HTTPException(status_code=404, detail='Export job not found for tenant.')


def _register_module_setting_routes(
    router: APIRouter,
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    module_settings_memory: list[dict[str, Any]],
    audit: Callable[[str, str, JsonObject], None],
) -> None:
    @router.get('/ops/platform/super-admin/module-settings')
    def list_module_settings(
        request: Request,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:modules:list',
            limit=120,
            window_seconds=60,
        )
        rows = [item for item in module_settings_memory if str(item.get('tenant_id', '')) == auth.tenant_id]
        rows.sort(key=lambda item: str(item.get('updated_at', '') or ''), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(rows),
            'settings': rows,
            'generated_at': datetime.now(UTC).isoformat(),
        }

    @router.post('/ops/platform/super-admin/module-settings')
    def upsert_module_setting(
        request: Request,
        payload: ModuleSettingUpdateRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:modules:update',
            limit=60,
            window_seconds=60,
        )
        now = datetime.now(UTC).isoformat()
        key = payload.key.strip().lower()
        for item in module_settings_memory:
            if item.get('tenant_id') == auth.tenant_id and item.get('key') == key:
                item['enabled'] = payload.enabled
                item['value'] = payload.value
                item['updated_at'] = now
                audit(auth.tenant_id, 'module.setting.updated', {'key': key, 'enabled': payload.enabled})
                return {'status': 'ok', 'setting': item}

        record: dict[str, Any] = {
            'id': len(module_settings_memory) + 1,
            'tenant_id': auth.tenant_id,
            'key': key,
            'enabled': payload.enabled,
            'value': payload.value,
            'created_at': now,
            'updated_at': now,
        }
        module_settings_memory.append(record)
        audit(auth.tenant_id, 'module.setting.created', {'key': key, 'enabled': payload.enabled})
        return {'status': 'ok', 'setting': record}


def _register_audit_routes(
    router: APIRouter,
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    audit_log_memory: list[dict[str, Any]],
) -> None:
    @router.get('/ops/platform/super-admin/audit-log')
    def list_super_admin_audit_log(
        request: Request,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=200)] = 20,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        _guard_request(
            request,
            auth,
            x_super_admin_key,
            enforce_rate_limit=enforce_rate_limit,
            require_super_admin_access=require_super_admin_access,
            scope='super-admin:audit-log:list',
            limit=120,
            window_seconds=60,
        )
        rows = [
            item
            for item in audit_log_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id
            and str(item.get('source', '')).lower() == 'super-admin-finance-router'
        ]
        rows.sort(key=lambda item: str(item.get('recorded_at', '') or ''), reverse=True)
        bounded_rows = rows[:limit]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(bounded_rows),
            'items': bounded_rows,
            'generated_at': datetime.now(UTC).isoformat(),
        }


def create_super_admin_finance_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    require_super_admin_access: Callable[[Request, str | None], None],
    accounting_integrations_memory: list[dict[str, Any]],
    accounting_exports_memory: list[dict[str, Any]],
    module_settings_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    def _audit(tenant_id: str, action: str, detail: JsonObject) -> None:
        audit_log_memory.append(
            {
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'detail': detail,
                'recorded_at': datetime.now(UTC).isoformat(),
                'source': 'super-admin-finance-router',
            }
        )

    _register_list_integrations_route(
        router,
        enforce_rate_limit=enforce_rate_limit,
        require_super_admin_access=require_super_admin_access,
        accounting_integrations_memory=accounting_integrations_memory,
    )
    _register_connect_integration_route(
        router,
        enforce_rate_limit=enforce_rate_limit,
        require_super_admin_access=require_super_admin_access,
        accounting_integrations_memory=accounting_integrations_memory,
        audit=_audit,
    )
    _register_disconnect_integration_route(
        router,
        enforce_rate_limit=enforce_rate_limit,
        require_super_admin_access=require_super_admin_access,
        accounting_integrations_memory=accounting_integrations_memory,
        audit=_audit,
    )
    _register_delete_integration_route(
        router,
        enforce_rate_limit=enforce_rate_limit,
        require_super_admin_access=require_super_admin_access,
        accounting_integrations_memory=accounting_integrations_memory,
        audit=_audit,
    )
    _register_export_routes(
        router,
        enforce_rate_limit=enforce_rate_limit,
        require_super_admin_access=require_super_admin_access,
        accounting_exports_memory=accounting_exports_memory,
        audit=_audit,
    )
    _register_module_setting_routes(
        router,
        enforce_rate_limit=enforce_rate_limit,
        require_super_admin_access=require_super_admin_access,
        module_settings_memory=module_settings_memory,
        audit=_audit,
    )
    _register_audit_routes(
        router,
        enforce_rate_limit=enforce_rate_limit,
        require_super_admin_access=require_super_admin_access,
        audit_log_memory=audit_log_memory,
    )
    return router
