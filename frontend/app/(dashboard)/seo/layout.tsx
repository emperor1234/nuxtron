import type { ReactNode } from 'react';
import SeoRouteIdentityBanner from './components/seo-route-identity-banner';

export default function SeoLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="seo-ultimate-shell relative min-h-screen overflow-x-clip bg-[var(--bg)] text-[var(--text)]">
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(6,182,212,0.18),transparent_38%),radial-gradient(circle_at_80%_10%,rgba(99,102,241,0.16),transparent_34%),radial-gradient(circle_at_70%_78%,rgba(45,212,191,0.14),transparent_38%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(148,163,184,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(148,163,184,0.05)_1px,transparent_1px)] bg-[size:70px_70px] [mask-image:radial-gradient(ellipse_at_center,black_58%,transparent_100%)]" />
      </div>

      <div className="pointer-events-none fixed inset-x-0 top-0 z-0 h-28 bg-gradient-to-b from-cyan-300/12 to-transparent" />

      <div className="relative z-10">
        <SeoRouteIdentityBanner />
        {children}
      </div>
    </div>
  );
}
