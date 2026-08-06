import { afterEach, describe, expect, it, vi } from 'vitest';

import { __test__ } from './route';

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('fastapi route fallback internals', () => {
  it('returns modules fallback payload with offline header', async () => {
    vi.stubEnv('NUXTRON_ALLOW_PROXY_FALLBACK', 'true');

    const response = __test__.buildOfflineFallbackResponse({
      method: 'GET',
      path: ['seo-platform', 'modules'],
      tenantId: 'tenant-demo',
      requestBody: undefined,
      detail: 'Upstream unavailable.',
      fallbackKind: 'offline',
    });

    expect(response).not.toBeNull();
    expect(response?.status).toBe(200);
    expect(response?.headers.get('X-Nuxtron-Fallback')).toBe('offline');

    const payload = await response?.json();
    expect(payload.total).toBeGreaterThan(0);
    expect(Array.isArray(payload.modules)).toBe(true);
  });

  it('returns llmo fallback payload for analyze post', async () => {
    vi.stubEnv('NUXTRON_ALLOW_PROXY_FALLBACK', 'true');

    const response = __test__.buildOfflineFallbackResponse({
      method: 'POST',
      path: ['seo-platform', 'llmo', 'analyze'],
      tenantId: 'tenant-demo',
      requestBody: JSON.stringify({ brand: 'Acme' }),
      detail: 'Forced fallback mode.',
      fallbackKind: 'forced',
    });

    expect(response).not.toBeNull();
    expect(response?.status).toBe(200);
    expect(response?.headers.get('X-Nuxtron-Fallback')).toBe('forced');

    const payload = await response?.json();
    expect(payload.fallback).toBe(true);
    expect(payload.model_representations.gpt_4).toContain('Acme');
    expect(Array.isArray(payload.knowledge_gap_topics)).toBe(true);
  });

  it('returns null when no fallback handler matches', () => {
    const response = __test__.buildOfflineFallbackResponse({
      method: 'GET',
      path: ['unknown', 'endpoint'],
      tenantId: 'tenant-demo',
      requestBody: undefined,
      detail: 'No route handler.',
      fallbackKind: 'offline',
    });

    expect(response).toBeNull();
  });

  it('forces fallback globally when env toggle is enabled', () => {
    vi.stubEnv('NUXTRON_PROXY_FORCE_FALLBACK', 'true');

    expect(__test__.isFallbackForced('GET', ['seo-platform', 'modules'])).toBe(true);
    expect(__test__.isFallbackForced('POST', ['seo-platform', 'llmo', 'analyze'])).toBe(true);
  });

  it('forces fallback for matching route rules only', () => {
    vi.stubEnv(
      'NUXTRON_PROXY_FORCE_FALLBACK_ROUTES',
      'seo-platform/modules, POST seo-platform/llmo/*, v1/loop/strategy-snapshots/*'
    );

    expect(__test__.isFallbackForced('GET', ['seo-platform', 'modules'])).toBe(true);
    expect(__test__.isFallbackForced('POST', ['seo-platform', 'llmo', 'analyze'])).toBe(true);
    expect(__test__.isFallbackForced('GET', ['v1', 'loop', 'strategy-snapshots', 'tenant-demo'])).toBe(true);
    expect(__test__.isFallbackForced('GET', ['seo-platform', 'health'])).toBe(false);
  });

  it('fails closed in production by excluding implicit localhost fallbacks', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('FASTAPI_URL', 'https://api.example.com');

    const upstreams = __test__.getUpstreamBaseUrls();

    expect(upstreams).toContain('https://api.example.com');
    expect(upstreams).not.toContain('http://127.0.0.1:8001');
    expect(upstreams).not.toContain('http://localhost:8001');
  });

  it('keeps localhost fallbacks outside production', () => {
    vi.stubEnv('NODE_ENV', 'development');

    const upstreams = __test__.getUpstreamBaseUrls();

    expect(upstreams).toContain('http://127.0.0.1:8001');
    expect(upstreams).toContain('http://localhost:8001');
  });

  it('detects production runtime using exported helper', () => {
    vi.stubEnv('NODE_ENV', 'production');
    expect(__test__.isProductionRuntime()).toBe(true);

    vi.stubEnv('NODE_ENV', 'development');
    expect(__test__.isProductionRuntime()).toBe(false);
  });
});
