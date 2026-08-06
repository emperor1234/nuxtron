export const PROXY_BASE_URL = '/api/fastapi';

export const DEFAULT_TENANT_ID = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || '').trim();
export const STORAGE_TOKEN_KEY = 'nuxtron.jwt';
export const STORAGE_TENANT_KEY = 'nuxtron.tenant';
export const STORAGE_SUPER_ADMIN_KEY = 'nuxtron.superAdminKey';

type JsonValue = Record<string, unknown>;

const RETRY_STATUS_CODES = new Set([502, 503, 504]);
const MAX_RETRIES = 2;

// In-flight GET dedupe, matching the same pattern already used in
// app/lib/platform-api.ts: if two components request the same
// tenant-scoped GET while a request is outstanding, they share one
// network call instead of firing duplicates. No TTL cache here (unlike
// platform-api.ts) — callers of this client include auth-sensitive reads
// that should stay always-fresh; this only collapses truly concurrent
// duplicate requests.
const INFLIGHT_GETS = new Map<string, Promise<JsonValue>>();

type RecoveryEventDetail = {
  path: string;
  attempt: number;
  totalRetries: number;
};

function isRetryableRequest(method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'): boolean {
  return method === 'GET';
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

function dispatchRecoveryEvent(eventName: string, detail: RecoveryEventDetail): void {
  if (!globalThis.window) return;
  globalThis.window.dispatchEvent(new CustomEvent(eventName, { detail }));
}

function getSessionTenant(): string {
  /* v8 ignore next */ if (!globalThis.window) return '';
  return globalThis.localStorage?.getItem(STORAGE_TENANT_KEY)?.trim() || '';
}

/** Reads the `exp` claim without verifying the signature — client-side this
 * is a UX check only ("don't bother sending an obviously-expired token"),
 * never a security boundary. Real verification happens server-side in
 * proxy.ts and the backend. */
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

function getSessionToken(): string {
  /* v8 ignore next */ if (!globalThis.window) return '';
  const token = globalThis.localStorage?.getItem(STORAGE_TOKEN_KEY)?.trim() || '';
  if (!token) return '';

  const exp = decodeTokenExpiry(token);
  if (exp !== null && Date.now() >= exp * 1000) {
    clearAuthSession();
    return '';
  }
  return token;
}

/**
 * Resolves the tenant scope for the current user from the authenticated
 * session, falling back to the configured default. Use this instead of a
 * user-editable tenant field so pages cannot pivot to another tenant's data
 * (A01: Broken Access Control).
 *
 * @returns The session tenant id, or `DEFAULT_TENANT_ID` when none is stored.
 */
export function resolveSessionTenant(): string {
  return getSessionTenant() || DEFAULT_TENANT_ID;
}

// sessionStorage, not localStorage: a super-admin key must not outlive the
// browser tab. localStorage persists indefinitely across restarts, which
// widens the window an XSS payload or a shared/unlocked machine could read
// it (A02: Cryptographic/Secrets Failure).
function getSuperAdminKey(): string {
  /* v8 ignore next */ if (!globalThis.window) return '';
  return globalThis.sessionStorage?.getItem(STORAGE_SUPER_ADMIN_KEY)?.trim() || '';
}

export function setAuthSession(token: string, tenantId: string): void {
  /* v8 ignore next */ if (!globalThis.window) return;
  if (token.trim()) {
    globalThis.localStorage?.setItem(STORAGE_TOKEN_KEY, token.trim());
  }
  if (tenantId.trim()) {
    globalThis.localStorage?.setItem(STORAGE_TENANT_KEY, tenantId.trim());
  }
}

export function clearAuthSession(): void {
  /* v8 ignore next */ if (!globalThis.window) return;
  globalThis.localStorage?.removeItem(STORAGE_TOKEN_KEY);
  globalThis.localStorage?.removeItem(STORAGE_TENANT_KEY);
}

/**
 * Mirrors the session token into an httpOnly cookie (`/api/auth/session`) so
 * `proxy.ts` can verify it server-side on the next navigation, before any
 * protected page shell is rendered. Call this right after `setAuthSession`
 * on login/register. Failure is non-fatal to the caller — the localStorage
 * token still lets API calls succeed — but the user will be bounced back to
 * /login by the server-side gate on their next page load, so callers should
 * surface a warning if this rejects.
 */
export async function syncServerSession(token: string): Promise<boolean> {
  /* v8 ignore next */ if (!globalThis.window) return false;
  try {
    const response = await fetch('/api/auth/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

/** Clears the httpOnly session cookie set by `syncServerSession`. */
export async function clearServerSession(): Promise<void> {
  /* v8 ignore next */ if (!globalThis.window) return;
  try {
    await fetch('/api/auth/session', { method: 'DELETE' });
  } catch {
    // Best-effort: if this fails the cookie expires on its own at token exp.
  }
}

/**
 * A 401 from the backend means the session is no longer valid (expired,
 * revoked, or the tenant/token combination was rejected) — there is nothing
 * a retry can fix. Clear the stale session and send the user back to login
 * rather than leaving the UI in an inconsistent authenticated-looking state.
 */
function handleUnauthorized(): void {
  /* v8 ignore next */ if (!globalThis.window) return;
  clearAuthSession();
  void clearServerSession();
  if (globalThis.window.location.pathname !== '/login') {
    globalThis.window.location.href = '/login';
  }
}

export function setSuperAdminKeySession(superAdminKey: string): void {
  /* v8 ignore next */ if (!globalThis.window) return;
  if (superAdminKey.trim()) {
    globalThis.sessionStorage?.setItem(STORAGE_SUPER_ADMIN_KEY, superAdminKey.trim());
  }
}

async function parseBody(response: Response): Promise<JsonValue> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    const text = await response.text();
    if (!text.trim()) {
      return {};
    }
    try {
      return JSON.parse(text) as JsonValue;
    } catch {
      return { detail: text };
    }
  }
  const text = await response.text();
  return text.trim() ? { detail: text } : {};
}

function formatErrorDetail(detail: unknown, status: number): string {
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== 'object') {
          return null;
        }

        const message = typeof item.msg === 'string' ? item.msg : '';
        const location = Array.isArray(item.loc)
          ? item.loc.filter((value: unknown) => typeof value === 'string' || typeof value === 'number').join('.')
          : '';

        if (message && location) {
          return `${location}: ${message}`;
        }

        return message || null;
      })
      .filter((value): value is string => Boolean(value));

    if (messages.length) {
      return messages.join('; ');
    }
  }

  return `Request failed with status ${status}`;
}

async function apiRequest( // NOSONAR
  path: string,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  tenantId: string,
  body?: JsonValue,
  extraHeaders?: Record<string, string>
): Promise<JsonValue> {
  const resolvedTenant = tenantId.trim() || getSessionTenant() || DEFAULT_TENANT_ID;
  if (!resolvedTenant) {
    throw new Error(
      'Tenant id is required in strict no-mock mode. Set NEXT_PUBLIC_DEFAULT_TENANT_ID or provide tenantId.'
    );
  }
  const superAdminKey = getSuperAdminKey();
  const sessionToken = getSessionToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-Id': resolvedTenant,
  };

  if (superAdminKey) {
    headers['X-Super-Admin-Key'] = superAdminKey;
  }
  if (sessionToken) {
    headers.Authorization = `Bearer ${sessionToken}`;
  }
  if (extraHeaders) {
    for (const [name, value] of Object.entries(extraHeaders)) {
      if (value.trim()) {
        headers[name] = value;
      }
    }
  }

  const canRetry = isRetryableRequest(method);
  const url = `${PROXY_BASE_URL}${path}`;
  const init: RequestInit = {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store',
  };

  let lastError: Error | null = null;
  let recoveryStarted = false;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt += 1) {
    try {
      const response = await fetch(url, init);
      const result = { response, data: await parseBody(response) };

      if (!result.response.ok) {
        const detail = formatErrorDetail(result.data.detail, result.response.status);

        if (result.response.status === 401) {
          handleUnauthorized();
        }

        if (canRetry && RETRY_STATUS_CODES.has(result.response.status) && attempt < MAX_RETRIES) {
          recoveryStarted = true;
          dispatchRecoveryEvent('nuxtron:auto-recovery:start', {
            path,
            attempt: attempt + 1,
            totalRetries: MAX_RETRIES,
          });
          await sleep(200 * (attempt + 1));
          continue;
        }

        throw new Error(detail);
      }

      if (recoveryStarted) {
        dispatchRecoveryEvent('nuxtron:auto-recovery:end', {
          path,
          attempt: attempt + 1,
          totalRetries: MAX_RETRIES,
        });
      }

      return result.data;
    } catch (error) {
      const retryableNetworkFailure = canRetry && attempt < MAX_RETRIES;
      if (!retryableNetworkFailure) {
        if (recoveryStarted) {
          dispatchRecoveryEvent('nuxtron:auto-recovery:end', {
            path,
            attempt: attempt + 1,
            totalRetries: MAX_RETRIES,
          });
        }
        throw error;
      }

      recoveryStarted = true;
      dispatchRecoveryEvent('nuxtron:auto-recovery:start', {
        path,
        attempt: attempt + 1,
        totalRetries: MAX_RETRIES,
      });

      await sleep(200 * (attempt + 1));
      lastError = error instanceof Error ? error : new Error('Unknown request error');
    }
  }

  throw lastError || new Error('Unable to recover request after retries.');
}

export async function apiGet(path: string, tenantId = DEFAULT_TENANT_ID): Promise<JsonValue> {
  const resolvedTenant = tenantId.trim() || getSessionTenant() || DEFAULT_TENANT_ID;
  const key = `${resolvedTenant}:${path}`;

  const existing = INFLIGHT_GETS.get(key);
  if (existing) return existing;

  const task = apiRequest(path, 'GET', tenantId).finally(() => {
    INFLIGHT_GETS.delete(key);
  });
  INFLIGHT_GETS.set(key, task);
  return task;
}

export async function apiPost(
  path: string,
  body: JsonValue,
  tenantId = DEFAULT_TENANT_ID,
  extraHeaders?: Record<string, string>
): Promise<JsonValue> {
  return apiRequest(path, 'POST', tenantId, body, extraHeaders);
}

export async function apiPatch(path: string, body: JsonValue, tenantId = DEFAULT_TENANT_ID): Promise<JsonValue> {
  return apiRequest(path, 'PATCH', tenantId, body);
}

export async function apiPut(path: string, body: JsonValue, tenantId = DEFAULT_TENANT_ID): Promise<JsonValue> {
  return apiRequest(path, 'PUT', tenantId, body);
}

export async function apiDelete(path: string, tenantId = DEFAULT_TENANT_ID): Promise<JsonValue> {
  return apiRequest(path, 'DELETE', tenantId);
}
