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

    await apiGet('/health', 'tenant-test');

    expect(fetch).toHaveBeenCalledWith(
      '/api/fastapi/health',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'X-Tenant-Id': 'tenant-test',
          'X-Request-ID': expect.any(String),
        }),
      })
    );
  });

  it('fails closed when no workspace context exists instead of inventing a tenant', async () => {
    localStorage.clear();

    await expect(apiGet('/health', '')).rejects.toThrow('Workspace context is required');
    expect(fetch).not.toHaveBeenCalled();
  });

  it('handles malformed JSON body with detail fallback', async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse('not-json', true, 200, 'application/json'));

    const data = await apiGet<{ detail: string }>('/raw', 'tenant-test');

    expect(data).toEqual({ detail: 'not-json' });
  });

  it('can bypass GET response caching for sensitive history payloads', async () => {
    localStorage.clear();
    vi.mocked(fetch).mockResolvedValue(mockResponse({ records: [] }));

    await apiGet('/sensitive-history', 'tenant-test', { cache: false });
    await apiGet('/sensitive-history', 'tenant-test', { cache: false });

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(localStorage.length).toBe(0);
  });

  it('can bypass POST response caching for generated workflow drafts', async () => {
    localStorage.clear();
    vi.mocked(fetch).mockResolvedValue(mockResponse({ status: 'draft' }));

    await apiSend('/seo-platform/planner/draft', 'POST', { goal: 'Plan a workflow' }, 'tenant-test', { cache: false });
    await apiSend('/seo-platform/planner/draft', 'POST', { goal: 'Plan a workflow' }, 'tenant-test', { cache: false });

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(localStorage.length).toBe(0);
  });

  it('throws detail message on failed write requests', async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ detail: 'Blocked' }, false, 403));

    await expect(apiSend('/write', 'POST', { a: 1 }, 'tenant-test')).rejects.toThrow('Blocked');
  });
});
