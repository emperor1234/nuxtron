from __future__ import annotations

import os

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')


import pytest
from fastapi.testclient import TestClient

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'test-tenant'}


@pytest.fixture(autouse=True)
def _reset_content_generation_state(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    lm._ai_generated_assets_memory.clear()
    lm._content_generations_memory.clear()
    lm._content_generation_jobs_memory.clear()
    with lm._content_generation_telemetry_lock:
        lm._content_generation_telemetry['strict_rejections_total'] = 0
        lm._content_generation_telemetry['strict_rejections_by_reason'] = {}
        lm._content_generation_telemetry['fallback_attempts_total'] = 0
        lm._content_generation_telemetry['fallback_attempts_by_reason'] = {}
        lm._content_generation_telemetry['timeout_failures_total'] = 0
        lm._content_generation_telemetry['updated_at'] = None
    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    monkeypatch.setattr(
        lm,
        '_run_optional_ai_generation',
        lambda payload, auth, created_at: (
            'openai',
            'gpt-4o-mini',
            {'provider': 'openai', 'model': 'gpt-4o-mini', 'output_text': 'Generated copy', 'usage': {}, 'latency_ms': 12},
            'Generated copy',
        ),
    )
    monkeypatch.setattr(
        lm,
        '_generate_media_asset_bundle',
        lambda **kwargs: {
            'image': {
                'id': 1,
                'kind': 'image',
                'mime_type': 'image/png',
                'file_name': 'image-1.png',
                'download_url': '/ai/generated-assets/1',
                'generation_status': 'generated',
                'provider_used': 'stability_ai',
                'size_bytes': 128,
            },
            'voice': {
                'id': 2,
                'kind': 'voice',
                'mime_type': 'audio/wav',
                'file_name': 'voice-2.wav',
                'download_url': '/ai/generated-assets/2',
                'generation_status': 'fallback',
                'provider_used': 'fallback',
                'size_bytes': 128,
            },
            'video': {
                'id': 3,
                'kind': 'video',
                'mime_type': 'image/gif',
                'file_name': 'video-3.gif',
                'download_url': '/ai/generated-assets/3',
                'generation_status': 'fallback',
                'provider_used': 'fallback',
                'size_bytes': 64,
            },
        },
    )


@pytest.fixture()
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_content_generation_history_is_persisted_and_listed(client: TestClient) -> None:
    response = client.post(
        '/content/generate',
        headers=H,
        json={
            'topic': 'AI automation',
            'audience': 'Growth teams',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    generation_id = payload['generation_id']
    assert generation_id.startswith('cg-')
    assert payload['generation_record']['headline']
    assert payload['generated_assets']['image']['download_url'] == '/ai/generated-assets/1'

    library_response = client.get('/content/library', headers=H)
    assert library_response.status_code == 200
    library = library_response.json()
    assert library['count'] == 1
    assert library['items'][0]['generation_id'] == generation_id
    assert library['items'][0]['topic'] == 'AI automation'

    single_response = client.get(f'/content/library/{generation_id}', headers=H)
    assert single_response.status_code == 200
    assert single_response.json()['item']['generation_id'] == generation_id


def test_content_generation_strict_mode_rejects_fallback_media(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'true')

    response = client.post(
        '/content/generate',
        headers=H,
        json={
            'topic': 'AI automation',
            'audience': 'Growth teams',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )

    assert response.status_code == 503
    assert 'Strict content generation mode' in response.json()['detail']

    telemetry = client.get('/content/generate/telemetry', headers=H)
    assert telemetry.status_code == 200
    counters = telemetry.json()['counters']
    assert counters['strict_rejections_total'] >= 1
    assert counters['strict_rejections_by_reason'].get('media_fallback', 0) >= 1


def test_content_generation_strict_mode_rejects_missing_ai_text(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'true')
    monkeypatch.setattr(
        lm,
        '_run_optional_ai_generation',
        lambda payload, auth, created_at: ('openai', 'gpt-4o-mini', {'provider': 'openai', 'model': 'gpt-4o-mini'}, ''),
    )
    monkeypatch.setattr(
        lm,
        '_generate_media_asset_bundle',
        lambda **kwargs: {
            'image': {
                'id': 1,
                'kind': 'image',
                'mime_type': 'image/png',
                'file_name': 'image-1.png',
                'download_url': '/ai/generated-assets/1',
                'generation_status': 'generated',
                'provider_used': 'stability_ai',
                'size_bytes': 128,
            },
            'voice': {
                'id': 2,
                'kind': 'voice',
                'mime_type': 'audio/wav',
                'file_name': 'voice-2.wav',
                'download_url': '/ai/generated-assets/2',
                'generation_status': 'generated',
                'provider_used': 'elevenlabs',
                'size_bytes': 128,
            },
            'video': {
                'id': 3,
                'kind': 'video',
                'mime_type': 'video/mp4',
                'file_name': 'video-3.mp4',
                'download_url': '/ai/generated-assets/3',
                'generation_status': 'generated',
                'provider_used': 'replicate',
                'size_bytes': 128,
            },
        },
    )

    response = client.post(
        '/content/generate',
        headers=H,
        json={
            'topic': 'AI automation',
            'audience': 'Growth teams',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )

    assert response.status_code == 503
    assert 'AI text generation returned no output' in response.json()['detail']


def test_content_generation_strict_mode_all_generated_succeeds(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'true')
    monkeypatch.setattr(
        lm,
        '_generate_media_asset_bundle',
        lambda **kwargs: {
            'image': {
                'id': 1,
                'kind': 'image',
                'mime_type': 'image/png',
                'file_name': 'image-1.png',
                'download_url': '/ai/generated-assets/1',
                'generation_status': 'generated',
                'provider_used': 'stability_ai',
                'size_bytes': 128,
            },
            'voice': {
                'id': 2,
                'kind': 'voice',
                'mime_type': 'audio/wav',
                'file_name': 'voice-2.wav',
                'download_url': '/ai/generated-assets/2',
                'generation_status': 'generated',
                'provider_used': 'elevenlabs',
                'size_bytes': 128,
            },
            'video': {
                'id': 3,
                'kind': 'video',
                'mime_type': 'video/mp4',
                'file_name': 'video-3.mp4',
                'download_url': '/ai/generated-assets/3',
                'generation_status': 'generated',
                'provider_used': 'replicate',
                'size_bytes': 128,
            },
        },
    )

    response = client.post(
        '/content/generate',
        headers=H,
        json={
            'topic': 'AI automation',
            'audience': 'Growth teams',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['production_mode'] == 'strict-real-generation'


def test_content_generation_provider_readiness_reports_missing_modalities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setattr(lm, '_resolve_provider_api_key', lambda provider: '')
    monkeypatch.setenv('ELEVENLABS_API_KEY', '')
    monkeypatch.setenv('REPLICATE_API_TOKEN', '')
    monkeypatch.setenv('GOOGLE_VERTEX_PROJECT_ID', '')
    monkeypatch.setenv('CONTENT_GENERATION_ALLOW_OSS_VOICE_IN_STRICT', 'false')

    ready, checks = lm._content_generation_required_provider_state()
    assert ready is False
    assert checks['text'] is False
    assert checks['image'] is False
    assert checks['voice'] is False
    assert checks['video'] is False


def test_content_generation_telemetry_tracks_fallback_attempts(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'false')

    response = client.post(
        '/content/generate',
        headers=H,
        json={
            'topic': 'AI automation',
            'audience': 'Growth teams',
            'channel': 'linkedin',
            'tone': 'professional',
            'include_seo': True,
        },
    )
    assert response.status_code == 200

    telemetry = client.get('/content/generate/telemetry', headers=H)
    assert telemetry.status_code == 200
    counters = telemetry.json()['counters']
    assert counters['fallback_attempts_total'] >= 2
    assert counters['fallback_attempts_by_reason'].get('media_fallback', 0) >= 2


def test_content_generation_strict_preflight_returns_503_when_not_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'true')
    monkeypatch.setattr(lm, '_resolve_provider_api_key', lambda provider: '')
    monkeypatch.setenv('ELEVENLABS_API_KEY', '')
    monkeypatch.setenv('REPLICATE_API_TOKEN', '')
    monkeypatch.setenv('GOOGLE_VERTEX_PROJECT_ID', '')
    monkeypatch.setenv('CONTENT_GENERATION_ALLOW_OSS_VOICE_IN_STRICT', 'false')

    response = client.get('/content/generate/preflight/strict', headers=H)
    assert response.status_code == 503
    payload = response.json()
    assert payload['strict_mode_enabled'] is True
    assert payload['ready'] is False


def test_content_generation_strict_preflight_returns_200_when_strict_disabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'false')
    monkeypatch.setattr(lm, '_resolve_provider_api_key', lambda provider: '')
    monkeypatch.setenv('ELEVENLABS_API_KEY', '')
    monkeypatch.setenv('REPLICATE_API_TOKEN', '')
    monkeypatch.setenv('GOOGLE_VERTEX_PROJECT_ID', '')

    response = client.get('/content/generate/preflight/strict', headers=H)
    assert response.status_code == 200
    payload = response.json()
    assert payload['strict_mode_enabled'] is False


def test_content_generation_strict_mode_defaults_on_in_production_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.delenv('CONTENT_GENERATION_STRICT_PRODUCTION', raising=False)
    monkeypatch.setenv('ENVIRONMENT', 'production')
    assert lm._content_generation_strict_production_mode() is True


def test_content_generation_production_verify_passes_with_strict_ready_and_no_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'true')
    monkeypatch.setattr(
        lm,
        '_content_generation_required_provider_state',
        lambda: (True, {'text': True, 'image': True, 'voice': True, 'video': True}),
    )
    with lm._content_generation_telemetry_lock:
        lm._content_generation_telemetry['strict_rejections_total'] = 0
        lm._content_generation_telemetry['strict_rejections_by_reason'] = {}
        lm._content_generation_telemetry['fallback_attempts_total'] = 0
        lm._content_generation_telemetry['fallback_attempts_by_reason'] = {}

    response = client.get('/content/generate/production/verify', headers=H)
    assert response.status_code == 200
    payload = response.json()
    assert payload['verification']['passed'] is True


def test_content_generation_production_verify_fails_when_fallback_attempts_present(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'true')
    monkeypatch.setattr(
        lm,
        '_content_generation_required_provider_state',
        lambda: (True, {'text': True, 'image': True, 'voice': True, 'video': True}),
    )
    with lm._content_generation_telemetry_lock:
        lm._content_generation_telemetry['strict_rejections_total'] = 0
        lm._content_generation_telemetry['strict_rejections_by_reason'] = {}
        lm._content_generation_telemetry['fallback_attempts_total'] = 2
        lm._content_generation_telemetry['fallback_attempts_by_reason'] = {'media_fallback': 2}

    response = client.get('/content/generate/production/verify', headers=H)
    assert response.status_code == 503
    payload = response.json()
    assert payload['verification']['passed'] is False


def test_content_generation_production_verify_fails_when_timeout_failures_present(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('CONTENT_GENERATION_STRICT_PRODUCTION', 'true')
    monkeypatch.setattr(
        lm,
        '_content_generation_required_provider_state',
        lambda: (True, {'text': True, 'image': True, 'voice': True, 'video': True}),
    )
    with lm._content_generation_telemetry_lock:
        lm._content_generation_telemetry['strict_rejections_total'] = 0
        lm._content_generation_telemetry['strict_rejections_by_reason'] = {}
        lm._content_generation_telemetry['fallback_attempts_total'] = 0
        lm._content_generation_telemetry['fallback_attempts_by_reason'] = {}
        lm._content_generation_telemetry['timeout_failures_total'] = 1

    response = client.get('/content/generate/production/verify', headers=H)
    assert response.status_code == 503
    payload = response.json()
    assert payload['verification']['passed'] is False


def test_strict_no_mock_production_verify_passes_when_all_criteria_satisfied(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('NUXTRON_STRICT_NO_MOCK', 'true')
    monkeypatch.setattr(
        lm,
        '_content_generation_production_verification_payload',
        lambda tenant_id: ({'status': 'ok', 'verification': {'passed': True}}, True),
    )
    monkeypatch.setattr(
        lm,
        '_platform_status_payload',
        lambda auth: {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'db_ready': True,
            'fallback_buffers': {
                'sizes': {'scheduled_posts': 0, 'email_contacts': 0},
                'hot_buffers': [],
                'any_buffer_hot': False,
            },
        },
    )
    monkeypatch.setattr(
        lm,
        '_strict_no_mock_module_store_counts',
        lambda tenant_id: {
            'scheduled_posts': 0,
            'social_accounts': 0,
            'smart_inbox_messages': 0,
            'content_approval_requests': 0,
            'social_listening': 0,
            'reviews': 0,
            'influencers': 0,
            'advocacy_campaigns': 0,
            'linkinbio_pages': 0,
            'ads_campaigns': 0,
            'trend_signals': 0,
        },
    )

    response = client.get('/production/no-mock/verify', headers=H)
    assert response.status_code == 200
    payload = response.json()
    assert payload['verification']['passed'] is True
    assert payload['strict_no_mock_mode_enabled'] is True
    assert payload['strict_no_mock_mode'] is True
    assert payload['fallback_blocked'] is False
    assert payload['source'] == 'verify'
    assert payload['route_family'] == 'platform'
    critical_buffers = payload['platform']['critical_module_buffers']
    class_breakdown = critical_buffers['class_breakdown']
    assert sorted(class_breakdown.keys()) == ['content_pipeline', 'distribution_surface', 'social_operations']
    assert class_breakdown['content_pipeline']['total'] == 0
    assert class_breakdown['social_operations']['total'] == 0
    assert class_breakdown['distribution_surface']['total'] == 0
    assert critical_buffers['class_overflow'] == {}


def test_strict_no_mock_production_verify_fails_when_fallback_buffers_have_items(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('NUXTRON_STRICT_NO_MOCK', 'true')
    monkeypatch.setattr(
        lm,
        '_content_generation_production_verification_payload',
        lambda tenant_id: ({'status': 'ok', 'verification': {'passed': True}}, True),
    )
    monkeypatch.setattr(
        lm,
        '_platform_status_payload',
        lambda auth: {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'db_ready': True,
            'fallback_buffers': {
                'sizes': {'scheduled_posts': 2, 'email_contacts': 0},
                'hot_buffers': ['scheduled_posts'],
                'any_buffer_hot': True,
            },
        },
    )
    monkeypatch.setattr(
        lm,
        '_strict_no_mock_module_store_counts',
        lambda tenant_id: {
            'scheduled_posts': 0,
            'social_accounts': 0,
            'smart_inbox_messages': 0,
            'content_approval_requests': 0,
            'social_listening': 0,
            'reviews': 0,
            'influencers': 0,
            'advocacy_campaigns': 0,
            'linkinbio_pages': 0,
            'ads_campaigns': 0,
            'trend_signals': 0,
        },
    )

    response = client.get('/production/no-mock/verify', headers=H)
    assert response.status_code == 503
    payload = response.json()
    assert payload['verification']['passed'] is False
    assert payload['fallback_blocked'] is True
    assert payload['source'] == 'fallback-buffers'
    assert payload['route_family'] == 'fallback-buffers'


def test_strict_no_mock_production_verify_fails_when_critical_module_buffers_exceed_limit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('NUXTRON_STRICT_NO_MOCK', 'true')
    monkeypatch.setenv('NUXTRON_STRICT_NO_MOCK_MAX_MODULE_BUFFER_ITEMS', '0')
    monkeypatch.setattr(
        lm,
        '_content_generation_production_verification_payload',
        lambda tenant_id: ({'status': 'ok', 'verification': {'passed': True}}, True),
    )
    monkeypatch.setattr(
        lm,
        '_platform_status_payload',
        lambda auth: {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'db_ready': True,
            'fallback_buffers': {
                'sizes': {'scheduled_posts': 0, 'email_contacts': 0},
                'hot_buffers': [],
                'any_buffer_hot': False,
            },
        },
    )
    monkeypatch.setattr(
        lm,
        '_strict_no_mock_module_store_counts',
        lambda tenant_id: {
            'scheduled_posts': 1,
            'social_accounts': 0,
            'smart_inbox_messages': 0,
            'content_approval_requests': 0,
            'social_listening': 0,
            'reviews': 0,
            'influencers': 0,
            'advocacy_campaigns': 0,
            'linkinbio_pages': 0,
            'ads_campaigns': 0,
            'trend_signals': 0,
        },
    )

    response = client.get('/production/no-mock/verify', headers=H)
    assert response.status_code == 503
    payload = response.json()
    assert payload['verification']['passed'] is False
    assert payload['fallback_blocked'] is True
    assert payload['source'] == 'critical-modules'
    assert payload['route_family'] == 'critical-modules'
    criteria = payload['verification']['criteria']
    module_criterion = next(item for item in criteria if item['id'] == 'critical-module-buffers-below-limit')
    assert module_criterion['pass'] is False
    class_overflow = module_criterion['details']['class_overflow']
    assert 'content_pipeline' in class_overflow
    assert class_overflow['content_pipeline']['total'] == 1


def test_strict_no_mock_verify_defaults_to_enabled_in_production(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.delenv('NUXTRON_STRICT_NO_MOCK', raising=False)
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setattr(
        lm,
        '_content_generation_production_verification_payload',
        lambda tenant_id: ({'status': 'ok', 'verification': {'passed': True}}, True),
    )
    monkeypatch.setattr(
        lm,
        '_platform_status_payload',
        lambda auth: {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'db_ready': True,
            'fallback_buffers': {
                'sizes': {'scheduled_posts': 2, 'email_contacts': 0},
                'hot_buffers': ['scheduled_posts'],
                'any_buffer_hot': True,
            },
        },
    )
    monkeypatch.setattr(
        lm,
        '_strict_no_mock_module_store_counts',
        lambda tenant_id: {
            'scheduled_posts': 0,
            'social_accounts': 0,
            'smart_inbox_messages': 0,
            'content_approval_requests': 0,
            'social_listening': 0,
            'reviews': 0,
            'influencers': 0,
            'advocacy_campaigns': 0,
            'linkinbio_pages': 0,
            'ads_campaigns': 0,
            'trend_signals': 0,
        },
    )

    response = client.get('/production/no-mock/verify', headers=H)
    assert response.status_code == 503
    payload = response.json()
    assert payload['strict_no_mock_mode_enabled'] is True
    assert payload['strict_no_mock_mode'] is True
    assert payload['fallback_blocked'] is True


def test_strict_no_mock_verify_allows_explicit_disable_in_production(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setenv('NUXTRON_STRICT_NO_MOCK', 'false')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setattr(
        lm,
        '_content_generation_production_verification_payload',
        lambda tenant_id: ({'status': 'ok', 'verification': {'passed': True}}, True),
    )
    monkeypatch.setattr(
        lm,
        '_platform_status_payload',
        lambda auth: {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'db_ready': True,
            'fallback_buffers': {
                'sizes': {'scheduled_posts': 2, 'email_contacts': 0},
                'hot_buffers': ['scheduled_posts'],
                'any_buffer_hot': True,
            },
        },
    )
    monkeypatch.setattr(
        lm,
        '_strict_no_mock_module_store_counts',
        lambda tenant_id: {
            'scheduled_posts': 0,
            'social_accounts': 0,
            'smart_inbox_messages': 0,
            'content_approval_requests': 0,
            'social_listening': 0,
            'reviews': 0,
            'influencers': 0,
            'advocacy_campaigns': 0,
            'linkinbio_pages': 0,
            'ads_campaigns': 0,
            'trend_signals': 0,
        },
    )

    response = client.get('/production/no-mock/verify', headers=H)
    assert response.status_code == 200
    payload = response.json()
    assert payload['strict_no_mock_mode_enabled'] is False
    assert payload['strict_no_mock_mode'] is False
    assert payload['fallback_blocked'] is True
