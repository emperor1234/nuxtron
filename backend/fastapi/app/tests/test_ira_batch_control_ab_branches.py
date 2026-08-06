from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key')


def _headers(tenant: str = 'ira-batch-control-tenant', include_super: bool = True) -> dict[str, str]:
    headers = {
        'X-API-Key': 'test-api-key',
        'X-Tenant-Id': tenant,
    }
    if include_super:
        headers['X-Super-Admin-Key'] = os.getenv('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key')
    return headers


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
            'tenant_id': 'ira-batch-control-tenant',
            'autonomy_enabled': True,
            'allow_high_impact_actions': True,
            'require_super_admin': True,
            'strict_policy_lock': True,
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


def test_actions_batch_skips_high_impact_without_human_validation(client: TestClient) -> None:
    r = client.post(
        '/ira/actions/batch',
        headers=_headers(),
        json={
            'actions': [
                {'target': 'admin', 'command': 'rotate-access-keys', 'payload': {'before_state': {'v': 1}}, 'dry_run': False},
                {'target': 'email', 'command': 'send-report', 'payload': {}, 'dry_run': False},
            ],
            'dry_run': False,
            'consent_reference': 'batch-consent-1',
            'human_validation_approved': False,
            'risk_analysis_approved': True,
        },
    )

    assert r.status_code == 200
    payload = r.json()
    assert payload['skipped'] == 1
    assert payload['executed'] == 1
    assert payload['results'][0]['status'] == 'skipped'
    assert 'human_validation_approved' in payload['results'][0]['reason']


def test_actions_batch_executes_high_impact_and_sends_notifications(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    with patch.dict(
        os.environ,
        {
            'RESEND_API_KEY': 'resend-key',
            'OPS_NOTIFICATION_EMAIL': 'ops@example.com',
            'SLACK_OPS_WEBHOOK_URL': 'https://slack.example/hook',
        },
        clear=False,
    ), patch('backend.fastapi.app.routers.ira.httpx.post') as http_post:
        r = client.post(
            '/ira/actions/batch',
            headers=_headers(),
            json={
                'actions': [
                    {'target': 'admin', 'command': 'set-maintenance-window', 'payload': {'before_state': {'mode': 'normal'}}, 'dry_run': False},
                    {'target': 'security', 'command': 'harden-policies', 'payload': {'before_state': {'level': 'medium'}}, 'dry_run': False},
                ],
                'dry_run': False,
                'consent_reference': 'batch-consent-2',
                'human_validation_approved': True,
                'risk_analysis_approved': True,
            },
        )

    assert r.status_code == 200
    payload = r.json()
    assert payload['executed'] == 2
    assert payload['skipped'] == 0
    assert payload['total_cost_pence'] == 4.0

    # Email + slack notification paths should both attempt delivery.
    assert http_post.call_count >= 2
    assert any(m.get('status') == 'sent' for m in memory_stores.resend_messages)
    assert any(m.get('status') == 'sent' for m in memory_stores.slack_messages)
    assert len(memory_stores.ira_action_snapshots) == 2


def test_actions_batch_rejects_when_autonomy_disabled(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    memory_stores.ira_controls[0]['autonomy_enabled'] = False

    r = client.post(
        '/ira/actions/batch',
        headers=_headers(),
        json={
            'actions': [{'target': 'email', 'command': 'noop', 'payload': {}, 'dry_run': True}],
            'dry_run': True,
            'consent_reference': 'batch-consent-3',
            'human_validation_approved': True,
            'risk_analysis_approved': True,
        },
    )

    assert r.status_code == 422
    assert 'autonomy' in r.json().get('detail', '').lower()


def test_control_config_strict_policy_lock_enforcements(client: TestClient) -> None:
    base_payload = {
        'autonomy_enabled': True,
        'allow_high_impact_actions': False,
        'min_profit_margin_pct': 70.0,
        'suspicious_signal_threshold': 0.75,
        'require_super_admin': True,
        'max_dispute_auto_resolution_gbp': 50.0,
        'strict_policy_lock': True,
        'policy_change_human_validation': True,
    }

    r1 = client.post('/ira/control/config', headers=_headers(), json={**base_payload, 'allow_high_impact_actions': True})
    assert r1.status_code == 422
    assert 'strict policy lock' in r1.json().get('detail', '').lower()

    r2 = client.post('/ira/control/config', headers=_headers(), json={**base_payload, 'require_super_admin': False})
    assert r2.status_code == 422
    assert 'strict policy lock' in r2.json().get('detail', '').lower()

    r3 = client.post('/ira/control/config', headers=_headers(), json={**base_payload, 'max_dispute_auto_resolution_gbp': 50.1})
    assert r3.status_code == 422
    assert 'less than or equal to 50' in str(r3.json().get('detail', '')).lower()


def test_ab_test_create_validation_paths(client: TestClient) -> None:
    invalid_len = client.post(
        '/ira/ab-tests',
        headers=_headers(),
        json={
            'name': 'split-length-mismatch',
            'variants': ['a', 'b'],
            'traffic_split': [1.0],
            'metric': 'conversion_rate',
        },
    )
    assert invalid_len.status_code == 422
    assert 'match variants length' in invalid_len.json().get('detail', '').lower()

    invalid_sum = client.post(
        '/ira/ab-tests',
        headers=_headers(),
        json={
            'name': 'split-sum-mismatch',
            'variants': ['a', 'b'],
            'traffic_split': [0.8, 0.8],
            'metric': 'conversion_rate',
        },
    )
    assert invalid_sum.status_code == 422
    assert 'must sum to 1.0' in invalid_sum.json().get('detail', '').lower()


def test_ab_test_record_rejects_non_running_or_unknown_variant(client: TestClient) -> None:
    created = client.post(
        '/ira/ab-tests',
        headers=_headers(),
        json={'name': 'record-paths', 'variants': ['a', 'b'], 'metric': 'conversion_rate'},
    )
    assert created.status_code == 200
    test_id = created.json()['test']['id']

    from backend.fastapi.app import memory_stores

    memory_stores.ira_ab_tests[0]['status'] = 'paused'
    paused = client.post(
        '/ira/ab-tests/record',
        headers=_headers(),
        json={'test_id': test_id, 'variant': 'a', 'outcome': 'success', 'value': 1.0, 'metadata': {}},
    )
    assert paused.status_code == 422
    assert 'not in running state' in paused.json().get('detail', '').lower()

    memory_stores.ira_ab_tests[0]['status'] = 'running'
    unknown_variant = client.post(
        '/ira/ab-tests/record',
        headers=_headers(),
        json={'test_id': test_id, 'variant': 'z', 'outcome': 'failure', 'value': 1.0, 'metadata': {}},
    )
    assert unknown_variant.status_code == 422
    assert 'not in test variants' in unknown_variant.json().get('detail', '').lower()


def test_agent_run_success_persists_job_and_event(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    r = client.post(
        '/ira/agent/run',
        headers=_headers(),
        json={
            'goal': 'stabilize onboarding funnel',
            'framework': 'auto',
            'max_iterations': 3,
            'dry_run': True,
            'memory_key': '',
        },
    )

    assert r.status_code == 200
    payload = r.json()
    assert payload['run']['run_id']
    assert payload['job']['job_type'] == 'agent_run'
    assert payload['job']['framework']
    assert any(e.get('event_type') == 'agent_run_completed' for e in memory_stores.ira_events)


def test_agent_run_rejects_when_autonomy_disabled(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    memory_stores.ira_controls[0]['autonomy_enabled'] = False

    r = client.post(
        '/ira/agent/run',
        headers=_headers(),
        json={
            'goal': 'run despite disabled autonomy',
            'framework': 'auto',
            'max_iterations': 2,
            'dry_run': True,
            'memory_key': '',
        },
    )

    assert r.status_code == 422
    assert 'autonomy' in r.json().get('detail', '').lower()


def test_fine_tuning_openai_missing_config_rejected(client: TestClient) -> None:
    with patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=False):
        missing_key = client.post(
            '/ira/ml/fine-tuning/jobs',
            headers=_headers(),
            json={
                'name': 'ft-missing-key',
                'provider': 'openai',
                'base_model': 'gpt-4o-mini',
                'training_file_id': 'file-1',
                'dry_run': False,
            },
        )

    assert missing_key.status_code == 422
    assert 'openai_api_key' in missing_key.json().get('detail', '').lower()

    with patch.dict(os.environ, {'OPENAI_API_KEY': 'ok-key'}, clear=False):
        missing_file = client.post(
            '/ira/ml/fine-tuning/jobs',
            headers=_headers(),
            json={
                'name': 'ft-missing-training-file',
                'provider': 'openai',
                'base_model': 'gpt-4o-mini',
                'training_file_id': '',
                'dry_run': False,
            },
        )

    assert missing_file.status_code == 422
    assert 'training_file_id' in missing_file.json().get('detail', '').lower()


def test_fine_tuning_openai_success_records_provider_job(client: TestClient) -> None:
    mock_response = type('Resp', (), {})()
    mock_response.headers = {'content-type': 'application/json'}
    mock_response.is_success = True
    mock_response.text = ''
    mock_response.json = lambda: {'id': 'ftjob-123', 'status': 'submitted'}

    with patch.dict(os.environ, {'OPENAI_API_KEY': 'ok-key'}, clear=False), patch(
        'backend.fastapi.app.routers.ira.httpx.Client'
    ) as client_cls:
        client_ctx = client_cls.return_value.__enter__.return_value
        client_ctx.post.return_value = mock_response

        r = client.post(
            '/ira/ml/fine-tuning/jobs',
            headers=_headers(),
            json={
                'name': 'ft-openai-success',
                'provider': 'openai',
                'base_model': 'gpt-4o-mini',
                'training_file_id': 'file-123',
                'validation_file_id': '',
                'suffix': 'tenant-tune',
                'hyperparameters': {'n_epochs': 1},
                'metadata': {'source': 'test'},
                'dry_run': False,
            },
        )

    assert r.status_code == 200
    payload = r.json()
    assert payload['job']['provider_job_id'] == 'ftjob-123'
    assert payload['job']['status'] == 'submitted'
