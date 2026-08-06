import os

import pytest
from backend.fastapi.app.routers import agents as agents_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'agents-test-tenant'}

os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv('ALLOW_HEADER_API_KEYS', 'true')
    monkeypatch.setenv('FASTAPI_API_KEY', 'test-api-key')
    monkeypatch.setenv('ENVIRONMENT', 'development')
    agents_router.agents_db.clear()
    agents_router.executions_db.clear()

    app = FastAPI()
    app.include_router(agents_router.router)
    return TestClient(app, raise_server_exceptions=False)


def test_create_and_list_agents_in_development(client: TestClient) -> None:
    create_response = client.post(
        '/api/v1/agents/create',
        headers=H,
        json={
            'name': 'Revenue Assistant',
            'agent_type': 'demand_gen',
            'description': 'Tenant scoped helper',
            'available_tools': [],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created['name'] == 'Revenue Assistant'
    assert created['created_by'] == H['X-Tenant-Id']

    list_response = client.get('/api/v1/agents/list', headers=H)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]['id'] == created['id']


def test_create_agent_fails_closed_in_production_without_durable_store(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'production')

    response = client.post(
        '/api/v1/agents/create',
        headers=H,
        json={
            'name': 'Blocked Agent',
            'agent_type': 'demand_gen',
            'available_tools': [],
        },
    )
    assert response.status_code == 503
    assert response.json()['detail'] == agents_router.MEMORY_STORE_UNAVAILABLE
