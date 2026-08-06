from __future__ import annotations

import os

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')

import pytest
from fastapi.testclient import TestClient

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'test-tenant'}


@pytest.fixture(autouse=True)
def _reset_generated_asset_state(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    from backend.fastapi.app import legacy_main as lm

    lm._ai_generated_assets_memory.clear()
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
