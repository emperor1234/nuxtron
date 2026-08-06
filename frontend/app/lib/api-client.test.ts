import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  apiPut,
  clearAuthSession,
  PROXY_BASE_URL,
  setAuthSession,
  setSuperAdminKeySession,
  STORAGE_SUPER_ADMIN_KEY,
  STORAGE_TENANT_KEY,
  STORAGE_TOKEN_KEY,
} from './api-client';

function makeFetchResponse(body: unknown, ok = true, status = 200, contentType = 'application/json') {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  return {
    ok,
    status,
    headers: { get: (h: string) => (h === 'content-type' ? contentType : null) },
    text: () => Promise.resolve(text),
  } as unknown as Response;
}

describe('api-client session helpers', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('stores tenant id and bearer token on setAuthSession', () => {
    localStorage.setItem(STORAGE_TOKEN_KEY, 'legacy-token');

    setAuthSession('new-token', 'tenant-42');

    expect(localStorage.getItem(STORAGE_TOKEN_KEY)).toBe('new-token');
    expect(localStorage.getItem(STORAGE_TENANT_KEY)).toBe('tenant-42');
  });

  it('clears auth session values', () => {
    localStorage.setItem(STORAGE_TOKEN_KEY, 'legacy-token');
    localStorage.setItem(STORAGE_TENANT_KEY, 'tenant-42');

    clearAuthSession();

    expect(localStorage.getItem(STORAGE_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(STORAGE_TENANT_KEY)).toBeNull();
  });

  it('stores super admin key only when non-empty', () => {
    setSuperAdminKeySession('');
    expect(localStorage.getItem(STORAGE_SUPER_ADMIN_KEY)).toBeNull();

    setSuperAdminKeySession('super-secret');
    expect(localStorage.getItem(STORAGE_SUPER_ADMIN_KEY)).toBe('super-secret');
  });
});

describe('api-client network helpers', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
    vi.spyOn(window, 'dispatchEvent');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('apiGet sends GET and returns parsed JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({ ok: true }));
    const result = await apiGet('/test/path', 'tenant-1');
    expect(fetch).toHaveBeenCalledWith(`${PROXY_BASE_URL}/test/path`, expect.objectContaining({ method: 'GET' }));
    expect(result).toEqual({ ok: true });
  });

  it('apiGet requires tenant id when neither argument nor session tenant is set', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({}));
    await expect(apiGet('/path')).rejects.toThrow('Tenant id is required in strict no-mock mode');
  });

  it('apiPost sends POST with body', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({ created: true }));
    const result = await apiPost('/items', { name: 'x' }, 'tenant-2');
    expect(fetch).toHaveBeenCalledWith(
      `${PROXY_BASE_URL}/items`,
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ name: 'x' }) })
    );
    expect(result).toEqual({ created: true });
  });

  it('apiPost passes extraHeaders', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({}));
    await apiPost('/items', {}, 'tenant-3', { 'X-Custom': 'val' });
    expect(fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-Custom': 'val' }),
      })
    );
  });

  it('apiPatch sends PATCH with body', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({ updated: true }));
    const result = await apiPatch('/items/1', { name: 'y' }, 'tenant-4');
    expect(fetch).toHaveBeenCalledWith(`${PROXY_BASE_URL}/items/1`, expect.objectContaining({ method: 'PATCH' }));
    expect(result).toEqual({ updated: true });
  });

  it('apiPut sends PUT with body', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({ updated: true }));
    const result = await apiPut('/items/1', { name: 'z' }, 'tenant-4');
    expect(fetch).toHaveBeenCalledWith(`${PROXY_BASE_URL}/items/1`, expect.objectContaining({ method: 'PUT' }));
    expect(result).toEqual({ updated: true });
  });

  it('apiDelete sends DELETE', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({}));
    await apiDelete('/items/1', 'tenant-5');
    expect(fetch).toHaveBeenCalledWith(`${PROXY_BASE_URL}/items/1`, expect.objectContaining({ method: 'DELETE' }));
  });

  it('throws on non-ok response with detail message', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({ detail: 'Not found' }, false, 404));
    await expect(apiGet('/missing', 'tenant-1')).rejects.toThrow('Not found');
  });

  it('throws generic message when detail is not a string', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({ detail: 42 }, false, 500));
    await expect(apiGet('/fail', 'tenant-1')).rejects.toThrow('Request failed with status 500');
  });

  it('formats array detail errors with field locations', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeFetchResponse(
        {
          detail: [
            { loc: ['body', 'email'], msg: 'field required' },
            { loc: ['body', 'name'], msg: 'too short' },
          ],
        },
        false,
        422
      )
    );

    await expect(apiGet('/validation', 'tenant-1')).rejects.toThrow('body.email: field required; body.name: too short');
  });

  it('formats array detail when location is missing and ignores invalid entries', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeFetchResponse(
        {
          detail: [
            null,
            { loc: 'body.email', msg: 'field required' },
            { loc: ['body', 'name'], msg: 42 },
            { foo: 'bar' },
          ],
        },
        false,
        422
      )
    );

    await expect(apiGet('/validation-mixed', 'tenant-1')).rejects.toThrow('field required');
  });

  it('falls back to generic status when array detail has no usable messages', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeFetchResponse(
        {
          detail: [null, { loc: ['body', 'name'], msg: 42 }, { foo: 'bar' }],
        },
        false,
        422
      )
    );

    await expect(apiGet('/validation-empty', 'tenant-1')).rejects.toThrow('Request failed with status 422');
  });

  it('parses empty JSON body as empty object', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse('', true, 200, 'application/json'));
    const result = await apiGet('/empty', 'tenant-1');
    expect(result).toEqual({});
  });

  it('returns detail for malformed JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse('not-json', true, 200, 'application/json'));
    const result = await apiGet('/bad-json', 'tenant-1');
    expect(result).toEqual({ detail: 'not-json' });
  });

  it('parses non-JSON response as detail text', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse('plain text', true, 200, 'text/plain'));
    const result = await apiGet('/text', 'tenant-1');
    expect(result).toEqual({ detail: 'plain text' });
  });

  it('uses session tenant when no explicit tenantId provided', async () => {
    localStorage.setItem(STORAGE_TENANT_KEY, 'session-tenant');
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({}));
    await apiGet('/path', '');
    expect(fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-Tenant-Id': 'session-tenant' }),
      })
    );
  });

  it('includes X-Super-Admin-Key when set in session', async () => {
    setSuperAdminKeySession('admin-key-123');
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({}));
    await apiGet('/admin-path', 'tenant-1');
    expect(fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-Super-Admin-Key': 'admin-key-123' }),
      })
    );
  });

  it('retries GET on transient upstream errors and recovers automatically', async () => {
    vi.useFakeTimers();
    vi.mocked(fetch)
      .mockResolvedValueOnce(makeFetchResponse({ detail: 'Bad gateway' }, false, 502))
      .mockResolvedValueOnce(makeFetchResponse({ detail: 'Service unavailable' }, false, 503))
      .mockResolvedValueOnce(makeFetchResponse({ ok: true }, true, 200));

    const request = apiGet('/platform/load', 'tenant-1');
    await vi.runAllTimersAsync();
    const result = await request;

    expect(fetch).toHaveBeenCalledTimes(3);
    expect(result).toEqual({ ok: true });
    expect(window.dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'nuxtron:auto-recovery:start' }));
    expect(window.dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'nuxtron:auto-recovery:end' }));
    vi.useRealTimers();
  });

  it('does not retry POST on failure to avoid duplicate writes', async () => {
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({ detail: 'Service unavailable' }, false, 503));

    await expect(apiPost('/platform/write', { value: 1 }, 'tenant-1')).rejects.toThrow('Service unavailable');
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('stops after max retries on transient upstream errors', async () => {
    vi.useFakeTimers();
    vi.mocked(fetch).mockResolvedValue(makeFetchResponse({ detail: 'Gateway timeout' }, false, 504));

    const request = apiGet('/platform/retry-exhausted', 'tenant-1');
    const assertion = expect(request).rejects.toThrow('Gateway timeout');
    await vi.runAllTimersAsync();

    await assertion;
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(window.dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'nuxtron:auto-recovery:start' }));
    expect(window.dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'nuxtron:auto-recovery:end' }));
    vi.useRealTimers();
  });

  it('retries GET network failures and surfaces the final network error', async () => {
    vi.useFakeTimers();
    vi.mocked(fetch).mockRejectedValue(new Error('network down'));

    const request = apiGet('/platform/network-fail', 'tenant-1');
    const assertion = expect(request).rejects.toThrow('network down');
    await vi.runAllTimersAsync();

    await assertion;
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(window.dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'nuxtron:auto-recovery:start' }));
    expect(window.dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'nuxtron:auto-recovery:end' }));
    vi.useRealTimers();
  });
});
