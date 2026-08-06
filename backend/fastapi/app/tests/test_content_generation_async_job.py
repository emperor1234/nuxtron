from __future__ import annotations

import os
import time
from datetime import UTC, datetime

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
    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    monkeypatch.setattr(
        lm,
        '_run_optional_ai_generation',
        lambda payload, auth, created_at: (
            'openai',
            'gpt-4o-mini',
            {'provider': 'openai', 'model': 'gpt-4o-mini', 'output_text': 'Generated copy', 'usage': {}, 'latency_ms': 15},
            'Generated copy',
        ),
    )
    monkeypatch.setattr(
        lm,
        '_generate_media_asset_bundle',
        lambda **kwargs: {
            'image': {
                'id': 11,
                'kind': 'image',
                'mime_type': 'image/png',
                'file_name': 'image-11.png',
                'download_url': '/ai/generated-assets/11',
                'generation_status': 'generated',
                'provider_used': 'stability_ai',
                'size_bytes': 200,
            },
            'voice': {
                'id': 12,
                'kind': 'voice',
                'mime_type': 'audio/wav',
                'file_name': 'voice-12.wav',
                'download_url': '/ai/generated-assets/12',
                'generation_status': 'fallback',
                'provider_used': 'fallback',
                'size_bytes': 200,
            },
            'video': {
                'id': 13,
                'kind': 'video',
                'mime_type': 'image/gif',
                'file_name': 'video-13.gif',
                'download_url': '/ai/generated-assets/13',
                'generation_status': 'fallback',
                'provider_used': 'fallback',
                'size_bytes': 200,
            },
        },
    )


@pytest.fixture()
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_async_content_generation_job_submit_and_poll(client: TestClient) -> None:
    submit = client.post(
        '/content/generate/async',
        headers=H,
        json={
            'topic': 'AI workflow automation',
            'audience': 'Growth teams',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )
    assert submit.status_code == 202
    submit_payload = submit.json()
    job_id = submit_payload['job_id']
    assert submit_payload['poll_url'].endswith(job_id)

    final_payload = None
    for _ in range(60):
        poll = client.get(f'/content/generate/jobs/{job_id}', headers=H)
        assert poll.status_code == 200
        final_payload = poll.json()
        status = final_payload['job']['status']
        if status in {'completed', 'failed'}:
            break
        time.sleep(0.02)

    assert final_payload is not None
    assert final_payload['job']['status'] == 'completed'
    assert int(final_payload['job']['progress_pct']) == 100
    assert str(final_payload['job']['stage']) == 'completed'
    assert final_payload['job']['result']['generation_id'].startswith('cg-')
    assert final_payload['job']['result']['generated_assets']['image']['download_url'] == '/ai/generated-assets/11'


def test_async_content_generation_job_missing_returns_404(client: TestClient) -> None:
    response = client.get('/content/generate/jobs/nonexistent-job', headers=H)
    assert response.status_code == 404


def test_async_content_generation_job_stream_sse(client: TestClient) -> None:
    submit = client.post(
        '/content/generate/async',
        headers=H,
        json={
            'topic': 'Streaming automation',
            'audience': 'Ops team',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )
    assert submit.status_code == 202
    job_id = submit.json()['job_id']

    # Wait for completion to keep stream deterministic in tests.
    for _ in range(60):
        poll = client.get(f'/content/generate/jobs/{job_id}', headers=H)
        if poll.status_code == 200 and poll.json()['job']['status'] in {'completed', 'failed'}:
            break
        time.sleep(0.02)

    with client.stream(
        'GET',
        f'/content/generate/jobs/{job_id}/stream?api_key=test-api-key&tenant_id=test-tenant',
    ) as response:
        assert response.status_code == 200
        first_chunk = next(response.iter_text())
        assert 'event: content-job.snapshot' in first_chunk
        assert job_id in first_chunk


def test_async_content_generation_job_cancel_pending(client: TestClient) -> None:
    from backend.fastapi.app import legacy_main as lm

    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-cancel-1',
            'tenant_id': 'test-tenant',
            'status': 'pending',
            'progress_pct': 0,
            'stage': 'queued',
            'created_at': '2026-01-01T00:00:00+00:00',
            'updated_at': '2026-01-01T00:00:00+00:00',
            'started_at': None,
            'completed_at': None,
            'result': None,
            'error': None,
            'cancel_requested': False,
            'payload_data': {
                'topic': 'cancel test',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    cancel = client.delete('/content/generate/jobs/cgj-cancel-1', headers=H)
    assert cancel.status_code == 200
    payload = cancel.json()['job']
    assert payload['status'] == 'cancelled'
    assert payload['stage'] == 'cancelled'
    assert payload['cancel_requested'] is True


def test_async_content_generation_job_retry_failed_then_completes(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    first_attempt = {'value': True}
    original_builder = lm._build_content_generation_response

    def flaky_builder(payload, auth):
        if first_attempt['value']:
            first_attempt['value'] = False
            raise RuntimeError('simulated failure for retry')
        return original_builder(payload, auth)

    monkeypatch.setattr(lm, '_build_content_generation_response', flaky_builder)

    submit = client.post(
        '/content/generate/async',
        headers=H,
        json={
            'topic': 'Retry automation',
            'audience': 'Growth teams',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )
    assert submit.status_code == 202
    job_id = submit.json()['job_id']

    failed = False
    for _ in range(80):
        poll = client.get(f'/content/generate/jobs/{job_id}', headers=H)
        assert poll.status_code == 200
        status = poll.json()['job']['status']
        if status == 'failed':
            failed = True
            break
        time.sleep(0.02)

    assert failed

    retry = client.post(f'/content/generate/jobs/{job_id}/retry', headers=H)
    assert retry.status_code == 200
    assert retry.json()['job']['status'] == 'pending'

    completed = False
    for _ in range(120):
        poll = client.get(f'/content/generate/jobs/{job_id}', headers=H)
        assert poll.status_code == 200
        status = poll.json()['job']['status']
        if status == 'completed':
            completed = True
            break
        time.sleep(0.02)

    assert completed


def test_async_content_generation_submit_rejects_when_inflight_limit_reached(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_MAX_INFLIGHT_PER_TENANT', '1')
    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-inflight-1',
            'tenant_id': 'test-tenant',
            'status': 'running',
            'progress_pct': 20,
            'stage': 'generating',
            'created_at': '2026-01-01T00:00:00+00:00',
            'updated_at': '2026-01-01T00:00:00+00:00',
            'started_at': '2026-01-01T00:00:00+00:00',
            'completed_at': None,
            'result': None,
            'error': None,
            'cancel_requested': False,
            'payload_data': {
                'topic': 'inflight',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    submit = client.post(
        '/content/generate/async',
        headers=H,
        json={
            'topic': 'should reject',
            'audience': 'Growth teams',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )
    assert submit.status_code == 429


def test_async_content_generation_retry_rejects_when_inflight_limit_reached(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_MAX_INFLIGHT_PER_TENANT', '1')
    now_iso = datetime.now(UTC).isoformat()

    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-busy-running',
            'tenant_id': 'test-tenant',
            'status': 'running',
            'progress_pct': 30,
            'stage': 'generating',
            'created_at': '2026-01-01T00:00:00+00:00',
            'updated_at': '2026-01-01T00:00:00+00:00',
            'started_at': '2026-01-01T00:00:00+00:00',
            'completed_at': None,
            'result': None,
            'error': None,
            'cancel_requested': False,
            'payload_data': {
                'topic': 'busy',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-failed-retry',
            'tenant_id': 'test-tenant',
            'status': 'failed',
            'progress_pct': 100,
            'stage': 'failed',
            'created_at': now_iso,
            'updated_at': now_iso,
            'started_at': now_iso,
            'completed_at': now_iso,
            'result': None,
            'error': 'failed',
            'cancel_requested': False,
            'payload_data': {
                'topic': 'retry me',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    retry = client.post('/content/generate/jobs/cgj-failed-retry/retry', headers=H)
    assert retry.status_code == 429


def test_async_content_generation_job_terminal_ttl_expires_to_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_JOB_RETENTION_SECONDS', '60')
    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-expired-terminal',
            'tenant_id': 'test-tenant',
            'status': 'completed',
            'progress_pct': 100,
            'stage': 'completed',
            'created_at': '2025-01-01T00:00:00+00:00',
            'updated_at': '2025-01-01T00:00:00+00:00',
            'started_at': '2025-01-01T00:00:00+00:00',
            'completed_at': '2025-01-01T00:00:00+00:00',
            'result': {'generation_id': 'cg-old'},
            'error': None,
            'cancel_requested': False,
            'payload_data': {
                'topic': 'expired',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    poll = client.get('/content/generate/jobs/cgj-expired-terminal', headers=H)
    assert poll.status_code == 404


def test_async_content_generation_job_running_not_pruned_by_ttl(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_JOB_RETENTION_SECONDS', '60')
    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-running-kept',
            'tenant_id': 'test-tenant',
            'status': 'running',
            'progress_pct': 40,
            'stage': 'generating',
            'created_at': '2025-01-01T00:00:00+00:00',
            'updated_at': '2025-01-01T00:00:00+00:00',
            'started_at': '2025-01-01T00:00:00+00:00',
            'completed_at': None,
            'result': None,
            'error': None,
            'cancel_requested': False,
            'payload_data': {
                'topic': 'running',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    poll = client.get('/content/generate/jobs/cgj-running-kept', headers=H)
    assert poll.status_code == 200
    assert poll.json()['job']['status'] == 'running'


def test_async_content_generation_jobs_list_filters_and_retention_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_JOB_RETENTION_SECONDS', '120')
    now_iso = datetime.now(UTC).isoformat()

    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-list-running',
            'tenant_id': 'test-tenant',
            'status': 'running',
            'progress_pct': 45,
            'stage': 'generating',
            'created_at': now_iso,
            'updated_at': now_iso,
            'started_at': now_iso,
            'completed_at': None,
            'result': None,
            'error': None,
            'cancel_requested': False,
            'payload_data': {
                'topic': 'list-running',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-list-completed',
            'tenant_id': 'test-tenant',
            'status': 'completed',
            'progress_pct': 100,
            'stage': 'completed',
            'created_at': now_iso,
            'updated_at': now_iso,
            'started_at': now_iso,
            'completed_at': now_iso,
            'result': {'generation_id': 'cg-list-completed'},
            'error': None,
            'cancel_requested': False,
            'payload_data': {
                'topic': 'list-completed',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-list-expired',
            'tenant_id': 'test-tenant',
            'status': 'failed',
            'progress_pct': 100,
            'stage': 'failed',
            'created_at': '2025-01-01T00:00:00+00:00',
            'updated_at': '2025-01-01T00:00:00+00:00',
            'started_at': '2025-01-01T00:00:00+00:00',
            'completed_at': '2025-01-01T00:00:00+00:00',
            'result': None,
            'error': 'expired failed',
            'cancel_requested': False,
            'payload_data': {
                'topic': 'list-expired',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    listed = client.get('/content/generate/jobs?limit=10', headers=H)
    assert listed.status_code == 200
    payload = listed.json()
    assert payload['retention']['terminal_seconds'] == 120
    ids = {item['job_id'] for item in payload['items']}
    assert 'cgj-list-running' in ids
    assert 'cgj-list-completed' in ids
    assert 'cgj-list-expired' not in ids

    completed = client.get('/content/generate/jobs?status=completed', headers=H)
    assert completed.status_code == 200
    completed_items = completed.json()['items']
    assert len(completed_items) == 1
    assert completed_items[0]['job_id'] == 'cgj-list-completed'
    assert completed_items[0]['is_terminal'] is True
    assert isinstance(completed_items[0]['expires_at'], str)

    invalid = client.get('/content/generate/jobs?status=unknown_state', headers=H)
    assert invalid.status_code == 400


def test_async_content_generation_running_job_times_out_and_is_marked_failed(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_ENFORCE_JOB_TIMEOUTS', 'true')
    monkeypatch.setenv('CONTENT_GENERATION_JOB_MAX_RUNTIME_SECONDS', '60')
    lm._persist_content_generation_job(
        {
            'job_id': 'cgj-timeout-1',
            'tenant_id': 'test-tenant',
            'status': 'running',
            'progress_pct': 30,
            'stage': 'generating',
            'created_at': '2025-01-01T00:00:00+00:00',
            'updated_at': '2025-01-01T00:00:00+00:00',
            'started_at': '2025-01-01T00:00:00+00:00',
            'completed_at': None,
            'result': None,
            'error': None,
            'cancel_requested': False,
            'payload_data': {
                'topic': 'timeout me',
                'audience': 'ops',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
                'provider': 'auto',
                'target_formats': [],
            },
        }
    )

    poll = client.get('/content/generate/jobs/cgj-timeout-1', headers=H)
    assert poll.status_code == 200
    job = poll.json()['job']
    assert job['status'] == 'failed'
    assert job['stage'] == 'timeout'
    assert 'exceeded max runtime' in job['error'].lower()

    telemetry = client.get('/content/generate/telemetry', headers=H)
    assert telemetry.status_code == 200
    assert telemetry.json()['counters']['timeout_failures_total'] >= 1
