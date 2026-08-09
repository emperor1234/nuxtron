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
 * Two-column auth shell matching the marketing site's Salix-derived identity:
 * white canvas, blue/cyan/pink gradient accent, bordered form card.
 */
export function AuthLayout({ heading, subheading, panelTitle, panelPoints, children }: AuthLayoutProps) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-white px-4 pb-16 pt-28 sm:px-6 sm:pt-32">
      {/* Ambient background — same faint dot grid + gradient glow as the marketing pages */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(rgba(24,24,24,0.06) 1px, transparent 1px)',
            backgroundSize: '28px 28px',
            maskImage: 'radial-gradient(circle at 50% 0%, black 0%, transparent 55%)',
            WebkitMaskImage: 'radial-gradient(circle at 50% 0%, black 0%, transparent 55%)',
          }}
        />
        <div
          className="absolute left-1/2 top-0 h-[500px] w-[900px] -translate-x-1/2"
          style={{
            background: 'linear-gradient(90deg, #21ccee, #466cf3, #f83d69)',
            opacity: 0.08,
            filter: 'blur(160px)',
          }}
        />
      </div>

      <div className="relative z-10 grid w-full max-w-[1100px] grid-cols-1 overflow-hidden rounded-3xl border border-[#18181814] bg-white shadow-[0_40px_120px_rgba(24,24,24,0.1)] lg:grid-cols-2 lg:items-stretch">
        {/* Brand panel */}
        <section
          aria-hidden
          className="relative hidden flex-col justify-between overflow-hidden border-[#18181814] bg-[#181818] p-12 lg:flex lg:border-r"
        >
          <div
            className="pointer-events-none absolute inset-0 opacity-90"
            style={{ background: 'radial-gradient(70% 60% at 20% 0%, rgba(70,108,243,0.25), transparent 70%)' }}
          />
          <div className="relative">
            <div className="mb-12 flex items-center gap-2">
              <span className="h-5 w-5 rotate-45 rounded-sm bg-[#466cf3]" />
              <span className="[font-family:var(--font-geist-sans)] text-lg font-bold tracking-tight text-white">
                Nuxtron
              </span>
            </div>
            <h2 className="max-w-[18ch] text-3xl font-semibold leading-tight tracking-tight text-white [font-family:var(--font-geist-sans)]">
              {panelTitle}
            </h2>
          </div>
          <ul className="relative mt-10 space-y-4">
            {panelPoints.map((point) => (
              <li key={point} className="flex items-start gap-3 text-zinc-300">
                <Check className="mt-0.5 h-5 w-5 shrink-0 text-[#466cf3]" strokeWidth={2.5} aria-hidden="true" />
                <span className="leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Form card */}
        <section className="bg-white p-8 sm:p-10 lg:p-12">
          <h1 className="text-2xl font-semibold tracking-tight text-[#181818] [font-family:var(--font-geist-sans)]">
            {heading}
          </h1>
          <p className="mt-2 text-[#46484d]">{subheading}</p>
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
      className="inline-flex w-full items-center justify-center rounded-xl bg-[#181818] px-6 py-3 text-base font-bold text-white transition-all duration-200 hover:bg-black hover:scale-[1.01] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </button>
  );
}

/** Footer link row under an auth form. */
export function AuthAltLinks({ children }: { children: ReactNode }) {
  return <p className="mt-6 text-center text-sm text-[#8a8d93]">{children}</p>;
}

export const authLink = 'font-semibold text-[#466cf3] underline-offset-4 hover:underline';
