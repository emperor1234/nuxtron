import type { NextConfig } from 'next';
import { copyLibFiles } from '@builder.io/partytown/utils';
import path from 'path';

// Content-Security-Policy is NOT set here. A static CSP can't carry a
// per-request nonce, and `script-src 'self'` without one blocks every
// inline hydration `<script>` the App Router injects — see proxy.ts and
// app/lib/security/csp.ts, which set a fresh nonce'd CSP per page request
// instead. Everything below is safe to stay static (no per-request state
// needed).

// Applied to every route. `frame-ancestors 'none'` + `X-Frame-Options` block
// clickjacking; HSTS enforces TLS (A02); Permissions-Policy strips unused
// device access to shrink the attack surface.
const securityHeaders = [
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
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'assets.watermelon.sh',
      },
    ],
  },
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
