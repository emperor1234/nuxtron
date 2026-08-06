import { NextRequest, NextResponse } from 'next/server';
import { verifySessionToken } from '@/app/lib/auth/jwt-edge';
import { SESSION_COOKIE_NAME, sessionCookieOptions } from '@/app/lib/auth/session-cookie';

/**
 * Mirrors the session token into an httpOnly cookie so `proxy.ts` can gate
 * `/dashboard/**`-equivalent page requests server-side, before any markup is
 * sent (A01: Broken Access Control). The token itself continues to live in
 * localStorage too (see app/lib/api-client.ts) for building the
 * `Authorization` header on same-origin API calls — this cookie exists
 * purely for server-side route gating and is never read by client JS.
 */

export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid request body.' }, { status: 400 });
  }

  const token = typeof (body as { token?: unknown })?.token === 'string' ? (body as { token: string }).token.trim() : '';
  if (!token) {
    return NextResponse.json({ detail: 'A session token is required.' }, { status: 400 });
  }

  const claims = await verifySessionToken(token);
  if (!claims) {
    return NextResponse.json({ detail: 'Token could not be verified.' }, { status: 401 });
  }

  const maxAgeSeconds = Math.max(0, claims.exp - Math.floor(Date.now() / 1000));
  if (maxAgeSeconds <= 0) {
    return NextResponse.json({ detail: 'Token is already expired.' }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE_NAME, token, sessionCookieOptions(maxAgeSeconds));
  return response;
}

export async function DELETE(): Promise<NextResponse> {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE_NAME, '', sessionCookieOptions(0));
  return response;
}
