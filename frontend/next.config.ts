import type { NextConfig } from 'next';
import { copyLibFiles } from '@builder.io/partytown/utils';
import path from 'path';

const isDev = process.env.NODE_ENV !== 'production';

/**
 * Content-Security-Policy for the dashboard.
 *
 * The app renders pervasive inline styles and loads Google Fonts, so
 * `style-src` and `font-src` must permit those origins. `'unsafe-inline'`
 * scripts are tolerated only in development (Next.js dev overlay + HMR);
 * production drops it. All data egress is same-origin through the
 * `/api/fastapi` proxy, so `connect-src 'self'` is sufficient.
 */
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self'${isDev ? " 'unsafe-inline' 'unsafe-eval'" : ''}`,
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

// Applied to every route. `frame-ancestors 'none'` + `X-Frame-Options` block
// clickjacking; HSTS enforces TLS (A02); Permissions-Policy strips unused
// device access to shrink the attack surface.
const securityHeaders = [
  { key: 'Content-Security-Policy', value: contentSecurityPolicy },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'X-DNS-Prefetch-Control', value: 'off' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()' },
  { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  typedRoutes: true,
  allowedDevOrigins: ['localhost', '127.0.0.1'],
  outputFileTracingRoot: path.join(__dirname, '..'),
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },
  // Partytown lib files are served from public/~partytown/ — Next.js handles this
  // automatically without any rewrite. A rewrite would shadow the public/ path.
  webpack(config, { isServer }) {
    if (!isServer) {
      // Copy Partytown lib files to public/~partytown on every build
      copyLibFiles(path.join(process.cwd(), 'public', '~partytown')).catch(() => {});
    }
    return config;
  },
};

export default nextConfig;
