import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'tenant-owly-e2e'}


@pytest.fixture(scope='module')
def client() -> TestClient:
    from backend.fastapi.app.main import app  # type: ignore[import-untyped]

    return TestClient(app, raise_server_exceptions=False)


class TestOwlyWriterAi:
    def test_generate_owly_writer_content(self, client: TestClient) -> None:
        response = client.post(
            '/social/ai/owly-writer/generate',
            headers=H,
            json={
                'topic': 'Launch our social analytics suite',
                'goal': 'engagement',
                'style': 'professional',
                'audience': 'B2B marketers',
                'platforms': ['linkedin', 'twitter'],
                'include_hashtags': True,
                'include_emoji': True,
                'include_cta': True,
                'variations_per_platform': 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        generation = data['generation']
        assert generation['provider'] == 'heuristic_v2'
        assert len(generation['items']) == 4
        assert all('quality' in item for item in generation['items'])

    def test_generate_owly_writer_rejects_unsupported_platform(self, client: TestClient) -> None:
        response = client.post(
            '/social/ai/owly-writer/generate',
            headers=H,
            json={
                'topic': 'Test platform validation',
                'goal': 'engagement',
                'style': 'casual',
                'audience': 'Creators',
                'platforms': ['myspace'],
                'variations_per_platform': 1,
            },
        )

        assert response.status_code == 422

    def test_owly_writer_history(self, client: TestClient) -> None:
        response = client.get('/social/ai/owly-writer/history?limit=5', headers=H)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['total'] >= 1
        assert len(data['items']) >= 1

    def test_legacy_generate_caption_works_without_openai(self, client: TestClient) -> None:
        response = client.post(
            '/social/ai/generate-caption',
            headers=H,
            params=[
                ('topic', 'Improve social campaign quality'),
                ('style', 'professional'),
                ('platforms', 'linkedin'),
                ('platforms', 'twitter'),
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['provider'] == 'heuristic_v2'
        assert set(data['captions'].keys()) == {'linkedin', 'twitter'}

    def test_best_time_to_post_returns_evidence(self, client: TestClient) -> None:
        seed = client.post(
            '/social/content/create',
            headers=H,
            json={
                'title': 'Best Time Seed',
                'caption': 'Testing best-time recommendation quality',
                'media_assets': [],
                'platforms': ['linkedin'],
                'requires_approval': False,
            },
        )
        assert seed.status_code == 200

        response = client.post(
            '/social/ai/best-time-to-post?platform=linkedin&content_type=video',
            headers=H,
        )

        assert response.status_code == 200
        data = response.json()
        assert data['platform'] == 'linkedin'
        assert data['basis'] == 'parity-heuristic-v3'
        assert len(data['recommended_slots_utc']) == 3
        assert 0.0 <= data['confidence'] <= 1.0
        assert 'historical_sample_size' in data['evidence']

    def test_sentiment_analysis_scores_are_calibrated(self, client: TestClient) -> None:
        response = client.post(
            '/social/ai/sentiment-analysis?text=I love this product but the onboarding bug is terrible',
            headers=H,
        )

        assert response.status_code == 200
        data = response.json()
        assert data['sentiment'] in {'positive', 'negative', 'neutral'}
        assert set(data['scores'].keys()) == {'positive', 'negative', 'neutral'}
        total = sum(float(value) for value in data['scores'].values())
        assert 0.99 <= total <= 1.01
        assert 0.0 <= float(data['confidence']) <= 1.0
        assert 'token_hits' in data


class TestTeamInviteFlow:
    def test_invite_member_with_json_body(self, client: TestClient) -> None:
        response = client.post(
            '/social/team/invite',
            headers=H,
            json={'email': 'member@example.com', 'role': 'editor'},
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['invite']['email'] == 'member@example.com'

    def test_list_team_members(self, client: TestClient) -> None:
        response = client.get('/social/team/members', headers=H)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['total'] >= 1
        assert any(item['email'] == 'member@example.com' for item in data['members'])
