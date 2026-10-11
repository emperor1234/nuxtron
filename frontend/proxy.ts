import { NextRequest, NextResponse } from 'next/server';
import { verifySessionToken } from '@/app/lib/auth/jwt-edge';
import INTERNAL_CONSOLES from '@/app/lib/internal-consoles.json';
import { SESSION_COOKIE_NAME } from '@/app/lib/auth/session-cookie';
import {
  PRODUCT_COOKIE_NAME,
  UNAVAILABLE_QUERY_PARAM,
  productForPath,
  resolveProductLine,
} from '@/app/lib/product-line';
import { buildContentSecurityPolicy, generateNonce } from '@/app/lib/security/csp';

/**
 * Proxy runs before matched requests. Three jobs:
 *
 * 1. Inject X-Tenant-Id on /api/fastapi/* calls so pages never need to pass
 *    it manually. Security headers are already handled in next.config.ts
 *    headers().
 * 2. Gate every app route that is NOT explicitly public: verify the session
 *    cookie server-side and redirect to /login before the page shell is
 *    ever rendered (A01: Broken Access Control). Previously this was
 *    enforced only by a client component (ClientAuthGuard) *after*
 *    hydration, meaning the protected markup was always sent to the
 *    browser regardless of auth state. ClientAuthGuard still runs as a
 *    defense-in-depth client-side check; this is the real gate.
 *
 * Route-group folders — `(public)` and `(dashboard)` — do not add a URL
 * segment, so app routes cannot be told apart by a path prefix. We
 * allowlist the known public surface instead: anything not in it is
 * treated as protected by default, so a newly added authenticated route
 * is protected automatically without this file needing an update.
 *
 * 3. Product lines (app/lib/product-line.ts): a session signed in to one
 *    product (SEO or Marketing) is redirected away from the other product's
 *    routes to `/dashboard?unavailable=<owner>`. `/dashboard` is the shared
 *    Home rail section, so `productForPath('/dashboard')` is always "shared"
 *    and the redirect can never bounce back into this branch (no loop).
 */

const PUBLIC_EXACT_PATHS = new Set([
  '/',
  '/about',
  '/blog',
  '/careers',
  '/case-studies',
  '/changelog',
  '/contact',
  '/faq',
  '/features',
  '/integrations',
  '/login',
  '/marketing',
  '/pricing',
  '/privacy',
  '/register',
  '/reset-password',
  '/terms',
  '/tools',
  '/trust',
]);

// /tools/translation-studio is the one surviving nested public page (the
// /tools listing page itself was removed, but a (dashboard) route re-exports
// this one — see app/(dashboard)/seo/ai-localization/page.tsx). /blog/
// covers individual [slug] post pages (the index itself is /blog, above).
const PUBLIC_PREFIXES = ['/tools/', '/blog/'];

// Paths that require an elevated role beyond plain authentication — the
// super-admin backend console plus the internal vendor-integration consoles
// listed in app/lib/internal-consoles.json. The
// backend RBAC layer (backend/fastapi/app/authz.py) is the real
// authorization boundary for API calls; this is a UI-level defense-in-depth
// gate so a non-admin session never even receives the admin page shell.
//
// Scoped to exactly the pages confirmed to use the super-admin key
// (app/lib/api-client.ts STORAGE_SUPER_ADMIN_KEY / X-Super-Admin-Key) —
// currently only /platform/backend. `/platform-ops` and `/white-label`
// sound admin-adjacent by name but have no such evidence in their page
// code; gating them here would incorrectly lock out regular users, and
// `/platform` itself hosts unrelated non-admin feature pages (e.g.
// /platform/owly-writer-ai), so the match must not be a bare prefix.
const ADMIN_ONLY_PATHS = ['/platform/backend', ...INTERNAL_CONSOLES.paths];
const ADMIN_ROLES = new Set(['admin', 'super_admin']);

// Same escape hatch as ClientAuthGuard (app/components/client-auth-guard.tsx)
// — both guards move together off one flag. Needed for the existing
// Playwright smoke suite, which navigates straight to protected routes with
// no login step; must never be set in a real deployment.
const AUTH_GUARD_DISABLED = process.env.NEXT_PUBLIC_DISABLE_AUTH_GUARD === 'true';

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_EXACT_PATHS.has(pathname)) return true;
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

function isAdminOnlyPath(pathname: string): boolean {
  return ADMIN_ONLY_PATHS.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

async function guardAppRoute(request: NextRequest): Promise<NextResponse | null> {
  if (AUTH_GUARD_DISABLED) return null;

  const { pathname } = request.nextUrl;
  if (isPublicPath(pathname)) return null;

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  const claims = token ? await verifySessionToken(token) : null;

  if (!claims) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('next', pathname);
    return NextResponse.redirect(loginUrl);
  }

  const isAdmin = claims.roles.some((role) => ADMIN_ROLES.has(role));

  if (isAdminOnlyPath(pathname) && !isAdmin) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return guardProductLine(request, pathname, {
    claim: claims.product,
    cookie: request.cookies.get(PRODUCT_COOKIE_NAME)?.value,
    isAdmin,
  });
}

/**
 * Keeps a product-restricted session inside its own product. The session's
 * product comes from the verified JWT claim first, then the httpOnly product
 * cookie set by /api/auth/session (both narrowed by `parseProductLine`, so a
 * tampered value simply means "unrestricted legacy session", never a crash or
 * an escalation). Admins and pre-product-line sessions are unrestricted.
 *
 * This is a UI-mode boundary, not an entitlement: the backend API remains the
 * authorization boundary for data.
 */
function guardProductLine(
  request: NextRequest,
  pathname: string,
  input: Parameters<typeof resolveProductLine>[0]
): NextResponse | null {
  const product = resolveProductLine(input);
  if (!product) return null;

  const owner = productForPath(pathname);
  if (owner === 'shared' || owner === product) return null;

  // Built from request.url with a fixed path, so the redirect can never leave
  // this origin, and `owner` is one of the two literal product names.
  const target = new URL('/dashboard', request.url);
  target.searchParams.set(UNAVAILABLE_QUERY_PARAM, owner);
  return NextResponse.redirect(target);
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith('/api/fastapi')) {
    const existing = request.headers.get('x-tenant-id')?.trim();
    const defaultTenant = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID?.trim() ?? '';
    const tenantId = existing || defaultTenant;

    if (tenantId) {
      const requestHeaders = new Headers(request.headers);
      requestHeaders.set('x-tenant-id', tenantId);
      return NextResponse.next({ request: { headers: requestHeaders } });
    }

    return NextResponse.next();
  }

  // All other API routes (health checks, /api/auth/session itself — called
  // *while* establishing the session cookie, so it must not be gated by the
  // cookie it's about to set) manage their own auth and must not be caught
  // by the page-redirect gate below.
  if (pathname.startsWith('/api/')) {
    return NextResponse.next();
  }

  const guardResponse = await guardAppRoute(request);
  if (guardResponse) return guardResponse;

  // Page render: attach a fresh nonce both to the outgoing request (so
  // app/layout.tsx can read it via next/headers and pass it to the one
  // custom inline <Script> tag it renders) and to the CSP response header
  // (so Next's own framework-injected hydration scripts pick it up too).
  const nonce = generateNonce();
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set('Content-Security-Policy', buildContentSecurityPolicy(nonce));
  return response;
}

export const config = {
  // Runs on every request except static assets and Next internals; API
  // proxy calls and app-route gating are both handled inside proxy() above.
  matcher: [
    '/((?!_next/static|_next/image|favicon\\.ico|brand/|images/|media/|robots\\.txt|sitemap\\.xml|sw\\.js|manifest\\.json|~partytown/).*)',
  ],
};
