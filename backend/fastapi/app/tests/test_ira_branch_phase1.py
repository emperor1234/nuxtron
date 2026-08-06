from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key')


def _headers(tenant: str = 'ira-phase1-tenant') -> dict[str, str]:
    return {
        'X-API-Key': 'test-api-key',
        'X-Tenant-Id': tenant,
        'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key'),
    }


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from backend.fastapi.app import main as app_main
    from backend.fastapi.app import memory_stores
    from backend.fastapi.app.main import app

    for value in vars(memory_stores).values():
        if isinstance(value, list):
            value.clear()
    app_main.reset_rate_limits_for_tests()

    memory_stores.ira_controls.append(
        {
            'id': 1,
            'tenant_id': 'ira-phase1-tenant',
            'autonomy_enabled': True,
            'allow_high_impact_actions': True,
            'require_super_admin': True,
            'strict_policy_lock': False,
            'min_profit_margin_pct': 70.0,
            'suspicious_signal_threshold': 0.75,
            'max_dispute_auto_resolution_gbp': 50.0,
            'protection_mode': False,
            'blocked_actions': [],
            'updated_at': '2025-01-01T00:00:00+00:00',
        }
    )

    yield TestClient(app, raise_server_exceptions=False)

    for value in vars(memory_stores).values():
        if isinstance(value, list):
            value.clear()
    app_main.reset_rate_limits_for_tests()


def test_frontier_stack_readiness_state_branches(client: TestClient) -> None:
    with patch('backend.fastapi.app.routers.ira._module_available', return_value=True), patch.dict(
        os.environ,
        {
            'OPENAI_API_KEY': '1',
            'ANTHROPIC_API_KEY': '1',
            'COHERE_API_KEY': '1',
            'GOOGLE_VERTEX_API_KEY': '1',
            'PINECONE_API_KEY': '1',
            'WEAVIATE_URL': 'http://w',
            'REDIS_HOST': '127.0.0.1',
            'NEO4J_URI': 'bolt://n',
            'CLOUDFLARE_API_TOKEN': '1',
            'CLOUDFLARE_ZONE_ID': '1',
            'VERCEL_TOKEN': '1',
            'VERCEL_PROJECT_ID': '1',
            'FLY_API_TOKEN': '1',
            'FLY_APP_NAME': '1',
            'UPSTASH_REDIS_REST_URL': '1',
            'UPSTASH_REDIS_REST_TOKEN': '1',
            'POSTHOG_PROJECT_API_KEY': '1',
            'SENTRY_DSN': '1',
            'LANGSMITH_API_KEY': '1',
            'LANGFUSE_PUBLIC_KEY': '1',
            'LANGFUSE_SECRET_KEY': '1',
            'GRAFANA_URL': '1',
            'GRAFANA_API_KEY': '1',
            'FIRECRAWL_API_KEY': '1',
            'AGENTOPS_API_KEY': '1',
            'NEXT_PUBLIC_ENABLE_MILLION': '1',
            'NEXT_PUBLIC_ENABLE_PARTYTOWN': '1',
            'NEXT_PUBLIC_ENABLE_ZUSTAND': '1',
            'API_BFF_FRAMEWORK': 'hono',
            'API_TRANSPORT': 'trpc',
            'DATABASE_ORM': 'drizzle',
            'API_SCHEMA_VALIDATION': 'zod',
        },
        clear=False,
    ):
        high = client.get('/ira/frontier/stack', headers=_headers())
        assert high.status_code == 200
        assert high.json()['readiness']['state'] in ('medium', 'high')

    with patch('backend.fastapi.app.routers.ira._module_available', return_value=False), patch.dict(
        os.environ,
        {
            'OPENAI_API_KEY': '1',
            'PINECONE_API_KEY': '1',
            'REDIS_HOST': '127.0.0.1',
            'SENTRY_DSN': '1',
            'LANGSMITH_API_KEY': '1',
        },
        clear=False,
    ):
        medium = client.get('/ira/frontier/stack', headers=_headers())
        assert medium.status_code == 200
        assert medium.json()['readiness']['state'] in ('low', 'medium', 'high')


def test_chat_history_short_confirm_billing_branch(client: TestClient) -> None:
    first = client.post(
        '/ira/chat',
        headers=_headers(),
        json={'role': 'operator', 'channel': 'chat', 'message': 'Need invoice dispute and refund credit review', 'context': {}},
    )
    assert first.status_code == 200

    second = client.post(
        '/ira/chat',
        headers=_headers(),
        json={'role': 'operator', 'channel': 'chat', 'message': 'yes', 'context': {}},
    )
    assert second.status_code == 200
    assert 'Billing workflow selected' in second.json()['ira']['response']


def test_chat_explicit_ads_and_social_branches(client: TestClient) -> None:
    ads = client.post(
        '/ira/chat',
        headers=_headers('ira-phase1-tenant-ads'),
        json={'role': 'operator', 'channel': 'chat', 'message': 'Need paid campaign CAC and ROAS optimization', 'context': {}},
    )
    assert ads.status_code == 200
    assert 'Ads workflow selected' in ads.json()['ira']['response']

    social = client.post(
        '/ira/chat',
        headers=_headers('ira-phase1-tenant-social'),
        json={'role': 'operator', 'channel': 'chat', 'message': 'Create social post and content calendar for tiktok', 'context': {}},
    )
    assert social.status_code == 200
    assert 'Social workflow selected' in social.json()['ira']['response']


def test_actions_delivery_direct_return_paths(client: TestClient) -> None:
    with patch(
        'backend.fastapi.app.routers.ira.dispatch_via_ira_connector',
        return_value={'provider': 'mock', 'delivery_status': 'sent', 'channel': '#ops'},
    ):
        email = client.post(
            '/ira/actions',
            headers=_headers('ira-phase1-tenant-email'),
            json={
                'target': 'email',
                'command': 'send update',
                'payload': {'to': 'ops@nuxtron.local', 'subject': 'S', 'body': 'B'},
                'dry_run': False,
                'user_consent': True,
                'consent_reference': 'consent-e',
                'risk_analysis_approved': True,
                'human_validation_approved': True,
                'explicit_approval': True,
            },
        )
        assert email.status_code == 200
        assert email.json()['result']['provider_result']['delivery_status'] == 'sent'

        upsert = client.post(
            '/ira/connectors/upsert',
            headers=_headers('ira-phase1-tenant-whatsapp'),
            json={'channel': 'customer_support', 'enabled': True, 'provider': 'twilio_whatsapp', 'config': {}},
        )
        assert upsert.status_code == 200

        whatsapp = client.post(
            '/ira/actions',
            headers=_headers('ira-phase1-tenant-whatsapp'),
            json={
                'target': 'customer_support',
                'command': 'support update',
                'payload': {'to': '+10000000000', 'message': 'hello'},
                'dry_run': False,
                'user_consent': True,
                'consent_reference': 'consent-w',
                'risk_analysis_approved': True,
                'human_validation_approved': True,
                'explicit_approval': True,
            },
        )
        assert whatsapp.status_code == 200
        assert whatsapp.json()['result']['provider_result']['delivery_status'] == 'sent'


def test_finetuning_openai_and_custom_success_paths(client: TestClient) -> None:
    response_mock = MagicMock()
    response_mock.headers = {'content-type': 'application/json'}
    response_mock.is_success = True
    response_mock.json.return_value = {'id': 'ftjob-123', 'status': 'submitted'}

    client_mock = MagicMock()
    client_mock.__enter__.return_value.post.return_value = response_mock
    client_mock.__exit__.return_value = False

    with patch('backend.fastapi.app.routers.ira.httpx.Client', return_value=client_mock), patch.dict(
        os.environ,
        {'OPENAI_API_KEY': 'sk-test', 'IRA_CUSTOM_FINETUNE_ENDPOINT': 'https://example.com/ft'},
        clear=False,
    ):
        openai_job = client.post(
            '/ira/ml/fine-tuning/jobs',
            headers=_headers('ira-phase1-tenant-ft-openai'),
            json={
                'provider': 'openai',
                'base_model': 'gpt-4o-mini',
                'training_file_id': 'file-abc',
                'dry_run': False,
            },
        )
        assert openai_job.status_code == 200
        assert openai_job.json()['job']['provider_job_id'] == 'ftjob-123'

        custom_job = client.post(
            '/ira/ml/fine-tuning/jobs',
            headers=_headers('ira-phase1-tenant-ft-custom'),
            json={
                'provider': 'custom_http',
                'base_model': 'local-model',
                'training_file_id': 'file-local',
                'endpoint_url': 'https://example.com/ft-custom',
                'dry_run': False,
            },
        )
        assert custom_job.status_code == 200
        assert custom_job.json()['job']['provider'] == 'custom_http'


def test_ml_pipeline_queued_and_waiting_runtime(client: TestClient) -> None:
    queued = client.post(
        '/ira/ml/pipelines',
        headers=_headers('ira-phase1-tenant-pipeline-q'),
        json={
            'name': 'Pipeline Q',
            'objective': 'Queue with available runtime',
            'pipeline_type': 'rag',
            'framework': 'sentence_transformers',
            'dry_run': False,
        },
    )
    assert queued.status_code == 200
    assert queued.json()['job']['status'] in ('queued', 'waiting_for_runtime')

    waiting = client.post(
        '/ira/ml/pipelines',
        headers=_headers('ira-phase1-tenant-pipeline-w'),
        json={
            'name': 'Pipeline W',
            'objective': 'Wait for missing runtime',
            'pipeline_type': 'fine_tuning',
            'framework': 'tensorflow',
            'dry_run': False,
        },
    )
    assert waiting.status_code == 200
    assert waiting.json()['job']['status'] in ('queued', 'waiting_for_runtime')