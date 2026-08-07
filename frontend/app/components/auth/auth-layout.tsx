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
 * Two-column auth shell matching the marketing site's light, blue-branded
 * identity: white canvas, light-blue glow, glass form card.
 */
export function AuthLayout({ heading, subheading, panelTitle, panelPoints, children }: AuthLayoutProps) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-white px-4 pb-16 pt-28 sm:px-6 sm:pt-32">
      {/* Ambient background — same grid + light-blue glow as the marketing pages */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div
          className="absolute inset-0"
          style={{ background: 'linear-gradient(to bottom, #f2fbff 0%, #ffffff 45%)' }}
        />
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'linear-gradient(rgba(14,165,233,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(14,165,233,0.05) 1px, transparent 1px)',
            backgroundSize: '44px 44px',
            maskImage: 'radial-gradient(circle at 50% 0%, black 0%, transparent 75%)',
            WebkitMaskImage: 'radial-gradient(circle at 50% 0%, black 0%, transparent 75%)',
          }}
        />
        <div
          className="absolute left-1/2 top-1/2 h-[900px] w-[900px] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ background: 'rgba(14,165,233,0.1)', filter: 'blur(140px)' }}
        />
      </div>

      <div className="relative z-10 grid w-full max-w-[1100px] grid-cols-1 overflow-hidden rounded-3xl border border-[#dbe6ee] bg-white shadow-[0_40px_120px_rgba(11,27,43,0.14)] lg:grid-cols-2 lg:items-stretch">
        {/* Brand panel */}
        <section
          aria-hidden
          className="relative hidden flex-col justify-between overflow-hidden border-[#dbe6ee] bg-gradient-to-b from-[#0b1b2b] to-[#0e2740] p-12 lg:flex lg:border-r"
        >
          <div
            className="pointer-events-none absolute inset-0 opacity-90"
            style={{ background: 'radial-gradient(70% 60% at 20% 0%, rgba(14,165,233,0.28), transparent 70%)' }}
          />
          <div className="relative">
            <div className="mb-12 flex items-center gap-2">
              <img src="/brand/nuxtron-icon-square.svg" alt="" width={22} height={22} className="rounded-md" />
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
              <li key={point} className="flex items-start gap-3 text-[#c3d8e8]">
                <Check className="mt-0.5 h-5 w-5 shrink-0 text-[#38bdf8]" strokeWidth={2.5} aria-hidden="true" />
                <span className="leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Form card */}
        <section className="bg-white p-8 sm:p-10 lg:p-12">
          <h1 className="text-2xl font-semibold tracking-tight text-[#0b1b2b] [font-family:var(--font-display)]">
            {heading}
          </h1>
          <p className="mt-2 text-[#55677c]">{subheading}</p>
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
      className="inline-flex w-full items-center justify-center rounded-xl bg-[#0ea5e9] px-6 py-3 text-base font-bold text-white shadow-[0_8px_20px_rgba(14,165,233,0.3)] transition-all duration-200 hover:bg-[#0c8fcc] hover:scale-[1.01] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </button>
  );
}

/** Footer link row under an auth form. */
export function AuthAltLinks({ children }: { children: ReactNode }) {
  return <p className="mt-6 text-center text-sm text-[#55677c]">{children}</p>;
}

export const authLink = 'font-semibold text-[#0c8fcc] underline-offset-4 hover:underline';
