"""The AI success path, exercised over real HTTP against an OpenAI-compatible server.

A local server stands in for the provider, so the request we send, the response
parsing, persistence and the API response are all the production code paths.
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('ALLOW_HEADER_API_KEYS', 'true')

import pytest
from fastapi.testclient import TestClient

H = {'X-API-Key': 'test-api-key', 'X-Tenant-Id': 'ai-round-trip'}
SEEN: list[dict] = []


class _Provider(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        SEEN.append({'path': self.path, 'auth': self.headers.get('Authorization'), 'body': body})
        content = 'Trail shoes that last\nGrip every mile. Built for first-time runners.'
        if 'response_format' in body:
            content = json.dumps({'title': 'Trail shoes that last', 'article': '# Trail shoes that last\n\nGrip every mile.', 'summary': 'Grip every mile.'})
        reply = {
            'choices': [{'message': {'content': content}}],
            'usage': {'prompt_tokens': 12, 'completion_tokens': 20, 'total_tokens': 32},
        }
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:  # silence
        return


@pytest.fixture()
def provider(monkeypatch: pytest.MonkeyPatch):
    server = HTTPServer(('127.0.0.1', 0), _Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    SEEN.clear()
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-key')
    monkeypatch.setenv('OPENAI_BASE_URL', f'http://127.0.0.1:{server.server_port}/v1')
    yield server
    server.shutdown()


@pytest.fixture()
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app)


def test_content_generate_returns_provider_text_and_sends_the_request(provider, client: TestClient, monkeypatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    response = client.post(
        '/content/generate',
        headers=H,
        json={'topic': 'Trail running shoes', 'audience': 'first-time runners', 'channel': 'linkedin', 'tone': 'friendly', 'provider': 'openai'},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['headline'] == 'Trail shoes that last'
    assert 'first-time runners' in data['body']
    assert data['provider_used'] == 'openai'
    assert SEEN, 'the provider was never called'
    assert SEEN[0]['path'] == '/v1/chat/completions'
    assert SEEN[0]['auth'] == 'Bearer sk-test-key'
    assert 'Trail running shoes' in json.dumps(SEEN[0]['body'])


def test_provider_outage_is_reported_not_papered_over(client: TestClient, monkeypatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-key')
    monkeypatch.setenv('OPENAI_BASE_URL', 'http://127.0.0.1:9/v1')  # nothing listens here
    response = client.post(
        '/content/generate',
        headers=H,
        json={'topic': 'Trail running shoes', 'audience': 'first-time runners', 'channel': 'linkedin', 'provider': 'openai'},
    )
    assert response.status_code == 503
    assert response.json()['detail']['code'] == 'AI_MODEL_UNAVAILABLE'


def test_ads_generate_uses_the_provider(provider, client: TestClient, monkeypatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    response = client.post('/ads/generate', headers=H, json={'product': 'Trail shoes', 'audience': 'runners', 'platform': 'meta', 'objective': 'traffic', 'provider': 'openai'})
    assert response.status_code == 200, response.text
    assert SEEN, 'the provider was never called'
    assert response.json()['headlines'], response.text


def test_social_copywriter_uses_the_provider(provider, client: TestClient, monkeypatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    response = client.post('/social/ai-assistant', headers=H, json={'text': 'We sell shoes', 'action': 'rephrase', 'tone': 'friendly'})
    assert response.status_code == 200, response.text
    assert SEEN, 'the provider was never called'
    assert response.json()['result'].startswith('Trail shoes that last')


def test_seo_writer_reaches_the_provider(provider, client: TestClient, monkeypatch) -> None:
    from backend.fastapi.app import legacy_main as lm

    monkeypatch.setattr(lm, '_redis_sync_client', lambda: None)
    monkeypatch.setenv('ENVIRONMENT', 'development')
    response = client.post('/seo-platform/content/write', headers=H, json={'topic': 'Trail running shoes', 'keywords': ['trail shoes'], 'word_count': 600, 'tone': 'friendly'})
    assert SEEN, f'the provider was never called: {response.status_code} {response.text[:300]}'
    assert SEEN[0]['path'] == '/v1/chat/completions'
    assert response.status_code == 200, response.text
    assert response.json().get('analysis_mode') == 'llm', response.text[:400]
