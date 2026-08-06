from __future__ import annotations

import builtins
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key')


def _headers(*, tenant: str = 'test-tenant-ira-branch') -> dict[str, str]:
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

    # Reset all in-memory lists so each test is deterministic.
    for value in vars(memory_stores).values():
        if isinstance(value, list):
            value.clear()

    app_main.reset_rate_limits_for_tests()
    memory_stores.ira_controls.append(
        {
            'id': 1,
            'tenant_id': 'test-tenant-ira-branch',
            'autonomy_enabled': True,
            'allow_high_impact_actions': True,
            'min_profit_margin_pct': 70.0,
            'suspicious_signal_threshold': 0.75,
            'require_super_admin': True,
            'max_dispute_auto_resolution_gbp': 50.0,
            'strict_policy_lock': False,
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


def test_frontier_apply_draft_merge_and_backup_success(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / '.env.frontier-branch'
    target.write_text('OPENAI_MODEL=\nANTHROPIC_MODEL=custom\nCUSTOM_KEY=locked\n', encoding='utf-8')

    with patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy', 'ANTHROPIC_API_KEY': 'dummy'}, clear=False):
        res = client.post(
            '/ira/frontier/env-template/apply-draft',
            headers=_headers(),
            json={'target_file': '.env.frontier-branch', 'mode': 'merge_and_backup'},
        )

    assert res.status_code == 200
    payload = res.json()
    assert payload['mode'] == 'merge_and_backup'
    assert payload['merge_stats']['kept_existing_non_empty'] >= 0
    assert payload['merge_stats']['appended_missing'] >= 1
    assert payload['backup_path']
    assert Path(payload['backup_path']).exists()


def test_frontier_apply_draft_existing_file_read_error_500(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / '.env.read-error'
    target.write_text('OPENAI_MODEL=\n', encoding='utf-8')
    target_abs = str(target.resolve())
    original_open = builtins.open

    def _open_with_read_error(file: Any, mode: str = 'r', *args: Any, **kwargs: Any):
        if str(file) == target_abs and 'r' in mode:
            raise OSError('boom-read')
        return original_open(file, mode, *args, **kwargs)

    with patch('builtins.open', side_effect=_open_with_read_error):
        res = client.post(
            '/ira/frontier/env-template/apply-draft',
            headers=_headers(),
            json={'target_file': '.env.read-error', 'mode': 'merge_non_destructive'},
        )

    assert res.status_code == 500
    assert 'Failed reading existing env file' in res.json().get('detail', '')


def test_frontier_apply_draft_target_file_validation_422(client: TestClient) -> None:
    res = client.post(
        '/ira/frontier/env-template/apply-draft',
        headers=_headers(),
        json={'target_file': 'not_env.txt', 'mode': 'overwrite'},
    )

    assert res.status_code == 422
    assert 'target_file must start with .env' in res.json().get('detail', '')


def test_ml_overview_aggregates_document_chunks(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    memory_stores.ira_ml_knowledge.extend(
        [
            {
                'id': 1,
                'tenant_id': 'test-tenant-ira-branch',
                'document_id': 'doc-a',
                'title': 'Doc A',
                'source': 'unit',
                'tags': ['a'],
                'embedding_backend': 'local_hash',
                'created_at': '2025-01-01T00:00:00+00:00',
                'updated_at': '2025-01-01T00:00:00+00:00',
            },
            {
                'id': 2,
                'tenant_id': 'test-tenant-ira-branch',
                'document_id': 'doc-a',
                'title': 'Doc A',
                'source': 'unit',
                'tags': ['a'],
                'embedding_backend': 'local_hash',
                'created_at': '2025-01-01T00:00:01+00:00',
                'updated_at': '2025-01-01T00:00:01+00:00',
            },
            {
                'id': 3,
                'tenant_id': 'test-tenant-ira-branch',
                'document_id': '   ',
                'title': 'Should Skip',
                'source': 'unit',
                'tags': [],
                'embedding_backend': 'local_hash',
                'created_at': '2025-01-01T00:00:02+00:00',
                'updated_at': '2025-01-01T00:00:02+00:00',
            },
        ]
    )

    res = client.get('/ira/ml/overview', headers=_headers())
    assert res.status_code == 200
    documents = res.json()['documents']
    assert len(documents) == 1
    assert documents[0]['document_id'] == 'doc-a'
    assert documents[0]['chunk_count'] == 2


def test_agent_frameworks_reads_tenant_memory_override(client: TestClient) -> None:
    upsert_res = client.post(
        '/ira/memory/structured/upsert',
        headers=_headers(),
        json={
            'memory_type': 'preference',
            'memory_key': 'agent_framework_auto',
            'payload': {'framework': 'semantic_kernel'},
        },
    )
    assert upsert_res.status_code == 200

    res = client.get('/ira/agent/frameworks', headers=_headers())
    assert res.status_code == 200
    assert res.json()['auto_policy']['tenant_override'] == 'semantic_kernel'


def test_chat_short_confirmation_uses_security_history(client: TestClient) -> None:
    first = client.post(
        '/ira/chat',
        headers=_headers(),
        json={'role': 'operator', 'channel': 'chat', 'message': 'Security incident breach detected in SIEM logs', 'context': {}},
    )
    assert first.status_code == 200

    second = client.post(
        '/ira/chat',
        headers=_headers(),
        json={'role': 'operator', 'channel': 'chat', 'message': 'yes', 'context': {}},
    )
    assert second.status_code == 200

    response_text = second.json()['ira']['response']
    assert 'Security workflow selected' in response_text


def test_actions_delivery_paths_queue_results(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    connector_result = {
        'provider': 'mock-provider',
        'delivery_status': 'queued',
        'channel': '#ops',
    }
    with patch('backend.fastapi.app.routers.ira.dispatch_via_ira_connector', return_value=connector_result):
        chat_connector = client.post(
            '/ira/connectors/upsert',
            headers=_headers(),
            json={'channel': 'chat', 'enabled': True, 'provider': 'slack', 'config': {}},
        )
        assert chat_connector.status_code == 200

        email = client.post(
            '/ira/actions',
            headers=_headers(),
            json={
                'target': 'email',
                'command': 'send customer update',
                'payload': {'to': 'ops@nuxtron.local', 'subject': 'S', 'body': 'B'},
                'dry_run': False,
                'user_consent': True,
                'consent_reference': 'consent-001',
                'risk_analysis_approved': True,
                'human_validation_approved': True,
                'explicit_approval': True,
            },
        )
        chats = client.post(
            '/ira/actions',
            headers=_headers(),
            json={
                'target': 'chats',
                'command': 'broadcast campaign update',
                'payload': {'message': 'hello'},
                'dry_run': False,
                'user_consent': True,
                'consent_reference': 'consent-002',
                'risk_analysis_approved': True,
                'human_validation_approved': True,
                'explicit_approval': True,
            },
        )

        # Force customer_support path to use WhatsApp delivery branch.
        client.post(
            '/ira/connectors/upsert',
            headers=_headers(),
            json={'channel': 'customer_support', 'enabled': True, 'provider': 'twilio_whatsapp', 'config': {}},
        )
        support = client.post(
            '/ira/actions',
            headers=_headers(),
            json={
                'target': 'customer_support',
                'command': 'support follow up',
                'payload': {'to': '+10000000000', 'message': 'm'},
                'dry_run': False,
                'user_consent': True,
                'consent_reference': 'consent-003',
                'risk_analysis_approved': True,
                'human_validation_approved': True,
                'explicit_approval': True,
            },
        )

    assert email.status_code == 200
    assert chats.status_code == 200
    assert support.status_code == 200
    assert email.json()['result']['provider_result']['message_id'] >= 1
    assert chats.json()['result']['provider_result']['message_id'] >= 1
    assert support.json()['result']['provider_result']['message_id'] >= 1
    assert len(memory_stores.resend_messages) == 1
    assert len(memory_stores.slack_messages) == 1
    assert len(memory_stores.twilio_messages) == 1


def test_actions_validation_gates_for_real_execution(client: TestClient) -> None:
    base_payload = {
        'target': 'email',
        'command': 'email update',
        'payload': {},
        'dry_run': False,
        'human_validation_approved': True,
        'explicit_approval': True,
    }

    consent_required = client.post('/ira/actions', headers=_headers(), json=base_payload)
    assert consent_required.status_code == 422
    assert 'explicit user consent' in consent_required.json().get('detail', '')

    reference_required = client.post(
        '/ira/actions',
        headers=_headers(),
        json={**base_payload, 'user_consent': True},
    )
    assert reference_required.status_code == 422
    assert 'consent_reference' in reference_required.json().get('detail', '')

    risk_required = client.post(
        '/ira/actions',
        headers=_headers(),
        json={**base_payload, 'user_consent': True, 'consent_reference': 'consent-xyz'},
    )
    assert risk_required.status_code == 422
    assert 'approved risk analysis' in risk_required.json().get('detail', '')


def test_actions_reject_disabled_connector(client: TestClient) -> None:
    upsert = client.post(
        '/ira/connectors/upsert',
        headers=_headers(),
        json={'channel': 'email', 'enabled': False, 'provider': 'internal', 'config': {}},
    )
    assert upsert.status_code == 200

    res = client.post(
        '/ira/actions',
        headers=_headers(),
        json={
            'target': 'email',
            'command': 'send email',
            'payload': {'to': 'ops@nuxtron.local'},
            'dry_run': False,
            'user_consent': True,
            'consent_reference': 'consent-disabled-connector',
            'risk_analysis_approved': True,
            'human_validation_approved': True,
            'explicit_approval': True,
        },
    )

    assert res.status_code == 422
    assert 'connector for channel email is disabled' in res.json().get('detail', '')