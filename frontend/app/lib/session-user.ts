import { STORAGE_TOKEN_KEY, STORAGE_TENANT_KEY, resolveSessionTenant } from './api-client';

export type SessionClaims = {
  email?: string;
  sub?: string;
  tenant_id?: string;
  name?: string;
  given_name?: string;
  family_name?: string;
  roles?: string[];
};

export type SessionUser = {
  email: string;
  name: string;
  initials: string;
  tenantId: string;
  roles: string[];
};

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payloadSegment] = token.split('.');
    if (!payloadSegment) return null;
    const normalized = payloadSegment.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');
    return JSON.parse(atob(padded)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function initialsFrom(name: string, email: string): string {
  const words = name.split(/\s+/).filter(Boolean);
  if (words.length >= 2) return `${words[0]![0]}${words[1]![0]}`.toUpperCase();
  if (words.length === 1 && words[0]!.length >= 2) return words[0]!.slice(0, 2).toUpperCase();
  const local = email.split('@')[0] || '';
  if (local.length >= 2) return local.slice(0, 2).toUpperCase();
  if (local.length === 1) return `${local}·`.toUpperCase();
  return '';
}

function displayName(claims: SessionClaims, email: string): string {
  const full = asString(claims.name);
  if (full) return full;
  const first = asString(claims.given_name);
  const last = asString(claims.family_name);
  const joined = `${first} ${last}`.trim();
  if (joined) return joined;
  const local = email.split('@')[0]?.replace(/[._-]+/g, ' ').trim();
  if (local) {
    return local.replace(/\b\w/g, (ch) => ch.toUpperCase());
  }
  return '';
}

export function readSessionClaims(): SessionClaims | null {
  if (!globalThis.window) return null;
  const token = globalThis.localStorage?.getItem(STORAGE_TOKEN_KEY)?.trim() || '';
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (!payload) return null;

  const rolesRaw = payload.roles;
  const roles = Array.isArray(rolesRaw)
    ? rolesRaw.filter((role): role is string => typeof role === 'string')
    : [];

  return {
    email: asString(payload.email),
    sub: asString(payload.sub),
    tenant_id: asString(payload.tenant_id) || asString(globalThis.localStorage?.getItem(STORAGE_TENANT_KEY)),
    name: asString(payload.name),
    given_name: asString(payload.given_name),
    family_name: asString(payload.family_name),
    roles,
  };
}

/** Live session identity from the JWT. Never invents a display name. */
export function readSessionUser(): SessionUser | null {
  const claims = readSessionClaims();
  const tenantId = claims?.tenant_id || resolveSessionTenant();
  if (!claims && !tenantId) return null;

  const email = claims?.email || '';
  const name = claims ? displayName(claims, email) : '';
  return {
    email,
    name,
    initials: initialsFrom(name, email),
    tenantId,
    roles: claims?.roles || [],
  };
}
