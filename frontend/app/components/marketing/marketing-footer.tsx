'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const COLUMNS = [
  {
    title: 'Platform',
    links: [
      ['/features', 'Features'],
      ['/pricing', 'Pricing'],
      ['/trust', 'Trust & security'],
      ['/tools/translation-studio', 'Translation Studio'],
    ],
  },
  {
    title: 'Company',
    links: [
      ['/about', 'About'],
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
    <footer className="relative overflow-hidden border-t border-[#18181814] bg-[#fafafa] pt-16 sm:pt-20 pb-8">
      <div className="mx-auto mb-16 sm:mb-20 grid max-w-6xl grid-cols-2 gap-8 sm:grid-cols-3 sm:gap-10 lg:grid-cols-6 lg:gap-8 px-6">
        <div className="col-span-2 sm:col-span-3 lg:col-span-2">
          <Link href="/" className="mb-5 flex items-center gap-2" aria-label="Nuxtron home">
            <span className="h-5 w-5 rotate-45 rounded-sm bg-[#466cf3]" aria-hidden="true" />
            <span className="[font-family:var(--font-geist-sans)] text-xl font-bold tracking-tight text-[#181818]">
              Nuxtron
            </span>
          </Link>
          <p className="max-w-xs text-sm leading-relaxed text-[#8a8d93]">
            One command center for CRM, SEO &amp; AI visibility, social operations, and security — run by your team
            and your AI agents together.
          </p>
        </div>

        {COLUMNS.map((column) => (
          <div key={column.title}>
            <h3 className="mb-5 text-xs font-bold uppercase tracking-widest text-[#181818]">{column.title}</h3>
            <ul className="space-y-3.5 text-sm text-[#6b6d72]">
              {column.links.map(([href, label]) => (
                <li key={href}>
                  <Link href={href} className="transition-colors hover:text-[#181818]">
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

      <div className="mx-auto flex max-w-6xl items-center justify-center border-t border-[#18181814] px-6 pt-8 text-[11px] uppercase tracking-widest text-[#8a8d93]">
        <p>&copy; {new Date().getFullYear()} Nuxtron, Inc. All rights reserved.</p>
      </div>
    </footer>
  );
}
