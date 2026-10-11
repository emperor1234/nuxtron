'use client';

import Link from 'next/link';
import Image from 'next/image';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { FOOTER_COLUMNS, FOOTER_LEGAL_LINKS } from './site-links';

/**
 * Site footer. Hidden on the sign-in pages, which keep their own focused
 * layout. Columns come from site-links.ts, the same source as the header, so
 * a page can't be linked from one and forgotten in the other.
 */
export function MarketingFooter({ authRoutes }: { authRoutes: readonly string[] }) {
  const pathname = usePathname();
  if (authRoutes.includes(pathname)) return null;

  return (
    <footer className="mk-foot">
      <div className="mk-foot-inner">
        <div className="mk-foot-brand">
          <Link href="/" className="mk-foot-logo" aria-label="Nuxtron home">
            <Image src="/brand/nuxtron-icon-square.svg" alt="" width={29} height={29} className="mk-logo-mark" />
            Nuxtron
          </Link>
          <p className="mk-foot-tagline">
            Search and AI visibility, content, social and customer work — two products, one account.
          </p>
        </div>

        <nav aria-label="Footer" className="mk-foot-columns">
          {FOOTER_COLUMNS.map((column) => (
            <div key={column.id} className="mk-foot-column">
              <h2 className="mk-foot-heading">{column.title}</h2>
              <ul className="mk-foot-links">
                {column.links.map((link) => (
                  <li key={`${column.id}:${link.href}:${link.label}`}>
                    <Link href={link.href as Route}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </div>

      <div aria-hidden="true" className="mk-foot-wordmark">
        NUXTRON
      </div>

      <div className="mk-foot-bottom">
        <p>&copy; {new Date().getFullYear()} Nuxtron, Inc. All rights reserved.</p>
        <ul className="mk-foot-legal">
          {FOOTER_LEGAL_LINKS.map((link) => (
            <li key={link.href}>
              <Link href={link.href as Route}>{link.label}</Link>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}
