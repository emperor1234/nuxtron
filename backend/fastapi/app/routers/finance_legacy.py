"""Legacy finance compatibility routes.

Extracted from legacy_main.py. Kept for selftest and older clients.
Routes depend on mutable app state which is injected via the factory.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

JsonObject = dict[str, object]
AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Request Models ────────────────────────────────────────────

class FinanceLegacyIntegrationConnectRequest(BaseModel):
    provider: Literal['quickbooks', 'xero', 'hmrc']
    client_id: str = Field(min_length=3, max_length=200)
    account_name: str = Field(min_length=2, max_length=120)


class FinanceLegacyExportRequest(BaseModel):
    provider: Literal['quickbooks', 'xero', 'hmrc']
    export_type: Literal['vat_return', 'pnl', 'ledger', 'invoice_batch', 'balance_sheet']
    period_label: str = Field(min_length=2, max_length=32)


class FinanceLegacyRotateSecretRequest(BaseModel):
    client_secret: str = Field(min_length=3, max_length=400)
    authorization_code: str = Field(default='', max_length=800)
    redirect_uri: str = Field(default='', max_length=500)
    account_realm_id: str = Field(default='', max_length=200)


def create_finance_router(
    *,
    enforce_rate_limit: 'Callable[[str, int, int], None]',
    accounting_integrations_memory: 'list[dict[str, Any]]',
    accounting_exports_memory: 'list[dict[str, Any]]',
    record_audit: 'Callable[[str, str, dict[str, Any]], None]',
) -> APIRouter:
    """Build the legacy finance router with injected dependencies."""
    router = APIRouter(tags=['finance-legacy'])

    @router.get('/ops/finance/hub')
    def finance_hub(auth: AuthContext = Depends(require_auth)) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:finance:hub', limit=120, window_seconds=60)
        integrations = [
            item for item in accounting_integrations_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id
        ]
        exports = [
            item for item in accounting_exports_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id
        ]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'connected_integrations': len(integrations),
            'exports_count': len(exports),
            'generated_at': datetime.now(UTC).isoformat(),
        }

    @router.post('/ops/finance/accounting/integrations/connect')
    def finance_connect_integration(
        payload: FinanceLegacyIntegrationConnectRequest,
        auth: AuthDep,
    ) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:finance:integrations:connect', limit=60, window_seconds=60)
        now = datetime.now(UTC).isoformat()
        provider = payload.provider.strip().lower()

        existing = next(
            (
                item for item in accounting_integrations_memory
                if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('provider', '')).lower() == provider
            ),
            None,
        )
        if existing is not None:
            existing['status'] = 'connected'
            existing['client_id_masked'] = payload.client_id[:3] + '***'
            existing['account_name'] = payload.account_name
            existing['updated_at'] = now
            integration = existing
        else:
            integration = {
                'id': len(accounting_integrations_memory) + 1,
                'tenant_id': auth.tenant_id,
                'provider': provider,
                'status': 'connected',
                'client_id_masked': payload.client_id[:3] + '***',
                'account_name': payload.account_name,
                'created_at': now,
                'updated_at': now,
            }
            accounting_integrations_memory.append(integration)

        record_audit(auth.tenant_id, 'finance.integration.connected', {'provider': provider})
        return {'status': 'ok', 'integration': integration}

    @router.get('/ops/finance/accounting/integrations')
    def finance_list_integrations(auth: AuthContext = Depends(require_auth)) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:finance:integrations:list', limit=120, window_seconds=60)
        rows = [
            item for item in accounting_integrations_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id
        ]
        rows.sort(key=lambda item: str(item.get('updated_at', '') or ''), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(rows),
            'integrations': rows,
            'generated_at': datetime.now(UTC).isoformat(),
        }

    @router.post('/ops/finance/accounting/exports')
    def finance_create_export(
        payload: FinanceLegacyExportRequest,
        auth: AuthDep,
    ) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:finance:exports:create', limit=60, window_seconds=60)
        now = datetime.now(UTC).isoformat()
        provider = payload.provider.strip().lower()
        delivery_status = 'submitted-live' if os.getenv('FINANCE_PROVIDER_LIVE', '0').strip().lower() in {'1', 'true', 'yes', 'on'} else 'queued-simulated'

        export_record = {
            'id': len(accounting_exports_memory) + 1,
            'tenant_id': auth.tenant_id,
            'provider': provider,
            'export_type': payload.export_type,
            'period_label': payload.period_label,
            'status': 'submitted',
            'delivery_status': delivery_status,
            'submitted_at': now,
            'completed_at': now,
            'detail': 'Legacy finance export accepted',
        }
        accounting_exports_memory.append(export_record)
        record_audit(
            auth.tenant_id,
            'finance.export.submitted',
            {'provider': provider, 'export_type': payload.export_type, 'period_label': payload.period_label},
        )
        return {'status': 'ok', 'export': export_record}

    @router.post(
        '/ops/finance/accounting/integrations/{provider}/refresh-token',
        responses={
            422: {'description': 'Unsupported provider or missing configuration'},
            409: {'description': 'Integration not connected for provider'},
        },
    )
    def finance_refresh_token(
        provider: str,
        auth: AuthContext = Depends(require_auth),
    ) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:finance:integrations:refresh', limit=40, window_seconds=60)
        normalized_provider = provider.strip().lower()
        if normalized_provider not in {'quickbooks', 'xero', 'hmrc'}:
            raise HTTPException(status_code=422, detail='Unsupported provider.')
        if normalized_provider == 'xero' and not os.getenv('XERO_CLIENT_SECRET', '').strip():
            raise HTTPException(status_code=422, detail='XERO_CLIENT_SECRET is not configured.')

        integration = next(
            (
                item for item in accounting_integrations_memory
                if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('provider', '')).lower() == normalized_provider
            ),
            None,
        )
        if integration is None:
            raise HTTPException(status_code=409, detail='Integration not connected for provider.')

        integration['updated_at'] = datetime.now(UTC).isoformat()
        record_audit(auth.tenant_id, 'finance.integration.refreshed', {'provider': normalized_provider})
        return {'status': 'ok', 'provider': normalized_provider, 'refresh': 'completed'}

    @router.post(
        '/ops/finance/accounting/integrations/{provider}/rotate-secret',
        responses={
            422: {'description': 'Unsupported provider'},
            409: {'description': 'Integration not connected for provider'},
        },
    )
    def finance_rotate_secret(
        provider: str,
        payload: FinanceLegacyRotateSecretRequest,
        auth: AuthContext = Depends(require_auth),
    ) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:finance:integrations:rotate-secret', limit=30, window_seconds=60)
        normalized_provider = provider.strip().lower()
        if normalized_provider not in {'quickbooks', 'xero', 'hmrc'}:
            raise HTTPException(status_code=422, detail='Unsupported provider.')

        integration = next(
            (
                item for item in accounting_integrations_memory
                if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('provider', '')).lower() == normalized_provider
            ),
            None,
        )
        if integration is None:
            raise HTTPException(status_code=409, detail='Integration not connected for provider.')

        integration['updated_at'] = datetime.now(UTC).isoformat()
        integration['secret_rotated'] = True
        integration['client_secret_masked'] = payload.client_secret[:3] + '***'
        record_audit(auth.tenant_id, 'finance.integration.secret_rotated', {'provider': normalized_provider})

        return {
            'status': 'ok',
            'provider': normalized_provider,
            'rotation_mode': 'secret-only',
        }

    return router
