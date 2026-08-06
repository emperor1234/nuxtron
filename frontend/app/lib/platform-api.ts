const API_BASE = '/api/fastapi';
const FALLBACK_TENANT_ID = 'tenant-demo';

export const DEFAULT_TENANT_ID = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || '').trim();
const API_TIMEOUT_MS = 45000;
const RESPONSE_CACHE_TTL_MS = 120000;
const INFLIGHT_REQUESTS = new Map<string, Promise<any>>();
const RESPONSE_CACHE = new Map<string, { expiresAt: number; value: unknown }>();
const LOCAL_CACHE_PREFIX = 'nuxtron:platform-api:';
const STORAGE_TOKEN_KEY = 'nuxtron.jwt';

function clearCachedEntry(cacheKey: string): void {
  RESPONSE_CACHE.delete(cacheKey);
  if (!globalThis.window) return;
  try {
    globalThis.localStorage.removeItem(LOCAL_CACHE_PREFIX + cacheKey);
  } catch {
    // Ignore localStorage removal errors; in-memory cache is already cleared.
  }
}

export function invalidateTenantGetCache(tenantId: string): void {
  const tenantPrefix = `GET:${tenantId}:`;
  for (const key of RESPONSE_CACHE.keys()) {
    if (key.startsWith(tenantPrefix)) clearCachedEntry(key);
  }

  if (!globalThis.window) return;
  try {
    for (let index = globalThis.localStorage.length - 1; index >= 0; index -= 1) {
      const storageKey = globalThis.localStorage.key(index);
      if (!storageKey?.startsWith(LOCAL_CACHE_PREFIX)) continue;
      const cacheKey = storageKey.slice(LOCAL_CACHE_PREFIX.length);
      if (cacheKey.startsWith(tenantPrefix)) {
        globalThis.localStorage.removeItem(storageKey);
      }
    }
  } catch {
    // Ignore localStorage iteration errors; fresh in-memory reads still continue.
  }
}

function requestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Reads `exp` without verifying the signature — a client-side UX check
 * only; real verification happens server-side in proxy.ts and the backend. */
function decodeTokenExpiry(token: string): number | null {
  try {
    const [, payloadSegment] = token.split('.');
    if (!payloadSegment) return null;
    const normalized = payloadSegment.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');
    const payload = JSON.parse(atob(padded)) as { exp?: unknown };
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
}

function readSessionToken(): string {
  if (!globalThis.window) return '';
  const token = globalThis.localStorage?.getItem(STORAGE_TOKEN_KEY)?.trim() || '';
  if (!token) return '';
  const exp = decodeTokenExpiry(token);
  if (exp !== null && Date.now() >= exp * 1000) {
    globalThis.localStorage?.removeItem(STORAGE_TOKEN_KEY);
    return '';
  }
  return token;
}

/** A 401 means the session is no longer valid — clear it and bounce to
 * login rather than leaving the UI in an inconsistent authenticated state. */
function handleUnauthorized(): void {
  if (!globalThis.window) return;
  globalThis.localStorage?.removeItem(STORAGE_TOKEN_KEY);
  void fetch('/api/auth/session', { method: 'DELETE' }).catch(() => {});
  if (globalThis.window.location.pathname !== '/login') {
    globalThis.window.location.href = '/login';
  }
}

async function parseResponseBody(res: Response): Promise<unknown> {
  const contentType = res.headers.get('content-type') || '';
  const raw = await res.text();
  if (!raw) return {};
  if (contentType.toLowerCase().includes('application/json')) {
    try {
      return JSON.parse(raw);
    } catch {
      return { detail: raw };
    }
  }
  return { detail: raw };
}

function inflightKey(method: string, path: string, tenantId: string, payload?: unknown): string {
  const payloadPart = payload === undefined ? '' : JSON.stringify(payload);
  return `${method}:${tenantId}:${path}:${payloadPart}`;
}

function getRequestTimeoutMs(path: string): number {
  if (path === '/seo-platform/performance/audit') {
    return 120000;
  }
  return API_TIMEOUT_MS;
}

function getCachedResponse<T>(key: string): T | null {
  const cached = RESPONSE_CACHE.get(key);
  if (cached) {
    if (cached.expiresAt <= Date.now()) {
      RESPONSE_CACHE.delete(key);
    } else {
      return cached.value as T;
    }
  }

  if (!globalThis.window) return null;
  try {
    const raw = globalThis.localStorage.getItem(LOCAL_CACHE_PREFIX + key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { expiresAt?: number; value?: unknown };
    if (!parsed || typeof parsed.expiresAt !== 'number' || parsed.expiresAt <= Date.now()) {
      globalThis.localStorage.removeItem(LOCAL_CACHE_PREFIX + key);
      return null;
    }
    RESPONSE_CACHE.set(key, { expiresAt: parsed.expiresAt, value: parsed.value });
    return parsed.value as T;
  } catch {
    return null;
  }
}

function setCachedResponse<T>(key: string, value: T): void {
  const entry = {
    expiresAt: Date.now() + RESPONSE_CACHE_TTL_MS,
    value,
  };
  RESPONSE_CACHE.set(key, entry);
  if (!globalThis.window) return;
  try {
    globalThis.localStorage.setItem(LOCAL_CACHE_PREFIX + key, JSON.stringify(entry));
  } catch {
    // Ignore localStorage write errors (quota/private mode); in-memory cache still works.
  }
}

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  let requestPath = '';
  if (typeof input === 'string') {
    requestPath = input;
  } else if (input instanceof URL) {
    requestPath = input.pathname;
  }
  const timeout = setTimeout(() => controller.abort(), getRequestTimeoutMs(requestPath.replace(/^\/api\/fastapi/, '')));
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

function dedupeInFlight<T>(key: string, run: () => Promise<T>): Promise<T> {
  const existing = INFLIGHT_REQUESTS.get(key);
  if (existing !== undefined) return existing;
  const task = run().finally(() => INFLIGHT_REQUESTS.delete(key));
  INFLIGHT_REQUESTS.set(key, task);
  return task;
}

export async function apiGet<T>(path: string, tenantId = DEFAULT_TENANT_ID): Promise<T> {
  const resolvedTenantId = tenantId.trim() || DEFAULT_TENANT_ID || FALLBACK_TENANT_ID;

  const key = inflightKey('GET', path, resolvedTenantId);
  const cached = getCachedResponse<T>(key);
  if (cached !== null) return cached;

  return dedupeInFlight<T>(key, async () => {
    const token = readSessionToken();
    const res = await fetchWithTimeout(`${API_BASE}${path}`, {
      method: 'GET',
      headers: {
        'X-Tenant-Id': resolvedTenantId,
        'X-Request-ID': requestId(),
        // No X-API-Key here: the service key is a server-only secret set by
        // the proxy route (app/api/fastapi/[...path]/route.ts). Client code
        // must never hold or forward it.
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: 'no-store',
    });
    const data = (await parseResponseBody(res)) as Record<string, unknown>;
    const detail = typeof data?.detail === 'string' ? data.detail : `Request failed: ${res.status}`;
    if (res.status === 401) handleUnauthorized();
    if (!res.ok) throw new Error(detail);
    const typed = data as T;
    setCachedResponse(key, typed);
    return typed;
  });
}

export async function apiSend<T>(
  path: string,
  method: 'POST' | 'PATCH' | 'PUT' | 'DELETE',
  payload?: unknown,
  tenantId = DEFAULT_TENANT_ID
): Promise<T> {
  const resolvedTenantId = tenantId.trim() || DEFAULT_TENANT_ID || FALLBACK_TENANT_ID;

  const cacheKey = inflightKey(method, path, resolvedTenantId, payload);
  const shouldCachePost =
    method === 'POST' && path.startsWith('/seo-platform/') && path !== '/seo-platform/performance/rum/ingest';
  if (shouldCachePost) {
    const cached = getCachedResponse<T>(cacheKey);
    if (cached !== null) return cached;
  }

  const run = async () => {
    const token = readSessionToken();
    const res = await fetchWithTimeout(`${API_BASE}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Id': resolvedTenantId,
        'X-Request-ID': requestId(),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });
    const data = (await parseResponseBody(res)) as Record<string, unknown>;
    const detail = typeof data?.detail === 'string' ? data.detail : `Request failed: ${res.status}`;
    if (res.status === 401) handleUnauthorized();
    if (!res.ok) throw new Error(detail);
    const typed = data as T;
    invalidateTenantGetCache(resolvedTenantId);
    if (shouldCachePost) setCachedResponse(cacheKey, typed);
    return typed;
  };

  // Most SEO calls are idempotent analyses; in-flight dedupe prevents duplicate compute work.
  if (shouldCachePost) {
    return dedupeInFlight<T>(cacheKey, run);
  }
  return run();
}
