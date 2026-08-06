import { Check } from 'lucide-react';
import type { ReactNode } from 'react';

type AuthLayoutProps = {
  /** Short heading above the form, e.g. "Sign in to Nuxtron". */
  heading: string;
  /** One-line supporting copy under the heading. */
  subheading: string;
  /** Brand-panel headline (left side). */
  panelTitle: string;
  /** Three short value-prop bullets for the brand panel. */
  panelPoints: readonly string[];
  /** The form. */
  children: ReactNode;
};

/**
 * Two-column auth shell matching the marketing site's red-noir identity:
 * black canvas, signature red glow, glass form card. Replaces the earlier
 * light navy/cyan shell, which didn't match the rest of the product.
 */
export function AuthLayout({ heading, subheading, panelTitle, panelPoints, children }: AuthLayoutProps) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black px-4 pb-16 pt-28 sm:px-6 sm:pt-32">
      {/* Ambient background — same grid + red glow as the marketing pages */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div
          className="absolute inset-0"
          style={{ background: 'linear-gradient(to bottom, #140505 0%, #050505 45%)' }}
        />
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)',
            backgroundSize: '44px 44px',
            maskImage: 'radial-gradient(circle at 50% 0%, black 0%, transparent 75%)',
            WebkitMaskImage: 'radial-gradient(circle at 50% 0%, black 0%, transparent 75%)',
          }}
        />
        <div
          className="absolute left-1/2 top-1/2 h-[900px] w-[900px] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ background: 'rgba(239,35,60,0.08)', filter: 'blur(140px)' }}
        />
      </div>

      <div className="relative z-10 grid w-full max-w-[1100px] grid-cols-1 overflow-hidden rounded-3xl border border-white/10 shadow-[0_40px_120px_rgba(0,0,0,0.6)] lg:grid-cols-2 lg:items-stretch">
        {/* Brand panel */}
        <section
          aria-hidden
          className="relative hidden flex-col justify-between overflow-hidden border-white/10 bg-gradient-to-b from-zinc-900/80 to-black p-12 lg:flex lg:border-r"
        >
          <div
            className="pointer-events-none absolute inset-0 opacity-90"
            style={{ background: 'radial-gradient(70% 60% at 20% 0%, rgba(239,35,60,0.16), transparent 70%)' }}
          />
          <div className="relative">
            <div className="mb-12 flex items-center gap-2">
              <span className="h-5 w-5 rotate-45 rounded-sm bg-[#ef233c]" />
              <span className="[font-family:var(--font-display)] text-lg font-bold tracking-tight text-white">
                Nuxtron
              </span>
            </div>
            <h2 className="max-w-[18ch] text-3xl font-semibold leading-tight tracking-tight text-white [font-family:var(--font-display)]">
              {panelTitle}
            </h2>
          </div>
          <ul className="relative mt-10 space-y-4">
            {panelPoints.map((point) => (
              <li key={point} className="flex items-start gap-3 text-zinc-300">
                <Check className="mt-0.5 h-5 w-5 shrink-0 text-[#ef233c]" strokeWidth={2.5} aria-hidden="true" />
                <span className="leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Form card */}
        <section className="bg-zinc-950/60 p-8 backdrop-blur-xl sm:p-10 lg:p-12">
          <h1 className="text-2xl font-semibold tracking-tight text-white [font-family:var(--font-display)]">
            {heading}
          </h1>
          <p className="mt-2 text-zinc-400">{subheading}</p>
          <div className="mt-8">{children}</div>
        </section>
      </div>
    </main>
  );
}

/** Shared primary submit button for auth forms. */
export function AuthSubmit({ busy, children }: { busy: boolean; children: ReactNode }) {
  return (
    <button
      type="submit"
      disabled={busy}
      aria-busy={busy}
      className="inline-flex w-full items-center justify-center rounded-xl bg-[#ef233c] px-6 py-3 text-base font-bold text-white transition-all duration-200 hover:bg-[#d81f36] hover:scale-[1.01] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </button>
  );
}

/** Footer link row under an auth form. */
export function AuthAltLinks({ children }: { children: ReactNode }) {
  return <p className="mt-6 text-center text-sm text-zinc-500">{children}</p>;
}

export const authLink = 'font-semibold text-[#ef233c] underline-offset-4 hover:underline';
