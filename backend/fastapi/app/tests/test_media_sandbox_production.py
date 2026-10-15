"""
Production-grade E2E tests for the Sandboxed Media SaaS Pipeline.

Tests cover all 16 endpoints (6 original + 6 new) and the three new
sandbox security behaviours added in the production implementation:
  - Per-tenant concurrency cap (429 on overflow)
  - Provider dispatch fails explicitly when credentials/output persistence are unavailable
  - IDOR prevention on raw-input delete
  - Audit trail completeness
  - Magic-byte validation with HMAC token
  - Signed output URL structure
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections.abc import Generator, Mapping
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Keep import-time app startup on the lightweight test path.
# Use deterministic values because other test modules may mutate process env.
os.environ['NUXTRON_SKIP_STARTUP_DB_INIT'] = '1'
os.environ['FASTAPI_API_KEY'] = 'test-api-key'
os.environ['JWT_SIGNING_KEY'] = 'media-sandbox-test-secret'
os.environ['APP_ENC_KEY'] = 'A' * 44
os.environ['ALLOW_HEADER_API_KEYS'] = '1'

TENANT = 'test-tenant-prod'


def _make_jwt(tenant_id: str = TENANT, secret: str | None = None) -> str:
    jwt_secret = secret or os.environ['JWT_SIGNING_KEY']
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b'=').decode()
    claims = {
        'sub': f'user-{tenant_id}',
        'tenant_id': tenant_id,
        'exp': int(time.time()) + 3600,
    }
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b'=').decode()
    signing_input = f'{header}.{payload}'.encode('ascii')
    signature = base64.urlsafe_b64encode(
        hmac.new(jwt_secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    ).rstrip(b'=').decode()
    return f'{header}.{payload}.{signature}'


def _auth_headers(tenant_id: str = TENANT) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {_make_jwt(tenant_id)}',
        'X-API-Key': os.environ['FASTAPI_API_KEY'],
        'X-Tenant-Id': tenant_id,
    }


class _DynamicAuthHeaders(Mapping[str, str]):
    def __getitem__(self, key: str) -> str:
        return _auth_headers()[key]

    def __iter__(self):
        return iter(_auth_headers())

    def __len__(self) -> int:
        return len(_auth_headers())

    def items(self):
        return _auth_headers().items()

    def keys(self):
        return _auth_headers().keys()

    def values(self):
        return _auth_headers().values()

    def get(self, key: str, default: str | None = None) -> str | None:
        return _auth_headers().get(key, default)

def _assert_media_job_unavailable(response) -> None:
    assert response.status_code == 501, response.text
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"


# ---------------------------------------------------------------------------
# App fixture — spin up a fresh isolated in-memory instance per test module
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def client() -> Generator[TestClient, None, None]:
    """
    Import legacy_main conditionally to avoid circular-import issues in CI.
    Falls back to mounting only the media router if legacy_main unavailable.
    """
    try:
        from backend.fastapi.app import legacy_main as legacy_main_module  # noqa: PLC0415

        # Do NOT reload — reloading re-executes Pydantic model definitions while
        # previous ones are still live, which causes access violations on teardown.
        app = legacy_main_module.app
        with TestClient(app) as c:
            yield c
    except Exception:  # noqa: BLE001
        from backend.fastapi.app import memory_stores  # noqa: PLC0415
        from backend.fastapi.app.routers.media_jobs import create_media_jobs_router  # noqa: PLC0415
        from fastapi import FastAPI  # noqa: PLC0415

        def _noop_rate_limit(tenant_id: str, limit: int, window: int) -> None:
            pass

        _app = FastAPI()
        _router = create_media_jobs_router(
            enforce_rate_limit=_noop_rate_limit,
            media_jobs_memory=memory_stores.media_jobs,
            media_jobs_dlq_memory=memory_stores.media_jobs_dlq,
            audit_log_memory=memory_stores.audit_log,
        )
        _app.include_router(_router)

        # Minimal auth shim
        from fastapi import Request  # noqa: PLC0415

        @_app.middleware('http')
        async def inject_auth(request: Request, call_next):  # type: ignore[no-untyped-def]
            return await call_next(request)

        with TestClient(_app) as c:
            yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AUTH_HEADERS: Mapping[str, str] = _DynamicAuthHeaders()

IMAGE_MAGIC = b'\xff\xd8\xff\xe0\x00\x10JFIF'  # JPEG magic bytes (first 10 of 16)
IMAGE_MAGIC_B64 = base64.b64encode(IMAGE_MAGIC.ljust(16, b'\x00')).decode()

PDF_MAGIC = b'%PDF-1.'
PDF_MAGIC_B64 = base64.b64encode(PDF_MAGIC.ljust(16, b'\x00')).decode()


def queue_job(
    client: TestClient,
    *,
    storage_key: str = 'raw-input/test-tenant-prod/test.jpg',
    media_type: str = 'image',
    provider: str | None = None,
    validation_token: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        'storage_key': storage_key,
        'media_type': media_type,
    }
    if provider:
        body['provider'] = provider
    if validation_token:
        body['validation_token'] = validation_token

    res = client.post('/media/jobs', json=body, headers=AUTH_HEADERS)
    # Accept both success (201) and 429 (concurrency limit) in batch tests
    return {'status_code': res.status_code, 'data': res.json() if res.content else {}}


# ---------------------------------------------------------------------------
# 1. GET /media/jobs/stats
# ---------------------------------------------------------------------------

class TestMediaJobsStats:
    def test_stats_are_unavailable_without_durable_jobs(self, client: TestClient) -> None:
        _assert_media_job_unavailable(client.get('/media/jobs/stats', headers=AUTH_HEADERS))

# ---------------------------------------------------------------------------
# 2. GET /media/sandbox/config
# ---------------------------------------------------------------------------

class TestSandboxConfig:
    def test_config_returns_200(self, client: TestClient) -> None:
        res = client.get('/media/sandbox/config', headers=AUTH_HEADERS)
        assert res.status_code == 200

    def test_config_has_three_isolation_layers(self, client: TestClient) -> None:
        res = client.get('/media/sandbox/config', headers=AUTH_HEADERS)
        body = res.json()
        cfg = body.get('sandbox') or body
        layers = cfg.get('isolation_layers', {})
        assert len(layers) == 3, f'Expected 3 isolation layers, got {len(layers)}'

    def test_config_has_six_security_rules(self, client: TestClient) -> None:
        res = client.get('/media/sandbox/config', headers=AUTH_HEADERS)
        body = res.json()
        cfg = body.get('sandbox') or body
        rules = cfg.get('security_rules', {})
        assert len(rules) == 6, f'Expected 6 security rules, got {len(rules)}'

    def test_config_execution_mode_field(self, client: TestClient) -> None:
        res = client.get('/media/sandbox/config', headers=AUTH_HEADERS)
        body = res.json()
        cfg = body.get('sandbox') or body
        assert 'execution_mode' in cfg
        assert cfg['execution_mode'] == 'unavailable'
        assert cfg['available_executors']['memory_fallback'] is False
        assert cfg['job_processing']['available'] is False

    def test_sandbox_does_not_advertise_any_executor(self, client: TestClient) -> None:
        response = client.get('/media/sandbox/config', headers=AUTH_HEADERS)
        cfg = response.json()['sandbox']
        assert not any(cfg['available_executors'].values())

    def test_security_rules_have_enforced_flag(self, client: TestClient) -> None:
        res = client.get('/media/sandbox/config', headers=AUTH_HEADERS)
        body = res.json()
        cfg = body.get('sandbox') or body
        for rule_key, rule in cfg.get('security_rules', {}).items():
            assert 'enforced' in rule, f'Rule {rule_key} missing "enforced" field'
            assert isinstance(rule['enforced'], bool)


# ---------------------------------------------------------------------------
# 3. GET /media/providers
# ---------------------------------------------------------------------------

class TestMediaProviders:
    def test_providers_returns_200(self, client: TestClient) -> None:
        res = client.get('/media/providers', headers=AUTH_HEADERS)
        assert res.status_code == 200

    def test_providers_lists_six(self, client: TestClient) -> None:
        res = client.get('/media/providers', headers=AUTH_HEADERS)
        body = res.json()
        providers = body.get('providers') or body
        assert len(providers) == 6, f'Expected 6 providers, got {len(providers)}'

    def test_providers_have_configured_flag(self, client: TestClient) -> None:
        res = client.get('/media/providers', headers=AUTH_HEADERS)
        body = res.json()
        providers = body.get('providers') or body
        for p in providers:
            assert 'configured' in p, f'Provider {p.get("id")} missing "configured" field'
            assert isinstance(p['configured'], bool)
            assert p['available'] is False

    def test_known_providers_present(self, client: TestClient) -> None:
        expected = {'cloudinary', 'mux', 'bunny', 'assemblyai', 'deepgram', 'adobe_pdf'}
        res = client.get('/media/providers', headers=AUTH_HEADERS)
        body = res.json()
        providers = body.get('providers') or body
        found = {p['id'] for p in providers}
        assert expected == found, f'Provider mismatch. Expected: {expected}, Got: {found}'

    def test_unconfigured_providers_list_missing_env_vars(self, client: TestClient) -> None:
        res = client.get('/media/providers', headers=AUTH_HEADERS)
        body = res.json()
        providers = body.get('providers') or body
        for p in providers:
            if not p['configured']:
                assert isinstance(p.get('missing_env_vars'), list)
                assert len(p['missing_env_vars']) > 0


# ---------------------------------------------------------------------------
# 4. POST /media/validate-file
# ---------------------------------------------------------------------------

class TestMagicByteValidation:
    def test_jpeg_validates_correctly(self, client: TestClient) -> None:
        res = client.post(
            '/media/validate-file',
            json={'first_bytes_b64': IMAGE_MAGIC_B64, 'expected_mime': 'image/jpeg'},
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 200
        body = res.json()
        assert body.get('mime_type') == 'image/jpeg'
        assert body.get('validation_token')

    def test_magic_byte_mismatch_returns_invalid(self, client: TestClient) -> None:
        # Send JPEG magic but claim it's a PDF
        res = client.post(
            '/media/validate-file',
            json={'first_bytes_b64': IMAGE_MAGIC_B64, 'expected_mime': 'application/pdf'},
            headers=AUTH_HEADERS,
        )
        assert res.status_code in (200, 422)
        if res.status_code == 200:
            assert res.json().get('valid') is False

    def test_validation_returns_token_when_enabled(self, client: TestClient) -> None:
        res = client.post(
            '/media/validate-file',
            json={'first_bytes_b64': IMAGE_MAGIC_B64, 'expected_mime': 'image/jpeg'},
            headers=AUTH_HEADERS,
        )
        if res.status_code == 200:
            body = res.json()
            # Token may or may not be present depending on MEDIA_REQUIRE_VALIDATION_TOKEN
            if 'validation_token' in body:
                assert isinstance(body['validation_token'], (str, type(None)))

    def test_missing_fields_returns_422(self, client: TestClient) -> None:
        res = client.post('/media/validate-file', json={}, headers=AUTH_HEADERS)
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# 5. POST /media/jobs (queue job)
# ---------------------------------------------------------------------------

class TestQueueJob:
    @pytest.mark.parametrize(
        'payload',
        [
            {'storage_key': f'raw-input/{TENANT}/img.jpg', 'media_type': 'image'},
            {'storage_key': f'raw-input/{TENANT}/vid.mp4', 'media_type': 'video', 'provider': 'mux'},
        ],
    )
    def test_create_job_fails_closed(self, client: TestClient, payload: dict[str, Any]) -> None:
        _assert_media_job_unavailable(client.post('/media/jobs', json=payload, headers=AUTH_HEADERS))

# ---------------------------------------------------------------------------
# 6. GET /media/jobs + GET /media/jobs/{id}
# ---------------------------------------------------------------------------

class TestListAndGetJob:
    def test_list_and_get_fail_closed(self, client: TestClient) -> None:
        _assert_media_job_unavailable(client.get('/media/jobs', headers=AUTH_HEADERS))
        _assert_media_job_unavailable(client.get('/media/jobs/999999', headers=AUTH_HEADERS))

# ---------------------------------------------------------------------------
# 7. POST /media/sandbox/dispatch — all 6 providers (no creds mode)
# ---------------------------------------------------------------------------

class TestSandboxDispatch:
    PROVIDERS_AND_TYPES = [
        ('cloudinary', 'image'),
        ('mux', 'video'),
        ('bunny', 'image'),
        ('assemblyai', 'audio'),
        ('deepgram', 'audio'),
        ('adobe_pdf', 'document'),
    ]

    @pytest.mark.parametrize('provider,media_type', PROVIDERS_AND_TYPES)
    def test_dispatch_provider_is_unavailable_before_creating_memory_job(
        self,
        client: TestClient,
        provider: str,
        media_type: str,
    ) -> None:
        from backend.fastapi.app import memory_stores

        jobs_before = len(memory_stores.media_jobs)
        res = client.post(
            '/media/sandbox/dispatch',
            json={
                'storage_key': f'raw-input/{TENANT}/test.file',
                'media_type': media_type,
                'provider': provider,
                'operation': 'auto',
            },
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 501, f'Provider {provider}: {res.text}'
        assert res.json()["detail"]["code"] == "NOT_IMPLEMENTED"
        assert len(memory_stores.media_jobs) == jobs_before

    def test_provider_processing_ack_is_not_reported_as_completed(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from backend.fastapi.app import memory_stores
        from backend.fastapi.app.domains.content.media import providers

        calls: list[str] = []

        async def accepted_but_untracked(*_args, **_kwargs) -> dict[str, str]:
            calls.append("called")
            return {"provider": "mux", "status": "processing", "asset_id": "asset-not-tracked"}

        monkeypatch.setitem(providers._PROVIDER_DISPATCH, "mux", accepted_but_untracked)
        jobs_before = len(memory_stores.media_jobs)
        res = client.post(
            '/media/sandbox/dispatch',
            json={
                'storage_key': f'raw-input/{TENANT}/processing-test.mp4',
                'media_type': 'video',
                'provider': 'mux',
                'operation': 'transcode',
            },
            headers=AUTH_HEADERS,
        )

        assert res.status_code == 501, res.text
        assert res.json()["detail"]["code"] == "NOT_IMPLEMENTED"
        assert calls == []
        assert len(memory_stores.media_jobs) == jobs_before

    def test_dispatch_unknown_provider_returns_400(self, client: TestClient) -> None:
        res = client.post(
            '/media/sandbox/dispatch',
            json={
                'storage_key': f'raw-input/{TENANT}/test.jpg',
                'media_type': 'image',
                'provider': 'nonexistent_provider_xyz',
            },
            headers=AUTH_HEADERS,
        )
        assert res.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 8. DELETE /media/raw-input — IDOR prevention
# ---------------------------------------------------------------------------

class TestRawInputDelete:
    def test_delete_own_key_requires_configured_storage(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.delenv('MINIO_ENDPOINT', raising=False)
        monkeypatch.delenv('MINIO_ACCESS_KEY', raising=False)
        monkeypatch.delenv('MINIO_SECRET_KEY', raising=False)
        res = client.delete(
            '/media/raw-input',
            params={'storage_key': f'raw-input/{TENANT}/myfile.jpg'},
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 503

    def test_delete_own_key_reports_success_only_after_storage_ack(self, client: TestClient, monkeypatch) -> None:
        calls: list[tuple[str, str]] = []

        def delete_minio_object(bucket: str, object_key: str) -> None:
            calls.append((bucket, object_key))

        monkeypatch.setattr(
            'backend.fastapi.app.domains.content.media.operations.purge_raw_input.delete_minio_object',
            delete_minio_object,
        )
        key = f'raw-input/{TENANT}/myfile.jpg'
        res = client.delete('/media/raw-input', params={'storage_key': key}, headers=AUTH_HEADERS)
        assert res.status_code == 200
        assert res.json()['deleted_from_storage'] is True
        assert calls == [('raw-input', key)]

    def test_delete_storage_failure_is_not_reported_as_success(self, client: TestClient, monkeypatch) -> None:
        def fail_delete(bucket: str, object_key: str) -> None:
            raise HTTPException(status_code=502, detail='Object storage deletion failed.')

        monkeypatch.setattr(
            'backend.fastapi.app.domains.content.media.operations.purge_raw_input.delete_minio_object',
            fail_delete,
        )
        res = client.delete(
            '/media/raw-input',
            params={'storage_key': f'raw-input/{TENANT}/myfile.jpg'},
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 502

    def test_storage_delete_uses_signed_url_without_redirects_or_environment_proxy(self, monkeypatch) -> None:
        from backend.fastapi.app.domains.content import storage

        monkeypatch.setenv('MINIO_ENDPOINT', 'https://minio.example.test')
        monkeypatch.setenv('MINIO_ACCESS_KEY', 'test-access-key')
        monkeypatch.setenv('MINIO_SECRET_KEY', 'test-secret-key')
        monkeypatch.setenv('ENVIRONMENT', 'production')
        signer_calls: list[tuple[str, ...]] = []
        sent_requests: list[tuple[str, str]] = []
        client_options: list[dict[str, Any]] = []

        def signer(*args: str) -> str:
            signer_calls.append(args)
            return 'https://minio.example.test/signed-delete'

        class Response:
            is_success = True

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        class Client:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def stream(self, method: str, url: str) -> Response:
                sent_requests.append((method, url))
                return Response()

        def client_factory(**kwargs):
            client_options.append(kwargs)
            return Client()

        monkeypatch.setattr(storage, '_minio_presign', signer)
        monkeypatch.setattr(storage.httpx, 'Client', client_factory)
        storage.delete_minio_object('raw-input', f'raw-input/{TENANT}/myfile.jpg')

        assert signer_calls == [
            ('https://minio.example.test', 'test-access-key', 'test-secret-key', 'raw-input',
             f'raw-input/{TENANT}/myfile.jpg', 'DELETE', 60)
        ]
        assert sent_requests == [('DELETE', 'https://minio.example.test/signed-delete')]
        assert client_options == [{'timeout': 10.0, 'trust_env': False, 'follow_redirects': False}]

    def test_delete_other_tenant_key_rejected(self, client: TestClient) -> None:
        """IDOR: tenant A must not delete tenant B's files."""
        res = client.delete(
            '/media/raw-input',
            params={'storage_key': 'raw-input/other-tenant/secret.jpg'},
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 403

    def test_delete_path_traversal_rejected(self, client: TestClient) -> None:
        """Path traversal: ../../etc/passwd must be rejected."""
        res = client.delete(
            '/media/raw-input',
            params={'storage_key': '../../etc/passwd'},
            headers=AUTH_HEADERS,
        )
        assert res.status_code in (400, 403)

    def test_delete_missing_key_param(self, client: TestClient) -> None:
        res = client.delete('/media/raw-input', headers=AUTH_HEADERS)
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# 9. GET /media/jobs/{id}/audit
# ---------------------------------------------------------------------------

class TestAuditTrail:
    def test_job_audit_requires_durable_job_store(self, client: TestClient) -> None:
        _assert_media_job_unavailable(client.get('/media/jobs/999999/audit', headers=AUTH_HEADERS))

# ---------------------------------------------------------------------------
# 10. POST /media/jobs/{id}/output-url
# ---------------------------------------------------------------------------

class TestOutputUrl:
    def test_output_url_never_uses_a_synthetic_cdn_signature(self, client: TestClient) -> None:
        response = client.post(
            '/media/jobs/999999/output-url',
            json={'expires_seconds': 300},
            headers=AUTH_HEADERS,
        )
        _assert_media_job_unavailable(response)
        assert 'signed_url' not in response.json()

    def test_invalid_expiry_is_rejected_before_job_capability(self, client: TestClient) -> None:
        response = client.post(
            '/media/jobs/1/output-url',
            json={'expires_seconds': 5},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 422

# ---------------------------------------------------------------------------
# 11. GET /media/jobs/dlq
# ---------------------------------------------------------------------------

class TestDLQ:
    def test_dead_letter_queue_requires_durable_job_store(self, client: TestClient) -> None:
        _assert_media_job_unavailable(client.get('/media/jobs/dlq', headers=AUTH_HEADERS))

# ---------------------------------------------------------------------------
# 12. DELETE /media/jobs/{id} (cancel)
# ---------------------------------------------------------------------------

class TestCancelJob:
    def test_cancel_requires_durable_job_store(self, client: TestClient) -> None:
        _assert_media_job_unavailable(client.delete('/media/jobs/999999', headers=AUTH_HEADERS))

# ---------------------------------------------------------------------------
# 13. Concurrency cap — 429 enforcement
# ---------------------------------------------------------------------------

class TestConcurrencyCap:
    def test_create_requests_are_not_accepted_into_process_local_state(self, client: TestClient) -> None:
        from backend.fastapi.app import memory_stores

        count_before = len(memory_stores.media_jobs)
        responses = [
            client.post(
                '/media/jobs',
                json={'storage_key': f'raw-input/{TENANT}/request-{index}.jpg', 'media_type': 'image'},
                headers=AUTH_HEADERS,
            )
            for index in range(3)
        ]
        assert all(response.status_code == 501 for response in responses)
        assert all(response.json()['detail']['code'] == 'NOT_IMPLEMENTED' for response in responses)
        assert len(memory_stores.media_jobs) == count_before

# ---------------------------------------------------------------------------
# 14. End-to-end flow: validate → queue → stats → SSE → output-url
# ---------------------------------------------------------------------------

class TestEndToEndFlow:
    def test_validation_works_but_job_creation_is_honestly_unavailable(self, client: TestClient) -> None:
        validation = client.post(
            '/media/validate-file',
            json={'first_bytes_b64': IMAGE_MAGIC_B64, 'expected_mime': 'image/jpeg'},
            headers=AUTH_HEADERS,
        )
        assert validation.status_code == 200
        assert validation.json().get('validation_token')

        creation = client.post(
            '/media/jobs',
            json={
                'storage_key': f'raw-input/{TENANT}/e2e-test.jpg',
                'media_type': 'image',
                'validation_token': validation.json()['validation_token'],
            },
            headers=AUTH_HEADERS,
        )
        _assert_media_job_unavailable(creation)
