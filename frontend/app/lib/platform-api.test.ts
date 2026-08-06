import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiGet, apiSend } from './platform-api';

function mockResponse(body: unknown, ok = true, status = 200, contentType = 'application/json'): Response {
  const raw = typeof body === 'string' ? body : JSON.stringify(body);
  return {
    ok,
    status,
    headers: {
      get: (name: string) => (name.toLowerCase() === 'content-type' ? contentType : null),
    },
    text: () => Promise.resolve(raw),
  } as unknown as Response;
}

describe('platform-api helpers', () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_FASTAPI_API_KEY = 'test-fastapi-key';
    process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID = 'tenant-test';
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_FASTAPI_API_KEY;
    delete process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID;
    vi.restoreAllMocks();
  });

  it('adds X-Request-ID and tenant header on GET requests', async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ status: 'ok' }));

    await apiGet('/health', 'tenant-demo');

    expect(fetch).toHaveBeenCalledWith(
      '/api/fastapi/health',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'X-Tenant-Id': 'tenant-demo',
          'X-Request-ID': expect.any(String),
        }),
      })
    );
  });

  it('handles malformed JSON body with detail fallback', async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse('not-json', true, 200, 'application/json'));

    const data = await apiGet<{ detail: string }>('/raw', 'tenant-demo');

    expect(data).toEqual({ detail: 'not-json' });
  });

  it('throws detail message on failed write requests', async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ detail: 'Blocked' }, false, 403));

    await expect(apiSend('/write', 'POST', { a: 1 }, 'tenant-demo')).rejects.toThrow('Blocked');
  });
});
