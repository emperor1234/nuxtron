'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const COLUMNS = [
  {
    title: 'Platform',
    links: [
      ['/features', 'Features'],
      ['/integrations', 'Integrations'],
      ['/pricing', 'Pricing'],
      ['/trust', 'Trust & security'],
      ['/tools/translation-studio', 'Translation Studio'],
    ],
  },
  {
    title: 'Resources',
    links: [
      ['/blog', 'Blog'],
      ['/case-studies', 'Case studies'],
      ['/changelog', 'Changelog'],
      ['/faq', 'FAQ'],
    ],
  },
  {
    title: 'Company',
    links: [
      ['/about', 'About'],
      ['/careers', 'Careers'],
      ['/contact', 'Contact'],
    ],
  },
  {
    title: 'Account',
    links: [
      ['/login', 'Log in'],
      ['/register', 'Create account'],
    ],
  },
  {
    title: 'Legal',
    links: [
      ['/privacy', 'Privacy'],
      ['/terms', 'Terms'],
    ],
  },
] as const;

export function MarketingFooter({ authRoutes }: { authRoutes: readonly string[] }) {
  const pathname = usePathname();
  if (authRoutes.includes(pathname)) return null;

  return (
    <footer className="relative overflow-hidden border-t border-[#dbe6ee] bg-[#f6fafd] pt-16 sm:pt-20 pb-8">
      <div className="mx-auto mb-16 sm:mb-20 grid max-w-6xl grid-cols-2 gap-8 sm:grid-cols-3 sm:gap-10 lg:grid-cols-7 lg:gap-8 px-6">
        <div className="col-span-2 sm:col-span-3 lg:col-span-2">
          <Link href="/" className="mb-5 flex items-center gap-2" aria-label="Nuxtron home">
          <img src="/brand/nuxtron-icon-square.svg" alt="" width={26} height={26} className="rounded-md" />
            <span className="[font-family:var(--font-display)] text-xl font-bold tracking-tight text-[#0b1b2b]">
              Nuxtron
            </span>
          </Link>
          <p className="max-w-xs text-sm leading-relaxed text-[#55677c]">
            One command center for CRM, SEO &amp; AI visibility, social operations, and security — run by your team
            and your AI agents together.
          </p>
        </div>

        {COLUMNS.map((column) => (
          <div key={column.title}>
            <h3 className="mb-5 text-xs font-bold uppercase tracking-widest text-[#0c8fcc]">{column.title}</h3>
            <ul className="space-y-3.5 text-sm text-[#55677c]">
              {column.links.map(([href, label]) => (
                <li key={href}>
                  <Link href={href} className="transition-colors hover:text-[#0b1b2b]">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div aria-hidden="true" className="flex select-none items-center justify-center overflow-hidden py-6">
        <span className="mk-wordmark">NUXTRON</span>
      </div>

      <div className="mx-auto flex max-w-6xl items-center justify-center border-t border-[#dbe6ee] px-6 pt-8 text-[11px] uppercase tracking-widest text-[#8595a8]">
        <p>&copy; {new Date().getFullYear()} Nuxtron, Inc. All rights reserved.</p>
      </div>
    </footer>
  );
}
