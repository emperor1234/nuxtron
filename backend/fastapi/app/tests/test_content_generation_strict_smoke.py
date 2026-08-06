from __future__ import annotations

import os
import time

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')

import pytest
from fastapi.testclient import TestClient

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'test-tenant'}


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    lm._ai_generated_assets_memory.clear()
    lm._content_generations_memory.clear()
    lm._content_generation_jobs_memory.clear()
    with lm._content_generation_telemetry_lock:
        lm._content_generation_telemetry['strict_rejections_total'] = 0
        lm._content_generation_telemetry['strict_rejections_by_reason'] = {}
        lm._content_generation_telemetry['fallback_attempts_total'] = 0
        lm._content_generation_telemetry['fallback_attempts_by_reason'] = {}
        lm._content_generation_telemetry['updated_at'] = None

    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'true')
    monkeypatch.setenv('CONTENT_GENERATION_STRICT_SKIP_STARTUP_PROVIDER_CHECK', 'true')
    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    monkeypatch.setattr(
        lm,
        '_run_optional_ai_generation',
        lambda payload, auth, created_at: (
            'openai',
            'gpt-4o-mini',
            {
                'provider': 'openai',
                'model': 'gpt-4o-mini',
                'output_text': 'Generated strict copy',
                'usage': {},
                'latency_ms': 10,
            },
            'Generated strict copy',
        ),
    )

    def _media_bundle(*, tenant_id: str, prompt: str, text_seed: str, requested_provider: str):
        image = lm._persist_ai_generated_asset(
            tenant_id=tenant_id,
            kind='image',
            mime_type='image/png',
            content=b'image-bytes',
            provider_used='stability_ai',
            generation_status='generated',
        )
        voice = lm._persist_ai_generated_asset(
            tenant_id=tenant_id,
            kind='voice',
            mime_type='audio/wav',
            content=b'voice-bytes',
            provider_used='elevenlabs',
            generation_status='generated',
        )
        video = lm._persist_ai_generated_asset(
            tenant_id=tenant_id,
            kind='video',
            mime_type='video/mp4',
            content=b'video-bytes',
            provider_used='replicate',
            generation_status='generated',
        )
        return {'image': image, 'voice': voice, 'video': video}

    monkeypatch.setattr(lm, '_generate_media_asset_bundle', _media_bundle)


@pytest.fixture()
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_strict_content_generation_end_to_end_smoke(client: TestClient) -> None:
    sync_response = client.post(
        '/content/generate',
        headers=H,
        json={
            'topic': 'Strict mode smoke',
            'audience': 'Operations',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )
    assert sync_response.status_code == 200
    sync_payload = sync_response.json()
    assert sync_payload['production_mode'] == 'strict-real-generation'
    assert sync_payload['ai_status'] == 'generated'

    image_download_url = sync_payload['generated_assets']['image']['download_url']
    asset_response = client.get(image_download_url, headers=H)
    assert asset_response.status_code == 200

    submit = client.post(
        '/content/generate/async',
        headers=H,
        json={
            'topic': 'Strict mode async smoke',
            'audience': 'Operations',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )
    assert submit.status_code == 202
    job_id = submit.json()['job_id']

    for _ in range(120):
        poll = client.get(f'/content/generate/jobs/{job_id}', headers=H)
        assert poll.status_code == 200
        if poll.json()['job']['status'] == 'completed':
            break
        time.sleep(0.02)

    completed = client.get(f'/content/generate/jobs/{job_id}', headers=H)
    assert completed.status_code == 200
    assert completed.json()['job']['status'] == 'completed'

    with client.stream(
        'GET',
        f'/content/generate/jobs/{job_id}/stream?api_key=test-api-key&tenant_id=test-tenant',
    ) as stream_response:
        assert stream_response.status_code == 200
        chunk = next(stream_response.iter_text())
        assert 'content-job.snapshot' in chunk
        assert job_id in chunk

    listed = client.get('/content/generate/jobs?status=completed', headers=H)
    assert listed.status_code == 200
    assert any(item['job_id'] == job_id for item in listed.json()['items'])

    telemetry = client.get('/content/generate/telemetry', headers=H)
    assert telemetry.status_code == 200
    counters = telemetry.json()['counters']
    assert counters['strict_rejections_total'] == 0
    assert counters['fallback_attempts_total'] == 0
