const isDev = process.env.NODE_ENV !== 'production';

/**
 * Builds a per-request Content-Security-Policy. `script-src` must carry a
 * fresh nonce every request — a static `script-src 'self'` (the previous
 * config, set once in next.config.ts) blocks the inline `<script>` tags
 * Next.js's App Router injects on every page for RSC hydration data. With
 * no nonce and no `unsafe-inline`, every one of those gets blocked, React
 * never hydrates, and forms silently fall back to native browser
 * submission — which submits via GET with every field, including
 * passwords, appended to the URL. That is what "poor" login/signup +
 * plaintext passwords in the address bar actually was: a CSP
 * misconfiguration, not a form bug.
 *
 * `'strict-dynamic'` lets scripts loaded BY the nonce'd bootstrap script
 * (Next's own chunks) execute without each needing its own nonce — the
 * standard pairing for nonce-based CSP with framework-injected scripts.
 */
export function buildContentSecurityPolicy(nonce: string): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ''}`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data: blob: https:",
    "connect-src 'self'",
    "worker-src 'self' blob:",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    'upgrade-insecure-requests',
  ].join('; ');
}

export function generateNonce(): string {
  return Buffer.from(crypto.randomUUID()).toString('base64');
}
