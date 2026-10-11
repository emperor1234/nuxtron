from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')

import pytest
from fastapi.testclient import TestClient

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'test-tenant'}


@pytest.fixture(autouse=True)
def _reset_generated_asset_state(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    from backend.fastapi.app import generated_asset_store
    from backend.fastapi.app import legacy_main as lm

    generated_asset_store.reset_generated_assets_for_tests()
    lm._content_generations_memory.clear()
    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    monkeypatch.setenv('AI_GENERATED_ASSET_INLINE_MAX_BYTES', '0')
    monkeypatch.setenv('AI_GENERATED_ASSET_STORAGE_DIR', str(tmp_path))


@pytest.fixture()
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_generated_asset_download_uses_file_storage_when_inline_missing(client: TestClient) -> None:
    from backend.fastapi.app import legacy_main as lm

    asset = lm._persist_ai_generated_asset(
        tenant_id='test-tenant',
        kind='image',
        mime_type='image/png',
        content=b'\x89PNG\r\n\x1a\nasset-body',
        provider_used='unit-test',
        generation_status='generated',
    )

    # Force download path to rely on file-backed payload.
    with lm._ai_generated_assets_lock:
        lm._ai_generated_assets_memory[0]['content_base64'] = ''

    response = client.get(f"/ai/generated-assets/{asset['id']}", headers=H)
    assert response.status_code == 200
    assert response.headers.get('content-type', '').startswith('image/png')
    assert response.content == b'\x89PNG\r\n\x1a\nasset-body'


def test_generated_asset_ids_are_unique_under_concurrency() -> None:
    from backend.fastapi.app import generated_asset_store
    from backend.fastapi.app import legacy_main as lm
    from backend.fastapi.app.services import ai_providers

    def persist(index: int) -> int:
        asset = lm._persist_ai_generated_asset(
            tenant_id='test-tenant',
            kind='image',
            mime_type='image/png',
            content=f'asset-{index}'.encode(),
            provider_used='unit-test',
            generation_status='generated',
        )
        return int(asset['id'])

    with ThreadPoolExecutor(max_workers=12) as executor:
        ids = list(executor.map(persist, range(80)))

    assert len(ids) == len(set(ids)) == 80
    assert sorted(ids) == list(range(1, 81))
    assert lm._ai_generated_assets_memory is generated_asset_store.ai_generated_assets
    assert ai_providers._ai_generated_assets_memory is generated_asset_store.ai_generated_assets
    assert lm._ai_generated_assets_lock is generated_asset_store.ai_generated_assets_lock
    assert ai_providers._ai_generated_assets_lock is generated_asset_store.ai_generated_assets_lock


def test_trimming_does_not_recycle_generated_asset_ids() -> None:
    from backend.fastapi.app import generated_asset_store

    ids = [
        generated_asset_store.append_generated_asset(
            lambda asset_id, index=index: {'id': asset_id, 'tenant_id': 'test-tenant', 'index': index}
        )['id']
        for index in range(2001)
    ]
    next_item = generated_asset_store.append_generated_asset(
        lambda asset_id: {'id': asset_id, 'tenant_id': 'test-tenant'}
    )

    assert ids == list(range(1, 2002))
    assert next_item['id'] == 2002
    assert len(generated_asset_store.ai_generated_assets) == 1502
    assert generated_asset_store.ai_generated_assets[0]['id'] == 501


def test_generated_asset_reader_uses_canonical_access_operation() -> None:
    from backend.fastapi.app import generated_asset_store

    generated_asset_store.append_generated_asset(
        lambda asset_id: {'id': asset_id, 'tenant_id': 'test-tenant', 'mime_type': 'image/png'}
    )

    item = generated_asset_store.find_generated_asset(1, 'test-tenant')

    assert item == {'id': 1, 'tenant_id': 'test-tenant', 'mime_type': 'image/png'}
    assert item is not generated_asset_store.ai_generated_assets[0]
