import { NextRequest, NextResponse } from 'next/server';
import { SESSION_COOKIE_NAME } from '@/app/lib/auth/session-cookie';

/**
 * Same-origin gateway to the FastAPI backend.
 *
 * It authenticates the call (service key + the caller's session token), scopes
 * it to a tenant, bounds time and body size, and returns exactly what the
 * backend returned. It never fabricates a response: when the backend is
 * unreachable or errors, the caller receives that failure so the page can show
 * an honest error state instead of invented data.
 */

const ALLOWED_METHODS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']);
const NO_STORE = { 'Cache-Control': 'no-store' } as const;
const PASSTHROUGH_HEADERS = ['content-type', 'cache-control', 'x-request-id', 'x-process-time'];

function isProductionRuntime(): boolean {
  return (process.env.NODE_ENV || '').trim().toLowerCase() === 'production';
}

function getUpstreamBaseUrls(): string[] {
  const envCandidates = [
    process.env.FASTAPI_URL || '',
    process.env.NEXT_PUBLIC_FASTAPI_URL || '',
    process.env.LOCAL_FASTAPI_URL || '',
  ]
    .map((value) => value.trim().replace(/\/$/, ''))
    .filter(Boolean);

  // Production only ever talks to explicitly configured upstreams.
  if (isProductionRuntime()) return Array.from(new Set(envCandidates));

  const localhostCandidates = [
    'http://127.0.0.1:8001',
    'http://localhost:8001',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
  ];
  return Array.from(new Set([...envCandidates, ...localhostCandidates]));
}

function getServiceApiKey(): string {
  // Server-only secret. Deliberately has no NEXT_PUBLIC_* fallback: that would
  // ship the backend service key inside the client bundle.
  return (process.env.FASTAPI_API_KEY || '').trim();
}

function getTenantId(request: NextRequest): string {
  const headerTenant = request.headers.get('x-tenant-id')?.trim() || '';
  const queryTenant = request.nextUrl.searchParams.get('tenant_id')?.trim() || '';
  const defaultTenant = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || '').trim();
  return headerTenant || queryTenant || defaultTenant;
}

function getUpstreamTimeoutMs(path: string[]): number {
  const joined = path.join('/');
  // AI inference routes can take much longer than CRUD endpoints.
  if (joined.startsWith('ira/agent/brain/reason') || joined.startsWith('ai/gateway/generate') || joined.startsWith('vse/')) {
    return 45_000;
  }
  if (joined.startsWith('seo-platform/') || joined.startsWith('content/generate') || joined.startsWith('ai/')) {
    return 60_000;
  }
  return 12_000;
}

function cookieAuthorization(request: NextRequest): string | null {
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value?.trim();
  return token ? `Bearer ${token}` : null;
}

function buildUpstreamHeaders(request: NextRequest, serviceApiKey: string, tenantId: string): Headers {
  const contentType = request.headers.get('content-type') || undefined;
  const requestId = request.headers.get('x-request-id');
  // EventSource (SSE job streams) cannot set custom headers, so fall back to
  // the httpOnly session cookie the browser attaches automatically.
  const authorization = request.headers.get('authorization') || cookieAuthorization(request);

  const headers = new Headers();
  headers.set('X-API-Key', serviceApiKey);
  headers.set('X-Tenant-Id', tenantId);
  if (requestId) headers.set('X-Request-ID', requestId);
  if (contentType) headers.set('Content-Type', contentType);
  // Forward the caller's session so the backend authenticates the actual user,
  // not just the shared service key plus a client-supplied tenant id.
  if (authorization) headers.set('Authorization', authorization);
  return headers;
}

function buildUpstreamUrl(base: string, pathname: string, query: string, isStreamRequest: boolean, serviceApiKey: string): string {
  const url = query ? `${base}/${pathname}?${query}` : `${base}/${pathname}`;
  if (!isStreamRequest || !serviceApiKey) return url;

  const withKey = new URL(url);
  if (!withKey.searchParams.get('api_key')) withKey.searchParams.set('api_key', serviceApiKey);
  return withKey.toString();
}

/** Try each configured upstream in order; return the first that answers. */
async function fetchFromUpstreams({
  upstreamBases,
  pathname,
  query,
  isStreamRequest,
  serviceApiKey,
  init,
  timeoutMs,
}: {
  upstreamBases: string[];
  pathname: string;
  query: string;
  isStreamRequest: boolean;
  serviceApiKey: string;
  init: RequestInit;
  timeoutMs: number;
}): Promise<{ upstreamRes: Response | null; lastError: unknown }> {
  let lastError: unknown = null;
  for (const base of upstreamBases) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const upstreamRes = await fetch(buildUpstreamUrl(base, pathname, query, isStreamRequest, serviceApiKey), {
        ...init,
        signal: controller.signal,
      });
      return { upstreamRes, lastError: null };
    } catch (error) {
      lastError = error;
    } finally {
      clearTimeout(timeoutId);
    }
  }
  return { upstreamRes: null, lastError };
}

// Bounds how much of a request body this route buffers before forwarding it.
// A large concurrent burst of uploads could otherwise exhaust server memory.
// This is a resource guard, not a substitute for content scanning.
const DEFAULT_MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024;

function resolveMaxRequestBodyBytes(): number {
  const parsed = Number(process.env.NUXTRON_MAX_REQUEST_BODY_BYTES);
  // A non-numeric override must not silently disable the cap.
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_MAX_REQUEST_BODY_BYTES;
}

function checkRequestBodySize(request: NextRequest): NextResponse | null {
  const limit = resolveMaxRequestBodyBytes();
  const contentLength = Number(request.headers.get('content-length') || 0);
  if (contentLength > limit) {
    return NextResponse.json({ detail: `Request body exceeds the ${limit}-byte limit.` }, { status: 413, headers: NO_STORE });
  }
  return null;
}

function getProxyConfigError(upstreamBases: string[], serviceApiKey: string, tenantId: string): NextResponse | null {
  if (!upstreamBases.length) {
    return NextResponse.json({ detail: 'FASTAPI_URL is not configured.' }, { status: 500, headers: NO_STORE });
  }
  if (!serviceApiKey) {
    return NextResponse.json({ detail: 'FASTAPI_API_KEY is not configured on the server.' }, { status: 500, headers: NO_STORE });
  }
  if (!tenantId) {
    return NextResponse.json({ detail: 'Tenant id is required.' }, { status: 400, headers: NO_STORE });
  }
  return null;
}

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const method = request.method.toUpperCase();
  if (!ALLOWED_METHODS.has(method)) {
    return NextResponse.json({ detail: 'Method not allowed.' }, { status: 405, headers: NO_STORE });
  }

  const upstreamBases = getUpstreamBaseUrls();
  const serviceApiKey = getServiceApiKey();
  const tenantId = getTenantId(request);

  const configError = getProxyConfigError(upstreamBases, serviceApiKey, tenantId);
  if (configError) return configError;

  const bodySizeError = checkRequestBodySize(request);
  if (bodySizeError) return bodySizeError;

  const requestBody = method === 'GET' || method === 'DELETE' ? undefined : await request.text();

  const { upstreamRes, lastError } = await fetchFromUpstreams({
    upstreamBases,
    pathname: path.map(encodeURIComponent).join('/'),
    query: request.nextUrl.searchParams.toString(),
    isStreamRequest: path.at(-1) === 'stream',
    serviceApiKey,
    init: {
      method,
      headers: buildUpstreamHeaders(request, serviceApiKey, tenantId),
      cache: 'no-store',
      body: requestBody,
    },
    timeoutMs: getUpstreamTimeoutMs(path),
  });

  if (!upstreamRes) {
    const detail = lastError instanceof Error ? lastError.message : 'Unable to reach the API.';
    return NextResponse.json({ detail }, { status: 502, headers: NO_STORE });
  }

  const responseHeaders = new Headers();
  for (const key of PASSTHROUGH_HEADERS) {
    const value = upstreamRes.headers.get(key);
    if (value) responseHeaders.set(key, value);
  }
  responseHeaders.set('Cache-Control', 'no-store');

  return new NextResponse(upstreamRes.body, { status: upstreamRes.status, headers: responseHeaders });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function handle(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export const __test__ = {
  getUpstreamBaseUrls,
  isProductionRuntime,
  getProxyConfigError,
  getUpstreamTimeoutMs,
  buildUpstreamUrl,
};
