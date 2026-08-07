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


  return (
    <header className="fixed top-0 left-0 z-[100] w-full pt-4 sm:pt-6 px-3 sm:px-4">
      <nav
        aria-label="Primary navigation"
        className={`mx-auto flex max-w-5xl items-center justify-between rounded-full border border-[#dbe6ee] bg-white/80 px-4 sm:px-6 py-2.5 sm:py-3 shadow-lg backdrop-blur-xl transition-shadow ${
          scrolled ? 'shadow-[0_8px_32px_rgba(11,27,43,0.12)]' : ''
        }`}
      >
        <Link href="/" className="flex items-center gap-2" aria-label="Nuxtron home">
          <img src="/brand/nuxtron-icon-square.svg" alt="" width={28} height={28} className="rounded-md" />
          <span className="[font-family:var(--font-display)] text-lg font-bold tracking-tight text-[#0b1b2b]">
            Nuxtron
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              className={`text-sm font-medium transition-colors ${
                pathname === href ? 'text-[#0b1b2b]' : 'text-[#55677c] hover:text-[#0b1b2b]'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          <Link href="/login" className="hidden md:block text-sm font-medium text-[#33475b] hover:text-[#0b1b2b]">
            Log in
          </Link>
          <Link
            href="/register"
            className="group relative inline-flex items-center justify-center overflow-hidden rounded-full bg-[#0ea5e9] px-5 py-2 shadow-[0_6px_18px_rgba(14,165,233,0.35)] transition-transform active:scale-95"
          >
            <span
              className="absolute inset-[-100%] animate-spin opacity-0 transition-opacity duration-300 group-hover:opacity-100 [animation-duration:3s]"
              style={{
                background: 'conic-gradient(from 90deg at 50% 50%, transparent 0%, transparent 75%, #f59e0b 100%)',
              }}
              aria-hidden="true"
            />
            <span className="absolute inset-[1px] rounded-full bg-[#0ea5e9]" aria-hidden="true" />
            <span className="relative z-10 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-white">
              Start free <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
          <button
            type="button"
            className="grid h-10 w-10 place-items-center rounded-full border border-[#dbe6ee] bg-white text-[#0b1b2b] md:hidden"
            onClick={() => setMobile((v) => !v)}
            aria-expanded={mobile}
            aria-label="Toggle navigation"
          >
            {mobile ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </nav>

      {mobile ? (
        <div className="mx-auto mt-2 w-[calc(100%-1.5rem)] max-w-5xl rounded-3xl border border-[#dbe6ee] bg-white/98 p-5 shadow-2xl backdrop-blur-xl md:hidden">
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map(([href, label]) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMobile(false)}
                className="rounded-xl px-3 py-2.5 text-sm font-semibold text-[#33475b] hover:bg-[#0ea5e9]/8 hover:text-[#0b1b2b]"
              >
                {label}
              </Link>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 border-t border-[#dbe6ee] pt-4">
            <Link
              href="/login"
              onClick={() => setMobile(false)}
              className="rounded-full border border-[#dbe6ee] px-4 py-2.5 text-center text-sm font-semibold text-[#0b1b2b]"
            >
              Log in
            </Link>
            <Link
              href="/register"
              onClick={() => setMobile(false)}
              className="rounded-full bg-[#0ea5e9] px-4 py-2.5 text-center text-sm font-semibold text-white"
            >
              Start free
            </Link>
          </div>
        </div>
      ) : null}
    </header>
  );
}
