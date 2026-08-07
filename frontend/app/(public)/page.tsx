import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Bot, Radar, Share2, Shield, Star } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Nuxtron — The command center for growth and security teams',
  description:
    'CRM, SEO & AI-visibility intelligence, social operations, and security monitoring — run by your team and your AI agents, in one workspace.',
  alternates: { canonical: '/' },
};

const CONNECTED = ['CRM', 'SEO & AEO', 'Social', 'Reviews', 'SIEM', 'IRA Agent'];

const PILLARS = [
  {
    icon: Bot,
    title: 'Autonomous AI agents',
    body: 'IRA plans, executes, and reports on real work across your stack — every action logged and reversible, nothing runs unsupervised by default.',
    span: 'lg:col-span-2 lg:row-span-2',
  },
  {
    icon: Radar,
    title: 'SEO & AI visibility',
    body: 'Track rankings, AEO/GEO citations, and how AI answer engines represent your brand — in one board, not five tabs.',
    span: 'lg:col-span-2',
  },
  {
    icon: Share2,
    title: 'Social command center',
    body: 'Schedule, publish, and listen across every channel from a single calendar.',
    span: '',
  },
  {
    icon: Shield,
    title: 'Security & SIEM',
    body: 'Real-time threat detection and audit trails built into the same workspace as the work itself.',
    span: '',
  },
];

const ORG_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Nuxtron',
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Web',
  description:
    'CRM, SEO & AI-visibility intelligence, social operations, and security monitoring — run by your team and your AI agents, in one workspace.',
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'USD',
  },
  aggregateRating: {
    '@type': 'AggregateRating',
    ratingValue: '4.8',
    reviewCount: '46',
  },
};

export default function HomePage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ORG_JSON_LD) }} />

      <section className="relative flex min-h-screen flex-col items-center justify-center px-6 pb-20 pt-40">
        <div className="mk-fade-up mx-auto max-w-4xl text-center">
          <span className="mk-eyebrow mb-8 inline-flex">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#0ea5e9] opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#0ea5e9]" />
            </span>
            Now live: autonomous AI agent orchestration
          </span>

          <h1 className="text-5xl font-semibold leading-[1.08] tracking-tighter text-[#0b1b2b] sm:text-7xl">
            One command center for
            <br />
            <span className="relative inline-block text-[#0ea5e9]">
              growth &amp; security
              <svg
                className="absolute -bottom-2 left-0 h-3 w-full text-[#f59e0b] opacity-70"
                viewBox="0 0 100 10"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <path d="M0 5 Q 50 10 100 5" stroke="currentColor" strokeWidth="2" fill="none" />
              </svg>
            </span>
          </h1>

          <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed text-[#55677c] sm:text-xl">
            Nuxtron connects your CRM, SEO &amp; AI-visibility data, social channels, and security monitoring — then
            gives your team AI agents that can act on all of it, with a full audit trail.
          </p>

          <div className="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta">
              Start free <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
            <Link href="/contact" className="mk-btn-secondary">
              Talk to sales
            </Link>
          </div>
        </div>

        <div className="mt-28 w-full border-y border-[#dbe6ee] bg-[#f6fafd] py-8 opacity-90 backdrop-blur-sm transition-opacity hover:opacity-100">
          <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-6 md:flex-row md:gap-12">
            <p className="shrink-0 text-xs font-bold uppercase tracking-widest text-[#8595a8]">
              One workspace, connected:
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
              {CONNECTED.map((item) => (
                <span key={item} className="text-sm font-semibold text-[#33475b]">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mb-16 max-w-2xl">
            <span className="mk-eyebrow mb-5">Platform</span>
            <h2 className="text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">
              Replace six disconnected tools with <span className="text-[#0ea5e9]">one system</span>
            </h2>
            <p className="mt-5 text-lg text-[#55677c]">
              Every pillar shares the same data, the same tenant, the same AI agents — so nothing you build in one
              tool has to be re-explained to the next.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {PILLARS.map((pillar) => (
              <div
                key={pillar.title}
                className={`group relative overflow-hidden rounded-2xl border border-[#dbe6ee] bg-white p-8 transition-all hover:border-[#0ea5e9]/40 hover:shadow-[0_16px_40px_rgba(11,27,43,0.08)] ${pillar.span}`}
              >
                <div className="relative z-10 flex h-full flex-col">
                  <div className="mb-6 inline-flex w-fit rounded-lg border border-[#dbe6ee] bg-[#f0f8fd] p-3 text-[#0ea5e9]">
                    <pillar.icon size={22} strokeWidth={1.75} aria-hidden="true" />
                  </div>
                  <h3 className="mb-3 text-2xl font-semibold tracking-tight text-[#0b1b2b]">{pillar.title}</h3>
                  <p className="text-[15px] leading-relaxed text-[#55677c]">{pillar.body}</p>
                </div>
                <div
                  className="pointer-events-none absolute inset-0 opacity-0 transition-opacity group-hover:opacity-10"
                  style={{ background: 'radial-gradient(circle at top right, #0ea5e9, transparent 70%)' }}
                  aria-hidden="true"
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-[#0ea5e9]/20 bg-[#0ea5e9] px-6 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-6 flex justify-center gap-1 text-[#f59e0b]" aria-hidden="true">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star key={i} size={22} fill="currentColor" />
            ))}
          </div>
          <p className="text-2xl font-semibold leading-tight text-white sm:text-4xl [font-family:var(--font-display)]">
            &ldquo;We replaced four tools and a spreadsheet with Nuxtron. Our team finally works from one source of
            truth.&rdquo;
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-full bg-white text-[#0ea5e9]">
              <span className="text-sm font-bold">RM</span>
            </div>
            <div className="text-left">
              <div className="text-sm font-bold text-white">Head of Revenue Operations</div>
              <div className="text-sm font-medium text-white/75">Mid-market SaaS company</div>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section text-center">
        <div className="mk-container">
          <span className="mk-eyebrow mb-5">Pricing</span>
          <h2 className="mx-auto max-w-xl text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">
            Simple plans that grow with you
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-lg text-[#55677c]">
            Start free. Upgrade when your team needs more seats, more automation, or dedicated support.
          </p>
          <Link
            href="/pricing"
            className="mt-10 inline-flex items-center gap-2 rounded-full border border-[#dbe6ee] px-7 py-3.5 font-semibold text-[#0b1b2b] transition-colors hover:border-[#0ea5e9] hover:text-[#0ea5e9]"
          >
            See full pricing <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      <section className="mk-section text-center">
        <div className="mk-container max-w-3xl">
          <h2 className="text-5xl font-bold tracking-tighter text-[#0b1b2b] sm:text-7xl">
            Ready to run everything <span className="text-[#0ea5e9]">from one place?</span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-lg text-[#55677c]">
            Create your workspace in minutes. No credit card required to start.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/register" className="mk-shiny-cta">
              Start free <ArrowRight size={16} />
            </Link>
            <Link href="/contact" className="mk-btn-secondary">
              Talk to sales
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
