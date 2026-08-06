from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.translation_studio import create_translation_studio_router


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, handler: Callable):
        self._handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None, data=None, files=None):
        return self._handler('POST', url, headers=headers, json=json, data=data, files=files)

    async def get(self, url, headers=None, params=None):
        return self._handler('GET', url, headers=headers, params=params)


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(create_translation_studio_router())
    return TestClient(app)


def test_translation_health_degraded_without_key(monkeypatch):
    monkeypatch.delenv('DEEPL_API_KEY', raising=False)
    client = _build_client()

    res = client.get('/translations/health')

    assert res.status_code == 200
    body = res.json()
    assert body['status'] == 'degraded'
    assert body['providers']['deepl'] is False


def test_translation_text_calls_deepl(monkeypatch):
    monkeypatch.setenv('DEEPL_API_KEY', 'test-key')

    def fake_handler(method, url, **kwargs):
        assert method == 'POST'
        assert url.endswith('/translate')
        payload = kwargs['json']
        assert payload['target_lang'] == 'DE'
        assert payload['text'] == ['Hello world']
        return _FakeResponse(
            200,
            {
                'translations': [
                    {
                        'detected_source_language': 'EN',
                        'text': 'Hallo Welt',
                    }
                ],
                'billed_characters': 11,
                'model_type_used': 'quality_optimized',
            },
        )

    monkeypatch.setattr(
        'app.routers.translation_studio.httpx.AsyncClient',
        lambda timeout=45.0: _FakeAsyncClient(fake_handler),
    )

    client = _build_client()
    res = client.post(
        '/translations/text',
        json={
            'texts': ['Hello world'],
            'target_lang': 'DE',
            'provider': 'deepl',
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body['provider_used'] == 'deepl'
    assert body['translations'][0]['text'] == 'Hallo Welt'
    assert body['billed_characters'] == 11


def test_translation_text_passes_advanced_params(monkeypatch):
    monkeypatch.setenv('DEEPL_API_KEY', 'test-key')

    def fake_handler(method, url, **kwargs):
        assert method == 'POST'
        assert url.endswith('/translate')
        payload = kwargs['json']
        assert payload['model_type'] == 'quality_optimized'
        assert payload['split_sentences'] == 'nonewlines'
        assert payload['tag_handling'] == 'xml'
        assert payload['tag_handling_version'] == 'v2'
        assert payload['outline_detection'] is False
        assert payload['non_splitting_tags'] == ['code']
        assert payload['splitting_tags'] == ['title', 'p']
        assert payload['ignore_tags'] == ['ignore']
        assert payload['style_id'] == 'style-123'
        assert payload['custom_instructions'] == ['Prefer legal wording']
        assert payload['translation_memory_id'] == 'tm-123'
        assert payload['translation_memory_threshold'] == 80
        return _FakeResponse(
            200,
            {
                'translations': [
                    {
                        'detected_source_language': 'EN',
                        'text': 'Hallo Welt',
                    }
                ],
                'billed_characters': 11,
                'model_type_used': 'quality_optimized',
            },
        )

    monkeypatch.setattr(
        'app.routers.translation_studio.httpx.AsyncClient',
        lambda timeout=45.0: _FakeAsyncClient(fake_handler),
    )

    client = _build_client()
    res = client.post(
        '/translations/text',
        json={
            'texts': ['Hello world'],
            'target_lang': 'DE',
            'provider': 'deepl',
            'model_type': 'quality_optimized',
            'split_sentences': 'nonewlines',
            'tag_handling': 'xml',
            'tag_handling_version': 'v2',
            'outline_detection': False,
            'non_splitting_tags': ['code'],
            'splitting_tags': ['title', 'p'],
            'ignore_tags': ['ignore'],
            'style_id': 'style-123',
            'custom_instructions': ['Prefer legal wording'],
            'translation_memory_id': 'tm-123',
            'translation_memory_threshold': 80,
        },
    )

    assert res.status_code == 200


def test_translation_text_rejects_latency_for_quality_only_features(monkeypatch):
    monkeypatch.setenv('DEEPL_API_KEY', 'test-key')
    client = _build_client()

    res = client.post(
        '/translations/text',
        json={
            'texts': ['Hello world'],
            'target_lang': 'DE',
            'provider': 'deepl',
            'model_type': 'latency_optimized',
            'style_id': 'style-123',
        },
    )

    assert res.status_code == 400
    assert 'quality-optimized' in res.json()['detail']


def test_translation_memory_crud_and_health_count(monkeypatch):
    monkeypatch.delenv('DEEPL_API_KEY', raising=False)
    client = _build_client()

    created = client.post(
        '/translations/translation-memories',
        json={
            'name': 'Support Memory',
            'source_lang': 'EN',
            'target_lang': 'DE',
            'description': 'Support tone and terminology',
            'deepl_translation_memory_id': 'deepl-tm-123',
        },
    )
    assert created.status_code == 200
    memory_id = created.json()['id']

    listed = client.get('/translations/translation-memories')
    assert listed.status_code == 200
    assert listed.json()['total'] == 1
    assert listed.json()['items'][0]['deepl_translation_memory_id'] == 'deepl-tm-123'

    updated = client.patch(
        f'/translations/translation-memories/{memory_id}',
        json={'description': 'Updated description'},
    )
    assert updated.status_code == 200
    assert updated.json()['description'] == 'Updated description'

    health = client.get('/translations/health')
    assert health.status_code == 200
    assert health.json()['translation_memories'] == 1

    deleted = client.delete(f'/translations/translation-memories/{memory_id}')
    assert deleted.status_code == 200
    assert deleted.json()['deleted'] is True


def test_translation_text_resolves_local_translation_memory_id(monkeypatch):
    monkeypatch.setenv('DEEPL_API_KEY', 'test-key')

    def fake_handler(method, url, **kwargs):
        if method == 'POST' and url.endswith('/translate'):
            payload = kwargs['json']
            assert payload['translation_memory_id'] == 'deepl-tm-999'
            return _FakeResponse(
                200,
                {
                    'translations': [
                        {
                            'detected_source_language': 'EN',
                            'text': 'Hallo Welt',
                        }
                    ],
                    'billed_characters': 11,
                    'model_type_used': 'quality_optimized',
                },
            )
        raise AssertionError(f'Unexpected call: {method} {url}')

    monkeypatch.setattr(
        'app.routers.translation_studio.httpx.AsyncClient',
        lambda timeout=45.0: _FakeAsyncClient(fake_handler),
    )

    client = _build_client()
    create_res = client.post(
        '/translations/translation-memories',
        json={
            'name': 'TM One',
            'source_lang': 'EN',
            'target_lang': 'DE',
            'deepl_translation_memory_id': 'deepl-tm-999',
        },
    )
    assert create_res.status_code == 200
    local_id = create_res.json()['id']

    translate_res = client.post(
        '/translations/text',
        json={
            'texts': ['Hello world'],
            'target_lang': 'DE',
            'provider': 'deepl',
            'translation_memory_id': local_id,
        },
    )
    assert translate_res.status_code == 200


def test_document_translation_requires_vendor_key(monkeypatch):
    monkeypatch.delenv('DEEPL_API_KEY', raising=False)
    client = _build_client()

    files = {'file': ('demo.txt', b'hello', 'text/plain')}
    data = {'target_lang': 'DE'}
    res = client.post('/translations/documents', data=data, files=files)

    assert res.status_code == 503
    assert 'DEEPL_API_KEY' in res.json()['detail']
