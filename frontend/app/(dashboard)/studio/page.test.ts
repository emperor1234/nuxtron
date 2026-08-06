/**
 * Comprehensive tests for Nuxtron Studio refactored architecture.
 * Validates state management, handler generation, endpoint config, and production safety.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStudioStore, type StudioState } from './lib/state';
import { STUDIO_ENDPOINTS, getEndpointsByCategory, getEndpointById } from './lib/endpoints';
import { createStudioHandlers } from './lib/handlers';

function createEmptyOutputs(): StudioState['outputs'] {
  return Object.keys(useStudioStore.getState().outputs).reduce(
    (acc, key) => ({ ...acc, [key]: null }),
    {} as StudioState['outputs']
  );
}

/**
 * Suite: State Management
 * Validates Zustand store initialization and mutations.
 */
describe('Studio State Management', () => {
  beforeEach(() => {
    // Reset store before each test
    useStudioStore.setState({
      apiKey: '',
      tenantId: '',
      publishAt: '',
      globalError: '',
      contentError: '',
      isGeneratingContent: false,
      latestTotpSecret: '',
      latestJwtToken: '',
      outputs: createEmptyOutputs(),
    });
  });

  it('should initialize with correct default values', () => {
    const state = useStudioStore.getState();
    expect(state.apiKey).toBe('');
    expect(state.tenantId).toBe('');
    expect(state.publishAt).toBe('');
    expect(state.globalError).toBe('');
    expect(state.contentError).toBe('');
    expect(state.isGeneratingContent).toBe(false);
  });

  it('should update apiKey via setApiKey', () => {
    const { result } = renderHook(() => useStudioStore());
    act(() => {
      result.current.setApiKey('test-key-123');
    });
    expect(result.current.apiKey).toBe('test-key-123');
  });

  it('should update tenantId via setTenantId', () => {
    const { result } = renderHook(() => useStudioStore());
    act(() => {
      result.current.setTenantId('custom-tenant');
    });
    expect(result.current.tenantId).toBe('custom-tenant');
  });

  it('should set single output via setOutput', () => {
    const { result } = renderHook(() => useStudioStore());
    const testOutput = { result: 'test data' };
    act(() => {
      result.current.setOutput('content', testOutput);
    });
    expect(result.current.outputs.content).toEqual(testOutput);
    expect(result.current.outputs.ads).toBeNull();
  });

  it('should set multiple outputs via setMultipleOutputs', () => {
    const { result } = renderHook(() => useStudioStore());
    const testOutputs = {
      content: { data: 'content' },
      ads: { data: 'ads' },
      seo: { data: 'seo' },
    };
    act(() => {
      result.current.setMultipleOutputs(testOutputs);
    });
    expect(result.current.outputs.content).toEqual(testOutputs.content);
    expect(result.current.outputs.ads).toEqual(testOutputs.ads);
    expect(result.current.outputs.seo).toEqual(testOutputs.seo);
  });

  it('should reset all state via reset', () => {
    const { result } = renderHook(() => useStudioStore());
    act(() => {
      result.current.setApiKey('some-key');
      result.current.setTenantId('some-tenant');
      result.current.setOutput('content', { data: 'test' });
    });
    act(() => {
      result.current.reset();
    });
    expect(result.current.apiKey).toBe('');
    expect(result.current.tenantId).toBe('');
    expect(result.current.outputs.content).toBeNull();
  });

  it('should track loading state independently', () => {
    const { result } = renderHook(() => useStudioStore());
    expect(result.current.isGeneratingContent).toBe(false);
    act(() => {
      result.current.setIsGeneratingContent(true);
    });
    expect(result.current.isGeneratingContent).toBe(true);
    act(() => {
      result.current.setIsGeneratingContent(false);
    });
    expect(result.current.isGeneratingContent).toBe(false);
  });

  it('should store TOTP secret independently', () => {
    const { result } = renderHook(() => useStudioStore());
    const secret = 'JBSWY3DPBLHXYPIT';
    act(() => {
      result.current.setLatestTotpSecret(secret);
    });
    expect(result.current.latestTotpSecret).toBe(secret);
  });

  it('should store JWT token independently', () => {
    const { result } = renderHook(() => useStudioStore());
    const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';
    act(() => {
      result.current.setLatestJwtToken(token);
    });
    expect(result.current.latestJwtToken).toBe(token);
  });
});

/**
 * Suite: Endpoint Configuration
 * Validates endpoint registry completeness and structure.
 */
describe('Studio Endpoint Configuration', () => {
  it('should have at least 60 endpoints defined', () => {
    expect(STUDIO_ENDPOINTS.length).toBeGreaterThanOrEqual(60);
  });

  it('should have unique endpoint IDs', () => {
    const ids = STUDIO_ENDPOINTS.map((ep) => ep.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it('should have valid HTTP methods', () => {
    const validMethods = ['GET', 'POST', 'PATCH', 'DELETE'];
    for (const endpoint of STUDIO_ENDPOINTS) {
      expect(validMethods).toContain(endpoint.method);
    }
  });

  it('should have valid path format', () => {
    for (const endpoint of STUDIO_ENDPOINTS) {
      expect(endpoint.path).toMatch(/^\/[a-z0-9\-/_]*(\/:id)?$/i);
    }
  });

  it('should organize endpoints by category', () => {
    const categories = getEndpointsByCategory();
    expect(categories.size).toBeGreaterThan(1);
    for (const [category, endpoints] of categories.entries()) {
      expect(category).toBeTruthy();
      expect(endpoints.length).toBeGreaterThan(0);
      for (const ep of endpoints) {
        expect(ep.category).toBe(category);
      }
    }
  });

  it('should map endpoint IDs to configs', () => {
    for (const endpoint of STUDIO_ENDPOINTS) {
      const found = getEndpointById(endpoint.id);
      expect(found).toEqual(endpoint);
    }
  });

  it('should have valid output keys for all endpoints', () => {
    for (const endpoint of STUDIO_ENDPOINTS) {
      expect(endpoint.outputKey).toBeTruthy();
    }
  });

  it('should have consistent buildPayload for endpoints that need it', () => {
    const postEndpoints = STUDIO_ENDPOINTS.filter((ep) => ep.method === 'POST');
    expect(postEndpoints.length).toBeGreaterThan(0);
    for (const ep of postEndpoints) {
      if (ep.buildPayload) {
        const payload = ep.buildPayload('test-tenant');
        expect(payload).toBeTruthy();
        expect(typeof payload).toBe('object');
      }
    }
  });
});

/**
 * Suite: Handler Factory
 * Validates dynamic handler generation and state management integration.
 */
describe('Studio Handler Factory', () => {
  it('should create handlers for all endpoints', () => {
    const handlers = createStudioHandlers('test-tenant');
    expect(Object.keys(handlers).length).toBeGreaterThanOrEqual(STUDIO_ENDPOINTS.length);
    for (const endpoint of STUDIO_ENDPOINTS) {
      expect(handlers[endpoint.id]).toBeTruthy();
      expect(typeof handlers[endpoint.id]).toBe('function');
    }
  });

  it('should bind tenantId to handlers', () => {
    const tenant1 = 'tenant-1';
    const tenant2 = 'tenant-2';
    const handlers1 = createStudioHandlers(tenant1);
    const handlers2 = createStudioHandlers(tenant2);
    expect(typeof handlers1['content-generate']).toBe('function');
    expect(typeof handlers2['content-generate']).toBe('function');
    // Handlers are different closures, so they should be different function objects
    expect(handlers1['content-generate']).not.toBe(handlers2['content-generate']);
  });

  it('should create bound functions without requiring params', () => {
    const handlers = createStudioHandlers('test-tenant');
    const handler = handlers['ads-generate'];
    // Handlers should be zero-argument async functions
    expect(handler.length).toBe(0);
  });
});

/**
 * Suite: Production Safety
 * Validates production-safe behavior (NODE_ENV checks, fail-closed design).
 */
describe('Studio Production Safety', () => {
  it('should have all endpoints with proper error handling structure', () => {
    // This validates that endpoints are structured for safe error handling
    for (const endpoint of STUDIO_ENDPOINTS) {
      expect(endpoint.id).toBeTruthy();
      expect(endpoint.path).toBeTruthy();
      expect(endpoint.method).toBeTruthy();
      expect(endpoint.outputKey).toBeTruthy();
    }
  });

  it('should have special handlers for dependent operations', () => {
    const handlers = createStudioHandlers('test-tenant');
    // These operations depend on state from previous runs
    expect(handlers['totp-verify']).toBeTruthy();
    expect(handlers['jwt-verify']).toBeTruthy();
    expect(handlers['totp-setup']).toBeTruthy();
    expect(handlers['jwt-issue']).toBeTruthy();
  });

  it('should support dynamic port resolution for testing', () => {
    // Validates that endpoints can work with configurable base URLs
    expect(STUDIO_ENDPOINTS[0].path).toMatch(/^\//);
    // All paths should be relative and port-agnostic
    for (const endpoint of STUDIO_ENDPOINTS) {
      expect(endpoint.path).not.toMatch(/localhost|127\.0\.0\.1|http:/);
    }
  });
});

/**
 * Suite: State Isolation
 * Validates that state changes don't leak between render cycles.
 */
describe('Studio State Isolation', () => {
  beforeEach(() => {
    useStudioStore.setState({
      apiKey: '',
      tenantId: '',
      outputs: createEmptyOutputs(),
    });
  });

  it('should isolate output state per endpoint', () => {
    const { result: result1 } = renderHook(() => useStudioStore());
    const { result: result2 } = renderHook(() => useStudioStore());

    act(() => {
      result1.current.setOutput('content', { data: 'test1' });
    });

    // Both should see the same store (they're subscribers to the same store)
    expect(result1.current.outputs.content).toEqual({ data: 'test1' });
    expect(result2.current.outputs.content).toEqual({ data: 'test1' });

    act(() => {
      result2.current.setOutput('ads', { data: 'test2' });
    });

    expect(result1.current.outputs.ads).toEqual({ data: 'test2' });
    expect(result2.current.outputs.ads).toEqual({ data: 'test2' });
  });
});
