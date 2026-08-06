from __future__ import annotations

from backend.fastapi.app.main import app
from backend.fastapi.app.routers import social_media_router as parity_router
from fastapi.testclient import TestClient


def _headers(tenant_id: str = 'tenant-parity-e2e') -> dict[str, str]:
    return {
        'X-API-Key': 'test-api-key',
        'X-Tenant-Id': tenant_id,
    }


def test_social_parity_create_list_get_flow(monkeypatch):
    monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
    monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')

    parity_router._parity_content_store.clear()

    client = TestClient(app)

    create_response = client.post(
        '/api/v1/social/content/create',
        headers=_headers(),
        json={
            'title': 'Parity Campaign Launch',
            'caption': 'Shipping parity flow to production',
            'media_assets': [],
            'platforms': ['linkedin'],
            'requires_approval': False,
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created['id']
    assert created['status'] == 'draft'

    list_response = client.get('/api/v1/social/content/list', headers=_headers())
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed['total'] >= 1
    item_ids = [item['id'] for item in listed['items']]
    assert created['id'] in item_ids

    detail_response = client.get(f"/api/v1/social/content/{created['id']}", headers=_headers())
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail['id'] == created['id']
    assert detail['title'] == 'Parity Campaign Launch'
    assert detail['platforms'] == ['linkedin']

    reschedule_response = client.post(
        f"/api/v1/social/content/{created['id']}/reschedule",
        headers=_headers(),
        json={'new_scheduled_time': '2031-01-01T12:00:00Z'},
    )
    assert reschedule_response.status_code == 200
    rescheduled = reschedule_response.json()
    assert rescheduled['success'] is True
    assert rescheduled['status'] == 'scheduled'

    delete_response = client.delete(f"/api/v1/social/content/{created['id']}", headers=_headers())
    assert delete_response.status_code == 200
    assert delete_response.json()['deleted'] is True

    deleted_detail_response = client.get(f"/api/v1/social/content/{created['id']}", headers=_headers())
    assert deleted_detail_response.status_code == 404


def test_social_parity_content_tenant_isolation(monkeypatch):
    monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
    monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')

    parity_router._parity_content_store.clear()

    client = TestClient(app)

    create_response = client.post(
        '/api/v1/social/content/create',
        headers=_headers('tenant-a'),
        json={
            'title': 'Tenant A Content',
            'caption': 'Only tenant A should access this',
            'media_assets': [],
            'platforms': ['twitter'],
            'requires_approval': False,
        },
    )
    assert create_response.status_code == 200
    content_id = create_response.json()['id']

    forbidden_response = client.get(f'/api/v1/social/content/{content_id}', headers=_headers('tenant-b'))
    assert forbidden_response.status_code == 404
