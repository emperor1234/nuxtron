from __future__ import annotations

import os

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('APP_ENC_KEY', '00' * 32)
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')

from fastapi.testclient import TestClient


def _headers(tenant_id: str = 'tenant-manychat-e2e') -> dict[str, str]:
    return {
        'X-API-Key': os.getenv('FASTAPI_API_KEY', 'test-api-key'),
        'X-Tenant-Id': tenant_id,
    }


def test_manychat_full_automation_slice() -> None:
    from backend.fastapi.app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    headers = _headers()

    overview = client.get('/social/manychat/overview', headers=headers)
    assert overview.status_code == 200
    overview_payload = overview.json()
    assert overview_payload['status'] == 'ok'
    assert overview_payload['counts']['tags'] >= 1
    assert isinstance(overview_payload['vendors'], list)
    assert len(overview_payload['vendors']) >= 1

    create_tag = client.post('/social/manychat/tags', headers=headers, json={'name': 'DemoRequested', 'color': '#0891b2'})
    assert create_tag.status_code == 200
    tag_id = int(create_tag.json()['item']['id'])

    create_segment = client.post(
        '/social/manychat/segments',
        headers=headers,
        json={
            'name': 'Demo Segment',
            'description': 'Users asking for demos',
            'conditions': [{'field': 'tag', 'operator': 'contains', 'value': 'DemoRequested'}],
        },
    )
    assert create_segment.status_code == 200
    segment_id = int(create_segment.json()['item']['id'])

    create_flow = client.post(
        '/social/manychat/flows',
        headers=headers,
        json={
            'name': 'Demo Flow',
            'channel': 'instagram',
            'trigger_type': 'keyword',
            'trigger_value': 'demo',
            'steps': [
                {'type': 'message', 'text': 'Thanks for requesting a demo.'},
                {'type': 'tag', 'name': 'DemoRequested'},
            ],
            'status': 'active',
        },
    )
    assert create_flow.status_code == 200

    create_keyword = client.post(
        '/social/manychat/keywords',
        headers=headers,
        json={
            'keyword': 'demo',
            'channel': 'instagram',
            'reply_text': 'We sent your demo guide in DM.',
            'assign_tag_ids': [tag_id],
        },
    )
    assert create_keyword.status_code == 200

    create_sequence = client.post(
        '/social/manychat/sequences',
        headers=headers,
        json={
            'name': 'Demo Nurture',
            'channel': 'instagram',
            'steps': [
                {'day_offset': 0, 'message': 'Welcome to the demo series.'},
                {'day_offset': 1, 'message': 'Here is a setup checklist.'},
            ],
            'enrollment_trigger': 'tag_added',
        },
    )
    assert create_sequence.status_code == 200
    sequence_id = int(create_sequence.json()['item']['id'])

    enroll = client.post(
        '/social/manychat/sequences/enroll',
        headers=headers,
        json={'contact_handle': '@alex', 'sequence_id': sequence_id},
    )
    assert enroll.status_code == 200
    assert enroll.json()['enrollment']['status'] == 'active'

    assign_tag = client.post(
        '/social/manychat/contacts/tag-assign',
        headers=headers,
        json={'contact_handle': '@alex', 'tag_id': tag_id},
    )
    assert assign_tag.status_code == 200
    assert tag_id in assign_tag.json()['assigned_tag_ids']

    create_broadcast = client.post(
        '/social/manychat/broadcasts',
        headers=headers,
        json={
            'name': 'Demo Day Reminder',
            'channel': 'instagram',
            'target_segment_ids': [segment_id],
            'message': 'Live demo starts in 1 hour.',
        },
    )
    assert create_broadcast.status_code == 200
    broadcast_id = int(create_broadcast.json()['item']['id'])

    send_broadcast = client.post(f'/social/manychat/broadcasts/{broadcast_id}/send', headers=headers)
    assert send_broadcast.status_code == 200
    assert send_broadcast.json()['item']['status'] == 'sent'

    simulate = client.post(
        '/social/manychat/simulate-event',
        headers=headers,
        json={
            'channel': 'instagram',
            'message_text': 'Can I get a demo now?',
            'contact_handle': '@alex',
        },
    )
    assert simulate.status_code == 200
    run = simulate.json()['run']
    assert 'demo' in run['keyword_matches']
    assert len(run['flow_matches']) >= 1
    assert len(run['replies']) >= 1
    assert tag_id in run['assigned_tag_ids']

    tenant_b = _headers('tenant-manychat-isolated')
    isolated = client.get('/social/manychat/flows', headers=tenant_b)
    assert isolated.status_code == 200
    isolated_items = isolated.json()['items']
    assert all(item.get('tenant_id') == 'tenant-manychat-isolated' for item in isolated_items)
