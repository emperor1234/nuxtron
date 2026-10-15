'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MENUS, RAIL_ITEMS, SETTINGS_ITEM } from './nav';
import { ROUTE_INDEX } from './route-index.generated';
import styles from './shell.module.css';

function titleize(segment: string): string {
  return segment
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export default function DashboardRouteIdentity() {
  const pathname = usePathname() || '/dashboard';
  if (pathname === '/dashboard') return null;

  const all = [...RAIL_ITEMS, SETTINGS_ITEM];
  let section: (typeof all)[number] | undefined;
  let best = -1;
  for (const item of all) {
    const menuRoutes = MENUS[item.key]?.groups.flatMap((group) =>
      group.items.map((entry) => entry.href),
    ) ?? [];
    for (const prefix of [item.href, ...(item.matchPrefixes ?? []), ...menuRoutes]) {
      if (
        (pathname === prefix || pathname.startsWith(`${prefix}/`)) &&
        prefix.length > best
      ) {
        section = item;
        best = prefix.length;
      }
    }
  }

  const menu = section ? MENUS[section.key] : undefined;
  const leaf = pathname
    .split('/')
    .filter(Boolean)
    .slice(-1)[0];
  const canonicalRoute = ROUTE_INDEX.find((entry) => entry.route === pathname);
  const leafLabel = canonicalRoute?.title ?? (leaf ? titleize(leaf) : 'Dashboard');
  const sameAsSection = section?.href === pathname;

  return (
    <nav aria-label="Breadcrumb" className={styles.crumb}>
      {section && !sameAsSection ? (
        <>
          <Link href={section.href}>{menu?.title || section.label}</Link>
          <span aria-hidden="true">/</span>
        </>
      ) : null}
      <strong aria-current="page">{leafLabel}</strong>
    </nav>
  );
}
