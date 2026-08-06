from __future__ import annotations

import os
from datetime import UTC, datetime

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ['ALLOW_HEADER_API_KEYS'] = 'true'

import pytest
from fastapi.testclient import TestClient

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'workflow-orchestrator-tenant'}


@pytest.fixture(scope='module')
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _create_high_risk_workflow(client: TestClient) -> int:
    response = client.post(
        '/workflows',
        headers=H,
        json={
            'name': 'Governed Publish Workflow',
            'trigger': {'trigger_type': 'manual'},
            'steps': [
                {'step_id': 's1', 'action_type': 'notify_rep', 'config': {'channel': 'slack'}},
                {'step_id': 's2', 'action_type': 'send_webhook', 'config': {'target': 'https://example.invalid/hook'}},
            ],
        },
    )
    assert response.status_code == 200
    return int(response.json()['workflow']['id'])


def test_workflow_approval_gate_and_enrollment(client: TestClient) -> None:
    workflow_id = _create_high_risk_workflow(client)

    policy_response = client.post(
        '/workflows/approval-policies',
        headers=H,
        json={
            'workflow_id': workflow_id,
            'enabled': True,
            'required_approvals': 2,
            'approver_roles': ['ops_lead', 'legal_reviewer'],
            'enforce_for_high_risk_only': True,
        },
    )
    assert policy_response.status_code == 200

    blocked_enroll_response = client.post(
        f'/workflows/{workflow_id}/enroll',
        headers=H,
        json={'contact_id': 'contact-9001', 'contact_email': 'contact-9001@example.local'},
    )
    assert blocked_enroll_response.status_code == 409

    request_response = client.post(
        '/workflows/approval-requests',
        headers=H,
        json={
            'workflow_id': workflow_id,
            'contact_id': 'contact-9001',
            'reason': 'High-impact publish requires legal + ops review.',
        },
    )
    assert request_response.status_code == 200
    request_id = int(request_response.json()['approval_request']['id'])

    first_approval = client.post(
        f'/workflows/approval-requests/{request_id}/decision',
        headers=H,
        json={'decision': 'approve', 'reviewer': 'ops.lead@nuxtron.local', 'note': 'Ops approved.'},
    )
    assert first_approval.status_code == 200
    assert first_approval.json()['approval_request']['status'] == 'pending'

    second_approval = client.post(
        f'/workflows/approval-requests/{request_id}/decision',
        headers=H,
        json={'decision': 'approve', 'reviewer': 'legal@nuxtron.local', 'note': 'Legal approved.'},
    )
    assert second_approval.status_code == 200
    assert second_approval.json()['approval_request']['status'] == 'approved'

    allowed_enroll_response = client.post(
        f'/workflows/{workflow_id}/enroll',
        headers=H,
        json={'contact_id': 'contact-9001', 'contact_email': 'contact-9001@example.local'},
    )
    assert allowed_enroll_response.status_code == 200
    assert allowed_enroll_response.json()['execution']['status'] == 'completed'


def test_workflow_connector_registry_and_health(client: TestClient) -> None:
    upsert_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'hubspot-marketing',
            'vendor': 'HubSpot',
            'auth_type': 'oauth2',
            'capabilities': ['contacts_sync', 'campaign_enroll', 'webhook_dispatch'],
            'rate_limit_per_minute': 300,
            'error_budget_pct': 1.0,
        },
    )
    assert upsert_response.status_code == 200
    connector_id = int(upsert_response.json()['connector']['id'])

    list_response = client.get('/workflow-connectors', headers=H)
    assert list_response.status_code == 200
    assert list_response.json()['total'] >= 1

    health_response = client.post(f'/workflow-connectors/{connector_id}/health-check', headers=H)
    assert health_response.status_code == 200
    health_payload = health_response.json().get('health', {})
    assert health_payload.get('status') in {'healthy', 'degraded'}


def test_workflow_connector_reliability_and_replay(client: TestClient) -> None:
    create_connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'salesforce-sync',
            'vendor': 'Salesforce',
            'auth_type': 'oauth2',
            'capabilities': ['lead_sync', 'opportunity_sync'],
            'rate_limit_per_minute': 180,
            'error_budget_pct': 1.0,
        },
    )
    assert create_connector_response.status_code == 200
    connector_id = int(create_connector_response.json()['connector']['id'])

    patch_policy_response = client.patch(
        f'/workflow-connectors/{connector_id}/reliability-policy',
        headers=H,
        json={
            'max_retries': 4,
            'base_backoff_ms': 300,
            'circuit_failure_threshold': 2,
            'circuit_cooldown_seconds': 120,
            'slo_availability_target_pct': 99.5,
            'slo_latency_p95_target_ms': 450,
            'replay_enabled': True,
        },
    )
    assert patch_policy_response.status_code == 200
    assert patch_policy_response.json()['policy']['max_retries'] == 4

    simulate_response = client.post(
        f'/workflow-connectors/{connector_id}/simulate-failure',
        headers=H,
        json={'failure_type': 'timeout', 'operation_ref': 'salesforce-op-001'},
    )
    assert simulate_response.status_code == 200
    replay_item = simulate_response.json().get('replay_item') or {}
    assert replay_item.get('status') == 'pending'

    reliability_response = client.get(f'/workflow-connectors/{connector_id}/reliability', headers=H)
    assert reliability_response.status_code == 200
    payload = reliability_response.json()
    assert payload['policy']['max_retries'] == 4
    assert 'slo' in payload
    assert 'availability_pct_rolling' in payload['slo']

    queue_response = client.get(f'/workflow-connectors/replay-queue?connector_id={connector_id}', headers=H)
    assert queue_response.status_code == 200
    assert queue_response.json()['total'] >= 1

    replay_id = int(queue_response.json()['items'][0]['id'])
    replay_response = client.post(
        f'/workflow-connectors/{connector_id}/replay-queue/{replay_id}/replay',
        headers=H,
        json={'force_success': True},
    )
    assert replay_response.status_code == 200
    assert replay_response.json()['item']['status'] == 'succeeded'


def test_workflow_connector_queue_processor_circuit_reconcile_and_sla_alerts(client: TestClient) -> None:
    create_connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'marketo-sync',
            'vendor': 'Marketo',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 120,
            'error_budget_pct': 0.5,
        },
    )
    assert create_connector_response.status_code == 200
    connector_id = int(create_connector_response.json()['connector']['id'])

    policy_response = client.patch(
        f'/workflow-connectors/{connector_id}/reliability-policy',
        headers=H,
        json={
            'max_retries': 2,
            'base_backoff_ms': 100,
            'circuit_failure_threshold': 1,
            'circuit_cooldown_seconds': 10,
            'slo_availability_target_pct': 99.99,
            'slo_latency_p95_target_ms': 150,
            'replay_enabled': True,
        },
    )
    assert policy_response.status_code == 200

    simulate_failure_response = client.post(
        f'/workflow-connectors/{connector_id}/simulate-failure',
        headers=H,
        json={'failure_type': 'timeout', 'operation_ref': 'marketo-op-001'},
    )
    assert simulate_failure_response.status_code == 200

    queue_before_response = client.get(f'/workflow-connectors/replay-queue?connector_id={connector_id}', headers=H)
    assert queue_before_response.status_code == 200
    assert queue_before_response.json()['total'] >= 1

    process_due_response = client.post(
        '/workflow-connectors/replay-queue/process',
        headers=H,
        json={'connector_id': connector_id, 'limit': 25, 'force_success': False},
    )
    assert process_due_response.status_code == 200
    assert process_due_response.json()['count'] >= 0

    process_force_response = client.post(
        '/workflow-connectors/replay-queue/process',
        headers=H,
        json={'connector_id': connector_id, 'limit': 25, 'force_success': True},
    )
    assert process_force_response.status_code == 200

    reconcile_response = client.post('/workflow-connectors/reconcile-circuits', headers=H, json={})
    assert reconcile_response.status_code == 200

    alerts_response = client.get('/workflow-connectors/sla-alerts', headers=H)
    assert alerts_response.status_code == 200
    assert alerts_response.json()['total'] >= 1


def test_workflow_connector_templates_maintenance_and_escalation(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'mailchimp-sync',
            'vendor': 'Mailchimp',
            'auth_type': 'oauth2',
            'capabilities': ['list_sync'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    template_response = client.post(
        '/workflow-connector-templates',
        headers=H,
        json={
            'name': 'Agency Baseline',
            'description': 'Baseline retry and SLO template',
            'max_retries': 5,
            'base_backoff_ms': 400,
            'circuit_failure_threshold': 3,
            'circuit_cooldown_seconds': 120,
            'slo_availability_target_pct': 99.7,
            'slo_latency_p95_target_ms': 500,
            'replay_enabled': True,
        },
    )
    assert template_response.status_code == 200
    template_id = int(template_response.json()['template']['id'])

    apply_response = client.post(
        f'/workflow-connector-templates/{template_id}/apply',
        headers=H,
        json={'connector_ids': [connector_id]},
    )
    assert apply_response.status_code == 200
    assert connector_id in apply_response.json()['updated_connector_ids']

    now_hour = datetime.now(UTC).hour
    next_hour = (now_hour + 1) % 24
    maintenance_response = client.post(
        '/workflow-connector-maintenance-windows',
        headers=H,
        json={
            'name': 'Current hour maintenance',
            'start_hour_utc': now_hour,
            'end_hour_utc': next_hour,
            'connector_ids': [connector_id],
            'enabled': True,
        },
    )
    assert maintenance_response.status_code == 200

    escalation_rule_response = client.post(
        '/workflow-connector-escalation-rules',
        headers=H,
        json={
            'name': 'Notify on first breach',
            'min_breach_count': 1,
            'channels': ['email'],
            'notify_recipients': ['oncall@nuxtron.local'],
            'enabled': True,
        },
    )
    assert escalation_rule_response.status_code == 200

    simulate_response = client.post(
        f'/workflow-connectors/{connector_id}/simulate-failure',
        headers=H,
        json={'failure_type': 'timeout', 'operation_ref': 'mailchimp-op-001'},
    )
    assert simulate_response.status_code == 200

    process_response = client.post(
        '/workflow-connectors/replay-queue/process',
        headers=H,
        json={'connector_id': connector_id, 'limit': 25, 'force_success': False, 'include_not_due': True},
    )
    assert process_response.status_code == 200
    processed_items = process_response.json().get('processed', [])
    assert processed_items
    assert any(item.get('reason') == 'maintenance_window_active' for item in processed_items)

    templates_list_response = client.get('/workflow-connector-templates', headers=H)
    assert templates_list_response.status_code == 200
    assert templates_list_response.json()['total'] >= 1

    windows_list_response = client.get('/workflow-connector-maintenance-windows', headers=H)
    assert windows_list_response.status_code == 200
    assert windows_list_response.json()['total'] >= 1

    escalation_events_response = client.get('/workflow-connector-escalation-events', headers=H)
    assert escalation_events_response.status_code == 200
    assert escalation_events_response.json()['total'] >= 1


def test_workflow_connector_escalation_ack_auto_resolve_and_runbooks(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'pardot-sync',
            'vendor': 'Pardot',
            'auth_type': 'oauth2',
            'capabilities': ['lead_sync'],
            'rate_limit_per_minute': 120,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    policy_response = client.patch(
        f'/workflow-connectors/{connector_id}/reliability-policy',
        headers=H,
        json={
            'max_retries': 2,
            'base_backoff_ms': 120,
            'circuit_failure_threshold': 1,
            'circuit_cooldown_seconds': 10,
            'slo_availability_target_pct': 50,
            'slo_latency_p95_target_ms': 60000,
            'replay_enabled': True,
        },
    )
    assert policy_response.status_code == 200

    escalation_rule_response = client.post(
        '/workflow-connector-escalation-rules',
        headers=H,
        json={
            'name': 'Wave6 escalation rule',
            'min_breach_count': 1,
            'channels': ['email', 'slack'],
            'notify_recipients': ['incident@nuxtron.local'],
            'enabled': True,
        },
    )
    assert escalation_rule_response.status_code == 200

    simulate_response = client.post(
        f'/workflow-connectors/{connector_id}/simulate-failure',
        headers=H,
        json={'failure_type': 'timeout', 'operation_ref': 'pardot-op-001'},
    )
    assert simulate_response.status_code == 200

    process_response = client.post(
        '/workflow-connectors/replay-queue/process',
        headers=H,
        json={'connector_id': connector_id, 'limit': 25, 'force_success': False, 'include_not_due': True},
    )
    assert process_response.status_code == 200

    escalation_events_response = client.get('/workflow-connector-escalation-events', headers=H)
    assert escalation_events_response.status_code == 200
    events = [event for event in escalation_events_response.json().get('events', []) if int(event.get('connector_id', 0)) == connector_id]
    assert events
    event_id = int(events[0]['id'])

    acknowledge_response = client.post(
        f'/workflow-connector-escalation-events/{event_id}/acknowledge',
        headers=H,
        json={'acknowledged_by': 'oncall@nuxtron.local', 'note': 'Investigating connector outage.'},
    )
    assert acknowledge_response.status_code == 200
    assert acknowledge_response.json()['event']['status'] == 'acknowledged'

    process_force_response = client.post(
        '/workflow-connectors/replay-queue/process',
        headers=H,
        json={'connector_id': connector_id, 'limit': 25, 'force_success': True, 'include_not_due': True},
    )
    assert process_force_response.status_code == 200

    first_health_response = client.post(f'/workflow-connectors/{connector_id}/health-check', headers=H)
    assert first_health_response.status_code == 200
    second_health_response = client.post(f'/workflow-connectors/{connector_id}/health-check', headers=H)
    assert second_health_response.status_code == 200

    auto_resolve_response = client.post('/workflow-connector-escalation-events/auto-resolve', headers=H, json={})
    assert auto_resolve_response.status_code == 200
    assert auto_resolve_response.json()['events_resolved'] >= 1

    runbook_response = client.post(
        '/workflow-connector-runbooks',
        headers=H,
        json={
            'name': 'Pardot Incident Runbook',
            'description': 'Standard response for connector failures.',
            'connector_ids': [connector_id],
            'steps': ['Check health endpoint', 'Process replay queue', 'Escalate if still failing'],
            'enabled': True,
        },
    )
    assert runbook_response.status_code == 200
    runbook_id = int(runbook_response.json()['runbook']['id'])

    runbooks_list_response = client.get('/workflow-connector-runbooks', headers=H)
    assert runbooks_list_response.status_code == 200
    assert runbooks_list_response.json()['total'] >= 1

    assignment_response = client.post(
        f'/workflow-connector-runbooks/{runbook_id}/assignments',
        headers=H,
        json={
            'operator': 'incident-commander@nuxtron.local',
            'role': 'incident_lead',
            'note': 'Primary owner for this runbook.',
        },
    )
    assert assignment_response.status_code == 200
    assert assignment_response.json()['assignment']['runbook_id'] == runbook_id

    assignments_list_response = client.get(f'/workflow-connector-runbooks/{runbook_id}/assignments', headers=H)
    assert assignments_list_response.status_code == 200
    assert assignments_list_response.json()['total'] >= 1


def test_workflow_connector_incident_timeline_sli_trends_and_postmortems(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'activecampaign-sync',
            'vendor': 'ActiveCampaign',
            'auth_type': 'oauth2',
            'capabilities': ['contact_sync'],
            'rate_limit_per_minute': 180,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    rule_response = client.post(
        '/workflow-connector-escalation-rules',
        headers=H,
        json={
            'name': 'Wave7 timeline trigger',
            'min_breach_count': 1,
            'channels': ['email'],
            'notify_recipients': ['sre@nuxtron.local'],
            'enabled': True,
        },
    )
    assert rule_response.status_code == 200

    simulate_failure_response = client.post(
        f'/workflow-connectors/{connector_id}/simulate-failure',
        headers=H,
        json={'failure_type': 'timeout', 'operation_ref': 'activecampaign-op-001'},
    )
    assert simulate_failure_response.status_code == 200

    timeline_response = client.get(f'/workflow-connectors/{connector_id}/incident-timeline?limit=50', headers=H)
    assert timeline_response.status_code == 200
    timeline = timeline_response.json().get('timeline', [])
    assert timeline_response.json()['total'] >= 1
    assert timeline

    trends_response = client.get(f'/workflow-connectors/{connector_id}/sli-trends?buckets=8', headers=H)
    assert trends_response.status_code == 200
    assert trends_response.json()['buckets'] == 8
    points = trends_response.json().get('points', [])
    assert len(points) == 8

    escalation_events_response = client.get('/workflow-connector-escalation-events', headers=H)
    assert escalation_events_response.status_code == 200
    connector_event_ids = [
        int(event['id'])
        for event in escalation_events_response.json().get('events', [])
        if int(event.get('connector_id', 0)) == connector_id
    ]

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'ActiveCampaign timeout incident',
            'summary': 'Connector degraded due to timeout and required replay intervention.',
            'incident_event_ids': connector_event_ids[:2],
            'action_items': ['Increase retry visibility', 'Add vendor canary endpoint checks'],
        },
    )
    assert postmortem_response.status_code == 200
    assert postmortem_response.json()['postmortem']['connector_id'] == connector_id

    postmortems_list_response = client.get(f'/workflow-connectors/{connector_id}/postmortems', headers=H)
    assert postmortems_list_response.status_code == 200
    assert postmortems_list_response.json()['total'] >= 1


def test_workflow_connector_postmortem_templates_action_items_and_closure(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'klaviyo-sync',
            'vendor': 'Klaviyo',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 220,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    escalation_rule_response = client.post(
        '/workflow-connector-escalation-rules',
        headers=H,
        json={
            'name': 'Wave8 template escalation',
            'min_breach_count': 1,
            'channels': ['email'],
            'notify_recipients': ['ops@nuxtron.local'],
            'enabled': True,
        },
    )
    assert escalation_rule_response.status_code == 200

    simulate_response = client.post(
        f'/workflow-connectors/{connector_id}/simulate-failure',
        headers=H,
        json={'failure_type': 'timeout', 'operation_ref': 'klaviyo-op-001'},
    )
    assert simulate_response.status_code == 200

    escalation_events_response = client.get('/workflow-connector-escalation-events', headers=H)
    assert escalation_events_response.status_code == 200
    connector_event_ids = [
        int(event['id'])
        for event in escalation_events_response.json().get('events', [])
        if int(event.get('connector_id', 0)) == connector_id
    ]

    template_response = client.post(
        '/workflow-connectors/postmortem-templates',
        headers=H,
        json={
            'name': 'Standard RCA Template',
            'summary_template': 'Template-based incident review summary.',
            'default_action_items': ['Validate vendor metrics', 'Publish internal RCA'],
            'closure_sla_hours': 24,
            'enabled': True,
        },
    )
    assert template_response.status_code == 200
    template_id = int(template_response.json()['template']['id'])

    apply_response = client.post(
        f'/workflow-connectors/postmortem-templates/{template_id}/apply',
        headers=H,
        json={
            'connector_id': connector_id,
            'title': 'Klaviyo incident RCA',
            'incident_event_ids': connector_event_ids[:2],
        },
    )
    assert apply_response.status_code == 200
    postmortem = apply_response.json()['postmortem']
    postmortem_id = int(postmortem['id'])

    add_action_item_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
        headers=H,
        json={'title': 'Add connector timeout synthetic check', 'owner': 'sre@nuxtron.local', 'due_in_hours': 24},
    )
    assert add_action_item_response.status_code == 200

    list_action_items_response = client.get(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
        headers=H,
    )
    assert list_action_items_response.status_code == 200
    action_items = list_action_items_response.json().get('action_items', [])
    assert action_items

    for item in action_items:
        item_id = int(item['id'])
        update_response = client.patch(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items/{item_id}',
            headers=H,
            json={'status': 'done', 'note': 'Completed for closure readiness.'},
        )
        assert update_response.status_code == 200
        assert update_response.json()['action_item']['status'] == 'done'

    close_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/close',
        headers=H,
        json={'closed_by': 'ops.lead@nuxtron.local', 'note': 'All actions complete.', 'require_action_items_resolved': True},
    )
    assert close_response.status_code == 200
    assert close_response.json()['postmortem']['status'] == 'closed'
    assert close_response.json()['postmortem']['closure_sla_status'] in {'met', 'breached'}


def test_workflow_connector_postmortem_closure_approvals_overdue_escalations_and_rollups(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'braze-sync',
            'vendor': 'Braze',
            'auth_type': 'oauth2',
            'capabilities': ['audience_sync'],
            'rate_limit_per_minute': 210,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Braze incident postmortem',
            'summary': 'Postmortem for closure approval workflow testing.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    action_item_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
        headers=H,
        json={'title': 'Resolve vendor timeout debt', 'owner': 'owner@nuxtron.local', 'due_in_hours': 1},
    )
    assert action_item_response.status_code == 200
    action_item_id = int(action_item_response.json()['action_item']['id'])

    # Force this action item into overdue state for deterministic escalation processing.
    overdue_patch_response = client.patch(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items/{action_item_id}',
        headers=H,
        json={'status': 'open', 'note': 'Marking for overdue escalation path.'},
    )
    assert overdue_patch_response.status_code == 200

    policy_response = client.post(
        '/workflow-connectors/postmortems/closure-policy',
        headers=H,
        json={
            'enabled': True,
            'required_approvals': 1,
            'approver_roles': ['ops_lead'],
            'enforce_for_breached_sla_only': False,
        },
    )
    assert policy_response.status_code == 200
    assert policy_response.json()['policy']['enabled'] is True

    routing_policy_response = client.post(
        '/workflow-connectors/postmortems/escalation-routing-policy',
        headers=H,
        json={
            'enabled': True,
            'paging_start_hour_utc': 0,
            'paging_end_hour_utc': 23,
            'in_window_channel': 'pagerduty',
            'off_window_channel': 'email',
            'medium_threshold_hours': 1,
            'high_threshold_hours': 8,
            'critical_threshold_hours': 24,
            'medium_recipients': ['ops@nuxtron.local'],
            'high_recipients': ['incident@nuxtron.local'],
            'critical_recipients': ['sre@nuxtron.local'],
        },
    )
    assert routing_policy_response.status_code == 200

    routing_policy_get_response = client.get('/workflow-connectors/postmortems/escalation-routing-policy', headers=H)
    assert routing_policy_get_response.status_code == 200
    assert routing_policy_get_response.json()['policy']['enabled'] is True

    cadence_policy_response = client.post(
        '/workflow-connectors/postmortems/escalation-cadence-policy',
        headers=H,
        json={
            'enabled': True,
            'l2_after_minutes': 0,
            'l3_after_minutes': 0,
            'repage_interval_minutes': 0,
            'max_repages': 8,
            'suppression_ttl_minutes': 0,
            'reopen_on_reoverdue': True,
            'l1_recipients': ['ops@nuxtron.local'],
            'l2_recipients': ['incident@nuxtron.local'],
            'l3_recipients': ['sre@nuxtron.local'],
        },
    )
    assert cadence_policy_response.status_code == 200

    close_blocked_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/close',
        headers=H,
        json={'closed_by': 'ops.lead@nuxtron.local', 'note': 'Attempt close without approval.', 'require_action_items_resolved': False},
    )
    assert close_blocked_response.status_code == 409

    closure_request_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/closure-requests',
        headers=H,
        json={},
    )
    assert closure_request_response.status_code == 200
    request_id = int(closure_request_response.json()['closure_request']['id'])

    approve_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/closure-requests/{request_id}/decision',
        headers=H,
        json={'decision': 'approve', 'reviewer': 'ops.lead@nuxtron.local', 'note': 'Approved for closure.'},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()['closure_request']['status'] == 'approved'

    overdue_process_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 50, 'include_not_due': True},
    )
    assert overdue_process_response.status_code == 200
    assert overdue_process_response.json()['count'] >= 1
    processed_items = overdue_process_response.json().get('processed', [])
    assert processed_items
    assert processed_items[0].get('severity') in {'medium', 'high', 'critical'}
    assert processed_items[0].get('channel') in {'pagerduty', 'email'}

    escalations_response = client.get('/workflow-connectors/postmortems/action-items/escalations?limit=100', headers=H)
    assert escalations_response.status_code == 200
    assert escalations_response.json()['total'] >= 1
    escalation_id = int(escalations_response.json()['escalations'][0]['id'])

    cadence_process_response = client.post(
        '/workflow-connectors/postmortems/action-items/escalations/process-cadence',
        headers=H,
        json={'limit': 100},
    )
    assert cadence_process_response.status_code == 200
    assert cadence_process_response.json()['count'] >= 1
    assert cadence_process_response.json()['processed'][0]['tier'] in {'l1', 'l2', 'l3'}

    ack_response = client.post(
        f'/workflow-connectors/postmortems/action-items/escalations/{escalation_id}/acknowledge',
        headers=H,
        json={'acknowledged_by': 'ops.lead@nuxtron.local', 'note': 'Taking ownership.'},
    )
    assert ack_response.status_code == 200
    assert ack_response.json()['escalation']['status'] == 'acknowledged'

    done_action_response = client.patch(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items/{action_item_id}',
        headers=H,
        json={'status': 'done', 'note': 'Resolved before final closure.'},
    )
    assert done_action_response.status_code == 200

    close_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/close',
        headers=H,
        json={'closed_by': 'ops.lead@nuxtron.local', 'note': 'Approved and complete.', 'require_action_items_resolved': True},
    )
    assert close_response.status_code == 200
    assert close_response.json()['postmortem']['status'] == 'closed'

    rollups_response = client.get('/workflow-connectors/postmortems/compliance-rollups?weeks=4', headers=H)
    assert rollups_response.status_code == 200
    assert rollups_response.json()['total'] == 4


def test_workflow_connector_escalation_suppression_reopen_and_aging_dashboard(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'iterable-sync',
            'vendor': 'Iterable',
            'auth_type': 'oauth2',
            'capabilities': ['journey_sync'],
            'rate_limit_per_minute': 200,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Iterable suppression/reopen test',
            'summary': 'Validation for suppression expiry and reopen.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    action_item_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
        headers=H,
        json={'title': 'Investigate delayed webhook retries', 'owner': 'owner@nuxtron.local', 'due_in_hours': 1},
    )
    assert action_item_response.status_code == 200

    routing_policy_response = client.post(
        '/workflow-connectors/postmortems/escalation-routing-policy',
        headers=H,
        json={
            'enabled': True,
            'paging_start_hour_utc': 0,
            'paging_end_hour_utc': 23,
            'in_window_channel': 'pagerduty',
            'off_window_channel': 'email',
            'medium_threshold_hours': 1,
            'high_threshold_hours': 2,
            'critical_threshold_hours': 3,
            'medium_recipients': ['ops@nuxtron.local'],
            'high_recipients': ['incident@nuxtron.local'],
            'critical_recipients': ['sre@nuxtron.local'],
        },
    )
    assert routing_policy_response.status_code == 200

    cadence_policy_response = client.post(
        '/workflow-connectors/postmortems/escalation-cadence-policy',
        headers=H,
        json={
            'enabled': True,
            'l2_after_minutes': 0,
            'l3_after_minutes': 0,
            'repage_interval_minutes': 0,
            'max_repages': 1,
            'suppression_ttl_minutes': 0,
            'reopen_on_reoverdue': True,
            'l1_recipients': ['ops@nuxtron.local'],
            'l2_recipients': ['incident@nuxtron.local'],
            'l3_recipients': ['sre@nuxtron.local'],
        },
    )
    assert cadence_policy_response.status_code == 200

    process_overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 50, 'include_not_due': True},
    )
    assert process_overdue_response.status_code == 200
    assert process_overdue_response.json()['count'] >= 1

    cadence_process_response = client.post(
        '/workflow-connectors/postmortems/action-items/escalations/process-cadence',
        headers=H,
        json={'limit': 100},
    )
    assert cadence_process_response.status_code == 200
    assert cadence_process_response.json()['count'] >= 1
    assert cadence_process_response.json()['processed'][0]['status'] in {'suppressed', 'open'}

    suppression_process_response = client.post(
        '/workflow-connectors/postmortems/action-items/escalations/process-suppression',
        headers=H,
        json={'limit': 100},
    )
    assert suppression_process_response.status_code == 200
    assert suppression_process_response.json()['count'] >= 1
    assert suppression_process_response.json()['reopened'][0]['status'] == 'open'

    aging_dashboard_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalations/aging-dashboard?ack_slo_minutes=60&lookback_hours=168',
        headers=H,
    )
    assert aging_dashboard_response.status_code == 200
    assert aging_dashboard_response.json()['total_escalations'] >= 1
    assert 'age_buckets' in aging_dashboard_response.json()


def test_workflow_connector_breach_forecast_and_escalation_priority_queue(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'customerio-sync',
            'vendor': 'Customer.io',
            'auth_type': 'oauth2',
            'capabilities': ['journey_sync'],
            'rate_limit_per_minute': 200,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Customer.io proactive risk test',
            'summary': 'Validation for breach forecast and priority queue.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    action_item_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
        headers=H,
        json={'title': 'Mitigate webhook latency spikes', 'owner': 'owner@nuxtron.local', 'due_in_hours': 1},
    )
    assert action_item_response.status_code == 200

    routing_policy_response = client.post(
        '/workflow-connectors/postmortems/escalation-routing-policy',
        headers=H,
        json={
            'enabled': True,
            'paging_start_hour_utc': 0,
            'paging_end_hour_utc': 23,
            'in_window_channel': 'pagerduty',
            'off_window_channel': 'email',
            'medium_threshold_hours': 1,
            'high_threshold_hours': 2,
            'critical_threshold_hours': 3,
            'medium_recipients': ['ops@nuxtron.local'],
            'high_recipients': ['incident@nuxtron.local'],
            'critical_recipients': ['sre@nuxtron.local'],
        },
    )
    assert routing_policy_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 50, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    priority_queue_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalations/priority-queue?limit=100&include_suppressed=true',
        headers=H,
    )
    assert priority_queue_response.status_code == 200
    assert priority_queue_response.json()['count'] >= 1
    top_item = priority_queue_response.json()['queue'][0]
    assert 'priority_score' in top_item
    assert top_item.get('recommended_action') in {'process_suppression', 'exec_page', 'incident_command_review', 'follow_up_owner', 'repage_or_ack'}

    forecast_response = client.get(
        '/workflow-connectors/postmortems/action-items/breach-forecast?window_hours=24&limit=100',
        headers=H,
    )
    assert forecast_response.status_code == 200
    assert forecast_response.json()['at_risk_total'] >= 1
    assert forecast_response.json()['items'][0]['risk_level'] in {'breached', 'critical_soon', 'high_soon', 'due_soon'}


def test_workflow_connector_owner_workload_and_rebalance_suggestions(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'sendgrid-sync',
            'vendor': 'SendGrid',
            'auth_type': 'oauth2',
            'capabilities': ['email_delivery_sync'],
            'rate_limit_per_minute': 220,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'SendGrid owner load balancing test',
            'summary': 'Validate workload dashboard and rebalance recommendations.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Tune retry policy for bounced traffic', 'alice@nuxtron.local'),
        ('Backfill vendor canary checks', 'alice@nuxtron.local'),
        ('Reduce webhook timeout variance', 'alice@nuxtron.local'),
        ('Verify suppression policy rollout', 'bob@nuxtron.local'),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    process_overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert process_overdue_response.status_code == 200
    assert process_overdue_response.json()['count'] >= 1

    workload_response = client.get(
        '/workflow-connectors/postmortems/action-items/owner-workload?include_done=false',
        headers=H,
    )
    assert workload_response.status_code == 200
    assert workload_response.json()['total_owners'] >= 2
    assert workload_response.json()['total_open_action_items'] >= 4
    owners = workload_response.json()['owners']
    assert any(owner.get('owner') == 'alice@nuxtron.local' for owner in owners)

    rebalance_response = client.post(
        '/workflow-connectors/postmortems/action-items/rebalance-suggestions',
        headers=H,
        json={
            'max_open_items_per_owner': 2,
            'include_unassigned': True,
            'limit': 25,
        },
    )
    assert rebalance_response.status_code == 200
    assert rebalance_response.json()['count'] >= 1
    suggestion = rebalance_response.json()['suggestions'][0]
    assert suggestion.get('from_owner') == 'alice@nuxtron.local'
    assert isinstance(suggestion.get('to_owner'), str)
    assert suggestion.get('to_owner') not in {'', 'alice@nuxtron.local'}


def test_workflow_connector_workload_hotspots_and_surge_alerts(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'campaignmonitor-sync',
            'vendor': 'Campaign Monitor',
            'auth_type': 'oauth2',
            'capabilities': ['audience_sync'],
            'rate_limit_per_minute': 180,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Campaign Monitor hotspot test',
            'summary': 'Validate hotspots and surge alerts for owner workload.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title in [
        'Investigate email API timeout pattern',
        'Tune retry jitter settings',
        'Backfill delivery latency canary checks',
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': 'hotspot@nuxtron.local', 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    process_overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert process_overdue_response.status_code == 200
    assert process_overdue_response.json()['count'] >= 1

    hotspots_response = client.get(
        '/workflow-connectors/postmortems/action-items/workload-hotspots?max_open_items_per_owner=2&max_overdue_items_per_owner=0',
        headers=H,
    )
    assert hotspots_response.status_code == 200
    assert hotspots_response.json()['count'] >= 1
    hotspot_owners = {item.get('owner') for item in hotspots_response.json()['hotspots']}
    assert 'hotspot@nuxtron.local' in hotspot_owners
    assert any(item.get('severity') in {'high', 'critical'} for item in hotspots_response.json()['hotspots'])

    surge_response = client.get(
        '/workflow-connectors/postmortems/action-items/surge-alerts?lookback_hours=24&min_new_open_escalations=1',
        headers=H,
    )
    assert surge_response.status_code == 200
    assert surge_response.json()['count'] >= 1
    alerts = surge_response.json()['alerts']
    assert any(item.get('owner') == 'hotspot@nuxtron.local' for item in alerts)
    assert any(int(item.get('new_open_escalations', 0)) >= 1 for item in alerts)
    assert any(item.get('severity') in {'medium', 'high', 'critical'} for item in alerts)


def test_workflow_connector_balance_index_and_coverage_gaps(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'mailerlite-sync',
            'vendor': 'MailerLite',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 190,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'MailerLite balance index test',
            'summary': 'Validate concentration and coverage gap analytics.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Tune campaign timeout defaults', 'imbalance@nuxtron.local'),
        ('Add retry observability dashboards', 'imbalance@nuxtron.local'),
        ('Backfill webhook dead-letter replay', 'imbalance@nuxtron.local'),
        ('Review template delivery drift', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    balance_index_response = client.get(
        '/workflow-connectors/postmortems/action-items/balance-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert balance_index_response.status_code == 200
    assert balance_index_response.json()['total_open_action_items'] >= 4
    assert balance_index_response.json()['overloaded_owner_count'] >= 1
    assert balance_index_response.json()['max_owner_share_pct'] > 0

    coverage_gaps_response = client.get(
        '/workflow-connectors/postmortems/action-items/coverage-gaps?max_open_items_per_owner=2',
        headers=H,
    )
    assert coverage_gaps_response.status_code == 200
    assert coverage_gaps_response.json()['unassigned_open_items'] >= 1
    assert coverage_gaps_response.json()['count'] >= 1
    gap_codes = {item.get('code') for item in coverage_gaps_response.json()['gaps']}
    assert 'unassigned_items' in gap_codes or 'overloaded_owner' in gap_codes


def test_workflow_connector_handoff_readiness_and_continuity_risks(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'getresponse-sync',
            'vendor': 'GetResponse',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 175,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'GetResponse continuity readiness test',
            'summary': 'Validate owner handoff readiness and continuity risk detection.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title in [
        'Stabilize campaign webhook retries',
        'Validate fallback sender profile',
        'Backfill delivery SLA guardrails',
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': 'continuity@nuxtron.local', 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    handoff_response = client.get(
        '/workflow-connectors/postmortems/action-items/handoff-readiness?max_open_items_per_owner=2&critical_open_escalations_threshold=1',
        headers=H,
    )
    assert handoff_response.status_code == 200
    assert handoff_response.json()['count'] >= 1
    owners = handoff_response.json()['owners']
    assert any(item.get('owner') == 'continuity@nuxtron.local' for item in owners)
    assert any(item.get('handoff_readiness_status') in {'at_risk', 'blocked'} for item in owners)

    continuity_response = client.get(
        '/workflow-connectors/postmortems/action-items/continuity-risks?min_single_owner_items=2',
        headers=H,
    )
    assert continuity_response.status_code == 200
    assert continuity_response.json()['count'] >= 1
    risks = continuity_response.json()['risks']
    assert any(item.get('owner') == 'continuity@nuxtron.local' for item in risks)
    assert any(item.get('code') in {'single_owner_connector_dependency', 'escalation_concentration'} for item in risks)


def test_workflow_connector_ownership_churn_and_stability_score(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'moosend-sync',
            'vendor': 'Moosend',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 170,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Moosend churn/stability test',
            'summary': 'Validate ownership churn and stability analytics.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Tighten retry backoff profile', 'churn@nuxtron.local'),
        ('Patch webhook timeout thresholds', 'churn@nuxtron.local'),
        ('Audit retry dead-letter queue', ''),
        ('Review send-failure suppression rules', 'backup@nuxtron.local'),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    process_overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert process_overdue_response.status_code == 200

    churn_response = client.get(
        '/workflow-connectors/postmortems/action-items/ownership-churn?min_owner_switch_risk_items=1',
        headers=H,
    )
    assert churn_response.status_code == 200
    assert churn_response.json()['count'] >= 1
    connectors = churn_response.json()['connectors']
    assert any(int(item.get('connector_id', 0)) == connector_id for item in connectors)
    assert any(item.get('severity') in {'low', 'medium', 'high'} for item in connectors)

    stability_response = client.get(
        '/workflow-connectors/postmortems/action-items/stability-score?max_open_items_per_owner=2',
        headers=H,
    )
    assert stability_response.status_code == 200
    assert 'stability_score' in stability_response.json()
    assert stability_response.json()['stability_band'] in {'stable', 'watch', 'unstable'}
    assert stability_response.json()['total_open_action_items'] >= 4


def test_workflow_connector_handoff_plan_and_resilience_snapshot(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'aweber-sync',
            'vendor': 'AWeber',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 165,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'AWeber handoff plan test',
            'summary': 'Validate handoff-plan and resilience-snapshot endpoints.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Reduce webhook timeout failures', 'handoff@nuxtron.local'),
        ('Verify fallback sender pool', 'handoff@nuxtron.local'),
        ('Patch campaign retry thresholds', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    handoff_plan_response = client.get(
        '/workflow-connectors/postmortems/action-items/handoff-plan?max_open_items_per_owner=2',
        headers=H,
    )
    assert handoff_plan_response.status_code == 200
    assert handoff_plan_response.json()['count'] >= 1
    plans = handoff_plan_response.json()['plans']
    assert any(item.get('owner') == 'handoff@nuxtron.local' for item in plans)
    assert any(item.get('priority') in {'medium', 'high', 'critical'} for item in plans)

    resilience_snapshot_response = client.get(
        '/workflow-connectors/postmortems/action-items/resilience-snapshot?max_open_items_per_owner=2',
        headers=H,
    )
    assert resilience_snapshot_response.status_code == 200
    assert 'resilience_score' in resilience_snapshot_response.json()
    assert resilience_snapshot_response.json()['resilience_band'] in {'strong', 'watch', 'fragile'}
    assert resilience_snapshot_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_queue_and_readiness_forecast(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'mailjet-sync',
            'vendor': 'Mailjet',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 160,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Mailjet remediation queue test',
            'summary': 'Validate remediation queue and readiness forecast APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Triage webhook retry faults', 'queue@nuxtron.local'),
        ('Address campaign timeout drift', 'queue@nuxtron.local'),
        ('Assign missing incident owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    remediation_queue_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-queue?max_open_items_per_owner=2&limit=50',
        headers=H,
    )
    assert remediation_queue_response.status_code == 200
    assert remediation_queue_response.json()['count'] >= 1
    queue_items = remediation_queue_response.json()['queue']
    assert any(item.get('action') in {'assign_owner', 'reassign_overdue', 'add_co_owner', 'rebalance_load'} for item in queue_items)

    readiness_forecast_response = client.get(
        '/workflow-connectors/postmortems/action-items/readiness-forecast?max_open_items_per_owner=2',
        headers=H,
    )
    assert readiness_forecast_response.status_code == 200
    assert 'readiness_forecast_score' in readiness_forecast_response.json()
    assert readiness_forecast_response.json()['forecast_band'] in {'ready', 'watch', 'risk'}
    assert readiness_forecast_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_throughput_and_risk_burndown(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'sendgrid-sync',
            'vendor': 'SendGrid',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 160,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'SendGrid throughput and burndown test',
            'summary': 'Validate throughput and burndown APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Repair retry strategy drift', 'burndown@nuxtron.local'),
        ('Reconcile template mapping errors', 'burndown@nuxtron.local'),
        ('Assign incident follow-up owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    throughput_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-throughput?max_open_items_per_owner=2&days_horizon=7',
        headers=H,
    )
    assert throughput_response.status_code == 200
    assert 'required_daily_remediations' in throughput_response.json()
    assert throughput_response.json()['throughput_band'] in {'sustainable', 'stretched', 'critical'}
    assert throughput_response.json()['total_open_action_items'] >= 3

    burndown_response = client.get(
        '/workflow-connectors/postmortems/action-items/risk-burndown?days_horizon=7',
        headers=H,
    )
    assert burndown_response.status_code == 200
    assert 'risk_burndown_index' in burndown_response.json()
    assert burndown_response.json()['burndown_band'] in {'on-track', 'needs-focus', 'off-track'}
    assert burndown_response.json()['critical_backlog'] >= 1


def test_workflow_connector_capacity_scenarios_and_remediation_sla(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'constant-contact-sync',
            'vendor': 'ConstantContact',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 155,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Capacity and remediation SLA test',
            'summary': 'Validate capacity scenarios and remediation SLA APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Resolve stale campaign mappings', 'capacity@nuxtron.local'),
        ('Close webhook retry loop', 'capacity@nuxtron.local'),
        ('Assign cross-team owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    capacity_response = client.get(
        '/workflow-connectors/postmortems/action-items/capacity-scenarios?max_open_items_per_owner=2&days_horizon=7',
        headers=H,
    )
    assert capacity_response.status_code == 200
    assert capacity_response.json()['count'] >= 1
    scenario_rows = capacity_response.json()['scenarios']
    assert any(item.get('scenario') in {'stabilize', 'accelerate', 'constrained'} for item in scenario_rows)

    remediation_sla_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-sla?sla_hours=24',
        headers=H,
    )
    assert remediation_sla_response.status_code == 200
    assert 'remediation_sla_score' in remediation_sla_response.json()
    assert remediation_sla_response.json()['sla_band'] in {'healthy', 'watch', 'breach'}
    assert remediation_sla_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_owner_relief_plan_and_escalation_clearance_eta(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'activecampaign-sync',
            'vendor': 'ActiveCampaign',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 170,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Owner relief and clearance ETA test',
            'summary': 'Validate owner relief plan and escalation clearance ETA APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Reconcile campaign deliverability drift', 'relief@nuxtron.local'),
        ('Fix webhook retry envelope', 'relief@nuxtron.local'),
        ('Assign unresolved incident owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    owner_relief_response = client.get(
        '/workflow-connectors/postmortems/action-items/owner-relief-plan?max_open_items_per_owner=2',
        headers=H,
    )
    assert owner_relief_response.status_code == 200
    assert owner_relief_response.json()['count'] >= 1
    relief_plans = owner_relief_response.json()['plans']
    assert any(item.get('priority') in {'critical', 'high', 'medium', 'low'} for item in relief_plans)

    clearance_eta_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-clearance-eta?days_horizon=7',
        headers=H,
    )
    assert clearance_eta_response.status_code == 200
    assert 'clearance_eta_days' in clearance_eta_response.json()
    assert clearance_eta_response.json()['eta_band'] in {'immediate', 'manageable', 'backlog-risk'}
    assert clearance_eta_response.json()['clearance_load'] >= 1


def test_workflow_connector_mitigation_readiness_and_owner_coverage_forecast(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'drip-sync',
            'vendor': 'Drip',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 165,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Mitigation readiness and coverage forecast test',
            'summary': 'Validate mitigation readiness and owner coverage forecast APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Reduce retry failure spikes', 'coverage@nuxtron.local'),
        ('Patch vendor callback drift', 'coverage@nuxtron.local'),
        ('Assign unresolved postmortem owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    readiness_response = client.get(
        '/workflow-connectors/postmortems/action-items/mitigation-readiness?max_open_items_per_owner=2',
        headers=H,
    )
    assert readiness_response.status_code == 200
    assert 'mitigation_readiness_score' in readiness_response.json()
    assert readiness_response.json()['readiness_band'] in {'ready', 'watch', 'at-risk'}
    assert readiness_response.json()['total_open_action_items'] >= 3

    coverage_response = client.get(
        '/workflow-connectors/postmortems/action-items/owner-coverage-forecast?max_open_items_per_owner=2',
        headers=H,
    )
    assert coverage_response.status_code == 200
    assert 'owner_coverage_score' in coverage_response.json()
    assert coverage_response.json()['coverage_band'] in {'strong', 'watch', 'fragile'}
    assert coverage_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_handoff_pressure_and_remediation_momentum(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'convertkit-sync',
            'vendor': 'ConvertKit',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 160,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Handoff pressure and remediation momentum test',
            'summary': 'Validate handoff pressure and remediation momentum APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Stabilize sender pool behavior', 'momentum@nuxtron.local'),
        ('Patch webhook timeout policy', 'momentum@nuxtron.local'),
        ('Assign unresolved run owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    pressure_response = client.get(
        '/workflow-connectors/postmortems/action-items/handoff-pressure?max_open_items_per_owner=2',
        headers=H,
    )
    assert pressure_response.status_code == 200
    assert 'handoff_pressure_score' in pressure_response.json()
    assert pressure_response.json()['pressure_band'] in {'steady', 'elevated', 'critical'}
    assert pressure_response.json()['total_open_action_items'] >= 3

    momentum_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-momentum?days_horizon=7',
        headers=H,
    )
    assert momentum_response.status_code == 200
    assert 'remediation_momentum_score' in momentum_response.json()
    assert momentum_response.json()['momentum_band'] in {'on-track', 'watch', 'stalled'}
    assert momentum_response.json()['open_action_items'] >= 3


def test_workflow_connector_ownership_stability_forecast_and_escalation_burn_rate(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'mailerlite-sync',
            'vendor': 'MailerLite',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 160,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Ownership stability and burn-rate test',
            'summary': 'Validate ownership stability forecast and escalation burn-rate APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Stabilize campaign queue ownership', 'stability@nuxtron.local'),
        ('Resolve retry loop regressions', 'stability@nuxtron.local'),
        ('Assign unresolved owner for backlog', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    stability_response = client.get(
        '/workflow-connectors/postmortems/action-items/ownership-stability-forecast?max_open_items_per_owner=2',
        headers=H,
    )
    assert stability_response.status_code == 200
    assert 'ownership_stability_score' in stability_response.json()
    assert stability_response.json()['stability_band'] in {'stable', 'watch', 'fragile'}
    assert stability_response.json()['total_open_action_items'] >= 3

    burn_rate_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-burn-rate?days_horizon=7',
        headers=H,
    )
    assert burn_rate_response.status_code == 200
    assert 'target_daily_burn' in burn_rate_response.json()
    assert burn_rate_response.json()['burn_band'] in {'low', 'managed', 'high'}
    assert burn_rate_response.json()['open_action_items'] >= 3


def test_workflow_connector_handoff_resilience_forecast_and_backlog_clearance_confidence(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'campaign-monitor-sync',
            'vendor': 'CampaignMonitor',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 160,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Handoff resilience and clearance confidence test',
            'summary': 'Validate handoff resilience forecast and backlog clearance confidence APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Reduce retry fallback drift', 'resilience@nuxtron.local'),
        ('Stabilize webhook ownership lane', 'resilience@nuxtron.local'),
        ('Assign unresolved response owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    resilience_response = client.get(
        '/workflow-connectors/postmortems/action-items/handoff-resilience-forecast?max_open_items_per_owner=2',
        headers=H,
    )
    assert resilience_response.status_code == 200
    assert 'handoff_resilience_score' in resilience_response.json()
    assert resilience_response.json()['resilience_band'] in {'resilient', 'watch', 'fragile'}
    assert resilience_response.json()['total_open_action_items'] >= 3

    confidence_response = client.get(
        '/workflow-connectors/postmortems/action-items/backlog-clearance-confidence?days_horizon=7',
        headers=H,
    )
    assert confidence_response.status_code == 200
    assert 'backlog_clearance_confidence' in confidence_response.json()
    assert confidence_response.json()['confidence_band'] in {'high', 'moderate', 'low'}
    assert confidence_response.json()['open_action_items'] >= 3


def test_workflow_connector_remediation_velocity_forecast_and_escalation_recovery_readiness(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'sendlane-sync',
            'vendor': 'Sendlane',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 160,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Velocity forecast and recovery readiness test',
            'summary': 'Validate remediation velocity forecast and escalation recovery readiness APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Reduce retry backlog saturation', 'velocity@nuxtron.local'),
        ('Patch escalation routing drift', 'velocity@nuxtron.local'),
        ('Assign unresolved coverage owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    velocity_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-velocity-forecast?days_horizon=7',
        headers=H,
    )
    assert velocity_response.status_code == 200
    assert 'remediation_velocity_score' in velocity_response.json()
    assert velocity_response.json()['velocity_band'] in {'fast', 'steady', 'lagging'}
    assert velocity_response.json()['open_action_items'] >= 3

    recovery_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-recovery-readiness?max_open_items_per_owner=2',
        headers=H,
    )
    assert recovery_response.status_code == 200
    assert 'escalation_recovery_score' in recovery_response.json()
    assert recovery_response.json()['recovery_band'] in {'ready', 'watch', 'risk'}
    assert recovery_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_continuity_readiness_index_and_escalation_drain_forecast(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'omnisend-sync',
            'vendor': 'Omnisend',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 160,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Continuity index and drain forecast test',
            'summary': 'Validate continuity readiness index and escalation drain forecast APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Stabilize remediation ownership handoff', 'continuity@nuxtron.local'),
        ('Reduce escalation queue pressure', 'continuity@nuxtron.local'),
        ('Assign unresolved escalation owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    continuity_response = client.get(
        '/workflow-connectors/postmortems/action-items/continuity-readiness-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert continuity_response.status_code == 200
    assert 'continuity_readiness_index' in continuity_response.json()
    assert continuity_response.json()['continuity_band'] in {'ready', 'watch', 'fragile'}
    assert continuity_response.json()['total_open_action_items'] >= 3

    drain_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-drain-forecast?days_horizon=7',
        headers=H,
    )
    assert drain_response.status_code == 200
    assert 'required_daily_drain' in drain_response.json()
    assert drain_response.json()['drain_band'] in {'light', 'moderate', 'heavy'}
    assert drain_response.json()['open_action_items'] >= 3


def test_workflow_connector_remediation_confidence_forecast_and_escalation_stabilization_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'klaviyo-sync',
            'vendor': 'Klaviyo',
            'auth_type': 'oauth2',
            'capabilities': ['campaign_sync'],
            'rate_limit_per_minute': 160,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Confidence forecast and stabilization index test',
            'summary': 'Validate remediation confidence forecast and escalation stabilization index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Reduce escalation carryover load', 'confidence@nuxtron.local'),
        ('Stabilize remediation handoff coverage', 'confidence@nuxtron.local'),
        ('Assign unresolved response owner', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    confidence_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-confidence-forecast?days_horizon=7',
        headers=H,
    )
    assert confidence_response.status_code == 200
    assert 'remediation_confidence_score' in confidence_response.json()
    assert confidence_response.json()['confidence_band'] in {'high', 'moderate', 'low'}
    assert confidence_response.json()['open_action_items'] >= 3

    stabilization_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-stabilization-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert stabilization_response.status_code == 200
    assert 'escalation_stabilization_index' in stabilization_response.json()
    assert stabilization_response.json()['stabilization_band'] in {'stable', 'watch', 'unstable'}
    assert stabilization_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_posture_score_and_escalation_runway_forecast(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'segment-sync',
            'vendor': 'Segment',
            'auth_type': 'api_key',
            'capabilities': ['event_forwarding'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.2,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation posture and escalation runway forecast test',
            'summary': 'Validate remediation posture score and escalation runway forecast APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Rebalance open remediation owners', 'posture@nuxtron.local'),
        ('Clear urgent action item backlog', 'posture@nuxtron.local'),
        ('Assign unowned mitigation task', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    posture_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-posture-score?max_open_items_per_owner=2',
        headers=H,
    )
    assert posture_response.status_code == 200
    assert 'remediation_posture_score' in posture_response.json()
    assert posture_response.json()['posture_band'] in {'strong', 'watch', 'weak'}
    assert posture_response.json()['total_open_action_items'] >= 3

    runway_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-runway-forecast?days_horizon=7',
        headers=H,
    )
    assert runway_response.status_code == 200
    assert 'required_daily_runway_actions' in runway_response.json()
    assert runway_response.json()['runway_band'] in {'comfortable', 'tight', 'critical'}
    assert runway_response.json()['open_action_items'] >= 3


def test_workflow_connector_remediation_balance_index_and_escalation_pressure_forecast(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'mixpanel-sync',
            'vendor': 'Mixpanel',
            'auth_type': 'api_key',
            'capabilities': ['event_analytics'],
            'rate_limit_per_minute': 140,
            'error_budget_pct': 1.1,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation balance and escalation pressure forecast test',
            'summary': 'Validate remediation balance index and escalation pressure forecast APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Redistribute action-item ownership', 'balance@nuxtron.local'),
        ('Drain overdue remediation queue', 'balance@nuxtron.local'),
        ('Assign pending escalation follow-up', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    balance_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-balance-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert balance_response.status_code == 200
    assert 'remediation_balance_index' in balance_response.json()
    assert balance_response.json()['balance_band'] in {'balanced', 'watch', 'imbalanced'}
    assert balance_response.json()['total_open_action_items'] >= 3

    pressure_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-pressure-forecast?days_horizon=7',
        headers=H,
    )
    assert pressure_response.status_code == 200
    assert 'required_daily_pressure_actions' in pressure_response.json()
    assert pressure_response.json()['pressure_band'] in {'contained', 'elevated', 'critical'}
    assert pressure_response.json()['open_action_items'] >= 3


def test_workflow_connector_remediation_concentration_forecast_and_escalation_containment_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'amplitude-sync',
            'vendor': 'Amplitude',
            'auth_type': 'api_key',
            'capabilities': ['product_analytics'],
            'rate_limit_per_minute': 145,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation concentration and escalation containment test',
            'summary': 'Validate remediation concentration forecast and escalation containment index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Reassign overloaded owner backlog', 'concentration@nuxtron.local'),
        ('Contain urgent remediation spillover', 'concentration@nuxtron.local'),
        ('Assign pending ownerless action item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    concentration_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-concentration-forecast?max_open_items_per_owner=2',
        headers=H,
    )
    assert concentration_response.status_code == 200
    assert 'remediation_concentration_score' in concentration_response.json()
    assert concentration_response.json()['concentration_band'] in {'distributed', 'watch', 'concentrated'}
    assert concentration_response.json()['total_open_action_items'] >= 3

    containment_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-containment-index?days_horizon=7',
        headers=H,
    )
    assert containment_response.status_code == 200
    assert 'escalation_containment_index' in containment_response.json()
    assert containment_response.json()['containment_band'] in {'contained', 'watch', 'breach-risk'}
    assert containment_response.json()['open_action_items'] >= 3


def test_workflow_connector_remediation_readiness_balance_and_escalation_load_shedding_forecast(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'heap-sync',
            'vendor': 'Heap',
            'auth_type': 'api_key',
            'capabilities': ['behavior_analytics'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation readiness balance and load shedding forecast test',
            'summary': 'Validate remediation readiness balance and escalation load shedding forecast APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Rebalance owner readiness capacity', 'readiness@nuxtron.local'),
        ('Drain urgent remediation commitments', 'readiness@nuxtron.local'),
        ('Assign pending ownerless response task', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    readiness_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-readiness-balance?max_open_items_per_owner=2',
        headers=H,
    )
    assert readiness_response.status_code == 200
    assert 'remediation_readiness_balance' in readiness_response.json()
    assert readiness_response.json()['readiness_band'] in {'balanced', 'watch', 'strained'}
    assert readiness_response.json()['total_open_action_items'] >= 3

    shedding_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-load-shedding-forecast?days_horizon=7',
        headers=H,
    )
    assert shedding_response.status_code == 200
    assert 'required_daily_load_shedding' in shedding_response.json()
    assert shedding_response.json()['shedding_band'] in {'light', 'moderate', 'heavy'}
    assert shedding_response.json()['open_action_items'] >= 3


def test_workflow_connector_remediation_pressure_index_and_escalation_relief_forecast(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'intercom-sync',
            'vendor': 'Intercom',
            'auth_type': 'oauth2',
            'capabilities': ['support_sync'],
            'rate_limit_per_minute': 155,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation pressure and escalation relief forecast test',
            'summary': 'Validate remediation pressure index and escalation relief forecast APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Reduce remediation pressure load', 'pressure@nuxtron.local'),
        ('Advance urgent support follow-up', 'pressure@nuxtron.local'),
        ('Assign pending recovery task', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    pressure_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-pressure-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert pressure_response.status_code == 200
    assert 'remediation_pressure_index' in pressure_response.json()
    assert pressure_response.json()['pressure_band'] in {'relieved', 'watch', 'pressured'}
    assert pressure_response.json()['total_open_action_items'] >= 3

    relief_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-relief-forecast?days_horizon=7',
        headers=H,
    )
    assert relief_response.status_code == 200
    assert 'required_daily_relief_actions' in relief_response.json()
    assert relief_response.json()['relief_band'] in {'relievable', 'tight', 'stretched'}
    assert relief_response.json()['open_action_items'] >= 3


def test_workflow_connector_remediation_recovery_index_and_escalation_recovery_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'customerio-sync',
            'vendor': 'Customer.io',
            'auth_type': 'api_key',
            'capabilities': ['lifecycle_automation'],
            'rate_limit_per_minute': 145,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation recovery and escalation recovery index test',
            'summary': 'Validate remediation recovery index and escalation recovery index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Restore remediation recovery posture', 'recovery@nuxtron.local'),
        ('Advance urgent recovery follow-up', 'recovery@nuxtron.local'),
        ('Assign pending recovery backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    recovery_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-recovery-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert recovery_response.status_code == 200
    assert 'remediation_recovery_index' in recovery_response.json()
    assert recovery_response.json()['recovery_band'] in {'recovering', 'watch', 'delayed'}
    assert recovery_response.json()['total_open_action_items'] >= 3

    escalation_recovery_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-recovery-index?days_horizon=7',
        headers=H,
    )
    assert escalation_recovery_response.status_code == 200
    assert 'required_daily_recovery_actions' in escalation_recovery_response.json()
    assert escalation_recovery_response.json()['recovery_band'] in {'recovered', 'tight', 'lagging'}
    assert escalation_recovery_response.json()['open_action_items'] >= 3


def test_workflow_connector_remediation_resilience_forecast_and_escalation_stability_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'salesloft-sync',
            'vendor': 'Salesloft',
            'auth_type': 'oauth2',
            'capabilities': ['sales_engagement'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation resilience and escalation stability index test',
            'summary': 'Validate remediation resilience forecast and escalation stability index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Strengthen remediation resilience', 'resilience@nuxtron.local'),
        ('Advance critical recovery follow-up', 'resilience@nuxtron.local'),
        ('Assign remaining resilience backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    resilience_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-resilience-forecast?days_horizon=7',
        headers=H,
    )
    assert resilience_response.status_code == 200
    assert 'remediation_resilience_score' in resilience_response.json()
    assert resilience_response.json()['resilience_band'] in {'resilient', 'watch', 'fragile'}
    assert resilience_response.json()['open_action_items'] >= 3

    stability_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-stability-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert stability_response.status_code == 200
    assert 'escalation_stability_index' in stability_response.json()
    assert stability_response.json()['stability_band'] in {'stable', 'watch', 'unstable', 'volatile'}
    assert stability_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_steadiness_forecast_and_escalation_steadiness_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'zendesk-sync',
            'vendor': 'Zendesk',
            'auth_type': 'oauth2',
            'capabilities': ['ticketing'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation steadiness and escalation steadiness index test',
            'summary': 'Validate remediation steadiness forecast and escalation steadiness index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Stabilize remediation steadiness', 'steadiness@nuxtron.local'),
        ('Advance urgent steadiness follow-up', 'steadiness@nuxtron.local'),
        ('Assign remaining steadiness backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    steadiness_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-steadiness-forecast?days_horizon=7',
        headers=H,
    )
    assert steadiness_response.status_code == 200
    assert 'remediation_steadiness_score' in steadiness_response.json()
    assert steadiness_response.json()['steadiness_band'] in {'steady', 'watch', 'shaky'}
    assert steadiness_response.json()['open_action_items'] >= 3

    escalation_steadiness_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-steadiness-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_steadiness_response.status_code == 200
    assert 'escalation_steadiness_index' in escalation_steadiness_response.json()
    assert escalation_steadiness_response.json()['steadiness_band'] in {'stable', 'watch', 'unstable'}
    assert escalation_steadiness_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_durability_forecast_and_escalation_durability_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'front-sync',
            'vendor': 'Front',
            'auth_type': 'oauth2',
            'capabilities': ['shared_inbox'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation durability and escalation durability index test',
            'summary': 'Validate remediation durability forecast and escalation durability index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Strengthen remediation durability', 'durability@nuxtron.local'),
        ('Advance urgent durability follow-up', 'durability@nuxtron.local'),
        ('Assign remaining durability backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    durability_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-durability-forecast?days_horizon=7',
        headers=H,
    )
    assert durability_response.status_code == 200
    assert 'remediation_durability_score' in durability_response.json()
    assert durability_response.json()['durability_band'] in {'durable', 'watch', 'brittle'}
    assert durability_response.json()['open_action_items'] >= 3

    escalation_durability_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-durability-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_durability_response.status_code == 200
    assert 'escalation_durability_index' in escalation_durability_response.json()
    assert escalation_durability_response.json()['durability_band'] in {'durable', 'watch', 'fragile'}
    assert escalation_durability_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_stability_forecast_and_escalation_stability_forecast(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'helpdesk-sync',
            'vendor': 'Helpdesk',
            'auth_type': 'api_key',
            'capabilities': ['support_ops'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation stability and escalation stability forecast test',
            'summary': 'Validate remediation stability forecast and escalation stability forecast APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Strengthen remediation stability', 'stability@nuxtron.local'),
        ('Advance urgent stability follow-up', 'stability@nuxtron.local'),
        ('Assign remaining stability backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    stability_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-stability-forecast?days_horizon=7',
        headers=H,
    )
    assert stability_response.status_code == 200
    assert 'remediation_stability_score' in stability_response.json()
    assert stability_response.json()['stability_band'] in {'stable', 'watch', 'unstable', 'volatile'}
    assert stability_response.json()['open_action_items'] >= 3

    escalation_stability_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-stability-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_stability_response.status_code == 200
    assert 'escalation_stability_index' in escalation_stability_response.json()
    assert escalation_stability_response.json()['stability_band'] in {'stable', 'watch', 'volatile', 'unstable'}
    assert escalation_stability_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_consistency_forecast_and_escalation_consistency_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'intercom-inbox-sync',
            'vendor': 'Intercom',
            'auth_type': 'api_key',
            'capabilities': ['inbox_automation'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation consistency and escalation consistency index test',
            'summary': 'Validate remediation consistency forecast and escalation consistency index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Strengthen remediation consistency', 'consistency@nuxtron.local'),
        ('Advance urgent consistency follow-up', 'consistency@nuxtron.local'),
        ('Assign remaining consistency backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    consistency_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-consistency-forecast?days_horizon=7',
        headers=H,
    )
    assert consistency_response.status_code == 200
    assert 'remediation_consistency_score' in consistency_response.json()
    assert consistency_response.json()['consistency_band'] in {'consistent', 'watch', 'inconsistent'}
    assert consistency_response.json()['open_action_items'] >= 3

    escalation_consistency_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-consistency-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_consistency_response.status_code == 200
    assert 'escalation_consistency_index' in escalation_consistency_response.json()
    assert escalation_consistency_response.json()['consistency_band'] in {'consistent', 'watch', 'volatile'}
    assert escalation_consistency_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_alignment_forecast_and_escalation_alignment_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'notion-sync',
            'vendor': 'Notion',
            'auth_type': 'api_key',
            'capabilities': ['workspace_automation'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation alignment and escalation alignment index test',
            'summary': 'Validate remediation alignment forecast and escalation alignment index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Strengthen remediation alignment', 'alignment@nuxtron.local'),
        ('Advance urgent alignment follow-up', 'alignment@nuxtron.local'),
        ('Assign remaining alignment backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    alignment_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-alignment-forecast?days_horizon=7',
        headers=H,
    )
    assert alignment_response.status_code == 200
    assert 'remediation_alignment_score' in alignment_response.json()
    assert alignment_response.json()['alignment_band'] in {'aligned', 'watch', 'misaligned'}
    assert alignment_response.json()['open_action_items'] >= 3

    escalation_alignment_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-alignment-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_alignment_response.status_code == 200
    assert 'escalation_alignment_index' in escalation_alignment_response.json()
    assert escalation_alignment_response.json()['alignment_band'] in {'aligned', 'watch', 'misaligned'}
    assert escalation_alignment_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_clarity_forecast_and_escalation_clarity_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'linear-sync',
            'vendor': 'Linear',
            'auth_type': 'api_key',
            'capabilities': ['issue_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation clarity and escalation clarity index test',
            'summary': 'Validate remediation clarity forecast and escalation clarity index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Strengthen remediation clarity', 'clarity@nuxtron.local'),
        ('Advance urgent clarity follow-up', 'clarity@nuxtron.local'),
        ('Assign remaining clarity backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    clarity_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-clarity-forecast?days_horizon=7',
        headers=H,
    )
    assert clarity_response.status_code == 200
    assert 'remediation_clarity_score' in clarity_response.json()
    assert clarity_response.json()['clarity_band'] in {'clear', 'watch', 'unclear'}
    assert clarity_response.json()['open_action_items'] >= 3

    escalation_clarity_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-clarity-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_clarity_response.status_code == 200
    assert 'escalation_clarity_index' in escalation_clarity_response.json()
    assert escalation_clarity_response.json()['clarity_band'] in {'clear', 'watch', 'unclear'}
    assert escalation_clarity_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_composure_forecast_and_escalation_composure_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'airtable-sync',
            'vendor': 'Airtable',
            'auth_type': 'api_key',
            'capabilities': ['database_automation'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation composure and escalation composure index test',
            'summary': 'Validate remediation composure forecast and escalation composure index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Strengthen remediation composure', 'composure@nuxtron.local'),
        ('Advance urgent composure follow-up', 'composure@nuxtron.local'),
        ('Assign remaining composure backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    composure_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-composure-forecast?days_horizon=7',
        headers=H,
    )
    assert composure_response.status_code == 200
    assert 'remediation_composure_score' in composure_response.json()
    assert composure_response.json()['composure_band'] in {'composed', 'watch', 'strained'}
    assert composure_response.json()['open_action_items'] >= 3

    escalation_composure_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-composure-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_composure_response.status_code == 200
    assert 'escalation_composure_index' in escalation_composure_response.json()
    assert escalation_composure_response.json()['composure_band'] in {'composed', 'watch', 'strained'}
    assert escalation_composure_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_focus_forecast_and_escalation_focus_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation focus and escalation focus index test',
            'summary': 'Validate remediation focus forecast and escalation focus index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Strengthen remediation focus', 'focus@nuxtron.local'),
        ('Advance urgent focus follow-up', 'focus@nuxtron.local'),
        ('Assign remaining focus backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    focus_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-focus-forecast?days_horizon=7',
        headers=H,
    )
    assert focus_response.status_code == 200
    assert 'remediation_focus_score' in focus_response.json()
    assert focus_response.json()['focus_band'] in {'focused', 'watch', 'scattered'}
    assert focus_response.json()['open_action_items'] >= 3

    escalation_focus_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-focus-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_focus_response.status_code == 200
    assert 'escalation_focus_index' in escalation_focus_response.json()
    assert escalation_focus_response.json()['focus_band'] in {'focused', 'watch', 'diffuse'}
    assert escalation_focus_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_attention_forecast_and_escalation_attention_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation attention and escalation attention index test',
            'summary': 'Validate remediation attention forecast and escalation attention index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Restore explicit owner attention', 'attention@nuxtron.local'),
        ('Advance overloaded owner queue', 'attention@nuxtron.local'),
        ('Assign remaining unattended backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    attention_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-attention-forecast?days_horizon=7',
        headers=H,
    )
    assert attention_response.status_code == 200
    assert 'remediation_attention_score' in attention_response.json()
    assert attention_response.json()['attention_band'] in {'attentive', 'watch', 'fractured'}
    assert attention_response.json()['open_action_items'] >= 3

    escalation_attention_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-attention-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_attention_response.status_code == 200
    assert 'escalation_attention_index' in escalation_attention_response.json()
    assert escalation_attention_response.json()['attention_band'] in {'attentive', 'watch', 'distracted'}
    assert escalation_attention_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_coordination_forecast_and_escalation_coordination_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation coordination and escalation coordination index test',
            'summary': 'Validate remediation coordination forecast and escalation coordination index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Coordinate shared remediation lane', 'coordination@nuxtron.local'),
        ('Balance owner coordination backlog', 'coordination@nuxtron.local'),
        ('Assign fragmented coordination follow-up', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    coordination_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-coordination-forecast?days_horizon=7',
        headers=H,
    )
    assert coordination_response.status_code == 200
    assert 'remediation_coordination_score' in coordination_response.json()
    assert coordination_response.json()['coordination_band'] in {'coordinated', 'watch', 'fragmented'}
    assert coordination_response.json()['open_action_items'] >= 3

    escalation_coordination_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-coordination-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_coordination_response.status_code == 200
    assert 'escalation_coordination_index' in escalation_coordination_response.json()
    assert escalation_coordination_response.json()['coordination_band'] in {'coordinated', 'watch', 'fragmented'}
    assert escalation_coordination_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_orchestration_forecast_and_escalation_orchestration_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation orchestration and escalation orchestration index test',
            'summary': 'Validate remediation orchestration forecast and escalation orchestration index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Orchestrate shared remediation flow', 'orchestration@nuxtron.local'),
        ('Balance orchestration backlog lane', 'orchestration@nuxtron.local'),
        ('Assign disjointed orchestration item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    orchestration_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-orchestration-forecast?days_horizon=7',
        headers=H,
    )
    assert orchestration_response.status_code == 200
    assert 'remediation_orchestration_score' in orchestration_response.json()
    assert orchestration_response.json()['orchestration_band'] in {'orchestrated', 'watch', 'disjointed'}
    assert orchestration_response.json()['open_action_items'] >= 3

    escalation_orchestration_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-orchestration-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_orchestration_response.status_code == 200
    assert 'escalation_orchestration_index' in escalation_orchestration_response.json()
    assert escalation_orchestration_response.json()['orchestration_band'] in {'orchestrated', 'watch', 'disjointed'}
    assert escalation_orchestration_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_synchronization_forecast_and_escalation_synchronization_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation synchronization and escalation synchronization index test',
            'summary': 'Validate remediation synchronization forecast and escalation synchronization index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Synchronize owner remediation queue', 'sync@nuxtron.local'),
        ('Align urgent synchronization follow-up', 'sync@nuxtron.local'),
        ('Assign desynced backlog action item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    synchronization_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-synchronization-forecast?days_horizon=7',
        headers=H,
    )
    assert synchronization_response.status_code == 200
    assert 'remediation_synchronization_score' in synchronization_response.json()
    assert synchronization_response.json()['synchronization_band'] in {'synchronized', 'watch', 'desynced'}
    assert synchronization_response.json()['open_action_items'] >= 3

    escalation_synchronization_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-synchronization-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_synchronization_response.status_code == 200
    assert 'escalation_synchronization_index' in escalation_synchronization_response.json()
    assert escalation_synchronization_response.json()['synchronization_band'] in {'synchronized', 'watch', 'desynced'}
    assert escalation_synchronization_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_harmony_forecast_and_escalation_harmony_index(client: TestClient) -> None:
    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation harmony and escalation harmony index test',
            'summary': 'Validate remediation harmony forecast and escalation harmony index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Align harmonized owner queue', 'harmony@nuxtron.local'),
        ('Balance harmony follow-up lane', 'harmony@nuxtron.local'),
        ('Assign discordant backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    harmony_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-harmony-forecast?days_horizon=7',
        headers=H,
    )
    assert harmony_response.status_code == 200
    assert 'remediation_harmony_score' in harmony_response.json()
    assert harmony_response.json()['harmony_band'] in {'harmonized', 'watch', 'discordant'}
    assert harmony_response.json()['open_action_items'] >= 3

    escalation_harmony_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-harmony-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_harmony_response.status_code == 200
    assert 'escalation_harmony_index' in escalation_harmony_response.json()
    assert escalation_harmony_response.json()['harmony_band'] in {'harmonized', 'watch', 'discordant'}
    assert escalation_harmony_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_rhythm_forecast_and_escalation_rhythm_index(client: TestClient) -> None:
    from backend.fastapi.app import legacy_main as app_main

    app_main._rate_buckets.clear()

    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation rhythm and escalation rhythm index test',
            'summary': 'Validate remediation rhythm forecast and escalation rhythm index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Stabilize owner rhythm queue', 'rhythm@nuxtron.local'),
        ('Balance rhythm follow-up load', 'rhythm@nuxtron.local'),
        ('Assign erratic backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    rhythm_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-rhythm-forecast?days_horizon=7',
        headers=H,
    )
    assert rhythm_response.status_code == 200
    assert 'remediation_rhythm_score' in rhythm_response.json()
    assert rhythm_response.json()['rhythm_band'] in {'steady', 'watch', 'erratic'}
    assert rhythm_response.json()['open_action_items'] >= 3

    escalation_rhythm_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-rhythm-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_rhythm_response.status_code == 200
    assert 'escalation_rhythm_index' in escalation_rhythm_response.json()
    assert escalation_rhythm_response.json()['rhythm_band'] in {'steady', 'watch', 'erratic'}
    assert escalation_rhythm_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_tempo_forecast_and_escalation_tempo_index(client: TestClient) -> None:
    from backend.fastapi.app import legacy_main as app_main

    app_main._rate_buckets.clear()

    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation tempo and escalation tempo index test',
            'summary': 'Validate remediation tempo forecast and escalation tempo index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Stabilize owner tempo queue', 'tempo@nuxtron.local'),
        ('Balance tempo follow-up load', 'tempo@nuxtron.local'),
        ('Assign rushing backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    tempo_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-tempo-forecast?days_horizon=7',
        headers=H,
    )
    assert tempo_response.status_code == 200
    assert 'remediation_tempo_score' in tempo_response.json()
    assert tempo_response.json()['tempo_band'] in {'steady', 'watch', 'rushing'}
    assert tempo_response.json()['open_action_items'] >= 3

    escalation_tempo_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-tempo-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_tempo_response.status_code == 200
    assert 'escalation_tempo_index' in escalation_tempo_response.json()
    assert escalation_tempo_response.json()['tempo_band'] in {'steady', 'watch', 'rushing'}
    assert escalation_tempo_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_cadence_forecast_and_escalation_cadence_index(client: TestClient) -> None:
    from backend.fastapi.app import legacy_main as app_main

    app_main._rate_buckets.clear()

    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation cadence and escalation cadence index test',
            'summary': 'Validate remediation cadence forecast and escalation cadence index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Stabilize owner cadence queue', 'cadence@nuxtron.local'),
        ('Balance cadence follow-up load', 'cadence@nuxtron.local'),
        ('Assign choppy backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    cadence_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-cadence-forecast?days_horizon=7',
        headers=H,
    )
    assert cadence_response.status_code == 200
    assert 'remediation_cadence_score' in cadence_response.json()
    assert cadence_response.json()['cadence_band'] in {'steady', 'watch', 'choppy'}
    assert cadence_response.json()['open_action_items'] >= 3

    escalation_cadence_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-cadence-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_cadence_response.status_code == 200
    assert 'escalation_cadence_index' in escalation_cadence_response.json()
    assert escalation_cadence_response.json()['cadence_band'] in {'steady', 'watch', 'choppy'}
    assert escalation_cadence_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_remediation_stability_forecast_and_escalation_stability_index(client: TestClient) -> None:
    from backend.fastapi.app import legacy_main as app_main

    app_main._rate_buckets.clear()

    connector_response = client.post(
        '/workflow-connectors',
        headers=H,
        json={
            'name': 'jira-sync',
            'vendor': 'Jira',
            'auth_type': 'oauth2',
            'capabilities': ['project_tracking'],
            'rate_limit_per_minute': 150,
            'error_budget_pct': 1.0,
        },
    )
    assert connector_response.status_code == 200
    connector_id = int(connector_response.json()['connector']['id'])

    postmortem_response = client.post(
        f'/workflow-connectors/{connector_id}/postmortems',
        headers=H,
        json={
            'title': 'Remediation stability and escalation stability index test',
            'summary': 'Validate remediation stability forecast and escalation stability index APIs.',
            'incident_event_ids': [],
            'action_items': [],
        },
    )
    assert postmortem_response.status_code == 200
    postmortem_id = int(postmortem_response.json()['postmortem']['id'])

    for title, owner in [
        ('Stabilize owner action queue', 'stability@nuxtron.local'),
        ('Balance stability follow-up load', 'stability@nuxtron.local'),
        ('Assign volatile backlog item', ''),
    ]:
        create_item_response = client.post(
            f'/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items',
            headers=H,
            json={'title': title, 'owner': owner, 'due_in_hours': 1},
        )
        assert create_item_response.status_code == 200

    overdue_response = client.post(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        headers=H,
        json={'connector_id': connector_id, 'limit': 100, 'include_not_due': True},
    )
    assert overdue_response.status_code == 200
    assert overdue_response.json()['count'] >= 1

    stability_response = client.get(
        '/workflow-connectors/postmortems/action-items/remediation-stability-forecast?days_horizon=7',
        headers=H,
    )
    assert stability_response.status_code == 200
    assert 'remediation_stability_score' in stability_response.json()
    assert stability_response.json()['stability_band'] in {'stable', 'watch', 'volatile'}
    assert stability_response.json()['open_action_items'] >= 3

    escalation_stability_response = client.get(
        '/workflow-connectors/postmortems/action-items/escalation-stability-index?max_open_items_per_owner=2',
        headers=H,
    )
    assert escalation_stability_response.status_code == 200
    assert 'escalation_stability_index' in escalation_stability_response.json()
    assert escalation_stability_response.json()['stability_band'] in {'stable', 'watch', 'volatile'}
    assert escalation_stability_response.json()['total_open_action_items'] >= 3


def test_workflow_connector_postmortem_escalation_routing_policy_defaults_and_upsert(client: TestClient) -> None:
    get_default_response = client.get('/workflow-connectors/postmortems/escalation-routing-policy', headers=H)
    assert get_default_response.status_code == 200
    default_policy = get_default_response.json()['policy']
    assert 'medium_threshold_hours' in default_policy

    upsert_response = client.post(
        '/workflow-connectors/postmortems/escalation-routing-policy',
        headers=H,
        json={
            'enabled': True,
            'paging_start_hour_utc': 6,
            'paging_end_hour_utc': 22,
            'in_window_channel': 'pagerduty',
            'off_window_channel': 'email',
            'medium_threshold_hours': 2,
            'high_threshold_hours': 12,
            'critical_threshold_hours': 36,
            'medium_recipients': ['ops@nuxtron.local'],
            'high_recipients': ['incident@nuxtron.local'],
            'critical_recipients': ['sre@nuxtron.local'],
        },
    )
    assert upsert_response.status_code == 200
    assert upsert_response.json()['policy']['enabled'] is True

    get_updated_response = client.get('/workflow-connectors/postmortems/escalation-routing-policy', headers=H)
    assert get_updated_response.status_code == 200
    updated_policy = get_updated_response.json()['policy']
    assert updated_policy['critical_threshold_hours'] == 36


def test_workflow_connector_postmortem_escalation_cadence_policy_defaults_and_upsert(client: TestClient) -> None:
    get_default_response = client.get('/workflow-connectors/postmortems/escalation-cadence-policy', headers=H)
    assert get_default_response.status_code == 200
    default_policy = get_default_response.json()['policy']
    assert 'l2_after_minutes' in default_policy

    upsert_response = client.post(
        '/workflow-connectors/postmortems/escalation-cadence-policy',
        headers=H,
        json={
            'enabled': True,
            'l2_after_minutes': 10,
            'l3_after_minutes': 30,
            'repage_interval_minutes': 5,
            'max_repages': 6,
            'l1_recipients': ['ops@nuxtron.local'],
            'l2_recipients': ['incident@nuxtron.local'],
            'l3_recipients': ['sre@nuxtron.local'],
        },
    )
    assert upsert_response.status_code == 200
    assert upsert_response.json()['policy']['enabled'] is True

    get_updated_response = client.get('/workflow-connectors/postmortems/escalation-cadence-policy', headers=H)
    assert get_updated_response.status_code == 200
    updated_policy = get_updated_response.json()['policy']
    assert updated_policy['repage_interval_minutes'] == 5


def test_workflow_graph_validation_template_instantiation_and_webhook_trigger(client: TestClient) -> None:
    validate_response = client.post(
        '/workflows/validate-graph',
        headers=H,
        json={
            'start_step_id': 's1',
            'steps': [
                {
                    'step_id': 's1',
                    'action_type': 'branch_condition',
                    'config': {'field': 'plan', 'equals': 'pro'},
                    'branch_yes': 's2',
                    'branch_no': 's3',
                },
                {
                    'step_id': 's2',
                    'action_type': 'send_webhook',
                    'config': {'url': 'https://example.invalid/hooks/pro'},
                },
                {
                    'step_id': 's3',
                    'action_type': 'notify_rep',
                    'config': {'channel': 'slack'},
                },
            ],
        },
    )
    assert validate_response.status_code == 200
    assert validate_response.json()['valid'] is True
    assert validate_response.json()['step_count'] == 3

    template_response = client.post(
        '/workflows/templates',
        headers=H,
        json={
            'name': 'Signup Qualification Template',
            'description': 'Route pro users to webhook and others to notifications.',
            'category': 'lead_qualification',
            'trigger_type': 'webhook',
            'tags': ['gumloop-parity', 'qualification'],
            'steps': [
                {
                    'step_id': 's1',
                    'action_type': 'branch_condition',
                    'config': {'field': 'plan', 'equals': 'pro'},
                    'branch_yes': 's2',
                    'branch_no': 's3',
                },
                {
                    'step_id': 's2',
                    'action_type': 'send_webhook',
                    'config': {'url': 'https://example.invalid/hooks/pro'},
                },
                {
                    'step_id': 's3',
                    'action_type': 'notify_rep',
                    'config': {'channel': 'slack'},
                },
            ],
        },
    )
    assert template_response.status_code == 200
    template_id = int(template_response.json()['template']['id'])

    instantiate_response = client.post(
        f'/workflows/templates/{template_id}/instantiate',
        headers=H,
        json={
            'name': 'Signup Qualification Workflow',
            'description': 'Instantiated from reusable template.',
            'trigger_conditions': [{'field': 'source', 'value': 'landing_page'}],
            're_enrollment': True,
            're_enrollment_days': 14,
        },
    )
    assert instantiate_response.status_code == 200
    workflow_id = int(instantiate_response.json()['workflow']['id'])

    webhook_response = client.post(
        '/workflows/triggers/webhook',
        headers=H,
        json={
            'event_type': 'webhook',
            'external_event_id': 'evt-signup-001',
            'payload': {
                'source': 'landing_page',
                'plan': 'pro',
                'contact_id': 'contact-001',
                'contact_email': 'contact-001@example.local',
            },
        },
    )
    assert webhook_response.status_code == 200
    assert webhook_response.json()['executed'] >= 1

    executions_response = client.get(f'/workflows/{workflow_id}/executions', headers=H)
    assert executions_response.status_code == 200
    assert executions_response.json()['total'] >= 1

    duplicate_webhook_response = client.post(
        '/workflows/triggers/webhook',
        headers=H,
        json={
            'event_type': 'webhook',
            'external_event_id': 'evt-signup-001',
            'payload': {
                'source': 'landing_page',
                'plan': 'pro',
                'contact_id': 'contact-001',
                'contact_email': 'contact-001@example.local',
            },
        },
    )
    assert duplicate_webhook_response.status_code == 200
    assert duplicate_webhook_response.json()['duplicate'] is True


def test_workflow_platform_production_readiness_matrix(client: TestClient) -> None:
    response = client.get('/workflow-platform/production-readiness', headers=H)
    assert response.status_code == 200
    payload = response.json()
    assert payload['completion_pct'] >= 90
    assert payload['implemented_count'] == payload['total_count']
    assert len(payload.get('matrix', [])) >= 10
    assert any(vendor.get('name') == 'OpenAI' for vendor in payload.get('vendors', []))


def test_workflow_platform_completion_chart(client: TestClient) -> None:
    response = client.get('/workflow-platform/completion-chart', headers=H)
    assert response.status_code == 200
    payload = response.json()
    assert payload.get('status') == 'ok'
    assert isinstance(payload.get('as_of'), str)
    assert payload.get('implemented_count') == payload.get('total_count')

    chart = payload.get('chart', {})
    summary = chart.get('summary', {})
    assert summary.get('done') == payload.get('implemented_count')
    assert summary.get('remaining') == 0
    assert summary.get('percent') == payload.get('completion_pct')
    assert len(chart.get('features', [])) >= 10
