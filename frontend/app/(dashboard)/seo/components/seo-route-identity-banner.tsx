'use client';

import { useMemo } from 'react';
import { usePathname } from 'next/navigation';

import { getCatalogByRoutePath } from '../module-catalog';
import { getTierBadgeStyle } from '../tier-tone';

export default function SeoRouteIdentityBanner() {
  const pathname = usePathname();
  const moduleInfo = useMemo(() => getCatalogByRoutePath(pathname), [pathname]);

  if (!moduleInfo || pathname === '/seo') return null;

  return (
    <div className="mx-auto w-full max-w-7xl px-4 pt-4 md:px-6 lg:px-8">
      <section
        style={{
          border: '1px solid var(--line)',
          background: 'var(--card)',
          borderRadius: 16,
          padding: '10px 12px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: 10,
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: 'var(--brand)',
            }}
          >
            {moduleInfo.category}
          </span>
          {moduleInfo.tier && <span style={getTierBadgeStyle(moduleInfo.tier)}>{moduleInfo.tier}</span>}
          <strong style={{ fontSize: 13, color: 'var(--text)' }}>{moduleInfo.title}</strong>
        </div>
        <p style={{ margin: '6px 0 0', fontSize: 12, lineHeight: 1.5, color: 'var(--muted)' }}>{moduleInfo.summary}</p>
      </section>
    </div>
  );
}
