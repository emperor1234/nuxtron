import { jwtVerify } from 'jose';

/**
 * Edge/server-side JWT verification for the Next.js proxy. Mirrors the
 * backend's HS256 contract exactly (backend/fastapi/app/deps.py:
 * `_resolve_jwt_secret` / `_jwt_verify_hs256`) so a token accepted here is
 * accepted there, and vice versa:
 *   - signing key: JWT_SIGNING_KEY, falling back to FASTAPI_API_KEY only
 *     outside production
 *   - never accept a known-default/placeholder secret
 *   - required claims: `sub`, `tenant_id`, `exp` (roles/jti are optional)
 */

export type SessionClaims = {
  sub: string;
  tenantId: string;
  roles: string[];
  jti: string;
  exp: number;
};

// Same denylist as backend/fastapi/app/deps.py `_INSECURE_DEFAULT_SECRETS` —
// keep in sync so neither side can be tricked into trusting a shipped default.
const INSECURE_DEFAULT_SECRETS = new Set(['change-this-fastapi-key', 'change-me', 'dev-jwt-signing-key', 'secret', '']);

function isProductionRuntime(): boolean {
  const environment = (process.env.ENVIRONMENT || '').trim().toLowerCase();
  if (environment) return environment === 'production';
  return (process.env.NODE_ENV || '').trim().toLowerCase() === 'production';
}

function resolveJwtSecret(): string | null {
  const primary = (process.env.JWT_SIGNING_KEY || '').trim();
  if (primary && !INSECURE_DEFAULT_SECRETS.has(primary)) return primary;

  if (isProductionRuntime()) return null;

  const fallback = (process.env.FASTAPI_API_KEY || '').trim();
  if (fallback && !INSECURE_DEFAULT_SECRETS.has(fallback)) return fallback;

  return null;
}

function sanitizeRoles(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const out: string[] = [];
  for (const item of raw) {
    if (typeof item === 'string' && item.trim() && !out.includes(item.trim())) {
      out.push(item.trim());
    }
  }
  return out;
}

/**
 * Verifies a bearer/session JWT. Returns `null` for any invalid, expired,
 * unsigned, or malformed token — callers must treat `null` as "not
 * authenticated" and never distinguish reasons to the client.
 */
export async function verifySessionToken(token: string): Promise<SessionClaims | null> {
  const secret = resolveJwtSecret();
  if (!secret || !token) return null;

  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(secret), { algorithms: ['HS256'] });
    const tenantId = typeof payload.tenant_id === 'string' ? payload.tenant_id.trim() : '';
    const sub = typeof payload.sub === 'string' ? payload.sub.trim() : '';
    if (!tenantId) return null;

    return {
      sub,
      tenantId,
      roles: sanitizeRoles(payload.roles),
      jti: typeof payload.jti === 'string' ? payload.jti : '',
      exp: typeof payload.exp === 'number' ? payload.exp : 0,
    };
  } catch {
    return null;
  }
}
