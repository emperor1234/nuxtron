import { NextRequest } from 'next/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { __test__ } from '../gateway';
import { GET, POST } from './route';

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

function call(method: 'GET' | 'POST', path: string[], init?: { body?: string; tenant?: string }) {
  const handler = method === 'GET' ? GET : POST;
  const request = new NextRequest(`http://localhost/api/fastapi/${path.join('/')}`, {
    method,
    headers: { 'x-tenant-id': init?.tenant ?? 'tenant-a', 'content-type': 'application/json' },
    body: init?.body,
  });
  return handler(request, { params: Promise.resolve({ path }) });
}

describe('fastapi gateway', () => {
  it('fails closed in production by excluding implicit localhost upstreams', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('FASTAPI_URL', 'https://api.example.com');

    const upstreams = __test__.getUpstreamBaseUrls();

    expect(upstreams).toEqual(['https://api.example.com']);
  });

  it('keeps localhost upstreams outside production', () => {
    vi.stubEnv('NODE_ENV', 'development');

    expect(__test__.getUpstreamBaseUrls()).toEqual(
      expect.arrayContaining(['http://127.0.0.1:8001', 'http://localhost:8000'])
    );
  });

  it('reports missing configuration instead of guessing', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('FASTAPI_URL', '');
    vi.stubEnv('NEXT_PUBLIC_FASTAPI_URL', '');
    vi.stubEnv('LOCAL_FASTAPI_URL', '');
    vi.stubEnv('FASTAPI_API_KEY', 'key');

    const response = await call('GET', ['social', 'queue']);

    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual({ detail: 'FASTAPI_URL is not configured.' });
  });

  it('returns a real 502 and no invented payload when the backend is unreachable', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('FASTAPI_URL', 'https://api.example.com');
    vi.stubEnv('FASTAPI_API_KEY', 'key');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('connect ECONNREFUSED')));

    const response = await call('GET', ['notifications']);

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual({ detail: 'connect ECONNREFUSED' });
  });

  it('passes backend errors through unchanged', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('FASTAPI_URL', 'https://api.example.com');
    vi.stubEnv('FASTAPI_API_KEY', 'key');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: { code: 'NOT_IMPLEMENTED' } }), {
          status: 501,
          headers: { 'content-type': 'application/json' },
        })
      )
    );

    const response = await call('POST', ['media', 'jobs'], { body: '{}' });

    expect(response.status).toBe(501);
    await expect(response.json()).resolves.toEqual({ detail: { code: 'NOT_IMPLEMENTED' } });
  });

  it('forwards the service key, tenant and session to the backend', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('FASTAPI_URL', 'https://api.example.com');
    vi.stubEnv('FASTAPI_API_KEY', 'service-key');
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await call('GET', ['social', 'queue'], { tenant: 'tenant-b' });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(url).toBe('https://api.example.com/social/queue');
    expect(headers.get('X-API-Key')).toBe('service-key');
    expect(headers.get('X-Tenant-Id')).toBe('tenant-b');
  });

  it('requires a tenant', () => {
    expect(__test__.getProxyConfigError(['https://api.example.com'], 'key', '')?.status).toBe(400);
  });

  it('gives AI analysis routes a longer timeout than CRUD routes', () => {
    expect(__test__.getUpstreamTimeoutMs(['seo-platform', 'on-page', 'analyze'])).toBeGreaterThan(
      __test__.getUpstreamTimeoutMs(['social', 'queue'])
    );
  });
});
