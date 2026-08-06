from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key')


def _headers(tenant: str = 'ira-crm-advisor-tenant', include_super: bool = True) -> dict[str, str]:
    headers = {
        'X-API-Key': 'test-api-key',
        'X-Tenant-Id': tenant,
    }
    if include_super:
        headers['X-Super-Admin-Key'] = os.getenv('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key')
    return headers


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from backend.fastapi.app import main as app_main
    from backend.fastapi.app import memory_stores
    from backend.fastapi.app.main import app

    for value in vars(memory_stores).values():
        if isinstance(value, list):
            value.clear()
    app_main.reset_rate_limits_for_tests()

    memory_stores.ira_controls.append(
        {
            'id': 1,
            'tenant_id': 'ira-crm-advisor-tenant',
            'autonomy_enabled': True,
            'allow_high_impact_actions': True,
            'require_super_admin': True,
            'strict_policy_lock': True,
            'min_profit_margin_pct': 70.0,
            'suspicious_signal_threshold': 0.75,
            'max_dispute_auto_resolution_gbp': 50.0,
            'protection_mode': False,
            'blocked_actions': [],
            'updated_at': '2025-01-01T00:00:00+00:00',
        }
    )

    yield TestClient(app, raise_server_exceptions=False)

    for value in vars(memory_stores).values():
        if isinstance(value, list):
            value.clear()
    app_main.reset_rate_limits_for_tests()


def test_crm_feature_governance_requires_human_validation(client: TestClient) -> None:
    r = client.post(
        '/ira/crm/feature-governance',
        headers=_headers(),
        json={
            'feature': 'multi_tenancy',
            'owner': 'corteza',
            'disable_duplicate_in_secondary': True,
            'policy_change_human_validation': False,
            'notes': 'no human validation',
        },
    )
    assert r.status_code == 422
    assert 'human validation' in r.json().get('detail', '').lower()


def test_crm_feature_governance_strict_lock_blocks_duplicate_enable(client: TestClient) -> None:
    r = client.post(
        '/ira/crm/feature-governance',
        headers=_headers(),
        json={
            'feature': 'low_code_objects',
            'owner': 'corteza',
            'disable_duplicate_in_secondary': False,
            'policy_change_human_validation': True,
            'notes': 'attempt to allow duplicate in secondary',
        },
    )
    assert r.status_code == 422
    assert 'strict policy lock' in r.json().get('detail', '').lower()


def test_crm_feature_governance_success_persists_to_control(client: TestClient) -> None:
    # Avoid flaky DB dependencies while still covering router success path.
    with patch('backend.fastapi.app.routers.ira.psycopg.connect', side_effect=RuntimeError('db unavailable')):
        r = client.post(
            '/ira/crm/feature-governance',
            headers=_headers(),
            json={
                'feature': 'ecosystem_modules',
                'owner': 'odoo',
                'disable_duplicate_in_secondary': True,
                'policy_change_human_validation': True,
                'notes': 'odoo owns ecosystem modules',
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    assert data['governance']['ecosystem_modules']['owner'] == 'odoo'
    assert data['governance']['ecosystem_modules']['secondary_disabled_for'] == 'corteza'


def test_crm_connectors_status_probe_disabled_reports_configured(client: TestClient) -> None:
    with patch.dict(
        os.environ,
        {
            'IRA_CONNECTOR_HEALTH_PROBE_ENABLED': 'false',
            'CORTEZA_API_BASE_URL': 'http://corteza.local',
            'ODOO_API_BASE_URL': 'http://odoo.local',
        },
        clear=False,
    ):
        r = client.get('/ira/crm/connectors/status', headers=_headers())
    assert r.status_code == 200
    connectors = r.json()['connectors']
    assert connectors['corteza']['configured'] is True
    assert connectors['corteza']['detail'] == 'probe disabled'
    assert connectors['odoo']['configured'] is True
    assert connectors['odoo']['detail'] == 'probe disabled'


def test_crm_connectors_status_probe_enabled_success_and_exception(client: TestClient) -> None:
    ok = Mock(is_success=True, status_code=200)

    def _side_effect(url: str, **_: object) -> object:
        if 'corteza' in url:
            return ok
        raise RuntimeError('odoo down')

    with patch.dict(
        os.environ,
        {
            'IRA_CONNECTOR_HEALTH_PROBE_ENABLED': 'true',
            'CORTEZA_API_BASE_URL': 'http://corteza.local',
            'ODOO_API_BASE_URL': 'http://odoo.local',
        },
        clear=False,
    ), patch('backend.fastapi.app.routers.ira.httpx.get', side_effect=_side_effect):
        r = client.get('/ira/crm/connectors/status', headers=_headers())

    assert r.status_code == 200
    connectors = r.json()['connectors']
    assert connectors['corteza']['healthy'] is True
    assert connectors['corteza']['detail'] == 'status=200'
    assert connectors['odoo']['healthy'] is False
    assert 'odoo down' in connectors['odoo']['detail']


def test_advisor_recommendations_requires_super_admin(client: TestClient) -> None:
    r = client.post(
        '/ira/advisor/recommendations',
        headers=_headers(include_super=False),
        json={'objective': 'growth', 'horizon_days': 30, 'include_feature_adoption': True},
    )
    assert r.status_code == 403


def test_advisor_recommendations_includes_risk_and_margin_actions(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    tenant = 'ira-crm-advisor-tenant'
    memory_stores.invoices.append({'tenant_id': tenant, 'status': 'paid', 'amount': 100.0})
    # Force low margin: large credit grant cost overwhelms revenue.
    memory_stores.credit_ledger.append({'tenant_id': tenant, 'amount': 100000})

    memory_stores.ira_events.append(
        {
            'id': 1,
            'tenant_id': tenant,
            'event_type': 'learning_feedback_collected',
            'payload': {'rating': 5},
            'created_at': '2025-01-01T00:00:00+00:00',
        }
    )

    memory_stores.stripe_events.append(
        {
            'tenant_id': tenant,
            'event_type': 'payment_failed',
            'status': 'failed',
            'created_at': datetime.now(UTC).isoformat(),
        }
    )
    memory_stores.api_usage_audit.extend({'tenant_id': tenant, 'timestamp': 32503680000} for _ in range(300))

    r = client.post(
        '/ira/advisor/recommendations',
        headers=_headers(),
        json={'objective': 'stabilize margin', 'horizon_days': 45, 'include_feature_adoption': True},
    )
    assert r.status_code == 200
    data = r.json()
    ids = {item['id'] for item in data['recommendations']}
    assert 'risk-1' in ids
    assert 'margin-1' in ids
    assert data['metrics']['feedback_count'] >= 1
