# pyright: reportMissingImports=false

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('APP_ENC_KEY', '00' * 32)
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')

HEADERS = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'test-vse-analytics'}


@pytest.fixture(scope='module')
def client() -> TestClient:
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_vse_dashboard_summary_contract(client: TestClient) -> None:
    response = client.get('/vse/dashboard/summary', headers=HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data.get('status') == 'ok'
    assert data.get('tenant_id') == HEADERS['X-Tenant-Id']
    assert data.get('persistence') in {'postgres', 'memory-fallback'}

    summary = data.get('summary', {})
    assert isinstance(summary, dict)
    assert 'engines_online' in summary
    assert 'subsystems_online' in summary
    assert 'total_viral_events' in summary
    assert 'avg_viral_probability_score' in summary


def test_vse_k_factor_contract(client: TestClient) -> None:
    response = client.get('/vse/analytics/k-factor', headers=HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data.get('status') == 'ok'
    assert data.get('tenant_id') == HEADERS['X-Tenant-Id']
    assert data.get('persistence') in {'postgres', 'memory-fallback'}

    assert 'k_factor' in data
    assert 'invites_per_user' in data
    assert 'conversion_rate' in data
    assert data.get('classification') in {'subcritical', 'accelerating', 'self-sustaining'}


def test_vse_cascade_map_contract(client: TestClient) -> None:
    response = client.get('/vse/analytics/cascade-map', headers=HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data.get('status') == 'ok'
    assert data.get('tenant_id') == HEADERS['X-Tenant-Id']
    assert data.get('persistence') in {'postgres', 'memory-fallback'}

    graph = data.get('map', {})
    assert isinstance(graph, dict)
    assert isinstance(graph.get('nodes', []), list)
    assert isinstance(graph.get('edges', []), list)
    assert graph.get('node_count', 0) >= 1
    assert graph.get('edge_count', 0) >= 1


def test_vse_roi_report_contract(client: TestClient) -> None:
    response = client.get('/vse/analytics/roi-report', headers=HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data.get('status') == 'ok'
    assert data.get('tenant_id') == HEADERS['X-Tenant-Id']
    assert data.get('persistence') in {'postgres', 'memory-fallback'}

    report = data.get('report', {})
    assert isinstance(report, dict)
    assert 'events' in report
    assert 'total_spend_gbp' in report
    assert 'estimated_revenue_gbp' in report
    assert 'roi_ratio' in report
    assert 'roi_percent' in report
