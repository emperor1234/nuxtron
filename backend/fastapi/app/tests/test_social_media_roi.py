from __future__ import annotations

import os

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')

import pytest
from fastapi.testclient import TestClient

HEADERS = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'tenant-roi'}


@pytest.fixture(scope='module')
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_social_roi_calculator_returns_expected_totals(client: TestClient) -> None:
    response = client.post(
        '/analytics/social-roi/calculator',
        headers=HEADERS,
        json={
            'attributed_revenue': 5000,
            'paid_social_spend': 1200,
            'team_cost': 600,
            'tools_cost': 200,
            'agency_cost': 0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    totals = payload['totals']
    assert totals['spend'] == 2000.0
    assert totals['net_profit'] == 3000.0
    assert totals['roas'] == 2.5
    assert totals['roi_pct'] == 150.0


def test_social_roi_calculator_does_not_invent_ratios_when_spend_is_zero(client: TestClient) -> None:
    response = client.post(
        '/analytics/social-roi/calculator',
        headers=HEADERS,
        json={'attributed_revenue': 100, 'paid_social_spend': 0, 'team_cost': 0, 'tools_cost': 0, 'agency_cost': 0},
    )
    assert response.status_code == 200
    totals = response.json()['totals']
    assert totals['revenue'] == 100.0
    assert totals['spend'] == 0.0
    assert totals['roas'] is None
    assert totals['roi_pct'] is None


def test_social_roi_spend_and_summary_flow(client: TestClient) -> None:
    touchpoint_res = client.post(
        '/analytics/revenue-attribution/touchpoints',
        headers=HEADERS,
        json={
            'post_id': 'post_123',
            'platform': 'linkedin',
            'campaign': 'spring_launch',
            'destination_url': 'https://example.com/pricing',
        },
    )
    assert touchpoint_res.status_code == 200
    assert touchpoint_res.json()['persistence_mode'] in {'postgres', 'process-memory'}
    tp = touchpoint_res.json()['touchpoint']['touchpoint_key']

    ingest_res = client.post(
        '/analytics/revenue-attribution/conversions/ingest',
        headers=HEADERS,
        json={
            'provider': 'stripe',
            'external_order_id': 'order_roi_1',
            'amount': 1000,
            'currency': 'USD',
            'event_type': 'order.paid',
            'touchpoint_keys': [tp],
        },
    )
    assert ingest_res.status_code == 200

    spend_res = client.post(
        '/analytics/social-roi/spend',
        headers=HEADERS,
        json={
            'channel': 'linkedin',
            'campaign': 'spring_launch',
            'amount': 250,
            'currency': 'USD',
        },
    )
    assert spend_res.status_code == 200
    assert spend_res.json()['persistence_mode'] in {'postgres', 'process-memory'}

    summary_res = client.get('/analytics/social-roi/summary?window_days=90', headers=HEADERS)
    assert summary_res.status_code == 200
    summary = summary_res.json()

    assert summary['currency_status'] == 'single'
    assert summary['currency_codes'] == ['USD']
    assert summary['persistence_mode'] in {'postgres', 'process-memory'}
    assert summary['totals']['conversions'] >= 1
    assert summary['totals']['revenue'] >= 1000.0
    assert summary['totals']['spend'] >= 250.0
    assert summary['totals']['roi_pct'] > 0
    assert summary['totals']['tracking_coverage_pct'] >= 0
    assert any(row['channel'] == 'linkedin' for row in summary['channels'])
    assert any(row['campaign'] == 'spring_launch' for row in summary['campaigns'])


def test_social_roi_summary_withholds_combined_totals_for_mixed_currencies(client: TestClient) -> None:
    headers = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'tenant-roi-mixed-currency'}
    touchpoint_response = client.post(
        '/analytics/revenue-attribution/touchpoints',
        headers=headers,
        json={
            'post_id': 'post_currency_test',
            'platform': 'linkedin',
            'campaign': 'currency_test',
            'destination_url': 'https://example.com/currency',
        },
    )
    assert touchpoint_response.status_code == 200
    touchpoint_key = touchpoint_response.json()['touchpoint']['touchpoint_key']
    conversion_response = client.post(
        '/analytics/revenue-attribution/conversions/ingest',
        headers=headers,
        json={
            'provider': 'stripe',
            'external_order_id': 'order_currency_test',
            'amount': 100,
            'currency': 'EUR',
            'event_type': 'order.paid',
            'touchpoint_keys': [touchpoint_key],
        },
    )
    assert conversion_response.status_code == 200
    spend_response = client.post(
        '/analytics/social-roi/spend',
        headers=headers,
        json={'channel': 'linkedin', 'campaign': 'currency_test', 'amount': 10, 'currency': 'USD'},
    )
    assert spend_response.status_code == 200

    summary_response = client.get('/analytics/social-roi/summary?window_days=90', headers=headers)
    assert summary_response.status_code == 200
    summary = summary_response.json()

    assert summary['currency_status'] == 'mixed'
    assert summary['currency_codes'] == ['EUR', 'USD']
    for metric in ('revenue', 'spend', 'net_profit', 'roas', 'roi_pct'):
        assert summary['totals'][metric] is None
        assert all(row[metric] is None for row in summary['channels'] + summary['campaigns'])
