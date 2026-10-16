"""
Targeted tests for the SEO platform module registry and performance audit endpoints.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')


def _make_client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=True)


def _headers() -> dict[str, str]:
    return {
        'X-API-Key': os.getenv('FASTAPI_API_KEY', 'test-api-key'),
        'X-Tenant-Id': 'test-tenant',
    }


@pytest.fixture
def client() -> TestClient:
    return _make_client()


def test_seo_module_registry_returns_all_catalog_entries(client: TestClient) -> None:
    response = client.get('/seo-platform/modules', headers=_headers())
    assert response.status_code == 200

    data = response.json()
    assert data['total'] == len(data['modules'])
    assert data['total'] >= 51
    assert any(group['group'] for group in data['groups'])


def test_seo_module_detail_for_performance_audit_is_not_offered(client: TestClient) -> None:
    """Performance audit needs a measurement provider, so the catalog does not list it."""
    response = client.get('/seo-platform/modules/performance-audit', headers=_headers())
    assert response.status_code == 404


def test_ahrefs_parity_audit_endpoint_returns_tool_matrix(client: TestClient) -> None:
    response = client.get('/seo-platform/ahrefs/parity', headers=_headers())
    assert response.status_code == 200

    data = response.json()
    audit = data['audit']
    assert audit['total_tools'] >= 10
    assert any(row['tool_key'] == 'site-explorer' for row in audit['rows'])
    assert all(row['route_path'].startswith('/seo/') for row in audit['rows'])


def test_performance_endpoints_refuse_without_a_measurement_provider(client: TestClient) -> None:
    for path in ('/seo-platform/performance/capabilities', '/seo-platform/performance/vendors'):
        response = client.get(path, headers=_headers())
        assert response.status_code == 501, path
        assert response.json()['detail']['code'] == 'NOT_IMPLEMENTED'
