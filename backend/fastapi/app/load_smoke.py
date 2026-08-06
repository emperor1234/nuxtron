import asyncio
import base64
import hashlib
import hmac
import json
import os
import time

import httpx

# Keep load-smoke focused on request-path latency instead of unrelated startup/background work.
if os.getenv('FASTAPI_LOAD_SMOKE_SKIP_STARTUP_DB_INIT', '1').strip().lower() in {'1', 'true', 'yes', 'on'}:
    os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
if os.getenv('FASTAPI_LOAD_SMOKE_DISABLE_AUTONOMOUS_WATCHDOG', '1').strip().lower() in {'1', 'true', 'yes', 'on'}:
    os.environ.setdefault('AUTONOMOUS_WORKFORCE_WATCHDOG_ENABLED', '0')
if os.getenv('FASTAPI_LOAD_SMOKE_DISABLE_REQUEST_TRACE_LOGGING', '1').strip().lower() in {'1', 'true', 'yes', 'on'}:
    os.environ.setdefault('REQUEST_TRACE_LOGGING_ENABLED', '0')

from .main import app


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _jwt_sign_hs256(payload: dict[str, object], secret: str) -> str:
    header = {'alg': 'HS256', 'typ': 'JWT'}
    head = _b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    body = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{head}.{body}'.encode('ascii')
    signature = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    return f'{head}.{body}.{_b64url_encode(signature)}'


def _bearer_token(tenant: str) -> str:
    now = int(time.time())
    secret = os.getenv('JWT_SIGNING_KEY', '').strip() or os.getenv('FASTAPI_API_KEY', 'change-this-fastapi-key').strip()
    claims: dict[str, object] = {
        'tenant_id': tenant,
        'iat': now,
        'exp': now + 600,
    }
    return _jwt_sign_hs256(claims, secret)


def _headers(tenant: str) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {_bearer_token(tenant)}',
        'X-Tenant-Id': tenant,
    }


async def _one_request(client: httpx.AsyncClient) -> tuple[int, float]:
    started = time.perf_counter()
    response = await client.get('/notifications/unread-count', headers=_headers('tenant-load'))
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return response.status_code, elapsed_ms


async def _run_load_smoke_async(
    total_requests: int,
    max_workers: int,
    p95_target_ms: float,
    success_target_pct: float,
) -> None:
    os.environ.setdefault('FASTAPI_API_KEY', 'change-this-fastapi-key')

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
        # Prime auth and route path once.
        warmup = await client.get('/notifications/unread-count', headers=_headers('tenant-load'))
        assert warmup.status_code == 200, warmup.text

        semaphore = asyncio.Semaphore(max_workers)

        async def _run_one() -> tuple[int, float]:
            async with semaphore:
                return await _one_request(client)

        results = await asyncio.gather(*(_run_one() for _ in range(total_requests)))

    status_codes = [code for code, _ in results]
    latencies = sorted(lat for _, lat in results)

    success_count = sum(1 for code in status_codes if code == 200)
    success_rate = (success_count / max(1, total_requests)) * 100.0
    p95_index = min(len(latencies) - 1, int(len(latencies) * 0.95))
    p95_ms = latencies[p95_index]

    assert success_rate >= success_target_pct, (
        f'Load smoke success rate too low: {success_rate:.2f}% '
        f'(target {success_target_pct:.2f}%)'
    )
    assert p95_ms < p95_target_ms, (
        f'Load smoke p95 latency too high: {p95_ms:.2f}ms '
        f'(target < {p95_target_ms:.2f}ms)'
    )

    print(
        'FastAPI load smoke passed '
        f'(requests={total_requests}, workers={max_workers}, '
        f'success_rate={success_rate:.2f}%, p95_ms={p95_ms:.2f}, '
        f'targets: success>={success_target_pct:.2f}%, p95<{p95_target_ms:.2f}ms)'
    )


def run_load_smoke(total_requests: int = 80, max_workers: int = 10) -> None:
    # Enhanced: avoid shared TestClient across threads to prevent intermittent deadlocks.
    total_requests = int(os.getenv('FASTAPI_LOAD_SMOKE_REQUESTS', str(total_requests)))
    max_workers = int(os.getenv('FASTAPI_LOAD_SMOKE_WORKERS', str(max_workers)))
    p95_target_ms = float(os.getenv('FASTAPI_LOAD_SMOKE_P95_MS', '200'))
    success_target_pct = float(os.getenv('FASTAPI_LOAD_SMOKE_SUCCESS_PCT', '99'))

    asyncio.run(_run_load_smoke_async(total_requests, max_workers, p95_target_ms, success_target_pct))


if __name__ == '__main__':
    run_load_smoke()
