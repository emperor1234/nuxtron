export const SESSION_COOKIE_NAME = 'nuxtron_session';

/** Shared cookie flags for setting/clearing the session cookie. */
export function sessionCookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    secure: (process.env.NODE_ENV || '').trim().toLowerCase() === 'production',
    sameSite: 'lax' as const,
    path: '/',
    maxAge: maxAgeSeconds,
  };
}
