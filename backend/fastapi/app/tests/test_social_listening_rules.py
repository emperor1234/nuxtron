from __future__ import annotations

from types import SimpleNamespace

from backend.fastapi.app.services import social_reviews


def test_list_social_listening_rules_is_workspace_scoped_and_discloses_memory_storage() -> None:
    original_store = social_reviews._social_listening_alert_rules_memory
    store = [
        {
            'id': 1,
            'tenant_id': 'workspace-a',
            'name': 'Older rule',
            'query': None,
            'platform': None,
            'min_engagement': 10,
            'negative_only': True,
            'enabled': True,
            'created_at': '2026-10-01T00:00:00Z',
        },
        {
            'id': 2,
            'tenant_id': 'workspace-a',
            'name': 'Newer rule',
            'query': 'brand',
            'platform': 'linkedin',
            'min_engagement': 5,
            'negative_only': False,
            'enabled': True,
            'created_at': '2026-10-02T00:00:00Z',
        },
        {
            'id': 3,
            'tenant_id': 'workspace-b',
            'name': 'Other workspace',
            'query': None,
            'platform': None,
            'min_engagement': 0,
            'negative_only': True,
            'enabled': True,
            'created_at': '2026-10-03T00:00:00Z',
        },
    ]
    social_reviews.set_memory_stores(social_listening_alert_rules_memory=store)
    try:
        result = social_reviews.list_social_listening_alert_rules(SimpleNamespace(tenant_id='workspace-a'))
    finally:
        social_reviews.set_memory_stores(social_listening_alert_rules_memory=original_store)

    assert result['status'] == 'ok'
    assert result['tenant_id'] == 'workspace-a'
    assert result['persistence'] == 'memory-fallback'
    assert result['count'] == 2
    assert [rule['name'] for rule in result['rules']] == ['Newer rule', 'Older rule']
    assert all(rule['tenant_id'] == 'workspace-a' for rule in result['rules'])
