'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { ArrowRight, Menu, X } from 'lucide-react';

const NAV_LINKS = [
  ['/features', 'Features'],
  ['/integrations', 'Integrations'],
  ['/pricing', 'Pricing'],
  ['/about', 'Company'],
  ['/trust', 'Trust'],
] as const;

export function MarketingHeader() {
  const pathname = usePathname();
  const [mobile, setMobile] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const update = () => setScrolled(window.scrollY > 12);
    update();
    window.addEventListener('scroll', update, { passive: true });
    return () => window.removeEventListener('scroll', update);
  }, []);

  useEffect(() => {
    setMobile(false);
  }, [pathname]);

  return (
    <header className="fixed top-0 left-0 z-[100] w-full pt-4 sm:pt-6 px-3 sm:px-4">
      <nav
        aria-label="Primary navigation"
        className={`mx-auto flex max-w-5xl items-center justify-between rounded-full border border-[#18181814] bg-white/80 px-4 sm:px-6 py-2.5 sm:py-3 shadow-sm backdrop-blur-xl transition-shadow ${
          scrolled ? 'shadow-[0_8px_30px_rgba(24,24,24,0.08)]' : ''
        }`}
      >
        <Link href="/" className="flex items-center gap-2" aria-label="Nuxtron home">
          <img src="/brand/nuxtron-icon-square.svg" alt="" width={20} height={20} className="rounded-sm" />
          <span className="[font-family:var(--font-geist-sans)] text-lg font-bold tracking-tight text-[#181818]">
            Nuxtron
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              className={`text-sm font-medium transition-colors ${
                pathname === href ? 'text-[#181818]' : 'text-[#6b6d72] hover:text-[#181818]'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          <Link href="/login" className="hidden md:block text-sm font-medium text-[#46484d] hover:text-[#181818]">
            Log in
          </Link>
          <Link
            href="/register"
            className="group relative inline-flex items-center justify-center overflow-hidden rounded-full bg-[#181818] px-5 py-2 transition-transform active:scale-95"
          >
            <span
              className="absolute inset-[-100%] animate-spin opacity-0 transition-opacity duration-300 group-hover:opacity-100 [animation-duration:3s]"
              style={{
                background:
                  'conic-gradient(from 90deg at 50% 50%, transparent 0%, transparent 75%, #21ccee 85%, #466cf3 92%, #f83d69 100%)',
              }}
              aria-hidden="true"
            />
            <span className="absolute inset-[1px] rounded-full bg-[#181818]" aria-hidden="true" />
            <span className="relative z-10 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-white">
              Start free <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
          <button
            type="button"
            className="grid h-10 w-10 place-items-center rounded-full border border-[#18181814] bg-white text-[#181818] md:hidden"
            onClick={() => setMobile((v) => !v)}
            aria-expanded={mobile}
            aria-label="Toggle navigation"
          >
            {mobile ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </nav>

      {mobile ? (
        <div className="mx-auto mt-2 w-[calc(100%-1.5rem)] max-w-5xl rounded-3xl border border-[#18181814] bg-white/95 p-5 shadow-2xl backdrop-blur-xl md:hidden">
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map(([href, label]) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMobile(false)}
                className="rounded-xl px-3 py-2.5 text-sm font-semibold text-[#46484d] hover:bg-[#18181808] hover:text-[#181818]"
              >
                {label}
              </Link>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 border-t border-[#18181814] pt-4">
            <Link
              href="/login"
              onClick={() => setMobile(false)}
              className="rounded-full border border-[#18181822] px-4 py-2.5 text-center text-sm font-semibold text-[#181818]"
            >
              Log in
            </Link>
            <Link
              href="/register"
              onClick={() => setMobile(false)}
              className="rounded-full bg-[#181818] px-4 py-2.5 text-center text-sm font-semibold text-white"
            >
              Start free
            </Link>
          </div>
        </div>
      ) : null}
    </header>
  );
}
