from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth
from ..middleware.admin_allowlist import require_privileged_ip
from ..quantum_nist import get_quantum_nist_status

AuthDep = Annotated[AuthContext, Depends(require_auth)]
JsonObject = dict[str, object]

TARGET_MARGIN_DEFAULT = 0.67
MIN_MARGIN = 0.65
MAX_MARGIN = 0.70


class ProviderUpsertRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    vendor: str = Field(min_length=2, max_length=120)
    endpoint: str = Field(min_length=5, max_length=500)
    model: str = Field(default='default', max_length=180)
    billing_unit: str = Field(default='token', pattern=r'^(token|credit)$')
    token: str = Field(min_length=8, max_length=4096)
    cost_per_token_usd: float = Field(default=0.0, ge=0, le=100)
    cost_per_credit_usd: float = Field(default=0.0, ge=0, le=10000)
    credits_purchased: float = Field(default=0.0, ge=0)
    tokens_purchased: int = Field(default=0, ge=0)
    target_margin: float = Field(default=TARGET_MARGIN_DEFAULT, ge=MIN_MARGIN, le=MAX_MARGIN)


class ProviderDisableRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=400)


class UsageEventRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=120)
    request_path: str = Field(min_length=2, max_length=200)
    tokens_used: int = Field(default=0, ge=0)
    credits_used: float = Field(default=0.0, ge=0)
    revenue_generated_usd: float = Field(default=0.0, ge=0)
    status_code: int = Field(default=200, ge=100, le=599)


@dataclass
class ApiGovernanceContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    te_encrypt: Callable[[str], str]
    provider_store: list[JsonObject]
    usage_store: list[JsonObject]
    incident_store: list[JsonObject]
    notification_store: list[JsonObject]
    ira_events_store: list[JsonObject]
    siem_cases_store: list[JsonObject]
    vault_hashicorp_health: Callable[[], JsonObject]
    vault_supabase_health: Callable[[], JsonObject]
    persist: Callable[[], None] = lambda: None  # noqa: E731 – default no-op for tests


def create_api_governance_router(ctx: ApiGovernanceContext) -> APIRouter:  # NOSONAR
    # require_privileged_ip was defined for this exact router family (see its
    # docstring) but never actually wired up anywhere. This router manages
    # provider credentials/tokens for the whole platform, so it belongs behind
    # the IP allowlist as well as the existing token-only policy below.
    router = APIRouter(prefix='/api-governance', tags=['api-governance'], dependencies=[Depends(require_privileged_ip)])

    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _require_token_only(auth: AuthContext) -> None:
        if auth.auth_mode != 'bearer_jwt':
            raise HTTPException(status_code=403, detail='Token-only policy is enforced for API governance endpoints.')  # NOSONAR

    def _provider_not_found(provider_id: int) -> None:
        raise HTTPException(status_code=404, detail=f'Provider {provider_id} not found.')  # NOSONAR

    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    def _mask_token(encrypted: str) -> str:
        if not encrypted:
            return ''
        if len(encrypted) <= 10:
            return '**********'
        return f'{encrypted[:6]}...{encrypted[-4:]}'

    def _find_provider(provider_id: int) -> JsonObject:
        for row in ctx.provider_store:
            if _coerce_int(row.get('id', 0)) == provider_id:
                return row
        _provider_not_found(provider_id)
        raise RuntimeError('unreachable')

    def _append_incident(provider: JsonObject, title: str, detail: str) -> None:
        incident: JsonObject = {
            'id': len(ctx.incident_store) + 1,
            'tenant_id': provider.get('tenant_id', ''),
            'provider_id': provider.get('id', 0),
            'provider_name': provider.get('name', ''),
            'title': title,
            'detail': detail,
            'severity': 'critical',
            'created_at': _now(),
        }
        ctx.incident_store.append(incident)

        ctx.notification_store.append({
            'id': len(ctx.notification_store) + 1,
            'tenant_id': provider.get('tenant_id', ''),
            'message': f'EMERGENCY: {title} :: {detail}',
            'channel': 'admin-emergency',
            'priority': 'critical',
            'created_at': _now(),
        })

        ctx.ira_events_store.append({
            'id': len(ctx.ira_events_store) + 1,
            'tenant_id': provider.get('tenant_id', ''),
            'event_type': 'api_governance_emergency',
            'message': f'{title} - {detail}',
            'created_at': _now(),
        })

        ctx.siem_cases_store.append({
            'id': len(ctx.siem_cases_store) + 1,
            'tenant_id': provider.get('tenant_id', ''),
            'title': f'API emergency: {provider.get("name", "unknown")}',
            'severity': 'critical',
            'status': 'open',
            'assignee': 'root-admin',
            'updated_at': _now(),
            'description': detail,
        })

    def _cost_for_usage(provider: JsonObject, usage: UsageEventRequest) -> float:
        token_cost = float(provider.get('cost_per_token_usd', 0.0) or 0.0)
        credit_cost = float(provider.get('cost_per_credit_usd', 0.0) or 0.0)
        return usage.tokens_used * token_cost + usage.credits_used * credit_cost

    def _recommended_unit_price(usage_cost: float, unit_count: float, target_margin: float) -> float:
        if usage_cost <= 0 or unit_count <= 0:
            return 0.0
        denominator = max(0.01, 1.0 - target_margin)
        return usage_cost / unit_count / denominator

    def _evaluate_provider_health(provider: JsonObject) -> None:
        if provider.get('status') == 'disabled':
            return

        remaining_credits = float(provider.get('credits_remaining', 0.0) or 0.0)
        remaining_tokens = _coerce_int(provider.get('tokens_remaining', 0), 0)
        profit = float(provider.get('profit_total_usd', 0.0) or 0.0)

        if remaining_credits <= 0 and remaining_tokens <= 0:
            provider['status'] = 'disabled'
            _append_incident(provider, 'Provider disabled', 'No purchased credits/tokens remain. Root admin action required.')
            return

        if float(provider.get('revenue_total_usd', 0.0) or 0.0) > 0 and profit <= 0:
            provider['status'] = 'disabled'
            _append_incident(provider, 'Provider disabled', 'Usage generated no profit or loss. Root admin must rotate/reprice.')

    @router.post('/providers')
    def upsert_provider(payload: ProviderUpsertRequest, auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        ctx.enforce_rate_limit(f'{auth.tenant_id}:api-governance:provider-upsert', 60, 60)

        encrypted_token = ctx.te_encrypt(payload.token)
        existing = next((p for p in ctx.provider_store if p.get('tenant_id') == auth.tenant_id and p.get('name') == payload.name), None)

        base_fields: JsonObject = {
            'tenant_id': auth.tenant_id,
            'name': payload.name,
            'vendor': payload.vendor,
            'endpoint': payload.endpoint,
            'model': payload.model,
            'billing_unit': payload.billing_unit,
            'token_encrypted': encrypted_token,
            'cost_per_token_usd': payload.cost_per_token_usd,
            'cost_per_credit_usd': payload.cost_per_credit_usd,
            'credits_purchased': float(payload.credits_purchased),
            'tokens_purchased': int(payload.tokens_purchased),
            'credits_remaining': float(payload.credits_purchased),
            'tokens_remaining': int(payload.tokens_purchased),
            'target_margin': float(payload.target_margin),
            'status': 'active',
            'revenue_total_usd': 0.0,
            'cost_total_usd': 0.0,
            'profit_total_usd': 0.0,
            'updated_at': _now(),
        }

        if existing is None:
            base_fields['id'] = len(ctx.provider_store) + 1
            base_fields['created_at'] = _now()
            ctx.provider_store.append(base_fields)
            row = base_fields
        else:
            existing.update(base_fields)
            row = existing

        ctx.persist()
        return {
            'status': 'ok',
            'provider': {
                **row,
                'token_encrypted': _mask_token(str(row.get('token_encrypted', ''))),
            },
            'note': 'Provider stored with transparent encryption at rest.',
        }

    @router.get('/providers')
    def list_providers(auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        providers = []
        for row in ctx.provider_store:
            if row.get('tenant_id') != auth.tenant_id:
                continue
            providers.append({
                **row,
                'token_encrypted': _mask_token(str(row.get('token_encrypted', ''))),
            })
        return {'status': 'ok', 'providers': providers}

    @router.post('/providers/{provider_id}/usage')
    def record_provider_usage(provider_id: int, payload: UsageEventRequest, auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        ctx.enforce_rate_limit(f'{auth.tenant_id}:api-governance:usage', 600, 60)

        provider = _find_provider(provider_id)
        if provider.get('tenant_id') != auth.tenant_id:
            raise HTTPException(status_code=404, detail='Provider not found.')  # NOSONAR
        if provider.get('status') == 'disabled':
            raise HTTPException(status_code=423, detail='Provider is disabled. Root admin action is required.')  # NOSONAR

        usage_cost = _cost_for_usage(provider, payload)
        revenue = float(payload.revenue_generated_usd)
        profit = revenue - usage_cost
        margin = (profit / revenue) if revenue > 0 else 0.0

        provider['revenue_total_usd'] = float(provider.get('revenue_total_usd', 0.0) or 0.0) + revenue
        provider['cost_total_usd'] = float(provider.get('cost_total_usd', 0.0) or 0.0) + usage_cost
        provider['profit_total_usd'] = float(provider.get('profit_total_usd', 0.0) or 0.0) + profit
        provider['credits_remaining'] = max(0.0, float(provider.get('credits_remaining', 0.0) or 0.0) - payload.credits_used)
        provider['tokens_remaining'] = max(0, _coerce_int(provider.get('tokens_remaining', 0), 0) - payload.tokens_used)
        provider['updated_at'] = _now()

        target_margin = float(provider.get('target_margin', TARGET_MARGIN_DEFAULT) or TARGET_MARGIN_DEFAULT)
        if payload.tokens_used > 0:
            provider['recommended_sell_price_per_token_usd'] = round(
                _recommended_unit_price(usage_cost, payload.tokens_used, target_margin), 8
            )
        if payload.credits_used > 0:
            provider['recommended_sell_price_per_credit_usd'] = round(
                _recommended_unit_price(usage_cost, payload.credits_used, target_margin), 6
            )

        usage_row: JsonObject = {
            'id': len(ctx.usage_store) + 1,
            'tenant_id': auth.tenant_id,
            'provider_id': provider_id,
            'provider_name': provider.get('name', ''),
            'user_id': payload.user_id,
            'request_path': payload.request_path,
            'tokens_used': payload.tokens_used,
            'credits_used': payload.credits_used,
            'cost_usd': round(usage_cost, 8),
            'revenue_usd': round(revenue, 8),
            'profit_usd': round(profit, 8),
            'margin_pct': round(margin * 100.0, 4),
            'status_code': payload.status_code,
            'created_at': _now(),
        }
        ctx.usage_store.append(usage_row)

        _evaluate_provider_health(provider)

        ctx.persist()
        return {
            'status': 'ok',
            'usage': usage_row,
            'provider_status': provider.get('status', 'active'),
            'pricing': {
                'target_margin_pct': round(target_margin * 100.0, 2),
                'min_margin_pct': MIN_MARGIN * 100.0,
                'max_margin_pct': MAX_MARGIN * 100.0,
                'recommended_sell_price_per_token_usd': provider.get('recommended_sell_price_per_token_usd', 0.0),
                'recommended_sell_price_per_credit_usd': provider.get('recommended_sell_price_per_credit_usd', 0.0),
            },
        }

    @router.post('/providers/{provider_id}/disable')
    def disable_provider(provider_id: int, payload: ProviderDisableRequest, auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        provider = _find_provider(provider_id)
        if provider.get('tenant_id') != auth.tenant_id:
            raise HTTPException(status_code=404, detail='Provider not found.')  # NOSONAR
        provider['status'] = 'disabled'
        provider['updated_at'] = _now()
        _append_incident(provider, 'Provider disabled by admin', payload.reason)
        ctx.persist()
        return {'status': 'ok', 'provider_id': provider_id, 'provider_status': 'disabled'}

    @router.get('/kpi')
    def kpi(auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        tenant_providers = [p for p in ctx.provider_store if p.get('tenant_id') == auth.tenant_id]
        tenant_usage = [u for u in ctx.usage_store if u.get('tenant_id') == auth.tenant_id]
        tenant_incidents = [i for i in ctx.incident_store if i.get('tenant_id') == auth.tenant_id]

        total_revenue = sum(float(p.get('revenue_total_usd', 0.0) or 0.0) for p in tenant_providers)
        total_cost = sum(float(p.get('cost_total_usd', 0.0) or 0.0) for p in tenant_providers)
        total_profit = total_revenue - total_cost
        margin_pct = (total_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0
        active_count = sum(1 for p in tenant_providers if p.get('status') == 'active')

        return {
            'status': 'ok',
            'kpis': {
                'providers_total': len(tenant_providers),
                'providers_active': active_count,
                'providers_disabled': len(tenant_providers) - active_count,
                'usage_events': len(tenant_usage),
                'revenue_total_usd': round(total_revenue, 4),
                'cost_total_usd': round(total_cost, 4),
                'profit_total_usd': round(total_profit, 4),
                'profit_margin_pct': round(margin_pct, 4),
                'critical_incidents': len(tenant_incidents),
            },
        }

    @router.get('/analytics')
    def analytics(auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        rows = [u for u in ctx.usage_store if u.get('tenant_id') == auth.tenant_id]

        latest = rows[-14:]
        line_profit = [float(row.get('profit_usd', 0.0) or 0.0) for row in latest]
        line_margin = [float(row.get('margin_pct', 0.0) or 0.0) for row in latest]

        grouped: dict[str, dict[str, float]] = {}
        for row in rows:
            name = str(row.get('provider_name', 'unknown'))
            bucket = grouped.setdefault(name, {'revenue': 0.0, 'cost': 0.0, 'profit': 0.0, 'tokens': 0.0, 'credits': 0.0})
            bucket['revenue'] += float(row.get('revenue_usd', 0.0) or 0.0)
            bucket['cost'] += float(row.get('cost_usd', 0.0) or 0.0)
            bucket['profit'] += float(row.get('profit_usd', 0.0) or 0.0)
            bucket['tokens'] += float(row.get('tokens_used', 0.0) or 0.0)
            bucket['credits'] += float(row.get('credits_used', 0.0) or 0.0)

        bars = [
            {'label': name, 'value': round(values['profit'], 4)}
            for name, values in sorted(grouped.items(), key=lambda item: item[1]['profit'], reverse=True)
        ][:6]

        avg_margin = mean([float(row.get('margin_pct', 0.0) or 0.0) for row in rows]) if rows else 0.0

        return {
            'status': 'ok',
            'line_profit': line_profit,
            'line_margin_pct': line_margin,
            'bars_profit_by_provider': bars,
            'avg_margin_pct': round(avg_margin, 4),
            'events_analyzed': len(rows),
        }

    @router.get('/third-party-profit')
    def third_party_profit(auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        providers = [p for p in ctx.provider_store if p.get('tenant_id') == auth.tenant_id]
        payload = []
        for row in providers:
            revenue = float(row.get('revenue_total_usd', 0.0) or 0.0)
            cost = float(row.get('cost_total_usd', 0.0) or 0.0)
            profit = revenue - cost
            margin = (profit / revenue * 100.0) if revenue > 0 else 0.0
            payload.append({
                'id': row.get('id', 0),
                'name': row.get('name', ''),
                'status': row.get('status', 'active'),
                'revenue_usd': round(revenue, 4),
                'cost_usd': round(cost, 4),
                'profit_usd': round(profit, 4),
                'margin_pct': round(margin, 4),
                'tokens_remaining': row.get('tokens_remaining', 0),
                'credits_remaining': row.get('credits_remaining', 0.0),
                'recommended_sell_price_per_token_usd': row.get('recommended_sell_price_per_token_usd', 0.0),
                'recommended_sell_price_per_credit_usd': row.get('recommended_sell_price_per_credit_usd', 0.0),
            })
        return {'status': 'ok', 'providers': payload}

    @router.get('/security/encryption-posture')
    def encryption_posture(auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        pq = get_quantum_nist_status()
        return {
            'status': 'ok',
            'encryption': {
                'at_rest': {'enabled': True, 'algorithm': 'AES-256-GCM transparent field encryption'},
                'in_transit': {'enabled': True, 'requirements': ['Bearer JWT', 'HTTPS header policy', 'optional mTLS']},
                'in_use': {'enabled': True, 'control_plane': 'token-only authz + runtime policy checks + rate limits'},
                'in_memory': {'enabled': True, 'controls': ['sensitive token masking', 'encrypted-at-rest provider secrets']},
                'quantum_nist': {
                    'enabled': pq.enabled,
                    'algorithm': pq.algorithm,
                    'provider': pq.provider,
                    'mode': pq.mode,
                    'detail': pq.detail,
                },
                'vaults': {
                    'hashicorp': ctx.vault_hashicorp_health(),
                    'supabase': ctx.vault_supabase_health(),
                },
            },
        }

    @router.get('/security/exposure')
    def exposure_posture(auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        providers = [p for p in ctx.provider_store if p.get('tenant_id') == auth.tenant_id]
        disabled = [p for p in providers if p.get('status') == 'disabled']
        return {
            'status': 'ok',
            'posture': {
                'token_only_policy': True,
                'frontend_secret_exposure': False,
                'backend_plaintext_secret_exposure': False,
                'database_plaintext_secret_exposure': False,
                'internet_exposure_controls': {
                    'zero_plaintext_tokens': True,
                    'masked_token_response': True,
                    'tenant_scoped_access': True,
                },
                'providers_disabled_for_risk': len(disabled),
            },
            'threat_tracking': {
                'mitm_detection': 'enabled-via-transport-policy',
                'unknown_user_detection': 'enabled-via-token-only-auth',
                'bypass_detection': 'enabled-via-rate-limit-and-siem-cases',
                'ira_watchdog': 'enabled-via-incident-events',
            },
        }

    @router.get('/incidents')
    def incidents(auth: AuthDep) -> JsonObject:
        _require_token_only(auth)
        rows = [i for i in ctx.incident_store if i.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'incidents': rows[-200:]}

    return router
