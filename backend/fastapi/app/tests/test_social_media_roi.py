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

    summary_res = client.get('/analytics/social-roi/summary?window_days=90', headers=HEADERS)
    assert summary_res.status_code == 200
    summary = summary_res.json()

    assert summary['totals']['revenue'] >= 1000.0
    assert summary['totals']['spend'] >= 250.0
    assert summary['totals']['roi_pct'] > 0
    assert summary['totals']['tracking_coverage_pct'] >= 0
    assert any(row['channel'] == 'linkedin' for row in summary['channels'])
    assert any(row['campaign'] == 'spring_launch' for row in summary['campaigns'])
