from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')


def _headers(tenant: str = 'growth-branch-tenant') -> dict[str, str]:
    return {'X-API-Key': 'test-api-key', 'X-Tenant-Id': tenant}


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from backend.fastapi.app import main as app_main
    from backend.fastapi.app import memory_stores
    from backend.fastapi.app.main import app

    for value in vars(memory_stores).values():
        if isinstance(value, list):
            value.clear()
    app_main.reset_rate_limits_for_tests()

    yield TestClient(app, raise_server_exceptions=False)

    for value in vars(memory_stores).values():
        if isinstance(value, list):
            value.clear()
    app_main.reset_rate_limits_for_tests()


def test_growth_suite_end_to_end_valid_payloads(client: TestClient) -> None:
    tenant = 'growth-branch-happy'
    h = _headers(tenant)

    bootstrap = client.post('/ops/platform/growth-suite/bootstrap', headers=h, json={})
    assert bootstrap.status_code == 200
    assert bootstrap.json()['totals']['configured'] >= 10

    brand = client.post(
        '/ai/brand-voice/profile',
        headers=h,
        json={
            'profile_name': 'Founder Voice',
            'sample_posts': ['Proof beats opinions in growth.', 'Pipeline over vanity metrics.', 'Specific outcomes win.'],
            'ai_output': 'We share practical growth lessons weekly.',
        },
    )
    assert brand.status_code == 200
    assert brand.json()['brand_voice']['voice_score'] > 0

    ab = client.post(
        '/experiments/ab-tests',
        headers=h,
        json={
            'name': 'CTA angle',
            'base_content': 'Turn attention into attributed pipeline with one repeatable content system.',
            'channel': 'linkedin',
            'goal': 'engagement',
        },
    )
    assert ab.status_code == 200
    test_key = ab.json()['test_key']
    assert len(ab.json()['variants']) == 5

    eval_ab = client.post(
        f'/experiments/ab-tests/{test_key}/evaluate',
        headers=h,
        json={'engagement_scores': [0.22, 0.28, 0.31, 0.26, 0.29], 'republish': True},
    )
    assert eval_ab.status_code == 200
    assert eval_ab.json()['winner']['variant_key'] == 'variant_3'

    roi = client.post(
        '/forecast/roi',
        headers=h,
        json={
            'content_title': 'Quarterly pipeline playbook',
            'platform': 'linkedin',
            'expected_impressions': 15000,
            'historical_revenue': [300.0, 450.0, 500.0],
            'historical_engagement_rate': [0.03, 0.04, 0.05],
        },
    )
    assert roi.status_code == 200
    assert roi.json()['forecast']['projected_revenue'] > 0

    counter = client.post(
        '/features/counter-strike/trigger',
        headers=h,
        json={'competitor_handle': '@rival', 'platform': 'linkedin', 'competitor_post': 'A long competitor post that claims fast growth.'},
    )
    assert counter.status_code == 200
    assert 'sharper CTA' in counter.json()['response_post']

    calendar = client.post(
        '/calendar/content-plan',
        headers=h,
        json={'topics': ['revenue', 'attribution', 'proof'], 'days': 30, 'primary_channel': 'linkedin'},
    )
    assert calendar.status_code == 200
    assert len(calendar.json()['calendar']) == 30

    workspace = client.post(
        '/agency/workspaces',
        headers=h,
        json={'name': 'Agency Alpha', 'owner_email': 'owner@example.com', 'clients': ['Client A', 'Client B']},
    )
    assert workspace.status_code == 200
    workspace_key = workspace.json()['workspace']['workspace_key']

    member = client.post(
        f'/agency/workspaces/{workspace_key}/members',
        headers=h,
        json={'email': 'editor@example.com', 'role': 'Editor'},
    )
    assert member.status_code == 200
    assert len(member.json()['members']) == 2

    mrr = client.post(
        f'/agency/workspaces/{workspace_key}/mrr',
        headers=h,
        json={'client_name': 'Client A', 'monthly_recurring_revenue': 2500.0},
    )
    assert mrr.status_code == 200
    assert mrr.json()['mrr_total'] == 2500.0

    overview = client.get('/agency/overview', headers=h)
    assert overview.status_code == 200
    assert overview.json()['overview']['workspaces'] >= 1

    audience = client.post('/audience-dna/analyze', headers=h, json={'audience_handles': ['a', 'b', 'c'], 'product_price': 149.0})
    assert audience.status_code == 200
    assert audience.json()['audience']['avg_buyer_score'] > 0

    ira = client.post('/ira/autonomous-brain/health-check', headers=h, json={'focus': 'growth'})
    assert ira.status_code == 200
    assert ira.json()['ira']['health_score'] >= 70

    ads = client.post(
        '/ads/campaigns/draft',
        headers=h,
        json={'campaign_name': 'Launch Wave', 'offer': 'Free audit call', 'primary_message': 'One brief, many channels, measurable outcomes.'},
    )
    assert ads.status_code == 200
    assert ads.json()['ads']['spec_count'] >= 10

    repurpose = client.post(
        '/content/repurpose',
        headers=h,
        json={'source_content': 'We map every post to revenue milestones and sales outcomes for the full quarter.'},
    )
    assert repurpose.status_code == 200
    assert repurpose.json()['repurpose']['hours_saved'] == 12

    geo = client.post(
        '/seo/geo-analyze',
        headers=h,
        json={'content': 'Use citeable stats and concise definitions to improve AI answer visibility.', 'competitors': ['c1', 'c2']},
    )
    assert geo.status_code == 200
    assert geo.json()['geo_seo']['citation_score'] > 0

    email = client.post(
        '/email/ai-generate',
        headers=h,
        json={'source_content': 'Weekly growth insights with clear action items and proof blocks.', 'audience': 'warm leads', 'cta': 'Book a call'},
    )
    assert email.status_code == 200
    assert len(email.json()['email']['drip_sequence']) == 5

    scheduler = client.post(
        '/scheduler/smart-fill',
        headers=h,
        json={'drafts': ['Draft 1', 'Draft 2', 'Draft 3'], 'platform': 'linkedin', 'fill_days': 7},
    )
    assert scheduler.status_code == 200
    assert len(scheduler.json()['scheduler']['scheduled_items']) == 3

    podcast = client.post(
        '/podcast/generate',
        headers=h,
        json={'title': 'Revenue Systems', 'source_text': 'A detailed discussion on proving content impact through attribution and pipeline.'},
    )
    assert podcast.status_code == 200
    assert len(podcast.json()['podcast']['chapters']) == 4

    video = client.post(
        '/video-script/generate',
        headers=h,
        json={'topic': 'Attribution', 'audience': 'founders', 'objective': 'qualified pipeline'},
    )
    assert video.status_code == 200
    assert len(video.json()['video']['scenes']) == 4

    report = client.post('/reports/advanced', headers=h, json={'client_name': 'Client A', 'reporting_window_days': 30})
    assert report.status_code == 200
    assert report.json()['report']['client_name'] == 'Client A'


def test_growth_suite_error_and_summary_fallback_branches(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    tenant = 'growth-branch-error'
    h = _headers(tenant)

    ab_missing = client.post('/experiments/ab-tests/missing/evaluate', headers=h, json={'engagement_scores': [0.5], 'republish': False})
    assert ab_missing.status_code == 404

    memory_stores.growth_suite_records.append(
        {
            'tenant_id': tenant,
            'feature_key': 'auto_ab_testing',
            'resource_type': 'test',
            'resource_key': 'ab_empty',
            'payload': {'variants': []},
            'created_at': '2025-01-01T00:00:00+00:00',
            'updated_at': '2025-01-01T00:00:00+00:00',
        }
    )
    ab_empty = client.post('/experiments/ab-tests/ab_empty/evaluate', headers=h, json={'engagement_scores': [0.5], 'republish': False})
    assert ab_empty.status_code == 422

    missing_member = client.post('/agency/workspaces/none/members', headers=h, json={'email': 'x@example.com', 'role': 'Editor'})
    assert missing_member.status_code == 404

    missing_mrr = client.post('/agency/workspaces/none/mrr', headers=h, json={'client_name': 'Client Missing', 'monthly_recurring_revenue': 200.0})
    assert missing_mrr.status_code == 404

    memory_stores.chatbots.append({'id': 1, 'tenant_id': tenant, 'deployed': True})
    memory_stores.chatbot_leads.append({'id': 1, 'tenant_id': tenant})
    memory_stores.email_campaigns.append({'id': 1, 'tenant_id': tenant})
    memory_stores.scheduled_posts.append({'id': 1, 'tenant_id': tenant})
    memory_stores.linkinbio_pages.append({'id': 1, 'tenant_id': tenant})
    memory_stores.linkinbio_links.append({'id': 1, 'tenant_id': tenant})
    memory_stores.analytics_reports.append({'id': 1, 'tenant_id': tenant})
    memory_stores.crm_contacts.append({'id': 1, 'tenant_id': tenant})
    memory_stores.crm_deals.append({'id': 1, 'tenant_id': tenant})
    memory_stores.revenue_touchpoints.append({'id': 1, 'tenant_id': tenant})
    memory_stores.revenue_conversions.append({'id': 1, 'tenant_id': tenant, 'amount': 120.0})

    summary = client.get('/ops/platform/growth-suite', headers=h)
    assert summary.status_code == 200
    features = {item['key']: item for item in summary.json()['features']}
    assert features['ai_lead_chatbot']['status'] == 'ready'
    assert features['email_marketing']['status'] == 'ready'
    assert features['smart_scheduler']['status'] == 'ready'
    assert features['link_in_bio_builder']['status'] == 'ready'
    assert features['advanced_reports']['status'] == 'ready'
    assert len(features['agency_portal']['metrics']) == 2
    assert len(features['roi_forecaster']['metrics']) == 2