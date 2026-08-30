'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MENUS, RAIL_ITEMS, SETTINGS_ITEM } from './nav';
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
  if (pathname === '/dashboard' || pathname.startsWith('/seo')) return null;

  const all = [...RAIL_ITEMS, SETTINGS_ITEM];
  let section = all[0]!;
  let best = -1;
  for (const item of all) {
    if ((pathname === item.href || pathname.startsWith(`${item.href}/`)) && item.href.length > best) {
      section = item;
      best = item.href.length;
    }
  }

  const menu = MENUS[section.key];
  const leaf = pathname
    .split('/')
    .filter(Boolean)
    .slice(-1)[0];
  const leafLabel = leaf ? titleize(leaf) : section.label;
  const sameAsSection = pathname === section.href;

  return (
    <nav aria-label="Location" className={styles.crumb}>
      <Link href={section.href}>{menu?.title || section.label}</Link>
      {!sameAsSection ? (
        <>
          <span aria-hidden="true">/</span>
          <strong>{leafLabel}</strong>
        </>
      ) : null}
    </nav>
  );
}
