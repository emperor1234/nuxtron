'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { getCatalogByRoutePath } from '../module-catalog';

export default function SeoRouteIdentityBanner() {
  const pathname = usePathname();
  const moduleInfo = useMemo(() => getCatalogByRoutePath(pathname), [pathname]);

  if (!moduleInfo || pathname === '/seo') return null;

  return (
    <nav aria-label="SEO location" className="seo-crumb">
      <Link href="/seo">SEO</Link>
      <span aria-hidden="true">/</span>
      <span>{moduleInfo.category}</span>
      <span aria-hidden="true">/</span>
      <strong>{moduleInfo.title}</strong>
    </nav>
  );
}
